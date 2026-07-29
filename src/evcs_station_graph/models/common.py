"""模型公共结构与统一输出。"""

from __future__ import annotations

from dataclasses import dataclass

import torch
from torch import nn


@dataclass
class ForecastOutput:
    """所有模型统一返回的预测及可解释中间量。"""

    prediction: torch.Tensor
    base_prediction: torch.Tensor | None = None
    residual: torch.Tensor | None = None
    adjacency: torch.Tensor | None = None


class ForecastModel(nn.Module):
    """预测模型统一接口。"""

    latent_dim: int

    def encode(self, x: torch.Tensor) -> torch.Tensor:
        """返回形状为 ``[B, N, D]`` 的节点隐表示。"""
        raise NotImplementedError

    def forecast_from_latent(self, latent: torch.Tensor) -> torch.Tensor:
        """由节点隐表示生成 ``[B, H, N]`` 预测。"""
        raise NotImplementedError

    def forward(self, x: torch.Tensor, **_: torch.Tensor) -> ForecastOutput:
        latent = self.encode(x)
        return ForecastOutput(prediction=self.forecast_from_latent(latent))
