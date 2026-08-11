"""历史图批次 17：简化多关系门控传播单元（已退出正式配图入口）。

严格对应 ``MultiRelationGatedGCN.forward``：三类固定关系独立传播，
经 Softmax 关系权重融合；节点门控同时接收自身表示 H 与关系消息 M，
完成邻居消息/自身信息混合，最后执行 Dropout、残差和 LayerNorm。
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

sys.path.insert(0, str(Path.home() / ".claude/skills/scipilot-figure-skill/scripts"))
try:
    from export_figure import export_figure  # noqa: E402
    from setup_style import setup_style  # noqa: E402
except ImportError:  # 无 skill 环境回退
    from _skill_compat import export_figure, setup_style  # noqa: E402

FIG_DIR = Path("outputs/figures")
FIG_DIR.mkdir(parents=True, exist_ok=True)
setup_style(journal="general", lang="zh")

# 色盲安全低饱和色板（与批次 16 一致）
BLUE = "#2C5F8A"      # 深蓝（固定关系 / β 门控）
ORANGE = "#B9935A"    # 浅棕金（关系融合）
GREEN = "#647A70"     # 灰绿（节点门控 / 输出）
GRAY_D = "#404040"
GRAY_M = "#808080"
GRAY_L = "#C8C8C8"
BG = "#F5F2EC"        # 米白卡片底


def final(fig, name: str, size: tuple[float, float]) -> None:
    """统一导出：SVG 矢量 + PNG 1200 DPI（论文硬性约束）。"""
    export_figure(
        fig, basename=str(FIG_DIR / name),
        formats=["svg", "png"], dpi=1200, size_inches=size,
        grayscale_preview=False,
    )
    print("  ✅ {}".format(name))


def _card(ax, x, y, w, h, text, *, fc=BG, ec=GRAY_M, fs=8.5, weight="normal",
          lw=1.2, radius=0.02, text_color=GRAY_D):
    """圆角卡片（与批次 16 相同 helper）。"""
    box = FancyBboxPatch(
        (x, y), w, h, boxstyle=f"round,pad=0.006,rounding_size={radius}",
        fc=fc, ec=ec, lw=lw, zorder=3,
    )
    ax.add_patch(box)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=fs, color=text_color, fontweight=weight, zorder=4)


def _arrow(ax, x1, y1, x2, y2, *, color=GRAY_M, lw=1.4, style="-|>",
           ls="-", ms=11, zorder=2, shrink=0.0):
    """流程箭头（与批次 16 相同 helper）。"""
    ax.add_patch(FancyArrowPatch(
        (x1, y1), (x2, y2), arrowstyle=style, mutation_scale=ms,
        color=color, lw=lw, linestyle=ls, shrinkA=shrink, shrinkB=shrink,
        zorder=zorder,
    ))


def fig3_2_relation_propagation_unit() -> None:
    """三关系消息 → β 融合 → 节点门控 → 残差归一化。"""
    fig, ax = plt.subplots(figsize=(10.4, 6.0))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 72)
    ax.axis("off")

    # 输入主干
    _card(ax, 3, 31, 10, 10, "$H$\n$[B,N,D]$", fc="#EEF3F7", ec=BLUE,
          lw=1.3, fs=9, weight="bold")

    # 三类固定关系平行传播；三行以标签和线型区分，不虚构权重值。
    rels = [
        ("负荷关系", r"$\hat A_{load}HW_{load}$", "-"),
        ("行为关系", r"$\hat A_{event}HW_{event}$", "--"),
        ("轮廓关系", r"$\hat A_{pattern}HW_{pattern}$", ":"),
    ]
    ys = [57, 36, 15]
    for (label, formula, ls), y in zip(rels, ys):
        _card(ax, 20, y - 4, 15, 8, label, fc="#F4F7F9", ec=BLUE,
              lw=1.1, fs=8.3)
        _card(ax, 42, y - 4, 17, 8, formula, fc="white", ec=GRAY_M,
              lw=1.0, fs=8.5)
        _arrow(ax, 13.5, 36, 19.5, y, color=BLUE, lw=1.15, ms=9,
               ls=ls)
        _arrow(ax, 35.5, y, 41.5, y, color=BLUE, lw=1.15, ms=9,
               ls=ls)

    # 关系级融合
    _card(ax, 64, 27, 13, 18,
          r"$\beta=\mathrm{softmax}(w)$" "\n" r"$M=\sum_r\beta_rM_r$",
          fc="#F6F0E5", ec=ORANGE, lw=1.3, fs=8.5)
    for y in ys:
        _arrow(ax, 59.5, y, 63.5, 36, color=ORANGE, lw=1.15, ms=9)

    # 节点级门控：明确 H 与 M 都进入 gate，并显示两条混合支路。
    _card(ax, 82, 46, 14, 9, r"$G=\sigma(W_g[H\Vert M])$",
          fc="#EEF3F1", ec=GREEN, lw=1.3, fs=8.3)
    _arrow(ax, 77.5, 36, 82, 50.5, color=GREEN, lw=1.2, ms=9)
    # 用同名端口复用 H，避免长旁路线穿越主体；公式明确门控接收 H 与 M。
    ax.text(80.0, 54.0, "$H$", ha="center", va="center", fontsize=8.5,
            color=GRAY_M)
    _arrow(ax, 80.8, 53.0, 82.0, 51.5, color=GRAY_M, lw=0.9, ms=8,
           ls="--")
    _card(ax, 82, 30, 14, 9,
          r"$\tilde H=G\odot M$" "\n" r"$+(1-G)\odot H$",
          fc="#EEF3F1", ec=GREEN, lw=1.3, fs=8.1)
    _arrow(ax, 89, 45.5, 89, 39.5, color=GREEN, lw=1.2, ms=9)

    # 残差与输出；旁路从 H 直达加法节点。
    _card(ax, 84, 21, 10, 5, "Dropout", fc="#F4F7F6",
          ec=GREEN, lw=1.1, fs=7.8)
    _arrow(ax, 89, 29.5, 89, 26.5, color=GREEN, lw=1.2, ms=9)
    ax.scatter([89], [16], s=300, facecolor="white", edgecolor=GREEN,
               linewidth=1.2, zorder=4)
    ax.text(89, 16, "+", ha="center", va="center", fontsize=13,
            color=GREEN, zorder=5)
    _arrow(ax, 89, 20.5, 89, 18.2, color=GREEN, lw=1.2, ms=9)
    # 外层残差同样使用 H 端口，终点明确指向加法节点。
    ax.text(80.0, 16, "$H$", ha="center", va="center", fontsize=8.5,
            color=GRAY_M)
    _arrow(ax, 81.0, 16, 86.8, 16, color=GRAY_M, lw=0.9, ms=8,
           ls="--")
    _card(ax, 84, 7, 10, 5, "LayerNorm", fc="#F4F7F6",
          ec=GREEN, lw=1.1, fs=7.8)
    _arrow(ax, 89, 13.8, 89, 12.5, color=GREEN, lw=1.2, ms=9)
    ax.text(89, 2, r"$H_{out}\in\mathbb{R}^{B\times N\times D}$",
            ha="center", va="center", fontsize=9, color=GRAY_D)
    _arrow(ax, 89, 6.5, 89, 3.5, color=GREEN, lw=1.2, ms=9)

    ax.text(70.5, 47.5, "关系级融合", ha="center", fontsize=7.2,
            color=ORANGE)
    ax.text(89, 57.5, "节点门控", ha="center", fontsize=7.2,
            color=GREEN)

    fig.tight_layout()
    final(fig, "legacy_fig3_2_relation_propagation_unit", (10.4, 6.0))
    plt.close(fig)


if __name__ == "__main__":
    raise RuntimeError(
        "该脚本生成的是已废弃的简化图3-2；正式图3-2为复杂多关系传播单元，"
        "不得用本脚本覆盖。"
    )
