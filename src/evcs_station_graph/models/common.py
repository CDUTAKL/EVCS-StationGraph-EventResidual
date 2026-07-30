"""模型公共结构与统一输出。

设计决策：所有预测模型遵循"编码→预测"两阶段接口，而非单一 forward。
这样做的原因是 SG-EXP-005 需要复用基模型的编码器（提取隐表示作为修正 MLP
的输入），而不重复执行前向推理。如果采用单阶段 forward，Residual 模型
要么内部调用 base_model（增加一次不必要的编码），要么复制编码逻辑。
"""

from __future__ import annotations

from dataclasses import dataclass

import torch
from torch import nn


@dataclass
class ForecastOutput:
    """所有模型统一返回的预测及可解释中间量。

    各字段语义：
    - ``prediction``：形状 ``[B, H, N]`` 的最终预测（可能含残差修正）
    - ``base_prediction``：仅当使用 EventResidualCorrection 时有值，
      表示修正前的默认预测，用于量化修正幅度
    - ``residual``：实际施加的残差（含门控和限幅后），
      ``prediction = base_prediction + residual``
    - ``adjacency``：图模型使用的邻接矩阵，用于可解释性分析
    """

    prediction: torch.Tensor
    base_prediction: torch.Tensor | None = None
    residual: torch.Tensor | None = None
    adjacency: torch.Tensor | None = None


class ForecastModel(nn.Module):
    """预测模型统一接口。

    子类只需实现 ``encode`` 和 ``forecast_from_latent``，``forward``
    由基类统一处理。这保证训练循环可以透明地调用任意模型，而残差修正
    模型可以拦截编码阶段复用隐表示。
    """

    latent_dim: int

    def encode(self, x: torch.Tensor) -> torch.Tensor:
        """将 ``[B, T, N, F]`` 输入编码为 ``[B, N, D]`` 节点隐表示。

        各节点独立编码还是交互编码，由子类决定。TCN 独立编码每个节点；
        Graph 模型通过消息传递让邻居信息进入隐表示。
        """
        raise NotImplementedError

    def forecast_from_latent(self, latent: torch.Tensor) -> torch.Tensor:
        """由 ``[B, N, D]`` 隐表示生成 ``[B, H, N]`` 预测。

        简单的线性投影 + permute，子类可覆写为更复杂的解码器。
        """
        raise NotImplementedError

    def forward(self, x: torch.Tensor, **_: torch.Tensor) -> ForecastOutput:
        latent = self.encode(x)
        return ForecastOutput(prediction=self.forecast_from_latent(latent))
