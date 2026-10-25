#!/usr/bin/env python3
"""Post-hoc JPL interval evaluation from frozen predictions; no model fitting.

Fix alpha=.1 and two previously used calibration paths before calculating any
test coverage. Event labels are evaluation-only. Symmetric intervals are not
clipped at zero. This is a viewed-period sensitivity analysis, not a coverage
guarantee or a new independently held-out confirmation.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = Path('/Users/xushuyuan/Documents/Codex/2026-10-05/sg-exp-028-jpl/outputs/recovered/SG-EXP-028/extracted/results/formal/mrg_full')


def digest(p):
    with p.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def write(p, value):
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def quantile(values):
    values = np.asarray(values).ravel()
    n = values.size
    k = int(np.ceil((n + 1) * .9))
    if n == 0 or k > n:
        raise ValueError('Infinite half-width required; do not silently interpolate')
    return float(np.partition(values, k - 1)[k - 1]), {'n': n, 'rank': k}


def evaluate(y, pred, q, event):
    error = np.abs(y - pred)
    covered = error <= q
    width = np.broadcast_to(q * 2, y.shape)
    score = width + 20 * np.maximum(error - q, 0)
    masks = {'overall': np.ones(y.shape, dtype=bool), 'event': event,
             'stable': ~event, 'zero': y == 0, 'nonzero': y != 0}
    return {name: {'n': int(mask.sum()), 'coverage': float(covered[mask].mean()),
                   'mean_width': float(width[mask].mean()),
                   'interval_score': float(score[mask].mean())}
            for name, mask in masks.items()}


def run(source, out):
    if out.exists():
        raise ValueError('Use a new output directory')
    out.mkdir(parents=True)
    write(out / 'analysis-plan.json', {'alpha': .1, 'seeds': [2024, 2025, 2026],
          'paths': ['node', 'behavior'], 'calibration': 'order ceil((n+1)*.9)',
          'intervals': 'symmetric, unclipped', 'target_event': 'evaluation only',
          'scope': 'post-hoc, previously viewed fixed JPL test period; no retraining'})
    records, inputs, reference = [], [], {}
    for seed in (2024, 2025, 2026):
        arrays = {}
        for split in ('calibration', 'test'):
            p = source / f'seed-{seed}' / f'predictions_{split}.npz'
            inputs.append({'path': str(p), 'sha256': digest(p)})
            with np.load(p, allow_pickle=False) as a:
                arrays[split] = {k: a[k] for k in a.files}
            a = arrays[split]
            assert np.isfinite(a['y_pred']).all() and np.isfinite(a['y_true']).all()
            assert a['y_true'].shape == a['y_pred'].shape == a['target_event'].shape == a['rule_trigger'].shape
            assert np.all(np.diff(a['origins']) > 0)
            for k in ('origins', 'node_ids', 'y_true', 'target_event', 'rule_trigger', 'target_timestamps_ns', 'origin_cutoff_ns'):
                if split in reference:
                    assert np.array_equal(a[k], reference[split][k])
            if split not in reference:
                reference[split] = a
        cal, test = arrays['calibration'], arrays['test']
        assert not np.intersect1d(cal['origins'], test['origins']).size
        assert not np.intersect1d(cal['target_timestamps_ns'], test['target_timestamps_ns']).size
        assert cal['target_timestamps_ns'].max() < test['target_timestamps_ns'].min()
        assert test['y_true'].size == 632640 and cal['y_true'].size == 313120
        residual = np.abs(cal['y_true'] - cal['y_pred'])
        ranks, qnode, qstable = {}, [], []
        for j in range(10):
            q, rank = quantile(residual[:, :, j]); qnode.append(q); ranks[f'node-{j}'] = rank
            q, rank = quantile(residual[:, :, j][~cal['rule_trigger'][:, :, j]])
            qstable.append(q); ranks[f'nontrigger-node-{j}'] = rank
        qtrigger, ranks['trigger-pooled'] = quantile(residual[cal['rule_trigger']])
        node = np.broadcast_to(np.asarray(qnode)[None, None, :], test['y_true'].shape)
        behavior = np.where(test['rule_trigger'], qtrigger, np.asarray(qstable)[None, None, :])
        records.append({'seed': seed, 'calibration_keys': residual.size, 'test_keys': test['y_true'].size,
                        'ranks': ranks, 'node_halfwidth': qnode, 'nontrigger_halfwidth': qstable,
                        'trigger_halfwidth': qtrigger,
                        'paths': {name: evaluate(test['y_true'], test['y_pred'], q, test['target_event'])
                                  for name, q in [('node', node), ('behavior', behavior)]}})
    summary = {}
    for path in ('node', 'behavior'):
        summary[path] = {}
        for group in ('overall', 'event', 'stable', 'zero', 'nonzero'):
            summary[path][group] = {'n': records[0]['paths'][path][group]['n']}
            for metric in ('coverage', 'mean_width', 'interval_score'):
                vals = [r['paths'][path][group][metric] for r in records]
                summary[path][group][metric] = {'mean': float(np.mean(vals)), 'sample_sd': float(np.std(vals, ddof=1))}
    write(out / 'audit.json', {'status': 'PASS', 'script_sha256': digest(Path(__file__)),
                              'alpha': .1, 'source': str(source), 'inputs': inputs,
                              'runs': records, 'summary': summary,
                              'scope': 'post-hoc fixed-period evaluation; no parameter/threshold tuning on test'})
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--source', type=Path, default=DEFAULT)
    ap.add_argument('--out', type=Path, default=ROOT / 'outputs/analysis/JPL-calibration-20261015')
    args = ap.parse_args(); run(args.source, args.out)
