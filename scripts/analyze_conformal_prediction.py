"""共形预测快速验证（D6-3）：标准共形 vs 规则路由分层共形（第 5 章 5.3 候选）。

目的（决策工具，非正式实验）：
  验证"共形预测不确定性量化"方向是否成立，并检验一个潜在的论文贡献点：
  全局 per-node 校准是否在事件窗口覆盖不足（事件窗口误差是稳定窗口的
  27.7 倍，全局分位数被稳定样本主导 → 事件窗口区间偏窄 → 覆盖率不足）。

方法（审查 2026-08-01 口径）：
  1. 加载 SG-EXP-003 正式 checkpoint（3 种子）→ 验证集前向得到残差
  2. 校准：alpha=0.1（90% 目标覆盖）；分层变量 = 冻结规则触发（与测试路由同变量）
     - 标准共形：per-node 全局残差分位数 q_global[N]
     - 规则路由分层共形：触发层全局分位数 q_event_rule[N]/未触发层 per-node q_stable_rule[N]
     - oracle 事后上界（对比）：真实标签分层校准 + 标签路由（不具备部署意义）
  3. 测试集前向 → 区间 → 覆盖率（整体 + 事件/稳定窗口 + 分 horizon）
  4. 三种口径的覆盖率对比

判定逻辑（规则路由正式口径）：
  标准共形在事件窗口覆盖率显著不足（<85%）
  → 分层共形（规则路由）若达标 → 可部署贡献；
  若未达标但 oracle 上界达标 → 分层校准机制有效，路由信号受限——
  定位为"事件窗口覆盖失效诊断 + 分层校准潜力上界分析"（5.3 核心内容）
  两者均不足 → 数据分布问题，方向降级

用法（本地 CPU/GPU 均可）：
  export PYTHONPATH=src
  .venv/bin/python scripts/analyze_conformal_prediction.py \
    --sg003-root outputs/night_run/20260730-171821/SG-EXP-003/20260730-171821
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
)
from evcs_station_graph.graphs import build_relation_set
from evcs_station_graph.models.graph import StaticGraphForecast
from evcs_station_graph.reproducibility import write_json
from evcs_station_graph.training.engine import _make_loader, _predict, _select_device

# 目标覆盖率（1-alpha=90%）：论文常用 90% 预测区间
ALPHA = 0.1
# 覆盖率达标阈值：有限样本共形保证覆盖 ≥ 1-alpha 但会略低（因校准集有限），
# 取 85% 作为"达标"判定线；事件窗口覆盖显著不足的判定线为 <85%
COVERAGE_TARGET = 0.90
COVERAGE_PASS = 0.85


def _load_model(
    checkpoint_path: Path,
    config: dict,
    bundle: TensorBundle,
    device: torch.device,
) -> StaticGraphForecast:
    """加载 StaticGraph 模型（与 D5-1/D5-1b 脚本同口径：从 checkpoint 推断参数）。"""
    payload = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    state = payload.get("model_state", payload)

    conv_key = "tcn.network.0.conv.weight"
    inferred_input_dim = int(state[conv_key].shape[1]) if conv_key in state else 7
    num_layers = len([k for k in state
                      if k.startswith("tcn.network.") and k.endswith(".conv.weight")])
    inferred_levels = num_layers if num_layers > 0 else int(config["experiment"]
                                                            .get("model_params", {})
                                                            .get("levels", 6))

    graph_cfg = config["experiment"].get("graph", {})
    train_end = int(bundle.split_origins["train"][-1])
    adjacencies = build_relation_set(
        bundle.features[: train_end + 1], bundle.targets[: train_end + 1],
        bundle.feature_names, top_k=int(graph_cfg.get("top_k", 3)),
    ).as_list()

    params = config["experiment"].get("model_params", {})
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


def _per_node_quantiles(
    residuals: np.ndarray, alpha: float,
) -> np.ndarray:
    """per-node 残差分位数：对 [S,H,N] 残差按节点取 (1-alpha) 分位。

    节点负荷量级差异超过 2 倍，必须按节点分别校准区间宽度，
    否则大负荷节点主导全局分位数，小负荷节点的区间过宽。
    """
    return np.quantile(residuals, 1.0 - alpha, axis=(0, 1)).astype(np.float32)


def _global_quantile(residuals: np.ndarray, alpha: float) -> float:
    """全局残差分位数：跨节点、跨样本的 (1-alpha) 分位。

    用于事件层校准——事件窗口样本占比仅 ~0.1%，per-node 分层后
    每节点事件样本仅几十个，分位数估计噪声过大；全局校准牺牲节点
    特异性换取统计稳定性。
    """
    return float(np.quantile(residuals, 1.0 - alpha))


def _masked_per_node_quantiles(
    residuals: np.ndarray, mask: np.ndarray, alpha: float,
) -> np.ndarray:
    """按布尔掩码选取 [S,H,N] 样本后逐节点取 (1-alpha) 分位。

    布尔索引会压平数组（丢失 H、N 结构），因此先记录节点索引再逐节点
    分组计算分位数。用于稳定层校准（样本充足，可 per-node 分层）。
    """
    n_nodes = residuals.shape[2]
    selected = residuals[mask]  # [K]，仅被选中的样本
    node_ids_flat = np.broadcast_to(np.arange(n_nodes), residuals.shape)[mask]
    quantiles = np.zeros(n_nodes, dtype=np.float32)
    for n in range(n_nodes):
        sel = selected[node_ids_flat == n]
        if sel.size == 0:
            raise ValueError(f"掩码后节点 {n} 无样本，无法校准分位数")
        quantiles[n] = np.quantile(sel, 1.0 - alpha)
    return quantiles


def _coverage_report(
    truth: np.ndarray, prediction: np.ndarray, widths: np.ndarray,
    target_event: np.ndarray, node_ids: list[str],
) -> dict[str, Any]:
    """按给定区间宽度计算覆盖率与分层覆盖率。

    widths：[N] per-node 半宽（标准共形）或 [S,H,N] 逐样本半宽（分层共形）。
    区间 = [pred - width, pred + width]。
    返回整体覆盖率、事件/稳定窗口覆盖率、per-horizon 覆盖率、平均区间宽度。
    """
    widths_full = widths[None, None, :] if widths.ndim == 1 else widths
    covered = np.abs(truth - prediction) <= widths_full
    event = target_event
    stable = ~event
    report: dict[str, Any] = {
        "coverage_overall": float(np.mean(covered)),
        "coverage_event_window": float(np.mean(covered[event])) if event.any() else None,
        "coverage_stable_window": float(np.mean(covered[stable])),
        "coverage_by_horizon": [
            float(np.mean(covered[:, h])) for h in range(covered.shape[1])
        ],
        "mean_interval_width": float(np.mean(2.0 * widths)),
    }
    if widths.ndim == 1:
        report["interval_width_by_node"] = {
            str(node_ids[i]): float(2.0 * widths[i]) for i in range(len(node_ids))
        }
    else:
        # 分层版本宽度随样本变化：按节点平均（事件层宽、稳定层窄的混合）
        report["interval_width_by_node"] = {
            str(node_ids[i]): float(np.mean(2.0 * widths[:, :, i]))
            for i in range(len(node_ids))
        }
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="D6-3 共形预测快速验证")
    parser.add_argument("--sg003-root", required=True, help="SG-EXP-003 运行根目录")
    parser.add_argument("--project", default="configs/project.yaml",
                        help="项目配置文件（用于重建关系图）")
    parser.add_argument("--dataset", default="data/processed/SG-DATA-005-primary-tensor.npz")
    parser.add_argument("--output-dir", default="outputs/analysis/conformal_prediction")
    parser.add_argument("--alpha", type=float, default=ALPHA)
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
        "validation": _make_loader(datasets["validation"], batch_size, False, 2024),
        "test": _make_loader(datasets["test"], batch_size, False, 2024),
    }

    rule = fit_frozen_event_rule(bundle, quantile=0.95, window_extension=2)
    trigger_by_origin = np.zeros((len(bundle.timestamps_ns), len(bundle.node_ids)), dtype=bool)
    for ds in datasets.values():
        trigger_by_origin[ds.origins] = apply_frozen_event_rule(bundle, ds.origins, rule)

    root = Path(args.sg003_root).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    node_ids = bundle.node_ids.tolist()
    started = time.perf_counter()

    per_seed: list[dict[str, Any]] = []
    seeds = [2024, 2025, 2026]
    for seed in seeds:
        ckpt = root / f"seed-{seed}" / "model.pt"
        if not ckpt.is_file():
            print(f"  ⚠ 跳过 seed={seed}：checkpoint 不存在", flush=True)
            continue
        model = _load_model(ckpt, config, bundle, device)

        # ---- 校准阶段：验证集残差（[S,H,N]，物理量纲） ----
        val = _predict(model, loaders["validation"], device, trigger_by_origin, bundle)
        val_residuals = np.abs(val["truth"] - val["prediction"])
        # rule_trigger 为 [S,N]，广播到 [S,H,N]（与残差同形，供布尔掩码）
        val_rule = np.broadcast_to(val["rule_trigger"][:, None, :],
                                   val_residuals.shape)

        # 标准共形：per-node 全局分位数
        q_global = _per_node_quantiles(val_residuals, args.alpha)
        # 分层共形（正式口径，审查 2026-08-01 修正）：校准分层变量 = 测试路由变量
        # = 冻结规则触发（可见信号）。事件/触发层用全局分位数（触发样本占比有限），
        # 未触发层用 per-node 分位数（样本充足）
        q_event_rule = np.full(
            len(bundle.node_ids),
            _global_quantile(val_residuals[val_rule], args.alpha),
            dtype=np.float32,
        )
        q_stable_rule = _masked_per_node_quantiles(
            val_residuals, ~val_rule, args.alpha)
        # oracle 对比（事后上界）：真实标签分层校准（分层变量 = 标签事件）
        val_event = val["target_event"]
        q_event_oracle = np.full(
            len(bundle.node_ids),
            _global_quantile(val_residuals[val_event], args.alpha),
            dtype=np.float32,
        )
        q_stable_oracle = _masked_per_node_quantiles(
            val_residuals, ~val_event, args.alpha)

        # ---- 评价阶段：测试集 ----
        test = _predict(model, loaders["test"], device, trigger_by_origin, bundle)
        widths_global = q_global
        # 正式口径（审查 2026-08-01）：规则分层校准 + 规则触发路由——校准与测试
        # 使用同一分层变量（可见冻结规则），无测试泄漏，标准 Mondrian 分层共形语义
        widths_stratified = np.where(
            test["rule_trigger"][:, None, :], q_event_rule[None, None, :],
            q_stable_rule[None, None, :],
        )
        # oracle 事后上界（对比）：真实标签分层校准 + 标签路由
        widths_oracle = np.where(
            test["target_event"], q_event_oracle[None, None, :],
            q_stable_oracle[None, None, :],
        )

        report_global = _coverage_report(
            test["truth"], test["prediction"], widths_global,
            test["target_event"], node_ids,
        )
        report_stratified = _coverage_report(
            test["truth"], test["prediction"], widths_stratified,
            test["target_event"], node_ids,
        )
        report_oracle = _coverage_report(
            test["truth"], test["prediction"], widths_oracle,
            test["target_event"], node_ids,
        )
        row = {
            "seed": seed,
            "standard_conformal": report_global,
            "stratified_conformal": report_stratified,
            "stratified_oracle_upper": report_oracle,
            "q_global_per_node": q_global.tolist(),
            # 正式口径：规则分层校准分位数（与测试路由同变量）
            "q_event_per_node": q_event_rule.tolist(),
            "q_stable_per_node": q_stable_rule.tolist(),
            # oracle 口径：真实标签分层校准分位数（诊断/上界用）
            "q_event_oracle_per_node": q_event_oracle.tolist(),
            "q_stable_oracle_per_node": q_stable_oracle.tolist(),
        }
        per_seed.append(row)
        print(f"\nseed={seed} 标准共形：整体覆盖={report_global['coverage_overall']:.3f} "
              f"事件窗口={report_global['coverage_event_window']:.3f} "
              f"稳定窗口={report_global['coverage_stable_window']:.3f}")
        print(f"       分层共形：整体覆盖={report_stratified['coverage_overall']:.3f} "
              f"事件窗口={report_stratified['coverage_event_window']:.3f} "
              f"稳定窗口={report_stratified['coverage_stable_window']:.3f}", flush=True)

    # ---- 聚合与判定 ----
    # 健壮性（审查发现）：全部种子 checkpoint 缺失时 per_seed 为空，
    # np.mean([]) 产生 NaN 覆盖率并给出"未通过"误导判定——先显式报错
    if not per_seed:
        raise RuntimeError(
            f"没有可用的种子结果（{root} 下 seed-*/model.pt 均缺失？），"
            "无法进行共形校准判定"
        )
    agg = {
        "seeds": seeds,
        "alpha": args.alpha,
        "standard_overall_mean": float(np.mean(
            [r["standard_conformal"]["coverage_overall"] for r in per_seed])),
        "standard_event_mean": float(np.mean([
            r["standard_conformal"]["coverage_event_window"] for r in per_seed])),
        "standard_stable_mean": float(np.mean([
            r["standard_conformal"]["coverage_stable_window"] for r in per_seed])),
        "stratified_overall_mean": float(np.mean(
            [r["stratified_conformal"]["coverage_overall"] for r in per_seed])),
        "stratified_event_mean": float(np.mean([
            r["stratified_conformal"]["coverage_event_window"] for r in per_seed])),
        "stratified_stable_mean": float(np.mean([
            r["stratified_conformal"]["coverage_stable_window"] for r in per_seed])),
        # oracle 上界对比（真实标签路由，仅事后诊断用）
        "stratified_oracle_event_mean": float(np.mean([
            r["stratified_oracle_upper"]["coverage_event_window"] for r in per_seed])),
        "stratified_oracle_overall_mean": float(np.mean([
            r["stratified_oracle_upper"]["coverage_overall"] for r in per_seed])),
        "per_seed": per_seed,
        "elapsed_seconds": time.perf_counter() - started,
    }

    standard_event = agg["standard_event_mean"]
    stratified_event = agg["stratified_event_mean"]
    oracle_event = agg["stratified_oracle_event_mean"]
    if standard_event < COVERAGE_PASS and stratified_event >= COVERAGE_PASS:
        verdict = (
            f"通过 + 论文贡献（规则路由可部署版）：标准共形事件窗口覆盖不足"
            f"（{standard_event:.1%}），规则路由分层共形达标（{stratified_event:.1%}）"
            f"；oracle 事后上界 {oracle_event:.1%}"
        )
    elif stratified_event >= COVERAGE_PASS:
        verdict = "通过：规则路由分层共形事件窗口覆盖达标，简单共形即够用（贡献点较弱）"
    else:
        verdict = "未通过：规则路由分层共形事件窗口覆盖仍不足，方向降级"
    agg["verdict"] = verdict
    print(f"\n标准共形事件窗口覆盖：{standard_event:.1%} vs "
          f"规则路由分层共形：{stratified_event:.1%}（oracle 上界 {oracle_event:.1%}）")
    print(f"判定：{verdict}")

    out_path = output_dir / "conformal_summary.json"
    write_json(agg, out_path)
    print(f"结果已写入：{out_path}")
    print(f"总耗时：{time.perf_counter() - started:.1f}s", flush=True)


if __name__ == "__main__":
    main()
