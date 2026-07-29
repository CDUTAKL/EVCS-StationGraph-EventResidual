"""SG-EXP-002：默认时间卷积预测模型。"""

from __future__ import annotations

import torch
from torch import nn

from evcs_station_graph.models.common import ForecastModel


class CausalConvBlock(nn.Module):
    """带残差连接的因果扩张卷积块。"""

    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        *,
        kernel_size: int,
        dilation: int,
        dropout: float,
    ) -> None:
        super().__init__()
        padding = (kernel_size - 1) * dilation
        self.padding = padding
        self.conv = nn.Conv1d(
            in_channels,
            out_channels,
            kernel_size=kernel_size,
            dilation=dilation,
            padding=padding,
        )
        self.norm = nn.GroupNorm(1, out_channels)
        self.activation = nn.GELU()
        self.dropout = nn.Dropout(dropout)
        self.residual = (
            nn.Identity()
            if in_channels == out_channels
            else nn.Conv1d(in_channels, out_channels, kernel_size=1)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        value = self.conv(x)
        if self.padding:
            value = value[..., :-self.padding]
        value = self.dropout(self.activation(self.norm(value)))
        return value + self.residual(x)


class TemporalConvNet(ForecastModel):
    """对每个节点共享参数的默认 TCN 路径。

    共享时间编码器能够在不使用跨节点关系的情况下学习历史负荷与行为特征，
    因而可作为稳定窗口中的默认预测路径。
    """

    def __init__(
        self,
        input_dim: int,
        horizon: int,
        *,
        hidden_dim: int = 32,
        levels: int = 3,
        kernel_size: int = 3,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        if levels <= 0:
            raise ValueError("levels 必须为正整数")
        blocks: list[nn.Module] = []
        channels = input_dim
        for level in range(levels):
            blocks.append(
                CausalConvBlock(
                    channels,
                    hidden_dim,
                    kernel_size=kernel_size,
                    dilation=2**level,
                    dropout=dropout,
                )
            )
            channels = hidden_dim
        self.network = nn.Sequential(*blocks)
        self.head = nn.Linear(hidden_dim, horizon)
        self.latent_dim = hidden_dim
        self.horizon = horizon

    def encode(self, x: torch.Tensor) -> torch.Tensor:
        if x.ndim != 4:
            raise ValueError("TCN 输入必须为 [B, T, N, F]")
        batch, time_steps, nodes, features = x.shape
        value = x.permute(0, 2, 3, 1).reshape(batch * nodes, features, time_steps)
        encoded = self.network(value)[..., -1]
        return encoded.reshape(batch, nodes, self.latent_dim)

    def forecast_from_latent(self, latent: torch.Tensor) -> torch.Tensor:
        prediction = self.head(latent)
        return prediction.permute(0, 2, 1).contiguous()
