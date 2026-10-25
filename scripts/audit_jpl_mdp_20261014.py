#!/usr/bin/env python3
"""Post-hoc JPL L1/L3 checkpoint audit. Inference only; frozen archives stay read-only."""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import platform
import sys
from pathlib import Path

import numpy as np
import torch

REPO = Path(__file__).resolve().parents[1]
DEFAULT_BUNDLE = REPO / 'outputs/evidence/checkpoint-replay-20261012/components/sg028'
TOL = 5e-6
INTERVENTIONS = {
    'g1_load_g2_learn': ([10., 0., 0.], None),
    'g1_learn_g2_pattern': (None, [0., 0., 10.]),
    'both_load': ([10., 0., 0.], [10., 0., 0.]),
    'both_event': ([0., 10., 0.], [0., 10., 0.]),
    'both_pattern': ([0., 0., 10.], [0., 0., 10.]),
    'equal': ([0., 0., 0.], [0., 0., 0.]),
    'swapped': ('swap', 'swap'),
}


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def metrics(y, pred, event, trigger):
    error = np.abs(y.astype(np.float64) - pred.astype(np.float64))
    total = float(error.sum())
    cells = {}
    for t, r in ((1, 1), (1, 0), (0, 1), (0, 0)):
        mask = (event == t) & (trigger == r)
        n = int(mask.sum())
        absolute_sum = float(error[mask].sum())
        cells[f'target_{t}_trigger_{r}'] = {
            'n': n, 'sample_share': n / error.size,
            'mae': absolute_sum / n if n else None,
            'sum_absolute_error': absolute_sum,
            'error_share': absolute_sum / total if total else 0.,
        }
    closure = abs(sum(c['sum_absolute_error'] for c in cells.values()) / error.size - float(error.mean()))
    assert sum(c['n'] for c in cells.values()) == error.size and closure < 1e-12
    return {'n': int(error.size), 'mae': float(error.mean()),
            'rmse': float(np.sqrt((error**2).mean())),
            'event_mae': float(error[event].mean()), 'stable_mae': float(error[~event].mean()),
            'by_horizon_mae': error.mean(axis=(0, 2)).tolist(),
            'by_node_mae': error.mean(axis=(0, 1)).tolist(),
            'four_cells': cells, 'weighted_mae_closure_gap': closure}


def run(bundle, out):
    if out.exists():
        raise ValueError('Use a new audit output directory')
    out.mkdir(parents=True)
    sys.path.insert(0, str(bundle / 'src'))
    spec = importlib.util.spec_from_file_location('frozen_jpl_mdp', bundle / 'scripts/jpl_experiment.py')
    experiment = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(experiment)
    original_manifest = experiment.verify_bundle()
    experiment.validate_training_spec()
    data = experiment.FrozenJPLData(experiment.DATA_PATH)
    lock = read(bundle / 'results/checkpoint_lock.json')
    export = read(bundle / 'results/test_export_state.json')
    assert lock['status'] == 'all_12_best_checkpoints_locked_before_test_export'
    assert export['status'] == 'all_12_test_exports_completed_once'
    assert lock['dataset_sha256'] == data.digest
    results, provenance = [], []
    reference_arrays = None
    for seed in (2024, 2025, 2026):
        folder = bundle / f'results/formal/mrg_full/seed-{seed}'
        record = next(r for r in lock['runs'] if r['model'] == 'mrg_full' and r['seed'] == seed)
        checkpoint, archived_file = folder / 'best.pt', folder / 'predictions_test.npz'
        tracked = [checkpoint, folder / 'last.pt', archived_file, folder / 'metrics.json',
                   folder / 'config_resolved.json', folder / 'train_log.json']
        before = {str(p.relative_to(bundle)): sha(p) for p in tracked}
        assert sha(checkpoint) == record['best_sha256']
        assert sha(folder / 'last.pt') == record['last_sha256']
        state_record = export['runs'][f'mrg_full/seed-{seed}']
        assert state_record['test_prediction_sha256'] == sha(archived_file)
        assert state_record['metrics_sha256'] == sha(folder / 'metrics.json')
        cfg = read(folder / 'config_resolved.json')
        expected = experiment.resolved_config('mrg_full', seed)
        assert all(cfg.get(k) == v for k, v in expected.items())
        assert cfg['code_sha256'] == experiment.runner.code_digest()
        payload = torch.load(checkpoint, map_location='cpu', weights_only=True)
        assert payload['contract'] == record['contract'] == cfg['contract']
        assert payload['epoch'] == read(folder / 'run_summary.json')['best_epoch']
        with np.load(archived_file, allow_pickle=False) as archive:
            saved = {k: archive[k] for k in archive.files}
        origins = data.arrays['test_origins']
        idx = origins[:, None] + np.arange(1, 5)
        event, trigger = data.masks(origins)
        arrays = {'origins': origins, 'node_ids': data.arrays['node_ids'],
                  'y_true': data.arrays['targets'][idx], 'target_event': event, 'rule_trigger': trigger,
                  'target_timestamps_ns': data.arrays['timestamps_ns'][idx],
                  'origin_cutoff_ns': data.arrays['timestamps_ns'][origins] + 900_000_000_000}
        checks = {k + '_exact': np.array_equal(v, saved[k]) for k, v in arrays.items()}
        if reference_arrays is not None:
            checks['three_seed_keys_truth_masks_exact'] = all(np.array_equal(v, reference_arrays[k]) for k, v in arrays.items())
        reference_arrays = arrays
        assert all(checks.values()) and saved['y_pred'].shape == (15816, 4, 10)
        assert all(np.isfinite(saved[k]).all() for k in ('y_true', 'y_pred'))
        archived_metrics = metrics(saved['y_true'], saved['y_pred'], event, trigger)
        formal_metrics = read(folder / 'metrics.json')['splits']['test']
        scalar_diffs = {k: abs(archived_metrics[k] - formal_metrics[k]) for k in ('mae', 'rmse', 'event_mae', 'stable_mae')}
        assert max(scalar_diffs.values()) < 1e-7
        for name, cell in archived_metrics['four_cells'].items():
            original = formal_metrics['four_cells'][name]
            assert cell['n'] == original['n']
            assert cell['mae'] is None or abs(cell['mae'] - original['mae']) < 1e-7
        experiment.runner.setup(seed, 'cpu', cfg.get('threads', 2))
        model = experiment.build_model('mrg_full', data.arrays['graphs'])
        model.load_state_dict(payload['model'], strict=True)
        model.eval()
        assert experiment.count_parameters(model) == 32714
        y, baseline, keys = experiment.runner.predict(model, data, 'test', cfg, 'cpu')
        baseline_diff = float(np.abs(baseline - saved['y_pred']).max())
        assert np.array_equal(y, saved['y_true']) and np.array_equal(keys, origins) and baseline_diff <= TOL
        learned = [getattr(model, f'relation_weights_gcn{i}').detach().clone() for i in (1, 2)]
        beta = [v.softmax(0).tolist() for v in learned]
        runs = {'learned': metrics(y, baseline, event, trigger)}
        np.savez_compressed(out / f'seed-{seed}-learned.npz', y_pred=baseline)
        print(f'PASS JPL seed-{seed} baseline max_diff={baseline_diff:.3g}', flush=True)
        for name, choices in INTERVENTIONS.items():
            variant = copy.deepcopy(model)
            with torch.no_grad():
                for i, choice in enumerate(choices):
                    if choice is None:
                        continue
                    replacement = learned[1-i] if isinstance(choice, str) else torch.tensor(choice, dtype=learned[i].dtype)
                    getattr(variant, f'relation_weights_gcn{i+1}').copy_(replacement)
            for key, value in variant.state_dict().items():
                if key not in ('relation_weights_gcn1', 'relation_weights_gcn2'):
                    assert torch.equal(value, model.state_dict()[key])
            actual, pred, current_keys = experiment.runner.predict(variant, data, 'test', cfg, 'cpu')
            assert np.array_equal(actual, y) and np.array_equal(current_keys, origins)
            result = metrics(y, pred, event, trigger)
            result['delta_mae_vs_learned'] = result['mae'] - runs['learned']['mae']
            result['relative_mae_change_pct'] = 100 * result['delta_mae_vs_learned'] / runs['learned']['mae']
            result['beta_used'] = [getattr(variant, f'relation_weights_gcn{i}').softmax(0).tolist() for i in (1, 2)]
            runs[name] = result
            np.savez_compressed(out / f'seed-{seed}-{name}.npz', y_pred=pred)
            print(f'JPL seed-{seed} {name}: MAE={result["mae"]:.9f}, delta={result["delta_mae_vs_learned"]:+.9f}', flush=True)
        # Function-preserving reparameterization: beta'=1/3; W'_r=3*beta_r*W_r.
        equivalent = copy.deepcopy(model)
        with torch.no_grad():
            for i in (1, 2):
                for r, linear in enumerate(getattr(equivalent, f'gcn{i}').W_r):
                    assert linear.bias is None
                    linear.weight.mul_(3 * learned[i-1].softmax(0)[r])
                getattr(equivalent, f'relation_weights_gcn{i}').zero_()
        _, equivalent_pred, equivalent_keys = experiment.runner.predict(equivalent, data, 'test', cfg, 'cpu')
        equivalent_diff = float(np.abs(equivalent_pred-baseline).max())
        assert equivalent_diff <= TOL and np.array_equal(equivalent_keys, origins)
        np.savez_compressed(out / f'seed-{seed}-equal-reparameterized.npz', y_pred=equivalent_pred)
        after = {str(p.relative_to(bundle)): sha(p) for p in tracked}
        assert before == after
        results.append({'seed': seed, 'archived_l3': archived_metrics, 'learned_beta': beta, 'runs': runs,
                        'baseline_max_prediction_abs_diff': baseline_diff,
                        'equal_reparameterized_max_prediction_abs_diff': equivalent_diff,
                        'source_files_unchanged': True, 'checks': checks})
        provenance.append({'seed': seed, 'source_hashes': before, 'contract': payload['contract'],
                           'best_epoch': int(payload['epoch']), 'archived_metric_diffs': scalar_diffs})
        write(out / f'seed-{seed}-audit.json', results[-1])
    aggregation = {}
    for name in ('learned', *INTERVENTIONS):
        aggregation[name] = {}
        for key in ('mae', 'event_mae', 'stable_mae'):
            values = np.array([r['runs'][name][key] for r in results])
            aggregation[name][key] = {'mean': float(values.mean()), 'sample_sd': float(values.std(ddof=1))}
        aggregation[name]['seed_delta_mae'] = [r['runs'][name]['mae']-r['runs']['learned']['mae'] for r in results]
    cells = {}
    for name in results[0]['archived_l3']['four_cells']:
        group = [r['archived_l3']['four_cells'][name] for r in results]
        assert len({c['n'] for c in group}) == 1
        cells[name] = {'n': group[0]['n'], 'sample_share': group[0]['sample_share']}
        for key in ('mae', 'error_share'):
            vals = [c[key] for c in group]
            cells[name][key] = None if vals[0] is None else {'mean': float(np.mean(vals)), 'sample_sd': float(np.std(vals, ddof=1))}
    final = {'status': 'PASS', 'date': '2026-10-14', 'scope': 'JPL L1/L3 post-hoc frozen-test inference audit',
             'retraining_performed': False, 'l2_replicated': False, 'statistical_confirmation': False,
             'bundle': str(bundle), 'original_manifest_verified_files': len(original_manifest),
             'dataset_sha256': data.digest, 'source_digest': experiment.runner.code_digest(),
             'script_sha256': sha(__file__), 'prediction_atol': TOL,
             'environment': {'python': sys.version, 'torch': str(torch.__version__), 'platform': platform.platform(), 'device': 'cpu'},
             'single_relation_weight_semantics': 'logits [10,0,0] softmax dominant=0.9999092, not exactly 1',
             'source_provenance': provenance, 'aggregation': aggregation, 'l3_cells': cells, 'seeds': results}
    write(out / 'audit.json', final)
    write(out / 'output-manifest.json', {p.name: sha(p) for p in out.iterdir() if p.is_file()})
    print(f'PASS JPL L1/L3, 3 seeds, 632640 keys/run; outputs: {out}', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, default=DEFAULT_BUNDLE)
    parser.add_argument('--out', type=Path, default=REPO / 'outputs/analysis/JPL-MDP-20261014')
    args = parser.parse_args()
    run(args.bundle.resolve(), args.out.resolve())
