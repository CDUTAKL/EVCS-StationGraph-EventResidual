"""SG-EXP-009：全节点历史展平的 MLP 基线模型。

本模块实现"无图结构但有跨节点信息"的对照基线，用于回答论文的关键问题：
跨节点交互信息是否必须依赖图结构（归纳偏置）才能转化为预测增益？

与 TCN（逐节点独立、无跨节点信息）和 StaticGraph（有跨节点信息、有图结构）
相比，MLP 处于信息谱系的中间位置：它能接触到与图模型完全相同的全节点历史，
但没有任何关系先验，只能靠全连接层自己学出跨节点模式。因此：

- 若 MLP 显著差于 StaticGraph → 图结构（而非信息可得性）是增益来源，
  论文核心命题成立；
- 若 MLP 接近甚至优于 StaticGraph → 图建模的必要性存疑，需重新审视结论。

参数量说明：全展平设计的第一层权重为 (T×N×F)×hidden_dim
（96×10×7=6720 输入、hidden=32 时约 215K），远大于 StaticGraph 的 ~32K。
这是有意为之——给 MLP 更大的容量预算后，若其仍落后于图模型，
"图结构必要"的结论反而更强，因为排除了容量差异这一混淆因素。
"""

from __future__ import annotations

import torch
from torch import nn

from evcs_station_graph.models.common import ForecastModel


class MLPBaseline(ForecastModel):
    """将全部节点历史展平为单向量的三层 MLP 预测基线。

    结构：flatten([B, T, N, F]) → Linear+ReLU+Dropout → Linear+ReLU+Dropout
    → Linear → reshape([B, H, N])。共三个全连接层，前两层带非线性与
    dropout，最后一层为预测头。

    接口适配说明：ForecastModel 契约约定 encode 产出 ``[B, N, D]``
    逐节点隐表示。MLP 的全局向量通过 expand 广播为 ``[B, N, D]``
    （零拷贝视图，所有节点行相同），forecast_from_latent 将其重新展平
    为 ``[B, N×D]`` 后经全连接头解码——逐节点预测差异由解码器权重
    分块产生，而非隐表示本身。这样基类 forward 与
    EventResidualCorrection 等包装器在形状契约上均可透明工作。
    由于输入行相同，head 的有效秩仅为 D，多出的参数是契约合规的
    代价，不影响"无图结构"这一实验变量的纯净性。
    """

    def __init__(
        self,
        input_dim: int,
        horizon: int,
        num_nodes: int,
        *,
        hidden_dim: int = 32,
        history_steps: int = 96,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        if history_steps <= 0:
            raise ValueError("history_steps 必须为正整数")
        if num_nodes <= 0:
            raise ValueError("num_nodes 必须为正整数")
        self.horizon = horizon
        self.num_nodes = num_nodes
        self.history_steps = history_steps
        self.latent_dim = hidden_dim
        # 展平维度固定：MLP 不像卷积那样对时间维有弹性，
        # 输入窗口长度变化必须显式报错而非静默错位
        self.flat_dim = history_steps * num_nodes * input_dim

        self.trunk = nn.Sequential(
            nn.Linear(self.flat_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
        )
        # head 输入为展平的 [N×D] 隐表示（encode 广播后的 N 行相同，
        # 有效秩仅 D），输出按 (节点, 预测步) 分块，保证逐节点预测可不同
        self.head = nn.Linear(num_nodes * hidden_dim, num_nodes * horizon)

    def encode(self, x: torch.Tensor) -> torch.Tensor:
        """将 [B, T, N, F] 展平编码为全局向量，并广播为 [B, N, D]。"""
        if x.ndim != 4:
            raise ValueError("MLP 输入必须为 [B, T, N, F]")
        flat = x.flatten(start_dim=1)
        if flat.shape[1] != self.flat_dim:
            raise ValueError(
                f"MLP 基线要求输入展平后为 {self.flat_dim} 维"
                f"（history_steps={self.history_steps} × num_nodes={self.num_nodes}"
                f" × input_dim），实际为 {flat.shape[1]} 维，"
                "请检查数据窗口与配置是否一致"
            )
        global_latent = self.trunk(flat)
        return global_latent.unsqueeze(1).expand(-1, self.num_nodes, -1)

    def forecast_from_latent(self, latent: torch.Tensor) -> torch.Tensor:
        """将 [B, N, D] 隐表示重新展平后解码为 [B, H, N] 预测。

        显式校验形状而非用 squeeze 自适应：后者会对错误形状静默放行，
        把隐表示错位成伪样本而不报任何错误。
        """
        if (
            latent.ndim != 3
            or latent.shape[1] != self.num_nodes
            or latent.shape[2] != self.latent_dim
        ):
            raise ValueError(
                f"MLPBaseline.forecast_from_latent 期望 latent 形状为 "
                f"[B, {self.num_nodes}, {self.latent_dim}]，"
                f"实际为 {tuple(latent.shape)}"
            )
        output = self.head(latent.reshape(latent.shape[0], -1))
        return output.view(-1, self.num_nodes, self.horizon).permute(0, 2, 1).contiguous()
