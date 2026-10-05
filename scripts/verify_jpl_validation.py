"""独立核验JPL冻结资产；使用searchsorted计数，不调用构建器或训练模型。"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_ASSETS = {'dataset.npz', 'audit.json', 'protocol.json', 'node_selection.json', 'node_crosswalk.json'}
REQUIRED_SOURCES = {
    'data/external/JPL-20261005/sessions.jsonl',
    'outputs/analysis/JPL-full-census-20261005/acquisition.json',
    'configs/data/SG-DATA-007-jpl-eventtime-v1.json',
    'configs/experiments/SG-EXP-028-jpl-independent-site.json',
    'scripts/prepare_jpl_validation.py',
    'src/evcs_station_graph/data/visibility_v2.py',
    'src/evcs_station_graph/graphs/relations.py'}


def digest(path):
    """计算文件摘要用于源和产物一致性检查。"""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_manifest(frozen, manifest):
    """要求完整的已知资产/来源集合，拒绝绝对路径、越界路径与空清单。"""
    if set(manifest.get('files', {})) != REQUIRED_ASSETS or set(manifest.get('sources', {})) != REQUIRED_SOURCES:
        raise ValueError('Required manifest entries missing or unexpected')
    for name, expected in manifest['files'].items():
        path = (frozen / name).resolve()
        if Path(name).name != name or not path.is_relative_to(frozen.resolve()) or digest(path) != expected:
            raise ValueError('Frozen artifact hash changed: ' + name)
    for name, expected in manifest['sources'].items():
        path = (ROOT / name).resolve()
        if not path.is_relative_to(ROOT) or digest(path) != expected:
            raise ValueError('Source hash changed: ' + name)


def independent_labels(frame, grid, nodes):
    """以端点差分独立生成逐格代理目标，并独立重算最终标签成熟时间。"""
    result = np.zeros((len(grid), len(nodes)), dtype='float64')
    maturity = np.broadcast_to(grid[:, None] + 900_000_000_000 - 1, result.shape).copy()
    for n, node in enumerate(nodes):
        changes = np.zeros(len(grid) + 1, dtype='float64')
        for row in frame.loc[frame.spaceID == node].itertuples(index=False):
            c, d = row.connectionTime.value, row.disconnectTime.value
            if c == d:
                continue
            lo = int(np.searchsorted(grid, c, side='right') - 1)
            hi = int(np.searchsorted(grid, d, side='left'))
            if not 0 <= lo < hi <= len(grid):
                raise ValueError('Session outside frozen grid')
            allocation = float(row.kWhDelivered) / (hi - lo)
            changes[lo] += allocation
            changes[hi] -= allocation
            final_time = d
            if hasattr(row, 'doneChargingTime') and pd.notna(row.doneChargingTime):
                final_time = max(final_time, row.doneChargingTime.value)
            maturity[lo:hi, n] = np.maximum(maturity[lo:hi, n], final_time)
        result[:, n] = np.cumsum(changes[:-1])
    return result, maturity


def independent_origins(grid, maturity, bounds, fit):
    """根据协议边界和重算成熟矩阵生成所有合法原点，不信任审计中的原点。"""
    output = {}
    for split, (lo, hi) in bounds.items():
        origins = np.arange(lo + 95, hi - 4, dtype=np.int64)
        cutoff = grid[hi - 1] + 900_000_000_000
        good = np.all(maturity[origins[:, None] + np.arange(1, 5)] < cutoff, axis=(1, 2))
        if split == 'train':
            good &= origins + 4 < fit
        output[split] = origins[good]
    return output


def verify(frozen, destination):
    """独立核查全节点时间格、边界、成熟标签和训练统计，写另目录记录。"""
    if destination.exists():
        raise FileExistsError('Independent verification exists; do not overwrite')
    manifest = json.loads((frozen / 'manifest.json').read_text())
    check_manifest(frozen, manifest)
    audit = json.loads((frozen / 'audit.json').read_text())
    spec = json.loads((frozen / 'protocol.json').read_text())
    if spec != json.loads((ROOT / 'configs/data/SG-DATA-007-jpl-eventtime-v1.json').read_text()):
        raise ValueError('Frozen protocol does not match the registered configuration')
    acquisition = json.loads((ROOT / spec['source_manifest']).read_text())
    if acquisition['status'] != 'complete' or acquisition['snapshot_sha256'] != digest(ROOT / spec['source_snapshot']):
        raise ValueError('Source acquisition incomplete or mismatched')
    frame = pd.read_json(ROOT / spec['source_snapshot'], lines=True, dtype=False, convert_dates=False)
    for field in ('session_key', 'siteID', 'stationID', 'spaceID', 'timezone'):
        if frame[field].isna().any() or not frame[field].map(lambda item: isinstance(item, str) and bool(item.strip()) and item.strip().lower() not in ('none', 'null', 'nan')).all():
            raise ValueError('Invalid original identity metadata: ' + field)
    for name in ('connectionTime', 'disconnectTime', 'doneChargingTime'):
        frame[name] = pd.to_datetime(frame[name], format='mixed', utc=True)
    with np.load(frozen / 'dataset.npz', allow_pickle=False) as handle:
        z = {name: handle[name] for name in handle.files}
    grid = z['timestamps_ns']
    end = grid + 900_000_000_000
    if z['features'].shape != (len(grid), 10, 7) or z['targets'].shape != (len(grid), 10) or z['graphs'].shape != (3, 10, 10):
        raise ValueError('Frozen tensor shape is inconsistent with the registered ten-node contract')
    if tuple(z['feature_names']) != tuple(spec['feature_names']) or str(z['schema']) != 'jpl-eventtime-v1-not-legacy-TensorBundle':
        raise ValueError('Frozen input schema differs from JPL protocol')
    if not np.isfinite(z['features']).all() or not np.isfinite(z['targets']).all() or not np.isfinite(z['graphs']).all():
        raise ValueError('Nonfinite frozen tensors')
    if not np.all(np.diff(grid) == 900_000_000_000):
        raise ValueError('Grid is not consecutive 15min')
    if grid[0] != frame.connectionTime.min().floor('15min').value or end[-1] != frame.disconnectTime.max().ceil('15min').value:
        raise ValueError('Grid range differs from the frozen source contract')
    limits = [0, int(len(grid) * .70), int(len(grid) * .775), int(len(grid) * .85), len(grid)]
    bounds = dict(zip(('train', 'tuning', 'calibration', 'test'), zip(limits[:-1], limits[1:])))
    if audit['split_bounds'] != {s: list(b) for s, b in bounds.items()}:
        raise ValueError('Recorded split differs from independently reconstructed split')
    completion = pd.concat([frame.disconnectTime, frame.doneChargingTime], axis=1).max(axis=1)
    mature_rows = frame.loc[completion < pd.Timestamp(grid[bounds['train'][1]], tz='UTC')]
    policy = spec['node_selection']
    ranked = []
    for node, rows in mature_rows.groupby('spaceID', sort=True):
        if len(rows) >= policy['minimum_mature_sessions'] and rows.connectionTime.dt.strftime('%Y-%m').nunique() >= policy['minimum_active_months']:
            ranked.append((str(node), len(rows)))
    ranked.sort(key=lambda item: (-item[1], item[0]))
    expected_nodes = [node for node, _ in ranked[:policy['count']]]
    if z['node_ids'].tolist() != expected_nodes or len(expected_nodes) != 10:
        raise ValueError('Frozen nodes differ from independent train-only selection')
    independent_y, maturity = independent_labels(frame, grid, z['node_ids'])
    np.testing.assert_allclose(z['targets'], independent_y, atol=2e-10, rtol=1e-10)
    np.testing.assert_array_equal(z['label_available_at_ns'], maturity)
    train_cutoff = end[bounds['train'][1] - 1]
    bad = np.flatnonzero(np.any(maturity[:bounds['train'][1]] >= train_cutoff, axis=1))
    fit = int(bad[0]) if len(bad) else bounds['train'][1]
    if audit['fit_prefix_end_exclusive'] != fit:
        raise ValueError('Recorded train-fit prefix differs from independently reconstructed prefix')
    expected_origins = independent_origins(grid, maturity, bounds, fit)
    for n, node in enumerate(z['node_ids']):
        rows = frame.loc[frame.spaceID == node]
        arrival = np.sort(rows.connectionTime.astype('int64').to_numpy())
        departure = np.sort(rows.disconnectTime.astype('int64').to_numpy())
        c0 = np.searchsorted(arrival, grid, side='left')
        c1 = np.searchsorted(arrival, end, side='left')
        d0 = np.searchsorted(departure, grid, side='left')
        d1 = np.searchsorted(departure, end, side='left')
        np.testing.assert_array_equal(z['features'][:, n, 0], c1 - c0)
        np.testing.assert_array_equal(z['features'][:, n, 1], d1 - d0)
        np.testing.assert_array_equal(z['features'][:, n, 2], c1 - d1)
        energy = rows.loc[rows.disconnectTime > rows.connectionTime, 'kWhDelivered'].sum()
        np.testing.assert_allclose(z['targets'][:, n].sum(), energy, atol=1e-8, rtol=1e-10)
    segments = {}
    for split, (lo, hi) in bounds.items():
        oo = z[split + '_origins']
        np.testing.assert_array_equal(oo, expected_origins[split])
        if len(oo) == 0 or not np.all(np.diff(oo) > 0) or np.any(oo - 95 < lo) or np.any(oo + 4 >= hi):
            raise ValueError('Invalid or cross-segment origins: ' + split)
        keys = oo[:, None] + np.arange(1, 5)
        cutoff = end[hi - 1]
        if np.any(z['label_available_at_ns'][keys] >= cutoff):
            raise ValueError('Immature forecast labels: ' + split)
        segments[split] = dict(origins=len(oo), forecast_keys=int(len(oo) * 4 * len(z['node_ids'])),
                               cross_segment_windows=0, immature_target_keys=0)
    if np.any(z['label_available_at_ns'][:fit] >= train_cutoff):
        raise ValueError('Immature labels in train-fit prefix')
    xf = z['features'][:fit].astype('float64')
    yf = z['targets'][:fit].astype('float64')
    np.testing.assert_allclose(z['feature_mean'], xf.mean((0, 1)), rtol=1e-12, atol=1e-12)
    np.testing.assert_allclose(z['feature_std'], np.where(xf.std((0, 1)) < 1e-6, 1., xf.std((0, 1))), rtol=1e-12, atol=1e-12)
    np.testing.assert_allclose(z['target_mean'], yf.mean(0), rtol=1e-12, atol=1e-12)
    np.testing.assert_allclose(z['target_std'], np.where(yf.std(0) < 1e-6, 1., yf.std(0)), rtol=1e-12, atol=1e-12)
    local = pd.to_datetime(end, utc=True).tz_convert('America/Los_Angeles')
    hour = np.asarray(local.hour + local.minute / 60)
    day = np.asarray(local.dayofweek)
    expected_calendar = np.stack([np.sin(2 * np.pi * hour / 24), np.cos(2 * np.pi * hour / 24),
                                  np.sin(2 * np.pi * day / 7), np.cos(2 * np.pi * day / 7)], axis=-1).astype('float32')
    np.testing.assert_array_equal(z['features'][:, :, 3:], np.broadcast_to(expected_calendar[:, None, :], (len(grid), 10, 4)))
    active_delta = np.abs(np.diff(z['features'][:, :, 2].astype('float64'), axis=0, prepend=z['features'][[0], :, 2]))
    components = np.stack([z['features'][:, :, 0], z['features'][:, :, 1], active_delta], axis=-1).astype('float64')
    std = np.maximum(components[:fit].std(0), 1e-8)
    np.testing.assert_allclose(z['rule_std'], std, rtol=1e-12, atol=1e-12)
    scores = (components / std).sum(-1)
    tune_scores = scores[z['tuning_origins']]
    thresholds = np.array([np.quantile(c[c > 0], .95) if np.any(c > 0) else np.inf for c in tune_scores.T])
    np.testing.assert_array_equal(z['rule_thresholds'], thresholds)
    points = (scores >= thresholds) & (scores > 0)
    trigger = points.copy()
    trigger[1:] |= points[:-1]
    trigger[2:] |= points[:-2]
    np.testing.assert_array_equal(z['rule_trigger'], trigger)
    delta = np.abs(np.diff(z['targets'], axis=0, prepend=z['targets'][[0]]))
    positive = delta[:fit][delta[:fit] > 0]
    jump = np.quantile(positive, .9) if len(positive) else np.inf
    np.testing.assert_array_equal(z['label_jump_threshold'], jump)
    np.testing.assert_array_equal(z['target_event'], (z['features'][:, :, 0] > 0) | (z['features'][:, :, 1] > 0) | (delta > jump))
    result = dict(status='passed', protocol=spec['protocol_id'], dataset_sha256=digest(frozen / 'dataset.npz'),
                  checked_node_time_rows=int(len(grid) * len(z['node_ids'])), splits=segments,
                  checks=['all_grid_independent_event_counts', 'all_grid_independent_proxy_targets', 'independent_final_label_maturity',
                          'per_node_energy_conservation', 'independent_all_split_origins', 'all_split_window_boundaries',
                          'all_forecast_label_maturity', 'all_train_fit_label_maturity', 'all_scalers_recomputed', 'rule_and_event_recomputed', 'source_and_output_hashes'],
                  graph_verification_scope='train-only source and heldout-perturbation invariance in builder; graph formulas not independently reimplemented here',
                  model_predictions_created=False, training_performed=False,
                  script_sha256=digest(Path(__file__)), data_manifest_sha256=digest(frozen / 'manifest.json'),
                  source_snapshot_sha256=digest(ROOT / spec['source_snapshot']), protocol_sha256=digest(frozen / 'protocol.json'),
                  limitation='assumed immediate events and retrospective proxy; no power or telemetry uptime certification')
    destination.mkdir(parents=True)
    path = destination / 'verification.json'
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    (destination / 'manifest.json').write_text(json.dumps({'verification.json': digest(path)}, indent=2) + '\n')
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--frozen', type=Path, default=ROOT / 'outputs/visibility/SG-DATA-007-jpl-eventtime-v1')
    parser.add_argument('--out', type=Path, default=ROOT / 'outputs/visibility/SG-DATA-007-jpl-eventtime-v1-verification')
    args = parser.parse_args()
    verify(args.frozen, args.out)
