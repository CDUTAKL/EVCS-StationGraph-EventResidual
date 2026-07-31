"""Gate 干预验证实验（D5-1b）：强制固定 β 组合 → 测试集 MAE 变化。

把第 4 章 L1 关系归因从"观察"升级为"因果验证"：
  观察（D5-1，已做）：模型学到了什么 β
  干预（本实验）：强制 β 为指定组合后，预测质量如何变化

实验设计（8 个组合 × 3 种子 = 24 次测试集前向推理，仅推理无训练）：
  learned           学习值（基线对照）
  g1_load_g2_learn  GCN1 全 load + GCN2 学习值   ← 验证第一层依赖 load
  g1_learn_g2_pat   GCN1 学习值 + GCN2 全 pattern ← 验证第二层依赖 pattern
  both_load         两层全 load
  both_pattern      两层全 pattern
  both_event        两层全 event  ← 验证 event 关系贡献微弱
  equal             两层等权 1/3 ← 门控价值对照
  swapped           交换两层学习值 ← 验证分层分工不可交换

判定逻辑：
  若 g1_load_g2_learn ≈ learned → 第一层确实主要依赖 load（干预无损失）
  若 g1_learn_g2_pat ≈ learned → 第二层确实主要依赖 pattern
  若 swapped > learned → 分层分工有因果作用（层间顺序不可互换）
  若 both_event 显著差 → event 关系确实贡献微弱

用法：
  .venv/bin/python scripts/analyze_gate_intervention.py \
    --sg003-root outputs/experiments/SG-EXP-003/<run_tag> \
    --output-dir outputs/analysis/gate_intervention
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch

from evcs_station_graph.data import (
    NodeWindowDataset,
    TensorBundle,
    WindowSpec,
    load_tensor_bundle,
)
from evcs_station_graph.evaluation import (
    apply_frozen_event_rule,
    fit_frozen_event_rule,
    four_cell_diagnostics,
    stratified_metrics,
)
from evcs_station_graph.graphs import build_relation_set
from evcs_station_graph.models.graph import StaticGraphForecast
from evcs_station_graph.reproducibility import write_json
from evcs_station_graph.training.engine import _make_loader, _predict, _select_device

# 干预组合定义：(名字, GCN1 β, GCN2 β)，β 为未归一化的 logits（softmax 前）
# "learned" 用 None 占位，运行时填学习值
# 注意（审查后修复）：β 在模型 forward 中经 softmax 归一化——logits [1,0,0]
# 实际只占 57.6% 权重而非"全 load"，故硬干预用 logits=10（softmax 后
# ≈99.99%），确保干预语义与名称一致；等权 [1,1,1] 经 softmax 恰为 1/3 不变。
INTERVENTIONS: list[dict[str, Any]] = [
    {"name": "learned", "gcn1": None, "gcn2": None,
     "desc": "学习值（基线对照）"},
    {"name": "g1_load_g2_learn", "gcn1": [10.0, 0.0, 0.0], "gcn2": None,
     "desc": "GCN1 全 load + GCN2 学习值 → 验证第一层依赖 load"},
    {"name": "g1_learn_g2_pattern", "gcn1": None, "gcn2": [0.0, 0.0, 10.0],
     "desc": "GCN1 学习值 + GCN2 全 pattern → 验证第二层依赖 pattern"},
    {"name": "both_load", "gcn1": [10.0, 0.0, 0.0], "gcn2": [10.0, 0.0, 0.0],
     "desc": "两层全 load"},
    {"name": "both_pattern", "gcn1": [0.0, 0.0, 10.0], "gcn2": [0.0, 0.0, 10.0],
     "desc": "两层全 pattern"},
    {"name": "both_event", "gcn1": [0.0, 10.0, 0.0], "gcn2": [0.0, 10.0, 0.0],
     "desc": "两层全 event → 验证 event 关系贡献微弱"},
    {"name": "equal", "gcn1": [1.0, 1.0, 1.0], "gcn2": [1.0, 1.0, 1.0],
     "desc": "等权 1/3 → 门控价值对照"},
    {"name": "swapped", "gcn1": "swap", "gcn2": "swap",
     "desc": "交换两层学习值 → 验证分层分工不可交换"},
]


def _load_model(
    checkpoint_path: Path,
    config: dict,
    bundle: TensorBundle,
    device: torch.device,
) -> StaticGraphForecast:
    """加载 StaticGraph 模型（与 D5-1/KD 脚本同口径）。"""
    payload = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    state = payload.get("model_state", payload)
    params = config["experiment"].get("model_params", {})

    # 从 checkpoint 推断输入维（Conv1d 权重形状 [out, in, kernel]）
    conv_key = "tcn.network.0.conv.weight"
    inferred_input_dim = int(state[conv_key].shape[1]) if conv_key in state else 7
    # 从 checkpoint 推断 levels（网络层数）——配置文件可能过时，以 checkpoint 为准
    num_layers = len([k for k in state
                      if k.startswith("tcn.network.") and k.endswith(".conv.weight")])
    inferred_levels = num_layers if num_layers > 0 else int(params.get("levels", 6))

    # 重建关系图（仅训练集）——仅用于初始化 buffer，
    # load_state_dict 会用 checkpoint 中的 adj_* 覆盖
    graph_cfg = config["experiment"].get("graph", {})
    train_end = int(bundle.split_origins["train"][-1])
    adjacencies = build_relation_set(
        bundle.features[: train_end + 1], bundle.targets[: train_end + 1],
        bundle.feature_names, top_k=int(graph_cfg.get("top_k", 3)),
    ).as_list()

    model = StaticGraphForecast(
        input_dim=inferred_input_dim,
        horizon=int(config["project"]["forecast_steps"]),
        num_nodes=len(bundle.node_ids),
        adjacencies=adjacencies,
        hidden_dim=int(params.get("hidden_dim", 32)),
        levels=inferred_levels,
        dropout=float(params.get("dropout", 0.1)),
    )
    model.load_state_dict(state, strict=True)
    model.to(device)
    model.eval()
    return model


def _run_intervention(
    model: StaticGraphForecast,
    loaders: dict,
    trigger_by_origin: np.ndarray,
    bundle: TensorBundle,
    device: torch.device,
    gcn1_beta: Any,
    gcn2_beta: Any,
) -> dict:
    """执行一次干预：覆盖 β → 测试集前向 → 分层指标。

    gcn1_beta/gcn2_beta：None=保持学习值；"swap"=交换两层学习值；
    否则为 [R] 原始 logits（softmax 前）。
    """
    learned1 = model.relation_weights_gcn1.detach().clone()
    learned2 = model.relation_weights_gcn2.detach().clone()

    with torch.no_grad():
        if isinstance(gcn1_beta, list):
            model.relation_weights_gcn1.data.copy_(
                torch.as_tensor(gcn1_beta, dtype=torch.float32, device=device))
        elif gcn1_beta == "swap":
            model.relation_weights_gcn1.data.copy_(learned2)
        # gcn1_beta is None → 保持学习值

        if isinstance(gcn2_beta, list):
            model.relation_weights_gcn2.data.copy_(
                torch.as_tensor(gcn2_beta, dtype=torch.float32, device=device))
        elif gcn2_beta == "swap":
            model.relation_weights_gcn2.data.copy_(learned1)
        # gcn2_beta is None → 保持学习值

        predictions = _predict(model, loaders["test"], device, trigger_by_origin, bundle)

        # 恢复学习值（避免污染后续组合）
        model.relation_weights_gcn1.data.copy_(learned1)
        model.relation_weights_gcn2.data.copy_(learned2)

    metrics = stratified_metrics(
        predictions["truth"], predictions["prediction"],
        target_event=predictions["target_event"],
        node_ids=bundle.node_ids.tolist(),
    )
    four = four_cell_diagnostics(
        predictions["truth"], predictions["prediction"],
        target_event=predictions["target_event"],
        rule_trigger=predictions["rule_trigger"],
    )
    return {
        "global_mae": metrics["global"]["mae"],
        "global_rmse": metrics["global"]["rmse"],
        "event_mae": metrics["event_window"]["mae"],
        "stable_mae": metrics["stable_window"]["mae"],
        # 键名修复（审查发现）：four_cell_diagnostics 返回 reconstruction_pass
        # 布尔（Σ加权 MAE ≡ 全局 MAE 是否通过 1e-9 容差），不是 reconstruction_error
        "four_cell_reconstruction_pass": four.get("reconstruction_pass"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="D5-1b Gate 干预验证")
    parser.add_argument("--sg003-root", required=True, help="SG-EXP-003 运行根目录")
    parser.add_argument("--project", default="configs/project.yaml",
                        help="项目配置文件（用于重建关系图）")
    parser.add_argument("--dataset", default="data/processed/SG-DATA-005-primary-tensor.npz")
    parser.add_argument("--output-dir", default="outputs/analysis/gate_intervention")
    parser.add_argument("--device", default="auto")
    args = parser.parse_args()

    from evcs_station_graph.config import load_experiment_config
    exp_config_path = Path("configs/experiments/SG-EXP-003-static-graph.yaml")
    config = load_experiment_config(Path(args.project), exp_config_path, ())

    bundle = load_tensor_bundle(args.dataset)
    device = _select_device(args.device)
    spec = WindowSpec(
        history_steps=int(config["project"]["history_steps"]),
        forecast_steps=int(config["project"]["forecast_steps"]),
    )
    datasets = {
        split: NodeWindowDataset(bundle, split, spec)
        for split in ("train", "validation", "test")
    }
    batch_size = int(config["experiment"].get("training", {}).get("batch_size", 256))
    loaders = {
        "train": _make_loader(datasets["train"], batch_size, True, 2024),
        "validation": _make_loader(datasets["validation"], batch_size, False, 2024),
        "test": _make_loader(datasets["test"], batch_size, False, 2024),
    }

    # 事件规则与 trigger 矩阵（与正式评价口径一致）
    rule = fit_frozen_event_rule(bundle, quantile=0.95, window_extension=2)
    trigger_by_origin = np.zeros((len(bundle.timestamps_ns), len(bundle.node_ids)), dtype=bool)
    for ds in datasets.values():
        trigger_by_origin[ds.origins] = apply_frozen_event_rule(bundle, ds.origins, rule)

    root = Path(args.sg003_root).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    seeds = [2024, 2025, 2026]
    all_rows: list[dict] = []
    started = time.perf_counter()

    for seed in seeds:
        ckpt = root / f"seed-{seed}" / "model.pt"
        if not ckpt.is_file():
            print(f"  ⚠ 跳过 seed={seed}：checkpoint 不存在", flush=True)
            continue
        model = _load_model(ckpt, config, bundle, device)
        print(f"\nseed={seed} 学习值 β: GCN1={torch.softmax(model.relation_weights_gcn1, dim=0).tolist()}"
              f" GCN2={torch.softmax(model.relation_weights_gcn2, dim=0).tolist()}", flush=True)

        for iv in INTERVENTIONS:
            result = _run_intervention(
                model, loaders, trigger_by_origin, bundle, device,
                iv["gcn1"], iv["gcn2"],
            )
            row = {"seed": seed, "intervention": iv["name"], "desc": iv["desc"], **result}
            all_rows.append(row)
            print(f"  [{iv['name']:20s}] global={result['global_mae']:.5f} "
                  f"event={result['event_mae']:.4f} stable={result['stable_mae']:.5f}", flush=True)

    # 按干预组合聚合三种子均值
    summary: dict[str, Any] = {"seeds": seeds, "device": str(device)}
    for iv in INTERVENTIONS:
        name = iv["name"]
        rows = [r for r in all_rows if r["intervention"] == name]
        if not rows:
            continue
        summary[name] = {
            "desc": iv["desc"],
            "global_mae_mean": float(np.mean([r["global_mae"] for r in rows])),
            "global_mae_std": float(np.std([r["global_mae"] for r in rows])),
            "event_mae_mean": float(np.mean([r["event_mae"] for r in rows])),
            "stable_mae_mean": float(np.mean([r["stable_mae"] for r in rows])),
        }

    # 关键发现（自动判定）
    learned = summary.get("learned", {})
    findings = []
    if learned:
        base = learned["global_mae_mean"]
        for name in ["g1_load_g2_learn", "g1_learn_g2_pattern", "both_load",
                     "both_pattern", "both_event", "equal", "swapped"]:
            if name in summary:
                delta = (summary[name]["global_mae_mean"] - base) / base * 100
                findings.append(f"{name}: global_mae={summary[name]['global_mae_mean']:.5f} "
                                f"(相对学习值 {'+' if delta > 0 else ''}{delta:.1f}%)")
    summary["key_findings"] = findings

    out_path = output_dir / "intervention_summary.json"
    write_json(summary, out_path)
    print(f"\n{'='*60}\n结果已写入：{out_path}")
    for f in findings:
        print(f"  {f}")
    print(f"总耗时：{time.perf_counter() - started:.1f}s", flush=True)


if __name__ == "__main__":
    main()
