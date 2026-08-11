#!/usr/bin/env python3
"""图5-1：TE候选与PCMCI+条件独立核验的圆形关系图（16:9）。

该图只解释两个统计步骤如何衔接；候选数量、参数和验证结果由正文、
表5-1及图5-2至图5-5承担，避免用流程图重复结果信息。
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Circle

sys.path.insert(0, str(Path.home() / ".claude/skills/scipilot-figure-skill/scripts"))
try:
    from export_figure import export_figure, setup_style
except ImportError:
    from _skill_compat import export_figure, setup_style

FIG_DIR = Path("outputs/figures")
FIG_DIR.mkdir(parents=True, exist_ok=True)
setup_style(journal="general", lang="zh")

BLUE, BLUE_L = "#2C5F8A", "#E8F0F5"
ORANGE, ORANGE_L = "#B97950", "#F4E9DF"
GREEN, GREEN_L = "#647A70", "#E9EFEC"
GRAY_D, GRAY_M, GRAY_L = "#404040", "#808080", "#CBD2D6"


def node(ax, x, y, r, text, fc, ec, fontsize=10.0, lw=1.6):
    ax.add_patch(Circle((x, y), r, fc=fc, ec=ec, lw=lw, zorder=3))
    ax.text(x, y, text, ha="center", va="center", fontsize=fontsize,
            color=GRAY_D, zorder=4, linespacing=1.18)


def arrow(ax, start, end, color=BLUE, style="-", rad=0.0, lw=1.35):
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>",
                                 connectionstyle=f"arc3,rad={rad}",
                                 mutation_scale=12, lw=lw, linestyle=style,
                                 color=color, zorder=2))


def main() -> None:
    fig, ax = plt.subplots(figsize=(10.8, 5.6))
    ax.set(xlim=(0, 100), ylim=(0, 52))
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")
    # 主路径只保留候选、核验和确认三个圆形节点；分支给出未确认和补充边。
    node(ax, 17, 26, 10.4, "TE候选\n76", BLUE_L, BLUE, fontsize=10.4, lw=1.8)
    node(ax, 48, 26, 8.8, "PCMCI+\n核验", "white", GRAY_M, fontsize=9.4, lw=1.5)
    node(ax, 79, 26, 10.4, "确认\n44 / 76", GREEN_L, GREEN, fontsize=10.2, lw=1.8)
    arrow(ax, (27.8, 26), (38.6, 26), color=BLUE)
    arrow(ax, (57.2, 26), (68.2, 26), color=GREEN)

    # PCMCI+核验的两个去向与额外发现以小圆卫星表示，避免矩形流程框。
    node(ax, 49, 7.5, 5.6, "未确认\n32 / 76", "#F4F5F6", GRAY_M,
         fontsize=7.3, lw=1.20)
    node(ax, 50, 45.0, 5.6, "补充边\n16", ORANGE_L, ORANGE,
         fontsize=7.5, lw=1.20)
    arrow(ax, (47.0, 17.0), (48.2, 13.3), color=GRAY_M, style="--", rad=0.05, lw=1.05)
    arrow(ax, (48.5, 35.2), (49.4, 39.0), color=ORANGE, style=":", rad=-0.05, lw=1.15)

    ax.text(33.2, 29.4, "方向性候选", ha="center", va="bottom",
            fontsize=7.8, color=GRAY_M)
    ax.text(63.0, 29.4, "条件独立核验", ha="center", va="bottom",
            fontsize=7.8, color=GRAY_M)
    ax.text(79, 14.2, "条件滞后依赖结构", ha="center", va="top",
            fontsize=8.0, color=GREEN)
    export_figure(fig, basename=str(FIG_DIR / "fig5_1_te_pcmci_flow"),
                  formats=["svg", "png"], dpi=1200, size_inches=(10.8, 5.6),
                  grayscale_preview=False)
    plt.close(fig)


if __name__ == "__main__":
    main()
