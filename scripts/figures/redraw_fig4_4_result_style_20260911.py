#!/usr/bin/env python3
"""重绘图4-4：用结果图风格呈现三种子四格诊断及误差贡献。"""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Rectangle


ROOT = Path(__file__).resolve().parents[2]
FIG_DIR = ROOT / "outputs" / "figures"
SUMMARY = ROOT / "outputs" / "analysis" / "SG-EXP-020-legacy-evidence-v1" / "four_cell_summary.csv"

FONT = ["Songti SC", "STSong", "PingFang SC", "Hiragino Sans GB", "Arial Unicode MS", "DejaVu Sans"]
INK = "#26333D"
BLUE = "#527A9B"
BLUE_LIGHT = "#B8CAD8"
BLUE_PALE = "#EAF0F4"
PINK = "#B8797D"
TAN = "#B38B67"
GRAY = "#7B858B"
GRID = "#D7DEE2"
WHITE = "#FFFFFF"

plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": FONT,
        "axes.unicode_minus": False,
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "figure.facecolor": WHITE,
        "savefig.facecolor": WHITE,
    }
)


ORDER = [
    "target_event_triggered",
    "target_event_not_triggered",
    "stable_triggered",
    "stable_not_triggered",
]
SHORT = ["事件×触发", "事件×未触发", "非事件×触发", "非事件×未触发"]


def load_rows() -> list[dict[str, float | int | str]]:
    with SUMMARY.open(newline="", encoding="utf-8") as f:
        rows = {row["cell"]: row for row in csv.DictReader(f)}
    if set(rows) != set(ORDER):
        raise ValueError(f"四格数据行不完整：{sorted(rows)}")
    result = []
    for key in ORDER:
        row = rows[key]
        result.append(
            {
                "cell": key,
                "n": int(row["n"]),
                "sample": float(row["sample_percent"]),
                "mae": float(row["mae_mean"]),
                "sd": float(row["mae_sd"]),
                "contrib": float(row["contribution_percent_mean"]),
            }
        )
    if sum(int(r["n"]) for r in result) != 712360:
        raise ValueError("四格总预测键不是 712,360")
    if not np.isclose(sum(float(r["contrib"]) for r in result), 100.0, atol=1e-8):
        raise ValueError("四格误差贡献未归一到 100%")
    return result


def style_axis(ax):
    ax.tick_params(axis="both", which="both", length=0, colors=INK, labelsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(GRID)
    ax.spines["bottom"].set_color(GRID)
    ax.grid(axis="x", color=GRID, linewidth=0.55, alpha=0.8)
    ax.set_axisbelow(True)


def panel_label(ax, label, title):
    ax.text(0.0, 1.08, f"({label}) {title}", transform=ax.transAxes,
            ha="left", va="bottom", fontsize=9.2, fontweight="bold", color=INK)


def main():
    data = load_rows()
    maes = np.array([float(r["mae"]) for r in data]).reshape(2, 2)
    colors = [PINK, TAN, BLUE_LIGHT, GRAY]
    cmap = LinearSegmentedColormap.from_list("muted_mae", ["#F4F7F8", "#C6D7E3", "#6F97B5"])

    fig = plt.figure(figsize=(10.8, 5.15), constrained_layout=False)
    gs = fig.add_gridspec(1, 3, width_ratios=[1.2, 0.92, 1.06],
                          left=0.065, right=0.985, bottom=0.20, top=0.84, wspace=0.38)

    # (a) A compact 2×2 result matrix. Text in each cell reports the exact
    # three-seed mean, sample SD and count; contribution is shown in panel (c).
    ax = fig.add_subplot(gs[0, 0])
    ax.imshow(maes, cmap=cmap, vmin=0.0, vmax=0.30, interpolation="nearest", aspect="equal")
    for i in range(2):
        for j in range(2):
            r = data[i * 2 + j]
            value = float(r["mae"])
            text_color = WHITE if value >= 0.15 else INK
            ax.text(j, i - 0.08, f"{value:.4f} ± {float(r['sd']):.4f}",
                    ha="center", va="center", fontsize=9.2, fontweight="bold", color=text_color)
            ax.text(j, i + 0.22, f"n = {int(r['n']):,}",
                    ha="center", va="center", fontsize=7.4, color=text_color)
    ax.set_xticks([0, 1], ["规则触发", "规则未触发"], fontsize=8.2)
    ax.set_yticks([0, 1], ["标签事件", "标签非事件"], fontsize=8.2)
    ax.tick_params(axis="both", which="both", length=0, pad=6)
    ax.set_xlim(-0.5, 1.5)
    ax.set_ylim(1.5, -0.5)
    ax.set_xticks(np.arange(-0.5, 2, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, 2, 1), minor=True)
    ax.grid(which="minor", color=WHITE, linewidth=2.0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    panel_label(ax, "a", "四格 MAE（kWh/15 min）")

    # (b) Sample composition. The data labels keep the rare cells visible
    # even at a linear percentage scale.
    ax = fig.add_subplot(gs[0, 1])
    sample = np.array([float(r["sample"]) for r in data])
    y = np.arange(4)
    ax.barh(y, sample, color=colors, height=0.54, edgecolor="none")
    for yi, value in zip(y, sample):
        label = "<0.1%" if value < 0.05 else f"{value:.1f}%"
        ax.text(max(value, 1.0) + 1.4, yi, label, va="center", ha="left",
                fontsize=7.2, color=INK)
    ax.set_yticks(y, SHORT, fontsize=7.7)
    ax.invert_yaxis()
    ax.set_xlim(0, 108)
    ax.set_xlabel("样本占比（%）", fontsize=8.0, labelpad=5)
    style_axis(ax)
    panel_label(ax, "b", "测试键组成")

    # (c) Absolute error contribution uses the same ordering and colors as
    # the matrix, making the rare-but-large error cell immediately visible.
    ax = fig.add_subplot(gs[0, 2])
    contrib = np.array([float(r["contrib"]) for r in data])
    ax.barh(y, contrib, color=colors, height=0.54, edgecolor="none")
    for yi, value in zip(y, contrib):
        ax.text(value + 1.4, yi, f"{value:.1f}%", va="center", ha="left",
                fontsize=7.2, color=INK, fontweight="bold")
    ax.set_yticks(y, SHORT, fontsize=7.7)
    ax.invert_yaxis()
    ax.set_xlim(0, 82)
    ax.set_xlabel("绝对误差贡献（%）", fontsize=8.0, labelpad=5)
    style_axis(ax)
    panel_label(ax, "c", "n×MAE 误差贡献")

    fig.text(0.065, 0.082,
             "原正式 MRG-GCN · StaticGraph 三种子均值±样本标准差 · 贡献按 n×MAE 归一化",
             ha="left", va="center", fontsize=7.6, color=GRAY)
    fig.text(0.985, 0.082, "总预测键 n = 712,360", ha="right", va="center",
             fontsize=7.6, color=GRAY)

    FIG_DIR.mkdir(parents=True, exist_ok=True)
    base = FIG_DIR / "fig4_4_four_cell"
    svg_path = base.with_suffix(".svg")
    fig.savefig(svg_path, format="svg", dpi=1200,
                bbox_inches="tight", pad_inches=0.04)
    fig.savefig(base.with_suffix(".png"), format="png", dpi=1200,
                bbox_inches="tight", pad_inches=0.04)
    # Matplotlib writes multiline path data with trailing spaces. Strip them
    # so the editable SVG also passes repository whitespace checks.
    svg_path.write_text(
        "\n".join(line.rstrip() for line in svg_path.read_text(encoding="utf-8").splitlines()) + "\n",
        encoding="utf-8",
    )
    plt.close(fig)
    print("redrawn: fig4_4_four_cell (result-style matrix + composition + contribution)")


if __name__ == "__main__":
    main()
