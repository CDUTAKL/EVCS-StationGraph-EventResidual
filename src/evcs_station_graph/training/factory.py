"""模型工厂，保证训练入口不包含分散的模型分支逻辑。

所有实验配置通过 ``model`` 字段选择模型类型，工厂负责创建对应的模块实例。
支持的模型名：
  - ``"temporal"`` / ``"TCN"``：纯时序 TCN（SG-EXP-002 默认路径）
  - ``"static_graph"`` / ``"TCN_GCN"``：固定图时空预测（SG-EXP-003）
  - ``"adaptive_graph"``：自适应图时空预测（SG-EXP-004）
  - ``"event_residual"``：事件门控残差修正（SG-EXP-005）。
    通过 ``model_params.base_model_type`` 选择冻结基模型类型：
    ``"temporal"``（默认）→ TCN；``"static_graph"`` → StaticGraphForecast；
    ``"adaptive_graph"`` → AdaptiveGraphForecast。
    非 temporal 基模型需通过 ``base_checkpoint`` 加载对应实验的检查点。

图相关公共参数：
  ``experiment.graph.relation_dropout``（默认 0.0，关闭）会传入
  StaticGraphForecast / AdaptiveGraphForecast 的两层 GCN 以及
  EventResidualCorrection 的邻居聚合，是 SG-EXP-006 关系 dropout
  敏感性实验的实际生效路径。
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
    adjacencies: list[np.ndarray],
    base_checkpoint: str | Path | None = None,
    feature_names: tuple[str, ...] | None = None,
) -> torch.nn.Module:
    """根据解析后的实验配置创建模型。

    ``adjacencies`` 为多类关系矩阵列表。
    仅 TCN 不使用该参数。

    ``feature_names`` 是特征列的顺序名称元组，用于
    EventResidualCorrection 自动查找事件特征列索引。
    非 event_residual 模型忽略此参数。
    """
    experiment = config["experiment"]
    params = experiment.get("model_params", {})
    model_name = str(experiment.get("model", experiment.get("model_family", ["TCN"])[0]))
    common = {
        "hidden_dim": int(params.get("hidden_dim", 32)),
        "levels": int(params.get("levels", 3)),
        "dropout": float(params.get("dropout", 0.1)),
    }
    # 关系 dropout（SG-EXP-006 敏感性实验）：从 experiment.graph 读取，
    # 与 mechanism.py 派生变体的写入位置保持一致；未配置时为 0.0（关闭），
    # 保证未启用该机制的实验行为完全不变。
    relation_dropout = float(experiment.get("graph", {}).get("relation_dropout", 0.0))

    if model_name in {"TCN", "temporal"}:
        return TemporalConvNet(input_dim, horizon, **common)

    if model_name in {"TCN_GCN", "static_graph"}:
        return StaticGraphForecast(
            input_dim, horizon, num_nodes, adjacencies,
            relation_dropout=relation_dropout, **common,
        )

    if model_name in {"adaptive_graph"}:
        return AdaptiveGraphForecast(
            input_dim, horizon, num_nodes, adjacencies,
            embedding_dim=int(params.get("embedding_dim", 12)),
            fixed_weight=float(params.get("fixed_weight", 0.3)),
            top_k=int(params.get("top_k", 5)),
            relation_dropout=relation_dropout, **common,
        )

    if model_name in {"event_residual", "frozen_event_gated_residual_correction"}:
        base_model_type = str(params.get("base_model_type", "temporal"))
        freeze_base = bool(params.get("freeze_base", base_checkpoint is not None))
        if freeze_base and base_checkpoint is None:
            raise ValueError(
                "冻结默认路径时必须提供对应随机种子的基模型检查点"
            )

        if base_model_type == "temporal":
            base: ForecastModel = TemporalConvNet(input_dim, horizon, **common)
        elif base_model_type == "static_graph":
            base = StaticGraphForecast(
                input_dim, horizon, num_nodes, adjacencies,
                relation_dropout=relation_dropout, **common,
            )
        elif base_model_type == "adaptive_graph":
            base = AdaptiveGraphForecast(
                input_dim, horizon, num_nodes, adjacencies,
                embedding_dim=int(params.get("embedding_dim", 12)),
                fixed_weight=float(params.get("fixed_weight", 0.3)),
                top_k=int(params.get("top_k", 5)),
                relation_dropout=relation_dropout, **common,
            )
        else:
            raise ValueError(f"不支持的基模型类型：{base_model_type}")

        if base_checkpoint is not None:
            payload = torch.load(base_checkpoint, map_location="cpu", weights_only=True)
            state = payload.get("model_state", payload)
            base.load_state_dict(_extract_base_state(state), strict=True)
        return EventResidualCorrection(
            base,
            adjacencies,
            horizon,
            hidden_dim=int(params.get("residual_hidden_dim", 32)),
            residual_bound=float(params.get("residual_bound", 0.5)),
            freeze_base=freeze_base,
            feature_names=feature_names,
            base_model_type=base_model_type,
            relation_dropout=relation_dropout,
        )
    raise ValueError(f"不支持的模型：{model_name}")


def _extract_base_state(state: dict[str, torch.Tensor]) -> dict[str, torch.Tensor]:
    """兼容两种检查点格式，提取基模型的权重。

    格式 1（直接检查点）：键名如 ``network.0.conv.weight``
      → 直接返回全量 state_dict，因为整个检查点就是基模型

    格式 2（EventResidualCorrection 检查点）：键名如 ``base_model.network.0.conv.weight``
      → 去掉 ``base_model.`` 前缀，因为 EventResidualCorrection
        将基模型包装在 self.base_model 属性中

    通过检测任意键是否以 ``base_model.`` 开头来区分两种格式。
    """
    if any(key.startswith("base_model.") for key in state):
        return {
            key.removeprefix("base_model."): value
            for key, value in state.items()
            if key.startswith("base_model.")
        }
    return state
