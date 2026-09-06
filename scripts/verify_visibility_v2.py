"""Independent vector-count verification of frozen eventtime-v1 data.

Does not import the v2 builder or modify frozen data. Writes a separate,
non-overwriting verification directory; no raw personal identifiers exported.
"""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FROZEN = ROOT/'outputs/visibility/SG-DATA-006-eventtime-v1'
DEST = ROOT/'outputs/visibility/SG-DATA-006-eventtime-v1-verification'


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1048576), b''):
            h.update(b)
    return h.hexdigest()


if __name__ == '__main__':
    if DEST.exists():
        raise FileExistsError('Verification exists; do not overwrite evidence')
    audit = json.loads((FROZEN/'audit.json').read_text())
    protocol = json.loads((FROZEN/'protocol.json').read_text())
    manifest = json.loads((FROZEN/'manifest.json').read_text())
    for name, hash_value in manifest['files'].items():
        assert sha(FROZEN/name) == hash_value
    for path, hash_value in manifest['source_hashes'].items():
        assert sha(Path(path)) == hash_value
    raw_path = Path(protocol['source'])
    raw = pd.read_csv(raw_path)
    for column in ('connectionTime', 'disconnectTime'):
        raw[column] = pd.to_datetime(raw[column], utc=True)
    z = np.load(FROZEN/'dataset.npz', allow_pickle=False)
    g = z['timestamps_ns']; end = g + 900_000_000_000
    nodes = z['node_ids'].tolist()
    x = z['features']; y = z['targets']; maturity = z['label_available_at_ns']
    for n, node in enumerate(nodes):
        rows = raw[raw.spaceID == node]
        c = np.sort(rows.connectionTime.astype('int64').to_numpy())
        d = np.sort(rows.disconnectTime.astype('int64').to_numpy())
        # Independent searchsorted counts, unlike production bincount/cumsum.
        c0 = np.searchsorted(c, g, side='left'); c1 = np.searchsorted(c, end, side='left')
        d0 = np.searchsorted(d, g, side='left'); d1 = np.searchsorted(d, end, side='left')
        np.testing.assert_array_equal(x[:, n, 0], c1-c0)
        np.testing.assert_array_equal(x[:, n, 1], d1-d0)
        np.testing.assert_array_equal(x[:, n, 2], c1-d1)
        np.testing.assert_allclose(y[:, n].sum(), rows.kWhDelivered.sum(), rtol=1e-12, atol=1e-9)
    stats = {}; legacy_overlap = {}
    for phase, (a, b) in audit['split_bounds_exclusive'].items():
        o = z[phase+'_origins']
        keys_y = o[:, None]+np.arange(1, 5)
        assert np.all(o-95 >= a) and np.all(keys_y < b)
        cutoff = g[b] if b < len(g) else end[-1]
        assert np.all(maturity[keys_y] < cutoff)
        stats[phase] = {'start_utc': str(pd.Timestamp(g[a])),
                        'end_utc_exclusive': str(pd.Timestamp(cutoff)),
                        'origins': len(o), 'forecast_keys': int(len(o)*4*len(nodes)),
                        'target_event_fraction': float(z['target_event'][keys_y].mean()),
                        'rule_trigger_fraction': float(z['rule_trigger'][o].mean()),
                        'immature_target_origins_removed': (b-a-99)-len(o)}
    old = np.load(ROOT/protocol['legacy_tensor'], allow_pickle=False)
    old_segments = {'train': (0, 83198), 'validation': (83198, 101005), 'test': (101005, len(g))}
    for phase, (a,b) in old_segments.items():
        o = old[phase+'_origins']
        legacy_overlap[phase] = {'history_cross_segment': int((o-95<a).sum()),
                                 'targets_cross_segment': int((o+4>=b).sum())}
    fit = audit['fit_prefix_end_exclusive']
    assert np.all(maturity[:fit] < g[audit['raw_train_end_exclusive']])
    train_y = y[:fit]
    np.testing.assert_allclose(z['target_mean'], train_y.mean(0), rtol=1e-12, atol=1e-12)
    # Full inventory of available local exports; no request to external API.
    inventory = []
    for p in sorted(raw_path.parent.glob('acn_caltech_*.csv')):
        f = pd.read_csv(p, usecols=['connectionTime', 'has_time_series'])
        inventory.append({'file': p.name, 'rows': len(f),
                          'time_series_flags': int(f.has_time_series.fillna(False).sum()), 'sha256': sha(p)})
    jsonl_inventory = []
    for p in sorted(raw_path.parent.glob('acn_caltech_*_checkpoint.jsonl')):
        count = current = pilot = ingestion = 0
        zones = set()
        for line in p.open():
            row = json.loads(line); count += 1
            current += bool(row.get('chargingCurrent'))
            pilot += bool(row.get('pilotSignal'))
            ingestion += any(k in row for k in ['receivedAt', 'ingestedAt', 'availableAt'])
            zones.add(row.get('timezone'))
        jsonl_inventory.append({'file': p.name, 'rows': count, 'nonempty_current': current,
                                 'nonempty_pilot': pilot, 'ingestion_timestamp_rows': ingestion,
                                 'timezones': sorted(zones), 'sha256': sha(p)})
    assert sum(f['rows'] for f in jsonl_inventory) == len(raw)
    raw_manifest = json.loads((raw_path.parent/'acn_sessions_manifest.json').read_text())
    tests = subprocess.run([sys.executable, '-m', 'pytest', 'tests/test_visibility_v2.py',
                            'tests/test_data_and_keys.py', 'tests/test_relations_and_evaluation.py',
                            'tests/test_models.py', '-p', 'no:cacheprovider', '--tb=short'],
                           cwd=ROOT, capture_output=True, text=True)
    assert tests.returncode == 0, tests.stdout+tests.stderr
    result = {'status': 'passed', 'checks': ['independent_all_grid_event_counts',
              'per_node_energy_conservation', 'all_split_window_boundaries',
              'all_forecast_label_maturity', 'all_training_fit_label_maturity',
              'training_target_mean_recomputed', 'frozen_source_and_output_hashes'],
              'checked_node_time_rows': int(len(g)*len(nodes)), 'splits': stats,
              'legacy_boundary_counts': legacy_overlap,
              'source_inventory': inventory, 'jsonl_inventory': jsonl_inventory,
              'upstream_manifest_warning': {'declared_rows': raw_manifest.get('row_count'),
                  'actual_rows': len(raw), 'declared_site': raw_manifest.get('site'),
                  'action': 'stale smoke manifest excluded as authority; upstream kept read-only'},
              'scope': 'event-time assumption only; no measured ingestion delay; no training accuracy tested',
              'source_code_sha256': {str(p.relative_to(ROOT)): sha(p) for p in (ROOT/'src').rglob('*.py')}}
    DEST.mkdir(parents=True)
    (DEST/'verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    (DEST/'tests.txt').write_text(tests.stdout+tests.stderr)
    (DEST/'manifest.json').write_text(json.dumps({p.name: sha(p) for p in DEST.iterdir() if p.is_file()}, indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['status','checked_node_time_rows','splits','legacy_boundary_counts']}, indent=2))
    print(tests.stdout)
