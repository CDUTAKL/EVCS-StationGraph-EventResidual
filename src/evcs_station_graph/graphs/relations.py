"""站内充电单元统计关系图。

这里的“图”描述节点代理负荷或事件状态的统计关联，不表示电气接线、物理距离
或控制关系。所有关系矩阵只允许使用训练阶段数据构建。
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class RelationSet:
    """三类站内充电桩行为交互关系矩阵。

    所有矩阵仅使用训练期数据构建，验证/测试集不参与计算。
    每类图独立完成 top-k 稀疏化和对称归一化，不预先融合——
    图模型通过可学习权重 β_r 在消息传递阶段融合多关系信息。
    """

    load: np.ndarray       # A_load：负荷耦合强度关系（abs(corr)，不区分正负方向）
    event: np.ndarray      # A_event：充电行为共现（接入/离站/活跃变化余弦相似度）
    pattern: np.ndarray    # A_pattern：时间模式相似度（固定相位 96 步窗口轮廓距离）

    def as_dict(self) -> dict[str, np.ndarray]:
        return {"load": self.load, "event": self.event, "pattern": self.pattern}

    def as_list(self) -> list[np.ndarray]:
        """返回固定顺序的三类关系矩阵列表，供模型逐关系消息传递。"""
        return [self.load, self.event, self.pattern]


def build_relation_set(
    train_features: np.ndarray,
    train_targets: np.ndarray,
    feature_names: tuple[str, ...],
    *,
    top_k: int = 5,
) -> RelationSet:
    """构建三类训练期候选关系矩阵，每类独立处理不预先融合。

    参数
    ----
    train_features:
        形状为 ``[T, N, F]``。
    train_targets:
        形状为 ``[T, N]``。
    top_k:
        每节点保留的最强邻居数。
    """
    if train_features.ndim != 3 or train_targets.ndim != 2:
        raise ValueError("训练特征或目标维度不正确")
    if train_features.shape[:2] != train_targets.shape:
        raise ValueError("训练特征与目标的时间、节点维不一致")

    feature_index = {name: index for index, name in enumerate(feature_names)}
    needed = {"access_count", "departure_count", "active_count"}
    missing = needed.difference(feature_index)
    if missing:
        raise ValueError(f"缺少构图特征：{sorted(missing)}")

    access = train_features[:, :, feature_index["access_count"]]
    departure = train_features[:, :, feature_index["departure_count"]]
    active = train_features[:, :, feature_index["active_count"]]

    # ---- 关系 1：负荷耦合强度关系（abs(corr)）----
    # 比较不同节点代理负荷变化的线性同步强度，度量耦合紧密度。
    # 取绝对值确保所有关系为非负——图模型通过消息聚合捕获耦合强度，
    # 不区分正负方向。负荷耦合强度关系不声称"正相关"或"同向相似性"。
    A_load = _safe_abs_corr(train_targets)
    A_load = sparsify_top_k(A_load, top_k)
    A_load = normalize_adjacency(A_load)

    # ---- 关系 2：充电行为共现（余弦相似度）----
    # 行为向量 = 接入数 + 离站数 + |活跃会话变化|，捕捉节点间
    # "是否在相近时段出现相似的充放电活动模式"。
    active_delta = np.abs(np.diff(active, axis=0, prepend=active[[0]]))
    event_signal = access + departure + active_delta
    A_event = _cosine_columns(event_signal)
    A_event = sparsify_top_k(A_event, top_k)
    A_event = normalize_adjacency(A_event)

    # ---- 关系 3：时间模式相似度（指数核距离）----
    # 比较节点日内平均负荷轮廓的形状相似性，而非逐点瞬时相关。
    # 捕捉"节点 A 和节点 B 在一天中是否具有相似的负荷形状"。
    A_pattern = _profile_similarity(train_targets)
    A_pattern = sparsify_top_k(A_pattern, top_k)
    A_pattern = normalize_adjacency(A_pattern)

    return RelationSet(load=A_load, event=A_event, pattern=A_pattern)


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
    """计算列之间的绝对皮尔逊相关系数（负荷耦合强度），安全处理常数列。

    使用中心化矩阵乘法 corr = (X-μ)ᵀ(X-μ) / (σ_i * σ_j) 计算相关系数。
    当某列为常数（σ→0）时，分母为零，在 where 条件中将其相关设为 0，
    避免 NaN 传播。取绝对值将相关系数转化为耦合强度（不区分正负方向），
    因为图消息传递以耦合强度而非相关性方向聚合邻居信息。
    """
    centered = values - values.mean(axis=0, keepdims=True)
    scale = np.sqrt(np.square(centered).sum(axis=0))
    denominator = scale[:, None] * scale[None, :]
    corr = centered.T @ centered
    corr = np.divide(corr, denominator, out=np.zeros_like(corr), where=denominator > 1e-12)
    corr = np.abs(corr)
    np.fill_diagonal(corr, 1.0)
    return corr.astype(np.float32)


def _cosine_columns(values: np.ndarray) -> np.ndarray:
    """计算列之间的余弦相似度矩阵。

    similarity = XᵀX / (‖col_i‖ * ‖col_j‖)，其中分母为零时设为 0。
    余弦相似度度量的是时序波形的形状相似性（方向一致），不受幅值影响——
    这意味着"两个节点的事件模式形状相似"即可获得高相似度，即使事件量级不同。
    """
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
    """根据训练期固定相位 96 步窗口轮廓构建相似度矩阵。

    方法：
    1. 将训练期数据按 96 步块切分（固定相位窗口，非自然日——审查 M-03，
       首时刻 11:00；所有节点同相位偏移，节点间距离结构仍有效），取块内平均值曲线
    2. 计算节点之间平均轮廓的欧氏距离
    3. 用指数核 exp(-distance/median_distance) 将距离转为相似度

    与 load_correlation 的区别：本方法捕捉"节点 A 和节点 B 在相同相位
    窗口内是否具有相似的负荷形状"（结构性），而非逐点瞬时同步（波动性）。
    因此互补——一个节点对可能瞬时相关弱但轮廓相似（或反之）。
    """
    usable = (len(values) // periods_per_day) * periods_per_day
    if usable < periods_per_day:
        return _safe_abs_corr(values)
    # 注意（审查 M-03，2026-08-01）：按数组起点切 96 步块，未按自然日时间戳对齐——
    # 数据集首时刻为 2018-04-25 11:00（非 00:00），"日内轮廓"实为固定相位的
    # 24h 窗口轮廓（所有节点同相位偏移，节点间距离结构仍有效）。论文表述用
    # "96 步窗口轮廓"而非"自然日轮廓"。
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
