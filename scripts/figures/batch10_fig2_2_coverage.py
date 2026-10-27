"""图 2-2 候选节点覆盖率与筛选结果（SG-EXP-001 筛选可视化）。

2026-10-27 重构表达形式：原"三条散点带"（训练/验证/测试各一行，55 节点
按训练期降序）改为二维象限散点——筛选规则本就是"训练期 ≥ 门槛 且 验证期
≥ 门槛"的联合条件，x=训练期比例、y=验证期比例的散点 + 两档门槛虚线 +
区域计数让规则依据直接可读，替代点串成珠链的带状表达。测试期不参与筛选，
以空心标记表达"测试期不可评价"（全量描述性统计）。

55 个候选节点按颜色 + 点形双编码区分主分析节点（10 个，训练+验证双 0.50
门槛）、敏感性专属节点（5 个）与未入选节点（40 个）。（敏感性门槛 0.25
通过者共 15 个，其中 10 个与主分析重叠，重叠者按主分析着色。）
底部堆叠条给出三类节点的数量构成。

画布直接按论文显示尺寸绘制（成品 5.59 in 宽，与 14.66 cm 版心吻合），故 fontsize
即纸面真实字号，排版时不再被等比缩小。
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
OUTPUT_STEM = "fig2_2_node_coverage"
setup_style(journal="general", lang="zh")
# 本图坐标轴位置全部按英寸显式给出，关闭 constrained_layout 以免版面被重排
plt.rcParams["figure.constrained_layout.use"] = False

BLUE = "#2C5F8A"
ORANGE = "#D08A3C"
GRAY_D = "#404040"
GRAY_M = "#808080"
GRAY_L = "#C8C8C8"

# 门槛来源：configs/experiments/SG-EXP-001-data-feasibility.yaml（筛选规则权威）
MAIN_THRESHOLD = 0.50  # 主分析节点：train/validation 活跃月份比例 ≥ 0.50
SENS_THRESHOLD = 0.25  # 敏感性节点：train/validation 活跃月份比例 ≥ 0.25

# (split 名, 带标签)：带标签第一行是分期名，第二行是该期日历月数（比例分母）
STAGES = [
    ("train", "训练期\n30 个月"),
    ("validation", "验证期\n7 个月"),
    ("test", "测试期\n7 个月"),
]

# ========== 画布与版面（英寸，按纸面尺寸设计） ==========
# 论文版心 = A4 宽 21 cm − 左右各 3.17 cm 页边距 = 14.66 cm = 5.77 in，图按
# 5.59 in 排版；直接把 figsize 设为显示尺寸后，fontsize 即为纸面 pt。
FIG_W_IN = 5.65  # 留出两端被 bbox_inches='tight' 裁掉的空白，成品宽 ≈5.59 in
FIG_H_IN = 3.80  # 面板 A（边际分布 + 象限散点）+ 底部堆叠条 + 各处轴标题

PAD_TOP = 0.05       # 顶端留白
HEADER_H = 0.22      # 顶部一行：面板字母 (a) + 类别图例
GAP_HEADER = 0.06
A_TOP_IN = PAD_TOP + HEADER_H + GAP_HEADER  # 面板 A 顶端距画布顶端
TOPH_H_IN = 0.42     # 顶部边际分布（训练期比例，节点计数）
MARG_GAP_IN = 0.04   # 边际分布与主散点的间距
A_H_IN = 1.72        # 主散点高度
RIGHT_W_IN = 0.50    # 右侧边际分布（验证期比例）宽度
GAP_A_B = 0.44       # A 的 x 刻度/轴标题 + 面板字母 (b) 所需间距
SUMMARY_H = 0.54     # 底部堆叠条面板高度
LEFT_IN = 0.66       # 面板 A 左边界：y 轴标题 + 刻度标签
RIGHT_IN = MARG_GAP_IN + RIGHT_W_IN + 0.10  # 主散点右缘右侧：边际分布 + 留白

# ========== 字号（pt；等于纸面字号） ==========
FS_PANEL = 8.2       # (a)/(b) 面板字母
FS_LEGEND = 7.4      # 类别图例
FS_STAGE = 7.8       # 分期标签
FS_TICK = 7.2        # 刻度标签
FS_AXLABEL = 8.0     # 轴标题
FS_THRESHOLD = 7.0   # 门槛参考线标注
FS_BAR = 7.0         # 堆叠条分段标注
FS_NOTE = 6.8        # 总计注记
MARKER_S = 13.0      # 散点面积（pt²）：点间距约 6.0 pt，实心直径 ≈3.6 pt，
                     # 同值相邻点之间留出可见缝隙（旧版 22.0 直径≈4.7 pt，
                     # 点串成珠链，2026-10-27 反馈）

SUMMARY_TOP = A_TOP_IN + TOPH_H_IN + MARG_GAP_IN + A_H_IN + GAP_A_B

AX_LEFT_FRAC = LEFT_IN / FIG_W_IN
AX_WIDTH_FRAC = (FIG_W_IN - LEFT_IN - RIGHT_IN) / FIG_W_IN


def _y_frac(top_in: float) -> float:
    """把"距画布顶端的英寸数"换算为 figure 分数坐标（左下原点，0~1）。"""
    return 1.0 - top_in / FIG_H_IN


def _axes_from_top(fig: plt.Figure, top_in: float, height_in: float) -> plt.Axes:
    """按"距画布顶端英寸数 + 高度"创建坐标轴，避免自动布局挪动留白。"""
    return fig.add_axes(
        [
            AX_LEFT_FRAC,
            _y_frac(top_in + height_in),
            AX_WIDTH_FRAC,
            height_in / FIG_H_IN,
        ]
    )


def main() -> None:
    """读取覆盖率 CSV，按论文显示尺寸绘制图 2-2 并导出 SVG + PNG。"""
    df = pd.read_csv("data/processed/SG-DATA-002-node-coverage-stability.csv")
    # SG-DATA-002 契约：55 候选节点；布尔列必须 bool dtype（object+NaN 经
    # astype(bool) 会静默提升为 True，把未入选节点错误标为主分析——显式断言封死）
    assert len(df) == 55, f"SG-DATA-002 契约 55 行，实际 {len(df)}"
    for col in ("primary_selected_train_validation",
                "sensitivity_selected_train_validation"):
        assert df[col].dtype == bool, f"{col} 应为 bool dtype，实际 {df[col].dtype}"
    ratio_cols = [f"{split}_active_month_ratio" for split, _ in STAGES]
    assert df[ratio_cols].notna().all().all(), "活跃月份比例列存在 NaN"
    df = df.sort_values("train_active_month_ratio", ascending=False).reset_index(drop=True)

    # 类别掩码：主分析 / 敏感性专属 / 未入选；三类同时用颜色和形状编码。
    is_main = df["primary_selected_train_validation"].astype(bool).to_numpy()
    is_sens = (~is_main) & df["sensitivity_selected_train_validation"].astype(bool).to_numpy()
    is_other = ~(is_main | is_sens)
    groups = [(is_main, BLUE, "o"), (is_sens, ORANGE, "D"), (is_other, GRAY_M, "s")]
    n_main, n_sens, n_other = int(is_main.sum()), int(is_sens.sum()), int(is_other.sum())

    fig = plt.figure(figsize=(FIG_W_IN, FIG_H_IN))

    # ========== 面板 A：训练期 × 验证期活跃比例象限散点（带边际分布） ==========
    # 筛选规则是"训练期 ≥ 门槛 且 验证期 ≥ 门槛"的联合条件：二维散点 +
    # 门槛虚线 + 区域计数让规则依据直接可读；顶部/右侧的边际分布直方图
    # （三类堆叠、节点计数）把 55 个候选的单变量分布显性化，填充单纯散点
    # 留下的大片空白（流式门控图的标准伴侣）。空心标记 = 测试期不可评价
    # （不参与筛选，仅作可评价性描述；图注交代）。
    ax_top = _axes_from_top(fig, A_TOP_IN, TOPH_H_IN)
    ax_a = _axes_from_top(fig, A_TOP_IN + TOPH_H_IN + MARG_GAP_IN, A_H_IN)
    # 右侧边际分布与主散点同纵向范围
    ax_right = fig.add_axes([
        (FIG_W_IN - RIGHT_IN + MARG_GAP_IN) / FIG_W_IN,
        _y_frac(A_TOP_IN + TOPH_H_IN + MARG_GAP_IN + A_H_IN),
        RIGHT_W_IN / FIG_W_IN, A_H_IN / FIG_H_IN])
    test_eval = df["test_evaluable"].astype(bool).to_numpy()
    train_r = df["train_active_month_ratio"].to_numpy(dtype=float)
    val_r = df["validation_active_month_ratio"].to_numpy(dtype=float)
    # 三类节点标记大小拉开层次：主分析最大、未入选最小
    for (mask, color, marker), scale in zip(groups, [2.0, 1.6, 1.2]):
        solid = mask & test_eval
        ax_a.scatter(train_r[solid], val_r[solid], s=MARKER_S * scale,
                     marker=marker, facecolor=color, edgecolor="white",
                     linewidth=0.5, alpha=0.92, zorder=3)
        hollow = mask & ~test_eval
        if hollow.any():
            ax_a.scatter(train_r[hollow], val_r[hollow], s=MARKER_S * scale,
                         marker=marker, facecolor="white", edgecolor=color,
                         linewidth=0.8, alpha=0.92, zorder=4)
    for thr, color in [(MAIN_THRESHOLD, BLUE), (SENS_THRESHOLD, ORANGE)]:
        ax_a.axvline(thr, color=color, lw=0.9, ls="--", alpha=0.75, zorder=1)
        ax_a.axhline(thr, color=color, lw=0.9, ls="--", alpha=0.75, zorder=1)
    # 门槛标注：蓝色标在竖线顶端（右上区数据已在门槛线上方，文字贴线右侧空白）；
    # 橙色标在横线右端下方（该区域无点）。
    bbox = {"facecolor": "white", "edgecolor": "none", "alpha": 0.85, "pad": 0.8}
    ax_a.text(MAIN_THRESHOLD + 0.012, 0.75, "主分析 ≥ 0.50", ha="left", va="top",
              fontsize=FS_THRESHOLD, color=BLUE, bbox=bbox)
    ax_a.text(0.985, SENS_THRESHOLD - 0.015, "敏感性 ≥ 0.25", ha="right", va="top",
              fontsize=FS_THRESHOLD, color=ORANGE, bbox=bbox)
    # 区域计数：右上象限 = 主分析；两阈值间的 L 形带 = 敏感性专属；其余 = 未入选
    # （数据坐标放置，避开点群与门槛线）
    ax_a.text(0.52, 0.60, f"主分析 {n_main}", ha="left", va="center",
              fontsize=FS_STAGE, color=BLUE, fontweight="bold")
    ax_a.text(0.53, 0.375, f"敏感性专属 {n_sens}", transform=ax_a.transAxes,
              ha="left", va="center", fontsize=FS_THRESHOLD, color=ORANGE,
              bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.85,
                    "pad": 0.8})
    ax_a.text(0.16, 0.10, f"未入选 {n_other}", transform=ax_a.transAxes,
              ha="center", va="center", fontsize=FS_THRESHOLD, color=GRAY_M)
    ax_a.set_xlim(-0.025, 1.0)
    ax_a.set_ylim(-0.035, 0.78)  # 负下边距：y=0 的 26 个验证期不活跃节点不贴轴
    ax_a.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    ax_a.set_yticks([0, 0.25, 0.5])
    ax_a.set_xlabel("训练期活跃月份比例（30 个自然月）", fontsize=FS_AXLABEL,
                    color=GRAY_D, labelpad=4)
    ax_a.set_ylabel("验证期活跃月份比例\n（7 个自然月）", fontsize=FS_AXLABEL,
                    color=GRAY_D, labelpad=2)
    ax_a.grid(axis="both", color=GRAY_L, lw=0.55, alpha=0.72, zorder=0)
    ax_a.set_axisbelow(True)
    ax_a.spines["top"].set_visible(False)
    ax_a.spines["right"].set_visible(False)
    ax_a.spines["left"].set_color(GRAY_D)
    ax_a.spines["bottom"].set_color(GRAY_D)
    ax_a.tick_params(labelsize=FS_TICK, colors=GRAY_D, length=0)

    # 边际分布：三类节点堆叠计数，与主散点共享量程；无边框无刻度，
    # 计数语义由图注交代（绝对计数不重要，分布形状重要）
    bins_x = np.linspace(0, 1.0, 13)
    bottom = np.zeros(len(bins_x) - 1)
    for mask, color, _m in groups:
        cnt, _ = np.histogram(train_r[mask], bins=bins_x)
        ax_top.bar(bins_x[:-1], cnt, width=np.diff(bins_x), align="edge",
                   bottom=bottom, color=color, alpha=0.85, edgecolor="white",
                   lw=0.3, zorder=2)
        bottom += cnt
    ax_top.set_xlim(ax_a.get_xlim())
    ax_top.set_ylim(0, bottom.max() * 1.06)
    ax_top.axis("off")

    bins_y = np.linspace(0, 0.78, 12)
    left = np.zeros(len(bins_y) - 1)
    for mask, color, _m in groups:
        cnt, _ = np.histogram(val_r[mask], bins=bins_y)
        ax_right.barh(bins_y[:-1], cnt, height=np.diff(bins_y), align="edge",
                      left=left, color=color, alpha=0.85, edgecolor="white",
                      lw=0.3, zorder=2)
        left += cnt
    ax_right.set_ylim(ax_a.get_ylim())
    ax_right.set_xlim(0, left.max() * 1.06)
    ax_right.axis("off")

    # 面板字母与图例同占顶部一行，紧贴散点带左边界对齐
    header_y = _y_frac(PAD_TOP + HEADER_H / 2)
    fig.text(AX_LEFT_FRAC, header_y, "(a)", ha="left", va="center",
             fontsize=FS_PANEL, fontweight="bold", color=GRAY_D)
    # 图例用真实标记（颜色 + 形状同时给出），而非灰色文字符号：后者看不出
    # 类别配色，读者得回图里比对才能把形状映射到颜色
    handles = [
        plt.Line2D([], [], marker=marker, linestyle="none", markersize=4.0,
                   markerfacecolor=color, markeredgecolor="white", markeredgewidth=0.4,
                   label=label)
        for (_, color, marker), label in zip(
            groups, ["主分析节点", "敏感性专属节点", "未入选节点"])
    ]
    fig.legend(handles=handles, loc="center left",
               bbox_to_anchor=(AX_LEFT_FRAC + 0.24 / FIG_W_IN, header_y),
               bbox_transform=fig.transFigure, ncol=3, frameon=False,
               fontsize=FS_LEGEND, handlelength=0.8, handletextpad=0.35,
               columnspacing=1.5, borderaxespad=0.0, labelcolor=GRAY_D)

    # ========== 面板 B：筛选结果堆叠条 ==========
    # 分段标注统一置于条上方：敏感性专属段仅占 5/55 宽，条内放不下文字。
    ax_sum = _axes_from_top(fig, SUMMARY_TOP, SUMMARY_H)
    counts = [(n_main, BLUE, f"主分析 {n_main}"),
              (n_sens, ORANGE, f"敏感性专属 {n_sens}"),
              (n_other, GRAY_M, f"未入选 {n_other}")]
    left = 0
    for count, color, label in counts:
        ax_sum.barh(-0.28, count, left=left, height=0.52, color=color,
                    edgecolor="white", linewidth=0.8, zorder=3)
        ax_sum.text(left + count / 2, 0.26, label, ha="center", va="center",
                    fontsize=FS_BAR, color=GRAY_D, zorder=4)
        left += count
    ax_sum.set_xlim(0, len(df))
    # y 范围只需容纳"条 + 条上方一行标注"，收紧以去掉面板内多余留白
    ax_sum.set_ylim(-0.72, 0.50)
    ax_sum.set_yticks([])
    ax_sum.set_xticks([0, 10, 15, 55])
    ax_sum.set_xlabel("候选节点数量", fontsize=FS_AXLABEL, color=GRAY_D, labelpad=3)
    for spine in ("top", "right", "left"):
        ax_sum.spines[spine].set_visible(False)
    ax_sum.spines["bottom"].set_color(GRAY_D)
    ax_sum.tick_params(labelsize=FS_TICK, colors=GRAY_D, length=0)

    # 面板字母与总计注记位于堆叠条上方一行（图内禁止 set_title/suptitle）；
    # 上移 0.035 in 恰好落在散点带 x 轴标题之下、堆叠条分段标注之上
    panel_b_y = _y_frac(SUMMARY_TOP - 0.035)
    fig.text(AX_LEFT_FRAC, panel_b_y, "(b)", ha="left", va="center",
             fontsize=FS_PANEL, fontweight="bold", color=GRAY_D)
    fig.text(1.0 - RIGHT_IN / FIG_W_IN, panel_b_y, f"总计 {len(df)} 个",
             ha="right", va="center", fontsize=FS_NOTE, color=GRAY_M)

    export_figure(
        fig,
        basename=str(FIG_DIR / OUTPUT_STEM),
        formats=["svg", "png"],
        dpi=1200,
        size_inches=(FIG_W_IN, FIG_H_IN),
        pad_inches=0.02,
        grayscale_preview=False,
    )
    # matplotlib 输出的多行 path 数据带行尾空格，逐行 rstrip 以通过仓库空白检查
    svg_path = FIG_DIR / f"{OUTPUT_STEM}.svg"
    svg_path.write_text(
        "\n".join(line.rstrip() for line in svg_path.read_text(encoding="utf-8").splitlines()) + "\n",
        encoding="utf-8",
    )
    plt.close(fig)
    print("  ✅ fig2_2_node_coverage")
    return None


if __name__ == "__main__":
    main()
