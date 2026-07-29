"""SG-EXP-003/004：固定图与自适应图预测模型。"""

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
        temporal = self.temporal.encode(x)
        neighbor = torch.einsum("nm,bmd->bnd", self.adjacency, temporal)
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
        logits = torch.relu(self.source_embedding @ self.target_embedding.T)
        learned = torch.softmax(logits, dim=-1)
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
