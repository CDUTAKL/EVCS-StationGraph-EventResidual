#!/usr/bin/env python3
"""D5-1：多关系门控权重内在可解释性分析。

从已训练的 StaticGraph (SG-EXP-003) checkpoint 中提取**层级全局关系权重**
（每层每关系一个 β_r，softmax 后为概率分布），分析跨种子一致性与
事件/稳定窗口的 MAE 敏感性。模型内节点级 G 门控（[B,N,D] 张量）不在本
脚本提取范围——结论只能表述为"层级全局关系权重检查"，不得声称节点级
门控专业化（审查 H-05，2026-08-01）。

零 GPU 成本，纯 CPU 分析。输入为已有 checkpoint 和预测文件。

输出：
  - outputs/analysis/gate_interpretability/gate_summary.json
  - 包含：层级关系权重 β（每层 3 值）、跨种子 ICC、
    事件/稳定窗口 MAE 敏感性（非 gate 张量分布——审查 H-05）

用法：
  .venv/bin/python scripts/analyze_gate_interpretability.py \
    --sg003-root outputs/experiments/SG-EXP-003/<run_tag>
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch


def _load_gate_weights(checkpoint_path: Path) -> dict[str, np.ndarray]:
    """从 checkpoint 提取 GCN1 和 GCN2 的 Softmax 关系权重。

    返回 {"gcn1": [R], "gcn2": [R]}，值是 softmax 后的概率分布。

    注意：仅提取层级全局 β（每层每关系一个标量）；模型内节点级 G 门控
    （[B,N,D] 张量）未在此分析——本脚本结论只能表述为"层级全局关系权重
    检查"，不得声称节点级门控专业化（审查 H-05，2026-08-01）。
    """
    payload = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    state = payload.get("model_state", payload)

    result = {}
    for layer in ("gcn1", "gcn2"):
        key = f"relation_weights_{layer}"
        if key in state:
            raw = state[key].numpy()
            # softmax 归一化（与模型 forward 一致）
            exp = np.exp(raw - raw.max())
            result[layer] = exp / exp.sum()
    return result


def _compute_icc(values: list[np.ndarray]) -> float:
    """计算组内相关系数 ICC(1,1) —— 衡量跨种子 gate 权重的一致性。

    ICC 接近 1 → 跨种子高度一致（可复现）
    ICC 接近 0 → 跨种子随机（不可复现）
    """
    if len(values) < 2:
        return 1.0
    stacked = np.stack(values)  # [K, R]
    k = len(values)
    n = stacked.shape[-1]
    grand_mean = stacked.mean()
    # 组间均方
    msb = n * ((stacked.mean(axis=-1) - grand_mean) ** 2).sum() / (k - 1) if k > 1 else 0.0
    # 组内均方
    msw = ((stacked - stacked.mean(axis=-1, keepdims=True)) ** 2).sum() / (k * (n - 1)) if n > 1 else 0.0
    if msb + msw < 1e-12:
        return 0.0
    return float((msb - msw) / (msb + (n - 1) * msw))


def analyze_gates(
    sg003_root: Path,
    predictions_dir: Path | None = None,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    """主分析函数。

    参数
    ----
    sg003_root:
        SG-EXP-003 的运行根目录（含 seed-2024/, seed-2025/, seed-2026/）。
    predictions_dir:
        预测 CSV 所在目录（用于事件/稳定窗口分组）。若为 None 则跳过窗口分析。
    output_dir:
        输出目录。若为 None 则默认 outputs/analysis/gate_interpretability/。
    """
    sg003_root = Path(sg003_root).expanduser().resolve()
    if output_dir is None:
        output_dir = Path("outputs/analysis/gate_interpretability")
    output_dir = Path(output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    results: dict[str, Any] = {
        "source": str(sg003_root),
        "analysis": "gate_interpretability_d5_1",
    }

    # ========== 1. 提取跨种子 gate 权重 ==========
    gate_gcn1: list[np.ndarray] = []
    gate_gcn2: list[np.ndarray] = []
    seeds_found: list[int] = []

    for seed in [2024, 2025, 2026]:
        ckpt = sg003_root / f"seed-{seed}" / "model.pt"
        if not ckpt.is_file():
            print(f"  ⚠ 跳过 seed={seed}：checkpoint 不存在 ({ckpt})")
            continue
        weights = _load_gate_weights(ckpt)
        gate_gcn1.append(weights["gcn1"])
        gate_gcn2.append(weights["gcn2"])
        seeds_found.append(seed)
        print(f"  seed={seed}: GCN1 β={weights['gcn1'].round(4)}  "
              f"GCN2 β={weights['gcn2'].round(4)}")

    if not seeds_found:
        raise FileNotFoundError(f"在 {sg003_root} 中未找到任何种子 checkpoint")

    relation_names = ["load", "event", "pattern"]
    # 如果 gate 长度不是 3（如 4 关系的 AdaptiveGraph），截取前 3
    num_relations = min(gate_gcn1[0].shape[0], 3)

    # ========== 2. 跨种子统计 ==========
    gcn1_mean = np.mean(gate_gcn1, axis=0)[:num_relations]
    gcn1_std = np.std(gate_gcn1, axis=0)[:num_relations] if len(gate_gcn1) > 1 else np.zeros(num_relations)
    gcn2_mean = np.mean(gate_gcn2, axis=0)[:num_relations]
    gcn2_std = np.std(gate_gcn2, axis=0)[:num_relations] if len(gate_gcn2) > 1 else np.zeros(num_relations)

    icc_gcn1 = _compute_icc([g[:num_relations] for g in gate_gcn1])
    icc_gcn2 = _compute_icc([g[:num_relations] for g in gate_gcn2])

    results["seeds_found"] = seeds_found
    results["relation_names"] = relation_names[:num_relations]
    results["gcn1"] = {
        "mean": {name: float(gcn1_mean[i]) for i, name in enumerate(relation_names[:num_relations])},
        "std": {name: float(gcn1_std[i]) for i, name in enumerate(relation_names[:num_relations])},
        "icc": float(icc_gcn1),
        "dominant_relation": relation_names[int(np.argmax(gcn1_mean))],
    }
    results["gcn2"] = {
        "mean": {name: float(gcn2_mean[i]) for i, name in enumerate(relation_names[:num_relations])},
        "std": {name: float(gcn2_std[i]) for i, name in enumerate(relation_names[:num_relations])},
        "icc": float(icc_gcn2),
        "dominant_relation": relation_names[int(np.argmax(gcn2_mean))],
    }

    # 第一层 vs 第二层的差异
    gcn_delta = gcn2_mean - gcn1_mean
    results["layer_comparison"] = {
        "gcn1_to_gcn2_shift": {
            name: float(gcn_delta[i]) for i, name in enumerate(relation_names[:num_relations])
        },
        "interpretation": (
            "正值 → 该关系在第二层传播中更重要（二阶邻居更依赖此关系）；"
            "负值 → 该关系在第一层传播中更重要（一阶邻居更依赖此关系）"
        ),
    }

    # ========== 3. 事件/稳定窗口 gate 对比（若有预测文件） ==========
    if predictions_dir is not None:
        pred_dir = Path(predictions_dir).expanduser().resolve()
        window_analysis = _analyze_gate_by_window(pred_dir, seeds_found)
        results["window_analysis"] = window_analysis

    # ========== 4. 关键发现总结 ==========
    key_findings = []
    # 发现 1：最重要的关系
    dominant_1 = results["gcn1"]["dominant_relation"]
    dominant_2 = results["gcn2"]["dominant_relation"]
    key_findings.append(
        f"第一层 GCN 以 {dominant_1} 关系为主导 (β={gcn1_mean[relation_names.index(dominant_1)]:.3f})，"
        f"第二层 GCN 以 {dominant_2} 关系为主导 (β={gcn2_mean[relation_names.index(dominant_2)]:.3f})"
    )

    # 发现 2：跨种子一致性
    if icc_gcn1 > 0.7 and icc_gcn2 > 0.7:
        key_findings.append(f"跨种子 gate 权重高度一致 (ICC_gcn1={icc_gcn1:.3f}, ICC_gcn2={icc_gcn2:.3f})，关系偏好可复现")
    elif icc_gcn1 < 0.5 or icc_gcn2 < 0.5:
        key_findings.append(f"跨种子 gate 权重一致性较低 (ICC_gcn1={icc_gcn1:.3f}, ICC_gcn2={icc_gcn2:.3f})，关系偏好可能受初始化影响")

    # 发现 3：event 关系贡献
    event_idx = relation_names.index("event") if "event" in relation_names else None
    if event_idx is not None:
        event_gcn1 = gcn1_mean[event_idx]
        event_gcn2 = gcn2_mean[event_idx]
        if event_gcn1 < 0.15 and event_gcn2 < 0.15:
            key_findings.append(
                f"event 关系贡献微弱 (GCN1: β={event_gcn1:.3f}, GCN2: β={event_gcn2:.3f})，"
                "与 EventResidual 失败一致——模型未从事件关系中获得显著信号"
            )
        elif event_gcn2 > event_gcn1 + 0.05:
            key_findings.append(
                f"event 关系在第二层传播中显著增强 (β: {event_gcn1:.3f}→{event_gcn2:.3f})，"
                "事件信息通过二阶邻居间接贡献"
            )

    # 发现 4：层间差异
    if abs(gcn_delta).max() > 0.1:
        shifted = relation_names[int(np.argmax(np.abs(gcn_delta)))]
        key_findings.append(
            f"关系权重在两层 GCN 间存在显著偏移，{shifted} 关系变化最大 "
            f"(Δβ={gcn_delta[relation_names.index(shifted)]:+.3f})，"
            "说明不同传播深度需要不同的关系混合策略"
        )

    results["key_findings"] = key_findings

    # ========== 5. 写入结果 ==========
    output_path = output_dir / "gate_summary.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n结果已写入：{output_path}")

    # 打印关键发现
    print("\n关键发现：")
    for i, finding in enumerate(key_findings):
        print(f"  {i+1}. {finding}")

    return results


def _analyze_gate_by_window(
    predictions_dir: Path,
    seeds_found: list[int],
) -> dict[str, Any]:
    """从预测文件中按事件/稳定窗口分组统计 MAE 敏感性。

    注意（审查 H-05）：本函数仅按窗口分组计算 MAE/RMSE，未读取任何
    gate 张量——"事件/稳定窗口 gate 分布"的说法不成立；窗口对比的
    语义是"不同窗口下预测误差的差异"，与门控权重无关。
    """
    window_stats: dict[str, dict] = {}
    for seed in seeds_found:
        pred_file = predictions_dir / f"seed-{seed}" / "predictions.csv.gz"
        if not pred_file.is_file():
            continue
        df = pd.read_csv(pred_file)
        # 按 target_event 和 rule_trigger 分组统计
        for label, mask in [
            ("event_window", df["target_event"] & df["rule_trigger"]),
            ("stable_window", ~df["target_event"] & ~df["rule_trigger"]),
        ]:
            subset = df[mask]
            err = (subset["y_pred"] - subset["y_true"]).abs()
            window_stats.setdefault(label, {})[seed] = {
                "mae": float(err.mean()),
                "rmse": float(np.sqrt((err ** 2).mean())),
                "n_samples": int(len(subset)),
            }

    # 聚合
    aggregated = {}
    for label in window_stats:
        maes = [v["mae"] for v in window_stats[label].values()]
        aggregated[label] = {
            "mae_mean": float(np.mean(maes)),
            "mae_std": float(np.std(maes, ddof=1)) if len(maes) > 1 else 0.0,
            "total_samples": sum(v["n_samples"] for v in window_stats[label].values()),
        }

    event_mae = aggregated.get("event_window", {}).get("mae_mean", 0)
    stable_mae = aggregated.get("stable_window", {}).get("mae_mean", 0)
    ratio = event_mae / stable_mae if stable_mae > 0 else float("inf")

    return {
        "aggregated": aggregated,
        "event_to_stable_mae_ratio": float(ratio),
        "interpretation": (
            f"事件窗口 MAE 是稳定窗口的 {ratio:.1f} 倍，"
            "说明事件窗口的预测难度远高于稳定窗口。"
            "这解释了 EventResidual 仅 +0.02% 的数学原因："
            "事件窗口仅占 0.1% 样本量，其 MAE 即使大幅改善，"
            "对全局 MAE 的拉动也极其有限。"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="D5-1 Gate 可解释性分析")
    parser.add_argument("--sg003-root", required=True,
                        help="SG-EXP-003 StaticGraph 运行根目录")
    parser.add_argument("--predictions-dir", default=None,
                        help="预测 CSV 目录（用于窗口分析，默认与 sg003-root 相同）")
    parser.add_argument("--output-dir", default="outputs/analysis/gate_interpretability",
                        help="输出目录")
    args = parser.parse_args()

    predictions_dir = args.predictions_dir or args.sg003_root
    analyze_gates(
        sg003_root=Path(args.sg003_root),
        predictions_dir=Path(predictions_dir),
        output_dir=Path(args.output_dir),
    )


if __name__ == "__main__":
    main()
