"""论文图批次 17：图 3-2 门控融合层架构示意图。

MRG-GCN 双层门控融合层（3.5.3-3.5.4 节）的机制示意：
- 四类关系独立消息计算（load/event/pattern/adaptive，逐关系 W_r）
- 关系级 β 门控（softmax，logit 初始化 0 → β₀=1/3）
- 节点级 G 门控（sigmoid，逐节点自适应保留）
- 残差 + LayerNorm 输出

布局（横版）：左=输入与四关系、中=β 门控融合（权重条可视化）、
右=G 门控与输出；底部标注训练期关系 dropout 与两层独立 β 口径。
统一规范：无标题、无章节号/实验代号、SVG+PNG 1200 DPI、
色盲安全配色 + 冗余编码。
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
ORANGE = "#D08A3C"    # 低饱和橙（自适应关系）
GREEN = "#4C7A5C"     # 低饱和绿（G 门控 / 输出）
RED_S = "#B05A4A"     # 低饱和红（约束 / 训练期）
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


def fig3_2_gate_fusion() -> None:
    """门控融合层示意图：四关系消息 → β 门控 → G 门控 → 输出。"""
    fig, ax = plt.subplots(figsize=(13.4, 7.6))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    # ---------- 左：输入与四类关系 ----------
    ax.text(8, 92, "输入表征", ha="center", fontsize=9.5, fontweight="bold",
            color=GRAY_D)
    _card(ax, 3, 84, 10, 5, "H\n[B,N,D]", fc=BG, ec=GRAY_D, lw=1.4, fs=8)
    _arrow(ax, 13.5, 86.5, 18.5, 86.5, color=GRAY_D, lw=1.5, ms=11)

    rels = [
        ("load", "负荷耦合\n绝对 Pearson 相关", BLUE, "固定"),
        ("event", "行为共现\n余弦相似度", BLUE, "固定"),
        ("pattern", "轮廓相似\n欧氏指数核", BLUE, "固定"),
        ("adaptive", "节点嵌入内积\n（对照）", ORANGE, "学习"),
    ]
    rel_x, rel_w = 19, 17
    for k, (name, desc, color, tag) in enumerate(rels):
        y = 74 - k * 13
        _card(ax, rel_x, y, rel_w, 10.5, f"{name}\n\n{desc}", fc=BG,
              ec=color, lw=1.4, fs=7.5)
        # 关系类型角标（固定/学习）
        _card(ax, rel_x + rel_w - 6.2, y + 7.8, 6.0, 2.2, tag,
              fc=color, ec=color, fs=6.5, text_color="white", radius=0.5)

    # 关系 → 消息 箭头（四条并行）
    for k in range(4):
        y = 74 - k * 13
        _arrow(ax, rel_x + rel_w + 0.6, y + 5.2, rel_x + rel_w + 4.4, y + 5.2,
               color=GRAY_M, lw=1.2, ms=9)

    # ---------- 中：逐关系消息计算 ----------
    msg_x, msg_w = 41, 15
    ax.text(48.5, 92, "逐关系消息计算", ha="center", fontsize=9.5,
            fontweight="bold", color=GRAY_D)
    for k, color in enumerate([BLUE, BLUE, BLUE, ORANGE]):
        y = 74 - k * 13
        _card(ax, msg_x, y, msg_w, 10.5,
              f"M{chr(ord('1') + k)} = Â{chr(ord('1') + k)} H W{chr(ord('1') + k)}",
              fc=BG, ec=color, lw=1.2, fs=7.8)
        if k < 3:
            # 固定关系之间：关系 dropout 标注（训练期）
            ax.text(msg_x + msg_w / 2, y - 1.6, "关系 dropout（训练期）",
                    ha="center", fontsize=5.5, color=GRAY_M)
        else:
            ax.text(msg_x + msg_w / 2, y - 1.6, "节点嵌入，无 top-k",
                    ha="center", fontsize=5.5, color=GRAY_M)

    # 消息 → β 门控 箭头
    for k in range(4):
        y = 74 - k * 13
        _arrow(ax, msg_x + msg_w + 0.6, y + 5.2, msg_x + msg_w + 4.0, y + 5.2,
               color=GRAY_M, lw=1.2, ms=9)

    # ---------- 中右：关系级 β 门控 ----------
    beta_x, beta_w = 61, 17
    ax.text(beta_x + beta_w / 2, 92, "关系级 β 门控（softmax）",
            ha="center", fontsize=9.5, fontweight="bold", color=BLUE)
    _card(ax, beta_x, 60, beta_w, 16,
          "β = softmax(w)\n\nβ₀ = 1/3\n（logit 初始化 0）\n\nM = Σᵣ βᵣ Mᵣ",
          fc=BG, ec=BLUE, lw=1.5, fs=8)
    # 权重条可视化（冗余编码：长度 ∝ 学习后权重示意，非真实值）
    bar_colors = [BLUE, BLUE, BLUE, ORANGE]
    bar_vals = [0.30, 0.22, 0.30, 0.18]
    for k, (bc, bv) in enumerate(zip(bar_colors, bar_vals)):
        y = 60 + k * 3.6 + 0.4
        bar = mpatches.FancyBboxPatch(
            (beta_x + 1.5, y), 14.0 * bv / 0.35, 2.4,
            boxstyle="round,pad=0.004,rounding_size=0.3",
            fc=bc, ec="none", zorder=4,
        )
        ax.add_patch(bar)
    ax.text(beta_x + beta_w / 2, 55.6, "学习后权重示意（两层独立，逐层重估）",
            ha="center", fontsize=5.5, color=GRAY_M)

    # β 输出 → G 门控 箭头
    _arrow(ax, beta_x + beta_w / 2, 59.4, beta_x + beta_w / 2, 50.5,
           color=BLUE, lw=1.6, ms=11)

    # ---------- 右：节点级 G 门控 → 输出 ----------
    g_x, g_w = 79, 17
    ax.text(g_x + g_w / 2, 92, "节点级 G 门控（sigmoid）",
            ha="center", fontsize=9.5, fontweight="bold", color=GREEN)
    _card(ax, g_x, 40, g_w, 14,
          "g = σ(W_g H)\n\nM′ = g ⊙ M\n\n逐节点自适应保留\n（0~1 连续，非开关）",
          fc=BG, ec=GREEN, lw=1.5, fs=7.8)
    _arrow(ax, g_x + g_w / 2, 39.4, g_x + g_w / 2, 32.5, color=GREEN,
           lw=1.6, ms=11)
    _card(ax, g_x, 23, g_w, 9, "残差 + LayerNorm\nH′ = H + LN(M′)",
          fc="#F0F5F0", ec=GREEN, lw=1.3, fs=7.8)
    _arrow(ax, g_x + g_w / 2, 22.4, g_x + g_w / 2, 17.5, color=GREEN,
           lw=1.6, ms=11)
    _card(ax, g_x, 10, g_w, 7, "输出 H′\n[B,N,D]", fc=BG, ec=GRAY_D,
          lw=1.4, fs=8)

    # 输出回注：Skip Fusion 上游
    ax.text(g_x + g_w / 2, 8.0, "H′ 汇入跨层 Skip Fusion（时序/一阶/二阶）",
            ha="center", fontsize=6, color=GRAY_M)

    # 右侧竖注：两层独立 β
    note = mpatches.FancyBboxPatch(
        (3, 4), 94, 8, boxstyle="round,pad=0.008,rounding_size=0.5",
        fc="#FDF3F1", ec=RED_S, lw=1.2, zorder=3,
    )
    ax.add_patch(note)
    ax.text(50, 8,
            "两层 GCN 使用独立关系权重：一阶传播与二阶传播分别选择关系混合；\n"
            "β 与 G 门控语义可解释：βᵣ 接近 1 → 该类关系对节点贡献大，g 接近 0 → 该节点无需邻居信息",
            ha="center", va="center", fontsize=7.5, color=RED_S, zorder=4)

    fig.tight_layout()
    final(fig, "fig3_2_gate_fusion", (13.4, 7.6))
    plt.close(fig)


if __name__ == "__main__":
    print("=== 批次 17：图 3-2 门控融合层架构示意图 ===")
    fig3_2_gate_fusion()
    print("=== 完成 ===")
