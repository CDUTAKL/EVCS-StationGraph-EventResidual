"""重绘 9 张问题图（对齐老论文素雅风格：灰阶 + 深蓝强调 + 低饱和）。

修复清单（用户 2026-08-01 反馈）：
- fig2_3b 自相关：文字遮挡曲线 + 顶部空旷 → y 上限 0.8、标注移至空白区、宽线+浅网格
- fig2_5 分布：右上角文字删除 + 2.0 后空旷 → x 截断 0-2.5 + 对数 y
- fig2_6 事件时间线：堆叠面积丑陋 → 4 行子图共享 x 轴
- fig3_1 误差棒不明显 → 加粗 + 大 capsize + 深色
- fig3_6 Bootstrap → 素雅重设计（点+粗误差棒+浅网格）
- fig4_4 四格 → 精致热力图（白网格线 + 大方格 + 双行标注）
- fig5_3 配色 → 深蓝/橙/灰素雅配色
- fig5_4 覆盖率 → 加大间距、标签不遮挡
- fig5_5 分位数 → 加大 figsize、布局舒展

统一规范：无标题、无文件名/代号、SVG+PNG 1200DPI。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path.home() / ".claude/skills/scipilot-figure-skill/scripts"))
from export_figure import export_figure  # noqa: E402
from setup_style import setup_style  # noqa: E402

sys.path.insert(0, "src")
from evcs_station_graph.data import load_tensor_bundle  # noqa: E402

FIG_DIR = Path("outputs/figures")
FIG_DIR.mkdir(parents=True, exist_ok=True)

setup_style(journal="general", lang="zh")
# 素雅配色（对齐老论文：深蓝主色 + 灰阶 + 低饱和强调）
BLUE = "#2C5F8A"      # 深蓝（老论文 40,80,120）
ORANGE = "#D08A3C"    # 低饱和橙
GRAY_D = "#404040"    # 深灰
GRAY_M = "#808080"    # 中灰
GRAY_L = "#C8C8C8"    # 浅灰
RED_S = "#B05A4A"     # 低饱和红
BUNDLE = load_tensor_bundle("data/processed/SG-DATA-005-primary-tensor.npz")


def final(fig, name: str, size: tuple[float, float]) -> None:
    """统一导出：SVG 矢量 + PNG 1200 DPI（论文硬性约束）。"""
    export_figure(
        fig, basename=str(FIG_DIR / name),
        formats=["svg", "png"], dpi=1200, size_inches=size,
        grayscale_preview=False,
    )
    print(f"  ✅ {name}")


def _clean_ax(ax, xlabel=None, ylabel=None):
    """统一轴风格：细边框 + 浅网格 + 标签。"""
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color(GRAY_D)
    ax.tick_params(labelsize=8, colors=GRAY_D)
    ax.grid(axis="y", color=GRAY_L, lw=0.5, alpha=0.6, zorder=0)
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=9)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=9)


# ========== ① fig2_3b 自相关（重绘） ==========
def redraw_autocorrelation() -> None:
    nodes = ["CA-303", "CA-327", "CA-489"]
    lags = np.arange(1, 193)
    fig, ax = plt.subplots(figsize=(6.8, 3.2))
    for n, c, ls, lw in zip(nodes, [BLUE, GRAY_D, GRAY_M], ["-", "--", "-."], [1.6, 1.4, 1.4]):
        idx = list(BUNDLE.node_ids).index(n)
        s = BUNDLE.targets[:, idx]
        acf = np.array([np.corrcoef(s[:-l], s[l:])[0, 1] for l in lags])
        ax.plot(lags / 4.0, acf, color=c, ls=ls, lw=lw, label=n)
    # 周期标注放在曲线下方空白（不遮挡）
    ax.axvline(24, color=GRAY_L, lw=0.9, ls="--")
    ax.axvline(168, color=GRAY_L, lw=0.9, ls="--")
    ax.text(24, 0.03, "24 h", fontsize=7.5, color=GRAY_M, ha="center")
    ax.text(168, 0.03, "168 h", fontsize=7.5, color=GRAY_M, ha="center")
    ax.set_xlabel("滞后（小时）", fontsize=9)
    ax.set_ylabel("自相关系数", fontsize=9)
    ax.set_ylim(-0.05, 0.8)
    ax.legend(fontsize=8, frameon=False, ncol=3, loc="upper right")
    _clean_ax(ax)
    final(fig, "fig2_3b_autocorrelation", (6.8, 3.2))


# ========== ② fig2_5 负荷分布（重绘） ==========
def redraw_distribution() -> None:
    vals = BUNDLE.targets.flatten()
    vals = vals[vals > 0]
    fig, ax = plt.subplots(figsize=(6.2, 3.4))
    ax.hist(vals, bins=np.arange(0, 2.6, 0.05), color=BLUE,
            edgecolor="white", linewidth=0.3, zorder=3)
    ax.set_yscale("log")
    ax.set_xlabel("负荷（kWh/15min）", fontsize=9)
    ax.set_ylabel("样本数（对数轴）", fontsize=9)
    ax.set_xlim(0, 2.5)
    _clean_ax(ax)
    final(fig, "fig2_5_load_distribution", (6.2, 3.4))


# ========== ③ fig2_6 事件时间线（重绘：4 行子图） ==========
def redraw_event_timeline() -> None:
    f = BUNDLE.features
    comps = {
        "access": f[:, 0, 1], "departure": f[:, 0, 2],
        "active_delta": np.abs(np.diff(f[:, 0, 3], prepend=f[0, 0, 3])),
        "load_delta": f[:, 0, 6].astype(float),
    }
    t0, t1 = 96 * 20, 96 * 21
    fig, axes = plt.subplots(4, 1, figsize=(6.8, 4.6), sharex=True,
                             gridspec_kw={"hspace": 0.12})
    x = np.arange(t1 - t0) / 4.0
    colors = [BLUE, ORANGE, GRAY_D, RED_S]
    for ax, (name, c) in zip(axes, zip(comps, colors)):
        seg = comps[name][t0:t1]
        ax.fill_between(x, 0, seg, color=c, alpha=0.75, lw=0)
        ax.set_ylabel(name.replace("_", " "), fontsize=7.5, rotation=0,
                      ha="right", va="center", color=GRAY_D)
        ax.tick_params(labelsize=7)
        ax.spines[["top", "right"]].set_visible(False)
        ax.set_yticks([])
    axes[-1].set_xlabel("时间（小时）", fontsize=9)
    _clean_ax(axes[0])
    for ax in axes:
        ax.grid(False)
    final(fig, "fig2_6_event_timeline", (6.8, 4.6))


# ========== ④ fig3_1 误差棒加强（重绘） ==========
def redraw_model_comparison() -> None:
    data = [
        ("StaticGraph\n(MRG-GCN)", 0.01376, None), ("AdaptiveGraph", 0.01396, 0.00010),
        ("GraphWaveNet", 0.01773, 0.00054), ("MLP", 0.02112, 0.00019),
        ("ARIMA(2,1,2)", 0.02260, None), ("TCN", 0.02952, None),
        ("LightGBM", 0.03758, None), ("XGBoost", 0.03873, None),
        ("Persistence", 0.07828, None),
    ]
    data.sort(key=lambda x: x[1])
    names = [d[0] for d in data]
    maes = [d[1] for d in data]
    stds = [d[2] for d in data]
    colors = [BLUE if i == 0 else GRAY_M for i in range(len(names))]

    fig, ax = plt.subplots(figsize=(6.8, 4.0))
    y = np.arange(len(names))
    bars = ax.barh(y, maes, height=0.62, color=colors,
                   edgecolor=GRAY_D, linewidth=0.5, zorder=3)
    for yi, (mae, std) in enumerate(zip(maes, stds)):
        if std is not None:
            ax.errorbar(mae, yi, xerr=std, fmt="none", ecolor="black",
                        elinewidth=1.6, capsize=5, capthick=1.6, zorder=5)
        ax.text(mae + 0.0015, yi, f"{mae:.4f}", va="center", fontsize=8.5,
                color=GRAY_D)
    bars[0].set_color(BLUE)
    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=8.5)
    ax.set_xlabel("Global MAE (kWh/15min)", fontsize=9)
    ax.set_xlim(0, 0.095)
    ax.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=BLUE),
                       plt.Rectangle((0, 0), 1, 1, color=GRAY_M)],
              labels=["图模型（本文）", "对比方法"], fontsize=8, frameon=False,
              loc="lower right")
    _clean_ax(ax)
    final(fig, "fig3_1_model_mae_comparison", (6.8, 4.0))


# ========== ⑤ fig3_6 Bootstrap（重绘） ==========
def redraw_bootstrap() -> None:
    d = json.load(open("outputs/analysis/bootstrap_significance.json"))
    labels = {
        "TCN - StaticGraph": "TCN → StaticGraph",
        "StaticGraph - AdaptiveGraph": "StaticGraph → AdaptiveGraph",
        "AdaptiveGraph - EventResidual": "AdaptiveGraph → EventResidual",
        "StaticGraph - MLP": "StaticGraph → MLP",
        "TCN - MLP": "TCN → MLP",
        "AdaptiveGraph - no_event_gate": "AdaptiveGraph → no-event-gate",
    }
    names, means, lows, highs, ps = [], [], [], [], []
    for c in d["comparisons"]:
        keys0 = list(c["per_seed"].keys())
        win = "global" if "global" in c["per_seed"][keys0[0]] else "event_window"
        diffs = [c["per_seed"][s][win]["observed_diff"] for s in keys0]
        cis = [(c["per_seed"][s][win]["ci_lower"], c["per_seed"][s][win]["ci_upper"])
               for s in keys0]
        name = labels.get(c["name"], c["name"])
        if win == "event_window":
            name += "（事件窗口）"
        names.append(name)
        means.append(float(np.mean(diffs)))
        lows.append(float(min(l[0] for l in cis)))
        highs.append(float(max(l[1] for l in cis)))
        ps.append(min(c["per_seed"][s][win]["p_value_one_sided"] for s in keys0))

    fig, ax = plt.subplots(figsize=(6.8, 3.4))
    y = np.arange(len(names))
    err_low = np.array(means) - np.array(lows)
    err_high = np.array(highs) - np.array(means)
    for yi, (m, lo, hi) in enumerate(zip(means, err_low, err_high)):
        ax.plot([m - lo, m + hi], [yi, yi], color=BLUE, lw=2.2, zorder=3)
        ax.plot([m], [yi], "o", color=BLUE, ms=8, zorder=4)
        ax.plot([m - lo, m - lo], [yi - 0.22, yi + 0.22], color=BLUE, lw=1.4)
        ax.plot([m + hi, m + hi], [yi - 0.22, yi + 0.22], color=BLUE, lw=1.4)
        p = ps[yi]
        star = "***" if p < 0.001 else ("**" if p < 0.01 else ("*" if p < 0.05 else "ns"))
        ax.text(m + hi + 0.0006, yi, star, va="center", fontsize=10, color=GRAY_D)
    ax.axvline(0, color=GRAY_D, lw=1.0, ls="--", zorder=2)
    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=8)
    ax.set_xlabel("MAE 差（基线 − 提议模型，Bootstrap 10,000 次）", fontsize=8.5)
    _clean_ax(ax)
    final(fig, "fig3_6_bootstrap_significance", (6.8, 3.4))


# ========== ⑥ fig4_4 四格诊断（重绘） ==========
def redraw_four_cell() -> None:
    m = json.load(open("outputs/experiments/SG-EXP-004/20260731-102456/seed-2024/metrics.json"))
    fc = m["four_cell"]["cells"]
    matrix = np.array([
        [fc["target_event_triggered"]["mae"], fc["target_event_not_triggered"]["mae"]],
        [fc["stable_triggered"]["mae"], fc["stable_not_triggered"]["mae"]],
    ])
    counts = np.array([
        [fc["target_event_triggered"]["count"], fc["target_event_not_triggered"]["count"]],
        [fc["stable_triggered"]["count"], fc["stable_not_triggered"]["count"]],
    ])

    fig, ax = plt.subplots(figsize=(5.4, 4.4))
    cmap = plt.get_cmap("YlOrRd")
    im = ax.imshow(matrix, cmap=cmap, aspect="equal", vmin=0, vmax=matrix.max())
    # 白色粗网格线
    for i in range(3):
        ax.axhline(i - 0.5, color="white", lw=2.5)
    for j in range(3):
        ax.axvline(j - 0.5, color="white", lw=2.5)
    labels_rows = ["事件发生", "稳定时段"]
    labels_cols = ["规则触发", "规则未触发"]
    for i in range(2):
        for j in range(2):
            ax.text(j, i - 0.14, f"MAE = {matrix[i, j]:.4f}", ha="center",
                    fontsize=11, fontweight="bold", color="white" if matrix[i, j] > matrix.max() * 0.5 else "black")
            ax.text(j, i + 0.17, f"n = {counts[i, j]:,}  ({100 * counts[i, j] / counts.sum():.3f}%)",
                    ha="center", fontsize=8.5,
                    color="white" if matrix[i, j] > matrix.max() * 0.5 else "black")
    ax.set_xticks([0, 1])
    ax.set_xticklabels(labels_cols, fontsize=9.5)
    ax.set_yticks([0, 1])
    ax.set_yticklabels(labels_rows, fontsize=9.5)
    ax.set_xlabel("规则触发（冻结规则）", fontsize=9)
    ax.set_ylabel("真实事件", fontsize=9)
    ax.tick_params(length=0)
    final(fig, "fig4_4_four_cell", (5.4, 4.4))


# ========== ⑦ fig5_3 方向不对称（重绘：素雅配色） ==========
def redraw_asymmetry() -> None:
    te = json.load(open("outputs/analysis/transfer_entropy/transfer_entropy_summary.json"))
    pairs = te["asymmetry"]["top_asymmetric_pairs"][:5]
    names = [f"{p['node_i'].split('-')[1]}→{p['node_j'].split('-')[1]}" for p in pairs]
    te_ij = [p["te_i_to_j"] for p in pairs]
    te_ji = [p["te_j_to_i"] for p in pairs]
    asym = [p["asymmetry"] for p in pairs]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.2, 3.2),
                                   gridspec_kw={"width_ratios": [1.5, 1.0], "wspace": 0.28})
    x = np.arange(len(names))
    w = 0.34
    ax1.bar(x - w / 2, te_ij, w, label="i→j", color=GRAY_L, edgecolor=GRAY_D, linewidth=0.5, zorder=3)
    ax1.bar(x + w / 2, te_ji, w, label="j→i", color=BLUE, edgecolor=GRAY_D, linewidth=0.5, zorder=3)
    for xi, (a, b) in enumerate(zip(te_ij, te_ji)):
        ax1.text(xi, max(a, b) * 1.05 + 0.0001, f"{max(a, b) / max(min(a, b), 1e-9):.0f}×",
                 ha="center", fontsize=7.5, color=GRAY_D)
    ax1.set_xticks(x)
    ax1.set_xticklabels(names, fontsize=8.5)
    ax1.set_ylabel("传递熵（nats）", fontsize=8.5)
    ax1.set_ylim(0, max(te_ji) * 1.35)
    ax1.legend(fontsize=7.5, frameon=False, loc="upper left")
    _clean_ax(ax1)

    ax2.barh(np.arange(len(pairs)), asym, color=ORANGE, edgecolor=GRAY_D,
             linewidth=0.5, height=0.6, zorder=3)
    ax2.set_yticks(range(len(pairs)))
    ax2.set_yticklabels(names, fontsize=8.5)
    ax2.set_xlabel("不对称度", fontsize=8.5)
    ax2.set_xlim(0, 1)
    for xi, a in enumerate(asym):
        ax2.text(a + 0.02, xi, f"{a:.2f}", va="center", fontsize=7.5, color=GRAY_D)
    _clean_ax(ax2)
    final(fig, "fig5_3_asymmetry", (7.2, 3.2))


# ========== ⑧ fig5_4 覆盖率（重绘：舒展布局） ==========
def redraw_coverage() -> None:
    c = json.load(open("outputs/analysis/conformal_prediction/conformal_summary.json"))
    groups = ["全局", "事件窗口", "稳定窗口"]
    std_v = [c["standard_overall_mean"], c["standard_event_mean"], c["standard_stable_mean"]]
    str_v = [c["stratified_overall_mean"], c["stratified_event_mean"], c["stratified_stable_mean"]]

    fig, ax = plt.subplots(figsize=(6.2, 3.8))
    x = np.arange(3)
    w = 0.32
    b1 = ax.bar(x - w / 2, std_v, w, label="标准共形", color=GRAY_L,
                edgecolor=GRAY_D, linewidth=0.5, zorder=3)
    b2 = ax.bar(x + w / 2, str_v, w, label="分层共形", color=BLUE,
                edgecolor=GRAY_D, linewidth=0.5, zorder=3)
    for bars, offset in ((b1, -w / 2), (b2, w / 2)):
        for b in bars:
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.03,
                    f"{b.get_height():.1%}", ha="center", fontsize=9, color=GRAY_D)
    ax.axhline(0.9, color=GRAY_D, lw=1.1, ls="--", zorder=2)
    ax.text(2.35, 0.93, "90% 目标", fontsize=8, color=GRAY_D, ha="right")
    ax.set_xticks(x)
    ax.set_xticklabels(groups, fontsize=9.5)
    ax.set_ylabel("覆盖率（α = 0.1）", fontsize=9)
    ax.set_ylim(0, 1.05)
    ax.legend(fontsize=8, frameon=False, loc="lower right")
    _clean_ax(ax)
    final(fig, "fig5_4_coverage", (6.2, 3.8))


# ========== ⑨ fig5_5 分位数（重绘：舒展） ==========
def redraw_quantile() -> None:
    c = json.load(open("outputs/analysis/conformal_prediction/conformal_summary.json"))
    s0 = c["per_seed"][0]
    q_global = s0["q_global_per_node"]
    q_event = s0["q_event_per_node"]

    fig, ax = plt.subplots(figsize=(6.6, 3.4))
    x = np.arange(10)
    w = 0.34
    ax.bar(x - w / 2, q_global, w, label="全局分位数", color=GRAY_L,
           edgecolor=GRAY_D, linewidth=0.5, zorder=3)
    ax.bar(x + w / 2, q_event, w, label="事件层分位数", color=BLUE,
           edgecolor=GRAY_D, linewidth=0.5, zorder=3)
    ax.set_xticks(x)
    ax.set_xticklabels([n.split("-")[1] for n in BUNDLE.node_ids], fontsize=8.5)
    ax.set_ylabel("90% 分位数（标准化残差）", fontsize=8.5)
    ax.legend(fontsize=8, frameon=False, loc="upper left")
    _clean_ax(ax)
    final(fig, "fig5_5_quantile_per_node", (6.6, 3.4))


if __name__ == "__main__":
    print("=== 批次 4：重绘 9 张 ===")
    redraw_autocorrelation()
    redraw_distribution()
    redraw_event_timeline()
    redraw_model_comparison()
    redraw_bootstrap()
    redraw_four_cell()
    redraw_asymmetry()
    redraw_coverage()
    redraw_quantile()
    print("批次 4 完成")
