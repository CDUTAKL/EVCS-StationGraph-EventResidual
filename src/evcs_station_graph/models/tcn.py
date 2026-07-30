"""SG-EXP-002：默认时间卷积预测模型。

本模块实现因果扩张时间卷积网络（Temporal Convolutional Network，TCN），
作为所有后续实验的默认预测路径。TCN 对每个节点独立编码——不使用跨节点
信息——因此可作为"不看邻居"的基线，用于量化图关系的增量收益。

关键设计：
- 因果卷积：padding 只加在左侧，forward 时裁剪右侧，保证时刻 t 的隐表示
  仅依赖 ≤t 的信息
- 扩张因子按 2^level 指数增长。感受野公式：
  RF = 1 + Σ (kernel_size-1) × dilation[level]
  对 levels=3、kernel=3，dilations=[1,2,4]：
  RF = 1 + 2×1 + 2×2 + 2×4 = 1 + 2 + 4 + 8 = 15 个时间步（3.75 小时）
  若需覆盖 96 步历史窗口，需 6 层：RF = 1 + 2×(1+2+4+8+16+32) = 127 步
- GroupNorm(1, ...)：组数=1 等价于沿通道的 LayerNorm，适合小 batch 训练
"""

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
        self.padding = padding  # 记录 padding 以便 forward 时裁剪右侧
        self.conv = nn.Conv1d(
            # Conv1d 输入形状 [B, C_in, T]，输出形状 [B, C_out, T+padding]
            in_channels,
            out_channels,
            kernel_size=kernel_size,  # 卷积核大小
            dilation=dilation,        # 扩张因子
            padding=padding,          # 左侧填充，保证输出长度 = 输入长度 + padding
        )
        self.norm = nn.GroupNorm(1, out_channels)  # 组数=1 等价于 LayerNorm，适合小 batch 训练
        self.activation = nn.GELU()                # GELU 激活函数，平滑非线性
        self.dropout = nn.Dropout(dropout)         # 随机失活，防止过拟合
        self.residual = (                          # 残差连接：若输入输出通道数相同，则直接相加，否则通过 1x1 卷积调整通道数
            nn.Identity()
            if in_channels == out_channels
            else nn.Conv1d(in_channels, out_channels, kernel_size=1)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # 因果卷积通过在左侧加 padding、前向时裁剪右侧来实现：
        # conv(x) 的输出比输入长 padding 个时间步，其中前 padding 个位置
        # 是"看到未来"的结果，因此裁剪掉右侧多余的 padding 个位置
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
        """将 [B, T, N, F] 输入编码为 [B, N, D] 节点隐表示。

        维度变换说明：
        - 输入形状 [B, T, N, F] → permute [B, N, F, T] → reshape [B*N, F, T]
        - 这样每个节点的时间序列成为独立的 Conv1d 样本，共享 TCN 参数
        - 最后取每个序列的最后一个时间步 [..., -1] 作为节点隐表示
        - reshape 回 [B, N, D] 恢复节点维度
        """
        if x.ndim != 4:
            raise ValueError("TCN 输入必须为 [B, T, N, F]")
        batch, time_steps, nodes, features = x.shape
        # [B, T, N, F] → [B, N, F, T] → [B*N, F, T]
        # 将每个节点的时序独立送入共享权重的 Conv1d
        value = x.permute(0, 2, 3, 1).reshape(batch * nodes, features, time_steps)
        encoded = self.network(value)[..., -1]  # 取最后一个时间步的隐表示
        return encoded.reshape(batch, nodes, self.latent_dim)

    def forecast_from_latent(self, latent: torch.Tensor) -> torch.Tensor:
        prediction = self.head(latent)
        return prediction.permute(0, 2, 1).contiguous()
