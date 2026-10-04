"""图 2-2 节点覆盖率/活跃月份分布图（SG-EXP-001 筛选可视化）。

55 个候选节点按训练期活跃月份比例降序排列，绘制训练/验证/测试三阶段的
活跃月份比例散点；颜色 + 点形双编码区分主分析节点（10 个，训练+验证双 0.50
门槛）、敏感性专属节点（5 个）与未入选节点（40 个）；虚线标注两档门槛。
（敏感性门槛 0.25 通过者共 15 个，其中 10 个与主分析重叠，重叠者按主分析着色。）
底部堆叠条给出三类节点的数量构成。测试期可评价性不参与选择，仅以点形可见性
体现（未入选节点测试期点仍画出）。

画布直接按论文显示尺寸绘制（成品 5.59 in 宽，与 14.66 cm 版心吻合），故 fontsize
即纸面真实字号，排版时不再被等比缩小（改前 9.22 in 宽被压到 0.61 倍，6.2 pt 缩成
3.8 pt）；高度按三条散点带 + 堆叠条的实际需要取 4.37 in。
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
# 5.59 in 排版；直接把 figsize 设为显示尺寸后，fontsize 即为纸面 pt，不再被
# 排版缩放吃掉。高度给到 4.37 in：55 个候选节点的刻度与各类标签才排得开。
FIG_W_IN = 5.65  # 留出两端被 bbox_inches='tight' 裁掉的空白，成品宽 ≈5.59 in
FIG_H_IN = 4.37  # 版面自顶端向下累计约 3.55 in，余量留给堆叠条刻度与轴标题

PAD_TOP = 0.05       # 顶端留白
HEADER_H = 0.22      # 顶部一行：面板字母 (a) + 类别图例
GAP_HEADER = 0.05
BAND_H = 0.79        # 单条散点带高度
GAP_BAND = 0.17      # 带间留白（带内侧 x 刻度已隐藏，无需容纳文字）
GAP_BAND_SUM = 0.50  # 末条散点带的 x 刻度/轴标签 + 面板字母 (b)
SUMMARY_H = 0.54     # 底部堆叠条面板高度
LEFT_IN = 0.90       # 散点带左边界：为"共享 y 轴标题 + 分期标签 + 刻度标签"预留
YLABEL_X_IN = 0.15   # 共享 y 轴标题中心距画布左缘
ROW_LABEL_RIGHT_IN = 0.65  # 分期标签右对齐位置（'30 个月' 与 '0.5' 间留 0.07 in）
RIGHT_IN = 0.06

# ========== 字号（pt；等于纸面字号） ==========
FS_PANEL = 8.2       # (a)/(b) 面板字母
FS_LEGEND = 7.4      # 类别图例
FS_STAGE = 7.8       # 分期标签
FS_TICK = 7.2        # 刻度标签
FS_AXLABEL = 8.0     # 轴标题
FS_THRESHOLD = 7.0   # 门槛参考线标注
FS_BAR = 7.0         # 堆叠条分段标注
FS_NOTE = 6.8        # 总计注记
MARKER_S = 22.0      # 散点面积（pt²）：点间距约 6.0 pt，实心直径 ≈4.7 pt

# 带顶端距画布顶端的英寸数（自顶向下累计，便于逐段核对版面）
BAND_TOPS = [
    PAD_TOP + HEADER_H + GAP_HEADER + i * (BAND_H + GAP_BAND) for i in range(len(STAGES))
]
SUMMARY_TOP = BAND_TOPS[-1] + BAND_H + GAP_BAND_SUM

AX_LEFT_FRAC = LEFT_IN / FIG_W_IN
AX_WIDTH_FRAC = (FIG_W_IN - LEFT_IN - RIGHT_IN) / FIG_W_IN
ROW_LABEL_X_FRAC = ROW_LABEL_RIGHT_IN / FIG_W_IN


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


def _style_band(ax: plt.Axes, is_bottom: bool) -> None:
    """统一单条散点带的样式：去顶/右边框、仅保留横向浅网格与 y 刻度。

    输入：ax 为散点带坐标轴；is_bottom 标记是否为最下方一条（其底边框加粗，
    并保留 x 刻度标签，充当面板 A 的公共 x 轴）。
    """
    ax.set_yticks([0.0, 0.5, 1.0])
    ax.grid(axis="y", color=GRAY_L, lw=0.55, alpha=0.72, zorder=0)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(GRAY_D)
    ax.spines["bottom"].set_color(GRAY_D if is_bottom else GRAY_L)
    ax.tick_params(labelsize=FS_TICK, colors=GRAY_D, length=0)
    ax.set_axisbelow(True)


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
    x = np.arange(len(df))

    # 类别掩码：主分析 / 敏感性专属 / 未入选；三类同时用颜色和形状编码。
    is_main = df["primary_selected_train_validation"].astype(bool).to_numpy()
    is_sens = (~is_main) & df["sensitivity_selected_train_validation"].astype(bool).to_numpy()
    is_other = ~(is_main | is_sens)
    groups = [(is_main, BLUE, "o"), (is_sens, ORANGE, "D"), (is_other, GRAY_M, "s")]
    n_main, n_sens, n_other = int(is_main.sum()), int(is_sens.sum()), int(is_other.sum())

    fig = plt.figure(figsize=(FIG_W_IN, FIG_H_IN))

    # ========== 面板 A：三条散点带（训练/验证/测试） ==========
    band_axes = []
    for row_i, (split, stage_label) in enumerate(STAGES):
        ax = _axes_from_top(fig, BAND_TOPS[row_i], BAND_H)
        band_axes.append(ax)
        y = df[f"{split}_active_month_ratio"].to_numpy(dtype=float)
        for mask, color, marker in groups:
            ax.scatter(x[mask], y[mask], s=MARKER_S, marker=marker,
                       facecolor=color, edgecolor="white", linewidth=0.35,
                       alpha=0.92, zorder=3)
        ax.set_xlim(-0.8, len(df) - 0.2)
        ax.set_ylim(-0.04, 1.06)
        is_bottom = row_i == len(STAGES) - 1
        _style_band(ax, is_bottom)
        # 分期标签放在刻度标签左侧（旋转 0°），避免 y 轴标题与刻度互相挤压
        fig.text(ROW_LABEL_X_FRAC, _y_frac(BAND_TOPS[row_i] + BAND_H / 2), stage_label,
                 ha="right", va="center", fontsize=FS_STAGE, color=GRAY_D,
                 linespacing=1.45)
        if row_i < 2:
            ax.tick_params(labelbottom=False)
            ax.axhline(MAIN_THRESHOLD, color=BLUE, lw=0.9, ls="--", alpha=0.75, zorder=1)
            ax.axhline(SENS_THRESHOLD, color=ORANGE, lw=0.9, ls="--", alpha=0.75, zorder=1)
        if row_i == 1:
            # 门槛标注放在数据稀疏的右端线上方，白底避免与网格线/散点粘连
            bbox = {"facecolor": "white", "edgecolor": "none", "alpha": 0.85, "pad": 0.8}
            ax.text(len(df) - 0.4, MAIN_THRESHOLD + 0.03, "主分析 ≥ 0.50",
                    ha="right", va="bottom", fontsize=FS_THRESHOLD, color=BLUE, bbox=bbox)
            ax.text(len(df) - 0.4, SENS_THRESHOLD + 0.03, "敏感性 ≥ 0.25",
                    ha="right", va="bottom", fontsize=FS_THRESHOLD, color=ORANGE, bbox=bbox)

    # 共享 y 轴标题：量纲（活跃月份比例）横跨三条带居中，替代原面板标题中的说明
    bands_center_in = (BAND_TOPS[0] + BAND_TOPS[-1] + BAND_H) / 2
    fig.text(YLABEL_X_IN / FIG_W_IN, _y_frac(bands_center_in), "活跃月份比例",
             ha="center", va="center", rotation=90, fontsize=FS_AXLABEL, color=GRAY_D)

    band_axes[-1].set_xticks(np.arange(0, len(df), 5))
    band_axes[-1].set_xticklabels([str(v + 1) for v in np.arange(0, len(df), 5)])
    band_axes[-1].set_xlabel(f"候选节点序号（共 {len(df)} 个；按训练期活跃月份比例降序）",
                             fontsize=FS_AXLABEL, color=GRAY_D, labelpad=5)

    # 面板字母与图例同占顶部一行，紧贴散点带左边界对齐
    header_y = _y_frac(PAD_TOP + HEADER_H / 2)
    fig.text(AX_LEFT_FRAC, header_y, "(a)", ha="left", va="center",
             fontsize=FS_PANEL, fontweight="bold", color=GRAY_D)
    # 图例用真实标记（颜色 + 形状同时给出），而非灰色文字符号：后者看不出
    # 类别配色，读者得回图里比对才能把形状映射到颜色
    handles = [
        plt.Line2D([], [], marker=marker, linestyle="none", markersize=4.6,
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
