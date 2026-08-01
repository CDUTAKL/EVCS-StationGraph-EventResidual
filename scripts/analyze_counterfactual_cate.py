"""分层参数干预敏感度分析（D6-5）：门控分配干预的分层条件效应。

目的（决策工具，非正式实验）：
  把 D5-1b 的 gate 干预（强制 β 组合 → 全局 MAE 变化）升级为分层
  参数干预敏感度分析（审查 M-07，2026-08-01：对模型内部 β 的强制替换
  是参数干预，非观测数据上的因果处理分配，无混杂控制/可识别条件——
  表述用"分层参数干预敏感度"，不使用严格 CATE 语义）：
    干预 = 反事实（将学习到的关系门控 β 替换为指定组合，观察预测质量变化）
    条件 = 事件窗口 / 稳定窗口 / 节点

  若不同窗口类型、不同节点对门控分配变化的敏感性存在系统差异
  （如事件窗口对 event 关系干预更敏感、稳定窗口对 load 更敏感），
  则"门控分配的可解释干预 → 分层敏感度"成为决策支持贡献。

输出：
  - 每个干预 × 种子：全局/事件/稳定窗口 ΔMAE（相对 learned 基线）
  - per-node ΔMAE：找出门控最敏感的节点（top 3）
  - 判定：存在窗口间/节点间敏感度差异（分层 ΔMAE 差异 > 1% 绝对量）
    → 反事实分层归因成立，作为 5.3 节素材

用法（本地 CPU/GPU 均可，约 1-3 分钟）：
  export PYTHONPATH=src
  .venv/bin/python scripts/analyze_counterfactual_cate.py \
    --sg003-root <SG-EXP-003-root> \
    --output-dir outputs/analysis/counterfactual_cate
"""

from __future__ import annotations

import argparse
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
)
from evcs_station_graph.models.graph import StaticGraphForecast
from evcs_station_graph.reproducibility import write_json
from evcs_station_graph.training.engine import _make_loader, _predict, _select_device

# 复用 D5-1b 的干预组合与模型加载逻辑（同目录脚本，运行时 sys.path[0]=scripts/）
from analyze_gate_intervention import INTERVENTIONS, _load_model

# 分层敏感度差异判定阈值：事件窗口与稳定窗口的 ΔMAE（相对 learned）差异
# 超过 1 个百分点视为存在系统性的条件效应（绝对 MAE 在 0.002-0.04 量级，
# 1 个百分点差异即约 0.0004-0.0008 的相对量，高于种子间噪声 0.0002）
STRATIFICATION_DIFF_THRESHOLD = 0.01


def _per_node_mae(predictions: dict) -> dict:
    """按节点计算 MAE：对 [S,H,N] 的 truth/prediction 沿 (S,H) 维分组。"""
    truth = predictions["truth"]
    pred = predictions["prediction"]
    return {i: float(np.mean(np.abs(truth[:, :, i] - pred[:, :, i])))
            for i in range(truth.shape[2])}


def _window_masked_mae(
    predictions: dict, mask: np.ndarray,
) -> float:
    """按掩码计算 MAE（事件/稳定窗口分层）。"""
    truth = predictions["truth"][mask]
    pred = predictions["prediction"][mask]
    return float(np.mean(np.abs(truth - pred)))


def _run_intervention_with_layers(
    model: StaticGraphForecast,
    loaders: dict,
    trigger_by_origin: np.ndarray,
    bundle: TensorBundle,
    device: torch.device,
    gcn1_beta: Any,
    gcn2_beta: Any,
) -> dict:
    """执行一次干预，返回全局/事件/稳定/节点级 MAE（D5-1b 的扩展版）。"""
    learned1 = model.relation_weights_gcn1.detach().clone()
    learned2 = model.relation_weights_gcn2.detach().clone()

    with torch.no_grad():
        if isinstance(gcn1_beta, list):
            model.relation_weights_gcn1.data.copy_(
                torch.as_tensor(gcn1_beta, dtype=torch.float32, device=device))
        elif gcn1_beta == "swap":
            model.relation_weights_gcn1.data.copy_(learned2)
        if isinstance(gcn2_beta, list):
            model.relation_weights_gcn2.data.copy_(
                torch.as_tensor(gcn2_beta, dtype=torch.float32, device=device))
        elif gcn2_beta == "swap":
            model.relation_weights_gcn2.data.copy_(learned1)

        predictions = _predict(model, loaders["test"], device, trigger_by_origin, bundle)

        # 恢复学习值（避免污染后续组合）
        model.relation_weights_gcn1.data.copy_(learned1)
        model.relation_weights_gcn2.data.copy_(learned2)

    event = predictions["target_event"]
    stable = ~event
    return {
        "global_mae": float(np.mean(np.abs(predictions["truth"] - predictions["prediction"]))),
        "event_mae": _window_masked_mae(predictions, event),
        "stable_mae": _window_masked_mae(predictions, stable),
        "node_mae": _per_node_mae(predictions),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="D6-5 反事实 CATE 快速验证")
    parser.add_argument("--sg003-root", required=True, help="SG-EXP-003 运行根目录")
    parser.add_argument("--project", default="configs/project.yaml",
                        help="项目配置文件（用于重建关系图）")
    parser.add_argument("--dataset", default="data/processed/SG-DATA-005-primary-tensor.npz")
    parser.add_argument("--output-dir", default="outputs/analysis/counterfactual_cate")
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
        for split in ("validation", "test")
    }
    batch_size = int(config["experiment"].get("training", {}).get("batch_size", 256))
    loaders = {
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
    node_ids = bundle.node_ids.tolist()
    started = time.perf_counter()

    seeds = [2024, 2025, 2026]
    all_rows: list[dict[str, Any]] = []
    for seed in seeds:
        ckpt = root / f"seed-{seed}" / "model.pt"
        if not ckpt.is_file():
            print(f"  ⚠ 跳过 seed={seed}：checkpoint 不存在", flush=True)
            continue
        model = _load_model(ckpt, config, bundle, device)
        print(f"\nseed={seed}", flush=True)
        for iv in INTERVENTIONS:
            result = _run_intervention_with_layers(
                model, loaders, trigger_by_origin, bundle, device,
                iv["gcn1"], iv["gcn2"],
            )
            row = {"seed": seed, "intervention": iv["name"], **result}
            all_rows.append(row)
            print(f"  [{iv['name']:20s}] global={result['global_mae']:.5f} "
                  f"event={result['event_mae']:.4f} stable={result['stable_mae']:.5f}",
                  flush=True)

    # ---- 聚合：每种干预的相对 learned 的 ΔMAE（全局/事件/稳定/节点） ----
    def _mean(intervention: str, key: str) -> float:
        rows = [r for r in all_rows if r["intervention"] == intervention]
        return float(np.mean([r[key] for r in rows]))

    def _mean_node_mae(intervention: str) -> list:
        """节点级 MAE 的种子均值：node_mae 是 {节点索引: MAE} dict，按节点聚合。"""
        rows = [r for r in all_rows if r["intervention"] == intervention]
        if not rows:
            raise RuntimeError(f"干预 {intervention} 无结果行")
        return [float(np.mean([r["node_mae"][i] for r in rows]))
                for i in range(len(node_ids))]

    learned_global = _mean("learned", "global_mae")
    learned_event = _mean("learned", "event_mae")
    learned_stable = _mean("learned", "stable_mae")
    learned_node = _mean_node_mae("learned")

    summary: dict[str, Any] = {
        "seeds": seeds,
        "baseline_learned": {
            "global_mae": learned_global,
            "event_mae": learned_event,
            "stable_mae": learned_stable,
            "node_mae": learned_node,
        },
        "interventions": {},
    }
    # 干预命名顺序：跳过 learned 自身，其余按 INTERVENTIONS 定义顺序
    for iv in INTERVENTIONS:
        if iv["name"] == "learned":
            continue
        name = iv["name"]
        global_delta = (_mean(name, "global_mae") - learned_global) / learned_global
        event_delta = (_mean(name, "event_mae") - learned_event) / learned_event
        stable_delta = (_mean(name, "stable_mae") - learned_stable) / learned_stable
        node_deltas = {
            node_ids[i]: (_mean_node_mae(name)[i] - learned_node[i]) / learned_node[i]
            for i in range(len(node_ids))
        }
        # top 敏感节点：|ΔMAE| 最大的 3 个
        top_sensitive = sorted(node_deltas.items(), key=lambda kv: abs(kv[1]),
                               reverse=True)[:3]
        summary["interventions"][name] = {
            "desc": iv["desc"],
            "global_delta": global_delta,
            "event_delta": event_delta,
            "stable_delta": stable_delta,
            "event_stable_gap": event_delta - stable_delta,
            "top_sensitive_nodes": [
                {"node": n, "node_delta": d} for n, d in top_sensitive
            ],
            "node_deltas": node_deltas,
        }
        print(f"{name}: 全局 {global_delta:+.1%} | 事件 {event_delta:+.1%} | "
              f"稳定 {stable_delta:+.1%} | 事件-稳定差 {event_delta - stable_delta:+.1%}")

    # ---- 判定：是否存在窗口间/节点间系统性敏感度差异 ----
    # 健壮性（审查发现）：全种子 checkpoint 缺失时 interventions 为空，
    # 对空序列 max() 会崩溃且无提示——先显式报错
    gaps = [v["event_stable_gap"] for v in summary["interventions"].values()]
    if not gaps:
        raise RuntimeError(
            "没有可用的干预结果（所有种子的 checkpoint 缺失？），"
            "无法进行反事实分层归因判定"
        )
    max_gap = max(abs(g) for g in gaps)
    node_spread = max(
        max(abs(v) for v in summary["interventions"][name]["node_deltas"].values())
        for name in summary["interventions"]
    )
    if max_gap >= STRATIFICATION_DIFF_THRESHOLD and node_spread >= STRATIFICATION_DIFF_THRESHOLD:
        verdict = (
            f"通过：窗口间敏感度差异最大 {max_gap:.1%}、节点间差异最大 "
            f"{node_spread:.1%}（均 ≥{STRATIFICATION_DIFF_THRESHOLD:.0%}）"
            f"→ 反事实分层归因成立"
        )
    elif max_gap >= STRATIFICATION_DIFF_THRESHOLD:
        verdict = (
            f"通过（窗口层）：窗口间敏感度差异最大 {max_gap:.1%}，"
            f"节点间差异不足（{node_spread:.1%}）"
        )
    else:
        verdict = (
            f"未通过：窗口间最大差异仅 {max_gap:.1%}（<{STRATIFICATION_DIFF_THRESHOLD:.0%}），"
            f"分层条件效应不显著"
        )
    summary["verdict"] = verdict
    summary["elapsed_seconds"] = time.perf_counter() - started
    print(f"\n判定：{verdict}")

    out_path = output_dir / "counterfactual_cate_summary.json"
    write_json(summary, out_path)
    print(f"结果已写入：{out_path}")
    print(f"总耗时：{time.perf_counter() - started:.1f}s", flush=True)


if __name__ == "__main__":
    main()
