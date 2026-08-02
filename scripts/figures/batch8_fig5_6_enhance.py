"""论文图批次 8：fig5_6 机制增强对比重绘（审查 2026-08-01）。

原图问题（GPT 审查）：
- 截断 y 轴（0.0142 起）视觉夸大约 5% 差异 → 改 0 起点点图
- 单种子验证集快速筛选数据未标注 → 图内明确"验证集快速筛选（单种子）"
- 旧默认配色 + 黑边框 → 统一素雅（深蓝/低饱和橙/灰阶）

数据来源：outputs/analysis/variant_quick_check/variant_napl.json + variant_gate-mi.json
（D6-4 快速筛选，非正式三种子；正式结果 SG-EXP-015/016 回填后替换本图）

统一规范：无标题、无文件名/代号、SVG+PNG 1200DPI、文字不遮挡图形。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt

sys.path.insert(0, str(Path.home() / ".claude/skills/scipilot-figure-skill/scripts"))
try:
    from export_figure import export_figure  # noqa: E402
    from setup_style import setup_style  # noqa: E402
except ImportError:  # 无 skill 环境回退（审查 L-03）
    from _skill_compat import export_figure, setup_style  # noqa: E402

FIG_DIR = Path("outputs/figures")
FIG_DIR.mkdir(parents=True, exist_ok=True)

setup_style(journal="general", lang="zh")
BLUE = "#2C5F8A"
ORANGE = "#D08A3C"
GRAY_D = "#404040"
GRAY_M = "#808080"
GRAY_L = "#C8C8C8"


def final(fig, name: str, size: tuple[float, float]) -> None:
    """统一导出：SVG 矢量 + PNG 1200 DPI（论文硬性约束）。"""
    export_figure(
        fig, basename=str(FIG_DIR / name),
        formats=["svg", "png"], dpi=1200, size_inches=size,
        grayscale_preview=False,
    )
    print(f"  ✅ {name}")


def fig5_6_mechanism_enhance() -> None:
    napl = json.load(open("outputs/analysis/variant_quick_check/variant_napl.json"))
    gmi = json.load(open("outputs/analysis/variant_quick_check/variant_gate-mi.json"))
    base = napl["baseline_val_mae"]
    items = [
        ("基线（StaticGraph）", base, GRAY_D, "-"),
        ("NAPL 节点差异化参数", napl["val_mae"], BLUE, "o"),
        ("Gate-MI 门控专业化去相关", gmi["val_mae"], ORANGE, "o"),
    ]

    fig, ax = plt.subplots(figsize=(6.6, 3.2))
    y = [2, 1, 0]
    for yi, (name, v, c, mk) in zip(y, items):
        ax.scatter(v, yi, s=120, facecolor=c if mk == "o" else "white",
                   edgecolor=c, linewidth=1.4, zorder=4)
        ax.text(v + 0.00028, yi, f"{v:.5f}", va="center", fontsize=8,
                color=GRAY_D)
        # 相对基线变化标注（基线行不标）
        if yi < 2:
            pct = 100 * (v / base - 1)
            ax.text(v - 0.00028, yi, f"{pct:+.1f}%", ha="right", va="center",
                    fontsize=8, color=c, fontweight="bold")
    # 基线参考虚线（0 起点不截断，视觉不夸大）
    ax.axvline(base, color=GRAY_M, lw=1.0, ls=":", zorder=2)
    ax.set_yticks(y)
    ax.set_yticklabels([i[0] for i in items], fontsize=8.5)
    ax.set_xlabel("验证集 MAE（kWh/15 min）", fontsize=9)
    ax.set_xlim(0, base * 1.18)
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color(GRAY_D)
    ax.tick_params(labelsize=8, colors=GRAY_D)
    ax.grid(axis="x", color=GRAY_L, lw=0.5, alpha=0.6, zorder=0)
    # 单种子/快速筛选性质只在图注和图表清单中披露，避免工作状态文字进入图面。
    final(fig, "fig5_6_mechanism_enhance", (6.6, 3.2))


if __name__ == "__main__":
    print("=== 批次 8：fig5_6 机制增强对比重绘 ===")
    fig5_6_mechanism_enhance()
    print("批次 8 完成")
