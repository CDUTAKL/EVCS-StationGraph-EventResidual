"""SG-EXP-021：只读归档预测的十节点需求阈值预警计算与审计。

输入严格保持 SG-EXP-019 的逐键预测，不训练、不裁剪、不调阈值。
分类四格、日配对 bootstrap、事件起点前匹配和工件写出相互独立。
时间语义：归档目标为时间片左端点，不把时间片右端点冒充事件起点。
仅依赖 NumPy 与标准库；默认输出新目录，拒绝覆盖已有计算结果。
"""

from __future__ import annotations

import argparse
import contextlib
import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path
import platform
import shlex
import subprocess
import sys
from datetime import datetime, timezone, date
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np

METRIC_NAMES = ('recall', 'precision', 'fpr', 'f1')
COUNT_NAMES = ('tp', 'fp', 'fn', 'tn')
NS_PER_MINUTE = 60_000_000_000  # 纳秒/分钟，所有内部时间计算使用整数。


def sha256_file(path: Path) -> str:
    """返回文件 SHA256；缺失或无法读取直接报错，不跳过输入。"""
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def clean_json(value: Any) -> Any:
    """将 NumPy 标量及未定义指标转成合法 JSON，未定义值明确写 null。"""
    if isinstance(value, dict):
        return {str(k): clean_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, np.ndarray)):
        return [clean_json(v) for v in value]
    if isinstance(value, np.generic):
        return clean_json(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def write_json(path: Path, value: Any) -> None:
    """确定性 UTF-8 写出计算工件，不允许非标准 NaN JSON。"""
    path.write_text(json.dumps(clean_json(value), ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + '\n', encoding='utf-8')


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    """写出稳定字段 CSV；未定义指标为空白，不伪造为零。"""
    if fields is None:
        fields = list(rows[0]) if rows else []
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(clean_json(rows))


def timestamp_text(timestamp_ns: int, zone: str = 'UTC') -> str:
    """将整分钟级纳秒时间戳转换为含时区文本，不改变计算时间键。"""
    return datetime.fromtimestamp(int(timestamp_ns) / 1e9, timezone.utc).astimezone(ZoneInfo(zone)).isoformat()


def deduplicate_truth(times: np.ndarray, truth: np.ndarray, atol: float, rtol: float) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    """按唯一目标时间去重，并逐节点拒绝超容差的重叠真值。"""
    # [origin,horizon,node]→[origin*horizon,node]，保留节点维防止总量抵消。
    flat_truth = truth.reshape(-1, truth.shape[-1])
    flat_times = times.reshape(-1)
    unique, first, inverse, counts = np.unique(flat_times, return_index=True, return_inverse=True, return_counts=True)
    selected = flat_truth[first]
    errors = np.abs(flat_truth - selected[inverse])
    if not np.all(np.isclose(flat_truth, selected[inverse], atol=atol, rtol=rtol)):
        bad = np.argwhere(~np.isclose(flat_truth, selected[inverse], atol=atol, rtol=rtol))[0]
        raise ValueError(f'inconsistent overlapping truth: target={int(flat_times[bad[0]])}, node={int(bad[1])}, max_error={float(errors.max())}')
    return unique, selected, dict(unique_targets=len(unique), total_target_occurrences=len(flat_times),
                                 duplicate_occurrences=len(flat_times)-len(unique), max_multiplicity=int(counts.max()),
                                 max_node_truth_error=float(errors.max()), exact_equal=bool(np.array_equal(flat_truth, selected[inverse])))


def time_semantics(times: np.ndarray, cutoffs: np.ndarray, step_ns: int) -> dict[str, Any]:
    """识别左端点 0..3 步或严格未来 1..4 步；负提前量或非统一键拒绝。"""
    delta = times - cutoffs[:, None]
    expected = np.arange(times.shape[1]) * step_ns
    if not (np.all(delta == expected) or np.all(delta == expected + step_ns)):
        raise ValueError('invalid target timestamp lead pattern: negative, nonuniform or unexpected horizons')
    leads = (delta[0] // step_ns).tolist()
    return dict(observed_target_start_lead_steps=leads, strict_future_target_start_contract=bool(np.all(delta > 0)),
                timestamp_shift_applied=False, issue_time_field='origin_cutoff_ns', target_time_field='target_timestamps_ns')


def validate_archive(arrays: dict[str, np.ndarray], config: dict[str, Any], split: str) -> dict[str, Any]:
    """验证单文件形状、有限值、唯一预测原点和时间步；事件掩码只作结构审计。"""
    required = {'y_true', 'y_pred', 'origins', 'node_ids', 'target_timestamps_ns', 'origin_cutoff_ns', 'target_event', 'rule_trigger'}
    if not required <= set(arrays):
        raise ValueError(f'missing NPZ keys: {sorted(required-set(arrays))}')
    origin_count = config['expected_origin_counts'][split]
    horizon_count, node_count = config['expected_horizons'], config['expected_nodes']
    shapes = {'y_true': (origin_count, horizon_count, node_count), 'y_pred': (origin_count, horizon_count, node_count),
              'target_event': (origin_count, horizon_count, node_count), 'rule_trigger': (origin_count, horizon_count, node_count),
              'origins': (origin_count,), 'node_ids': (node_count,), 'target_timestamps_ns': (origin_count, horizon_count),
              'origin_cutoff_ns': (origin_count,)}
    for key, shape in shapes.items():
        if arrays[key].shape != shape:
            raise ValueError(f'{key} shape {arrays[key].shape} != {shape}')
        if np.issubdtype(arrays[key].dtype, np.number) and not np.isfinite(arrays[key]).all():
            raise ValueError(f'nonfinite {key}')
    for key in ('origins', 'target_timestamps_ns', 'origin_cutoff_ns'):
        if not np.issubdtype(arrays[key].dtype, np.integer):
            raise ValueError(f'{key} must have integer dtype')
    for key in ('target_event', 'rule_trigger'):
        if not np.isin(arrays[key], [0, 1]).all():
            raise ValueError(f'{key} not boolean-valued')
    if np.any(np.diff(arrays['origins']) <= 0) or np.any(np.diff(arrays['origin_cutoff_ns']) <= 0):
        raise ValueError('origins/cutoffs not monotonically unique')
    if len(np.unique(arrays['node_ids'])) != node_count:
        raise ValueError('nonunique node_ids')
    if np.any(arrays['y_true'] < 0):
        raise ValueError('negative proxy ground truth')
    step_ns = config['step_minutes'] * NS_PER_MINUTE
    if not np.all(np.diff(arrays['target_timestamps_ns'], axis=1) == step_ns):
        raise ValueError('nonconsecutive target horizon timestamps')
    if not np.all(np.diff(arrays['origin_cutoff_ns']) == np.diff(arrays['origins']) * step_ns):
        raise ValueError('origin index/time mismatch')
    semantics = time_semantics(arrays['target_timestamps_ns'], arrays['origin_cutoff_ns'], step_ns)
    semantics['observed_target_start_lead_minutes'] = [x * config['step_minutes'] for x in semantics['observed_target_start_lead_steps']]
    return dict(shapes={k: list(v.shape) for k, v in arrays.items()}, dtypes={k: str(v.dtype) for k, v in arrays.items()},
                negative_prediction_values=int(np.sum(arrays['y_pred'] < 0)), min_prediction=float(arrays['y_pred'].min()),
                max_prediction=float(arrays['y_pred'].max()), time_semantics=semantics, ignored_mask_keys=['target_event', 'rule_trigger'])


def load_archives(source_root: Path, config: dict[str, Any], audit: dict[str, Any]) -> tuple[dict[tuple[str, int, str], dict[str, np.ndarray]], dict[str, tuple[np.ndarray, np.ndarray]]]:
    """只读载入全部模型/种子/划分，验证跨运行逐键完全相同，并检查划分不相交。"""
    loaded, unique_truth, references = {}, {}, {}
    for split in config['splits']:
        for model in config['models']:
            for seed in config['seeds']:
                relative = Path(model) / f'seed-{seed}' / f'predictions_{split}.npz'
                path = source_root / relative
                record = dict(relative_path=str(relative), path=str(path), sha256=sha256_file(path), bytes=path.stat().st_size)
                audit['sources'].append(record)
                with np.load(path, allow_pickle=False) as archive:
                    arrays = {key: archive[key] for key in archive.files}
                record.update(validate_archive(arrays, config, split))
                unique_times, node_truth, dedup = deduplicate_truth(arrays['target_timestamps_ns'], arrays['y_true'],
                                                                  config['overlapping_truth_atol'], config['overlapping_truth_rtol'])
                record['deduplication'] = dedup
                if split not in references:
                    references[split] = arrays
                    unique_truth[split] = (unique_times, node_truth.sum(axis=-1, dtype=np.float64))
                else:
                    for key in ('origins', 'node_ids', 'target_timestamps_ns', 'origin_cutoff_ns', 'y_true'):
                        if not np.array_equal(arrays[key], references[split][key]):
                            raise ValueError(f'cross-model/seed {key} mismatch: {relative}')
                record['cross_run_keys_truth_exact_equal'] = True
                loaded[(model, seed, split)] = arrays
    overlap = np.intersect1d(unique_truth['calibration'][0], unique_truth['test'][0])
    if len(overlap):
        raise ValueError(f'calibration/test target overlap: {len(overlap)}')
    if unique_truth['calibration'][0][-1] >= unique_truth['test'][0][0]:
        raise ValueError('calibration does not chronologically precede test')
    if not np.array_equal(references['calibration']['node_ids'], references['test']['node_ids']):
        raise ValueError('calibration/test node identity mismatch')
    if np.intersect1d(references['calibration']['origins'], references['test']['origins']).size:
        raise ValueError('calibration/test origin overlap')
    audit['split_checks'] = dict(target_timestamp_overlap=0, calibration_precedes_test=True, node_ids=references['test']['node_ids'].tolist(),
                                 cross_run_truth_equality='exact_array_equal', overlapping_truth_tolerance=dict(atol=config['overlapping_truth_atol'], rtol=config['overlapping_truth_rtol']))
    return loaded, unique_truth


def confusion_counts(truth: np.ndarray, prediction: np.ndarray, threshold: float) -> np.ndarray:
    """严格大于同一冻结阈值生成 TP/FP/FN/TN；不使用旧事件掩码。"""
    positive, alarm = truth > threshold, prediction > threshold
    return np.array([np.sum(positive & alarm), np.sum(~positive & alarm), np.sum(positive & ~alarm), np.sum(~positive & ~alarm)], dtype=np.int64)


def metric_values(counts: np.ndarray) -> np.ndarray:
    """最后一维四格转 recall/precision/FPR/F1；零分母返回未定义 NaN。"""
    tp, fp, fn, tn = np.moveaxis(np.asarray(counts, dtype=np.float64), -1, 0)
    numerators = np.stack([tp, tp, fp, 2 * tp], axis=-1)
    denominators = np.stack([tp + fn, tp + fp, fp + tn, 2 * tp + fp + fn], axis=-1)
    # F1 直接用四格定义；无阳性但有误报时为零，不因为 recall 未定义而丢弃。
    return np.divide(numerators, denominators, out=np.full_like(numerators, np.nan), where=denominators != 0)


def complete_summary(values: np.ndarray) -> tuple[float, float, int]:
    """所有种子均有定义才报告均值/样本标准差，不静默忽略未定义种子。"""
    valid = int(np.isfinite(values).sum())
    if valid != len(values) or valid < 2:
        return float('nan'), float('nan'), valid
    return float(values.mean()), float(values.std(ddof=1)), valid


def classification_tables(loaded: dict, thresholds: list[dict], config: dict) -> tuple[list[dict], list[dict]]:
    """计算 calibration/test 每种子每步及 pooled 指标，随后作三种子汇总。"""
    rows = []
    horizon_count = config['expected_horizons']
    for threshold_record in thresholds:
        quantile, threshold = threshold_record['quantile'], threshold_record['threshold_kwh_per_15min']
        for (model, seed, split), arrays in loaded.items():
            truth, pred = arrays['y_true'].sum(axis=-1, dtype=np.float64), arrays['y_pred'].sum(axis=-1, dtype=np.float64)
            lead_steps = time_semantics(arrays['target_timestamps_ns'], arrays['origin_cutoff_ns'], config['step_minutes'] * NS_PER_MINUTE)['observed_target_start_lead_steps']
            for horizon in range(horizon_count + 1):
                pooled = horizon == horizon_count
                counts = confusion_counts(truth if pooled else truth[:, horizon], pred if pooled else pred[:, horizon], threshold)
                row = dict(quantile=quantile, threshold=threshold, split=split, model=model, seed=seed,
                           horizon_minutes='pooled' if pooled else (horizon + 1) * config['step_minutes'],
                           horizon_step='pooled' if pooled else horizon + 1,
                           actual_target_start_lead_minutes='mixed' if pooled else lead_steps[horizon] * config['step_minutes'], n=int(counts.sum()))
                row.update(zip(COUNT_NAMES, counts.tolist()))
                row.update(zip(METRIC_NAMES, metric_values(counts).tolist()))
                rows.append(row)
    summaries = []
    for quantile in [r['quantile'] for r in thresholds]:
        for split in config['splits']:
            for model in config['models']:
                for horizon in [15, 30, 45, 60, 'pooled']:
                    group = [r for r in rows if (r['quantile'], r['split'], r['model'], r['horizon_minutes']) == (quantile, split, model, horizon)]
                    if len(group) != len(config['seeds']):
                        raise ValueError('incomplete classification seed group')
                    row = dict(quantile=quantile, threshold=group[0]['threshold'], split=split, model=model, horizon_minutes=horizon,
                               actual_target_start_lead_minutes=group[0]['actual_target_start_lead_minutes'], n_per_seed=group[0]['n'], seeds=len(group))
                    for name in COUNT_NAMES + METRIC_NAMES:
                        mean, sd, defined = complete_summary(np.array([g[name] for g in group]))
                        row.update({name+'_mean': mean, name+'_sample_sd': sd, name+'_defined_seeds': defined})
                    summaries.append(row)
    return rows, summaries


def local_day_groups(cutoffs: np.ndarray, zone: str) -> tuple[list[str], np.ndarray]:
    """按预测 cutoff 本地日分组，自动遵循夏令时，不按目标时点分组。"""
    keys = [datetime.fromtimestamp(int(t) / 1e9, timezone.utc).astimezone(ZoneInfo(zone)).date().isoformat() for t in cutoffs]
    dates, inverse = np.unique(keys, return_inverse=True)
    return dates.tolist(), inverse


def daily_counts(truth: np.ndarray, prediction: np.ndarray, threshold: float, day_index: np.ndarray, day_count: int) -> np.ndarray:
    """每日期保留完整步长；[day,horizon+pooled,TP/FP/FN/TN] 为充分统计量。"""
    positive, alarm = truth > threshold, prediction > threshold
    result = np.zeros((day_count, truth.shape[1] + 1, 4), dtype=np.int64)
    masks = (positive & alarm, ~positive & alarm, positive & ~alarm, ~positive & ~alarm)
    for cell, mask in enumerate(masks):
        for horizon in range(truth.shape[1]):
            np.add.at(result[:, horizon, cell], day_index, mask[:, horizon].astype(np.int64))
        result[:, -1, cell] = result[:, :-1, cell].sum(axis=1)
    return result


def day_draws(day_count: int, replicates: int, seed: int, block_days: int = 1) -> np.ndarray:
    """固定 PCG64 日期重采样；移动块非循环，拼接后截取原日期总数。"""
    if day_count < block_days or day_count < 1:
        raise ValueError('too few dates for requested bootstrap block')
    rng = np.random.Generator(np.random.PCG64(seed))
    if block_days == 1:
        return rng.integers(0, day_count, size=(replicates, day_count))
    blocks = math.ceil(day_count / block_days)
    starts = rng.integers(0, day_count - block_days + 1, size=(replicates, blocks))
    # [replicate,block,offset]→[replicate,draw]，每块真实连续，尾块按总日数截断。
    return (starts[..., None] + np.arange(block_days)).reshape(replicates, -1)[:, :day_count]


def draws_to_weights(draws: np.ndarray, day_count: int) -> np.ndarray:
    """将同一日期抽样转换为 multiplicity；同一权重共同应用全部方法和种子。"""
    weights = np.zeros((len(draws), day_count), dtype=np.int64)
    np.add.at(weights, (np.repeat(np.arange(len(draws)), draws.shape[1]), draws.reshape(-1)), 1)
    return weights


def apply_day_weights(counts: np.ndarray, weights: np.ndarray) -> np.ndarray:
    """成组计数 [model,seed,day,horizon,cell]→[replicate,model,seed,horizon,cell]。"""
    # 对 day 轴求加权和，不拆散同日的任何原点、步长、种子或模型。
    return np.einsum('bd,msdhc->bmshc', weights, counts, optimize=True)


def bootstrap_tables(loaded: dict, thresholds: list[dict], config: dict, output: Path) -> tuple[list[dict], dict]:
    """日配对和七日移动块 CI；先按种子计算指标再平均，不混合种子四格。"""
    reference = loaded[(config['models'][0], config['seeds'][0], 'test')]
    dates, day_index = local_day_groups(reference['origin_cutoff_ns'], config['timezone'])
    consecutive = all((date.fromisoformat(b)-date.fromisoformat(a)).days == 1 for a, b in zip(dates, dates[1:]))
    daily_rows = [dict(day_index=i, local_date=d, origin_count=int(np.sum(day_index == i))) for i, d in enumerate(dates)]
    write_csv(output / 'bootstrap_days.csv', daily_rows)
    draws_by_method = {'paired_calendar_day': day_draws(len(dates), config['bootstrap_replicates'], config['bootstrap_seed'])}
    diagnostics = dict(timezone=config['timezone'], grouping='origin_cutoff_ns', dates=len(dates), consecutive_dates=consecutive,
                       replicates=config['bootstrap_replicates'], rng='numpy.random.Generator(PCG64)', seed=config['bootstrap_seed'],
                       seed_replicates_resampled=False, all_models_seeds_horizons_share_date_draws=True,
                       ci='uncorrected descriptive percentile 95%; not a significance claim', methods={})
    if consecutive and len(dates) >= config['moving_block_days']:
        draws_by_method['moving_block_7day_descriptive'] = day_draws(len(dates), config['bootstrap_replicates'], config['bootstrap_seed'], config['moving_block_days'])
    else:
        diagnostics['moving_block_skip_reason'] = 'not enough consecutive calendar dates'
    summaries, replicate_rows, counts_rows = [], [], []
    for method, draws in draws_by_method.items():
        np.savez_compressed(output / f'bootstrap_draws_{method}.npz', date_index_draws=draws, local_dates=np.array(dates))
        diagnostics['methods'][method] = dict(draws_sha256=sha256_file(output / f'bootstrap_draws_{method}.npz'), circular=False,
                                             block_days=1 if method == 'paired_calendar_day' else config['moving_block_days'])
    for threshold_record in thresholds:
        quantile, threshold = threshold_record['quantile'], threshold_record['threshold_kwh_per_15min']
        counts = np.stack([np.stack([daily_counts(loaded[(model, seed, 'test')]['y_true'].sum(axis=-1, dtype=np.float64),
                           loaded[(model, seed, 'test')]['y_pred'].sum(axis=-1, dtype=np.float64), threshold, day_index, len(dates))
                           for seed in config['seeds']]) for model in config['models']])
        for mi, model in enumerate(config['models']):
            for si, seed in enumerate(config['seeds']):
                for di, d in enumerate(dates):
                    for hi, h in enumerate([15, 30, 45, 60, 'pooled']):
                        row = dict(quantile=quantile, model=model, seed=seed, local_date=d, horizon_minutes=h)
                        row.update(zip(COUNT_NAMES, counts[mi, si, di, hi].tolist()))
                        counts_rows.append(row)
        point = metric_values(counts.sum(axis=2)).mean(axis=1)
        for method, draws in draws_by_method.items():
            samples = metric_values(apply_day_weights(counts, draws_to_weights(draws, len(dates)))).mean(axis=2)
            for left, right in config['bootstrap_comparisons']:
                li, ri = config['models'].index(left), config['models'].index(right)
                delta = samples[:, li] - samples[:, ri]
                for hi, h in enumerate([15, 30, 45, 60, 'pooled']):
                    for metric_index, metric in enumerate(METRIC_NAMES):
                        values = delta[:, hi, metric_index]
                        defined = int(np.isfinite(values).sum())
                        # 任一重采样无定义时不挑选有效样本报告 CI，只给出明确缺失和计数。
                        ci = np.quantile(values, config['bootstrap_ci_quantiles'], method='linear') if defined == len(values) else [float('nan')] * 2
                        summaries.append(dict(method=method, quantile=quantile, comparison=f'{left}-{right}', horizon_minutes=h, metric=metric,
                                              point_difference=float(point[li, hi, metric_index]-point[ri, hi, metric_index]),
                                              ci_lower=float(ci[0]), ci_upper=float(ci[1]), defined_replicates=defined, total_replicates=len(values),
                                              favorable_direction='negative' if metric == 'fpr' else 'positive'))
                        for replicate, value in enumerate(values):
                            replicate_rows.append(dict(method=method, quantile=quantile, comparison=f'{left}-{right}', horizon_minutes=h,
                                                       metric=metric, replicate=replicate, difference=float(value)))
    write_csv(output / 'daily_confusion_counts.csv', counts_rows)
    write_csv(output / 'bootstrap_replicate_differences.csv', replicate_rows)
    write_csv(output / 'bootstrap_summary.csv', summaries)
    write_json(output / 'bootstrap.json', dict(diagnostics=diagnostics, summaries=summaries))
    return summaries, diagnostics


def build_episodes(times: np.ndarray, values: np.ndarray, threshold: float, step_ns: int) -> list[dict[str, Any]]:
    """唯一连续超阈值时间片合并为事件；缺口断开并注明左/右删失。"""
    if len(times) != len(values) or np.any(np.diff(times) <= 0):
        raise ValueError('episode times must be unique sorted and aligned')
    indices = np.flatnonzero(values > threshold)
    if not len(indices):
        return []
    groups = np.split(indices, np.flatnonzero(np.diff(times[indices]) != step_ns) + 1)
    episodes = []
    for episode_index, group in enumerate(groups):
        first, last = int(group[0]), int(group[-1])
        episodes.append(dict(episode_id=episode_index+1, onset_ns=int(times[first]), last_target_ns=int(times[last]),
                             interval_end_ns=int(times[last]+step_ns), n_intervals=len(group), peak=float(values[group].max()),
                             left_censored=bool(first == 0 or times[first]-times[first-1] != step_ns),
                             right_censored=bool(last == len(times)-1 or times[last+1]-times[last] != step_ns)))
    return episodes


def history_eligible(onset_ns: int, cutoffs: set[int], history_ns: int, step_ns: int) -> bool:
    """完整历史机会要求 onset-history 到 onset-step 全部原点可用；不要求 onset 原点。"""
    return all(onset_ns - offset in cutoffs for offset in range(step_ns, history_ns + 1, step_ns))


def earliest_warning(episode: dict[str, Any], cutoffs: np.ndarray, times: np.ndarray, alarms: np.ndarray) -> dict[str, int] | None:
    """只匹配严格 onset 前发出且目标属于本事件的警报，返回最早一次或 None。"""
    valid = (cutoffs[:, None] < episode['onset_ns']) & (times >= episode['onset_ns']) & (times <= episode['last_target_ns']) & alarms
    positions = np.argwhere(valid)
    if not len(positions):
        return None
    earliest_index = int(np.argmin(cutoffs[positions[:, 0]]))
    origin_row, horizon = positions[earliest_index]
    return dict(issue_ns=int(cutoffs[origin_row]), target_ns=int(times[origin_row, horizon]), origin_row=int(origin_row), horizon_step=int(horizon+1))


def episode_tables(loaded: dict, unique_truth: dict, thresholds: list[dict], config: dict) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    """事件检测只按新阈值真值事件；漏事件与命中条件提前量分别报告。"""
    times, values = unique_truth['test']
    reference = loaded[(config['models'][0], config['seeds'][0], 'test')]
    step_ns = config['step_minutes'] * NS_PER_MINUTE
    cutoffs = set(reference['origin_cutoff_ns'].tolist())
    event_rows, count_rows, summary_rows, primary_episodes = [], [], [], []
    for threshold_record in thresholds:
        quantile, threshold = threshold_record['quantile'], threshold_record['threshold_kwh_per_15min']
        episodes = build_episodes(times, values, threshold, step_ns)
        for episode in episodes:
            episode['eligible'] = not episode['left_censored'] and history_eligible(episode['onset_ns'], cutoffs, config['episode_history_minutes'] * NS_PER_MINUTE, step_ns)
            episode['exclusion_reason'] = 'onset_left_censored' if episode['left_censored'] else ('missing_full_60min_origin_history' if not episode['eligible'] else '')
        if quantile == config['primary_quantile']:
            primary_episodes = episodes
        for model in config['models']:
            for seed in config['seeds']:
                arrays = loaded[(model, seed, 'test')]
                alarms = arrays['y_pred'].sum(axis=-1, dtype=np.float64) > threshold
                lead_times = []
                for episode in episodes:
                    match = earliest_warning(episode, arrays['origin_cutoff_ns'], arrays['target_timestamps_ns'], alarms) if episode['eligible'] else None
                    lead = (episode['onset_ns'] - match['issue_ns']) / NS_PER_MINUTE if match else None
                    if lead is not None:
                        lead_times.append(lead)
                    event_rows.append(dict(quantile=quantile, threshold=threshold, model=model, seed=seed, **episode,
                                           onset_utc=timestamp_text(episode['onset_ns']), onset_local=timestamp_text(episode['onset_ns'], config['timezone']),
                                           detected=match is not None if episode['eligible'] else None,
                                           first_warning_issue_ns=match['issue_ns'] if match else None,
                                           first_warning_target_ns=match['target_ns'] if match else None,
                                           first_warning_horizon_step=match['horizon_step'] if match else None, lead_minutes_conditional=lead))
                eligible = sum(e['eligible'] for e in episodes)
                count_rows.append(dict(quantile=quantile, model=model, seed=seed, total_episodes=len(episodes), eligible=eligible,
                                       excluded=len(episodes)-eligible, left_censored=sum(e['left_censored'] for e in episodes),
                                       right_censored=sum(e['right_censored'] for e in episodes), detected=len(lead_times), missed=eligible-len(lead_times),
                                       detection_rate=len(lead_times)/eligible if eligible else float('nan'),
                                       lead_mean_detected_only=float(np.mean(lead_times)) if lead_times else float('nan'),
                                       lead_median_detected_only=float(np.median(lead_times)) if lead_times else float('nan'),
                                       lead_min_detected_only=min(lead_times) if lead_times else float('nan'),
                                       lead_max_detected_only=max(lead_times) if lead_times else float('nan')))
        for model in config['models']:
            group = [r for r in count_rows if r['quantile'] == quantile and r['model'] == model]
            row = dict(quantile=quantile, model=model, total_episodes=len(episodes), eligible=sum(e['eligible'] for e in episodes), excluded=sum(not e['eligible'] for e in episodes))
            for name in ('detected', 'missed', 'detection_rate', 'lead_mean_detected_only', 'lead_median_detected_only'):
                mean, sd, defined = complete_summary(np.array([g[name] for g in group]))
                row.update({name+'_mean': mean, name+'_sample_sd': sd, name+'_defined_seeds': defined})
            summary_rows.append(row)
    return event_rows, count_rows, summary_rows, primary_episodes


def example_tables(loaded: dict, unique_truth: dict, episodes: list[dict], threshold: float, config: dict, output: Path) -> dict:
    """固定第一个合格事件及 onset-45min 原点；三种子均值仅用于展示。"""
    eligible = [e for e in episodes if e['eligible']]
    metadata = dict(selection='first_chronological_eligible_test_episode', selection_uses_predictions=False,
                    origin_offset_minutes=config['example_origin_before_onset_minutes'], target_timestamp_shift_applied=False)
    if not eligible:
        metadata.update(status='no_eligible_episode', reason='valid_no_signal_or_no_full_history_outcome')
        write_csv(output / 'first_example.csv', [], ['model', 'seed', 'origin_index', 'origin_cutoff_ns', 'horizon_step', 'horizon_minutes', 'target_timestamps_ns', 'y_true_sum', 'y_pred_sum'])
        write_json(output / 'first_example.json', metadata)
        return metadata
    episode = eligible[0]
    origin_cutoff = episode['onset_ns'] - config['example_origin_before_onset_minutes'] * NS_PER_MINUTE
    step_ns = config['step_minutes'] * NS_PER_MINUTE
    forecast_rows, node_rows, mean_rows = [], [], []
    for model in config['models']:
        for seed in config['seeds']:
            arrays = loaded[(model, seed, 'test')]
            positions = np.flatnonzero(arrays['origin_cutoff_ns'] == origin_cutoff)
            if len(positions) != 1:
                raise ValueError('fixed example origin missing/nonunique despite eligibility')
            index = int(positions[0])
            for horizon in range(config['expected_horizons']):
                target_ns = int(arrays['target_timestamps_ns'][index, horizon])
                truth_sum, pred_sum = float(arrays['y_true'][index, horizon].sum()), float(arrays['y_pred'][index, horizon].sum())
                in_episode = episode['onset_ns'] <= target_ns <= episode['last_target_ns']
                row = dict(model=model, seed=seed, origin_index=int(arrays['origins'][index]), origin_cutoff_ns=origin_cutoff,
                           origin_cutoff_utc=timestamp_text(origin_cutoff), origin_cutoff_local=timestamp_text(origin_cutoff, config['timezone']),
                           horizon_step=horizon+1, horizon_minutes=(horizon+1)*config['step_minutes'],
                           actual_target_start_lead_minutes=(target_ns-origin_cutoff)/NS_PER_MINUTE,
                           target_timestamps_ns=target_ns, target_utc=timestamp_text(target_ns), target_local=timestamp_text(target_ns, config['timezone']),
                           target_interval_end_ns=target_ns+step_ns, episode_onset_ns=episode['onset_ns'], y_true_sum=truth_sum, y_pred_sum=pred_sum,
                           threshold=threshold, actual_crossing=truth_sum>threshold, predicted_crossing=pred_sum>threshold,
                           target_in_selected_episode=in_episode, credited_pre_onset_warning=bool(pred_sum>threshold and in_episode and origin_cutoff<episode['onset_ns']))
                forecast_rows.append(row)
                for node_index, node_id in enumerate(arrays['node_ids']):
                    node_rows.append(dict(model=model, seed=seed, origin_index=row['origin_index'], horizon_step=horizon+1, node_id=str(node_id),
                                          origin_cutoff_ns=origin_cutoff, target_timestamps_ns=target_ns,
                                          y_true=float(arrays['y_true'][index, horizon, node_index]), y_pred=float(arrays['y_pred'][index, horizon, node_index])))
    for model in config['models']:
        for horizon in range(1, config['expected_horizons'] + 1):
            group = [r for r in forecast_rows if r['model'] == model and r['horizon_step'] == horizon]
            if len(group) != len(config['seeds']):
                raise ValueError('example seed group incomplete')
            if len({r['target_timestamps_ns'] for r in group}) != 1 or len({r['y_true_sum'] for r in group}) != 1:
                raise ValueError('example display truth/time mismatch')
            mean, sd, _ = complete_summary(np.array([r['y_pred_sum'] for r in group]))
            first = group[0]
            mean_rows.append(dict(model=model, horizon_step=horizon, horizon_minutes=first['horizon_minutes'], seeds=len(group),
                                  origin_index=first['origin_index'], origin_cutoff_ns=origin_cutoff,
                                  origin_cutoff_local=first['origin_cutoff_local'], target_timestamps_ns=first['target_timestamps_ns'],
                                  target_local=first['target_local'], target_interval_end_ns=first['target_interval_end_ns'],
                                  actual_target_start_lead_minutes=first['actual_target_start_lead_minutes'],
                                  episode_onset_ns=episode['onset_ns'], y_true_sum=first['y_true_sum'],
                                  y_pred_sum_mean_display_only=mean, y_pred_sum_sample_sd_display_only=sd,
                                  threshold=threshold, target_in_selected_episode=first['target_in_selected_episode'],
                                  display_only_not_used_for_scoring=True))
    times, values = unique_truth['test']
    context_mask = (times >= episode['onset_ns']-120*NS_PER_MINUTE) & (times <= episode['interval_end_ns']+120*NS_PER_MINUTE)
    context_rows = [dict(target_timestamps_ns=int(t), target_utc=timestamp_text(t), target_local=timestamp_text(t, config['timezone']),
                         y_true_sum=float(v), threshold=threshold, actual_crossing=v>threshold,
                         in_selected_episode=bool(episode['onset_ns']<=t<=episode['last_target_ns'])) for t,v in zip(times[context_mask], values[context_mask])]
    write_csv(output / 'first_example.csv', forecast_rows)
    write_csv(output / 'first_example_seed_mean_display_only.csv', mean_rows)
    write_csv(output / 'first_example_node_values.csv', node_rows)
    write_csv(output / 'first_example_truth_context.csv', context_rows)
    metadata.update(status='complete', episode=episode, origin_cutoff_ns=origin_cutoff,
                    origin_cutoff_utc=timestamp_text(origin_cutoff), origin_cutoff_local=timestamp_text(origin_cutoff, config['timezone']),
                    any_fixed_origin_target_in_episode=any(r['target_in_selected_episode'] for r in forecast_rows),
                    display_policy=config['example_display_policy'], time_index_correction=config['time_index_correction'],
                    timing_note='Source-index correction within authorized analysis: same first eligible episode, onset-45min forecasts onset-45/-30/-15/0min. Final slot contains onset. Max real onset lead is 45min.')
    write_json(output / 'first_example.json', metadata)
    return metadata


def environment_snapshot() -> dict[str, Any]:
    """只记录必要版本及 NumPy 配置，不导出含凭据的整个环境变量。"""
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        np.show_config()
    return dict(python=sys.version, executable=sys.executable, numpy=np.__version__, platform=platform.platform(),
                machine=platform.machine(), cpu_count=os.cpu_count(), numpy_build_configuration=buffer.getvalue(),
                execution_target='local_mac_cpu_archived_analysis', pandas_required=False, training_performed=False)


def render_report(config: dict, audit: dict, thresholds: list[dict], summaries: list[dict], bootstrap: list[dict], events: list[dict], example: dict) -> str:
    """生成计算交接报告；区分描述性结果、时间约束和不能支持的论文主张。"""
    lines = ['# SG-EXP-021 归档预测应用计算交接', '', '状态：completed_unreviewed；需主代理和独立评审复核后才能整合论文。', '',
             '## 不变范围', '', config['scope'], '', '18 个源文件只读；没有训练、预测后处理、模型/阈值选优或 DOCX/图件写入。', '',
             '## 时间语义关键限制', '',
             '导出代码使用未来片左端点 `target_timestamps_ns`，而 cutoff 是历史最后一片右端点。',
             '归档四步的目标左端点提前量为 0/15/30/45 min；15/30/45/60 是四个未来片右端点的名义步长。',
             '原始时间戳未平移。严格未来左端点 15/30/45/60 合同未通过；不能宣称最长 60 min 的事件起点前预警。',
             '事件 onset 以左端点为准，issue 必须严格小于 onset，且预测目标必须落在同一事件。',
             '主 agent 基于源时间索引实施 metadata-only 纠错：事件仍为最早 eligible，展示原点改 onset−45min（最早能包含 onset 的归档原点）。',
             '展示导出三种子均值，不用于评分；全部分类和事件评分仍逐种子。完整 60min 原点历史资格检查不等于有 60min 起点前预测能力。', '',
             '## 审计', '', f"输入文件：{len(audit['sources'])}；跨方法/种子的 origins/node_ids/time/y_true 完全一致。",
             '重叠目标逐节点真值一致，校准与测试目标时间不相交；负预测保留，无裁剪。', '',
             '## 冻结阈值', '', '校准唯一目标时点的十节点真值总量 → np.quantile(method=linear)；严格 >。', '']
    for t in thresholds:
        lines.append(f"- q={t['quantile']}: {t['threshold_kwh_per_15min']:.17g} kWh/15min；calibration unique n={t['calibration_unique_targets']}；test unique exceedances={t['test_unique_exceedances']}/{t['test_unique_targets']}")
    lines.extend(['', '## 主阈值 pooled test（均值±样本SD）', '', '| model | recall | precision | FPR | F1 |', '|---|---:|---:|---:|---:|'])
    for r in summaries:
        if r['quantile'] == config['primary_quantile'] and r['split'] == 'test' and r['horizon_minutes'] == 'pooled':
            cells = [f"{r[m+'_mean']:.8f} ± {r[m+'_sample_sd']:.8f}" for m in METRIC_NAMES]
            lines.append('| '+r['model']+' | '+' | '.join(cells)+' |')
    lines.extend(['', '## 主阈值 pooled 日配对 bootstrap 差异', '', '先每个种子计算指标，再取三种子均值差；2000 次固定日期抽样，所有模型共享日期 multiplicity。', '',
                  '| difference | metric | point | percentile 95% CI |', '|---|---|---:|---|'])
    for r in bootstrap:
        if r['method'] == 'paired_calendar_day' and r['quantile'] == config['primary_quantile'] and r['horizon_minutes'] == 'pooled':
            lines.append(f"| {r['comparison']} | {r['metric']} | {r['point_difference']:.8f} | [{r['ci_lower']:.8f}, {r['ci_upper']:.8f}] |")
    lines.extend(['', '七日非循环移动块为描述性敏感性；不进行多重比较校正或显著性升级。', '', '## 主阈值事件检测', '',
                  '| model | eligible/excluded | detected mean | missed mean | lead mean detected only |', '|---|---|---:|---:|---:|'])
    for r in events:
        if r['quantile'] == config['primary_quantile']:
            lines.append(f"| {r['model']} | {r['eligible']}/{r['excluded']} | {r['detected_mean']:.8f} | {r['missed_mean']:.8f} | {r['lead_mean_detected_only_mean']:.8f} min |")
    lines.extend(['', '未检测事件不把提前量填成零；提前量只条件于命中。所有事件及删失/排除原因见 episodes.csv。', '',
                  '## 固定示例', '', json.dumps(clean_json(example), ensure_ascii=False, indent=2), '',
                  '## 交接与不可支持主张', '',
                  '技能约束：先保留审计、机器可读数值、原始输入哈希和描述性不确定性，再由主代理决定证据提升。',
                  '主代理可使用 metrics_summary.csv、bootstrap_summary.csv、episode_summary.csv 与 first_example*.csv 作表格/图件；本任务不画出版图。',
                  '待独立复核：时间语义/事件资格、bootstrap 种子均值定义、固定示例、阈值去重、未定义分母。',
                  '登记交接目标：experiment-registry、experiment-reports、data-quality-report、metric-diagnostics、material-passport；仓库尚未写入。',
                  '不支持：整站总负荷、实测功率、变压器过载、成本节约、部署验证、跨站泛化、MRG 普遍优于 AGCRN、统计显著性。',
                  '90% 与 97.5% 是预指定描述性敏感性，不能据此换主阈值；旧 target_event/rule_trigger 未作为阈值预警真值。',
                  '归档的 event-time 行为/日历输入沿用 SG-EXP-019 证据，没有以本脚本重新证明实时标签可用性。', '',
                  '## 问题清单', ''])
    for issue in audit['issues']:
        lines.append(f"- {issue['severity']} {issue['code']}: {issue['message']}")
    return '\n'.join(lines) + '\n'


def check_config(config: dict[str, Any]) -> None:
    """验证本协议不可调参字段，路径可移动但统计设计不自动改变。"""
    frozen = dict(models=['mrg_full', 'tcn_wide', 'agcrn_full'], seeds=[2024, 2025, 2026], splits=['calibration', 'test'],
                  expected_horizons=4, expected_nodes=10, step_minutes=15, primary_quantile=.95,
                  sensitivity_quantiles=[.9, .975], quantile_method='linear', crossing_operator='>',
                  bootstrap_replicates=2000, bootstrap_seed=20261002, timezone='America/Los_Angeles',
                  moving_block_days=7, episode_history_minutes=60, example_origin_before_onset_minutes=45,
                  episode_timestamp_basis='archived_target_left_endpoint')
    for key, expected in frozen.items():
        if config.get(key) != expected:
            raise ValueError(f'frozen protocol mismatch: {key}={config.get(key)!r}, expected {expected!r}')


def main() -> int:
    """执行完整只读分析，失败保留审计；新输出目录拒绝覆盖旧工件。"""
    # ========== 阶段 1：冻结合同、独立测试与环境 ==========
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=Path(__file__).with_name('config_frozen.json'))
    parser.add_argument('--source-root', type=Path, help='仅替换归档根路径，不改变统计协议')
    parser.add_argument('--out', type=Path, default=Path(__file__).with_name('results_final'))
    parser.add_argument('--test-file', type=Path, default=Path(__file__).with_name('test_analyze_demand_warning.py'),
                        help='可移植测试文件路径；默认与脚本同目录，可显式传 repo/tests/test_demand_warning.py')
    args = parser.parse_args()
    config_path = args.config.resolve()
    config = json.loads(config_path.read_text(encoding='utf-8'))
    check_config(config)
    source_root = (args.source_root or Path(config['source_root'])).resolve()
    output = args.out.resolve()
    if output.exists():
        raise ValueError(f'output already exists; use a new --out directory: {output}')
    # 防止将默认/误传输出置于源归档，输入目录保持只读。
    if output == source_root or source_root in output.parents:
        raise ValueError('output must not be inside source archive')
    output.mkdir(parents=True)
    script_path = Path(__file__).resolve()
    test_file = args.test_file.resolve()
    if not test_file.is_file():
        raise ValueError(f'test file missing: {test_file}')
    config['source_root'] = str(source_root)
    audit = dict(status='running', sources=[], issues=[], command=shlex.join([sys.executable, str(script_path)]+sys.argv[1:]),
                 started_utc=datetime.now(timezone.utc).isoformat(), output=str(output), source_root=str(source_root),
                 script_sha256=sha256_file(script_path), config_file_sha256=sha256_file(config_path),
                 test_file_path=str(test_file), test_file_sha256=sha256_file(test_file))
    write_json(output / 'config_resolved.json', config)
    write_json(output / 'environment.json', environment_snapshot())
    try:
        test_environment = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
        previous_pythonpath = test_environment.get('PYTHONPATH', '')
        test_environment['PYTHONPATH'] = str(script_path.parent) + (os.pathsep + previous_pythonpath if previous_pythonpath else '')
        test_command = [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', str(test_file.parent), '-p', test_file.name, '-v']
        tests = subprocess.run(test_command,
                               cwd=script_path.parent, env=test_environment, capture_output=True, text=True, check=False)
        (output / 'tests.log').write_text(tests.stdout + tests.stderr, encoding='utf-8')
        audit['tests'] = dict(command=shlex.join(test_command), pythonpath_script_directory=str(script_path.parent), exit_code=tests.returncode)
        if tests.returncode:
            raise ValueError('unit tests failed; see tests.log')
        code_relative_paths = ['src/evcs_station_graph/eventtime/runner.py', 'src/evcs_station_graph/eventtime/data.py',
                               'docs/development/code-style-and-change-protocol.md', 'docs/thesis/experiment-reports/EXP-019-eventtime-v1-phase2.md']
        audit['source_code_conventions_provenance'] = []
        for parent in source_root.parents:
            if (parent / code_relative_paths[0]).is_file():
                audit['source_code_conventions_provenance'] = [dict(path=str(parent / relative), sha256=sha256_file(parent / relative)) for relative in code_relative_paths if (parent / relative).is_file()]
                break
        # ========== 阶段 2：归档输入审计、校准去重与冻结阈值 ==========
        loaded, unique_truth = load_archives(source_root, config, audit)
        temporal = audit['sources'][0]['time_semantics']
        audit['temporal_contract'] = temporal
        if not temporal['strict_future_target_start_contract']:
            audit['issues'].append(dict(severity='WARNING', code='TARGET_LEFT_ENDPOINT_NOT_STRICT_FUTURE_15_60',
                                        message='Actual archived start leads 0/15/30/45min. Nominal 15/30/45/60 labels describe interval endpoints, not onset lead. Raw keys preserved.'))
            print('WARNING: archived target-start leads 0/15/30/45min; no timestamp shift. Strict future 15/30/45/60 start contract FAILED.', flush=True)
        audit['issues'].append(dict(severity='LIMITATION', code='RETROSPECTIVE_PROXY_SELECTED_NODES', message=config['scope']))
        audit['issues'].append(dict(severity='LIMITATION', code='SHARED_HISTORICAL_TEST', message='Same historical period, only three seeds; bootstrap is descriptive and not an independent future test or multiplicity-adjusted significance claim.'))
        negative_count = sum(s['negative_prediction_values'] for s in audit['sources'])
        audit['issues'].append(dict(severity='INFO', code='RAW_NEGATIVE_PREDICTIONS_PRESERVED', message=f'{negative_count} node-level negative values across 18 inputs; no clipping.'))
        thresholds = []
        cal_times, cal_values = unique_truth['calibration']
        test_times, test_values = unique_truth['test']
        for q in [config['primary_quantile']] + config['sensitivity_quantiles']:
            threshold = float(np.quantile(cal_values, q, method=config['quantile_method']))
            thresholds.append(dict(quantile=q, role='primary' if q==config['primary_quantile'] else 'prespecified_descriptive_sensitivity',
                                   threshold_kwh_per_15min=threshold, calibration_unique_targets=len(cal_times), test_unique_targets=len(test_times),
                                   calibration_unique_exceedances=int(np.sum(cal_values>threshold)), test_unique_exceedances=int(np.sum(test_values>threshold)),
                                   calibration_min=float(cal_values.min()), calibration_max=float(cal_values.max()),
                                   test_min=float(test_values.min()), test_max=float(test_values.max()), operator='>', method='linear'))
        write_json(output / 'thresholds.json', thresholds)
        write_csv(output / 'thresholds.csv', thresholds)
        primary = thresholds[0]
        calibration_prevalence = primary['calibration_unique_exceedances'] / primary['calibration_unique_targets']
        test_prevalence = primary['test_unique_exceedances'] / primary['test_unique_targets']
        audit['primary_label_prevalence'] = dict(calibration_unique_rate=calibration_prevalence, test_unique_rate=test_prevalence,
                                                difference=test_prevalence-calibration_prevalence)
        audit['issues'].append(dict(severity='LIMITATION', code='CALIBRATION_TEST_EXCEEDANCE_SHIFT',
                                    message=f'Primary frozen threshold exceedance: calibration={calibration_prevalence:.8%}, test={test_prevalence:.8%}. A calibration 95th percentile does not imply a test 5% event rate.'))
        for split, (times, values) in unique_truth.items():
            write_csv(output / f'unique_truth_{split}.csv', [dict(target_timestamps_ns=int(t), target_utc=timestamp_text(t), y_true_sum=float(v)) for t,v in zip(times, values)])
        print(f'Audited {len(loaded)} files; unique calibration/test targets {len(cal_times)}/{len(test_times)}; primary threshold {thresholds[0]["threshold_kwh_per_15min"]:.17g}', flush=True)
        # ========== 阶段 3：分类、日期重采样与事件匹配 ==========
        metrics, summaries = classification_tables(loaded, thresholds, config)
        write_csv(output / 'metrics_per_run.csv', metrics)
        write_csv(output / 'metrics_summary.csv', summaries)
        bootstrap, bootstrap_diagnostics = bootstrap_tables(loaded, thresholds, config, output)
        audit['bootstrap_diagnostics'] = bootstrap_diagnostics
        event_rows, event_counts, event_summaries, primary_episodes = episode_tables(loaded, unique_truth, thresholds, config)
        write_csv(output / 'episodes.csv', event_rows, list(event_rows[0]) if event_rows else ['quantile','model','seed','episode_id','onset_ns','eligible','detected','lead_minutes_conditional'])
        write_csv(output / 'episode_counts.csv', event_counts)
        write_csv(output / 'episode_summary.csv', event_summaries)
        write_json(output / 'episode_counts.json', dict(per_run=event_counts, summaries=event_summaries))
        example = example_tables(loaded, unique_truth, primary_episodes, thresholds[0]['threshold_kwh_per_15min'], config, output)
        if example.get('status') == 'complete' and not example['any_fixed_origin_target_in_episode']:
            audit['issues'].append(dict(severity='WARNING', code='FIXED_EXAMPLE_HAS_NO_EPISODE_TARGET',
                                        message='First eligible event retained, but the requested fixed example origin has no target inside the episode.'))
        for row in event_counts:
            if row['eligible'] == 0 or row['detected'] == 0:
                audit['issues'].append(dict(severity='VALID_NO_SIGNAL', code='NO_ELIGIBLE_OR_NO_DETECTED_EVENTS', message=f'{row["model"]} seed={row["seed"]} q={row["quantile"]}: eligible={row["eligible"]}, detected={row["detected"]}; conditional lead remains undefined.'))
        undefined_metrics = sum(not np.isfinite(row[metric]) for row in metrics for metric in METRIC_NAMES)
        audit['undefined_classification_metric_cells'] = undefined_metrics
        if undefined_metrics:
            audit['issues'].append(dict(severity='VALID_NO_SIGNAL', code='UNDEFINED_CLASSIFICATION_DENOMINATORS', message=f'{undefined_metrics} zero-denominator metric cells; null/blank, never substituted by favorable scores.'))
        # ========== 阶段 4：源不变检查、可追踪交接与 manifest ==========
        for record in audit['sources']:
            if sha256_file(Path(record['path'])) != record['sha256']:
                raise ValueError(f'source changed during computation: {record["path"]}')
            record['unchanged_after_run'] = True
        for record in audit['source_code_conventions_provenance']:
            if sha256_file(Path(record['path'])) != record['sha256']:
                raise ValueError(f'source convention/code changed during computation: {record["path"]}')
        if sha256_file(script_path) != audit['script_sha256'] or sha256_file(config_path) != audit['config_file_sha256'] or sha256_file(test_file) != audit['test_file_sha256']:
            raise ValueError('script/config/test file changed during run')
        audit.update(status='completed_unreviewed', input_integrity_pass=True, strict_future_15_60_target_start_contract_pass=temporal['strict_future_target_start_contract'],
                     prospective_60min_onset_warning_claim_supported=False, completed_utc=datetime.now(timezone.utc).isoformat())
        write_json(output / 'audit.json', audit)
        (output / 'report.md').write_text(render_report(config, audit, thresholds, summaries, bootstrap, event_summaries, example), encoding='utf-8')
        artifact_hashes = {str(p.relative_to(output)): sha256_file(p) for p in sorted(output.rglob('*')) if p.is_file()}
        write_json(output / 'manifest.json', dict(experiment_id=config['experiment_id'], status=audit['status'], source_sha256s={s['relative_path']:s['sha256'] for s in audit['sources']},
                                                 script_sha256=audit['script_sha256'], config_file_sha256=audit['config_file_sha256'], test_file_path=str(test_file), test_file_sha256=audit['test_file_sha256'],
                                                 artifact_sha256s=artifact_hashes, command=audit['command'], input_integrity_pass=True, independent_review_pending=True))
        for row in summaries:
            if row['quantile']==config['primary_quantile'] and row['split']=='test' and row['horizon_minutes']=='pooled':
                print(json.dumps(clean_json(row), ensure_ascii=False), flush=True)
        print(f'Completed; artifacts: {output}', flush=True)
        return 0
    except Exception as error:
        # 只捕获以写出明确失败审计，重新抛出，不吞异常或降级为成功。
        audit.update(status='failed', error_type=type(error).__name__, error=str(error), failed_utc=datetime.now(timezone.utc).isoformat())
        write_json(output / 'audit.json', audit)
        raise


if __name__ == '__main__':
    raise SystemExit(main())
