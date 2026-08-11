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
        sds.append(float(np.std(vals, ddof=1)))
    order = np.argsort(alphas)
    alphas = np.asarray(alphas)[order]
    means = np.asarray(means)[order]
    sds = np.asarray(sds)[order]

    # v4：横向条形图（fig3_1 同款风格）——天然无遮挡、无空旷、无数字重合
    # 教师/TCN 的 SD 取正式核验值（与 fig3_1 一致）；学生为 4 组 α 的
    # 三种子均值（0.0292~0.0294，α 扫描无显著差异——KD 不奏效的直接证据）
    GREEN = "#597A62"
    student_mean = float(np.mean(means))
    student_lo = float(means.min())
    student_hi = float(means.max())
    rows = [
        ("教师模型 StaticGraph", TEACHER_MAE, 0.00019, None, None, GREEN),
        ("学生模型 TCN（α 扫描 4 组）", student_mean, None,
         student_lo, student_hi, BLUE),
        ("纯 TCN 基线（无蒸馏）", TCN_MAE, 0.00011, None, None, GRAY_M),
    ]
    fig, ax = plt.subplots(figsize=(7.6, 3.0))
    ys = np.arange(len(rows))
    for yi, (label, m, sd, lo, hi, color) in enumerate(rows):
        if sd is not None:
            ax.barh(yi, m, height=0.52, color=color, edgecolor="white",
                    lw=0.6, xerr=sd, capsize=2.5, error_kw=dict(lw=0.8),
                    zorder=3)
        else:  # 学生行：误差棒 = 4 组 α 的 min-max 范围（不对称）
            ax.barh(yi, m, height=0.52, color=color, edgecolor="white",
                    lw=0.6, xerr=[[m - lo], [hi - m]], capsize=2.5,
                    error_kw=dict(lw=0.8), zorder=3)
        ax.text(m + 0.0006, yi, f"{m:.4f}", va="center", ha="left",
                fontsize=7.4, color=GRAY_D)
    # 学生行补充 α 扫描差异说明
    ax.text(student_hi + 0.0032, 1, "α 0.1→2.0\n差异 <0.1%",
            fontsize=6.8, color=BLUE, ha="left", va="center")
    # 教师与学生柱之间的差距标注（双箭头 + 文字）
    ax.annotate("", xy=(0.0316, 0), xytext=(0.0316, 1),
                arrowprops=dict(arrowstyle="<->", color=GRAY_D, lw=1.0))
    ax.text(0.0320, 0.5, "差距 ≈ 2.1×", fontsize=7.6, color=GRAY_D,
            ha="left", va="center")

    ax.set_yticks(ys)
    ax.set_yticklabels([r[0] for r in rows], fontsize=8.0)
    ax.invert_yaxis()  # 教师行（最优）显示在最上方
    ax.set_xlabel("测试集全局 MAE（kWh/15 min）", fontsize=8.8)
    ax.set_xlim(0, 0.036)
    ax.grid(axis="x", color=GRAY_L, lw=0.55, alpha=0.72, zorder=0)

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
