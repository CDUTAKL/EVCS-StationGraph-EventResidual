"""按预登记协议核查JPL全量元数据并冻结张量；不训练、不产生测试预测。"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from evcs_station_graph.data import visibility_v2 as v
from evcs_station_graph.graphs.relations import build_relation_set


def sha256(path):
    """计算本地文件来源摘要，不输出文件内容。"""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    """写入派生审计工件；禁止隐式NaN或无限值。"""
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def split_bounds(length):
    """固定70/7.5/7.5/15顺序分段，和配置口径一致。"""
    limits = [0, int(length * .70), int(length * .775), int(length * .85), length]
    return dict(zip(('train', 'tuning', 'calibration', 'test'), zip(limits[:-1], limits[1:])))


def select_nodes(frame, cutoff, spec):
    """只以成熟训练会话计数和月份选节点，拒绝按测试结果替换节点。"""
    final_time = frame.disconnectTime
    if 'doneChargingTime' in frame:
        final_time = pd.concat([final_time, frame.doneChargingTime], axis=1).max(axis=1)
    mature = frame.loc[final_time < cutoff]
    candidates = []
    for node, group in mature.groupby('spaceID', sort=True):
        months = group.connectionTime.dt.strftime('%Y-%m').nunique()
        candidates.append(dict(node_id=str(node), mature_training_sessions=len(group), active_months=int(months)))
    eligible = [r for r in candidates if r['mature_training_sessions'] >= spec['minimum_mature_sessions'] and r['active_months'] >= spec['minimum_active_months']]
    eligible.sort(key=lambda r: (-r['mature_training_sessions'], r['node_id']))
    if len(eligible) < spec['count']:
        raise ValueError('Fewer than ten eligible training-only spaces; pre-registered stop')
    return [r['node_id'] for r in eligible[:spec['count']]], candidates


def validate_frame(frame):
    """核查全量字段与身份；异常不静默填补，不把时序缺失视为实测零。"""
    essential = ['session_key', 'siteID', 'stationID', 'spaceID', 'connectionTime', 'disconnectTime', 'kWhDelivered', 'timezone']
    if frame[essential].isna().any().any():
        raise ValueError('Essential session metadata missing; stop before target construction')
    for field in ('session_key', 'siteID', 'stationID', 'spaceID', 'timezone'):
        if not frame[field].map(lambda item: isinstance(item, str) and bool(item.strip()) and item.strip().lower() not in ('none', 'null', 'nan')).all():
            raise ValueError('Invalid or empty identity metadata: ' + field)
    if frame.session_key.duplicated().any():
        raise ValueError('Duplicate session keys')
    if not np.isfinite(frame.kWhDelivered).all() or (frame.kWhDelivered < 0).any():
        raise ValueError('Invalid energy')
    if (frame.disconnectTime < frame.connectionTime).any():
        raise ValueError('Departure precedes arrival')
    if frame.siteID.nunique() != 1 or set(frame.timezone) != {'America/Los_Angeles'}:
        raise ValueError('Unexpected site/timezone')
    if frame.groupby('stationID').spaceID.nunique().max() > 1:
        raise ValueError('stationID maps to multiple parking spaces; identity gate failed')


def execute(config_path):
    """在所有来源与可见性检查通过后保存冻结资产，不改旧协议和正式论文。"""
    spec = json.loads(config_path.read_text())
    if (spec['history_steps'], spec['horizon_steps'], spec['interval_minutes']) != (96, 4, 15):
        raise ValueError('Only the frozen 96-to-4, 15min contract is supported')
    if tuple(spec['feature_names']) != v.FEATURE_NAMES or spec['split_fractions'] != {'train': .70, 'tuning': .075, 'calibration': .075, 'test': .15}:
        raise ValueError('Frozen feature or split policy changed')
    if spec['rule']['quantile'] != .95 or spec['rule']['extension'] != 2:
        raise ValueError('Frozen rule contract changed')
    source = ROOT / spec['source_snapshot']
    acquisition_path = ROOT / spec['source_manifest']
    acquisition = json.loads(acquisition_path.read_text())
    if acquisition['status'] != 'complete' or sha256(source) != acquisition['snapshot_sha256']:
        raise ValueError('Incomplete or changed source snapshot')
    dest = ROOT / spec['output']
    if dest.exists():
        raise FileExistsError('Frozen output exists; use verify instead of overwriting')
    # 禁止先字符串化：null变为"None"会绕过缺失门禁；保留API原始字段类型。
    frame = pd.read_json(source, lines=True, dtype=False, convert_dates=False)
    for column in ('connectionTime', 'disconnectTime', 'doneChargingTime'):
        frame[column] = pd.to_datetime(frame[column], utc=True, errors='raise', format='mixed')
    if len(frame) != acquisition['records_saved']:
        raise ValueError('Source count mismatch')
    basic_quality = dict(source_records=len(frame), source_sha256=sha256(source),
                         missing_counts={c: int(frame[c].isna().sum()) for c in frame.columns},
                         duplicate_session_keys=int(frame.session_key.duplicated().sum()),
                         negative_energy=int((frame.kWhDelivered < 0).sum()),
                         reversed_sessions=int((frame.disconnectTime < frame.connectionTime).sum()),
                         station_ids_mapping_multiple_spaces=int((frame.groupby('stationID').spaceID.nunique() > 1).sum()),
                         credential_saved=False, training_performed=False)
    try:
        validate_frame(frame)
    except ValueError as error:
        write_json(acquisition_path.parent / 'quality.json', dict(basic_quality, status='data_gate_failed', reason=str(error)))
        raise
    write_json(acquisition_path.parent / 'quality.json', dict(basic_quality, status='metadata_gate_passed'))
    start = frame.connectionTime.min().floor('15min')
    stop = frame.disconnectTime.max().ceil('15min')
    grid = pd.date_range(start, stop, freq='15min', inclusive='left').astype('int64').to_numpy()
    bounds = split_bounds(len(grid))
    cutoff = pd.Timestamp(grid[bounds['train'][1]], tz='UTC')
    nodes, candidates = select_nodes(frame, cutoff, spec['node_selection'])
    selected = frame.loc[frame.spaceID.isin(nodes)].copy()
    x = v.event_features(selected, grid, nodes)
    y, maturity = v.proxy_targets(selected, grid, nodes)
    # 仅用于事后标签成熟门禁；若完成字段晚于离站，采用更晚时刻而不回灌输入。
    for row in selected.loc[selected.doneChargingTime > selected.disconnectTime].itertuples(index=False):
        if row.connectionTime == row.disconnectTime:
            continue
        lo = int((row.connectionTime.value - grid[0]) // v.STEP)
        hi = int((row.disconnectTime.value - grid[0] + v.STEP - 1) // v.STEP)
        n = nodes.index(str(row.spaceID))
        maturity[lo:hi, n] = np.maximum(maturity[lo:hi, n], row.doneChargingTime.value)
    zero_duration = selected.disconnectTime == selected.connectionTime
    expected_energy = float(selected.loc[~zero_duration, 'kWhDelivered'].sum())
    if not np.isclose(y.sum(), expected_energy, rtol=1e-10, atol=1e-8):
        raise AssertionError('Proxy energy conservation failed')
    train_end = bounds['train'][1]
    fit_end = v.mature_prefix_end(maturity, grid, train_end)
    params = v.fit_preprocessing(x, y, fit_end)
    graphs = np.stack(build_relation_set(x[:fit_end], y[:fit_end], v.FEATURE_NAMES, top_k=spec['graphs']['top_k']).as_list())
    origins = {s: v.safe_origins(grid, maturity, lo, hi, spec['history_steps'], spec['horizon_steps']) for s, (lo, hi) in bounds.items()}
    origins['train'] = origins['train'][origins['train'] + spec['horizon_steps'] < fit_end]
    if any(len(o) < 100 for o in origins.values()):
        raise ValueError('Insufficient eligible windows in a frozen segment')
    scores = v.rule_scores(x, params['rule_std'])
    tuning_scores = scores[origins['tuning']]
    thresholds = np.array([np.quantile(c[c > 0], .95) if np.any(c > 0) else np.inf for c in tuning_scores.T])
    trigger = v.apply_rule(scores, thresholds, spec['rule']['extension'])
    jumps = np.abs(np.diff(y, axis=0, prepend=y[[0]]))
    target_event = (x[:, :, 0] > 0) | (x[:, :, 1] > 0) | (jumps > params['label_jump_threshold'])

    # 改动持出期数值，训练拟合及图必须保持逐值一致。
    changed_x, changed_y = x.copy(), y.copy()
    changed_x[train_end:] += 12345
    changed_y[train_end:] += 12345
    altered_params = v.fit_preprocessing(changed_x, changed_y, fit_end)
    for name, values in params.items():
        np.testing.assert_array_equal(values, altered_params[name])
    altered_graphs = np.stack(build_relation_set(changed_x[:fit_end], changed_y[:fit_end], v.FEATURE_NAMES, top_k=spec['graphs']['top_k']).as_list())
    np.testing.assert_array_equal(graphs, altered_graphs)
    mutated = selected.copy()
    mutated['kWhDelivered'] = mutated.kWhDelivered * 1000 + 999
    np.testing.assert_array_equal(x, v.event_features(mutated, grid, nodes))

    # 固定每段首、中、末原点，屏蔽尚未结束会话字段并逐前缀回放。
    replay_cases = []
    for split, oo in origins.items():
        for k in np.unique(oo[[0, len(oo) // 2, -1]]):
            instant = pd.Timestamp(grid[k] + v.STEP, tz='UTC')
            censored = selected.loc[selected.connectionTime < instant].copy()
            censored.loc[censored.disconnectTime >= instant, 'disconnectTime'] = pd.NaT
            censored = censored.drop(columns=['kWhDelivered', 'doneChargingTime'])
            prefix = v.event_features(censored, grid[:k + 1], nodes)
            np.testing.assert_array_equal(prefix, x[:k + 1])
            np.testing.assert_array_equal(v.apply_rule(v.rule_scores(prefix, params['rule_std']), thresholds, 2), trigger[:k + 1])
            replay_cases.append(dict(split=split, origin=int(k), cutoff_utc=instant.isoformat(), pass_input_and_rule=True))

    mapping = []
    for space, group in frame.groupby('spaceID', sort=True):
        mapping.append(dict(node_id=str(space), station_ids=sorted(group.stationID.unique()), clusters=sorted(group.clusterID.dropna().unique()), sessions=len(group)))
    monthly = Counter(frame.connectionTime.dt.strftime('%Y-%m'))
    missing_months = [str(m) for m in pd.period_range(start.tz_localize(None), stop.tz_localize(None), freq='M') if str(m) not in monthly]
    static_path = ROOT / 'outputs/analysis/JPL-feasibility-20261004/candidate_coverage.json'
    static_ids = {r['candidate_id'] for r in json.loads(static_path.read_text())}
    official_ids = set(frame.stationID)
    late_completion = (frame.doneChargingTime > frame.disconnectTime).fillna(False)
    early_completion = (frame.doneChargingTime < frame.connectionTime).fillna(False)
    summary = dict(protocol=spec['protocol_id'], experiment='SG-EXP-028', status='data_frozen_no_training',
                   source_records=len(frame), site_ids=sorted(frame.siteID.unique()),
                   station_ids=int(frame.stationID.nunique()), parking_spaces=int(frame.spaceID.nunique()),
                   spaces_with_station_aliases=sum(len(r['station_ids']) > 1 for r in mapping),
                   static_crosswalk=dict(static_station_prefixes=len(static_ids), official_station_ids=len(official_ids), matching=len(static_ids & official_ids), static_only=sorted(static_ids - official_ids), api_only=sorted(official_ids - static_ids)),
                   essential_missing_counts={c: int(frame[c].isna().sum()) for c in frame.columns},
                   completion_outside_connection_interval=int((late_completion | early_completion).sum()),
                   connection_min_utc=frame.connectionTime.min().isoformat(), disconnect_max_utc=frame.disconnectTime.max().isoformat(),
                   monthly_session_counts=dict(sorted(monthly.items())), months_without_records=missing_months,
                   grid_steps=len(grid), selected_nodes=nodes, selected_sessions=len(selected),
                   zero_duration_sessions=int(zero_duration.sum()), zero_duration_energy=float(selected.loc[zero_duration, 'kWhDelivered'].sum()),
                   conservation_absolute_gap=float(abs(y.sum() - expected_energy)),
                   fit_prefix_end_exclusive=fit_end, split_bounds={s: list(b) for s, b in bounds.items()},
                   split_cutoffs_utc={s: pd.Timestamp(grid[hi - 1] + v.STEP, tz='UTC').isoformat() for s, (_, hi) in bounds.items()},
                   origin_counts={s: len(o) for s, o in origins.items()},
                   test_time_blocks_7day=int(len(np.unique((grid[origins['test']] - grid[origins['test'][0]]) // (7 * 86400 * 10**9)))),
                   invariance_cases=replay_cases,
                   checks=dict(complete_source=True, unique_sessions=True, stable_node_aliases=True, train_only_selection=True, label_maturity=True, energy_conservation=True, future_energy_not_in_inputs=True, heldout_changes_leave_train_fit_unchanged=True, input_rule_prefix_replay=True),
                   limitations=['unmeasured event reporting latency', 'session proxy rather than actual power', 'no certified telemetry uptime on empty days', 'same ACN source family and overlapping historical period', 'no zero-shot transfer', 'only metadata QC and no model test scores inspected'],
                   training_performed=False, model_test_predictions_created=False,
                   training_adapter_status='pending JPL-specific strict loader and package; existing SG-DATA-006 hardcoded loader must not be used')
    dest.mkdir(parents=True)
    np.savez_compressed(dest / 'dataset.npz', timestamps_ns=grid, node_ids=np.array(nodes), feature_names=np.array(v.FEATURE_NAMES),
                        features=x, targets=y, label_available_at_ns=maturity, target_event=target_event, rule_trigger=trigger,
                        graphs=graphs, rule_thresholds=thresholds, **params,
                        **{s + '_origins': o for s, o in origins.items()}, schema=np.array('jpl-eventtime-v1-not-legacy-TensorBundle'))
    write_json(dest / 'audit.json', summary)
    write_json(dest / 'node_selection.json', dict(selected=nodes, candidates=candidates, cutoff_utc=cutoff.isoformat(), policy=spec['node_selection']))
    write_json(dest / 'node_crosswalk.json', mapping)
    write_json(dest / 'protocol.json', spec)
    source_paths = [source, acquisition_path, config_path, Path(__file__), Path(v.__file__), ROOT / 'src/evcs_station_graph/graphs/relations.py', ROOT / 'configs/experiments/SG-EXP-028-jpl-independent-site.json']
    write_json(dest / 'manifest.json', dict(files={p.name: sha256(p) for p in sorted(dest.iterdir()) if p.is_file()},
                                         sources={str(p.relative_to(ROOT)): sha256(p) for p in source_paths}))
    print(json.dumps({k: summary[k] for k in ('status', 'source_records', 'station_ids', 'parking_spaces', 'grid_steps', 'selected_nodes', 'origin_counts', 'checks')}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=ROOT / 'configs/data/SG-DATA-007-jpl-eventtime-v1.json')
    args = parser.parse_args()
    execute(args.config)
