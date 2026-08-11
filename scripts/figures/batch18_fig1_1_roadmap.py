"""论文图批次 18：图 1-2 总体技术路线图（第 1 章，四阶段）。

按第 1 章 1.5 节四阶段组织：数据重构与节点筛选 → LRE 关系构建与
MRG-GCN 建模 → MDP 三层机制诊断 → 预测支持探索与结论。
每阶段为一张卡片（阶段名 + 三个子要点），阶段间以箭头串联，
底部标注"数据 → 方法 → 机制 → 结论"的贯通主线。

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

# 色盲安全低饱和色板（与批次 16/17 一致）
BLUE = "#2C5F8A"      # 深蓝（阶段一：数据）
ORANGE = "#D08A3C"    # 低饱和橙（阶段二：方法）
GREEN = "#4C7A5C"     # 低饱和绿（阶段三：机制）
RED_S = "#B05A4A"     # 低饱和红（阶段四：探索）
GRAY_D = "#404040"
GRAY_M = "#808080"
BG = "#F5F2EC"


def final(fig, name: str, size: tuple[float, float]) -> None:
    """统一导出：SVG 矢量 + PNG 1200 DPI（论文硬性约束）。"""
    export_figure(
        fig, basename=str(FIG_DIR / name),
        formats=["svg", "png"], dpi=1200, size_inches=size,
        grayscale_preview=False,
    )
    print("  ✅ {}".format(name))


def _card(ax, x, y, w, h, text, *, fc=BG, ec=GRAY_M, fs=8, weight="normal",
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


def _badge(ax, cx, cy, r, text, *, fc=BLUE, fs=8, tc="white"):
    """编号徽章（与批次 16 相同 helper）。"""
    circle = mpatches.Circle((cx, cy), r, fc=fc, ec="white", lw=1.2, zorder=5)
    ax.add_patch(circle)
    ax.text(cx, cy, text, ha="center", va="center", fontsize=fs,
            color=tc, fontweight="bold", zorder=6)


def fig1_2_roadmap() -> None:
    """技术路线图：四阶段蛇形流程 + 底部贯通主线。"""
    fig, ax = plt.subplots(figsize=(8.4, 6.0))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    stages = [
        ("数据重构与节点筛选", BLUE,
         "充电会话记录清洗与 15 min 粒度\n节点代理负荷张量重构\n"
         "节点可用性筛选与质量门禁\n负荷统计特征与事件窗口分析"),
        ("LRE 关系构建与 MRG-GCN 建模", ORANGE,
         "负荷耦合 / 行为共现 / 轮廓相似\n三类统计关系图（top-k 稀疏化）\n"
         "TCN 时间编码 + 双层门控 GCN\n多模型对比与消融闭环"),
        ("MDP 三层机制诊断", GREEN,
         "L1 门控干预归因：模型依赖什么关系\n"
         "L2 蒸馏验证：图结构能否被替代\n"
         "L3 四格溯源：误差集中在哪类窗口"),
        ("预测支持探索与结论", RED_S,
         "有向候选结构与条件独立核验\n事件窗口区间预测与潜力上界\n"
         "分层参数干预敏感度与结论"),
    ]

    # 两行蛇形布置，确保缩放到论文版心后标题和正文仍可辨识。
    card_w, card_h = 40, 23
    positions = [(6, 59), (54, 59), (54, 30), (6, 30)]
    for k, ((title, color, body), (x, y)) in enumerate(zip(stages, positions)):
        cx = x + card_w / 2
        _card(ax, x, y, card_w, card_h, body, fc=BG, ec=color,
              lw=1.5, fs=9.2)
        _card(ax, x, y + card_h + 1.2, card_w, 6.0, title,
              fc=color, ec=color, fs=9.4, weight="bold",
              text_color="white", radius=0.35)
        _badge(ax, x + 2.4, y + card_h - 2.5, 1.45, str(k + 1), fc=color)
        mainline = ["数据", "方法", "机制", "结论"][k]
        ax.text(cx, y - 1.8, mainline, ha="center", fontsize=8.5,
                color=color, fontweight="bold")

    # 两条论文贡献线不再另设一张框架图，而以阶段 2、3 的贡献标签直接嵌入
    # 总体技术路线，避免与双贡献示意图的内容重复。
    _card(ax, 54, 89.2, 18.0, 4.8, "方法贡献", fc="#F4E9D9", ec=ORANGE,
          lw=1.0, fs=8.0, weight="bold", radius=0.25, text_color=ORANGE)
    _card(ax, 74, 89.2, 20.0, 4.8, "机制诊断贡献", fc="#E8F0EA", ec=GREEN,
          lw=1.0, fs=8.0, weight="bold", radius=0.25, text_color=GREEN)

    # 1→2，2→3，3→4 的蛇形主流程。
    _arrow(ax, 46.8, 70.5, 53.2, 70.5, color=GRAY_D, lw=1.8, ms=13)
    _arrow(ax, 74, 57.4, 74, 54.0, color=GRAY_D, lw=1.8, ms=13)
    _arrow(ax, 53.2, 41.5, 46.8, 41.5, color=GRAY_D, lw=1.8, ms=13)

    # 顶部：四阶段总述（正文语义文字）
    ax.text(29, 96.0,
            "数据驱动重构 → 场景化关系建模 → 机制化诊断 → 探索性支持",
            ha="center", fontsize=10.5, fontweight="bold", color=GRAY_D)

    # 底部贯通主线条
    bar = mpatches.FancyBboxPatch(
        (4, 4), 92, 15, boxstyle="round,pad=0.008,rounding_size=0.5",
        fc=BG, ec=GRAY_D, lw=1.3, zorder=3,
    )
    ax.add_patch(bar)
    ax.text(50, 16.8, "贯通主线", ha="center", fontsize=8, color=GRAY_M)
    for k, (t, color) in enumerate(zip(
            ["统一预测键与三种子\n一致评价口径",
             "测试集不参与关系图\n与阈值确定",
             "三层诊断贯通至\n预测支持探索",
             "结论以量化证据\n逐条给出"], [BLUE, ORANGE, GREEN, RED_S])):
        cx = [15, 39, 63, 85][k]
        _card(ax, cx - 10, 4.8, 20, 9.5, t, fc="#FDFDFB",
              ec=color, lw=1.2, fs=8.2)

    fig.tight_layout()
    final(fig, "fig1_2_roadmap", (8.4, 6.0))
    plt.close(fig)


if __name__ == "__main__":
    print("=== 批次 18：图 1-2 总体技术路线图 ===")
    fig1_2_roadmap()
    print("=== 完成 ===")
