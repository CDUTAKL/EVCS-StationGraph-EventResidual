"""Build and audit SG-DATA-006 without mutating legacy artifacts.

Run from project root: .venv/bin/python scripts/audit_visibility_v2.py
The destination must not exist. --verify checks frozen artifact hashes only.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import platform
from pathlib import Path
import subprocess
import sys

import numpy as np
import pandas as pd
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from evcs_station_graph.data import visibility_v2 as v
from evcs_station_graph.graphs.relations import build_relation_set
from evcs_station_graph.models.graph import StaticGraphForecast


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(1024*1024), b''):
            h.update(b)
    return h.hexdigest()


def dump(path, payload):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False)+'\n')


def execute(spec_path):
    spec = json.loads(spec_path.read_text())
    dest = ROOT/spec['output']
    if dest.exists():
        raise FileExistsError('Frozen output exists; use --verify or a new version, never overwrite')
    source = Path(spec['source'])
    paths = [source, ROOT/spec['legacy_tensor'], ROOT/spec['node_list'],
             ROOT/spec['legacy_split_manifest'], spec_path, Path(v.__file__), Path(__file__),
             ROOT/'tests/test_visibility_v2.py', ROOT/'src/evcs_station_graph/graphs/relations.py',
             ROOT/'src/evcs_station_graph/models/graph.py']
    before = {str(p): digest(p) for p in paths}
    frame = pd.read_csv(source)
    raw_count = len(frame)
    if frame.sessionID.duplicated().any():
        raise ValueError('Duplicate session ID')
    if frame.has_time_series.fillna(False).any():
        raise ValueError('Measurement availability changed; reconsider scheme A before B')
    for col in ('connectionTime', 'disconnectTime'):
        frame[col] = pd.to_datetime(frame[col], errors='raise', utc=True).dt.tz_localize(None)
    if frame[['connectionTime', 'disconnectTime', 'spaceID', 'kWhDelivered']].isna().any().any():
        raise ValueError('Missing essential raw field')
    if (frame.disconnectTime < frame.connectionTime).any() or (frame.kWhDelivered < 0).any():
        raise ValueError('Invalid raw chronology/energy')
    nodes = pd.read_csv(ROOT/spec['node_list']).node_id.astype(str).tolist()
    frame = frame[frame.spaceID.isin(nodes)].copy()
    if frame.siteID.nunique() != 1 or frame.groupby('spaceID').stationID.nunique().max() != 1:
        raise ValueError('Node/site mapping not one-to-one')
    if frame.groupby('stationID').spaceID.nunique().max() != 1:
        raise ValueError('EVSE aliases duplicated as nodes')
    legacy = np.load(ROOT/spec['legacy_tensor'], allow_pickle=False)
    if nodes != legacy['node_ids'].tolist():
        raise ValueError('Node order mismatch')
    grid = legacy['timestamps_ns']; T = len(grid)
    split = json.loads((ROOT/spec['legacy_split_manifest']).read_text())['split_boundaries']
    train_end = split['validation']['start_index']
    cal_end = split['test']['start_index']
    tune_end = (train_end+cal_end)//2
    bounds = {'train': (0, train_end), 'tuning': (train_end, tune_end),
              'calibration': (tune_end, cal_end), 'test': (cal_end, T)}
    x = v.event_features(frame, grid, nodes)
    y, maturity = v.proxy_targets(frame, grid, nodes)
    checks = {}
    np.testing.assert_allclose(y, legacy['targets'], rtol=2e-6, atol=2e-6)
    checks['proxy_reproduces_legacy_with_float32_tolerance'] = True
    fit_end = v.mature_prefix_end(maturity, grid, train_end)
    params = v.fit_preprocessing(x, y, fit_end)
    graphs = build_relation_set(x[:fit_end], y[:fit_end], v.FEATURE_NAMES, top_k=5).as_list()
    H, P = spec['history_steps'], spec['horizon_steps']
    origins = {s: v.safe_origins(grid, maturity, a, b, H, P) for s, (a, b) in bounds.items()}
    origins['train'] = origins['train'][origins['train']+P < fit_end]
    for s, o in origins.items():
        if not len(o):
            raise ValueError(f'No usable origins in {s}')
        a, b = bounds[s]
        assert o.min()-H+1 >= a and o.max()+P < b
    checks['all_input_target_windows_within_segments'] = True
    scores = v.rule_scores(x, params['rule_std'])
    tune_scores = scores[origins['tuning']]
    thresholds = np.array([np.quantile(c[c>0], .95) if np.any(c>0) else np.inf for c in tune_scores.T])
    trigger = v.apply_rule(scores, thresholds, 2)
    delta = np.abs(np.diff(y, axis=0, prepend=y[[0]]))
    labels = (x[:, :, 0] > 0) | (x[:, :, 1] > 0) | (delta > params['label_jump_threshold'])

    # Full-period upstream derived-feature exposure: diagnostic, not new input.
    risk = {}
    for s in ('train', 'validation', 'test'):
        oo = legacy[s+'_origins']
        exposed = np.zeros((len(oo), len(nodes)), dtype=bool)
        for offset in range(H):
            exposed |= maturity[oo-offset] >= (grid[oo]+v.STEP)[:, None]
        risk[s] = {'origins': len(oo), 'origin_node_pairs': int(exposed.size),
                   'exposed_origin_node_pairs': int(exposed.sum()),
                   'exposed_pair_fraction': float(exposed.mean()),
                   'origins_with_any_exposed_node_fraction': float(exposed.any(axis=1).mean())}

    # Fitted preprocessing/graphs cannot be affected by held-out target changes.
    changed_y = y.copy(); changed_x = x.copy()
    changed_y[train_end:] += 12345.; changed_x[train_end:] += 12345.
    for k, a in params.items():
        np.testing.assert_array_equal(a, v.fit_preprocessing(changed_x, changed_y, fit_end)[k])
    altered_graphs = build_relation_set(changed_x[:fit_end], changed_y[:fit_end], v.FEATURE_NAMES, top_k=5).as_list()
    for a, b in zip(graphs, altered_graphs):
        np.testing.assert_array_equal(a, b)
    checks['heldout_perturbation_does_not_change_fit_or_graphs'] = True

    # Fixed random untrained model: tests invariance through real architecture,
    # not forecasting quality and not an old seven-channel checkpoint.
    torch.manual_seed(20260905); torch.set_num_threads(2)
    model = StaticGraphForecast(7, P, len(nodes), graphs, hidden_dim=32, levels=6, dropout=.1).eval()
    cases = []
    for s in ('calibration', 'test'):
        sampled = np.unique(origins[s][np.linspace(0, len(origins[s])-1, 8, dtype=int)])
        for origin in sampled:
            cutoff = pd.Timestamp(grid[origin]+v.STEP)
            prefix_grid = grid[:origin+1]
            censored = frame[frame.connectionTime < cutoff].copy()
            censored.loc[censored.disconnectTime >= cutoff, 'disconnectTime'] = pd.NaT
            censored = censored.drop(columns=['kWhDelivered', 'doneChargingTime'])
            replay = v.event_features(censored, prefix_grid, nodes)
            np.testing.assert_array_equal(replay, x[:origin+1])
            altered = frame.copy()
            altered.loc[altered.disconnectTime >= cutoff, 'disconnectTime'] += pd.Timedelta(days=3650)
            altered['kWhDelivered'] = altered.kWhDelivered*1000 + 999
            mutated = v.event_features(altered, prefix_grid, nodes)
            np.testing.assert_array_equal(mutated, replay)
            replay_trigger = v.apply_rule(v.rule_scores(replay, params['rule_std']), thresholds, 2)
            np.testing.assert_array_equal(replay_trigger, trigger[:origin+1])
            def predict(features):
                z = (features[-H:]-params['feature_mean'])/params['feature_std']
                with torch.no_grad():
                    return model(torch.tensor(z[None], dtype=torch.float32)).prediction.numpy()
            np.testing.assert_array_equal(predict(mutated), predict(replay))
            cases.append({'split': s, 'origin': int(origin), 'cutoff_utc': str(cutoff), 'passed': True})
    checks['real_data_prefix_future_mutation_rule_model_invariance'] = True

    # Positive control: same mutation MUST alter legacy proxy history somewhere.
    audit_origin = int(legacy['test_origins'][0])
    occupied = np.flatnonzero(np.any(maturity[legacy['test_origins']] >= (grid[legacy['test_origins']]+v.STEP)[:, None], axis=1))
    if len(occupied):
        audit_origin = int(legacy['test_origins'][occupied[0]])
    cutoff = pd.Timestamp(grid[audit_origin]+v.STEP)
    altered = frame.copy()
    altered.loc[altered.disconnectTime >= cutoff, 'kWhDelivered'] *= 2
    old_changed, _ = v.proxy_targets(altered, grid[:audit_origin+1], nodes)
    positive_delta = float(np.max(np.abs(old_changed[-H:]-y[audit_origin-H+1:audit_origin+1])))
    assert positive_delta > 0, 'Positive leakage control failed'
    checks['legacy_positive_control_detects_leakage'] = True

    # All checks precede output creation. Unit tests must also pass.
    tests = subprocess.run([sys.executable, '-m', 'pytest', 'tests/test_visibility_v2.py',
                            '-p', 'no:cacheprovider', '--tb=short'], cwd=ROOT, capture_output=True, text=True)
    if tests.returncode:
        raise RuntimeError(tests.stdout+tests.stderr)
    for p, h in before.items():
        assert digest(p) == h, f'Source changed during audit: {p}'
    dest.mkdir(parents=True)
    np.savez_compressed(dest/'dataset.npz', timestamps_ns=grid, node_ids=np.array(nodes),
                        feature_names=np.array(v.FEATURE_NAMES), features=x, targets=y,
                        label_available_at_ns=maturity, target_event=labels, rule_trigger=trigger,
                        **{f'{k}_origins': o for k, o in origins.items()}, **params,
                        rule_thresholds=thresholds, graphs=np.stack(graphs),
                        schema=np.array('eventtime-v1-not-legacy-TensorBundle'))
    zero = frame.disconnectTime == frame.connectionTime
    summary = {'protocol': spec['protocol_id'], 'status': 'frozen_event_time_data_protocol',
               'training_adapter_status': 'not_integrated_do_not_use_legacy_rules',
               'raw_sessions': raw_count, 'selected_sessions': len(frame), 'nodes': nodes,
               'zero_duration_sessions': int(zero.sum()), 'zero_duration_energy': float(frame.loc[zero, 'kWhDelivered'].sum()),
               'fit_prefix_end_exclusive': fit_end, 'raw_train_end_exclusive': train_end,
               'purged_fit_tail_steps': train_end-fit_end, 'split_bounds_exclusive': bounds,
               'origin_counts': {s: len(o) for s,o in origins.items()}, 'legacy_input_exposure': risk,
               'legacy_positive_control_max_difference': positive_delta, 'checks': checks,
               'invariance_cases': cases, 'deployment_validated': False,
               'assumptions': ['no ingestion timestamps; zero delay event-time replay only',
                               'fixed historical node inventory, not train-only reselection',
                               'old test already inspected; no new independent confirmation'],
               'source_hashes': before,
               'environment': {'python': sys.version, 'platform': platform.platform(),
                               'numpy': np.__version__, 'pandas': pd.__version__, 'torch': torch.__version__},
               'git_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()}
    dump(dest/'audit.json', summary)
    dump(dest/'protocol.json', spec)
    (dest/'tests.txt').write_text(tests.stdout+tests.stderr)
    hashes = {p.name: digest(p) for p in dest.iterdir() if p.is_file()}
    dump(dest/'manifest.json', {'files': hashes, 'source_hashes': before})
    print(json.dumps({k: summary[k] for k in ['status', 'origin_counts', 'fit_prefix_end_exclusive', 'legacy_input_exposure', 'checks']}, indent=2))
    print(dest)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default='configs/data/SG-DATA-006-eventtime-v1.json')
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    spec_path = ROOT/args.config
    if args.verify:
        out = ROOT/json.loads(spec_path.read_text())['output']
        m = json.loads((out/'manifest.json').read_text())
        for name, expected in m['files'].items():
            assert digest(out/name) == expected, name
        for path, expected in m['source_hashes'].items():
            assert digest(path) == expected, path
        print('PASS: all frozen output and source hashes match')
    else:
        execute(spec_path)
