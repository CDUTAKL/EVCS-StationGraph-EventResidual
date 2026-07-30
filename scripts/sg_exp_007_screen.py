#!/usr/bin/env python3
"""SG-EXP-007 事件加权损失筛选与正式实验。

实验设计（遵循 GPT 五维分析建议）：
  SG-EXP-007a — 二值加权 λ 筛选：λ ∈ {0, 2, 3, 5}，3 种子
  SG-EXP-007b — 连续强度加权（使用 007a 最优 λ）
  SG-EXP-007c — 关系级事件调制（可选，仅当 007a/b 有效时启用）

执行顺序：
  1. λ=0 对照（标准 L1Loss，验证底座复现）
  2. λ ∈ {2, 3, 5} 筛选
  3. 选择最优 λ → 007b intensity 模式
  4. 汇总 → 选择最优方案

底座：AdaptiveGraph (B3 最优: embed=12, fixed_weight=0.5, levels=6, hidden=32)
所有实验使用完全相同的模型初始化（统一 seed），仅损失函数不同。

工件输出：outputs/sg_exp_007_YYYYMMDD-HHMMSS/
"""

from __future__ import annotations

import copy
import json
import time
from pathlib import Path
from typing import Any

import numpy as np

from evcs_station_graph.config import load_experiment_config
from evcs_station_graph.data import WindowSpec, load_tensor_bundle
from evcs_station_graph.training import train_experiment

# ── 路径与常量 ──
PROJECT_PATH = Path("configs/project.yaml")
CONFIG_007A = Path("configs/experiments/SG-EXP-007a-event-weighted.yaml")
CONFIG_007B = Path("configs/experiments/SG-EXP-007b-event-intensity.yaml")
BUNDLE_PATH = "data/processed/SG-DATA-005-primary-tensor.npz"

# B 阶段最优超参数（与 night_run.py 一致）
B1_BEST = {"levels": 6, "hidden_dim": 32}
B3_BEST = {"embedding_dim": 12, "fixed_weight": 0.5}

# ── 实验参数 ──
LAMBDA_VALUES = [0, 2, 3, 5]  # λ=0 为标准 L1Loss 对照
MODE_007A = "binary"

# ── 停止条件 ──
STABLE_DEGRADATION_LIMIT = 0.05  # 稳定窗口 MAE 上升超过 5% 则拒绝
EVENT_IMPROVEMENT_MIN = 0.05     # 事件窗口 MAE 改善低于 5% 则无意义


def _inject_params(config: dict, lambda_val: float, mode: str = MODE_007A,
                   normalize_intensity: bool = True) -> dict:
    """将 B 阶段最优参数和损失配置注入实验配置。"""
    cfg = copy.deepcopy(config)
    mp = cfg["experiment"].setdefault("model_params", {})
    mp["levels"] = B1_BEST["levels"]
    mp["hidden_dim"] = B1_BEST["hidden_dim"]
    mp["dropout"] = 0.1
    mp["embedding_dim"] = B3_BEST["embedding_dim"]
    mp["fixed_weight"] = B3_BEST["fixed_weight"]
    mp["top_k"] = 5

    graph = cfg["experiment"].setdefault("graph", {})
    graph.setdefault("top_k", 3)
    graph.setdefault("enabled_relations", ["load", "event", "pattern"])

    # 注入损失配置
    if lambda_val > 0:
        cfg["experiment"]["training"]["loss"] = {
            "lambda": lambda_val,
            "mode": mode,
            "normalize_intensity": normalize_intensity,
        }
    elif "loss" in cfg["experiment"].get("training", {}):
        # λ=0：删除 loss 段，使用标准 L1Loss
        del cfg["experiment"]["training"]["loss"]

    return cfg


def _check_stop_conditions(
    results: dict[int, dict],
    baseline: dict,
    lambda_val: int,
) -> list[str]:
    """检查停止条件，返回触发的条件列表。"""
    issues: list[str] = []

    baseline_event = baseline["event_window"]["mae"]
    baseline_stable = baseline["stable_window"]["mae"]

    current = results[lambda_val]
    current_event = current["event_window"]["mae"]
    current_stable = current["stable_window"]["mae"]

    # 停止条件 1：稳定窗口退化 >5%
    stable_change = (current_stable - baseline_stable) / baseline_stable
    if stable_change > STABLE_DEGRADATION_LIMIT:
        issues.append(
            f"稳定窗口退化 {stable_change:.1%} > {STABLE_DEGRADATION_LIMIT:.1%} "
            f"({baseline_stable:.5f} → {current_stable:.5f})"
        )

    # 停止条件 2：事件窗口改善不显著
    event_change = (baseline_event - current_event) / baseline_event
    if event_change < EVENT_IMPROVEMENT_MIN:
        issues.append(
            f"事件窗口改善 {event_change:.1%} < {EVENT_IMPROVEMENT_MIN:.1%} "
            f"({baseline_event:.4f} → {current_event:.4f})"
        )

    return issues


def run_sg_exp_007() -> None:
    """运行 SG-EXP-007 完整实验流程。"""
    tag = time.strftime("%Y%m%d-%H%M%S")
    root = Path("outputs/sg_exp_007") / tag
    root.mkdir(parents=True, exist_ok=True)
    print(f"SG-EXP-007 实验开始：{tag}")
    print(f"工件目录：{root}")

    bundle = load_tensor_bundle(BUNDLE_PATH)

    # ═══════════════════════════════════════════════════════════════
    # 阶段 1：SG-EXP-007a — 二值加权 λ 筛选
    # ═══════════════════════════════════════════════════════════════
    print("\n" + "=" * 60)
    print("SG-EXP-007a：二值加权 λ 筛选")
    print(f"λ ∈ {LAMBDA_VALUES}")
    print("=" * 60)

    results_007a: dict[int, dict] = {}
    overrides: tuple[str, ...] = ()

    for lambda_val in LAMBDA_VALUES:
        label = f"λ={lambda_val}" if lambda_val > 0 else "λ=0 (标准 L1Loss 对照)"
        print(f"\n▶ {label}", flush=True)

        config = load_experiment_config(PROJECT_PATH, CONFIG_007A, overrides)
        config = _inject_params(config, lambda_val)

        # 修改 experiment_id 以区分不同 λ
        config["experiment"]["experiment_id"] = f"SG-EXP-007a-lambda{lambda_val}"

        run_root = train_experiment(config, bundle, str(root / "007a_screening"))

        # 读取汇总指标
        summary_path = run_root / "metrics_summary.json"
        if summary_path.exists():
            with open(summary_path) as f:
                summary = json.load(f)
            results_007a[lambda_val] = summary["scopes"]
            print(f"  λ={lambda_val}: event_mae={summary['scopes']['event_window']['mae']['mean']:.5f} "
                  f"stable_mae={summary['scopes']['stable_window']['mae']['mean']:.5f} "
                  f"global_mae={summary['scopes']['global']['mae']['mean']:.5f}", flush=True)
        else:
            print(f"  ✗ λ={lambda_val}: 实验未生成汇总文件", flush=True)
            results_007a[lambda_val] = {"error": "missing summary"}

    # ── 分析 ──
    print("\n── SG-EXP-007a 汇总 ──")
    baseline = results_007a.get(0, {})
    if not baseline or "event_window" not in baseline:
        print("✗ 基线 (λ=0) 实验失败，无法比较")
        return

    print(f"  基线 (λ=0):       event_mae={baseline['event_window']['mae']['mean']:.5f} "
          f"stable_mae={baseline['stable_window']['mae']['mean']:.5f}")
    valid_candidates: list[tuple[int, dict]] = []
    for lambda_val in sorted(LAMBDA_VALUES):
        if lambda_val == 0:
            continue
        result = results_007a.get(lambda_val, {})
        if "error" in result:
            continue
        event_change = (baseline["event_window"]["mae"]["mean"] -
                        result["event_window"]["mae"]["mean"]) / baseline["event_window"]["mae"]["mean"]
        stable_change = (result["stable_window"]["mae"]["mean"] -
                         baseline["stable_window"]["mae"]["mean"]) / baseline["stable_window"]["mae"]["mean"]
        issues = _check_stop_conditions(results_007a, baseline, lambda_val)
        flag = "✗ " + "; ".join(issues) if issues else "✓"
        print(f"  λ={lambda_val}:           event_mae={result['event_window']['mae']['mean']:.5f} "
              f"({event_change:+.1%})  stable_mae={result['stable_window']['mae']['mean']:.5f} "
              f"({stable_change:+.1%})  {flag}")
        if not issues:
            valid_candidates.append((lambda_val, result))

    # ── 选择最优 λ ──
    if not valid_candidates:
        print("\n✗ 所有 λ 均未通过停止条件。SG-EXP-007 终止。")
        print("  结论：事件加权损失在当前数据条件下无统计显著改善。")
        _save_report(root, "FAILED", results_007a, None, None)
        return

    # 在通过停止条件的候选中，选择事件窗口 MAE 最低者
    best_lambda, best_result = min(
        valid_candidates, key=lambda x: x[1]["event_window"]["mae"]["mean"]
    )
    print(f"\n  → 007a 最优 λ = {best_lambda}")
    print(f"     event_mae: {best_result['event_window']['mae']['mean']:.5f} "
          f"stable_mae: {best_result['stable_window']['mae']['mean']:.5f}")

    # ═══════════════════════════════════════════════════════════════
    # 阶段 2：SG-EXP-007b — 连续强度加权（使用最优 λ）
    # ═══════════════════════════════════════════════════════════════
    print("\n" + "=" * 60)
    print(f"SG-EXP-007b：连续强度加权 (λ={best_lambda})")
    print("=" * 60)

    config_007b = load_experiment_config(PROJECT_PATH, CONFIG_007B, overrides)
    config_007b = _inject_params(config_007b, best_lambda, mode="intensity",
                                  normalize_intensity=True)
    config_007b["experiment"]["experiment_id"] = "SG-EXP-007b-intensity"

    run_root_007b = train_experiment(config_007b, bundle, str(root / "007b_intensity"))

    results_007b = None
    summary_path_007b = run_root_007b / "metrics_summary.json"
    if summary_path_007b.exists():
        with open(summary_path_007b) as f:
            summary_007b = json.load(f)
        results_007b = summary_007b["scopes"]
        print(f"  intensity mode: event_mae={results_007b['event_window']['mae']['mean']:.5f} "
              f"stable_mae={results_007b['stable_window']['mae']['mean']:.5f}")

    # ── 最终结论 ──
    print("\n" + "=" * 60)
    print("SG-EXP-007 最终结论")
    print("=" * 60)

    best_mode = "binary"
    best_overall = best_result

    if results_007b and "event_window" in results_007b:
        intensity_event = results_007b["event_window"]["mae"]["mean"]
        binary_event = best_result["event_window"]["mae"]["mean"]
        if intensity_event < binary_event:
            best_mode = "intensity"
            best_overall = results_007b

    print(f"  最优方案: {best_mode} 加权, λ={best_lambda}")
    print(f"  event_window MAE: {best_overall['event_window']['mae']['mean']:.5f}")
    print(f"  stable_window MAE: {best_overall['stable_window']['mae']['mean']:.5f}")
    print(f"  global MAE: {best_overall['global']['mae']['mean']:.5f}")

    _save_report(root, "PASSED", results_007a, results_007b,
                 {"best_lambda": best_lambda, "best_mode": best_mode})

    print(f"\n全部工件已保存至：{root}")


def _save_report(
    root: Path,
    status: str,
    results_007a: dict,
    results_007b: dict | None,
    best: dict | None,
) -> None:
    """保存实验报告为 JSON。"""
    report: dict[str, Any] = {
        "experiment": "SG-EXP-007",
        "status": status,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "stop_conditions": {
            "stable_degradation_limit": STABLE_DEGRADATION_LIMIT,
            "event_improvement_min": EVENT_IMPROVEMENT_MIN,
        },
    }

    # 将 results_007a 转为可序列化形式
    serializable_007a: dict[str, Any] = {}
    for lam, scopes in results_007a.items():
        if "error" in scopes:
            serializable_007a[str(lam)] = {"error": scopes["error"]}
        else:
            serializable_007a[str(lam)] = {
                scope: {
                    metric: val
                    for metric, val in metrics.items()
                }
                for scope, metrics in scopes.items()
            }
    report["007a_results"] = serializable_007a

    if results_007b:
        report["007b_results"] = {
            scope: {metric: val for metric, val in metrics.items()}
            for scope, metrics in results_007b.items()
        }

    if best:
        report["best_config"] = best

    with open(root / "experiment_report.json", "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\n实验报告已保存至：{root / 'experiment_report.json'}")


if __name__ == "__main__":
    run_sg_exp_007()
