#!/usr/bin/env python3
"""SG-EXP-031: equal-capacity JPL relation replacements; isolated runner adapter."""
from __future__ import annotations
import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import numpy as np
import torch
from evcs_station_graph.eventtime import runner
from evcs_station_graph.eventtime.models import build_model as original_factory, count_parameters
from evcs_station_graph.jpl_eventtime.data import FrozenJPLData, sha256

EXPERIMENT = 'SG-EXP-031'
VARIANTS = ('full', 'load_to_self', 'event_to_self', 'pattern_to_self')
SEEDS = (2024, 2025, 2026)
DEFAULT_DATA = ROOT / 'data/jpl/dataset.npz'

def factory(name, graphs):
    if name not in VARIANTS:
        raise ValueError(f'Unknown relation control: {name}')
    modified = np.array(graphs, copy=True)
    if name != 'full':
        slot = VARIANTS.index(name) - 1
        modified[slot] = np.eye(10, dtype=modified.dtype)
    return original_factory('mrg_full', modified)

@contextmanager
def isolated_factory():
    # Dependency injection is scoped to this dedicated CLI process. The old
    # runner and frozen bundles are not edited; restore on every exit path.
    previous = runner.build_model
    runner.build_model = factory
    try:
        yield
    finally:
        runner.build_model = previous

def verify_bundle():
    path = ROOT / 'BUNDLE_MANIFEST.json'
    if path.exists():
        for rel, digest in json.loads(path.read_text()).items():
            candidate = (ROOT / rel).resolve()
            if not candidate.is_relative_to(ROOT.resolve()) or not candidate.is_file() or sha256(candidate) != digest:
                raise ValueError(f'Input bundle mismatch: {rel}')

def parameter_digest(model):
    h = hashlib.sha256()
    for name, param in model.named_parameters():
        h.update(name.encode())
        h.update(param.detach().cpu().numpy().tobytes())
    return h.hexdigest()

def config(name, seed, data):
    cfg = runner.default_config(name, seed)
    cfg.update(experiment=EXPERIMENT, protocol='SG-DATA-007-jpl-eventtime-v1',
               relation_control=name, entrypoint_sha256=sha256(Path(__file__)),
               original_graph_sha256=hashlib.sha256(data.arrays['graphs'].tobytes()).hexdigest(),
               plan_sha256=sha256(ROOT / 'metadata/training-design-20261015.md'))
    runner.setup(seed, 'cpu')
    model = factory(name, data.arrays['graphs'])
    cfg['initial_parameters_sha256'] = parameter_digest(model)
    cfg['used_graph_sha256'] = hashlib.sha256(np.stack([a.numpy() for a in model._get_adjacencies()]).tobytes()).hexdigest()
    return cfg

def check(data, device, out):
    if (out / 'jpl').exists():
        raise ValueError('Cannot replace contract check after training starts')
    out.mkdir(parents=True, exist_ok=True)
    records = []
    for seed in SEEDS:
        initial = None
        for name in VARIANTS:
            cfg = config(name, seed, data)
            runner.setup(seed, device)
            model = factory(name, data.arrays['graphs']).to(device)
            digest = parameter_digest(model)
            if initial is None:
                initial = digest
            assert digest == initial == cfg['initial_parameters_sha256']
            assert count_parameters(model) == 32714
            assert model._num_relations == 3
            for index, graph in enumerate(model._get_adjacencies()):
                expected = np.eye(10) if name != 'full' and index == VARIANTS.index(name)-1 else data.arrays['graphs'][index]
                assert np.array_equal(graph.detach().cpu().numpy(), expected)
            x, y, _ = next(iter(runner.loader(data, 'train', dict(cfg, train_limit=4, batch_size=4), epoch=0)))
            loss = torch.nn.functional.l1_loss(model(x.to(device)).prediction, y.to(device))
            loss.backward()  # Contract probe only: no optimizer or parameter update.
            for layer in (model.gcn1, model.gcn2):
                assert len(layer.W_r) == 3
                for transform in layer.W_r:
                    grad = transform.weight.grad
                    assert grad is not None and torch.isfinite(grad).all() and torch.count_nonzero(grad) > 0
            assert parameter_digest(model) == digest
            records.append(dict(variant=name, seed=seed, parameters=32714, initial_sha256=digest,
                                branch_gradients_pass=True, parameters_unchanged=True, config=cfg))
    report = dict(status='PASS', experiment=EXPERIMENT, training_started=False,
                  dataset_sha256=data.digest, device=device, environment=runner.environment(device),
                  split_origins={s:len(data.arrays[s+'_origins']) for s in ('train','tuning','calibration','test')},
                  runs=records)
    runner.write_json(out / 'contract-check.json', report)
    print(json.dumps(dict(status='PASS', configurations=len(records), training_started=False)), flush=True)

def locked_runs(data, root, device):
    locks = []
    for seed in SEEDS:
        for name in VARIANTS:
            cfg = config(name, seed, data)
            folder = root / 'jpl' / name / f'seed-{seed}'
            ckpt = torch.load(folder / 'last.pt', map_location='cpu', weights_only=True)
            best = torch.load(folder / 'best.pt', map_location='cpu', weights_only=True)
            expected = runner.contract(data, cfg, device)
            if not ckpt['complete'] or ckpt['contract'] != expected or best['contract'] != expected:
                raise ValueError(f'Incomplete or changed training contract: {folder}')
            locks.append(dict(variant=name, seed=seed, best_sha256=sha256(folder/'best.pt'),
                              last_sha256=sha256(folder/'last.pt'), best_epoch=best['epoch']))
    return locks

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('check', 'train', 'evaluate', 'all'))
    parser.add_argument('--data', type=Path, default=DEFAULT_DATA)
    parser.add_argument('--out', type=Path, default=ROOT/'results/SG-EXP-031')
    parser.add_argument('--device', choices=('cpu','cuda'), default='cuda')
    parser.add_argument('--variant', choices=VARIANTS, default='full')
    parser.add_argument('--seed', type=int, choices=SEEDS, default=2024)
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    if args.command != 'check' and args.device != 'cuda':
        raise ValueError('Formal runs require CUDA')
    verify_bundle()
    data = FrozenJPLData(args.data)
    with isolated_factory():
        if args.command == 'check':
            check(data, args.device, args.out)
            return
        gate = json.loads((args.out/'contract-check.json').read_text())
        if gate['status'] != 'PASS' or gate['dataset_sha256'] != data.digest or gate['device'] != 'cuda':
            raise ValueError('Missing CUDA contract check')
        if gate['environment'] != runner.environment(args.device):
            raise ValueError('Environment changed after contract check')
        frozen = { (r['variant'],r['seed']):r['config'] for r in gate['runs'] }
        for seed in SEEDS:
            for name in VARIANTS:
                if config(name,seed,data) != frozen[(name,seed)]:
                    raise ValueError('Design/config changed after contract check')
        if args.command in ('train','all'):
            jobs = [(seed,name) for seed in SEEDS for name in VARIANTS] if args.command == 'all' else [(args.seed,args.variant)]
            for seed,name in jobs:
                runner.train(data,config(name,seed,data),args.out/'jpl'/name/f'seed-{seed}',args.device,resume=args.resume)
        if args.command in ('evaluate','all'):
            locks = locked_runs(data,args.out,args.device)
            lock_path = args.out/'checkpoint-lock.json'
            if lock_path.exists() and json.loads(lock_path.read_text()) != locks:
                raise ValueError('Frozen checkpoint lock changed')
            runner.write_json(lock_path,locks)
            for seed in SEEDS:
                for name in VARIANTS:
                    runner.export(data,config(name,seed,data),args.out/'jpl'/name/f'seed-{seed}',args.device)
            runner.write_json(args.out/'suite-status.json',dict(status='COMPLETED_UNREVIEWED',runs=12,experiment=EXPERIMENT))

if __name__ == '__main__':
    main()
