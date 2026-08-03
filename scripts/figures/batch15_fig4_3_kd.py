"""图 4-3：GCN→TCN 知识蒸馏结果（SG-EXP-013，4 组 α × 3 种子）。

横轴为蒸馏权重 α（对数刻度），纵轴为测试集全局 MAE（三种子均值 ± SD）。
参考线：教师 StaticGraph（0.01376）与纯 TCN 学生无蒸馏基线（0.02952）。
结论：α 从 0.1 增至 2.0，学生始终停留在 0.029 量级（与教师差距约 2.1 倍）——
KD 未弥合差距，图结构承载不可蒸馏的结构知识（4.3 节判定分支 B）。
输出：同名 SVG + 1200 DPI PNG。
数据来源：outputs/experiments/SG-EXP-013/20260803-093503/（2026-08-04 核验）。
"""

from __future__ import annotations

import glob
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

BASE = "outputs/experiments/SG-EXP-013/20260803-093503"
TEACHER_MAE = 0.01376  # StaticGraph 三种子均值（正式）
TCN_MAE = 0.02952  # 纯 TCN 无蒸馏基线（正式）


def main() -> None:
    """读取 KD 各 α×seed 结果，绘制蒸馏曲线并导出 SVG + PNG。"""
    alphas, means, sds = [], [], []
    for sub in sorted(glob.glob(f"{BASE}/alpha-*_seed-*")):
        name = Path(sub).name
        alpha = float(name.split("_seed-")[0].replace("alpha-", ""))
        mf = glob.glob(f"{sub}/metrics.json")
        if not mf:
            continue
        vals = [json.load(open(f))["global"]["mae"] for f in mf]
        alphas.append(alpha)
        means.append(float(np.mean(vals)))
        sds.append(float(np.std(vals)))
    order = np.argsort(alphas)
    alphas = np.asarray(alphas)[order]
    means = np.asarray(means)[order]
    sds = np.asarray(sds)[order]

    fig, ax = plt.subplots(figsize=(7.4, 4.4))
    GREEN = "#597A62"
    # 差距带：教师线到学生区域之间的浅绿带（填充空白 + 表达"蒸馏未弥合"语义）
    band_top = float(np.mean(means)) + 0.0003
    ax.axhspan(TEACHER_MAE, band_top, color=GREEN, alpha=0.07, zorder=0)
    ax.text(2.08, (TEACHER_MAE + band_top) / 2, "蒸馏未弥合区间\n≈ 2.1×",
            fontsize=7.2, color=GREEN, ha="right", va="center")

    # 学生曲线（蓝点 + 误差棒 + 连接线）
    ax.plot(alphas, means, color=BLUE, lw=1.2, zorder=3)
    ax.errorbar(alphas, means, yerr=sds, fmt="o", ms=6.5, color=BLUE,
                ecolor=BLUE, capsize=3.0, lw=1.2, label="蒸馏学生（TCN+KD）",
                zorder=4)
    # 数值标注放点下方（TCN 参考线在点上方，避免与标注重叠）
    for xi, m in zip(alphas, means):
        ax.text(xi, m - 0.0008, f"{m:.4f}", ha="center", va="top",
                fontsize=7.0, color=BLUE)
    # 参考线：教师（绿虚线）与纯 TCN（灰点线），名称左端、数值右端
    ax.axhline(TEACHER_MAE, color=GREEN, lw=1.4, ls="--", zorder=1)
    ax.text(0.105, TEACHER_MAE + 0.00025, "教师 StaticGraph", fontsize=7.4,
            color=GREEN, ha="left", va="bottom")
    ax.text(2.0, TEACHER_MAE + 0.00025, f"{TEACHER_MAE:.4f}", fontsize=7.4,
            color=GREEN, ha="right", va="bottom")
    ax.axhline(TCN_MAE, color=GRAY_M, lw=1.3, ls=":", zorder=1)
    ax.text(0.105, TCN_MAE + 0.00025, "纯 TCN 基线", fontsize=7.4,
            color=GRAY_M, ha="left", va="bottom")
    ax.text(2.0, TCN_MAE + 0.00025, f"{TCN_MAE:.4f}", fontsize=7.4,
            color=GRAY_M, ha="right", va="bottom")

    ax.set_xscale("log")
    ax.set_xticks(list(alphas))
    ax.set_xticklabels([str(a) for a in alphas], fontsize=8.2)
    ax.set_xlabel("蒸馏权重 α（对数刻度）", fontsize=8.8)
    ax.set_ylabel("测试集全局 MAE（kWh/15 min）", fontsize=8.8)
    ax.set_ylim(0.0132, 0.0306)
    ax.set_xlim(0.09, 2.35)
    ax.legend(fontsize=7.4, frameon=False, loc="upper center",
              bbox_to_anchor=(0.5, 1.10))

    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color(GRAY_D)
    ax.tick_params(labelsize=8, colors=GRAY_D)
    ax.grid(axis="y", color=GRAY_L, lw=0.55, alpha=0.72, zorder=0)

    export_figure(fig, basename=str(FIG_DIR / "fig4_3_kd_distillation"),
                  formats=["svg", "png"], dpi=1200,
                  size_inches=(7.0, 4.2), grayscale_preview=False)
    print("  ✅ fig4_3_kd_distillation")
    return None


if __name__ == "__main__":
    main()
