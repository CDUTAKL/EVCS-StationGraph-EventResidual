"""SG-EXP-005：验证集冻结规则驱动的事件残差修正。

本模块实现"冻结默认路径 + 事件门控 + 有界局部残差"的三段式修正架构。

三段式架构：
1. **默认路径（冻结）**：复用 SG-EXP-002 的 TCN，不更新参数。
   保证非事件窗口内的预测与基线完全一致。
2. **修正 MLP（可训练）**：以节点自身隐表示和"邻居与自身的差异"
   （neighbor - self）作为输入，输出有界残差。差异量捕捉了
   "图信息告诉你的、时间信息没告诉你的"部分。
3. **事件门控（冻结）**：验证集确定的规则矩阵 ``rule_trigger``
   控制哪些样本/节点/预测步长进入修正路径。门关闭时残差为零。

最终预测：prediction = base + gate × clip(correction, ±residual_bound)
"""

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
        """切换训练模式，但始终保持冻结的基模型为 eval 模式。

        这样设计的原因是：即使残差修正 MLP 在训练，基模型的 BatchNorm/Dropout
        等状态相关层也不能改变行为——否则修正器学到的是"基模型在训练模式的
        随机波动"而非"基模型推理时的系统偏差"。
        """
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
        # ---- 第一步：默认路径预测（冻结，不计算梯度） ----
        # 选择 no_grad 或 null_context 取决于 freeze_base 设置
        context = torch.no_grad() if self.freeze_base else _null_context()
        with context:
            base_latent = self.base_model.encode(x)       # [B, N, D]
            base_prediction = self.base_model.forecast_from_latent(base_latent)  # [B, H, N]

        # ---- 第二步：构造修正 MLP 的输入 ----
        # 邻居聚合：与 graph.py 相同的消息传递逻辑
        neighbor = torch.einsum("nm,bmd->bnd", self.adjacency, base_latent)
        # 关键设计：输入 = [自身隐表示, 邻居与自身的差异]
        # 差异量捕捉了"图信息告诉你的、时间信息没告诉你的"部分——
        # 如果邻居信息与自身信息一致，差异→0，correction→0
        correction_input = torch.cat([base_latent, neighbor - base_latent], dim=-1)

        # ---- 第三步：有界残差生成 ----
        # correction MLP 输出经过 Tanh → [-1, 1] → 乘以 residual_bound
        # 这保证每条修正的幅度不超过 residual_bound（单位：标准化后负荷）
        residual = self.corrector(correction_input).permute(0, 2, 1).contiguous()
        residual = residual * self.residual_bound

        # ---- 第四步：事件门控 ----
        if rule_trigger is None:
            # 无门控消融模式：所有样本均进入修正路径
            gate = torch.ones_like(residual)
        else:
            gate = rule_trigger.to(dtype=residual.dtype)
            # 维度自适应：rule_trigger 可以是 [B, N]（per-node 门控）
            # 或 [B, H, N]（per-node-per-horizon 门控）
            if gate.ndim == 2:
                gate = gate[:, None, :].expand_as(residual)
            if gate.shape != residual.shape:
                raise ValueError("rule_trigger 必须为 [B,N] 或 [B,H,N]")

        final_prediction = base_prediction + gate * residual
        return ForecastOutput(
            prediction=final_prediction,
            base_prediction=base_prediction,       # 保留默认预测用于量化修正幅度
            residual=gate * residual,               # 仅报告实际施加的残差
            adjacency=self.adjacency,
        )


class _null_context:
    """当基模型不冻结时，替代 ``torch.no_grad()`` 的空操作上下文管理器。

    这种场景仅出现在消融实验中（如"自由训练整个模型"的对比组），
    正式实验（SG-EXP-005/006）始终启用冻结。
    """
