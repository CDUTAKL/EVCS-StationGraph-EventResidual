#!/usr/bin/env python3
"""Independent arithmetic audit of saved JPL MDP outputs; no torch or training."""
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/analysis/JPL-MDP-20261014'
BUNDLE = ROOT / 'outputs/evidence/checkpoint-replay-20261012/components/sg028'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    audit = json.loads((OUT / 'audit.json').read_text())
    manifest = json.loads((OUT / 'output-manifest.json').read_text())
    assert all(sha(OUT / rel) == digest for rel, digest in manifest.items())
    gaps, closures = [], []
    pairs = []
    for result in audit['seeds']:
        seed = result['seed']
        source = BUNDLE / f'results/formal/mrg_full/seed-{seed}/predictions_test.npz'
        with np.load(source, allow_pickle=False) as archive:
            y, event, trigger = archive['y_true'], archive['target_event'], archive['rule_trigger']
            original_prediction = archive['y_pred']
        assert y.shape == (15816, 4, 10)
        for relative, digest in audit['source_provenance'][seed-2024]['source_hashes'].items():
            assert sha(BUNDLE / relative) == digest
        with np.load(OUT / f'seed-{seed}-learned.npz', allow_pickle=False) as pred:
            learned = pred['y_pred']
        assert np.max(np.abs(learned-original_prediction)) <= audit['prediction_atol']
        for name, reported in result['runs'].items():
            with np.load(OUT / f'seed-{seed}-{name}.npz', allow_pickle=False) as pred:
                error = np.abs(pred['y_pred'].astype('float64') - y.astype('float64'))
            values = {'mae': float(np.sum(error)/error.size),
                      'event_mae': float(np.sum(error[event])/event.sum()),
                      'stable_mae': float(np.sum(error[~event])/(~event).sum()),
                      'by_horizon_mae': error.sum(axis=(0, 2))/(error.shape[0]*error.shape[2]),
                      'by_node_mae': error.sum(axis=(0, 1))/(error.shape[0]*error.shape[1])}
            gaps.extend(float(np.max(np.abs(np.asarray(value)-np.asarray(reported[key])))) for key, value in values.items())
            total = 0.
            for cell_name, cell in reported['four_cells'].items():
                t, r = int(cell_name.split('_')[1]), int(cell_name.split('_')[3])
                mask = (event == t) & (trigger == r)
                assert int(mask.sum()) == cell['n']
                subtotal = float(np.sum(error[mask]))
                total += subtotal
                gaps.append(abs(subtotal/cell['n']-cell['mae']) if cell['n'] else 0.)
            closures.append(abs(total/error.size-values['mae']))
            pairs.append({'seed': seed, 'variant': name, 'n_keys': int(error.size)})
        with np.load(OUT / f'seed-{seed}-equal-reparameterized.npz', allow_pickle=False) as pred:
            gap = float(np.max(np.abs(pred['y_pred']-learned)))
        assert gap <= audit['prediction_atol']
        assert abs(gap-result['equal_reparameterized_max_prediction_abs_diff']) < 1e-12
    assert max(gaps) < 1e-12 and max(closures) < 1e-12
    assert len(pairs) == 24
    result = {'status': 'PASS', 'retraining_performed': False, 'audit_sha256': sha(OUT/'audit.json'),
              'output_manifest_verified_files': len(manifest), 'n_metric_variants': len(pairs),
              'n_reparameterization_pairs': 3, 'max_metric_abs_diff': max(gaps),
              'max_four_cell_closure_gap': max(closures), 'prediction_keys_per_variant': 632640,
              'verification_method': 'saved predictions independently summed; source/output hashes checked; no model re-execution',
              'pairs': pairs}
    destination = ROOT/'docs/thesis/revision-20261014-evidence/jpl-independent-verification.json'
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='pairs'}))


if __name__ == '__main__':
    main()
