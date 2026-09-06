"""Auditable train/selection/export loop for SG-EXP-019, never legacy engine."""
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import subprocess
import time

import numpy as np
import torch
from torch.utils.data import DataLoader

from .data import sha256
from .models import build_model, count_parameters


def write_json(path, value):
    path = Path(path)
    tmp = path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)+'\n')
    os.replace(tmp, path)


def default_config(model, seed, smoke=False):
    return dict(protocol='SG-DATA-006-eventtime-v1', experiment='SG-EXP-019', model=model,
                seed=seed, max_epochs=2 if smoke else 60, patience=8,
                batch_size=4 if smoke else 256, lr=.001, weight_decay=.0001,
                loss='standardized_L1', selection='tuning_original_unit_MAE',
                mode='SMOKE_NOT_SCIENTIFIC_EVIDENCE' if smoke else 'formal',
                train_limit=16 if smoke else None, eval_limit=8 if smoke else None,
                num_workers=0, threads=2, precision='float32', deterministic=True,
                gradient_clip=5.)


def code_digest():
    root = Path(__file__).resolve().parents[1]
    paths = sorted((root/'eventtime').glob('*.py')) + [root/'models'/f for f in ('graph.py','tcn.py','common.py')]
    return hashlib.sha256(''.join(p.name+sha256(p) for p in paths).encode()).hexdigest()


def setup(seed, device, threads=2):
    if device not in ('cpu', 'cuda'):
        raise ValueError('Use cpu for local smoke or cuda for formal runs')
    if device == 'cuda' and not torch.cuda.is_available():
        raise RuntimeError('CUDA requested but unavailable; no silent CPU fallback')
    os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.set_num_threads(threads)
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark = False
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False


def contract(data, cfg, device):
    obj = dict(config=cfg, dataset_sha256=data.digest, code_sha256=code_digest(),
               torch=str(torch.__version__), device=device,
               gpu=torch.cuda.get_device_name(0) if device == 'cuda' else platform.machine())
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()


def atomic_checkpoint(path, value):
    tmp = Path(str(path)+'.tmp')
    torch.save(value, tmp)
    os.replace(tmp, path)


def loader(data, split, cfg, epoch=None):
    limit = cfg['train_limit'] if split == 'train' else cfg['eval_limit']
    generator = torch.Generator().manual_seed(cfg['seed'] + (epoch or 0))
    return DataLoader(data.windows(split, limit), batch_size=cfg['batch_size'],
                      shuffle=epoch is not None, generator=generator, num_workers=0)


@torch.no_grad()
def predict(model, data, split, cfg, device):
    model.eval()
    predictions, origins = [], []
    for x, _, k in loader(data, split, cfg):
        predictions.append(model(x.to(device)).prediction.cpu().numpy().astype('float64'))
        origins.append(k.numpy())
    origins = np.concatenate(origins)
    pred = np.concatenate(predictions) * data.arrays['target_std'] + data.arrays['target_mean']
    actual = data.arrays['targets'][origins[:, None] + np.arange(1, 5)]
    if not np.isfinite(pred).all():
        raise FloatingPointError('Nonfinite prediction')
    return actual, pred, origins


def metric_report(y, pred, target, trigger):
    error = np.abs(y.astype('float64') - pred.astype('float64'))
    total = float(error.sum())
    cells = {}
    for t, r in ((True, True), (True, False), (False, True), (False, False)):
        mask = (target == t) & (trigger == r)
        n = int(mask.sum())
        s = float(error[mask].sum())
        cells[f'target_{int(t)}_trigger_{int(r)}'] = dict(n=n, mae=s/n if n else None,
              sum_absolute_error=s, error_contribution=s/total if total else 0.)
    mae = float(error.mean())
    reconstructed = sum(c['sum_absolute_error'] for c in cells.values()) / error.size
    gap = abs(mae-reconstructed)
    if gap > 1e-9:
        raise AssertionError('Four-cell reconstruction failed')
    return dict(n=int(error.size), mae=mae, rmse=float(np.sqrt(np.mean((y-pred)**2))),
                event_mae=float(error[target].mean()) if target.any() else None,
                stable_mae=float(error[~target].mean()) if (~target).any() else None,
                by_horizon_mae=error.mean(axis=(0,2)).tolist(),
                by_node_mae=error.mean(axis=(0,1)).tolist(), four_cells=cells,
                four_cell_reconstruction_error=gap)


def environment(device):
    return dict(python=platform.python_version(), platform=platform.platform(),
                torch=str(torch.__version__), numpy=np.__version__, cuda=torch.version.cuda,
                device=device, gpu=torch.cuda.get_device_name(0) if device=='cuda' else None)


def train(data, cfg, out, device='cuda', resume=False, stop_after=None):
    """Only train and tuning are touched. Interruption limit is not a scientific budget."""
    out = Path(out)
    setup(cfg['seed'], device, cfg['threads'])
    fingerprint = contract(data, cfg, device)
    model = build_model(cfg['model'], data.arrays['graphs']).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=cfg['lr'], weight_decay=cfg['weight_decay'])
    start, history, best, stale = 0, [], float('inf'), 0
    if out.exists() and any(out.iterdir()) and not resume:
        raise FileExistsError(f'Refusing overwrite: {out}; use --resume')
    out.mkdir(parents=True, exist_ok=True)
    if resume:
        ckpt = torch.load(out/'last.pt', map_location='cpu', weights_only=True)
        if ckpt.get('contract') != fingerprint:
            raise ValueError('Checkpoint contract mismatch: code/data/config/device/environment changed')
        model.load_state_dict(ckpt['model'], strict=True)
        optimizer.load_state_dict(ckpt['optimizer'])
        start, history, best, stale = ckpt['epoch'], ckpt['history'], ckpt['best'], ckpt['stale']
        torch.set_rng_state(ckpt['rng'])
        if device == 'cuda':
            torch.cuda.set_rng_state_all(ckpt['cuda_rng'])
        if ckpt['complete']:
            return ckpt
    write_json(out/'config_resolved.json', dict(cfg, dataset_sha256=data.digest,
        code_sha256=code_digest(), contract=fingerprint, trainable_parameters=count_parameters(model)))
    write_json(out/'environment.json', environment(device))
    if not (out/'environment.txt').exists():
        with (out/'environment.txt').open('w') as f:
            import sys
            subprocess.run([sys.executable, '-m', 'pip', 'freeze'], stdout=f, stderr=subprocess.STDOUT, check=True)
    for epoch in range(start, cfg['max_epochs']):
        tic = time.monotonic()
        model.train()
        loss_sum, count = 0., 0
        for x, y, _ in loader(data, 'train', cfg, epoch=epoch):
            optimizer.zero_grad(set_to_none=True)
            prediction = model(x.to(device)).prediction
            loss = torch.nn.functional.l1_loss(prediction, y.to(device))
            if not torch.isfinite(loss):
                raise FloatingPointError('Nonfinite training loss')
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), cfg['gradient_clip'], error_if_nonfinite=True)
            optimizer.step()
            loss_sum += float(loss.detach()) * y.numel()
            count += y.numel()
        y, pred, _ = predict(model, data, 'tuning', cfg, device)
        score = float(np.abs(y-pred).mean())
        improved = score < best
        if improved:
            best, stale = score, 0
        else:
            stale += 1
        row = dict(epoch=epoch+1, train_standardized_mae=loss_sum/count,
                   tuning_mae=score, seconds=time.monotonic()-tic)
        history.append(row)
        print(json.dumps(dict(model=cfg['model'], seed=cfg['seed'], **row)), flush=True)
        ckpt = dict(contract=fingerprint, model=model.state_dict(), optimizer=optimizer.state_dict(),
                    epoch=epoch+1, best=best, stale=stale, history=history,
                    rng=torch.get_rng_state(), cuda_rng=torch.cuda.get_rng_state_all() if device=='cuda' else [],
                    complete=stale >= cfg['patience'] or epoch+1 >= cfg['max_epochs'])
        # Best is saved first; if last-save is interrupted the deterministic epoch
        # is repeated. Neither calibration nor test participates in this decision.
        if improved:
            atomic_checkpoint(out/'best.pt', dict(contract=fingerprint, model=model.state_dict(), epoch=epoch+1, tuning_mae=score))
        atomic_checkpoint(out/'last.pt', ckpt)
        write_json(out/'train_log.json', history)
        if ckpt['complete'] or (stop_after is not None and epoch+1 >= stop_after):
            break
    return ckpt


def export(data, cfg, out, device='cuda'):
    out = Path(out)
    setup(cfg['seed'], device, cfg['threads'])
    expected = contract(data, cfg, device)
    last = torch.load(out/'last.pt', map_location='cpu', weights_only=True)
    best = torch.load(out/'best.pt', map_location='cpu', weights_only=True)
    if last.get('contract') != expected or best.get('contract') != expected or not last['complete']:
        raise ValueError('Incomplete training or checkpoint contract mismatch')
    model = build_model(cfg['model'], data.arrays['graphs']).to(device)
    model.load_state_dict(best['model'], strict=True)
    reports = {}
    for split in ('tuning', 'calibration', 'test'):
        y, pred, origins = predict(model, data, split, cfg, device)
        target, trigger = data.masks(origins)
        reports[split] = metric_report(y, pred, target, trigger)
        target_indices = origins[:, None] + np.arange(1, 5)
        np.savez_compressed(out/f'predictions_{split}.npz', y_true=y, y_pred=pred,
             origins=origins, node_ids=data.arrays['node_ids'], target_event=target,
             rule_trigger=trigger, target_timestamps_ns=data.arrays['timestamps_ns'][target_indices],
             origin_cutoff_ns=data.arrays['timestamps_ns'][origins]+900_000_000_000)
    write_json(out/'metrics.json', dict(mode=cfg['mode'], unit='retrospective proxy kWh/15min',
                                      selected_epoch=best['epoch'], splits=reports))
    if hasattr(model, 'relation_weights_gcn1'):
        write_json(out/'beta.json', {f'layer_{i}': getattr(model, f'relation_weights_gcn{i}').softmax(0).detach().cpu().tolist() for i in (1,2)})
    (out/'exit_code.txt').write_text('0\n')
    write_json(out/'run_summary.json', dict(status='complete', mode=cfg['mode'],
        artifact_path=str(out.resolve()), contract=expected, best_epoch=best['epoch']))
    write_json(out/'manifest.json', {p.name: sha256(p) for p in sorted(out.iterdir())
                                   if p.is_file() and p.name != 'manifest.json' and not p.name.endswith('.tmp')})
    return reports
