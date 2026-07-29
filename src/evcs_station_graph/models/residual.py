"""SG-EXP-005：验证集冻结规则驱动的事件残差修正。"""

from __future__ import annotations

import numpy as np
import torch
from torch import nn

from evcs_station_graph.models.common import ForecastModel, ForecastOutput


class EventResidualCorrection(nn.Module):
    """仅在规则触发位置叠加有界局部残差。

    该模块不改变默认路径结构，也不把触发规则学习成分类器。规则阈值在验证集
    上确定后冻结，测试阶段只执行既定分流。
    """

    def __init__(
        self,
        base_model: ForecastModel,
        adjacency: np.ndarray | torch.Tensor,
        horizon: int,
        *,
        hidden_dim: int = 32,
        residual_bound: float = 0.5,
        freeze_base: bool = True,
    ) -> None:
        super().__init__()
        self.base_model = base_model
        matrix = torch.as_tensor(adjacency, dtype=torch.float32)
        self.register_buffer("adjacency", matrix)
        self.residual_bound = float(residual_bound)
        self.freeze_base = bool(freeze_base)
        self.corrector = nn.Sequential(
            nn.Linear(base_model.latent_dim * 2, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, horizon),
            nn.Tanh(),
        )
        if freeze_base:
            for parameter in self.base_model.parameters():
                parameter.requires_grad_(False)

    def train(self, mode: bool = True) -> "EventResidualCorrection":
        super().train(mode)
        if self.freeze_base:
            self.base_model.eval()
        return self

    def forward(
        self,
        x: torch.Tensor,
        *,
        rule_trigger: torch.Tensor | None = None,
        **_: torch.Tensor,
    ) -> ForecastOutput:
        context = torch.no_grad() if self.freeze_base else _null_context()
        with context:
            base_latent = self.base_model.encode(x)
            base_prediction = self.base_model.forecast_from_latent(base_latent)
        neighbor = torch.einsum("nm,bmd->bnd", self.adjacency, base_latent)
        correction_input = torch.cat([base_latent, neighbor - base_latent], dim=-1)
        residual = self.corrector(correction_input).permute(0, 2, 1).contiguous()
        residual = residual * self.residual_bound
        if rule_trigger is None:
            gate = torch.ones_like(residual)
        else:
            gate = rule_trigger.to(dtype=residual.dtype)
            if gate.ndim == 2:
                gate = gate[:, None, :].expand_as(residual)
            if gate.shape != residual.shape:
                raise ValueError("rule_trigger 必须为 [B,N] 或 [B,H,N]")
        final_prediction = base_prediction + gate * residual
        return ForecastOutput(
            prediction=final_prediction,
            base_prediction=base_prediction,
            residual=gate * residual,
            adjacency=self.adjacency,
        )


class _null_context:
    def __enter__(self) -> None:
        return None

    def __exit__(self, *_: object) -> None:
        return None
