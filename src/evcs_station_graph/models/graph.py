"""SG-EXP-003/004：两层多关系门控图卷积 + TCN 交错预测模型。

架构（SG-EXP-003 固定图）：
  TCN时间编码 → GCN1 → 图特征MLP精炼 → GCN2 → 跨层融合
  即 TCN1 → GatedGCN1（一阶邻居）→ GraphMLPRefine → GatedGCN2（二阶传播）
  → Skip Fusion(H0,H1,H2) → Head

注：图特征MLP精炼不是第二个时间卷积模块，因为时间维在TCN编码后已被压缩至
节点向量，MLP仅做节点特征的非线性变换（残差MLP），不含时序卷积操作。

架构（SG-EXP-004 自适应图）：
  在三类固定关系基础上增加节点嵌入学习的自适应关系，
  共四类关系参与多关系消息传递。
"""

from __future__ import annotations

import numpy as np
import torch
from torch import nn

from evcs_station_graph.models.common import (
    ForecastModel,
    ForecastOutput,
    sample_relation_keep_mask,
)
from evcs_station_graph.models.tcn import TemporalConvNet


# ========== 多关系门控图卷积层 ==========

class MultiRelationGatedGCN(nn.Module):
    """单层多关系门控图卷积。

    对每类关系独立做消息传递，通过可学习权重 β_r（Softmax 归一化）融合，
    再用门控机制选择性保留或抑制邻居信息。

    公式：
      M = Σ_r β_r · Â_r H W_r           （多关系消息聚合）
      G = σ(W_g [H ‖ M])                （门控信号）
      H̃ = G ⊙ M + (1-G) ⊙ H            （门控融合）
      H_out = LayerNorm(H + Dropout(H̃)) （残差 + 归一化）
    """

    def __init__(
        self,
        hidden_dim: int,
        num_relations: int,
        dropout: float = 0.1,
        relation_dropout: float = 0.0,
    ) -> None:
        super().__init__()
        # 每类关系独立的变换矩阵（无 bias，保持消息的线性组合性）
        self.W_r = nn.ModuleList([
            nn.Linear(hidden_dim, hidden_dim, bias=False)
            for _ in range(num_relations)
        ])
        # 门控：拼接自身和聚合消息后经 sigmoid
        self.W_gate = nn.Linear(hidden_dim * 2, hidden_dim)
        self.norm = nn.LayerNorm(hidden_dim)
        self.dropout = nn.Dropout(dropout)
        # 关系 dropout：训练时以概率 p 随机屏蔽整类关系（SG-EXP-006 敏感性实验）。
        # 0.0（默认）表示关闭，未配置该参数的实验行为与此前完全一致。
        self.relation_dropout = float(relation_dropout)

    def forward(
        self,
        H: torch.Tensor,
        adjacencies: list[torch.Tensor],
        relation_weights: torch.Tensor,
    ) -> torch.Tensor:
        """单层多关系门控图卷积前向。

        参数
        ----
        H:
            节点特征 [B, N, D]。
        adjacencies:
            归一化邻接矩阵列表，每项形状 [N, N]。
        relation_weights:
            原始关系权重（未归一化），将被 Softmax 归一化。
        """
        beta = torch.softmax(relation_weights, dim=0)  # [R]

        # ---- 关系 dropout（仅训练模式生效） ----
        # 随机屏蔽部分关系后对 β 重新归一化：被丢弃的关系本次前向贡献为 0，
        # 保留关系按比例分摊全部权重。这迫使模型不过度依赖单一关系，
        # 是 SG-EXP-006 relation_dropout 敏感性实验的实际作用点。
        # eval/测试模式下不采样，保证推理结果确定。
        if self.training and self.relation_dropout > 0.0:
            keep = sample_relation_keep_mask(
                beta.numel(), self.relation_dropout, beta.device,
            )
            beta = beta * keep
            beta = beta / beta.sum().clamp(min=1e-12)

        # 多关系消息聚合
        M = torch.zeros_like(H)
        for r, (adj, W) in enumerate(zip(adjacencies, self.W_r)):
            # einsum("nm,bmd->bnd")：邻接矩阵 A[n,m] 作为权重聚合节点 m 的隐表示
            neighbor_msg = torch.einsum("nm,bmd->bnd", adj, H)
            M = M + beta[r] * W(neighbor_msg)

        # 门控：学习每个节点在每个维度上保留多少邻居信息
        gate_input = torch.cat([H, M], dim=-1)  # [B, N, 2D]
        G = torch.sigmoid(self.W_gate(gate_input))  # [B, N, D]

        # 门控融合：G 趋近 1 → 信任邻居；G 趋近 0 → 保留自身
        H_tilde = G * M + (1.0 - G) * H

        # 残差连接 + LayerNorm（防止过平滑）
        return self.norm(H + self.dropout(H_tilde))


# ========== 站内图时空预测模型基类 ==========

class StationGraphForecast(ForecastModel):
    """TCN时间编码 → GCN1 → 图特征MLP精炼 → GCN2 → 跨层融合 预测模型（SG-EXP-003）。

    架构：
      TCN1 → GatedGCN1（一阶邻居）→ GraphMLPRefine（特征精炼）
      → GatedGCN2（二阶传播）→ Skip Fusion(H0,H1,H2) → Head

    关键设计决策：
    - TCN1 编码时间序列，将 ``[B,T,N,F]`` 压缩为 ``[B,N,D]`` 节点隐表示，
      此后时间维消失，后续模块均操作 ``[B,N,D]`` 张量。
    - GraphMLPRefine（即原 tcn2_refine）是一个残差MLP，做节点特征的非线性
      精炼，而非时序卷积——因为 TCN 编码后已无时间维度。
      不要将其误解为"第二个TCN模块"。
    - GCN1 和 GCN2 使用独立的关系权重参数（β_r 分别学习），
      因为一阶邻居与二阶传播后的信息需要不同的关系混合策略。
    - GCN1 和 GCN2 权重独立，因为它们处于不同跳数，
      一阶邻居信息与二阶传播后的信息需要不同的变换参数。
    - Skip Fusion 将 H0（纯时序）、H1（一阶空间）、H2（二阶空间）
      拼接后经线性层融合，保留不同抽象层次的信息。
    """

    def __init__(
        self,
        input_dim: int,
        horizon: int,
        num_nodes: int,
        num_relations: int,
        *,
        hidden_dim: int = 32,
        levels: int = 3,
        dropout: float = 0.1,
        relation_dropout: float = 0.0,
        relation_weights_gcn1: torch.Tensor | None = None,
        relation_weights_gcn2: torch.Tensor | None = None,
    ) -> None:
        super().__init__()
        # 共享 TCN 编码器
        self.tcn = TemporalConvNet(
            input_dim, horizon,
            hidden_dim=hidden_dim, levels=levels, dropout=dropout,
        )
        # 图模型只使用 tcn.encode（卷积编码），预测由外层 self.head 完成，
        # tcn.head 从不参与前向——删除以避免死参数混入参数量统计与优化器状态
        del self.tcn.head
        # 两层独立的门控图卷积（不同跳数，不同参数）
        self.gcn1 = MultiRelationGatedGCN(hidden_dim, num_relations, dropout, relation_dropout)
        self.gcn2 = MultiRelationGatedGCN(hidden_dim, num_relations, dropout, relation_dropout)
        # 图特征MLP精炼：残差MLP做节点特征的非线性变换
        # 重要：这不是第二个时序卷积模块。TCN1 已将时间维压缩到节点向量，
        # 此处仅做节点特征的非线性精炼（残差 MLP），无时序卷积操作。
        self.graph_mlp_refine = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim),
        )
        # Skip Fusion：拼接 H0/H1/H2 并压缩
        self.skip_fusion = nn.Linear(hidden_dim * 3, hidden_dim)
        self.skip_norm = nn.LayerNorm(hidden_dim)
        self.skip_activation = nn.GELU()
        self.skip_dropout = nn.Dropout(dropout)
        # 预测头
        self.head = nn.Linear(hidden_dim, horizon)
        self.latent_dim = hidden_dim
        self.horizon = horizon
        # 独立关系权重：GCN1 和 GCN2 各自学习关系混合比例 β_r
        # 两层权重均可独立获取梯度，不共享
        init_rw1 = relation_weights_gcn1 if relation_weights_gcn1 is not None else torch.zeros(num_relations)
        init_rw2 = relation_weights_gcn2 if relation_weights_gcn2 is not None else torch.zeros(num_relations)
        self.relation_weights_gcn1 = nn.Parameter(init_rw1)
        self.relation_weights_gcn2 = nn.Parameter(init_rw2)

    def encode(self, x: torch.Tensor) -> torch.Tensor:
        """交错编码：TCN1→GCN1→GraphMLPRefine→GCN2→Skip→[B,N,D]。

        调用方通过 ``_get_relation_weights_gcn1()`` / ``_get_relation_weights_gcn2()``
        提供两套独立的关系权重，子类可覆写以支持不同的初始化策略。
        """
        # ---- TCN1：纯时序编码（各节点独立） ----
        h0 = self.tcn.encode(x)  # [B, N, D]

        adjacencies = self._get_adjacencies()

        # ---- GCN1：一阶邻居空间聚合（使用 GCN1 独立关系权重） ----
        h1 = self.gcn1(h0, adjacencies, self._get_relation_weights_gcn1())  # [B, N, D]

        # ---- GraphMLPRefine：图增强特征精炼 ----
        # 残差连接保证即使图信息无帮助，模型仍可回退到纯时序
        h1_refined = h1 + self.graph_mlp_refine(h1)

        # ---- GCN2：二阶空间传播（使用 GCN2 独立关系权重） ----
        h2 = self.gcn2(h1_refined, adjacencies, self._get_relation_weights_gcn2())  # [B, N, D]

        # ---- Skip Fusion：H0(时序) + H1(一阶空间) + H2(二阶空间) ----
        h_fused = self.skip_fusion(torch.cat([h0, h1, h2], dim=-1))
        h_fused = self.skip_norm(h_fused)
        return self.skip_dropout(self.skip_activation(h_fused))

    def forecast_from_latent(self, latent: torch.Tensor) -> torch.Tensor:
        return self.head(latent).permute(0, 2, 1).contiguous()

    def _get_adjacencies(self) -> list[torch.Tensor]:
        """返回参与消息传递的邻接矩阵列表。子类可覆写以追加自适应图。"""
        raise NotImplementedError

    def _get_relation_weights_gcn1(self) -> torch.Tensor:
        """返回 GCN1 层原始（未归一化）关系权重 β_r。"""
        return self.relation_weights_gcn1

    def _get_relation_weights_gcn2(self) -> torch.Tensor:
        """返回 GCN2 层原始（未归一化）关系权重 β_r。"""
        return self.relation_weights_gcn2


# ========== 固定图预测模型 ==========

class StaticGraphForecast(StationGraphForecast):
    """仅使用训练期构建的三类固定统计关系图（SG-EXP-003）。

    三类固定关系：
      - load：历史负荷相关性
      - event：充电行为共现
      - pattern：时间模式相似度

    三类关系的融合权重 β_r 是可学习参数，通过 Softmax 归一化。
    训练结束后 β_r 值直接反映"哪类关系对预测更重要"——
    这是可解释性的核心来源。
    """

    def __init__(
        self,
        input_dim: int,
        horizon: int,
        num_nodes: int,
        adjacencies: list[np.ndarray | torch.Tensor],
        *,
        hidden_dim: int = 32,
        levels: int = 3,
        dropout: float = 0.1,
        relation_dropout: float = 0.0,
    ) -> None:
        num_relations = len(adjacencies)
        super().__init__(
            input_dim, horizon, num_nodes, num_relations,
            hidden_dim=hidden_dim, levels=levels, dropout=dropout,
            relation_dropout=relation_dropout,
        )
        # 将三类固定邻接矩阵注册为 buffer（不参与梯度更新）
        for r, adj in enumerate(adjacencies):
            self.register_buffer(f"adj_{r}", torch.as_tensor(adj, dtype=torch.float32))
        self._num_relations = num_relations
        # 注：relation_weights_gcn1/gcn2 已在基类中创建为 nn.Parameter

    def _get_adjacencies(self) -> list[torch.Tensor]:
        return [getattr(self, f"adj_{r}") for r in range(self._num_relations)]

    def forward(self, x: torch.Tensor, **_: torch.Tensor) -> ForecastOutput:
        prediction = self.forecast_from_latent(self.encode(x))
        return ForecastOutput(
            prediction=prediction,
            adjacency=self._get_adjacencies()[0],  # 返回第一类图作为代表
            relation_weights_gcn1=self.relation_weights_gcn1.detach(),
            relation_weights_gcn2=self.relation_weights_gcn2.detach(),
        )


# ========== 自适应图预测模型 ==========

class AdaptiveGraphForecast(StationGraphForecast):
    """在三类固定图基础上增加节点嵌入学习的自适应关系（SG-EXP-004）。

    自适应图公式：
      A_adp = Softmax(ReLU(E_s · E_t^T / √d_e))
      随后保留每行 top-k 个最强邻居，其余归零。
      A_mix = α · A_fixed + (1-α) · A_adp

    其中 α（fixed_weight）只能通过验证集选择，测试阶段冻结。
    自适应嵌入仅在训练时通过损失函数更新，验证/测试时不重构。

    关键设计决策：
    - 自适应图是三类固定图之外的**第四类关系**，而非替换固定图
    - 缩放因子 √d_e 防止嵌入维度过大导致 Softmax 退化为 argmax
    - top-k 稀疏化防止所有节点形成近似全连接图
    """

    def __init__(
        self,
        input_dim: int,
        horizon: int,
        num_nodes: int,
        adjacencies: list[np.ndarray | torch.Tensor],
        *,
        hidden_dim: int = 32,
        embedding_dim: int = 12,
        levels: int = 3,
        dropout: float = 0.1,
        fixed_weight: float = 0.3,
        top_k: int = 5,
        relation_dropout: float = 0.0,
    ) -> None:
        # 4 类关系：load, event, pattern + adaptive
        num_relations = len(adjacencies) + 1
        super().__init__(
            input_dim, horizon, num_nodes, num_relations,
            hidden_dim=hidden_dim, levels=levels, dropout=dropout,
            relation_dropout=relation_dropout,
        )
        # 固定邻接矩阵
        for r, adj in enumerate(adjacencies):
            self.register_buffer(f"adj_{r}", torch.as_tensor(adj, dtype=torch.float32))
        self._num_fixed = len(adjacencies)
        self._num_nodes = num_nodes

        # 节点嵌入（非对称：source 发出信息，target 接收信息）
        self.source_embedding = nn.Parameter(torch.empty(num_nodes, embedding_dim))
        self.target_embedding = nn.Parameter(torch.empty(num_nodes, embedding_dim))
        nn.init.xavier_uniform_(self.source_embedding)
        nn.init.xavier_uniform_(self.target_embedding)
        self._embed_dim = embedding_dim
        self._top_k = int(top_k)

        # 固定图融合权重（可学习，训练后冻结）
        # 注：relation_weights_gcn1/gcn2 已在基类中创建为 nn.Parameter，
        # fixed_weight 通过 sigmoid 在 _build_adaptive_adjacency 中参与 alpha 计算
        self.fixed_weight = nn.Parameter(torch.tensor(float(fixed_weight)))

    def _build_adaptive_adjacency(self) -> torch.Tensor:
        """由节点嵌入动态生成自适应邻接矩阵。

        仅在训练时更新（嵌入参与梯度），推理时使用当前冻结值。
        返回 A_mix = α·A_fixed_avg + (1-α)·A_adp，其中 α = sigmoid(fixed_weight)。
        """
        # 缩放点积注意力：E_s @ E_t^T / √d_e
        scale = self._embed_dim ** 0.5
        logits = self.source_embedding @ self.target_embedding.T / scale
        # ReLU 截断负亲和度 → Softmax 逐行归一化
        learned = torch.softmax(torch.relu(logits), dim=-1)
        # top-k 稀疏化：先屏蔽自身对角线，确保自身不占用 top-k 邻居名额，
        # 再选每节点仅保留 k 个最强邻居。
        # 注意：必须使用 masked_fill（非 in-place）而非 fill_diagonal_——
        # in-place 修改 softmax 输出会使反向传播崩溃（版本计数冲突），
        # 且 in-place scatter 到无梯度零张量会截断嵌入的梯度流。
        self_mask = torch.eye(self._num_nodes, device=learned.device, dtype=torch.bool)
        learned = learned.masked_fill(self_mask, float("-inf"))
        topk_vals, topk_idx = torch.topk(
            learned, k=min(self._top_k, self._num_nodes - 1), dim=-1,
        )
        # 非 in-place scatter：保持 topk_vals → learned → 嵌入的梯度通路完整
        sparse = torch.zeros_like(learned).scatter(-1, topk_idx, topk_vals)
        # 对称化 + 自环 + 归一化
        sparse = (sparse + sparse.transpose(0, 1)) / 2.0
        # top-k 完成后添加自环（之前已屏蔽，此处以非 in-place 方式加回）
        sparse = sparse.masked_fill(self_mask, 1.0)
        deg = sparse.sum(dim=-1).pow(-0.5).clamp(min=1e-12)
        adaptive = deg.unsqueeze(-1) * sparse * deg.unsqueeze(-2)

        # 固定图与自适应图混合：α = sigmoid(fixed_weight) 将可学习标量压缩到 (0,1)
        # 注释验证：self.fixed_weight 是 nn.Parameter，通过 torch.sigmoid 参与
        # _build_adaptive_adjacency 的 alpha 计算，梯度可反向传播至 fixed_weight。
        # 训练时 alpha 随 fixed_weight 更新；验证/测试时冻结 fixed_weight 即可固定 α。
        alpha = torch.sigmoid(self.fixed_weight)
        fixed_sum = torch.zeros_like(adaptive)
        for r in range(self._num_fixed):
            fixed_sum = fixed_sum + getattr(self, f"adj_{r}")
        fixed_avg = fixed_sum / max(self._num_fixed, 1)
        return alpha * fixed_avg + (1.0 - alpha) * adaptive

    def _get_adjacencies(self) -> list[torch.Tensor]:
        fixed = [getattr(self, f"adj_{r}") for r in range(self._num_fixed)]
        adaptive = self._build_adaptive_adjacency()
        # 自适应图作为第四类独立关系参与消息传递，
        # 与三类固定关系并列，通过 β 权重在 GCN 中融合
        return fixed + [adaptive]

    # 注：_get_relation_weights_gcn1/gcn2 继承自父类，
    # 直接返回 self.relation_weights_gcn1/gcn2，无需覆写

    def forward(self, x: torch.Tensor, **_: torch.Tensor) -> ForecastOutput:
        prediction = self.forecast_from_latent(self.encode(x))
        return ForecastOutput(
            prediction=prediction,
            adjacency=self._build_adaptive_adjacency(),
            relation_weights_gcn1=self.relation_weights_gcn1.detach(),
            relation_weights_gcn2=self.relation_weights_gcn2.detach(),
        )
