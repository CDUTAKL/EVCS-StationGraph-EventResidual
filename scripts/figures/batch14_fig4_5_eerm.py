"""图 4-5：EERM 不变性惩罚 λ 敏感性曲线（SG-EXP-014，5λ × 3 种子）。

横轴为不变性正则化权重 λ（对数刻度），纵轴为事件窗口/稳定窗口/全局 MAE
（三种子均值 ± 跨种子标准差）。判定口径（审查 H-09）：λ 增大时事件与稳定
窗口 MAE 均基本不变（变化 <0.5%）——不变性惩罚在本文配置下敏感性不显著，
不作事件特征伪相关的因果诊断。
输出：同名 SVG + 1200 DPI PNG。
数据来源：outputs/experiments/SG-EXP-014/20260731-181616/（2026-08-04 核验）。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path.home() / ".claude/skills/scipilot-figure-skill/scripts"))
try:
    from export_figure import export_figure  # noqa: E402
    from setup_style import setup_style  # noqa: E402
except ImportError:  # 无 skill 环境回退
    from _skill_compat import export_figure, setup_style  # noqa: E402

FIG_DIR = Path("outputs/figures")
setup_style(journal="general", lang="zh")

BLUE = "#2C5F8A"
ORANGE = "#D08A3C"
GRAY_D = "#404040"
GRAY_M = "#808080"
GRAY_L = "#C8C8C8"
RED = "#B05A4A"
GREEN = "#597A62"


def main() -> None:
    """读取 eerm_summary.json，绘制 λ 敏感性曲线并导出 SVG + PNG。"""
    d = json.load(open("outputs/experiments/SG-EXP-014/20260731-181616/eerm_summary.json"))
    # 按 λ 聚合三种子
    by_lambda = {}
    for s in d["summaries"]:
        lam = s["lambda"]
        by_lambda.setdefault(lam, {"event": [], "stable": [], "global": []})
        by_lambda[lam]["event"].append(s["event_window"]["mae"])
        by_lambda[lam]["stable"].append(s["stable_window"]["mae"])
        by_lambda[lam]["global"].append(s["global"]["mae"])
    lams = sorted(by_lambda)

    fig, ax = plt.subplots(figsize=(7.0, 4.1))
    series = [("event", "事件窗口", RED, "o"),
              ("global", "全局", BLUE, "s"),
              ("stable", "稳定窗口", GRAY_M, "^")]
    for key, label, color, marker in series:
        means = np.asarray([np.mean(by_lambda[l][key]) for l in lams])
        sds = np.asarray([np.std(by_lambda[l][key]) for l in lams])
        ax.errorbar(lams, means, yerr=sds, fmt=marker, ms=6.0, color=color,
                    ecolor=color, capsize=2.8, lw=1.2, label=label, zorder=4)
        for xi, m in zip(lams, means):
            ax.text(xi, m + (0.012 if key == "event" else 0.0018 if key == "global" else 0.0012),
                    f"{m:.4f}", ha="center", va="bottom", fontsize=6.4, color=color)

    ax.set_xscale("log")
    ax.set_xticks(lams)
    ax.set_xticklabels([str(l) for l in lams], fontsize=8.2)
    ax.set_xlabel("不变性正则化权重 λ（对数刻度）", fontsize=8.8)
    ax.set_ylabel("MAE（kWh/15 min）", fontsize=8.8)
    ax.set_ylim(0, 0.32)
    ax.legend(fontsize=7.6, frameon=False, loc="upper left")
    # 判定口径说明（审查 H-09）：λ 增大时事件/稳定窗口均基本不变
    ax.text(0.98, -0.16,
            "λ 0→10 时事件窗口变化 <0.5%、稳定窗口变化 <2%——不变性惩罚敏感性不显著，"
            "不作事件伪相关因果诊断",
            transform=ax.transAxes, ha="right", va="top", fontsize=6.6, color=GRAY_M)

    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color(GRAY_D)
    ax.tick_params(labelsize=8, colors=GRAY_D)
    ax.grid(axis="y", color=GRAY_L, lw=0.55, alpha=0.72, zorder=0)

    export_figure(fig, basename=str(FIG_DIR / "fig4_5_eerm_lambda"),
                  formats=["svg", "png"], dpi=1200,
                  size_inches=(7.0, 4.1), grayscale_preview=False)
    print("  ✅ fig4_5_eerm_lambda")
    return None


if __name__ == "__main__":
    main()
