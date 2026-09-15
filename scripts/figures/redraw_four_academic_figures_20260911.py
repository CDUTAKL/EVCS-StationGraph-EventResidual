#!/usr/bin/env python3
"""Deterministic academic redraw of the four figures reviewed on 2026-09-11.

The diagrams are deliberately built from flat rectangles, thin strokes and
orthogonal arrows so that the exported SVG remains editable and the PNGs stay
readable after thesis-column downscaling.  No experiment results are changed.
"""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle


ROOT = Path(__file__).resolve().parents[2]
FIG_DIR = ROOT / "outputs" / "figures"
FOUR_CELL_SUMMARY = ROOT / "outputs" / "analysis" / "SG-EXP-020-legacy-evidence-v1" / "four_cell_summary.csv"

FONT = ["PingFang SC", "Hiragino Sans GB", "Songti SC", "STSong", "Arial Unicode MS", "DejaVu Sans"]
INK = "#1F2B36"
BLUE = "#214E78"
BLUE_M = "#6C8EAA"
BLUE_L = "#E8EFF5"
BLUE_XL = "#F5F8FB"
PINK = "#C87879"
PINK_L = "#F5E6E7"
YELLOW = "#B89647"
YELLOW_L = "#F5EED8"
BROWN = "#956C50"
BROWN_L = "#F0E6DE"
GRAY = "#6D7780"
GRAY_L = "#CDD4D9"
GRAY_XL = "#F4F6F7"
WHITE = "#FFFFFF"


plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": FONT,
        "axes.unicode_minus": False,
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "savefig.facecolor": WHITE,
        "figure.facecolor": WHITE,
    }
)


def canvas(size: tuple[float, float]):
    fig, ax = plt.subplots(figsize=size)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")
    return fig, ax


def box(ax, x, y, w, h, text, *, fc=WHITE, ec=GRAY, lw=0.9, fs=8.4,
        weight="normal", color=INK, ha="center", va="center", pad=0.0,
        ls="-"):
    ax.add_patch(Rectangle((x, y), w, h, facecolor=fc, edgecolor=ec,
                           linewidth=lw, linestyle=ls, zorder=2))
    ax.text(x + w / 2 if ha == "center" else x + pad,
            y + h / 2 if va == "center" else y + h - pad,
            text, ha=ha, va=va, fontsize=fs, color=color,
            fontweight=weight, linespacing=1.16, zorder=3)


def section(ax, x, y, w, h, label, *, fc=BLUE_XL, ec=GRAY_L, accent=BLUE,
            fs=9.1):
    ax.add_patch(Rectangle((x, y), w, h, facecolor=fc, edgecolor=ec,
                           linewidth=0.8, zorder=0))
    ax.plot([x, x], [y, y + h], color=accent, linewidth=2.0, zorder=1)
    ax.text(x + 2.0, y + h - 2.4, label, ha="left", va="top",
            fontsize=fs, color=INK, fontweight="bold", zorder=3)


def orth_arrow(ax, points, *, color=INK, lw=1.0, head=7.0, ls="-"):
    """Draw a polyline and put one arrow head on its final segment."""
    xs, ys = zip(*points)
    ax.plot(xs, ys, color=color, linewidth=lw, linestyle=ls,
            solid_capstyle="butt", solid_joinstyle="miter", zorder=4)
    if len(points) >= 2:
        (x1, y1), (x2, y2) = points[-2], points[-1]
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops={"arrowstyle": "-|>", "color": color,
                                "lw": lw, "mutation_scale": head,
                                "shrinkA": 0, "shrinkB": 0,
                                "linestyle": ls}, zorder=5)


def save(fig, stem: str):
    base = FIG_DIR / stem
    fig.savefig(base.with_suffix(".svg"), format="svg", dpi=1200,
                bbox_inches="tight", pad_inches=0.04)
    fig.savefig(base.with_suffix(".png"), format="png", dpi=1200,
                bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)


def fig1_2():
    fig, ax = canvas((10.8, 7.2))
    ax.text(50, 96.5, "数据 → 方法 → 机制 → 结论", ha="center", va="center",
            fontsize=10.5, color=INK, fontweight="bold")

    stages = [
        (3, "数据重构与节点筛选", BLUE, BLUE_L,
         "会话记录审计\n15 min 代理负荷重构\n节点可用性质量门禁\n事件窗口统计"),
        (27.5, "LRE 关系与 MRG-GCN", BROWN, BROWN_L,
         "负荷耦合 / 行为共现 / 轮廓相似\n三类统计关系图与稀疏化\nTCN 时间编码 + 双层门控 GCN\n多步预测与对照实验"),
        (52, "MDP 三层机制诊断", PINK, PINK_L,
         "L1 门控干预：关系依赖\nL2 知识蒸馏：结构替代检验\nL3 四格溯源：误差归属\n诊断证据闭环"),
        (76.5, "预测支持探索", YELLOW, YELLOW_L,
         "TE 与 PCMCI+ 方向候选\n分层共形区间\n分层参数敏感度\n仅作预测支持探索"),
    ]
    w, y, h = 20.5, 58, 28
    for i, (x, title, edge, fill, body) in enumerate(stages, 1):
        box(ax, x, y, w, h, body, fc=WHITE, ec=edge, lw=1.0, fs=8.0)
        box(ax, x, y + h - 6.7, w, 6.7, title, fc=fill, ec=edge, lw=1.0,
            fs=8.0, weight="bold")
        ax.text(x + 1.2, y + h - 1.4, f"{i}", ha="left", va="top",
                fontsize=7.4, color=edge, fontweight="bold")
        if i < 4:
            orth_arrow(ax, [(x + w + 0.8, 72), (stages[i][0] - 0.8, 72)],
                       color=INK, lw=0.95, head=7)

    # Two independent contribution lines, explicitly attached to stages 2/3.
    box(ax, 27.5, 43.5, w, 8.5, "方法贡献\nLRE 三关系 + MRG-GCN 多步建模",
        fc=BROWN_L, ec=BROWN, lw=1.0, fs=7.7, weight="bold")
    box(ax, 52, 43.5, w, 8.5, "机制诊断贡献\nMDP：干预—蒸馏—四格溯源",
        fc=PINK_L, ec=PINK, lw=1.0, fs=7.7, weight="bold")
    orth_arrow(ax, [(37.75, 58), (37.75, 52.2)], color=BROWN, lw=0.9)
    orth_arrow(ax, [(62.25, 58), (62.25, 52.2)], color=PINK, lw=0.9)

    box(ax, 39, 32.5, 22, 6.2, "方法与诊断证据", fc=GRAY_XL, ec=GRAY,
        lw=0.9, fs=8.2, weight="bold")
    orth_arrow(ax, [(37.75, 43.5), (37.75, 36.0), (39, 36.0)],
               color=GRAY, lw=0.85)
    orth_arrow(ax, [(62.25, 43.5), (62.25, 36.0), (61, 36.0)],
               color=GRAY, lw=0.85)

    ax.plot([18, 82], [24.5, 24.5], color=GRAY_L, lw=0.8)
    ax.text(50, 22.5, "共同结论 / 边界", ha="center", va="center",
            fontsize=7.8, color=GRAY, fontweight="bold")
    ax.text(50, 18.3,
            "量化证据贯通；第5章用于预测支持探索，不承诺解决事件预测",
            ha="center", va="center", fontsize=7.6, color=INK)
    ax.text(50, 12.0, "测试集不参与关系图与阈值确定 · 结论按证据边界表述",
            ha="center", va="center", fontsize=7.0, color=GRAY)
    save(fig, "fig1_2_roadmap")


def fig2_10():
    fig, ax = canvas((11.2, 6.8))
    section(ax, 3, 54, 67, 38, "目标侧标签：事后评价时间轴",
            fc=BLUE_XL, ec="#B9CBD9", accent=BLUE)
    section(ax, 3, 13, 67, 38, "预测时可见冻结规则：部署时间轴",
            fc=PINK_L, ec="#E0BFC1", accent=PINK)

    # Upper track: target_event is evaluation-only.
    box(ax, 6, 68, 15, 9, "目标侧观测\ny(t+1:t+4)", fc=WHITE, ec=BLUE, fs=8.0)
    box(ax, 26, 65.5, 21, 14, "target_event\n标签事件窗口\n1.43% · 仅分层评价",
        fc=WHITE, ec=BLUE, lw=1.1, fs=7.9, weight="bold")
    box(ax, 53, 68, 14, 9, "分层评价", fc=WHITE, ec=BLUE, fs=8.0)
    orth_arrow(ax, [(21, 72.5), (26, 72.5)], color=BLUE, lw=1.0)
    orth_arrow(ax, [(47, 72.5), (53, 72.5)], color=BLUE, lw=1.0)
    ax.text(6, 59.5, "标签在预测后可见；不作为部署路由输入", ha="left", va="center",
            fontsize=7.0, color=GRAY)

    # Lower track: rule_trigger is the only deployable route signal.
    box(ax, 6, 27, 15, 9, "预测起点信息\nx(≤t)", fc=WHITE, ec=PINK, fs=8.0)
    box(ax, 26, 24.5, 21, 14, "rule_trigger\n冻结规则触发\n0.43% · 仅路由",
        fc=WHITE, ec=PINK, lw=1.1, fs=7.9, weight="bold")
    box(ax, 53, 27, 14, 9, "冻结规则路由", fc=WHITE, ec=PINK, fs=8.0)
    orth_arrow(ax, [(21, 31.5), (26, 31.5)], color=PINK, lw=1.0)
    orth_arrow(ax, [(47, 31.5), (53, 31.5)], color=PINK, lw=1.0)
    ax.text(6, 18.5, "阈值来自验证期并冻结；预测时只执行可见规则", ha="left", va="center",
            fontsize=7.0, color=GRAY)

    # The two definitions feed a compact cross-tab for diagnosis only.
    ax.text(85.5, 87.5, "交叉诊断", ha="center", va="center",
            fontsize=8.8, color=INK, fontweight="bold")
    x0, y0, cw, rh = 75, 61, 9, 8
    # 3 x 3 table: corner, two rule columns; two target rows.
    for r in range(3):
        for c in range(3):
            fc = GRAY_XL if r == 0 or c == 0 else WHITE
            box(ax, x0 + c * cw, y0 + (2 - r) * rh, cw, rh, "",
                fc=fc, ec=BLUE, lw=0.75)
    ax.text(x0 + cw * 1.5, y0 + rh * 2.5, "rule=1", ha="center", va="center", fontsize=6.9, color=INK)
    ax.text(x0 + cw * 2.5, y0 + rh * 2.5, "rule=0", ha="center", va="center", fontsize=6.9, color=INK)
    ax.text(x0 + cw * 0.5, y0 + rh * 1.5, "target=1", ha="center", va="center", fontsize=6.9, color=INK)
    ax.text(x0 + cw * 0.5, y0 + rh * 0.5, "target=0", ha="center", va="center", fontsize=6.9, color=INK)
    for c, v in enumerate(("11", "10"), 1):
        ax.text(x0 + cw * (c + 0.5), y0 + rh * 1.5, v, ha="center", va="center", fontsize=8.8, color=BLUE, fontweight="bold")
    for c, v in enumerate(("01", "00"), 1):
        ax.text(x0 + cw * (c + 0.5), y0 + rh * 0.5, v, ha="center", va="center", fontsize=8.8, color=PINK, fontweight="bold")
    orth_arrow(ax, [(36.5, 65.5), (71.5, 65.5), (75, 73)], color=BLUE, lw=0.9)
    orth_arrow(ax, [(36.5, 24.5), (70.5, 24.5), (70.5, 65), (75, 65)], color=PINK, lw=0.9)
    ax.text(85.5, 56.5, "仅描述两种口径的交叉\n不将其解释为分类器指标",
            ha="center", va="center", fontsize=6.8, color=GRAY, linespacing=1.2)
    ax.plot([3, 97], [8.5, 8.5], color=GRAY_L, lw=0.8)
    ax.text(50, 5.7, "target_event 仅用于分层评价；rule_trigger 仅用于冻结规则路由；两者不得混用",
            ha="center", va="center", fontsize=7.4, color=INK)
    save(fig, "fig2_10_dual_window_definition")


def load_four_cell_summary():
    """Use the正文口径：三种子四格 MAE 与 n×MAE 贡献均值。"""
    rows = []
    with FOUR_CELL_SUMMARY.open(newline="", encoding="utf-8") as f:
        rows.extend(csv.DictReader(f))
    order = ["target_event_triggered", "target_event_not_triggered",
             "stable_triggered", "stable_not_triggered"]
    by_cell = {r["cell"]: r for r in rows}
    if set(by_cell) != set(order):
        raise ValueError(f"four-cell summary rows mismatch: {sorted(by_cell)}")
    expected_n = [235, 9925, 2825, 699375]
    data = []
    for cell, n in zip(order, expected_n):
        row = by_cell[cell]
        if int(row["n"]) != n:
            raise ValueError(f"{cell}: expected n={n}, got {row['n']}")
        data.append({"cell": cell, "n": n, "sample": float(row["sample_percent"]),
                     "mae": float(row["mae_mean"]),
                     "contrib": float(row["contribution_percent_mean"])})
    return data


def bar_panel(ax, x, y, w, values, labels, color, *, max_value=100):
    # The section heading is drawn once by ``section``.  Keep a compact
    # plotting area below it so 0 and 100% remain visibly separated.
    xbar, wbar = x + 10, w - 12
    for i, (label, value) in enumerate(zip(labels, values)):
        yy = y + 43 - i * 11
        ax.text(x + 9, yy + 1.8, label, ha="right", va="center",
                fontsize=6.4, color=INK)
        ax.plot([xbar, xbar + wbar], [yy, yy], color=GRAY_L, lw=0.7, zorder=1)
        length = max(0.0, min(max_value, value)) / max_value * wbar
        ax.add_patch(Rectangle((xbar, yy - 1.8), length, 3.6,
                               facecolor=color, edgecolor=color, linewidth=0.5, zorder=2))
        value_text = "<0.1%" if value < 0.05 else f"{value:.1f}%"
        ax.text(xbar + max(length, 0.4) + 0.8, yy, value_text,
                ha="left", va="center", fontsize=6.4, color=color,
                fontweight="bold")
    ax.text(xbar, y + 3.5, "0", ha="left", va="center", fontsize=6.0, color=GRAY)
    ax.text(xbar + wbar, y + 3.5, "100%", ha="right", va="center", fontsize=6.0, color=GRAY)


def fig4_4():
    data = load_four_cell_summary()
    fig, ax = canvas((11.4, 6.6))
    section(ax, 3, 17, 42, 72, "(A) 四格交叉分层", fc=GRAY_XL, ec=GRAY_L, accent=BLUE)
    section(ax, 48, 17, 22, 72, "(B) 测试键组成", fc=GRAY_XL, ec=GRAY_L, accent=BLUE_M)
    section(ax, 73, 17, 24, 72, "(C) n×MAE 贡献", fc=GRAY_XL, ec=GRAY_L, accent=BROWN)

    x0, y0, cw, ch = 15, 35, 13, 19
    ax.text(x0 + cw * 0.5, 78, "rule=1", ha="center", va="center", fontsize=7.1, color=INK)
    ax.text(x0 + cw * 1.5, 78, "rule=0", ha="center", va="center", fontsize=7.1, color=INK)
    ax.text(13.0, y0 + ch * 1.5, "标签事件", ha="right", va="center", fontsize=7.0, color=INK)
    ax.text(13.0, y0 + ch * 0.5, "标签非事件", ha="right", va="center", fontsize=7.0, color=INK)
    fills = [PINK_L, BROWN_L, BLUE_L, WHITE]
    for idx, (row, fill) in enumerate(zip(data, fills)):
        rr, cc = divmod(idx, 2)
        xx, yy = x0 + cc * cw, y0 + (1 - rr) * ch
        txt = f"n = {row['n']:,}\nMAE {row['mae']:.4f}\n样本 {row['sample']:.3f}%\n贡献 {row['contrib']:.1f}%"
        box(ax, xx, yy, cw, ch, txt, fc=fill, ec=BLUE if idx < 2 else GRAY,
            lw=0.85, fs=6.4, weight="bold" if idx == 1 else "normal")
    ax.text(28, 29.5, "规则触发状态", ha="center", va="center", fontsize=6.8, color=GRAY)
    labels = ["事×触", "事×未", "非×触", "非×未"]
    bar_panel(ax, 48, 23, 22, [d["sample"] for d in data], labels, BLUE_M)
    bar_panel(ax, 73, 23, 24, [d["contrib"] for d in data], labels, BROWN)
    ax.plot([3, 97], [11.5, 11.5], color=GRAY_L, lw=0.8)
    ax.text(50, 8.0, "原正式 MRG-GCN 三种子均值 · 总预测键 712,360 · 贡献占比 = (n × MAE) / Σ(n × MAE)",
            ha="center", va="center", fontsize=7.0, color=INK)
    save(fig, "fig4_4_four_cell")


def fig5_6():
    fig, ax = canvas((11.6, 6.8))
    section(ax, 3, 20, 53, 72, "验证期校准", fc=BLUE_XL, ec="#B9CBD9", accent=BLUE)
    section(ax, 60, 20, 37, 72, "测试期区间", fc=GRAY_XL, ec=GRAY_L, accent=GRAY)

    top = [(6, "冻结主模型"), (18, "验证集前向"), (30, "绝对残差\nr=|y−ŷ|"), (42, "按冻结规则\n分层")]
    for x, text in top:
        box(ax, x, 77, 10, 9, text, fc=WHITE, ec=BLUE, fs=7.0,
            weight="bold" if "冻结" in text else "normal")
    for (x1, _), (x2, _) in zip(top[:-1], top[1:]):
        orth_arrow(ax, [(x1 + 10, 81.5), (x2, 81.5)], color=BLUE, lw=0.85)

    # Split from the grouping node into two independent calibration tracks.
    box(ax, 7, 51, 12, 9, "rule_trigger=1\n事件层", fc=PINK_L, ec=PINK, fs=6.9, weight="bold")
    box(ax, 22, 51, 12, 9, "90%分位数\nα=0.1", fc=WHITE, ec=PINK, fs=6.9)
    box(ax, 37, 51, 12, 9, "q_evt", fc=PINK_L, ec=PINK, fs=8.0, weight="bold")
    orth_arrow(ax, [(19, 55.5), (22, 55.5)], color=PINK, lw=0.85)
    orth_arrow(ax, [(34, 55.5), (37, 55.5)], color=PINK, lw=0.85)

    box(ax, 7, 31, 12, 9, "rule_trigger=0\n稳定层", fc=BLUE_L, ec=BLUE, fs=6.9, weight="bold")
    box(ax, 22, 31, 12, 9, "逐节点90%分位数\nα=0.1", fc=WHITE, ec=BLUE, fs=6.6)
    box(ax, 37, 31, 12, 9, "q_stable,n", fc=BLUE_L, ec=BLUE, fs=7.3, weight="bold")
    orth_arrow(ax, [(19, 35.5), (22, 35.5)], color=BLUE, lw=0.85)
    orth_arrow(ax, [(34, 35.5), (37, 35.5)], color=BLUE, lw=0.85)
    orth_arrow(ax, [(47, 77), (47, 64), (13, 64), (13, 60)], color=BLUE, lw=0.85)
    orth_arrow(ax, [(47, 64), (47, 44), (13, 44), (13, 40)], color=BLUE, lw=0.85)

    # Both calibrated half-widths arrive at one selector; the selector is also
    # fed by the frozen, prediction-time-visible route signal on the right.
    box(ax, 72, 47, 18, 9, "选择区间半宽 q", fc=YELLOW_L, ec=YELLOW, fs=7.4, weight="bold")
    orth_arrow(ax, [(49, 55.5), (58, 55.5), (58, 53), (72, 53)], color=PINK, lw=0.85)
    orth_arrow(ax, [(49, 35.5), (63, 35.5), (63, 49), (72, 49)], color=BLUE, lw=0.85)

    box(ax, 68, 77, 20, 9, "测试输入", fc=WHITE, ec=GRAY, fs=8.0, weight="bold")
    box(ax, 63, 64, 13, 8, "冻结模型预测", fc=WHITE, ec=GRAY, fs=7.0)
    box(ax, 82, 64, 13, 8, "冻结规则路由", fc=YELLOW_L, ec=YELLOW, fs=7.0, weight="bold")
    box(ax, 63, 52, 13, 7, "ŷ", fc=WHITE, ec=GRAY, fs=10.0, weight="bold")
    box(ax, 68, 25, 23, 10, "预测区间\nŷ ± q", fc=BLUE_L, ec=BLUE, fs=8.3, weight="bold")
    orth_arrow(ax, [(78, 77), (69.5, 77), (69.5, 72)], color=GRAY, lw=0.85)
    orth_arrow(ax, [(78, 77), (88.5, 77), (88.5, 72)], color=GRAY, lw=0.85)
    orth_arrow(ax, [(69.5, 64), (69.5, 59)], color=GRAY, lw=0.85)
    orth_arrow(ax, [(88.5, 64), (88.5, 58), (90, 58)], color=YELLOW, lw=0.85)
    orth_arrow(ax, [(90, 58), (90, 51.5)], color=YELLOW, lw=0.85)
    orth_arrow(ax, [(69.5, 52), (69.5, 40), (78, 40), (78, 35)], color=GRAY, lw=0.85)
    orth_arrow(ax, [(81, 47), (81, 35)], color=BLUE, lw=0.85)
    ax.text(78.5, 42, "只按可见规则选择 q", ha="center", va="center", fontsize=6.3, color=YELLOW)

    box(ax, 8, 22, 43, 5.5,
        "target_event：仅用于事后评价，不接入测试期部署路由",
        fc=WHITE, ec=GRAY_L, lw=0.8, fs=6.8, color=GRAY, ls="--")
    ax.plot([3, 97], [13.5, 13.5], color=GRAY_L, lw=0.8)
    ax.text(50, 9.3, "冻结主模型 → 验证集残差校准 → 冻结规则路由 → 测试期输出区间",
            ha="center", va="center", fontsize=7.2, color=INK)
    save(fig, "fig5_6_conformal_method")


def main():
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig1_2()
    fig2_10()
    fig4_4()
    fig5_6()
    print("redrawn: fig1_2_roadmap, fig2_10_dual_window_definition, fig4_4_four_cell, fig5_6_conformal_method")


if __name__ == "__main__":
    main()
