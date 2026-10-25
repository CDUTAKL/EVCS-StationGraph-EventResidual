"""Independently check recovered CUDA predictions, selection evidence and hashes."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/analysis/AdaptiveGraph-CUDA-20261015'
PACKAGE = ROOT / 'outputs/evidence/AdaptiveGraph-CUDA-replay-20261014'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

manifest = json.loads((OUT / 'output-manifest.json').read_text())
assert all(sha(OUT / name) == digest for name, digest in manifest.items())
inputs = json.loads((PACKAGE / 'MANIFEST.json').read_text())
assert all(sha(PACKAGE / name) == digest for name, digest in inputs.items())
status = json.loads((OUT / 'status.json').read_text())
assert status['prediction_atol'] == 5e-6
assert status['retraining_performed'] is False
rows = []
for run in status['runs']:
    seed = run['seed']
    frame = pd.read_csv(PACKAGE / f'legacy/results/SG-EXP-004/seed-{seed}/predictions.csv.gz')
    frame = frame.sort_values(['origin_index', 'horizon', 'node_index'])
    assert not frame.duplicated(['split', 'origin_index', 'horizon', 'node_id']).any()
    pred = np.load(OUT / f'seed-{seed}-predictions.npz', allow_pickle=False)
    actual = {}
    mae = {}
    truth = frame.y_true.to_numpy()
    for name in ('native_cpu', 'native_cuda', 'cpu_with_cuda_adjacency'):
        values = pred[name].ravel()
        assert len(values) == len(frame) and np.isfinite(values).all()
        actual[name] = float(np.max(np.abs(values - frame.y_pred.to_numpy())))
        assert abs(actual[name] - run['max_prediction_abs_differences'][name]) < 1e-12
        mae[name] = float(np.mean(np.abs(values - truth)))
    cpu = np.load(OUT / f'seed-{seed}-cpu-adjacency.npz', allow_pickle=False)
    cuda = np.load(OUT / f'seed-{seed}-cuda-adjacency.npz', allow_pickle=False)
    changed = np.flatnonzero(np.any(np.sort(cpu['topk_indices'], axis=1) != np.sort(cuda['topk_indices'], axis=1), axis=1)).tolist()
    assert changed == run['changed_neighbor_rows']
    only_tied = set(changed).issubset(set(cpu['ambiguous_rows'].tolist()))
    confirmed = actual['native_cuda'] <= 5e-6 and actual['cpu_with_cuda_adjacency'] <= 5e-6 and actual['native_cpu'] > 5e-6 and bool(changed) and only_tied
    assert confirmed == run['tie_backend_explanation_confirmed']
    rows.append({'seed': seed, 'prediction_keys': len(frame), 'max_abs_difference': actual,
                 'global_mae': mae, 'archived_global_mae': float(np.mean(np.abs(frame.y_pred.to_numpy() - truth))),
                 'changed_neighbor_rows_zero_based': changed, 'tie_explanation_confirmed': confirmed})
audit = {'status': 'PASS', 'remote_manifest_files_verified': len(manifest), 'local_package_files_verified': len(inputs),
         'remote_uri': 'ssh://root@connect.westc.seetacloud.com:24376/root/autodl-tmp/AdaptiveGraph-CUDA-replay-20261014/replay-cuda-20261015',
         'runs': rows, 'retraining_performed': False, 'environment': status['environment']}
(OUT / 'independent-verification.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(audit, ensure_ascii=False, indent=2))
