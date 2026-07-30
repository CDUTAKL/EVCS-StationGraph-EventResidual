"""统一误差指标与分层统计。

本模块计算三个核心回归指标（MAE、RMSE、WAPE），并在四个层次上分层报告：
1. 全局 + 非零负荷子集 — 区分"预测零负荷"和"预测实际充电活动"的能力
2. 事件窗口 vs 稳定窗口 — 量化事件残差修正的局部收益
3. 按预测步长（horizon 1-4）— 观察预测不确定性随步长的增长
4. 按节点 — 检查模型在不同充电单元上的表现均衡性

四格诊断（four_cell_diagnostics）是核心审计工具：
  target_event × rule_trigger → 四个互斥单元格
  加权重建的 MAE 必须等于全局 MAE（容差 ≤ 1e-9），否则不得解释事件收益来源。
"""

from __future__ import annotations

from typing import Any

import numpy as np


def regression_metrics(
    truth: np.ndarray,
    prediction: np.ndarray,
    mask: np.ndarray | None = None,
) -> dict[str, float | int]:
    """计算 MAE、RMSE 与 WAPE。

    WAPE 的分母为目标绝对值之和；当分母接近零时返回 ``nan``，避免制造虚假比率。
    """
    y_true = np.asarray(truth, dtype=np.float64)
    y_pred = np.asarray(prediction, dtype=np.float64)
    if y_true.shape != y_pred.shape:
        raise ValueError("真实值与预测值形状不一致")
    selected = np.ones_like(y_true, dtype=bool) if mask is None else np.asarray(mask, dtype=bool)
    if selected.shape != y_true.shape:
        raise ValueError("mask 与目标形状不一致")
    error = y_pred[selected] - y_true[selected]
    if error.size == 0:
        return {"count": 0, "mae": float("nan"), "rmse": float("nan"), "wape": float("nan")}
    denominator = np.abs(y_true[selected]).sum()
    return {
        "count": int(error.size),
        "mae": float(np.abs(error).mean()),
        "rmse": float(np.sqrt(np.square(error).mean())),
        "wape": float(np.abs(error).sum() / denominator) if denominator > 1e-12 else float("nan"),
    }


def stratified_metrics(
    truth: np.ndarray,
    prediction: np.ndarray,
    *,
    target_event: np.ndarray,
    node_ids: list[str],
) -> dict[str, Any]:
    """生成全局、事件/稳定、节点和预测步长指标。"""
    if truth.ndim != 3:
        raise ValueError("分层评价输入必须为 [样本, 步长, 节点]")
    # 非零负荷子集：仅包含真实负荷 > 1e-8 kWh/15min 的样本
    # 1e-8 ≈ 0 的工程近似，用于滤除充电单元空闲时段（占全部样本的 ~78%）
    nonzero_load = truth > 1e-8
    output: dict[str, Any] = {
        "global": regression_metrics(truth, prediction),
        "nonzero_load": regression_metrics(truth, prediction, nonzero_load),
        "event_window": regression_metrics(truth, prediction, target_event),
        "stable_window": regression_metrics(truth, prediction, ~target_event),
        "by_horizon": {},
        "by_node": {},
    }
    for horizon in range(truth.shape[1]):
        output["by_horizon"][str(horizon + 1)] = regression_metrics(
            truth[:, horizon, :],
            prediction[:, horizon, :],
        )
    for node_index, node_id in enumerate(node_ids):
        output["by_node"][node_id] = regression_metrics(
            truth[:, :, node_index],
            prediction[:, :, node_index],
        )
    return output


def four_cell_diagnostics(
    truth: np.ndarray,
    prediction: np.ndarray,
    *,
    target_event: np.ndarray,
    rule_trigger: np.ndarray,
) -> dict[str, Any]:
    """按“目标事件 × 规则触发”形成四个互斥单元并还原全局 MAE。"""
    if rule_trigger.ndim == 2:
        rule_trigger = np.broadcast_to(rule_trigger[:, None, :], truth.shape)
    if not (truth.shape == prediction.shape == target_event.shape == rule_trigger.shape):
        raise ValueError("四格诊断数组形状不一致")
    # 四个互斥单元格的业务语义：
    # 1. target_event_triggered：事件发生 + 规则触发 → 修正生效的场景（期望受益）
    # 2. target_event_not_triggered：事件发生 + 规则未触发 → 漏检（规则 Recall 问题）
    # 3. stable_triggered：稳定时段 + 规则误触发 → 误报（规则 Precision 问题）
    # 4. stable_not_triggered：稳定时段 + 规则未触发 → 默认路径正常运作
    definitions = {
        "target_event_triggered": target_event & rule_trigger,
        "target_event_not_triggered": target_event & ~rule_trigger,
        "stable_triggered": ~target_event & rule_trigger,
        "stable_not_triggered": ~target_event & ~rule_trigger,
    }
    cells: dict[str, Any] = {}
    absolute_error_sum = 0.0
    total_count = 0
    for name, mask in definitions.items():
        metrics = regression_metrics(truth, prediction, mask)
        cells[name] = metrics
        if metrics["count"]:
            absolute_error_sum += float(metrics["mae"]) * int(metrics["count"])
            total_count += int(metrics["count"])
    global_mae = regression_metrics(truth, prediction)["mae"]
    reconstructed = absolute_error_sum / total_count if total_count else float("nan")
    difference = abs(float(global_mae) - reconstructed)
    return {
        "cells": cells,
        "global_mae": global_mae,
        "weighted_reconstructed_mae": reconstructed,
        "absolute_difference": difference,
        "reconstruction_pass": bool(difference <= 1e-9),
        "total_count": total_count,
    }
