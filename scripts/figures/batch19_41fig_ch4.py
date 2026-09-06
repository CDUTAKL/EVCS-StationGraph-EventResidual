#!/usr/bin/env python3
"""41 幅主文图重构：第 4 章新增 β 画像并增强四格诊断。

图 4-2：正式主模型 StaticGraph（SG-EXP-003）三种子 checkpoint 的两层
三关系 β（softmax）权重。图中展示每个种子值和均值±跨种子 SD，不将该
权重观察写成节点级门控或因果效应。

图 4-4：使用 SG-EXP-003 StaticGraph 三种子锁定证据的四格诊断。A 为各单元
MAE均值，B 为两个集合的样本组成，C 对比样本占比与绝对误差贡献占比。所有
比例均由锁定工件的 count×MAE 计算，避免使用四舍五入后的表中数字。
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.gridspec import GridSpec
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from matplotlib.ticker import FuncFormatter

sys.path.insert(0, str(Path.home() / ".claude/skills/scipilot-figure-skill/scripts"))
try:
    from export_figure import export_figure  # noqa: E402
    from setup_style import setup_style  # noqa: E402
except ImportError:
    from _skill_compat import export_figure, setup_style  # noqa: E402

FIG_DIR = Path("outputs/figures")
FIG_DIR.mkdir(parents=True, exist_ok=True)
setup_style(journal="general", lang="zh")

BLUE = "#2C5F8A"
BLUE_L = "#AFC4D2"
ORANGE = "#B97950"
ORANGE_L = "#E8CDBB"
GREEN = "#6F8874"
GREEN_L = "#C9D6CB"
GRAY_D = "#404040"
GRAY_M = "#808080"
GRAY_L = "#C8C8C8"
GRAY_XL = "#ECEFF1"

STATIC_ROOT = Path("outputs/night_run/20260730-171821/SG-EXP-003/20260730-171821")
FOUR_CELL_SUMMARY = Path(
    "outputs/analysis/SG-EXP-020-legacy-evidence-v1/four_cell_summary.csv"
)


def final(fig: plt.Figure, name: str, size: tuple[float, float]) -> None:
    export_figure(fig, basename=str(FIG_DIR / name), formats=["svg", "png"],
                  dpi=1200, size_inches=size, grayscale_preview=False)
    print(f"  OK {name}")


def clean_ax(ax, grid_axis: str = "y") -> None:
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color(GRAY_D)
    ax.tick_params(labelsize=8.2, colors=GRAY_D)
    if grid_axis:
        ax.grid(axis=grid_axis, color=GRAY_L, lw=0.55, alpha=0.75, zorder=0)


def panel_label(ax, label: str, text: str = "") -> None:
    ax.text(-0.11, 1.055, label, transform=ax.transAxes, ha="left", va="bottom",
            fontsize=10.5, fontweight="bold", color=GRAY_D)
    if text:
        ax.text(-0.045, 1.057, text, transform=ax.transAxes, ha="left", va="bottom",
                fontsize=8.5, color=GRAY_D)


def _softmax_from_checkpoint(path: Path) -> tuple[np.ndarray, np.ndarray]:
    payload = torch.load(path, map_location="cpu", weights_only=True)
    state = payload.get("model_state", payload)
    values = []
    for layer in ("gcn1", "gcn2"):
        raw = state[f"relation_weights_{layer}"].detach().cpu().numpy()
        if raw.size != 3:
            raise ValueError(f"{path}: {layer} 应为 3 个固定关系，实际为 {raw.size}")
        exp = np.exp(raw - raw.max())
        values.append(exp / exp.sum())
    return values[0], values[1]


def plot_beta_profile() -> None:
    """图4-2：两层关系权重的均值、跨种子SD与单种子读数。"""
    weights = []
    for seed in (2024, 2025, 2026):
        weights.append(_softmax_from_checkpoint(STATIC_ROOT / f"seed-{seed}" / "model.pt"))
    values = np.asarray(weights, dtype=float)  # [3 seeds, 2 layers, 3 relations]
    names = ["负荷耦合", "行为共现", "轮廓相似"]
    x = np.arange(3, dtype=float)
    layer_colors = [BLUE, ORANGE]
    layer_markers = ["o", "D"]
    offsets = [-0.09, 0.09]
    fig, ax = plt.subplots(figsize=(9.0, 4.65))
    fig.set_layout_engine(None)
    ax.axhline(1 / 3, color=GRAY_L, lw=0.8, ls="--", zorder=0)
    ax.text(2.46, 1 / 3, "等权 1/3", ha="right", va="bottom",
            fontsize=7.2, color=GRAY_M)
    for layer_idx, (color, marker, offset) in enumerate(
            zip(layer_colors, layer_markers, offsets)):
        means = values[:, layer_idx, :].mean(axis=0)
        sds = values[:, layer_idx, :].std(axis=0, ddof=1)
        # 每个随机种子的三关系轮廓以极细线连接，主视觉仍由均值和误差棒承担。
        for seed_values in values[:, layer_idx, :]:
            ax.plot(x + offset, seed_values, color=color, lw=0.65, alpha=0.22, zorder=1)
            ax.scatter(x + offset, seed_values, s=18, marker=marker,
                       facecolor="white", edgecolor=color, lw=0.75, alpha=0.75, zorder=2)
        ax.errorbar(x + offset, means, yerr=sds, color=color, marker=marker,
                    markerfacecolor=color, markeredgecolor="white", markeredgewidth=0.9,
                    ms=7.5, lw=1.7, elinewidth=1.25, capsize=3.5, capthick=1.1,
                    label=f"第{layer_idx + 1}层", zorder=4)
        for xi, mean in zip(x + offset, means):
            dy = 0.008 if layer_idx == 0 else -0.010
            va = "bottom" if layer_idx == 0 else "top"
            ax.text(xi, mean + dy, f"{mean:.3f}", ha="center", va=va,
                    fontsize=7.3, color=color, fontweight="bold")
    ax.set_xlim(-0.42, 2.48)
    ax.set_ylim(0.225, 0.430)
    ax.set_xticks(x, names, fontsize=9.0)
    ax.set_ylabel("关系级权重 β", fontsize=8.8)
    clean_ax(ax, "y")
    ax.legend(frameon=False, loc="upper right", fontsize=8.2, ncol=2,
              handlelength=2.4, columnspacing=1.6)
    final(fig, "fig4_2_beta_profile", (9.0, 4.65))
    plt.close(fig)


def plot_four_cell_enhanced() -> None:
    """图4-4：三种子 MRG-GCN 四格 MAE 与误差贡献错位点线图。"""
    if not FOUR_CELL_SUMMARY.is_file():
        raise FileNotFoundError(
            f"缺少锁定四格汇总 {FOUR_CELL_SUMMARY}，请先运行 scripts/lock_legacy_evidence.py"
        )
    keys = ["target_event_triggered", "target_event_not_triggered",
            "stable_triggered", "stable_not_triggered"]
    labels = ["事件×触发", "事件×未触发", "非事件×触发", "非事件×未触发"]
    colors = [BLUE, ORANGE, "#7C8B92", "#B8C0C4"]
    summary = pd.read_csv(FOUR_CELL_SUMMARY).set_index("cell").loc[keys]
    counts = summary["n"].to_numpy(dtype=float)
    maes = summary["mae_mean"].to_numpy(dtype=float)
    mae_sds = summary["mae_sd"].to_numpy(dtype=float)
    contributions = counts * maes
    matrix = np.array([[maes[0], maes[1]], [maes[2], maes[3]]])
    sample_share = counts / counts.sum() * 100
    error_share = contributions / contributions.sum() * 100

    # 一个主矩阵加一个配对点线图，避免把同一证据拆成多个零碎面板。
    fig = plt.figure(figsize=(10.0, 5.2), constrained_layout=False)
    fig.set_layout_engine(None)
    gs = GridSpec(1, 2, figure=fig, width_ratios=[1.22, 1.0],
                  left=0.08, right=0.96, bottom=0.17, top=0.88, wspace=0.30)

    ax = fig.add_subplot(gs[0, 0])
    cmap = LinearSegmentedColormap.from_list(
        "muted_blue", ["#F2F5F7", "#C8D8E4", "#78A2C0", "#2C5F8A"])
    ax.set_xlim(0, 2)
    ax.set_ylim(0, 2)
    ax.set_aspect("equal")
    ax.set_anchor("N")
    for i in range(2):
        for j in range(2):
            value = matrix[i, j]
            y0 = 1 - i
            ax.add_patch(Rectangle((j, y0), 1, 1,
                                   facecolor=cmap(value / 0.30), edgecolor="white",
                                   linewidth=2.3))
            ax.text(j + 0.5, y0 + 0.43, f"{value:.4f}", ha="center", va="center", fontsize=12.5,
                    fontweight="bold", color="white" if value > 0.16 else GRAY_D)
            ax.text(j + 0.5, y0 + 0.67, f"n = {int(counts[i * 2 + j]):,}", ha="center", va="center",
                    fontsize=7.4, color="white" if value > 0.16 else GRAY_D)
            ax.text(j + 0.5, y0 + 0.23, f"s = {mae_sds[i * 2 + j]:.4f}", ha="center", va="center",
                    fontsize=6.9, color="white" if value > 0.16 else GRAY_M)
    ax.set_xticks([0.5, 1.5], ["规则触发", "规则未触发"], fontsize=9)
    ax.set_yticks([1.5, 0.5], ["标签事件", "标签非事件"], fontsize=9)
    ax.tick_params(length=0)
    ax.set_xlabel("规则触发状态", fontsize=8.5, labelpad=7)
    for spine in ax.spines.values():
        spine.set_visible(False)
    panel_label(ax, "A", "四格单元误差")

    ax = fig.add_subplot(gs[0, 1])
    y = np.arange(4)[::-1]
    for idx, yi in enumerate(y):
        ax.plot([sample_share[idx], error_share[idx]], [yi, yi], color=colors[idx],
                lw=2.0, alpha=0.80, zorder=2)
        ax.scatter(sample_share[idx], yi, s=52, facecolor="white",
                   edgecolor=colors[idx], lw=1.25, zorder=3)
        ax.scatter(error_share[idx], yi, s=58, facecolor=colors[idx],
                   edgecolor="white", lw=0.9, zorder=4)
        # 两个百分比采用上下错位标注，极小值也不会互相覆盖。
        sample_text = "<0.1%" if sample_share[idx] < 0.05 else f"{sample_share[idx]:.1f}%"
        ax.text(sample_share[idx], yi + 0.20, sample_text,
                ha="center", va="bottom", fontsize=7.0, color=GRAY_M)
        ax.text(error_share[idx], yi - 0.20, f"{error_share[idx]:.1f}%",
                ha="center", va="top", fontsize=7.0, color=colors[idx],
                fontweight="bold")
    ax.set_yticks(y, labels, fontsize=8.2)
    ax.set_xlim(-2, 102)
    ax.set_ylim(-0.65, 3.65)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, pos: f"{v:.0f}%"))
    ax.set_xlabel("占全体样本（或绝对误差）的比例", fontsize=8.2)
    clean_ax(ax, "x")
    ax.legend(handles=[
        Line2D([], [], marker="o", markerfacecolor="white", markeredgecolor=GRAY_M,
               linestyle="none", label="样本占比"),
        Line2D([], [], marker="o", markerfacecolor=GRAY_M, markeredgecolor="white",
               linestyle="none", label="绝对误差贡献"),
    ], loc="lower right", frameon=False, fontsize=7.5, ncol=2,
       bbox_to_anchor=(1.0, 1.01))
    panel_label(ax, "B", "样本占比与误差贡献错位")

    fig.text(0.08, 0.055, "注：MAE为StaticGraph三种子均值，s为跨种子样本标准差；绝对误差贡献按 n×MAE计算。",
             fontsize=7.5, color=GRAY_M)
    final(fig, "fig4_4_four_cell", (10.0, 5.2))
    plt.close(fig)


if __name__ == "__main__":
    plot_beta_profile()
    plot_four_cell_enhanced()
