"""SG-EXP-010：Graph WaveNet 时空图预测基线（简化变体）。

参考 Wu et al., IJCAI 2019 的结构：门控扩张因果卷积 + 预定义/自适应双图
卷积 + 跨层 skip connection，作为项目内时空图参照基线，与 SG-EXP-003/004
的多关系门控 GCN 形成对照。
**简化说明（审查 H-07，2026-08-01）**：实现为单步预定义图 + 自适应图聚合，
未包含原模型典型的多阶 diffusion convolution——论文中命名为
"simplified Graph-WaveNet-style baseline"，不得声称完整复现原模型。

感受野计算：
  RF = 1 + Σ (kernel_size - 1) × dilation[level]
kernel_size=2，dilations=[1, 2, 4, 8, 16, 32, 64] 时：
  RF = 1 + 1×(1+2+4+8+16+32+64) = 128 个时间步
大于 96 步的历史输入窗口，保证每个输出位置都能看到完整历史。
"""

from __future__ import annotations

from collections.abc import Sequence

import torch
import torch.nn.functional as F
from torch import nn

from evcs_station_graph.models.common import ForecastModel, ForecastOutput


class _GatedCausalConv(nn.Module):
    """门控扩张因果卷积。

    包含 filter 卷积（tanh）和 gate 卷积（sigmoid），输出为两者逐元素乘积。
    采用 PyTorch 的 ``padding`` 参数在输入两侧补零，并在卷积后裁剪右侧
    padding 个位置，从而保证时刻 ``t`` 的输出仅依赖输入中 ≤t 的时间步。

    参数
    ----
    channels:
        输入/输出通道数（即隐层维度）。
    kernel_size:
        因果卷积核大小；本项目取 2，使感受野按扩张因子线性增长。
    dilation:
        扩张因子，控制时间卷积的感受野跨度。
    dropout:
        门控输出后的随机失活概率。
    """

    def __init__(
        self,
        channels: int,
        kernel_size: int,
        dilation: int,
        dropout: float,
    ) -> None:
        super().__init__()
        if channels <= 0:
            raise ValueError("channels 必须为正整数")
        if kernel_size <= 0:
            raise ValueError("kernel_size 必须为正整数")
        if dilation <= 0:
            raise ValueError("dilation 必须为正整数")
        if not 0.0 <= dropout <= 1.0:
            raise ValueError("dropout 必须在 [0.0, 1.0] 范围内")
        # 左侧需填充的长度；右侧同等长度会在 forward 中被裁剪
        self.padding = (kernel_size - 1) * dilation
        self.filter_conv = nn.Conv1d(
            channels,
            channels,
            kernel_size=kernel_size,
            dilation=dilation,
            padding=self.padding,
        )
        self.gate_conv = nn.Conv1d(
            channels,
            channels,
            kernel_size=kernel_size,
            dilation=dilation,
            padding=self.padding,
        )
        self.norm = nn.LayerNorm(channels)  # 逐时间步归一化，不跨时间耦合
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """前向计算。

        输入/输出形状均为 ``[B*N, C, T]``。
        """
        # 两侧补零后裁剪右侧 padding，保证时刻 t 只看 ≤t
        filter_out = torch.tanh(self.filter_conv(x))
        gate_out = torch.sigmoid(self.gate_conv(x))
        if self.padding > 0:
            filter_out = filter_out[..., :-self.padding]
            gate_out = gate_out[..., :-self.padding]
        out = filter_out * gate_out  # [B*N, C, T]
        # 逐时间步 LayerNorm：[B*N, C, T] → [B*N, T, C] → norm → [B*N, C, T]
        # 同 TCN 设计：每个时间步独立归一化，不跨时间耦合，保证因果性
        out = self.norm(out.transpose(1, 2)).transpose(1, 2)
        return self.dropout(out)


class _AdaptiveGraphConvolution(nn.Module):
    """预定义图与自适应图双路图卷积，结果相加。

    自适应邻接矩阵公式：
      A_adp = softmax(ReLU(E1 @ E2^T))
    其中 ``E1``、``E2`` 形状均为 ``[N, embedding_dim]``，按行做 softmax 归一化，
    保证每行是一个概率分布。E1 与 E2 的独立分解比单嵌入矩阵具有更强表达能力。
    """

    def __init__(self, num_nodes: int, embedding_dim: int) -> None:
        super().__init__()
        self.E1 = nn.Parameter(torch.empty(num_nodes, embedding_dim))
        self.E2 = nn.Parameter(torch.empty(num_nodes, embedding_dim))
        nn.init.xavier_uniform_(self.E1)
        nn.init.xavier_uniform_(self.E2)

    def forward(self, x: torch.Tensor, A_pre: torch.Tensor) -> torch.Tensor:
        """聚合邻居信息。

        参数
        ----
        x:
            节点特征，形状 ``[B, N, C, T]``。
        A_pre:
            预定义邻接矩阵，形状 ``[N, N]``。

        返回
        ----
        形状 ``[B, N, C, T]`` 的聚合后特征。
        """
        A_adp = F.softmax(F.relu(self.E1 @ self.E2.t()), dim=1)  # [N, N]
        out_pre = torch.einsum("mn,bnct->bmct", A_pre, x)
        out_adp = torch.einsum("mn,bnct->bmct", A_adp, x)
        return out_pre + out_adp


class _GraphWaveNetBlock(nn.Module):
    """Graph WaveNet 单层时空块。

    结构：门控因果卷积 → 双图卷积 → 残差连接 → skip 分支。
    """

    def __init__(
        self,
        channels: int,
        num_nodes: int,
        embedding_dim: int,
        kernel_size: int,
        dilation: int,
        dropout: float,
    ) -> None:
        super().__init__()
        self.gated_conv = _GatedCausalConv(channels, kernel_size, dilation, dropout)
        self.graph_conv = _AdaptiveGraphConvolution(num_nodes, embedding_dim)
        # 1x1 卷积将块输出投影到 skip 通道，保持通道数不变
        self.skip_conv = nn.Conv1d(channels, channels, kernel_size=1)

    def forward(self, x: torch.Tensor, A_pre: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """前向计算。

        参数
        ----
        x:
            输入特征，形状 ``[B, N, C, T]``。
        A_pre:
            预定义邻接矩阵，形状 ``[N, N]``。

        返回
        ----
        (residual_output, skip_output)，形状均为 ``[B, N, C, T]``。
        """
        b, n, c, t = x.shape
        # 每个节点的时间序列独立做因果卷积，再恢复维度做图卷积
        x_time = x.reshape(b * n, c, t)
        h_time = self.gated_conv(x_time).reshape(b, n, c, t)
        h_graph = self.graph_conv(h_time, A_pre)
        h = h_time + h_graph
        skip = self.skip_conv(h.reshape(b * n, c, t)).reshape(b, n, c, t)
        return x + h, skip


class GraphWaveNetForecast(ForecastModel):
    """Graph WaveNet 预测模型。

    构造签名：
      (input_dim, horizon, num_nodes, adjacencies, *,
       hidden_dim=32, embedding_dim=12, dropout=0.1, kernel_size=2, levels=7)

    扩张因子按 ``2**i (i=0..levels-1)`` 生成。levels=7 时感受野
    RF = 1 + Σ(kernel-1)×d = 1+2×(1+2+4+8+16+32+64) = 128 ≥ 96 步历史窗口。
    若需覆盖更大窗口（如特殊数据配置），通过 levels 参数上调。

    参数
    ----
    input_dim:
        输入特征维度 ``F``。
    horizon:
        预测步数 ``H``。
    num_nodes:
        节点数 ``N``。
    adjacencies:
        预定义邻接矩阵序列，可迭代（如 ``[R, N, N]`` 列表或 numpy 数组列表）。
        构造时按关系维取平均，得到 ``[N, N]`` 预定义图。
    hidden_dim:
        时间/空间隐藏通道数 ``C``；10 节点小场景下 32 泛化优于 64。
    embedding_dim:
        自适应图节点嵌入维度，用于学习 ``A_adp``。
    dropout:
        门控卷积与网络内的随机失活概率。
    kernel_size:
        因果卷积核大小，默认 2。
    levels:
        扩张卷积层数，默认 7。减少层数会缩小感受野，必须 ≥ ceil(log2(history_steps/(kernel_size-1)+1))。
    """

    def __init__(
        self,
        input_dim: int,
        horizon: int,
        num_nodes: int,
        adjacencies: Sequence[torch.Tensor],
        *,
        hidden_dim: int = 32,
        embedding_dim: int = 12,
        dropout: float = 0.1,
        kernel_size: int = 2,
        levels: int = 7,
    ) -> None:
        super().__init__()
        if num_nodes <= 0:
            raise ValueError("num_nodes 必须为正整数")
        if horizon <= 0:
            raise ValueError("horizon 必须为正整数")
        if input_dim <= 0:
            raise ValueError("input_dim 必须为正整数")
        if hidden_dim <= 0:
            raise ValueError("hidden_dim 必须为正整数")
        if embedding_dim <= 0:
            raise ValueError("embedding_dim 必须为正整数")
        if kernel_size <= 0:
            raise ValueError("kernel_size 必须为正整数")
        if not 0.0 <= dropout <= 1.0:
            raise ValueError("dropout 必须在 [0.0, 1.0] 范围内")
        if levels <= 0:
            raise ValueError("levels 必须为正整数")
        # 感受野校验：必须覆盖 history_steps（默认 96），
        # 否则模型在预测时缺少足够历史信息
        rf = 1 + sum((kernel_size - 1) * (2**i) for i in range(levels))
        if rf < 96:
            raise ValueError(
                f"levels={levels} 时感受野 RF={rf} < 96 步历史窗口，"
                "无法覆盖完整的输入时间上下文"
            )
        self.num_nodes = num_nodes
        self.hidden_dim = hidden_dim
        self.horizon = horizon

        # 预定义图：构造时传入的三类固定关系邻接矩阵按关系维取平均
        adjacency_list = [torch.as_tensor(a, dtype=torch.float32) for a in adjacencies]
        if not adjacency_list:
            raise ValueError("adjacencies 不能为空")
        expected_shape = (num_nodes, num_nodes)
        for idx, a in enumerate(adjacency_list):
            if a.shape != expected_shape:
                raise ValueError(
                    f"adjacencies[{idx}] 形状必须为 {list(expected_shape)}，"
                    f"实际为 {list(a.shape)}"
                )
        A_pre = torch.stack(adjacency_list).mean(dim=0)  # [N, N]
        self.register_buffer("A_pre", A_pre)

        # 输入投影：1x1 卷积将特征维 F 映射到隐藏通道 C
        self.start_conv = nn.Conv1d(input_dim, hidden_dim, kernel_size=1)

        # 扩张因子序列：按 levels 生成指数增长序列，
        # levels=7 → [1,2,4,8,16,32,64]，感受野 128 步 ≥ 96 步历史窗口
        self.dilations = [2**i for i in range(levels)]
        self.blocks = nn.ModuleList([
            _GraphWaveNetBlock(
                hidden_dim,
                num_nodes,
                embedding_dim,
                kernel_size,
                dilation,
                dropout,
            )
            for dilation in self.dilations
        ])

        # 末端 1x1 卷积：汇聚 skip 信息并映射到 latent 空间
        self.end_conv = nn.Conv1d(hidden_dim, hidden_dim, kernel_size=1)
        self.head = nn.Linear(hidden_dim, horizon)
        self.latent_dim = hidden_dim

    def _temporal_features(self, x: torch.Tensor) -> torch.Tensor:
        """提取完整时间轴上的节点隐表示。

        输入 ``[B, T, N, F]``，输出 ``[B, N, D, T]``，其中 ``D=hidden_dim``。
        用于内部因果性测试，也支撑 ``encode`` 取最后时刻的预测范式。
        """
        if x.ndim != 4:
            raise ValueError("Graph WaveNet 输入必须为 [B, T, N, F]")
        b, t, n, f = x.shape
        if n != self.num_nodes:
            raise ValueError(
                f"输入节点数 {n} 与模型节点数 {self.num_nodes} 不一致"
            )
        if f != self.start_conv.in_channels:
            raise ValueError(
                f"输入特征维 {f} 与模型输入维 {self.start_conv.in_channels} 不一致"
            )
        # [B, T, N, F] → [B*N, F, T]，每个节点为独立 Conv1d 样本
        hidden = x.permute(0, 2, 3, 1).reshape(b * n, f, t)
        hidden = self.start_conv(hidden).reshape(b, n, self.hidden_dim, t)

        skip = torch.zeros_like(hidden)
        for block in self.blocks:
            hidden, skip_i = block(hidden, self.A_pre)
            skip = skip + skip_i

        out = F.relu(skip).reshape(b * n, self.hidden_dim, t)
        out = F.relu(self.end_conv(out)).reshape(b, n, self.hidden_dim, t)
        return out

    def forward(self, x: torch.Tensor, **_: torch.Tensor) -> ForecastOutput:
        """前向传播，返回包含邻接矩阵的完整输出。

        覆写基类以暴露预定义图与自适应图的混合邻接矩阵，
        供可解释性分析与邻接可视化使用（与 StaticGraph/AdaptiveGraph 接口一致）。
        """
        latent = self.encode(x)
        # 使用最后一层的自适应图卷积重建邻接矩阵（最深语义层）
        last_gconv = self.blocks[-1].graph_conv
        A_adp = F.softmax(F.relu(last_gconv.E1 @ last_gconv.E2.t()), dim=1)
        return ForecastOutput(
            prediction=self.forecast_from_latent(latent),
            adjacency=self.A_pre + A_adp,
        )

    def encode(self, x: torch.Tensor) -> torch.Tensor:
        """将 ``[B, T, N, F]`` 编码为 ``[B, N, D]`` 节点隐表示。

        取完整时间特征 ``_temporal_features`` 的最后一个时间步作为当前时刻隐状态。
        """
        return self._temporal_features(x)[..., -1]

    def forecast_from_latent(self, latent: torch.Tensor) -> torch.Tensor:
        """由 ``[B, N, D]`` 隐表示生成 ``[B, H, N]`` 预测。

        使用逐节点线性头，与 SG-EXP-002 TCN 的解码方式保持一致。
        """
        prediction = self.head(latent)  # [B, N, H]
        # [B, N, H] → [B, H, N]，匹配项目统一预测格式
        return prediction.permute(0, 2, 1).contiguous()
