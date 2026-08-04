"""SG-EXP-018：GRU 循环时序基线。

本模块实现逐节点独立共享权重的 GRU 预测模型，作为循环时序基线，
与 TCN（卷积时序基线，SG-EXP-002）互为对照，用于第 3 章主表对比。

与 TCN 的差异：
- TCN 以因果膨胀卷积并行编码全窗口（levels=6 时感受野 127 步，覆盖
  96 步历史窗口）；GRU 以循环状态顺序扫描 96 步历史，取最后一步隐状态
  作为节点表征；
- 两者均为逐节点独立（共享权重、无跨节点聚合），评价口径一致：
  GRU 与 TCN 的差距度量"循环 vs 卷积"时序编码族的性能差异，
  图模块的增益仍由 TCN vs StaticGraph 单独度量（53.4%，表 3-1）。

历史：该模型原为快速验证脚本（validate_variant_single_seed.py 的
GruForecast，D6-4 quick check）的一部分，2026-08-04 升级为正式模型
（SG-EXP-018），通过工厂统一入口运行三种子正式实验，输出完整工件
（metrics.json 含 RMSE/WAPE/非零负荷分层指标、predictions.csv、
diagnostics.json）。
"""

from __future__ import annotations

import torch
from torch import nn

from evcs_station_graph.models.common import ForecastModel


class GruForecast(ForecastModel):
    """GRU 时序基线：逐节点独立 GRU 编码 → 预测头（无图）。

    节点维展开为批维后共享同一 GRU 单元（与 TCN 逐节点独立卷积的
    参数共享口径一致），预测头为单层线性映射，输出 [B,H,N]。
    注意：model_params 的 dropout 对 GRU 不生效（num_layers=1 时
    PyTorch GRU 的 dropout 无意义，num_layers>1 时也未透传），
    基线实验统一不使用 dropout。
    """

    def __init__(
        self,
        input_dim: int,
        horizon: int,
        num_nodes: int,
        *,
        hidden_dim: int = 32,
        num_layers: int = 1,
    ) -> None:
        super().__init__()
        # num_nodes 当前仅用于接口一致（共享 GRU 不区分节点）；
        # 保留参数以便未来 per-node 变体扩展
        self.gru = nn.GRU(input_dim, hidden_dim, num_layers, batch_first=True)
        self.head = nn.Linear(hidden_dim, horizon)
        self.latent_dim = hidden_dim
        self.horizon = horizon

    def encode(self, x: torch.Tensor) -> torch.Tensor:
        """[B,T,N,F] → [B,N,D]：节点维展开为批维，GRU 编码后取最后一步。

        permute/reshape：[B,T,N,F] → [B*N,T,F]（逐节点独立序列），
        编码输出 [B*N,T,D] 取末步后还原为 [B,N,D]。
        """
        batch, time_steps, nodes, features = x.shape
        per_node = x.permute(0, 2, 1, 3).reshape(batch * nodes, time_steps, features)
        output, _ = self.gru(per_node)  # [B*N,T,D]
        return output[:, -1, :].reshape(batch, nodes, -1)  # [B,N,D]

    def forecast_from_latent(self, latent: torch.Tensor) -> torch.Tensor:
        """[B,N,D] → [B,H,N]：线性头映射后置换 horizon 维到第二位。"""
        return self.head(latent).permute(0, 2, 1).contiguous()  # [B,H,N]
