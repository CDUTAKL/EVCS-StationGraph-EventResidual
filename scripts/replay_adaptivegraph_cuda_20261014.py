#!/usr/bin/env python3
"""Replay SG-EXP-004 checkpoints and isolate CUDA/CPU adjacency differences. No training."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import platform
import sys
import types
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import yaml

TOL = 5e-6


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write(path, obj):
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def selection(model):
    with torch.no_grad():
        logits = model.source_embedding @ model.target_embedding.T / model._embed_dim**.5
        dense = torch.softmax(torch.relu(logits), dim=-1)
        mask = torch.eye(model._num_nodes, dtype=torch.bool, device=dense.device)
        masked = dense.masked_fill(mask, float('-inf'))
        vals, idx = torch.topk(masked, min(model._top_k, model._num_nodes-1), dim=-1)
        sparse = torch.zeros_like(masked).scatter(-1, idx, vals)
        ambiguous = []
        for n in range(model._num_nodes):
            cutoff = vals[n, -1]
            above = int((masked[n] > cutoff).sum())
            tied = int((masked[n] == cutoff).sum())
            if tied > vals.shape[-1] - above:
                ambiguous.append(n)
        return {'topk_indices': idx.cpu().numpy(), 'topk_values': vals.cpu().numpy(),
                'pre_symmetry_sparse': sparse.cpu().numpy(),
                'mixed_normalized_adjacency': model._build_adaptive_adjacency().cpu().numpy(),
                'ambiguous_rows': np.asarray(ambiguous, dtype=np.int64)}


def run(component, out, preflight, manifest_path=None):
    if out.exists():
        raise ValueError('Output directory must be new')
    out.mkdir(parents=True)
    verified_files = 0
    if manifest_path is not None:
        manifest_root = manifest_path.parent.resolve()
        for relative, digest in json.loads(manifest_path.read_text()).items():
            path = (manifest_root / relative).resolve()
            if not path.is_relative_to(manifest_root) or not path.is_file() or sha(path) != digest:
                raise ValueError(f'Replay package hash mismatch: {relative}')
            verified_files += 1
    elif not preflight:
        raise ValueError('CUDA evidence replay requires --manifest for immutable input provenance')
    sys.path.insert(0, str(component / 'src'))
    from evcs_station_graph.data import NodeWindowDataset, WindowSpec, load_tensor_bundle
    from evcs_station_graph.evaluation import FrozenEventRule, apply_frozen_event_rule
    from evcs_station_graph.training.engine import _make_loader, _predict
    from evcs_station_graph.training.factory import build_model

    environment = {'python': sys.version, 'torch': str(torch.__version__), 'cuda_build': torch.version.cuda,
                   'cuda_available': torch.cuda.is_available(), 'platform': platform.platform()}
    expected = str(torch.__version__).split('+')[0] == '2.4.1' and torch.version.cuda == '12.1'
    if torch.cuda.is_available():
        environment['gpu'] = torch.cuda.get_device_name(0)
    if not preflight and not (expected and environment['cuda_available'] and platform.system() == 'Linux'):
        write(out / 'status.json', {'status': 'BLOCKED_ORIGINAL_ENVIRONMENT_UNAVAILABLE', 'environment': environment,
                                  'required': 'Linux, PyTorch 2.4.1, CUDA build 12.1, CUDA device', 'retraining_performed': False})
        raise RuntimeError('Original CUDA/PyTorch environment contract not available')
    group = component / 'results/SG-EXP-004'
    cfg = yaml.safe_load((group / 'config_resolved.yaml').read_text())
    data = load_tensor_bundle(component / 'data/dataset.npz')
    with np.load(group / 'relation_matrices.npz', allow_pickle=False) as graphs:
        adj = [graphs[n] for n in ('load', 'event', 'pattern')]
    ds = NodeWindowDataset(data, 'test', WindowSpec(96, 4))
    rows = []
    os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')
    torch.set_num_threads(2)
    torch.backends.cudnn.benchmark = False
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    for seed in (2024, 2025, 2026):
        folder = group / f'seed-{seed}'
        tracked = [folder / 'model.pt', folder / 'predictions.csv.gz', folder / 'metrics.json',
                   group / 'config_resolved.yaml', component / 'data/dataset.npz']
        hashes = {str(p.relative_to(component)): sha(p) for p in tracked}
        run_manifest = json.loads((folder / 'manifest.json').read_text())
        if isinstance(run_manifest, dict) and 'files' in run_manifest:
            run_manifest = run_manifest['files']
        # The output package MANIFEST authenticates all files; original run
        # manifests may contain absolute legacy paths and are retained as history.
        payload = torch.load(folder / 'model.pt', map_location='cpu', weights_only=True)
        assert payload['seed'] == seed
        state = payload['model_state']
        conf = copy.deepcopy(cfg)
        params = conf['experiment']['model_params']
        params['levels'] = len([k for k in state if k.startswith('tcn.network.') and k.endswith('.conv.weight')])
        first = state['tcn.network.0.conv.weight']
        params['hidden_dim'] = int(first.shape[0])
        conf['project'].pop('history_steps', None)
        model = build_model(conf, input_dim=int(first.shape[1]), horizon=4,
                            num_nodes=len(data.node_ids), adjacencies=adj)
        model.load_state_dict(state, strict=True)
        model.eval()
        original = json.loads((folder / 'metrics.json').read_text())
        assert sum(p.numel() for p in model.parameters() if p.requires_grad) == original['training']['trainable_parameters']
        frame = pd.read_csv(folder / 'predictions.csv.gz').sort_values(['origin_index', 'horizon', 'node_index'])
        assert len(frame) == len(ds.origins)*4*len(data.node_ids)
        assert not frame.duplicated(['split', 'origin_index', 'horizon', 'node_id']).any()
        assert bool((frame['split'] == 'test').all())
        assert np.array_equal(frame.origin_index.to_numpy(), np.repeat(ds.origins, 40))
        assert np.array_equal(frame.horizon.to_numpy(), np.tile(np.repeat(np.arange(1, 5), 10), len(ds.origins)))
        assert np.array_equal(frame.node_index.to_numpy(), np.tile(np.arange(10), len(ds.origins)*4))
        assert np.array_equal(frame.node_id.to_numpy(), np.tile(data.node_ids, len(ds.origins)*4))
        cpu_selection = selection(model)
        np.savez_compressed(out / f'seed-{seed}-cpu-adjacency.npz', **cpu_selection)
        if preflight:
            rows.append({'seed': seed, 'source_hashes': hashes, 'parameters': original['training']['trainable_parameters'],
                         'levels': params['levels'], 'ambiguous_topk_rows': cpu_selection['ambiguous_rows'].tolist()})
            continue
        rule_cfg = original['frozen_event_rule']
        rule = FrozenEventRule(thresholds=np.asarray(rule_cfg['thresholds'], dtype='float32'),
                               quantile=rule_cfg['quantile'], score_definition=rule_cfg['score_definition'],
                               window_extension=rule_cfg['window_extension'], score_stats=rule_cfg['score_stats'])
        triggers = np.zeros((len(data.timestamps_ns), len(data.node_ids)), dtype=bool)
        triggers[ds.origins] = apply_frozen_event_rule(data, ds.origins, rule)

        def predict(current, device):
            with torch.no_grad():
                values = _predict(current, _make_loader(ds, 256, False, seed), torch.device(device), triggers, data)
            assert float(np.abs(values['truth'].ravel()-frame.y_true.to_numpy()).max()) <= 1e-7
            assert np.array_equal(values['target_event'].ravel(), frame.target_event.to_numpy())
            assert np.array_equal(np.repeat(values['rule_trigger'][:, None, :], 4, axis=1).ravel(), frame.rule_trigger.to_numpy())
            return values['prediction']

        native_cpu = predict(model, 'cpu')
        cuda_model = copy.deepcopy(model).to('cuda')
        cuda_selection = selection(cuda_model)
        np.savez_compressed(out / f'seed-{seed}-cuda-adjacency.npz', **cuda_selection)
        cuda_pred = predict(cuda_model, 'cuda')
        explicit = torch.from_numpy(cuda_selection['mixed_normalized_adjacency'].copy())
        fixed_cpu = copy.deepcopy(model)
        fixed_cpu._build_adaptive_adjacency = types.MethodType(lambda self: explicit, fixed_cpu)
        fixed_pred = predict(fixed_cpu, 'cpu')
        original_pred = frame.y_pred.to_numpy().reshape(cuda_pred.shape)
        differences = {name: float(np.abs(pred-original_pred).max()) for name, pred in
                       [('native_cpu', native_cpu), ('native_cuda', cuda_pred), ('cpu_with_cuda_adjacency', fixed_pred)]}
        changed = np.flatnonzero(np.any(np.sort(cpu_selection['topk_indices'], axis=1) !=
                                       np.sort(cuda_selection['topk_indices'], axis=1), axis=1))
        only_tied = set(changed.tolist()).issubset(set(cpu_selection['ambiguous_rows'].tolist()))
        confirmed = (differences['native_cuda'] <= TOL and differences['cpu_with_cuda_adjacency'] <= TOL
                     and differences['native_cpu'] > TOL and len(changed) > 0 and only_tied)
        np.savez_compressed(out / f'seed-{seed}-predictions.npz', native_cpu=native_cpu, native_cuda=cuda_pred,
                            cpu_with_cuda_adjacency=fixed_pred, origin_indices=ds.origins)
        assert hashes == {str(p.relative_to(component)): sha(p) for p in tracked}
        row = {'seed': seed, 'source_hashes': hashes, 'max_prediction_abs_differences': differences,
               'changed_neighbor_rows': changed.tolist(), 'changes_only_in_cpu_tied_rows': only_tied,
               'tie_backend_explanation_confirmed': confirmed,
               'status': 'PASS' if differences['native_cuda'] <= TOL and differences['cpu_with_cuda_adjacency'] <= TOL else 'FAIL'}
        rows.append(row)
        write(out / f'seed-{seed}.json', row)
        print(f'{row["status"]} AdaptiveGraph seed-{seed}: {differences}', flush=True)
    result = {'status': 'PREFLIGHT_ONLY_CUDA_PENDING' if preflight else ('PASS' if all(r['status']=='PASS' for r in rows) else 'FAIL'),
              'environment': environment, 'original_environment_version_matched': expected,
              'prediction_atol': TOL, 'retraining_performed': False,
              'historical_source_authenticity': 'recovered source snapshot; training git_commit was null',
              'manifest_verified_files': verified_files,
              'script_sha256': sha(__file__), 'runs': rows}
    write(out / 'status.json', result)
    write(out / 'output-manifest.json', {p.name: sha(p) for p in out.iterdir() if p.is_file()})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--component', type=Path, required=True, help='Frozen legacy component root')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--preflight-only', action='store_true', help='CPU artifact and adjacency checks; no CUDA replay')
    parser.add_argument('--manifest', type=Path, help='Replay package MANIFEST.json; required for CUDA evidence')
    args = parser.parse_args()
    run(args.component.resolve(), args.out.resolve(), args.preflight_only,
        args.manifest.resolve() if args.manifest else None)
