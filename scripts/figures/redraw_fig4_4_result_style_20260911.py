#!/usr/bin/env python3
"""重绘图4-4：用结果图风格呈现三种子四格诊断及误差贡献。

画布尺寸按论文实际显示宽度设定，使图内字号即为纸面字号。
"""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap


ROOT = Path(__file__).resolve().parents[2]
FIG_DIR = ROOT / "outputs" / "figures"
SUMMARY = ROOT / "outputs" / "analysis" / "SG-EXP-020-legacy-evidence-v1" / "four_cell_summary.csv"

FONT = ["Songti SC", "STSong", "PingFang SC", "Hiragino Sans GB", "Arial Unicode MS", "DejaVu Sans"]
INK = "#26333D"
BLUE_LIGHT = "#B8CAD8"
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

# 画布宽度取值：论文 A4 版心 14.66 cm = 5.77 in（左右页边距 3.17 cm），
# 图按 5.59 in 宽排版，故 figsize 取与之匹配的值，使 fontsize 即为纸面 pt。
FIG_W_IN = 5.69
FIG_H_IN = 2.90
FIG_H_PAD_IN = 0.02

# 字号均按论文显示尺寸取值（图内文字 6.6–8.8 pt，小于 9 pt 图注）。
FS_PANEL = 8.0
FS_TICK = 7.0
FS_VALUE = 6.8
FS_AXLABEL = 7.4
FS_NOTE = 6.6


ORDER = [
    "target_event_triggered",
    "target_event_not_triggered",
    "stable_triggered",
    "stable_not_triggered",
]
# 行标签折为两行：水平方向受宽度限制，垂直方向每行尚有余量。
SHORT = ["事件\n×触发", "事件\n×未触发", "非事件\n×触发", "非事件\n×未触发"]


def load_rows() -> list[dict[str, float | int]]:
    """读取四格汇总表，按固定顺序返回并校验两条恒等式。

    输入：SUMMARY 指向的 CSV（列 cell/n/sample_percent/mae_mean/mae_sd/
    contribution_percent_mean）。
    输出：长度 4 的记录列表，顺序与 ORDER 一致。
    边界：四格不齐全、总预测键不等于 712,360，或误差贡献未归一到 100% 时抛错，
    不静默补齐。
    """
    with SUMMARY.open(newline="", encoding="utf-8") as f:
        rows = {row["cell"]: row for row in csv.DictReader(f)}
    if set(rows) != set(ORDER):
        raise ValueError(f"四格数据行不完整：{sorted(rows)}")
    result: list[dict[str, float | int]] = []
    for key in ORDER:
        row = rows[key]
        result.append(
            {
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


def style_axis(ax) -> None:
    """统一条形图坐标轴样式：隐藏上/右边框、仅保留横向浅色网格。"""
    ax.tick_params(axis="both", which="both", length=0, colors=INK, labelsize=FS_TICK)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(GRID)
    ax.spines["bottom"].set_color(GRID)
    ax.grid(axis="x", color=GRID, linewidth=0.5, alpha=0.8)
    ax.set_axisbelow(True)


def main() -> None:
    data = load_rows()
    maes = np.array([float(r["mae"]) for r in data]).reshape(2, 2)
    colors = [PINK, TAN, BLUE_LIGHT, GRAY]
    cmap = LinearSegmentedColormap.from_list("muted_mae", ["#F4F7F8", "#C6D7E3", "#6F97B5"])

    fig = plt.figure(figsize=(FIG_W_IN, FIG_H_IN))
    # 用 add_axes 而非 gridspec：y 轴标签位于 axes 之外，需为其显式预留宽度，
    # 否则缩放后标签会侵入相邻面板。
    box_bottom, box_height = 0.225, 0.575
    ax_a_box = [0.055, box_bottom, 0.240, box_height]
    ax_b_box = [0.400, box_bottom, 0.240, box_height]
    ax_c_box = [0.748, box_bottom, 0.222, box_height]

    # ========== 面板 a：四格 MAE 矩阵 ==========
    # 每格三行（值 / ±SD / n）分行排布，避免格宽不足导致文字截断。
    ax = fig.add_axes(ax_a_box)
    ax.imshow(maes, cmap=cmap, vmin=0.0, vmax=0.30, interpolation="nearest", aspect="auto")
    for i in range(2):
        for j in range(2):
            record = data[i * 2 + j]
            value = float(record["mae"])
            text_color = WHITE if value >= 0.15 else INK
            ax.text(j, i - 0.16, f"{value:.4f}", ha="center", va="center",
                    fontsize=8.8, fontweight="bold", color=text_color)
            ax.text(j, i + 0.08, f"±{float(record['sd']):.4f}", ha="center", va="center",
                    fontsize=FS_VALUE - 0.2, color=text_color)
            ax.text(j, i + 0.28, f"n={int(record['n']):,}", ha="center", va="center",
                    fontsize=FS_VALUE - 0.2, color=text_color)
    ax.set_xticks([0, 1], ["规则触发", "规则未触发"], fontsize=FS_TICK)
    ax.set_yticks([0, 1], ["事件", "非事件"], fontsize=FS_TICK)
    ax.tick_params(axis="x", which="both", length=0, pad=9)
    ax.tick_params(axis="y", which="both", length=0, pad=4)
    ax.set_xlim(-0.5, 1.5)
    ax.set_ylim(1.5, -0.5)
    ax.set_xticks(np.arange(-0.5, 2, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, 2, 1), minor=True)
    ax.grid(which="minor", color=WHITE, linewidth=1.6)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.text(0.0, 1.055, "(a) 四格 MAE（kWh/15 min）", transform=ax.transAxes,
            ha="left", va="bottom", fontsize=FS_PANEL, fontweight="bold", color=INK)

    # ========== 面板 b/c：样本组成与误差贡献 ==========
    y = np.arange(4)

    def bars(box, values, xlabel, title, x_max):
        """绘制四行横向条形图；边框为浅色长条提供灰度下的可辨边界。"""
        ax_ = fig.add_axes(box)
        ax_.barh(y, values, color=colors, height=0.60, edgecolor=INK, linewidth=0.35)
        for yi, value in zip(y, values):
            label = "<0.1%" if value < 0.05 else f"{value:.1f}%"
            ax_.text(max(value, x_max * 0.012) + x_max * 0.02, yi, label,
                     va="center", ha="left", fontsize=FS_VALUE, color=INK, fontweight="bold")
        ax_.set_yticks(y, SHORT, fontsize=FS_TICK)
        ax_.invert_yaxis()
        ax_.set_xlim(0, x_max)
        ax_.set_xlabel(xlabel, fontsize=FS_AXLABEL, labelpad=4)
        style_axis(ax_)
        ax_.text(0.0, 1.055, title, transform=ax_.transAxes, ha="left", va="bottom",
                 fontsize=FS_PANEL, fontweight="bold", color=INK)
        return ax_

    bars(ax_b_box, np.array([float(r["sample"]) for r in data]),
         "样本占比（%）", "(b) 测试键组成", 108)
    bars(ax_c_box, np.array([float(r["contrib"]) for r in data]),
         "绝对误差贡献（%）", "(c) n×MAE 误差贡献", 88)

    # 底部注记保留 MRG-GCN 与 StaticGraph 的别名对应关系，避免读者误认作两个模型。
    fig.text(0.055, 0.072,
             "MRG-GCN（StaticGraph）· 三种子均值±样本标准差；贡献按 n×MAE 归一化",
             ha="left", va="center", fontsize=FS_NOTE, color=GRAY)
    fig.text(0.970, 0.072, "总预测键 n = 712,360", ha="right", va="center",
             fontsize=FS_NOTE, color=GRAY)

    FIG_DIR.mkdir(parents=True, exist_ok=True)
    base = FIG_DIR / "fig4_5_four_cell"
    svg_path = base.with_suffix(".svg")
    fig.savefig(svg_path, format="svg", dpi=1200,
                bbox_inches="tight", pad_inches=FIG_H_PAD_IN)
    fig.savefig(base.with_suffix(".png"), format="png", dpi=1200,
                bbox_inches="tight", pad_inches=FIG_H_PAD_IN)
    # Matplotlib writes multiline path data with trailing spaces. Strip them
    # so the editable SVG also passes repository whitespace checks.
    svg_path.write_text(
        "\n".join(line.rstrip() for line in svg_path.read_text(encoding="utf-8").splitlines()) + "\n",
        encoding="utf-8",
    )
    plt.close(fig)
    print("redrawn: fig4_5_four_cell (paper-size canvas, matrix + composition + contribution)")


if __name__ == "__main__":
    main()
