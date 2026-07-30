"""SG-EXP-003/004：固定图与自适应图预测模型。

两个模型共享 TCN 编码 + 图消息传递的架构，区别在于邻接矩阵的来源：

- ``StaticGraphForecast`` (SG-EXP-003)：使用训练期构建的固定统计关系矩阵，
  验证与测试阶段不更新。量化"引入固定站内关系"的收益。
- ``AdaptiveGraphForecast`` (SG-EXP-004)：通过可学习的节点嵌入动态生成邻接矩阵，
  与固定先验按 ``fixed_weight`` 融合。仅在训练时更新嵌入，测试时不重构。

消息传递（两者相同）：
  h_i' = self_linear(h_i) + neighbor_linear(Σ_j A_ij * h_j)
  即节点更新 = 自身变换 + 邻居聚合，保留每个节点的独立表征同时引入
  图结构信息。
"""

from __future__ import annotations

import numpy as np
import torch
from torch import nn

from evcs_station_graph.models.common import ForecastModel, ForecastOutput
from evcs_station_graph.models.tcn import TemporalConvNet


class StaticGraphForecast(ForecastModel):
    """训练期统计关系固定不变的站内图预测模型。"""

    def __init__(
        self,
        input_dim: int,
        horizon: int,
        adjacency: np.ndarray | torch.Tensor,
        *,
        hidden_dim: int = 32,
        levels: int = 3,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        self.temporal = TemporalConvNet(
            input_dim,
            horizon,
            hidden_dim=hidden_dim,
            levels=levels,
            dropout=dropout,
        )
        matrix = torch.as_tensor(adjacency, dtype=torch.float32)
        self.register_buffer("adjacency", matrix)
        self.self_linear = nn.Linear(hidden_dim, hidden_dim)
        self.neighbor_linear = nn.Linear(hidden_dim, hidden_dim)
        self.norm = nn.LayerNorm(hidden_dim)
        self.activation = nn.GELU()
        self.dropout = nn.Dropout(dropout)
        self.head = nn.Linear(hidden_dim, horizon)
        self.latent_dim = hidden_dim

    def encode(self, x: torch.Tensor) -> torch.Tensor:
        temporal = self.temporal.encode(x)  # [B, N, D] TCN 独立编码
        # 消息传递：einsum("nm,bmd->bnd") = 对每个 batch 样本，
        # 邻接矩阵 A[n,m] 作为权重聚合来自节点 m 的隐表示 h_m
        neighbor = torch.einsum("nm,bmd->bnd", self.adjacency, temporal)
        # 节点更新 = 自身变换 + 邻居聚合（残差式设计，保留独立表征）
        value = self.self_linear(temporal) + self.neighbor_linear(neighbor)
        return self.dropout(self.activation(self.norm(value)))

    def forecast_from_latent(self, latent: torch.Tensor) -> torch.Tensor:
        return self.head(latent).permute(0, 2, 1).contiguous()

    def forward(self, x: torch.Tensor, **_: torch.Tensor) -> ForecastOutput:
        prediction = self.forecast_from_latent(self.encode(x))
        return ForecastOutput(prediction=prediction, adjacency=self.adjacency)


class AdaptiveGraphForecast(ForecastModel):
    """由节点嵌入学习站内关系的自适应图模型。

    自适应矩阵仅由训练损失更新；验证与测试阶段不会根据真实目标重构图。
    """

    def __init__(
        self,
        input_dim: int,
        horizon: int,
        num_nodes: int,
        *,
        hidden_dim: int = 32,
        embedding_dim: int = 12,
        levels: int = 3,
        dropout: float = 0.1,
        fixed_adjacency: np.ndarray | torch.Tensor | None = None,
        fixed_weight: float = 0.2,
    ) -> None:
        super().__init__()
        self.temporal = TemporalConvNet(
            input_dim,
            horizon,
            hidden_dim=hidden_dim,
            levels=levels,
            dropout=dropout,
        )
        self.source_embedding = nn.Parameter(torch.empty(num_nodes, embedding_dim))
        self.target_embedding = nn.Parameter(torch.empty(num_nodes, embedding_dim))
        nn.init.xavier_uniform_(self.source_embedding)
        nn.init.xavier_uniform_(self.target_embedding)
        if fixed_adjacency is None:
            fixed = torch.eye(num_nodes, dtype=torch.float32)
            fixed_weight = 0.0
        else:
            fixed = torch.as_tensor(fixed_adjacency, dtype=torch.float32)
        self.register_buffer("fixed_adjacency", fixed)
        self.fixed_weight = float(fixed_weight)
        self.self_linear = nn.Linear(hidden_dim, hidden_dim)
        self.neighbor_linear = nn.Linear(hidden_dim, hidden_dim)
        self.norm = nn.LayerNorm(hidden_dim)
        self.activation = nn.GELU()
        self.dropout = nn.Dropout(dropout)
        self.head = nn.Linear(hidden_dim, horizon)
        self.latent_dim = hidden_dim

    def learned_adjacency(self) -> torch.Tensor:
        """由节点嵌入动态生成自适应邻接矩阵。

        实现原理：
        1. ``source_embedding @ target_embedding.T`` 计算节点间的非对称亲和度，
           其中 source_embedding[n] 表示"节点 n 作为信息接收者"的角色，
           target_embedding[m] 表示"节点 m 作为信息发送者"的角色
        2. ``relu`` 截断负亲和度，使关系稀疏化（负值→零边）
        3. ``softmax(dim=-1)`` 将每行的出边权重归一化为概率分布，
           保证消息传递的数值稳定性
        4. 与固定先验按 ``fixed_weight`` 融合，避免学习过程中
           图结构完全偏离统计先验
        """
        # 非对称亲和度：source 接收来自 target 的信息
        logits = torch.relu(self.source_embedding @ self.target_embedding.T)
        # 逐行 softmax：每个节点对其所有邻居的注意力之和为 1
        learned = torch.softmax(logits, dim=-1)
        # 加权融合：fixed_weight 控制对统计先验的依赖程度
        return self.fixed_weight * self.fixed_adjacency + (1.0 - self.fixed_weight) * learned

    def encode(self, x: torch.Tensor) -> torch.Tensor:
        temporal = self.temporal.encode(x)
        adjacency = self.learned_adjacency()
        neighbor = torch.einsum("nm,bmd->bnd", adjacency, temporal)
        value = self.self_linear(temporal) + self.neighbor_linear(neighbor)
        return self.dropout(self.activation(self.norm(value)))

    def forecast_from_latent(self, latent: torch.Tensor) -> torch.Tensor:
        return self.head(latent).permute(0, 2, 1).contiguous()

    def forward(self, x: torch.Tensor, **_: torch.Tensor) -> ForecastOutput:
        adjacency = self.learned_adjacency()
        prediction = self.forecast_from_latent(self.encode(x))
        return ForecastOutput(prediction=prediction, adjacency=adjacency)
