"""模型工厂，保证训练入口不包含分散的模型分支逻辑。

所有实验配置通过 ``model`` 字段选择模型类型，工厂负责创建对应的模块实例。
模型名的别名（如 "TCN"="temporal"、"GraphWaveNet_style"="adaptive_graph"）
是为了兼容不同论文和框架的命名习惯，逻辑上完全等价。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import torch

from evcs_station_graph.models import (
    AdaptiveGraphForecast,
    EventResidualCorrection,
    ForecastModel,
    StaticGraphForecast,
    TemporalConvNet,
)


def build_model(
    config: dict[str, Any],
    *,
    input_dim: int,
    horizon: int,
    num_nodes: int,
    adjacency: np.ndarray,
    base_checkpoint: str | Path | None = None,
) -> torch.nn.Module:
    """根据解析后的实验配置创建模型。"""
    experiment = config["experiment"]
    params = experiment.get("model_params", {})
    model_name = str(experiment.get("model", experiment.get("model_family", ["TCN"])[0]))
    common = {
        "hidden_dim": int(params.get("hidden_dim", 32)),
        "levels": int(params.get("levels", 3)),
        "dropout": float(params.get("dropout", 0.1)),
    }

    if model_name in {"TCN", "temporal"}:
        return TemporalConvNet(input_dim, horizon, **common)
    if model_name in {"TCN_GCN", "static_graph"}:
        return StaticGraphForecast(input_dim, horizon, adjacency, **common)
    if model_name in {"GraphWaveNet_style", "AGCRN_style", "adaptive_graph"}:
        return AdaptiveGraphForecast(
            input_dim,
            horizon,
            num_nodes,
            embedding_dim=int(params.get("embedding_dim", 12)),
            fixed_adjacency=adjacency,
            fixed_weight=float(params.get("fixed_weight", 0.2)),
            **common,
        )
    if model_name in {"event_residual", "frozen_event_gated_residual_correction"}:
        freeze_base = bool(params.get("freeze_base", base_checkpoint is not None))
        if freeze_base and base_checkpoint is None:
            raise ValueError(
                "冻结默认路径时必须提供对应随机种子的 SG-EXP-002 检查点"
            )
        base = TemporalConvNet(input_dim, horizon, **common)
        if base_checkpoint is not None:
            payload = torch.load(base_checkpoint, map_location="cpu", weights_only=True)
            state = payload.get("model_state", payload)
            base.load_state_dict(_extract_base_state(state), strict=True)
        return EventResidualCorrection(
            base,
            adjacency,
            horizon,
            hidden_dim=int(params.get("residual_hidden_dim", 32)),
            residual_bound=float(params.get("residual_bound", 0.5)),
            freeze_base=freeze_base,
        )
    raise ValueError(f"不支持的模型：{model_name}")


def _extract_base_state(state: dict[str, torch.Tensor]) -> dict[str, torch.Tensor]:
    """兼容两种检查点格式，提取基模型（TCN）的权重。

    格式 1（SG-EXP-002 检查点）：键名如 ``network.0.conv.weight``
      → 直接返回全量 state_dict，因为整个检查点就是 TCN

    格式 2（SG-EXP-005 检查点）：键名如 ``base_model.network.0.conv.weight``
      → 需要去掉 ``base_model.`` 前缀，因为 EventResidualCorrection
        将 TCN 包装在 self.base_model 属性中

    通过检测任意键是否以 ``base_model.`` 开头来区分两种格式。
    """
    if any(key.startswith("base_model.") for key in state):
        return {
            key.removeprefix("base_model."): value
            for key, value in state.items()
            if key.startswith("base_model.")
        }
    return state
