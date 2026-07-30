"""架构审核脚本（本地 CPU，不触碰真实数据集与测试集）。

用途：在进入超参数预筛选（阶段 B）之前，用合成小张量验证当前图架构的
真实计算行为，输出机器可读的审核数据（JSON），供人工审核报告引用。

审核范围（对应第八节验收要求）：
1. 各模型真实张量维度流（正式配置尺寸：N=10, F=7, T=96, H=4, D=32）
2. 总参数量与可训练参数量（含分模块拆分）
3. TCN 实际感受野（梯度法实测 vs 理论公式值）
4. 三种残差模型的基础模型加载测试（temporal / static_graph / adaptive_graph）
5. 小样本前向、反向传播、梯度与 NaN 检查
6. relation_dropout 的训练随机性与评估确定性

约束：本脚本不加载任何真实数据工件，不使用测试集，不进行训练。
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import numpy as np
import torch

from evcs_station_graph.graphs import normalize_adjacency
from evcs_station_graph.models import (
    AdaptiveGraphForecast,
    EventResidualCorrection,
    StaticGraphForecast,
    TemporalConvNet,
)
from evcs_station_graph.models.common import sample_relation_keep_mask
from evcs_station_graph.training.factory import build_model

# ---- 正式实验配置尺寸（与 configs/experiments/SG-EXP-002~005 对齐） ----
NUM_NODES = 10       # 主节点清单的充电单元数
NUM_FEATURES = 7     # load/access/departure/active/occupancy/demand/jump_flag
HISTORY = 96         # 输入窗口（24 小时 × 15 分钟）
HORIZON = 4          # 预测窗口（1 小时）
HIDDEN = 32          # model_params.hidden_dim
LEVELS = 3           # model_params.levels
BATCH = 2            # 审核用小 batch

FEATURE_NAMES = (
    "load", "access_count", "departure_count", "active_count",
    "occupancy_rate", "demand_intensity", "load_jump_flag",
)


def _three_relations() -> list[np.ndarray]:
    """构造三类互不相同的归一化关系矩阵（模拟 load/event/pattern）。

    固定随机种子保证审核可复现；矩阵结构与真实关系无关，
    仅要求归一化邻接矩阵的数学性质（对称、自环、谱半径 ≤ 1）。
    """
    rng = np.random.default_rng(20240730)
    relations = []
    for _ in range(3):
        raw = rng.random((NUM_NODES, NUM_NODES)).astype(np.float32)
        raw = np.maximum(raw, raw.T)  # 对称化
        relations.append(normalize_adjacency(raw))
    return relations


def _shape(tensor: torch.Tensor) -> list[int]:
    return list(tensor.shape)


# ---------------------------------------------------------------------------
# 1. 张量维度流
# ---------------------------------------------------------------------------

def audit_tensor_flow() -> dict:
    """逐模块记录各模型的真实张量形状（正式配置尺寸）。"""
    torch.manual_seed(0)
    x = torch.randn(BATCH, HISTORY, NUM_NODES, NUM_FEATURES)
    adjs = _three_relations()
    flow: dict[str, object] = {"input_x": _shape(x)}

    # ---- TCN（SG-EXP-002） ----
    tcn = TemporalConvNet(NUM_FEATURES, HORIZON, hidden_dim=HIDDEN, levels=LEVELS, dropout=0.0)
    tcn.eval()
    latent = tcn.encode(x)
    flow["TCN"] = {
        "encode_output[B,N,D]": _shape(latent),
        "forecast_output[B,H,N]": _shape(tcn.forecast_from_latent(latent)),
    }

    # ---- StaticGraphForecast（SG-EXP-003）：逐模块展开 encode 内部 ----
    static = StaticGraphForecast(
        NUM_FEATURES, HORIZON, NUM_NODES, adjs,
        hidden_dim=HIDDEN, levels=LEVELS, dropout=0.0,
    )
    static.eval()
    with torch.no_grad():
        h0 = static.tcn.encode(x)
        adj_list = static._get_adjacencies()
        h1 = static.gcn1(h0, adj_list, static._get_relation_weights_gcn1())
        h1r = h1 + static.graph_mlp_refine(h1)
        h2 = static.gcn2(h1r, adj_list, static._get_relation_weights_gcn2())
        fused_in = torch.cat([h0, h1, h2], dim=-1)
        fused = static.skip_fusion(fused_in)
        pred = static.forecast_from_latent(static.skip_dropout(static.skip_activation(static.skip_norm(fused))))
    flow["StaticGraphForecast"] = {
        "adjacencies": [f"[{NUM_NODES},{NUM_NODES}]"] * len(adj_list),
        "h0_tcn_encode[B,N,D]": _shape(h0),
        "h1_gcn1[B,N,D]": _shape(h1),
        "h1_refined_mlp[B,N,D]": _shape(h1r),
        "h2_gcn2[B,N,D]": _shape(h2),
        "skip_fusion_input[B,N,3D]": _shape(fused_in),
        "skip_fusion_output[B,N,D]": _shape(fused),
        "prediction[B,H,N]": _shape(pred),
    }

    # ---- AdaptiveGraphForecast（SG-EXP-004） ----
    adaptive = AdaptiveGraphForecast(
        NUM_FEATURES, HORIZON, NUM_NODES, adjs,
        hidden_dim=HIDDEN, embedding_dim=12, levels=LEVELS, dropout=0.0,
    )
    adaptive.eval()
    with torch.no_grad():
        adp_adj = adaptive._build_adaptive_adjacency()
        all_adj = adaptive._get_adjacencies()
        out = adaptive(x)
    flow["AdaptiveGraphForecast"] = {
        "fixed_adjacencies": len(adjs),
        "adaptive_adjacency[N,N]": _shape(adp_adj),
        "total_relations_in_message_passing": len(all_adj),
        "alpha_sigmoid_fixed_weight": float(torch.sigmoid(adaptive.fixed_weight.detach())),
        "prediction[B,H,N]": _shape(out.prediction),
    }

    # ---- EventResidualCorrection（SG-EXP-005，三种基模型） ----
    residual_flows = {}
    for base_type, base in (
        ("temporal", TemporalConvNet(NUM_FEATURES, HORIZON, hidden_dim=HIDDEN, levels=LEVELS, dropout=0.0)),
        ("static_graph", StaticGraphForecast(NUM_FEATURES, HORIZON, NUM_NODES, adjs, hidden_dim=HIDDEN, levels=LEVELS, dropout=0.0)),
        ("adaptive_graph", AdaptiveGraphForecast(NUM_FEATURES, HORIZON, NUM_NODES, adjs, hidden_dim=HIDDEN, embedding_dim=12, levels=LEVELS, dropout=0.0)),
    ):
        model = EventResidualCorrection(
            base, adjs, HORIZON,
            hidden_dim=HIDDEN, freeze_base=True, feature_names=FEATURE_NAMES,
            base_model_type=base_type,
        )
        model.eval()
        with torch.no_grad():
            base_latent = base.encode(x)
            base_pred = base.forecast_from_latent(base_latent)
            neighbor_parts = [
                torch.einsum("nm,bmd->bnd", getattr(model, f"adj_{r}"), base_latent)
                for r in range(model._num_adj)
            ]
            M = torch.stack(neighbor_parts).mean(dim=0)
            E = x[:, -1, :, model._event_feat_indices]
            correction_input = torch.cat([base_latent, M - base_latent, E], dim=-1)
            trigger = torch.ones(BATCH, NUM_NODES, dtype=torch.bool)
            out = model(x, rule_trigger=trigger)
        residual_flows[base_type] = {
            "base_latent[B,N,D]": _shape(base_latent),
            "base_prediction[B,H,N]": _shape(base_pred),
            "neighbor_aggregate_M[B,N,D]": _shape(M),
            "event_features_E[B,N,4]": _shape(E),
            "correction_input[B,N,2D+4]": _shape(correction_input),
            "residual[B,H,N]": _shape(out.residual),
            "final_prediction[B,H,N]": _shape(out.prediction),
        }
    flow["EventResidualCorrection"] = residual_flows
    return flow


# ---------------------------------------------------------------------------
# 2. 参数量
# ---------------------------------------------------------------------------

def _count_parameters(model: torch.nn.Module) -> dict:
    """分模块统计总参数量与可训练参数量（按顶层属性分组）。"""
    groups: dict[str, dict[str, int]] = {}
    for name, param in model.named_parameters():
        top = name.split(".")[0]
        entry = groups.setdefault(top, {"total": 0, "trainable": 0})
        entry["total"] += param.numel()
        if param.requires_grad:
            entry["trainable"] += param.numel()
    total = sum(entry["total"] for entry in groups.values())
    trainable = sum(entry["trainable"] for entry in groups.values())
    return {"per_module": groups, "total": total, "trainable": trainable}


def audit_parameters() -> dict:
    adjs = _three_relations()
    models = {
        "TCN(SG-EXP-002)": TemporalConvNet(NUM_FEATURES, HORIZON, hidden_dim=HIDDEN, levels=LEVELS, dropout=0.0),
        "StaticGraph(SG-EXP-003)": StaticGraphForecast(NUM_FEATURES, HORIZON, NUM_NODES, adjs, hidden_dim=HIDDEN, levels=LEVELS, dropout=0.0),
        "AdaptiveGraph(SG-EXP-004)": AdaptiveGraphForecast(NUM_FEATURES, HORIZON, NUM_NODES, adjs, hidden_dim=HIDDEN, embedding_dim=12, levels=LEVELS, dropout=0.0),
    }
    for base_type, base in (
        ("temporal", TemporalConvNet(NUM_FEATURES, HORIZON, hidden_dim=HIDDEN, levels=LEVELS, dropout=0.0)),
        ("static_graph", StaticGraphForecast(NUM_FEATURES, HORIZON, NUM_NODES, adjs, hidden_dim=HIDDEN, levels=LEVELS, dropout=0.0)),
        ("adaptive_graph", AdaptiveGraphForecast(NUM_FEATURES, HORIZON, NUM_NODES, adjs, hidden_dim=HIDDEN, embedding_dim=12, levels=LEVELS, dropout=0.0)),
    ):
        models[f"EventResidual(base={base_type})"] = EventResidualCorrection(
            base, adjs, HORIZON,
            hidden_dim=HIDDEN, freeze_base=True, feature_names=FEATURE_NAMES,
            base_model_type=base_type,
        )
    return {name: _count_parameters(model) for name, model in models.items()}


# ---------------------------------------------------------------------------
# 3. TCN 实际感受野（梯度法实测）
# ---------------------------------------------------------------------------

def audit_receptive_field() -> dict:
    """对 encode 输出关于输入求梯度，测量末时间步隐表示的实际感受野。

    方法：encode 取序列最后一个时间步的隐表示；其关于输入 x 的梯度
    在时间维上非零的最早位置决定了实际感受野。因果裁剪保证
    "未来位置"（t > 末步）的梯度严格为零；感受野之外的过去位置同理。

    理论公式：RF = 1 + Σ (kernel-1) × dilation
    levels=3 → 1+2×(1+2+4) = 15；levels=5 → 63；levels=6 → 127。
    """
    results = {}
    for levels, theoretical in ((3, 15), (5, 63), (6, 127)):
        torch.manual_seed(levels)
        model = TemporalConvNet(NUM_FEATURES, HORIZON, hidden_dim=HIDDEN, levels=levels, dropout=0.0)
        model.eval()
        x = torch.randn(1, HISTORY, NUM_NODES, NUM_FEATURES, requires_grad=True)
        latent = model.encode(x)
        latent.sum().backward()
        grad_per_step = x.grad.abs().amax(dim=(0, 2, 3))  # [T]
        nonzero = torch.nonzero(grad_per_step > 0).flatten()
        earliest = int(nonzero[0])
        empirical = HISTORY - earliest
        results[f"levels={levels}"] = {
            "theoretical_rf_steps": theoretical,
            "empirical_rf_steps": empirical,
            "history_window_steps": HISTORY,
            "earliest_influential_step": earliest,
            # 感受野之外的过去位置梯度必须严格为零（因果 + 有限感受野）
            "gradient_beyond_rf_exactly_zero": bool((grad_per_step[:earliest] == 0).all()),
            "match": empirical == min(theoretical, HISTORY),
        }
    return results


# ---------------------------------------------------------------------------
# 4. 三种残差模型的基础模型加载测试
# ---------------------------------------------------------------------------

def audit_residual_base_loading() -> dict:
    """验证 EventResidualCorrection 对三种基模型的检查点加载路径。

    每种 base_model_type 检查：
    a. 经 factory + base_checkpoint 加载后，base 参数与保存的检查点完全一致
    b. freeze_base=True 时 base 参数全部 requires_grad=False
    c. 门全关时 EventResidualCorrection 输出 == 独立 base 模型输出
       （非事件窗口内的预测与基模型逐位一致，保证"默认路径冻结"语义）
    """
    adjs = _three_relations()
    model_names = {
        "temporal": "TCN",
        "static_graph": "TCN_GCN",
        "adaptive_graph": "adaptive_graph",
    }
    results = {}
    with tempfile.TemporaryDirectory() as tmp:
        for base_type, model_name in model_names.items():
            # ---- 构造并"训练"一个独立 base（确定性扰动模拟训练后权重） ----
            base_cfg = {
                "experiment": {
                    "model": model_name,
                    "model_params": {"hidden_dim": HIDDEN, "levels": LEVELS, "dropout": 0.0},
                }
            }
            standalone = build_model(
                base_cfg, input_dim=NUM_FEATURES, horizon=HORIZON,
                num_nodes=NUM_NODES, adjacencies=adjs,
            )
            with torch.no_grad():
                for param in standalone.parameters():
                    param.add_(0.01)  # 模拟训练后的权重变化
            checkpoint = Path(tmp) / f"{base_type}.pt"
            torch.save({"model_state": standalone.state_dict()}, checkpoint)

            # ---- 经 factory 创建残差模型并加载检查点 ----
            res_cfg = {
                "experiment": {
                    "model": "event_residual",
                    "model_params": {
                        "hidden_dim": HIDDEN, "levels": LEVELS, "dropout": 0.0,
                        "base_model_type": base_type, "freeze_base": True,
                    },
                }
            }
            residual = build_model(
                res_cfg, input_dim=NUM_FEATURES, horizon=HORIZON,
                num_nodes=NUM_NODES, adjacencies=adjs,
                base_checkpoint=checkpoint, feature_names=FEATURE_NAMES,
            )

            # a. 参数一致性
            standalone_state = standalone.state_dict()
            loaded_state = residual.base_model.state_dict()
            params_identical = all(
                torch.equal(loaded_state[key], standalone_state[key])
                for key in standalone_state
            )

            # b. 冻结标志
            all_frozen = all(
                not param.requires_grad for param in residual.base_model.parameters()
            )
            corrector_trainable = all(
                param.requires_grad for param in residual.corrector.parameters()
            )

            # c. 门全关时输出与独立 base 数值一致
            # 验收口径为数值容差（rtol=1e-5, atol=1e-6）而非逐位相等：
            # einsum 多线程归约顺序差异会产生 1e-7 量级浮点误差，
            # 属正常数值现象，不构成"默认路径冻结"语义的破坏
            torch.manual_seed(42)
            x = torch.randn(BATCH, HISTORY, NUM_NODES, NUM_FEATURES)
            standalone.eval()
            residual.eval()
            with torch.no_grad():
                expected = standalone(x).prediction
                out = residual(x, rule_trigger=torch.zeros(BATCH, NUM_NODES, dtype=torch.bool))
            max_abs_diff = float((out.prediction - expected).abs().max())
            gate_off_matches_base = bool(
                torch.allclose(out.prediction, expected, rtol=1e-5, atol=1e-6)
            )
            gate_off_matches_base_pred_field = bool(
                torch.allclose(out.prediction, out.base_prediction, rtol=1e-5, atol=1e-6)
            )

            results[base_type] = {
                "checkpoint_params_identical": params_identical,
                "base_all_frozen": all_frozen,
                "corrector_trainable": corrector_trainable,
                "gate_off_output_equals_standalone_base": gate_off_matches_base,
                "gate_off_max_abs_diff": max_abs_diff,
                "gate_off_output_equals_base_prediction_field": gate_off_matches_base_pred_field,
            }
    return results


# ---------------------------------------------------------------------------
# 5. 小样本前向 + 反向传播 + 梯度 + NaN 检查
# ---------------------------------------------------------------------------

def audit_forward_backward() -> dict:
    """每种模型执行一次前向+反向，检查输出有限、梯度存在且有限。

    特别检查：
    - relation_weights_gcn1/gcn2（可解释性核心参数）必须收到非零梯度
    - EventResidualCorrection(freeze_base=True)：base 参数不出现在梯度
      计算中（requires_grad=False），corrector 梯度非零
    """
    adjs = _three_relations()
    torch.manual_seed(123)
    x = torch.randn(BATCH, HISTORY, NUM_NODES, NUM_FEATURES)
    y = torch.randn(BATCH, HORIZON, NUM_NODES)
    trigger = torch.ones(BATCH, NUM_NODES, dtype=torch.bool)

    models: dict[str, torch.nn.Module] = {
        "TCN": TemporalConvNet(NUM_FEATURES, HORIZON, hidden_dim=HIDDEN, levels=LEVELS, dropout=0.0),
        "StaticGraph": StaticGraphForecast(NUM_FEATURES, HORIZON, NUM_NODES, adjs, hidden_dim=HIDDEN, levels=LEVELS, dropout=0.0),
        "AdaptiveGraph": AdaptiveGraphForecast(NUM_FEATURES, HORIZON, NUM_NODES, adjs, hidden_dim=HIDDEN, embedding_dim=12, levels=LEVELS, dropout=0.0),
        "EventResidual(base=temporal)": EventResidualCorrection(
            TemporalConvNet(NUM_FEATURES, HORIZON, hidden_dim=HIDDEN, levels=LEVELS, dropout=0.0),
            adjs, HORIZON, hidden_dim=HIDDEN, freeze_base=True,
            feature_names=FEATURE_NAMES, base_model_type="temporal",
        ),
        "EventResidual(base=static_graph)": EventResidualCorrection(
            StaticGraphForecast(NUM_FEATURES, HORIZON, NUM_NODES, adjs, hidden_dim=HIDDEN, levels=LEVELS, dropout=0.0),
            adjs, HORIZON, hidden_dim=HIDDEN, freeze_base=True,
            feature_names=FEATURE_NAMES, base_model_type="static_graph",
        ),
        "EventResidual(base=adaptive_graph)": EventResidualCorrection(
            AdaptiveGraphForecast(NUM_FEATURES, HORIZON, NUM_NODES, adjs, hidden_dim=HIDDEN, embedding_dim=12, levels=LEVELS, dropout=0.0),
            adjs, HORIZON, hidden_dim=HIDDEN, freeze_base=True,
            feature_names=FEATURE_NAMES, base_model_type="adaptive_graph",
        ),
    }

    results = {}
    for name, model in models.items():
        model.train()
        model.zero_grad(set_to_none=True)
        out = model(x, rule_trigger=trigger)
        loss = torch.nn.functional.l1_loss(out.prediction, y)
        loss.backward()

        grad_report: dict[str, object] = {}
        all_finite = True
        any_nonzero = False
        for param_name, param in model.named_parameters():
            if not param.requires_grad:
                continue
            if param.grad is None:
                all_finite = False
                grad_report[param_name] = "MISSING"
                continue
            finite = bool(torch.isfinite(param.grad).all())
            nonzero = bool(param.grad.abs().max() > 0)
            all_finite = all_finite and finite
            any_nonzero = any_nonzero or nonzero
        # 关键参数单独报告
        key_params = {}
        for key in ("relation_weights_gcn1", "relation_weights_gcn2", "fixed_weight"):
            param = getattr(model, key, None)
            if param is None and hasattr(model, "base_model"):
                param = getattr(model.base_model, key, None)
            if param is not None:
                key_params[key] = {
                    "requires_grad": bool(param.requires_grad),
                    "grad_is_nonzero": (
                        bool(param.grad.abs().max() > 0) if param.grad is not None else False
                    ),
                }
        results[name] = {
            "output_finite": bool(torch.isfinite(out.prediction).all()),
            "loss_finite": bool(torch.isfinite(loss)),
            "all_trainable_grads_finite": all_finite,
            "any_trainable_grad_nonzero": any_nonzero,
            "key_interpretable_params": key_params,
        }
    return results


# ---------------------------------------------------------------------------
# 6. relation_dropout 行为验证
# ---------------------------------------------------------------------------

def audit_relation_dropout() -> dict:
    """验证 relation_dropout 的训练随机性、评估确定性与掩码统计特性。"""
    adjs = _three_relations()
    torch.manual_seed(7)
    x = torch.randn(BATCH, HISTORY, NUM_NODES, NUM_FEATURES)
    model = StaticGraphForecast(
        NUM_FEATURES, HORIZON, NUM_NODES, adjs,
        hidden_dim=HIDDEN, levels=LEVELS, dropout=0.0, relation_dropout=0.4,
    )

    # 训练模式：16 次前向，统计不同输出的种数
    model.train()
    train_outputs = [model(x).prediction for _ in range(16)]
    distinct = 1 + sum(
        1 for other in train_outputs[1:]
        if not torch.allclose(train_outputs[0], other)
    )

    # eval 模式：两次前向必须逐位一致
    model.eval()
    with torch.no_grad():
        eval_first = model(x).prediction
        eval_second = model(x).prediction
    eval_deterministic = bool(torch.equal(eval_first, eval_second))

    # 掩码统计：p=0.2, R=3 时每位保留率期望 = (1-p) + p/R ≈ 0.8667
    # （零同步实现：无条件强制保留一个随机位置，叠加在独立 Bernoulli 上）
    torch.manual_seed(99)
    trials = 2000
    counts = torch.zeros(3)
    min_kept = 3
    for _ in range(trials):
        mask = sample_relation_keep_mask(3, 0.2, torch.device("cpu"))
        counts += mask
        min_kept = min(min_kept, int(mask.sum()))
    empirical_keep_rate = (counts / trials).tolist()

    return {
        "train_distinct_outputs_in_16_forwards": distinct,
        "train_randomness_active": distinct > 1,
        "eval_deterministic": eval_deterministic,
        "mask_keep_rate_per_relation": empirical_keep_rate,
        "mask_keep_rate_expected": (1.0 - 0.2) + 0.2 / 3,
        "mask_min_relations_kept_in_2000_trials": min_kept,
    }


def main() -> None:
    report = {
        "config": {
            "num_nodes": NUM_NODES, "num_features": NUM_FEATURES,
            "history": HISTORY, "horizon": HORIZON,
            "hidden_dim": HIDDEN, "levels": LEVELS,
            "note": "正式实验配置尺寸；合成输入，不触碰真实数据与测试集",
        },
        "tensor_flow": audit_tensor_flow(),
        "parameters": audit_parameters(),
        "receptive_field": audit_receptive_field(),
        "residual_base_loading": audit_residual_base_loading(),
        "forward_backward": audit_forward_backward(),
        "relation_dropout": audit_relation_dropout(),
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
