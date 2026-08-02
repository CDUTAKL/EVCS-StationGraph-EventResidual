"""第 4/5 章新增 4 图：图 4-6、4-7、5-10、5-11。

- 图 4-6 预测残差分布：TCN/StaticGraph/AdaptiveGraph 的全局与事件窗口残差
  核密度对比（事件窗口残差量级远大于全局，拆双面板）。
- 图 4-7 误差 vs 事件强度：测试集按事件分数分箱的 MAE 曲线（主模型 vs TCN）。
- 图 5-10 共形逐步长覆盖率与节点区间宽度：标准 vs 规则路由双对比。
- 图 5-11 TE 强度与三类统计关系权重一致性：90 有向对的散点 + Spearman r。

数据：SG-EXP-004 seed-2024 predictions.csv.gz、conformal_summary.json、
transfer_entropy_summary.json、SG-EXP-004 relation_matrices.npz。
输出：同名 SVG + 1200 DPI PNG。
"""

from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path.home() / ".claude/skills/scipilot-figure-skill/scripts"))
try:
    from export_figure import export_figure  # noqa: E402
    from setup_style import setup_style  # noqa: E402
except ImportError:  # 无 skill 环境回退
    from _skill_compat import export_figure, setup_style  # noqa: E402

sys.path.insert(0, "src")
from evcs_station_graph.data import load_tensor_bundle  # noqa: E402
from evcs_station_graph.evaluation.rules import fit_frozen_event_rule, visible_event_scores  # noqa: E402

FIG_DIR = Path("outputs/figures")
FIG_DIR.mkdir(parents=True, exist_ok=True)
setup_style(journal="general", lang="zh")

BLUE = "#2C5F8A"
ORANGE = "#D08A3C"
GRAY_D = "#404040"
GRAY_M = "#808080"
GRAY_L = "#C8C8C8"
GRAY_XL = "#E6E9EC"
RED = "#B05A4A"
GREEN = "#597A62"

BUNDLE = load_tensor_bundle("data/processed/SG-DATA-005-primary-tensor.npz")
CONFORMAL = json.load(open("outputs/analysis/conformal_prediction/conformal_summary.json"))
TE = json.load(open("outputs/analysis/transfer_entropy/transfer_entropy_summary.json"))


def _final(fig, name: str, size: tuple) -> None:
    """导出 SVG + 1200 DPI PNG。"""
    export_figure(fig, basename=str(FIG_DIR / name), formats=["svg", "png"],
                  dpi=1200, size_inches=size, grayscale_preview=False)
    print(f"  ✅ {name}")


def _clean(ax, grid_axis="y") -> None:
    """去除上/右边框，网格线保持浅色。"""
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color(GRAY_D)
    ax.tick_params(labelsize=8, colors=GRAY_D)
    if grid_axis:
        ax.grid(axis=grid_axis, color=GRAY_L, lw=0.55, alpha=0.72, zorder=0)


def redraw_fig4_6() -> None:
    """图 4-6：预测残差分布（全局 vs 事件窗口，三模型核密度）。"""
    resids = {}
    for exp, label, color in [("SG-EXP-002", "TCN", GRAY_M),
                              ("SG-EXP-003", "StaticGraph", ORANGE),
                              ("SG-EXP-004", "AdaptiveGraph", BLUE)]:
        df = pd.read_csv(_pred_path(exp))
        df["resid"] = df["y_pred"] - df["y_true"]
        resids[label] = (df[~df["target_event"]]["resid"].to_numpy(),
                         df[df["target_event"]]["resid"].to_numpy())

    fig, axes = plt.subplots(1, 2, figsize=(8.6, 3.6))
    # 事件窗口残差量级约为全局的 20 倍，两面板各自限定绘图范围
    for win_key, (win_label, xmax) in enumerate(
            [("全局（非事件样本）", 0.05), ("事件窗口样本", 0.8)]):
        ax = axes[win_key]
        xs = np.linspace(-xmax, xmax, 300)
        # 三条 KDE 高度重叠（残差集中于 0 附近），颜色 + 线型双编码区分
        for label, color, ls in [("TCN", GRAY_M, "-"),
                                 ("StaticGraph", ORANGE, "--"),
                                 ("AdaptiveGraph", BLUE, "-.")]:
            r_global, r_evt = resids[label]
            r = r_global if win_key == 0 else r_evt
            kde = stats.gaussian_kde(r)
            ax.plot(xs, kde(xs), lw=1.5, ls=ls, label=label, color=color)
        ax.set_xlabel("预测残差（kWh/15 min）", fontsize=8.4)
        ax.set_ylabel("核密度", fontsize=8.4)
        ax.set_xlim(-xmax, xmax)
        ax.set_title(win_label, fontsize=8.8, color=GRAY_D, loc="left", pad=6)
        _clean(ax)
        if win_key == 0:
            ax.legend(fontsize=7.2, frameon=False, loc="upper right")
    _final(fig, "fig4_6_residual_distribution", (8.6, 3.6))
    return None


def _pred_path(exp: str) -> str:
    """返回实验 seed-2024 的 predictions.csv.gz 路径。"""
    hits = glob.glob(f"outputs/experiments/{exp}/*/seed-2024/predictions.csv.gz") \
        or glob.glob(f"outputs/night_run/20260730-171821/{exp}/*/seed-2024/predictions.csv.gz")
    if not hits:
        raise FileNotFoundError(f"{exp} 无 predictions.csv.gz")
    return hits[0]


def redraw_fig4_7() -> None:
    """图 4-7：误差 vs 事件强度——按事件分数分箱的 MAE 曲线。"""
    # 事件分数（可见代理）在测试集 origin 上计算
    rule = fit_frozen_event_rule(BUNDLE)
    scores = visible_event_scores(
        BUNDLE, BUNDLE.split_origins["test"],
        score_stats={k: np.asarray(v, dtype=np.float32)
                     for k, v in rule.score_stats.items()})  # [O, N]
    score_flat = scores.ravel()  # [O*N]
    df = pd.read_csv(_pred_path("SG-EXP-004"))
    test = df[(df["split"] == "test")].copy()
    # origin 序号 → 行号映射（predictions 的 origin_index 是全局时间索引；
    # score_flat 按 [O, N] 展平，行内偏移 = 节点索引 × 节点数）
    n_nodes = BUNDLE.node_ids.shape[0]
    o2row = {o: i for i, o in enumerate(BUNDLE.split_origins["test"])}
    test["score"] = [score_flat[o2row[o] * n_nodes + n]
                     for o, n in zip(test["origin_index"], test["node_index"])]
    test["abs_err"] = (test["y_pred"] - test["y_true"]).abs()

    # 事件分数分布：97.9% 为零、非零范围约 9–44（4 分量 std 归一化求和）。
    # 分箱取 0 单独一档 + 非零分数按 50%/95% 分位数分三档（95 分位≈冻结触发阈值）
    nz = score_flat[score_flat > 0]
    q50, q95 = np.percentile(nz, [50, 95])
    bins = [0.0, 1e-6, q50, q95, np.inf]
    labels = ["无事件\n(0)", "弱\n(非零低档)", "中\n(非零中档)", "强\n(≥95 分位≈触发)"]
    test["bin"] = pd.cut(test["score"], bins=bins, labels=labels,
                         include_lowest=True)
    fig, ax = plt.subplots(figsize=(6.8, 3.8))
    x = np.arange(len(labels))
    means, counts = [], []
    for lab in labels:
        sub = test[test["bin"] == lab]
        means.append(sub["abs_err"].mean())
        counts.append(len(sub))
    ax.plot(x, means, marker="o", ms=6, lw=1.6, color=BLUE, zorder=4)
    # 标注位置：高值点（>上限 70%）标签放点下方避免顶出图面
    ymax_show = max(means) * 1.28
    for xi, (m, c) in enumerate(zip(means, counts)):
        if m > ymax_show * 0.7:
            ax.text(xi, m - 0.004, f"{m:.3f}\nn={c:,}", ha="center",
                    va="top", fontsize=6.8, color=GRAY_D)
        else:
            ax.text(xi, m + 0.012, f"{m:.3f}\nn={c:,}", ha="center",
                    va="bottom", fontsize=6.8, color=GRAY_D)
    ax.set_ylim(0, ymax_show)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=7.6)
    ax.set_xlabel("事件强度分箱（可见事件分数）", fontsize=8.6)
    ax.set_ylabel("平均绝对误差（kWh/15 min）", fontsize=8.6)
    _clean(ax)
    _final(fig, "fig4_7_error_vs_event_intensity", (6.8, 3.8))
    return None


def redraw_fig5_10() -> None:
    """图 5-10：共形逐步长覆盖率 + 节点区间宽度（标准 vs 规则路由）。"""
    seeds = CONFORMAL["per_seed"]
    if len(seeds) != 3:
        raise ValueError(f"conformal_summary 应有 3 种子，实际 {len(seeds)}")
    hs = np.arange(1, 5)
    std_cov = np.asarray([s["standard_conformal"]["coverage_by_horizon"] for s in seeds])
    rule_cov = np.asarray([s["stratified_conformal"]["coverage_by_horizon"] for s in seeds])
    # interval_width_by_node 为 dict{节点: 宽度}：按固定节点顺序转数组
    node_order = list(BUNDLE.node_ids)
    std_w = np.asarray([[s["standard_conformal"]["interval_width_by_node"][n]
                         for n in node_order] for s in seeds])
    rule_w = np.asarray([[s["stratified_conformal"]["interval_width_by_node"][n]
                          for n in node_order] for s in seeds])

    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.7))
    ax = axes[0]
    for data, label, color in [(std_cov, "标准共形", GRAY_M),
                               (rule_cov, "规则路由分层共形", BLUE)]:
        mean, sd = data.mean(axis=0), data.std(axis=0)
        ax.errorbar(hs, mean, yerr=sd, fmt="o", ms=5.5, color=color,
                    ecolor=color, capsize=2.8, lw=1.1, label=label, zorder=4)
    ax.axhline(0.90, color=RED, lw=1.0, ls="--", zorder=1)
    ax.text(4.35, 0.905, "90% 目标", fontsize=7.0, color=RED, ha="right")
    ax.set_xticks(hs)
    ax.set_xticklabels([f"h={h}" for h in hs], fontsize=8.0)
    ax.set_ylim(0.55, 0.95)
    ax.set_xlabel("预测步长", fontsize=8.6)
    ax.set_ylabel("覆盖率（均值 ± 跨种子 SD）", fontsize=8.6)
    ax.legend(fontsize=7.0, frameon=False, loc="lower left")
    _clean(ax)

    ax = axes[1]
    node_order = list(BUNDLE.node_ids)
    x = np.arange(len(node_order))
    w = 0.36
    ax.bar(x - w / 2, std_w.mean(axis=0), width=w, color=GRAY_M,
           edgecolor="white", lw=0.5,
           yerr=std_w.std(axis=0), capsize=2.0, label="标准共形", zorder=3)
    ax.bar(x + w / 2, rule_w.mean(axis=0), width=w, color=BLUE,
           edgecolor="white", lw=0.5,
           yerr=rule_w.std(axis=0), capsize=2.0,
           label="规则路由分层共形", zorder=3)
    ax.set_xticks(x)
    ax.set_xticklabels(BUNDLE.node_ids, fontsize=6.8, rotation=45, ha="right")
    ax.set_ylabel("区间宽度（kWh/15 min）", fontsize=8.4)
    ax.legend(fontsize=6.8, frameon=False, loc="upper right")
    _clean(ax)
    _final(fig, "fig5_10_coverage_width", (9.2, 3.7))
    return None


def redraw_fig5_11() -> None:
    """图 5-11：TE 强度 vs 三类统计关系权重（90 有向对 × 3 关系散点）。"""
    te_mat = np.asarray(TE["te_matrix"], dtype=float)  # [N, N]
    rel = np.load("outputs/experiments/SG-EXP-004/20260731-102456/relation_matrices.npz")
    n = te_mat.shape[0]
    iu, ju = np.triu_indices(n, k=1)  # 45 对无向 → 双向 90 有向边
    pairs = []
    for i, j in zip(iu, ju):
        pairs.extend([(i, j), (j, i)])

    fig, axes = plt.subplots(1, 3, figsize=(9.6, 3.4))
    rel_names = [("load", "负荷耦合关系", BLUE),
                 ("event", "行为共现关系", ORANGE),
                 ("pattern", "轮廓相似关系", GREEN)]
    for ax, (key, name, color) in zip(axes, rel_names):
        w_mat = np.asarray(rel[key], dtype=float)
        te_vals = np.asarray([te_mat[i, j] for i, j in pairs])
        w_vals = np.asarray([w_mat[i, j] for i, j in pairs])
        # TE=0 的边（无显著信息流）画为灰色小叉，不混入散点云
        nz = te_vals > 0
        ax.scatter(w_vals[nz], te_vals[nz], s=16, color=color,
                   alpha=0.75, zorder=3, label="_nolegend_")
        ax.scatter(w_vals[~nz], te_vals[~nz], s=12, marker="x",
                   color=GRAY_M, alpha=0.7, zorder=2, label="_nolegend_")
        r, p = stats.spearmanr(w_vals, te_vals)
        # 显著性标注阈值：p<0.01 双星（探索性分析，未做多重比较校正）
        ax.text(0.97, 0.05, f"Spearman r = {r:.2f}{'**' if p < 0.01 else ''}",
                transform=ax.transAxes, ha="right", va="bottom",
                fontsize=7.4, color=GRAY_D)
        ax.set_xlabel(f"{name}权重", fontsize=7.8)
        ax.set_ylabel("TE(i→j)（nats）" if key == "load" else "",
                      fontsize=7.8)
        ax.set_xlim(0, 1)
        _clean(ax)
    _final(fig, "fig5_11_te_vs_relations", (9.6, 3.4))
    return None


if __name__ == "__main__":
    print("=== 批次 13：第 4/5 章新增 4 图 ===")
    redraw_fig4_6()
    redraw_fig4_7()
    redraw_fig5_10()
    redraw_fig5_11()
    print("批次 13 完成")
