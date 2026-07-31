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
  - ``"mlp"``：全节点历史展平的无图基线（SG-EXP-009）。
    展平维度依赖 ``project.history_steps``，缺失时报错而非静默猜测。
  - ``"agcrn"``：AGCRN 自适应图基线（SG-EXP-008，NeurIPS 2020）。
  - ``"graph_wavenet"`` / ``"gwnet"``：Graph WaveNet 时空图基线
    （SG-EXP-010，IJCAI 2019），使用三类固定关系均值作为预定义图。
  - ``"decomp_gcn"`` / ``"decomposition_gcn"``：多分辨率分解 + 关系路由
    GCN（SG-EXP-011）。将信号分解为趋势/周期/瞬变三分量，
    各分量通过最相关的关系图独立传播后门控融合。
    通过 ``model_params.routing`` 控制路由策略（one_to_one/full/swapped）。

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
    AGCRNForecast,
    DecompGCNForecast,
    EventResidualCorrection,
    ForecastModel,
    GraphWaveNetForecast,
    MLPBaseline,
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
    # 历史窗口长度：TCN 感受野校验依赖它。TCN 系为"有配置即校验"的可选
    # 增强——缺失或非法时跳过校验（不破坏未配置该字段的旧实验）；
    # MLP 分支对展平维度是硬依赖，保留严格校验（见下）
    raw_history = config.get("project", {}).get("history_steps", 0)
    if isinstance(raw_history, bool) or not isinstance(raw_history, int) or raw_history <= 0:
        history_steps = None
    else:
        history_steps = raw_history
    # 图基线模型共用的隐藏层/嵌入/dropout 参数
    graph_kwargs = {
        "hidden_dim": common["hidden_dim"],
        "embedding_dim": int(params.get("embedding_dim", 12)),
        "dropout": common["dropout"],
    }
    # 关系 dropout（SG-EXP-006 敏感性实验）：从 experiment.graph 读取，
    # 与 mechanism.py 派生变体的写入位置保持一致；未配置时为 0.0（关闭），
    # 保证未启用该机制的实验行为完全不变。
    relation_dropout = float(experiment.get("graph", {}).get("relation_dropout", 0.0))

    if model_name in {"TCN", "temporal"}:
        return TemporalConvNet(
            input_dim, horizon, history_steps=history_steps, **common,
        )

    if model_name in {"mlp", "mlp_baseline"}:
        if history_steps is None:
            raise ValueError(
                "MLP 基线需要 project.history_steps 确定输入展平维度，"
                "请在项目配置中提供（正整数，浮点/布尔会被拒绝）"
            )
        return MLPBaseline(
            input_dim,
            horizon,
            num_nodes,
            hidden_dim=common["hidden_dim"],
            history_steps=history_steps,
            dropout=common["dropout"],
        )

    if model_name in {"agcrn"}:
        return AGCRNForecast(input_dim, horizon, num_nodes, adjacencies, **graph_kwargs)

    if model_name in {"graph_wavenet", "gwnet"}:
        return GraphWaveNetForecast(input_dim, horizon, num_nodes, adjacencies, **graph_kwargs)

    if model_name in {"decomp_gcn", "decomposition_gcn"}:
        return DecompGCNForecast(
            input_dim, horizon, num_nodes, adjacencies,
            hidden_dim=common["hidden_dim"],
            levels=int(params.get("levels", 6)),
            dropout=common["dropout"],
            routing=str(params.get("routing", "one_to_one")),
            trend_kernel=int(params.get("trend_kernel", 12)),
            season_kernel=int(params.get("season_kernel", 4)),
        )

    if model_name in {"TCN_GCN", "static_graph"}:
        return StaticGraphForecast(
            input_dim, horizon, num_nodes, adjacencies,
            relation_dropout=relation_dropout, history_steps=history_steps, **common,
        )

    if model_name in {"adaptive_graph"}:
        return AdaptiveGraphForecast(
            input_dim, horizon, num_nodes, adjacencies,
            embedding_dim=int(params.get("embedding_dim", 12)),
            fixed_weight=float(params.get("fixed_weight", 0.3)),
            top_k=int(params.get("top_k", 5)),
            relation_dropout=relation_dropout, history_steps=history_steps, **common,
        )

    if model_name in {"event_residual", "frozen_event_gated_residual_correction"}:
        base_model_type = str(params.get("base_model_type", "temporal"))
        freeze_base = bool(params.get("freeze_base", base_checkpoint is not None))
        if freeze_base and base_checkpoint is None:
            raise ValueError(
                "冻结默认路径时必须提供对应随机种子的基模型检查点"
            )

        if base_model_type == "temporal":
            base: ForecastModel = TemporalConvNet(
                input_dim, horizon, history_steps=history_steps, **common,
            )
        elif base_model_type == "static_graph":
            base = StaticGraphForecast(
                input_dim, horizon, num_nodes, adjacencies,
                relation_dropout=relation_dropout, history_steps=history_steps, **common,
            )
        elif base_model_type == "adaptive_graph":
            base = AdaptiveGraphForecast(
                input_dim, horizon, num_nodes, adjacencies,
                embedding_dim=int(params.get("embedding_dim", 12)),
                fixed_weight=float(params.get("fixed_weight", 0.3)),
                top_k=int(params.get("top_k", 5)),
                relation_dropout=relation_dropout, history_steps=history_steps, **common,
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
        prefix = "base_model."
        return {
            key[len(prefix):]: value
            for key, value in state.items()
            if key.startswith(prefix)
        }
    return state
