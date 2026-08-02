"""图 2-2 节点覆盖率/活跃月份分布图（SG-EXP-001 筛选可视化）。

55 个候选节点按训练期活跃月份比例降序排列，绘制训练/验证/测试三阶段的
活跃月份比例散点；颜色区分主分析节点（10 个，训练+验证双 0.50 门槛）、
敏感性专属节点（5 个）与未入选节点（40 个）；虚线标注两档门槛。
（敏感性门槛 0.25 通过者共 15 个，其中 10 个与主分析重叠，重叠者按主分析着色。）
测试期可评价性不参与选择，仅以点形可见性体现（未入选节点测试期点仍画出）。
输出：同名 SVG 矢量图 + 1200 DPI PNG。
数据来源：SG-DATA-002-node-coverage-stability.csv（55 行，SG-EXP-001 产物）。
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

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
GRAY_XL = "#E6E9EC"

# 门槛来源：configs/experiments/SG-EXP-001-data-feasibility.yaml（筛选规则权威）
MAIN_THRESHOLD = 0.50  # 主分析节点：train/validation 活跃月份比例 ≥ 0.50
SENS_THRESHOLD = 0.25  # 敏感性节点：train/validation 活跃月份比例 ≥ 0.25

# (split 名, 标记形状, 是否实心)：训练期实心，验证/测试期空心（空心=占比分子不同）
SPLITS = [
    ("train", "o", True),
    ("validation", "s", False),
    ("test", "^", False),
]


def main() -> None:
    """读取覆盖率 CSV，绘制图 2-2 并导出 SVG + PNG。"""
    df = pd.read_csv("data/processed/SG-DATA-002-node-coverage-stability.csv")
    # SG-DATA-002 契约：55 候选节点；布尔列必须 bool dtype（object+NaN 经
    # astype(bool) 会静默提升为 True，把未入选节点错误标为主分析——显式断言封死）
    assert len(df) == 55, f"SG-DATA-002 契约 55 行，实际 {len(df)}"
    for col in ("primary_selected_train_validation",
                "sensitivity_selected_train_validation"):
        assert df[col].dtype == bool, f"{col} 应为 bool dtype，实际 {df[col].dtype}"
    ratio_cols = [f"{s}_active_month_ratio" for s, _, _ in SPLITS]
    assert df[ratio_cols].notna().all().all(), "活跃月份比例列存在 NaN"
    df = df.sort_values("train_active_month_ratio", ascending=False).reset_index(drop=True)
    x = np.arange(len(df))

    # 类别掩码：主分析 / 敏感性专属 / 未入选；三类同时用颜色和形状编码。
    is_main = df["primary_selected_train_validation"].astype(bool).to_numpy()
    is_sens = (~is_main) & df["sensitivity_selected_train_validation"].astype(bool).to_numpy()
    is_other = ~(is_main | is_sens)
    groups = [(is_main, BLUE, "o"), (is_sens, ORANGE, "D"), (is_other, GRAY_M, "s")]

    fig = plt.figure(figsize=(9.2, 5.4))
    gs = fig.add_gridspec(5, 1, height_ratios=[0.36, 1.0, 1.0, 1.0, 0.72],
                          left=0.10, right=0.985, top=0.96, bottom=0.12,
                          hspace=0.22)
    ax_header = fig.add_subplot(gs[0, 0])
    ax_header.axis("off")
    axes = [fig.add_subplot(gs[i, 0]) for i in range(1, 4)]
    ax_sum = fig.add_subplot(gs[4, 0])
    split_info = [("train", "训练期\n30个月"),
                  ("validation", "验证期\n7个月"),
                  ("test", "测试期\n7个月")]

    for row_i, (split, split_label) in enumerate(split_info):
        ax = axes[row_i]
        y = df[f"{split}_active_month_ratio"].to_numpy(dtype=float)
        for mask, color, marker in groups:
            ax.scatter(x[mask], y[mask], s=28 if row_i else 31,
                       marker=marker, facecolor=color, edgecolor="white",
                       linewidth=0.35, alpha=0.92, zorder=3)
        ax.set_xlim(-0.8, len(df) - 0.2)
        ax.set_ylim(-0.03, 1.08)
        ax.set_yticks([0, 0.5, 1.0])
        ax.set_ylabel(split_label, fontsize=8.0, rotation=0, ha="right", va="center",
                      labelpad=22)
        ax.grid(axis="y", color=GRAY_L, lw=0.55, alpha=0.72, zorder=0)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color(GRAY_D)
        ax.spines["bottom"].set_color(GRAY_L if row_i < 2 else GRAY_D)
        ax.tick_params(labelsize=7.4, colors=GRAY_D)
        if row_i < 2:
            ax.axhline(MAIN_THRESHOLD, color=BLUE, lw=0.9, ls="--", alpha=0.75, zorder=1)
            ax.axhline(SENS_THRESHOLD, color=ORANGE, lw=0.9, ls="--", alpha=0.75, zorder=1)
        if row_i == 1:
            ax.text(len(df) - 0.35, MAIN_THRESHOLD + 0.035, "主分析 ≥ 0.50",
                    ha="right", va="bottom", fontsize=6.8, color=BLUE)
            ax.text(len(df) - 0.35, SENS_THRESHOLD + 0.035, "敏感性 ≥ 0.25",
                    ha="right", va="bottom", fontsize=6.8, color=ORANGE)
        if row_i < 2:
            ax.tick_params(labelbottom=False)

    # 标题与图例占据独立栏位，避免紧边界导出时与首行数据相撞。
    ax_header.text(0.0, 0.78, "A  三阶段活跃月份比例：按训练期降序排列",
                   transform=ax_header.transAxes, ha="left", va="center",
                   fontsize=9.8, color=GRAY_D)
    axes[2].set_xticks(np.arange(0, len(df), 5))
    axes[2].set_xticklabels([str(v + 1) for v in np.arange(0, len(df), 5)], fontsize=7.4)
    axes[2].set_xlabel(f"候选节点序号（共 {len(df)} 个；按训练期活跃月份比例降序）",
                       fontsize=8.6, labelpad=5)
    ax_header.text(0.0, 0.18, "● 主分析节点   ◆ 敏感性专属节点   ■ 未入选节点",
                   transform=ax_header.transAxes, ha="left", va="center",
                   fontsize=7.3, color=GRAY_D)

    # B：把筛选结果单独总结为一条组成条，避免在主图内塞入节点名称和大图例。
    n_main = int(is_main.sum())
    n_sens = int(is_sens.sum())
    n_gray = int(is_other.sum())
    counts = [(n_main, BLUE, f"主分析\n{n_main}"),
              (n_sens, ORANGE, f"敏感性专属\n{n_sens}"),
              (n_gray, GRAY_M, f"未入选\n{n_gray}")]
    left = 0
    for count, color, label in counts:
        ax_sum.barh(0, count, left=left, height=0.48, color=color,
                    edgecolor="white", linewidth=0.8)
        ax_sum.text(left + count / 2, 0, label, ha="center", va="center",
                    fontsize=6.6, color="white" if color != ORANGE else GRAY_D,
                    fontweight="bold")
        left += count
    ax_sum.set_xlim(0, len(df))
    ax_sum.set_ylim(-0.55, 0.62)
    ax_sum.set_yticks([])
    ax_sum.set_xticks([0, 10, 15, 55])
    ax_sum.set_xlabel("候选节点数量", fontsize=7.2, labelpad=3)
    # 面板标注用 ax.text 而非 set_title（图内禁止标题 API，见 CLAUDE.md 图表约束）
    ax_sum.text(0.0, 0.60,
                f"B  筛选结果：{n_main} 个主分析 + {n_sens} 个敏感性专属 + {n_gray} 个未入选",
                ha="left", va="top", fontsize=8.4, color=GRAY_D)
    ax_sum.text(len(df), 0.42, f"总计 {len(df)} 个", ha="right", va="bottom",
                fontsize=6.2, color=GRAY_M)
    for spine in ("top", "right", "left"):
        ax_sum.spines[spine].set_visible(False)
    ax_sum.spines["bottom"].set_color(GRAY_D)
    ax_sum.tick_params(labelsize=6.7, colors=GRAY_D)

    export_figure(
        fig,
        basename=str(FIG_DIR / "fig2_2_node_coverage"),
        formats=["svg", "png"],
        dpi=1200,
        size_inches=(9.2, 5.4),
        grayscale_preview=False,
    )
    print("  ✅ fig2_2_node_coverage")
    return None


if __name__ == "__main__":
    main()
