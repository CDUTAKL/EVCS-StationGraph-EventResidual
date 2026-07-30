"""SG-EXP-005：验证集冻结规则驱动的事件残差修正。

本模块实现"冻结默认路径 + 事件门控 + 有界局部残差"的三段式修正架构。

三段式架构：
1. **默认路径（冻结）**：复用前置实验的基模型，不更新参数。
   支持三种基模型类型（由 ``base_model_type`` 指定）：
   - ``"temporal"``：TCN（SG-EXP-002），仅依赖节点自身历史
   - ``"static_graph"``：StaticGraphForecast（SG-EXP-003），
     包含训练期固定的多关系图卷积编码
   - ``"adaptive_graph"``：AdaptiveGraphForecast（SG-EXP-004），
     在三类固定关系基础上增加节点嵌入学习的自适应图
   保证非事件窗口内的预测与基模型完全一致。
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
    """仅在规则触发位置叠加有界局部残差（SG-EXP-005）。

    支持三种冻结基模型类型（通过 ``base_model_type`` 指定）：
      - ``"temporal"``（默认）：TCN 纯时序编码器
      - ``"static_graph"``：StaticGraphForecast 固定图编码器
      - ``"adaptive_graph"``：AdaptiveGraphForecast 自适应图编码器

    修正 MLP 使用三类信息：
      H：当前节点隐状态（基模型编码输出）
      M：邻居聚合结果（多关系消息传递）
      E：预测起点的可见事件特征（接入/离站/活跃/负荷跳变）

    公式：
      ΔŶ = r_max · tanh(MLP([H, M-H, E]))
      Ŷ = Ŷ_base + m_t · ΔŶ

    ``adjacencies`` 支持多关系图——与 graph.py 的消息传递保持结构一致。
    ``feature_names`` 用于自动查找事件特征列索引，替代硬编码的 event_feat_indices。
    """

    def __init__(
        self,
        base_model: ForecastModel,
        adjacencies: np.ndarray | torch.Tensor | list,
        horizon: int,
        *,
        hidden_dim: int = 32,
        residual_bound: float = 0.5,
        freeze_base: bool = True,
        feature_names: tuple[str, ...] | None = None,
        base_model_type: str = "temporal",
    ) -> None:
        super().__init__()
        self.base_model = base_model
        self._base_type = base_model_type
        # 支持单个邻接矩阵或多关系矩阵列表
        if isinstance(adjacencies, (np.ndarray, torch.Tensor)):
            adjacencies = [adjacencies]
        for r, adj in enumerate(adjacencies):
            self.register_buffer(f"adj_{r}", torch.as_tensor(adj, dtype=torch.float32))
        self._num_adj = len(adjacencies)
        self.residual_bound = float(residual_bound)
        self.freeze_base = bool(freeze_base)
        # 事件特征索引：通过 feature_names 查找默认事件特征列
        # 默认查找 ["access_count", "departure_count", "active_count", "load_jump_flag"]
        # 找不到的特征静默跳过；全部找不到则报错
        if feature_names is not None:
            name_to_idx = {name: idx for idx, name in enumerate(feature_names)}
            found_indices: list[int] = []
            for feat_name in ("access_count", "departure_count", "active_count", "load_jump_flag"):
                idx = name_to_idx.get(feat_name)
                if idx is not None:
                    found_indices.append(idx)
            if not found_indices:
                raise ValueError(
                    f"在 feature_names={feature_names} 中未找到任何默认事件特征 "
                    f"(access_count, departure_count, active_count, load_jump_flag)"
                )
            self._event_feat_indices = found_indices
        else:
            # 向后兼容：未提供 feature_names 时使用硬编码索引
            self._event_feat_indices = [1, 2, 3, 6]
        n_event_feats = len(self._event_feat_indices)
        # 修正 MLP：[H, M-H, E] → hidden → horizon → tanh
        # correction_input 维度 = base_latent_dim * 2 + n_event_feats
        self.corrector = nn.Sequential(
            nn.Linear(base_model.latent_dim * 2 + n_event_feats, hidden_dim),
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
        context = torch.no_grad() if self.freeze_base else _null_context()
        with context:
            base_latent = self.base_model.encode(x)       # [B, N, D]
            base_prediction = self.base_model.forecast_from_latent(base_latent)  # [B, H, N]

        # ---- 第二步：多关系邻居聚合 ----
        # 对每类关系独立做消息传递后取平均——与 graph.py 的 GCN 保持一致结构
        adjs = [getattr(self, f"adj_{r}") for r in range(self._num_adj)]
        neighbor_parts = []
        for adj in adjs:
            neighbor_parts.append(torch.einsum("nm,bmd->bnd", adj, base_latent))
        M = torch.stack(neighbor_parts).mean(dim=0)  # [B, N, D] 平均多关系邻居信息

        # ---- 第三步：提取可见事件特征 E ----
        # 取预测起点（最后一个时间步）的事件相关特征
        # 这些特征在事件规则中用于计算分数，在此为修正 MLP 提供上下文
        E = x[:, -1, :, self._event_feat_indices]  # [B, N, F_event]

        # ---- 第四步：修正 MLP 输入 = [H, M - H, E] ----
        # M-H：邻居与自身的差异，捕捉图信息独有的增量
        # E：预测起点的可见事件特征，提供触发上下文
        correction_input = torch.cat([base_latent, M - base_latent, E], dim=-1)

        # ---- 第五步：有界残差生成 ----
        residual = self.corrector(correction_input).permute(0, 2, 1).contiguous()
        residual = residual * self.residual_bound

        # ---- 第六步：事件门控 ----
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
            adjacency=adjs[0] if adjs else None,
        )


class _null_context:
    """当基模型不冻结时，替代 ``torch.no_grad()`` 的空操作上下文管理器。

    这种场景仅出现在消融实验中（如"自由训练整个模型"的对比组），
    正式实验（SG-EXP-005/006）始终启用冻结。
    """
