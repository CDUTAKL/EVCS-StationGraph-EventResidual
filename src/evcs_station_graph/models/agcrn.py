"""SG-EXP-008：AGCRN 自适应图卷积循环网络基线（简化变体）。

参考 Bai et al. (NeurIPS 2020) 的 Adaptive Graph Convolutional Recurrent
Network（AGCRN）设计，作为与本文多关系门控 GCN 可比的自适应图基线。
**简化说明（审查 H-07，2026-08-01）**：实现使用共享门控权重与自适应邻接，
未包含原方法核心的节点自适应参数池（NAPL）——论文中命名为
"AGCRN-inspired adaptive graph GRU"，不得声称完整复现原模型。

核心机制：
- adaptive adjacency learning：可学习节点嵌入 E ∈ [N, d_e]，自适应邻接
  （审查 H-07：不等同于原版 NAPL 节点自适应参数池——本实现权重跨节点共享）
  A_adp = Softmax(ReLU(E @ E^T))，逐行和为 1，无需预定义图结构。
- 图卷积 GRU：将 GRU 中 update / reset / candidate 三个门的线性变换替换为
  基于 A_adp 的图卷积，即先以 A_adp 聚合邻居特征，再对特征维做线性投影。
- 时间编码：对 [B, T, N, F] 逐步循环 T 步，最终隐藏态 [B, N, D] 作为节点隐表示。

设计说明：
- adjacencies 参数仅为保持工厂统一调用而接收，AGCRN 内部完全使用自适应邻接。
- 96 步循环内仅使用批量张量运算，禁止 .item() / .cpu() 等同步操作。
"""

from __future__ import annotations

import numpy as np
import torch
from torch import nn

from evcs_station_graph.models.common import ForecastModel, ForecastOutput


class AGCRNCell(nn.Module):
    """单步图卷积 GRU 单元。

    将标准 GRU 的输入/隐藏线性变换替换为自适应图卷积：
      r_t = σ(A @ X_t @ W_ir + A @ H_{t-1} @ W_hr + b_ir + b_hr)
      z_t = σ(A @ X_t @ W_iz + A @ H_{t-1} @ W_hz + b_iz + b_hz)
      n_t = tanh(A @ X_t @ W_in + r_t ⊙ (A @ H_{t-1} @ W_hn) + b_in + b_hn)
      H_t = (1 - z_t) ⊙ H_{t-1} + z_t ⊙ n_t

    其中 A 由外层 ``AGCRNForecast._build_adaptive_adjacency`` 提供。
    """

    def __init__(
        self,
        input_dim: int,
        hidden_dim: int,
        dropout: float,
    ) -> None:
        super().__init__()
        self.hidden_dim = hidden_dim

        # 输入侧图卷积权重：reset / update / candidate
        self.weight_ir = nn.Parameter(torch.empty(input_dim, hidden_dim))
        self.weight_iz = nn.Parameter(torch.empty(input_dim, hidden_dim))
        self.weight_in = nn.Parameter(torch.empty(input_dim, hidden_dim))

        # 隐藏侧图卷积权重
        self.weight_hr = nn.Parameter(torch.empty(hidden_dim, hidden_dim))
        self.weight_hz = nn.Parameter(torch.empty(hidden_dim, hidden_dim))
        self.weight_hn = nn.Parameter(torch.empty(hidden_dim, hidden_dim))

        # 偏置：输入侧与隐藏侧分离，与 PyTorch GRU 一致
        self.bias_ir = nn.Parameter(torch.empty(hidden_dim))
        self.bias_iz = nn.Parameter(torch.empty(hidden_dim))
        self.bias_in = nn.Parameter(torch.empty(hidden_dim))
        self.bias_hr = nn.Parameter(torch.empty(hidden_dim))
        self.bias_hz = nn.Parameter(torch.empty(hidden_dim))
        self.bias_hn = nn.Parameter(torch.empty(hidden_dim))

        self.dropout = nn.Dropout(dropout)
        self.norm = nn.LayerNorm(hidden_dim)  # 稳定 96 步循环训练的归一化层
        self._reset_parameters()

    def _reset_parameters(self) -> None:
        """Xavier 初始化权重，零初始化偏置。"""
        for weight in (
            self.weight_ir, self.weight_iz, self.weight_in,
            self.weight_hr, self.weight_hz, self.weight_hn,
        ):
            nn.init.xavier_uniform_(weight)
        for bias in (
            self.bias_ir, self.bias_iz, self.bias_in,
            self.bias_hr, self.bias_hz, self.bias_hn,
        ):
            nn.init.zeros_(bias)

    def _graph_conv(
        self,
        adjacency: torch.Tensor,
        x: torch.Tensor,
        weight: torch.Tensor,
        bias: torch.Tensor,
    ) -> torch.Tensor:
        """执行图卷积：A @ X @ W + b。

        参数
        ----
        adjacency:
            自适应邻接矩阵，形状 [N, N]。
        x:
            节点特征，形状 [B, N, C]。
        weight:
            特征变换权重，形状 [C, D]。
        bias:
            偏置，形状 [D]。

        返回
        ----
        图卷积结果，形状 [B, N, D]。
        """
        # A @ X: [N, N] × [B, N, C] → [B, N, C]
        # 使用 einsum 显式表达“邻接矩阵沿节点维聚合”
        ax = torch.einsum("nm,bmc->bnc", adjacency, x)
        # X @ W + b: [B, N, C] × [C, D] → [B, N, D]
        return ax @ weight + bias

    def forward(
        self,
        x_t: torch.Tensor,
        h_prev: torch.Tensor,
        adjacency: torch.Tensor,
    ) -> torch.Tensor:
        """单步前向，返回新的隐藏态 [B, N, D]。

        参数
        ----
        x_t:
            当前时刻输入，形状 [B, N, F]。
        h_prev:
            上一时刻隐藏态，形状 [B, N, D]。
        adjacency:
            自适应邻接矩阵，形状 [N, N]。

        返回
        ----
        当前时刻隐藏态，形状 [B, N, D]。
        """
        if x_t.ndim != 3:
            raise ValueError("AGCRNCell 输入 x_t 必须为 [B, N, F]")
        if h_prev.ndim != 3:
            raise ValueError("AGCRNCell 隐藏态 h_prev 必须为 [B, N, D]")
        if x_t.shape[-1] != self.weight_ir.shape[0]:
            raise ValueError(
                f"AGCRNCell 输入特征维度 {x_t.shape[-1]} 与期望 "
                f"input_dim {self.weight_ir.shape[0]} 不一致"
            )
        if h_prev.shape[-1] != self.hidden_dim:
            raise ValueError(
                f"AGCRNCell 隐藏态维度 {h_prev.shape[-1]} 与 hidden_dim "
                f"{self.hidden_dim} 不一致"
            )
        if x_t.shape[1] != h_prev.shape[1]:
            raise ValueError(
                f"AGCRNCell 输入节点数 {x_t.shape[1]} 与隐藏态节点数 "
                f"{h_prev.shape[1]} 不一致"
            )

        x_t = self.dropout(x_t)

        # reset gate
        r = torch.sigmoid(
            self._graph_conv(adjacency, x_t, self.weight_ir, self.bias_ir)
            + self._graph_conv(adjacency, h_prev, self.weight_hr, self.bias_hr)
        )

        # update gate
        z = torch.sigmoid(
            self._graph_conv(adjacency, x_t, self.weight_iz, self.bias_iz)
            + self._graph_conv(adjacency, h_prev, self.weight_hz, self.bias_hz)
        )

        # candidate hidden state
        n = torch.tanh(
            self._graph_conv(adjacency, x_t, self.weight_in, self.bias_in)
            + r * self._graph_conv(adjacency, h_prev, self.weight_hn, self.bias_hn)
        )

        # GRU 状态更新：z 趋近 1 则更多采用候选态
        h_new = (1.0 - z) * h_prev + z * n
        return self.norm(h_new)


class AGCRNForecast(ForecastModel):
    """AGCRN 预测模型（SG-EXP-008）。

    完全基于自适应邻接的图卷积 GRU，逐步处理 T 步历史，最终隐藏态经
    per-node Linear 投影为 horizon 步预测。

    参数
    ----
    input_dim:
        输入特征维度 F。
    horizon:
        预测步长 H。
    num_nodes:
        节点数 N。
    adjacencies:
        预定义邻接矩阵列表。AGCRN 为纯自适应图设计，此参数仅用于保持
        ``build_model`` 统一调用签名，内部不参与计算。
    hidden_dim:
        GRU 隐藏状态维度 D。默认 32，与本文 10 节点小图场景匹配。
    embedding_dim:
        节点嵌入维度 d_e。默认 12。
    dropout:
        输入 dropout 概率。默认 0.1。
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
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        if num_nodes <= 0:
            raise ValueError("num_nodes 必须为正整数")
        if input_dim <= 0:
            raise ValueError("input_dim 必须为正整数")
        if horizon <= 0:
            raise ValueError("horizon 必须为正整数")
        if hidden_dim <= 0:
            raise ValueError("hidden_dim 必须为正整数")
        if embedding_dim <= 0:
            raise ValueError("embedding_dim 必须为正整数")
        if not 0.0 <= dropout <= 1.0:
            raise ValueError("dropout 必须在 [0.0, 1.0] 范围内")
        self._num_nodes = num_nodes
        self._input_dim = input_dim
        self._embed_dim = embedding_dim
        self.hidden_dim = hidden_dim
        self.latent_dim = hidden_dim
        self.horizon = horizon

        # 节点嵌入 E：自适应邻接的唯一来源，训练时直接优化
        self.node_embedding = nn.Parameter(torch.empty(num_nodes, embedding_dim))
        nn.init.xavier_uniform_(self.node_embedding)

        # 图卷积 GRU 单元
        self.cell = AGCRNCell(input_dim, hidden_dim, dropout)

        # 预测头：per-node Linear(D → H)，共享权重 across nodes
        self.head = nn.Linear(hidden_dim, horizon)

    def _build_adaptive_adjacency(self) -> torch.Tensor:
        """由节点嵌入生成自适应邻接矩阵 A_adp ∈ [N, N]，逐行和为 1。

        公式：A_adp = Softmax(ReLU(E @ E^T))。
        ReLU 截断负亲和度，Softmax 沿列（dim=-1）归一化，保证每行是
        概率分布，可直接解释为“节点 i 对节点 j 的注意力权重”。
        """
        # [N, d_e] @ [d_e, N] → [N, N]
        logits = self.node_embedding @ self.node_embedding.T
        return torch.softmax(torch.relu(logits), dim=-1)

    def _encode(self, x: torch.Tensor, adjacency: torch.Tensor) -> torch.Tensor:
        """逐步循环编码：将 [B, T, N, F] 映射为 [B, N, D]。

        参数
        ----
        x:
            输入历史序列，形状 [B, T, N, F]。
        adjacency:
            自适应邻接矩阵，形状 [N, N]。

        返回
        ----
        最终时刻隐藏态，形状 [B, N, D]。
        """
        if x.ndim != 4:
            raise ValueError("AGCRNForecast 输入必须为 [B, T, N, F]")
        batch, time_steps, nodes, features = x.shape
        if features != self._input_dim:
            raise ValueError(
                f"输入特征维度 {features} 与模型声明的 input_dim "
                f"{self._input_dim} 不一致"
            )
        if nodes != self._num_nodes:
            raise ValueError(
                f"输入节点数 {nodes} 与模型声明的 num_nodes {self._num_nodes} 不一致"
            )
        if time_steps == 0:
            raise ValueError("历史步长 time_steps 必须大于 0")

        # 隐藏态 [B, N, D] 初始化为零，沿时间步循环，不访问未来信息
        h = torch.zeros(
            batch, self._num_nodes, self.hidden_dim,
            device=x.device, dtype=x.dtype,
        )
        for t in range(time_steps):
            x_t = x[:, t, :, :]  # [B, N, F]
            h = self.cell(x_t, h, adjacency)
        return h

    def encode(self, x: torch.Tensor) -> torch.Tensor:
        """将 [B, T, N, F] 编码为 [B, N, D] 节点隐表示。"""
        return self._encode(x, self._build_adaptive_adjacency())

    def forecast_from_latent(self, latent: torch.Tensor) -> torch.Tensor:
        """由 [B, N, D] 隐表示生成 [B, H, N] 预测。

        维度变换：
        - head: [B, N, D] → [B, N, H]
        - permute(0, 2, 1): [B, N, H] → [B, H, N]
        """
        if latent.ndim != 3 or latent.shape[-1] != self.hidden_dim:
            raise ValueError(
                f"latent 必须为 [B, N, {self.hidden_dim}]，"
                f"实际 {tuple(latent.shape)}"
            )
        prediction = self.head(latent)  # [B, N, H]
        return prediction.permute(0, 2, 1).contiguous()  # [B, H, N]

    def forward(self, x: torch.Tensor, **_: torch.Tensor) -> ForecastOutput:
        """统一前向接口，返回 ForecastOutput 并暴露自适应邻接矩阵。"""
        adjacency = self._build_adaptive_adjacency()
        return ForecastOutput(
            prediction=self.forecast_from_latent(self._encode(x, adjacency)),
            adjacency=adjacency,
        )
