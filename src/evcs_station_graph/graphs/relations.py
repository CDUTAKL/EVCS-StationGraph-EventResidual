"""站内充电单元统计关系图。

这里的“图”描述节点代理负荷或事件状态的统计关联，不表示电气接线、物理距离
或控制关系。所有关系矩阵只允许使用训练阶段数据构建。
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class RelationSet:
    """五类候选统计关系及其融合矩阵。"""

    current_event: np.ndarray
    historical_event: np.ndarray
    load_correlation: np.ndarray
    temporal_profile: np.ndarray
    fused: np.ndarray

    def as_dict(self) -> dict[str, np.ndarray]:
        return {
            "current_event": self.current_event,
            "historical_event": self.historical_event,
            "load_correlation": self.load_correlation,
            "temporal_profile": self.temporal_profile,
            "fused": self.fused,
        }


def build_relation_set(
    train_features: np.ndarray,
    train_targets: np.ndarray,
    feature_names: tuple[str, ...],
    *,
    top_k: int = 5,
    smoothing: float = 0.5,
) -> RelationSet:
    """构建五类训练期候选关系。

    参数
    ----
    train_features:
        形状为 ``[T, N, F]``。
    train_targets:
        形状为 ``[T, N]``。
    smoothing:
        融合图中负荷相关关系的权重，其余权重分配给事件和时间轮廓关系。
    """
    if train_features.ndim != 3 or train_targets.ndim != 2:
        raise ValueError("训练特征或目标维度不正确")
    if train_features.shape[:2] != train_targets.shape:
        raise ValueError("训练特征与目标的时间、节点维不一致")
    if not 0.0 <= smoothing <= 1.0:
        raise ValueError("smoothing 必须位于 [0, 1]")

    feature_index = {name: index for index, name in enumerate(feature_names)}
    needed = {"access_count", "departure_count", "active_count"}
    missing = needed.difference(feature_index)
    if missing:
        raise ValueError(f"缺少构图特征：{sorted(missing)}")

    access = train_features[:, :, feature_index["access_count"]]
    departure = train_features[:, :, feature_index["departure_count"]]
    active = train_features[:, :, feature_index["active_count"]]
    event_signal = access + departure

    # 当前事件关系：同一时间片内接入/离站事件的共现强度。
    current_event = _cosine_columns(event_signal)
    # 历史事件关系：活跃会话变化及事件历史的联合相关性。
    active_delta = np.diff(active, axis=0, prepend=active[[0]])
    historical_event = _safe_abs_corr(event_signal + np.abs(active_delta))
    # 历史负荷相关关系：训练期代理负荷的线性同步性。
    load_correlation = _safe_abs_corr(train_targets)
    # 时间轮廓关系：比较节点日内平均负荷曲线，而非逐点瞬时相关。
    temporal_profile = _profile_similarity(train_targets)

    current_event = sparsify_top_k(current_event, top_k)
    historical_event = sparsify_top_k(historical_event, top_k)
    load_correlation = sparsify_top_k(load_correlation, top_k)
    temporal_profile = sparsify_top_k(temporal_profile, top_k)

    auxiliary = (current_event + historical_event + temporal_profile) / 3.0
    fused = smoothing * load_correlation + (1.0 - smoothing) * auxiliary
    fused = sparsify_top_k(fused, top_k)
    return RelationSet(
        current_event=normalize_adjacency(current_event),
        historical_event=normalize_adjacency(historical_event),
        load_correlation=normalize_adjacency(load_correlation),
        temporal_profile=normalize_adjacency(temporal_profile),
        fused=normalize_adjacency(fused),
    )


def normalize_adjacency(adjacency: np.ndarray) -> np.ndarray:
    """加入自环并进行对称归一化。"""
    matrix = np.asarray(adjacency, dtype=np.float32)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError("邻接矩阵必须为方阵")
    matrix = np.maximum(matrix, matrix.T)
    np.fill_diagonal(matrix, 1.0)
    degree = matrix.sum(axis=1)
    inv_sqrt = np.power(np.maximum(degree, 1e-12), -0.5)
    normalized = inv_sqrt[:, None] * matrix * inv_sqrt[None, :]
    return normalized.astype(np.float32)


def sparsify_top_k(similarity: np.ndarray, top_k: int) -> np.ndarray:
    """每个节点仅保留最强的 ``top_k`` 个非自身关系。"""
    matrix = np.asarray(similarity, dtype=np.float32).copy()
    n_nodes = matrix.shape[0]
    if matrix.shape != (n_nodes, n_nodes):
        raise ValueError("相似度矩阵必须为方阵")
    k = min(max(int(top_k), 0), max(n_nodes - 1, 0))
    np.fill_diagonal(matrix, 0.0)
    if k == 0:
        return np.eye(n_nodes, dtype=np.float32)
    mask = np.zeros_like(matrix, dtype=bool)
    indices = np.argpartition(matrix, -k, axis=1)[:, -k:]
    rows = np.arange(n_nodes)[:, None]
    mask[rows, indices] = True
    matrix = np.where(mask, matrix, 0.0)
    matrix = np.maximum(matrix, matrix.T)
    np.fill_diagonal(matrix, 1.0)
    return matrix


def _safe_abs_corr(values: np.ndarray) -> np.ndarray:
    """计算列之间绝对相关系数，并处理常数列。"""
    centered = values - values.mean(axis=0, keepdims=True)
    scale = np.sqrt(np.square(centered).sum(axis=0))
    denominator = scale[:, None] * scale[None, :]
    corr = centered.T @ centered
    corr = np.divide(corr, denominator, out=np.zeros_like(corr), where=denominator > 1e-12)
    corr = np.abs(corr)
    np.fill_diagonal(corr, 1.0)
    return corr.astype(np.float32)


def _cosine_columns(values: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(values, axis=0)
    denominator = norms[:, None] * norms[None, :]
    similarity = values.T @ values
    similarity = np.divide(
        similarity,
        denominator,
        out=np.zeros_like(similarity),
        where=denominator > 1e-12,
    )
    np.fill_diagonal(similarity, 1.0)
    return similarity.astype(np.float32)


def _profile_similarity(values: np.ndarray, periods_per_day: int = 96) -> np.ndarray:
    """根据训练期日内平均轮廓构建相似度。"""
    usable = (len(values) // periods_per_day) * periods_per_day
    if usable < periods_per_day:
        return _safe_abs_corr(values)
    profile = values[:usable].reshape(-1, periods_per_day, values.shape[1]).mean(axis=0)
    centered = profile - profile.mean(axis=0, keepdims=True)
    distances = np.sqrt(
        np.square(centered[:, :, None] - centered[:, None, :]).mean(axis=0)
    )
    positive = distances[distances > 0]
    scale = float(np.median(positive)) if positive.size else 1.0
    similarity = np.exp(-distances / max(scale, 1e-6))
    np.fill_diagonal(similarity, 1.0)
    return similarity.astype(np.float32)
