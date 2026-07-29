"""验证集冻结的事件分流规则。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from evcs_station_graph.data.tensor import TensorBundle


@dataclass(frozen=True)
class FrozenEventRule:
    """按节点保存的事件分数阈值。"""

    thresholds: np.ndarray
    quantile: float
    score_definition: str


def visible_event_scores(bundle: TensorBundle, origins: np.ndarray) -> np.ndarray:
    """仅使用预测起点及其历史信息计算事件分数。"""
    feature_index = {name: index for index, name in enumerate(bundle.feature_names)}
    required = {"load", "access_count", "departure_count", "active_count"}
    missing = required.difference(feature_index)
    if missing:
        raise ValueError(f"缺少事件分数特征：{sorted(missing)}")

    load = bundle.features[:, :, feature_index["load"]]
    access = bundle.features[:, :, feature_index["access_count"]]
    departure = bundle.features[:, :, feature_index["departure_count"]]
    active = bundle.features[:, :, feature_index["active_count"]]
    previous = np.maximum(origins - 1, 0)
    load_scale = np.maximum(bundle.target_std, 1e-6)
    score = (
        access[origins]
        + departure[origins]
        + np.abs(active[origins] - active[previous])
        + np.abs(load[origins] - load[previous]) / load_scale[None, :]
    )
    return score.astype(np.float32)


def fit_frozen_event_rule(
    bundle: TensorBundle,
    *,
    quantile: float = 0.95,
) -> FrozenEventRule:
    """只在验证集上确定阈值，测试阶段不得更新。"""
    if not 0.0 < quantile < 1.0:
        raise ValueError("quantile 必须位于 (0, 1)")
    scores = visible_event_scores(bundle, bundle.split_origins["validation"])
    thresholds = np.quantile(scores, quantile, axis=0).astype(np.float32)
    return FrozenEventRule(
        thresholds=thresholds,
        quantile=quantile,
        score_definition="access+departure+abs(active_delta)+abs(load_delta)/train_std",
    )


def apply_frozen_event_rule(
    bundle: TensorBundle,
    origins: np.ndarray,
    rule: FrozenEventRule,
) -> np.ndarray:
    """应用已冻结阈值，返回 ``[样本, 节点]`` 触发矩阵。"""
    scores = visible_event_scores(bundle, origins)
    return scores >= rule.thresholds[None, :]
