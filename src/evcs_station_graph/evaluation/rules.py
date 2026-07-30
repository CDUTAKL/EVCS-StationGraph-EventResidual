"""验证集冻结的事件分流规则。

事件分数将接入、离站、活跃会话变化和负荷突变四个分量按训练集 per-node
标准差归一化后求和，使罕见事件自动获得高分，避免大量零值主导分位点。

阈值只在验证集非零事件分数上估计，完整验证集保留用于统计报告。

触发点通过**因果前向扩展**形成完整事件窗口：
- 每个触发点 t 仅向后延续 ``window_extension`` 个 15 分钟时间片，
  覆盖 t, t+1, ..., t+w，不向过去扩展（避免未来信息泄漏）；
- 相邻或重叠窗口自动合并；
- 扩展参数和阈值均在验证集确定并冻结，测试集只执行冻结规则；
- 另有 ``build_symmetric_event_windows`` 提供对称邻域 [t-w, t+w]，
  仅用于结果分析和可视化，不参与路径分流。
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from evcs_station_graph.data.tensor import TensorBundle


@dataclass(frozen=True)
class FrozenEventRule:
    """按节点保存的事件分数阈值、窗口扩展参数与归一化统计量。

    ``score_stats`` 中各键值均为形状 ``[N]`` 的 float32 数组：
    ``std_access``、``std_departure``、``std_active_delta``、``std_load_delta``。
    这些统计量只在训练集上计算一次。

    ``trigger_point_fraction`` 为阈值触发点占比（扩展前），
    ``event_window_fraction`` 为窗口扩展合并后的占比（扩展后）。
    两者均在验证集上估计。
    """

    thresholds: np.ndarray
    quantile: float
    score_definition: str
    window_extension: int = 0
    score_stats: dict = field(default_factory=dict)
    trigger_point_fraction: np.ndarray = field(
        default_factory=lambda: np.array([], dtype=np.float32)
    )
    event_window_fraction: np.ndarray = field(
        default_factory=lambda: np.array([], dtype=np.float32)
    )


def _compute_score_stats(bundle: TensorBundle) -> dict[str, np.ndarray]:
    """从训练集计算事件分量 per-node 标准差，用于分数归一化。"""
    train_end = int(bundle.split_origins["train"][-1])
    feature_index = {name: index for index, name in enumerate(bundle.feature_names)}
    required = {"load", "access_count", "departure_count", "active_count"}
    missing = required.difference(feature_index)
    if missing:
        raise ValueError(f"缺少事件分数特征：{sorted(missing)}")

    train_features = bundle.features[: train_end + 1]
    access = train_features[:, :, feature_index["access_count"]]
    departure = train_features[:, :, feature_index["departure_count"]]
    active = train_features[:, :, feature_index["active_count"]]
    load = train_features[:, :, feature_index["load"]]

    active_delta = np.abs(np.diff(active, axis=0, prepend=active[[0]]))
    load_delta = np.abs(np.diff(load, axis=0, prepend=load[[0]]))

    eps = 1e-8
    return {
        "std_access": np.maximum(access.std(axis=0).astype(np.float32), eps),
        "std_departure": np.maximum(departure.std(axis=0).astype(np.float32), eps),
        "std_active_delta": np.maximum(active_delta.std(axis=0).astype(np.float32), eps),
        "std_load_delta": np.maximum(load_delta.std(axis=0).astype(np.float32), eps),
    }


def visible_event_scores(
    bundle: TensorBundle,
    origins: np.ndarray,
    score_stats: dict[str, np.ndarray] | None = None,
) -> np.ndarray:
    """仅使用预测起点及其历史信息计算归一化事件分数。

    每个分量除以训练集 per-node 标准差，使不同量纲的分量可比，
    且罕见事件自动获得高分。
    """
    if score_stats is None:
        score_stats = _compute_score_stats(bundle)

    feature_index = {name: index for index, name in enumerate(bundle.feature_names)}
    load = bundle.features[:, :, feature_index["load"]]
    access = bundle.features[:, :, feature_index["access_count"]]
    departure = bundle.features[:, :, feature_index["departure_count"]]
    active = bundle.features[:, :, feature_index["active_count"]]
    previous = np.maximum(origins - 1, 0)

    score = (
        access[origins] / score_stats["std_access"][None, :]
        + departure[origins] / score_stats["std_departure"][None, :]
        + np.abs(active[origins] - active[previous])
        / score_stats["std_active_delta"][None, :]
        + np.abs(load[origins] - load[previous])
        / score_stats["std_load_delta"][None, :]
    )
    return score.astype(np.float32)


def fit_frozen_event_rule(
    bundle: TensorBundle,
    *,
    quantile: float = 0.95,
    window_extension: int = 2,
) -> FrozenEventRule:
    """只在验证集非零事件分数上确定阈值，测试阶段不得更新。

    阈值估计仅使用验证集中分数 > 0 的样本；完整验证集保留用于统计报告。
    若某节点无非零事件分数，则将对应阈值设为极大值（永不触发）。

    触发点按 ``window_extension`` 向前后扩展并合并相邻窗口，形成最终事件窗口。
    扩展参数与阈值均在验证集冻结，测试集只执行冻结规则。
    """
    if not 0.0 < quantile < 1.0:
        raise ValueError("quantile 必须位于 (0, 1)")
    if window_extension < 0:
        raise ValueError("window_extension 必须为非负整数")

    score_stats = _compute_score_stats(bundle)
    val_origins = bundle.split_origins["validation"]
    scores = visible_event_scores(bundle, val_origins, score_stats=score_stats)

    n_nodes = scores.shape[1]
    thresholds = np.zeros(n_nodes, dtype=np.float32)

    for node_idx in range(n_nodes):
        node_scores = scores[:, node_idx]
        nonzero = node_scores[node_scores > 0]
        if len(nonzero) > 0:
            thresholds[node_idx] = float(
                np.quantile(nonzero, quantile).astype(np.float32)
            )
        else:
            # 该节点在验证集中无任何非零事件分数，设为永不触发
            thresholds[node_idx] = np.finfo(np.float32).max

    # ---- 触发点占比（扩展前） ----
    triggered_count = (scores >= thresholds[None, :]).sum(axis=0)
    trigger_point_fraction = (
        triggered_count / max(len(val_origins), 1)
    ).astype(np.float32)

    # ---- 事件窗口占比（前向扩展，用于路径分流） ----
    # 注意：这里使用因果的前向扩展（t → t+w），与 apply_frozen_event_rule 一致。
    # 对称窗口 [t-w, t+w] 的占比由 build_symmetric_event_windows 另行计算，
    # 仅用于结果分析和可视化。
    T = len(bundle.timestamps_ns)
    full_triggers = np.zeros((T, n_nodes), dtype=bool)
    full_triggers[val_origins] = scores >= thresholds[None, :]

    if window_extension > 0:
        expanded = np.copy(full_triggers)
        for n in range(n_nodes):
            triggered_pos = np.where(full_triggers[:, n])[0]
            for t in triggered_pos:
                # 仅向后扩展：lo = t，hi = t + w + 1
                lo = t
                hi = min(T, t + window_extension + 1)
                expanded[lo:hi, n] = True
        event_window_fraction = expanded[val_origins].mean(axis=0).astype(np.float32)
    else:
        event_window_fraction = trigger_point_fraction.copy()

    return FrozenEventRule(
        thresholds=thresholds,
        quantile=quantile,
        window_extension=window_extension,
        score_definition=(
            "access/std_access + departure/std_departure + "
            "abs(active_delta)/std_active_delta + abs(load_delta)/std_load_delta; "
            "thresholds fit on non-zero validation scores only; "
            f"trigger points expanded forward +{window_extension}×15min (causal), "
            "adjacent windows merged"
        ),
        score_stats={
            key: value.tolist() if hasattr(value, "tolist") else value
            for key, value in score_stats.items()
        },
        trigger_point_fraction=trigger_point_fraction,
        event_window_fraction=event_window_fraction,
    )


def apply_frozen_event_rule(
    bundle: TensorBundle,
    origins: np.ndarray,
    rule: FrozenEventRule,
) -> np.ndarray:
    """应用已冻结阈值与窗口扩展规则，返回 ``[样本, 节点]`` 触发矩阵。

    阈值和窗口扩展参数均在验证集确定，测试集直接使用冻结规则，绝不重新计算。

    窗口扩展是**严格因果的**：触发点 t 的窗口仅覆盖 t, t+1, ..., t+w，
    不向过去扩展。这保证时刻 t-1 的模型在预测时不知道 t 时刻将发生事件，
    避免未来信息泄漏到训练和评价中。
    """
    # 重建 numpy 数组形式的 score_stats
    score_stats = {
        key: np.asarray(value, dtype=np.float32)
        for key, value in rule.score_stats.items()
    } if rule.score_stats else None
    scores = visible_event_scores(bundle, origins, score_stats=score_stats)
    raw = scores >= rule.thresholds[None, :]  # [O, N]

    if rule.window_extension <= 0:
        return raw

    # 将触发点映射到完整时间轴，仅向未来方向扩张
    T = len(bundle.timestamps_ns)
    N = len(bundle.node_ids)
    full = np.zeros((T, N), dtype=bool)
    full[origins] = raw

    w = rule.window_extension
    expanded = np.copy(full)
    for n in range(N):
        triggered_pos = np.where(full[:, n])[0]
        for t in triggered_pos:
            # 关键：lo = t（不从触发点向前扩展），仅向后延续 w 个时间片
            # 这样时刻 t-1 的预测起点不会被 t 时刻的事件标记为"事件路径"
            lo = t
            hi = min(T, t + w + 1)
            expanded[lo:hi, n] = True

    return expanded[origins]


def build_symmetric_event_windows(
    bundle: TensorBundle,
    origins: np.ndarray,
    rule: FrozenEventRule,
) -> np.ndarray:
    """构建对称事件邻域 ``[样本, 节点]``，用于画局部曲线和评价事件前后误差。

    与 ``apply_frozen_event_rule`` 不同，本函数使用对称窗口 [t-w, t+w]，
    覆盖事件发生前后的完整邻域。此函数仅用于结果分析和可视化，
    不得用于模型训练或路径分流（后者使用因果的 ``apply_frozen_event_rule``）。
    """
    score_stats = {
        key: np.asarray(value, dtype=np.float32)
        for key, value in rule.score_stats.items()
    } if rule.score_stats else None
    scores = visible_event_scores(bundle, origins, score_stats=score_stats)
    raw = scores >= rule.thresholds[None, :]

    if rule.window_extension <= 0:
        return raw

    T = len(bundle.timestamps_ns)
    N = len(bundle.node_ids)
    full = np.zeros((T, N), dtype=bool)
    full[origins] = raw

    w = rule.window_extension
    expanded = np.copy(full)
    for n in range(N):
        triggered_pos = np.where(full[:, n])[0]
        for t in triggered_pos:
            lo = max(0, t - w)
            hi = min(T, t + w + 1)
            expanded[lo:hi, n] = True

    return expanded[origins]
