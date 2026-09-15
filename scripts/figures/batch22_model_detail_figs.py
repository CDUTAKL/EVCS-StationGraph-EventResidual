"""Two compact, deterministic model-detail figures for Chapter 3.

These are intentionally complementary to the existing architecture figures:
Fig. 3-13 isolates node gating and the residual update, while Fig. 3-14
isolates the representation routes and explicitly keeps the refined state out
of cross-layer concatenation.  Both are generated as editable SVG plus
1200-DPI PNG so the manuscript does not depend on a raster-only illustration.
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Polygon, Rectangle

sys.path.insert(0, str(Path.home() / ".claude/skills/scipilot-figure-skill/scripts"))
try:
    from export_figure import export_figure
    from setup_style import setup_style
except ImportError:
    from _skill_compat import export_figure, setup_style

FIG_DIR = Path("outputs/figures")
FIG_DIR.mkdir(parents=True, exist_ok=True)
setup_style(journal="general", lang="zh")

BLUE = "#2C5F8A"
BLUE_L = "#EAF1F6"
BLUE_M = "#C9DAE7"
ROSE = "#B97973"
ROSE_L = "#F5E9E7"
GOLD = "#B9935A"
GOLD_L = "#F4EDDE"
INK = "#263238"
GRAY = "#6E7B82"
LIGHT = "#D8DEE2"
WHITE = "#FFFFFF"


def export(fig, name: str, size: tuple[float, float]) -> None:
    export_figure(fig, basename=str(FIG_DIR / name), formats=["svg", "png"],
                  dpi=1200, size_inches=size, grayscale_preview=False)
    plt.close(fig)


def card(ax, x, y, w, h, text, *, fc=WHITE, ec=BLUE, fs=9.2, lw=1.2,
         radius=0.025, color=INK, weight="normal"):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h, boxstyle=f"round,pad=0.008,rounding_size={radius}",
        facecolor=fc, edgecolor=ec, linewidth=lw, zorder=3,
    ))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=fs, color=color, fontweight=weight, zorder=4,
            linespacing=1.15)


def arrow(ax, x1, y1, x2, y2, *, color=BLUE, lw=1.45, ls="-", ms=10,
          rad=0.0):
    ax.add_patch(FancyArrowPatch(
        (x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=ms,
        connectionstyle=f"arc3,rad={rad}", color=color, linewidth=lw,
        linestyle=ls, shrinkA=1, shrinkB=1, zorder=2,
    ))


def tensor(ax, x, y, w, h, *, depth=3.0, fc=BLUE_L, ec=BLUE, label=None,
           label_fs=9.0):
    """Small flat 3-D feature block; no shading or gradient."""
    dx, dy = depth * 0.65, depth * 0.45
    front = Rectangle((x, y), w, h, facecolor=fc, edgecolor=ec,
                      linewidth=1.05, zorder=3)
    top = Polygon([(x, y + h), (x + dx, y + h + dy),
                   (x + w + dx, y + h + dy), (x + w, y + h)],
                  closed=True, facecolor=fc, edgecolor=ec, linewidth=1.05,
                  zorder=3)
    side = Polygon([(x + w, y), (x + w + dx, y + dy),
                    (x + w + dx, y + h + dy), (x + w, y + h)],
                   closed=True, facecolor=fc, edgecolor=ec, linewidth=1.05,
                   zorder=3)
    ax.add_patch(front); ax.add_patch(top); ax.add_patch(side)
    # A few grid lines communicate tensor axes without turning the block into
    # a dense decorative mesh.
    for frac in (0.33, 0.66):
        ax.plot([x + w * frac, x + w * frac], [y, y + h], color=ec,
                linewidth=0.55, alpha=0.72, zorder=4)
    if label:
        ax.text(x + w / 2 + dx * 0.1, y - 2.1, label, ha="center",
                va="top", fontsize=label_fs, color=INK, zorder=5)


def fig3_6_gate_residual_detail() -> None:
    fig, ax = plt.subplots(figsize=(8.8, 4.5))
    ax.set(xlim=(0, 100), ylim=(0, 56))
    ax.axis("off")

    ax.text(2.5, 52.5, "节点级门控与残差更新", fontsize=12, fontweight="bold",
            color=INK, ha="left", va="center")
    ax.text(2.5, 48.5, "关系消息先融合，再由节点门值控制保留比例", fontsize=8.6,
            color=GRAY, ha="left", va="center")

    tensor(ax, 4, 22, 10, 12, fc=BLUE_L, label=r"$Z^{(l)}$")
    tensor(ax, 4, 39, 10, 9, fc=GOLD_L, ec=GOLD, label=r"$M^{(l)}$")

    card(ax, 21, 28, 18, 12, "节点门控\n$G^{(l)}=σ([Z∥M]W_g+b_g)$",
         fc=BLUE_L, ec=BLUE, fs=9.0)
    arrow(ax, 14.5, 28, 20.5, 33.5, color=BLUE)
    arrow(ax, 14.5, 43, 20.5, 36.5, color=GOLD)

    card(ax, 45, 28, 18, 12, "门控混合\n$G⊙M+(1−G)⊙Z$",
         fc=ROSE_L, ec=ROSE, fs=9.2)
    arrow(ax, 39.5, 34, 44.5, 34, color=ROSE)

    card(ax, 69, 28, 13, 12, "残差更新\n$Z+Dropout(·)$",
         fc=GOLD_L, ec=GOLD, fs=9.0)
    arrow(ax, 63.5, 34, 68.5, 34, color=GOLD)

    card(ax, 87, 28, 9, 12, "LayerNorm\n$H^{(l)}$",
         fc=BLUE_L, ec=BLUE, fs=9.5)
    arrow(ax, 82.5, 34, 86.5, 34, color=BLUE)

    # Residual identity is shown as a thin lower route that joins the update
    # block; it is not connected to the relation-message branch by accident.
    ax.plot([14.5, 17, 17, 68.5], [26, 26, 18, 18], color=GRAY,
            linewidth=1.0, linestyle="--", zorder=1)
    arrow(ax, 68.5, 18, 72.0, 28, color=GRAY, lw=1.0, ls="--", ms=9)
    ax.text(25, 14.2, "身份路径：$Z^{(l)}$ 直接保留到残差更新", fontsize=9.4,
            color=GRAY, ha="left", va="center")
    ax.text(4, 7.5, "关系级 β：决定融合哪些关系", fontsize=9.0, color=BLUE,
            ha="left")
    ax.text(49, 7.5, "节点级 G：决定当前节点保留多少消息", fontsize=9.0,
            color=ROSE, ha="left")

    export(fig, "fig3_6_gate_residual_detail", (8.8, 4.5))


def fig3_7_cross_layer_detail() -> None:
    fig, ax = plt.subplots(figsize=(8.8, 4.6))
    ax.set(xlim=(0, 100), ylim=(0, 58))
    ax.axis("off")

    ax.text(2.5, 54.5, "跨层表示路径", fontsize=12, fontweight="bold",
            color=INK, ha="left", va="center")
    ax.text(2.5, 50.5, "精炼表示只承担第二层输入；跨层拼接保留原始层级状态",
            fontsize=8.6, color=GRAY, ha="left", va="center")

    tensor(ax, 4, 35, 9, 9, fc=BLUE_L, label=r"$H^{(0)}$", label_fs=8.8)
    card(ax, 19, 34, 17, 11, "第一层\n关系传播", fc=BLUE_L, ec=BLUE, fs=9.0)
    tensor(ax, 42, 35, 9, 9, fc=BLUE_M, label=r"$H^{(1)}$", label_fs=9.0)
    card(ax, 57, 34, 17, 11, "残差 MLP\n精炼", fc=ROSE_L, ec=ROSE, fs=9.0)
    tensor(ax, 80, 35, 10, 9, fc=ROSE_L, ec=ROSE,
           label=r"$H^{(1,ref)}$", label_fs=9.5)
    arrow(ax, 13.5, 39.5, 18.5, 39.5)
    arrow(ax, 36.5, 39.5, 41.5, 39.5)
    arrow(ax, 51.5, 39.5, 56.5, 39.5, color=ROSE)
    arrow(ax, 74.5, 39.5, 79.5, 39.5, color=ROSE)

    # The second layer is a separate lower route.  Its only incoming state is
    # H^(1,ref), making the intended topology visually explicit.
    card(ax, 63, 16, 20, 10, "第二层\n关系传播", fc=BLUE_L, ec=BLUE, fs=9.0)
    tensor(ax, 88, 16, 9, 9, fc=GOLD_L, ec=GOLD,
           label=r"$H^{(2)}$", label_fs=8.8)
    # H^(1,ref) enters the second-layer propagation card first; it must not
    # point directly to H^(2).
    ax.plot([85, 85, 73], [34, 29, 29], color=ROSE, linewidth=1.25,
            zorder=1)
    arrow(ax, 73, 29, 73, 26.5, color=ROSE, lw=1.2)
    arrow(ax, 83.5, 21, 87.5, 21, color=GOLD)
    ax.text(90.5, 31, "仅作\n第二层输入", ha="left", va="center", fontsize=9.0,
            color=ROSE)

    # Cross-layer concatenation uses H0, H1 and H2; the three orthogonal paths
    # meet above the final fusion card without crossing the refined branch.
    card(ax, 36, 3, 28, 8, "跨层拼接\n$[H^{(0)}∥H^{(1)}∥H^{(2)}]$",
         fc=GOLD_L, ec=GOLD, fs=9.0)
    # Route the H^(1) branch around the second-layer card; a line crossing that
    # card would falsely suggest that the concatenation path feeds propagation.
    ax.plot([8.5, 8.5, 50], [35, 12, 12], color=BLUE, linewidth=1.0,
            linestyle="-", zorder=1)
    ax.plot([46.5, 36, 36, 50], [35, 35, 12, 12], color=BLUE,
            linewidth=1.0, linestyle="-", zorder=1)
    ax.plot([92.5, 92.5, 50], [16, 12, 12], color=BLUE, linewidth=1.0,
            linestyle="-", zorder=1)
    arrow(ax, 50, 12, 50, 11, color=GOLD, lw=1.1, ms=9)
    ax.text(67, 7, "$H^{(1,ref)}$不进入跨层拼接", ha="left", va="center",
            fontsize=9.0, color=ROSE)

    export(fig, "fig3_7_cross_layer_detail", (8.8, 4.6))


if __name__ == "__main__":
    fig3_6_gate_residual_detail()
    fig3_7_cross_layer_detail()
    print("generated fig3_6_gate_residual_detail and fig3_7_cross_layer_detail")
