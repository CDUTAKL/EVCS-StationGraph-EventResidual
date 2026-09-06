"""SG-EXP-002：默认时间卷积预测模型。

本模块实现因果扩张时间卷积网络（Temporal Convolutional Network，TCN），
作为所有后续实验的默认预测路径。TCN 对每个节点独立编码——不使用跨节点
信息——因此可作为"不看邻居"的基线，用于量化图关系的增量收益。

关键设计：
- 因果卷积：padding 只加在左侧，forward 时裁剪右侧，保证时刻 t 的隐表示
  仅依赖 ≤t 的信息
- dilation>1 的膨胀卷积不走 nn.Conv1d 的 ATen 实现，而是
  CausalConvBlock._dilated_conv_deterministic 的「左 padding + 分段切片 +
  matmul 求和」手动实现：torch.use_deterministic_algorithms(True) 下
  dilated conv 在 CUDA 无确定性算法，会回退 aten::slow_conv_dilated2d，
  CPU kernel-launch 开销使单 batch 慢 200+ 倍（SG-EXP-019 AutoDL 实测）。
  手动路径仅用确定性算子，数学上与裁剪后的因果 Conv1d 完全等价，
  且 state_dict 参数（conv.weight/conv.bias）不变。
- 扩张因子按 2^level 指数增长。感受野公式：
  RF = 1 + Σ (kernel_size-1) × dilation[level]
  对 levels=3、kernel=3，dilations=[1,2,4]：
  RF = 1 + 2×1 + 2×2 + 2×4 = 1 + 2 + 4 + 8 = 15 个时间步（3.75 小时）
  若需覆盖 96 步历史窗口，需 6 层：RF = 1 + 2×(1+2+4+8+16+32) = 127 步
- 归一化采用逐时间步 LayerNorm：对每个时间步独立归一化通道维。
  注意不能使用 GroupNorm(1, C)——其对 [B, C, T] 的归一化统计量
  跨 (C×T) 计算，会把所有时间步（包括未来）耦合进每个输出位置，
  既破坏逐点因果性，也使实际感受野退化为整个输入窗口（实测 96 步），
  与上面 15 步的理论公式不符。
"""

from __future__ import annotations

import torch
import torch.nn.functional as F
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
        self.norm = nn.LayerNorm(out_channels)  # 逐时间步归一化通道维，不跨时间耦合
        self.activation = nn.GELU()             # GELU 激活函数，平滑非线性
        self.dropout = nn.Dropout(dropout)      # 随机失活，防止过拟合
        self.residual = (                       # 残差连接：若输入输出通道数相同，则直接相加，否则通过 1x1 卷积调整通道数
            nn.Identity()
            if in_channels == out_channels
            else nn.Conv1d(in_channels, out_channels, kernel_size=1)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # 因果卷积通过在左侧加 padding、前向时裁剪右侧来实现：
        # conv(x) 的输出比输入长 padding 个时间步，其中前 padding 个位置
        # 是"看到未来"的结果，因此裁剪掉右侧多余的 padding 个位置
        if self.conv.dilation[0] > 1:
            value = self._dilated_conv_deterministic(x)
        else:
            value = self.conv(x)
            if self.padding:
                value = value[..., :-self.padding]
        # 逐时间步 LayerNorm：[B, C, T] → [B, T, C] → norm → [B, C, T]
        # 每个时间步的统计量仅来自该步自身，保证逐点因果与理论感受野
        value = self.norm(value.transpose(1, 2)).transpose(1, 2)
        value = self.dropout(self.activation(value))
        return value + self.residual(x)

    def _dilated_conv_deterministic(self, x: torch.Tensor) -> torch.Tensor:
        """dilation>1 时的手动因果膨胀卷积（与 nn.Conv1d 逐位/近逐位等价）。

        背景（SG-EXP-019）：torch.use_deterministic_algorithms(True) 下，
        dilation>1 的 Conv1d 在 CUDA 上没有确定性实现，会回退到
        aten::slow_conv_dilated2d——该路径按 (batch, 输出位置) 逐个 launch
        CPU kernel，实测单 batch 9.2 s（GPU 实际计算仅 0.8 s，慢 200+ 倍）。
        因此这里改用确定性算子手动计算：左 pad → 按抽头 k 分段切片 →
        每个切片与 weight[:, :, k] 做 matmul（einsum 'bct,oc->bot'）→ 求和加 bias。
        切片/matmul/add 均为确定性算子（不使用 unfold/fold——其反向是
        非确定性的 atomicAdd）。

        数学定义（与 self.conv(x)[..., :-padding] 完全一致）：
            out[o, t] = bias[o] + Σ_k Σ_c weight[o, c, k] * x_pad[c, t + k*d]
        其中 x_pad 为左侧 pad 了 self.padding 个零的输入，输出长度 = 输入长度。
        右侧 padding 的位置永远不会被裁剪后保留的输出访问，因此只需左 pad。
        """
        dilation = self.conv.dilation[0]
        kernel_size = self.conv.kernel_size[0]
        time_steps = x.shape[-1]
        x_pad = F.pad(x, (self.padding, 0))
        weight = self.conv.weight  # [C_out, C_in, K]
        value = torch.einsum("bct,oc->bot", x_pad[:, :, 0:time_steps], weight[:, :, 0])
        for tap in range(1, kernel_size):
            offset = tap * dilation
            value = value + torch.einsum(
                "bct,oc->bot", x_pad[:, :, offset : offset + time_steps], weight[:, :, tap]
            )
        if self.conv.bias is not None:
            value = value + self.conv.bias.view(1, -1, 1)
        return value


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
        history_steps: int | None = None,
    ) -> None:
        super().__init__()
        if levels <= 0:
            raise ValueError("levels 必须为正整数")
        # 感受野下限校验（硬约束）：RF = 1 + (kernel-1) × (2^levels - 1)，
        # 必须覆盖完整历史窗口，否则模型静默只看得到部分历史（审查发现：
        # 仓库 YAML 曾写 levels=3 → RF=15 < 96，独立 evcs-sg run 无任何报错）
        rf = 1 + (kernel_size - 1) * (2 ** levels - 1)
        if history_steps is not None and rf < history_steps:
            raise ValueError(
                f"TCN 感受野 {rf} 步 < history_steps {history_steps} 步，"
                f"请增大 levels（每层约 ×2 感受野）或减小历史窗口"
            )
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
