"""导师审阅版重绘：图 3-5、3-6、3-7、4-4、5-4、5-5、5-6。

设计原则：每张图保留一个主问题，并用第二/第三面板补充互不重复的证据。
所有数值均从现有实验工件读取，不补造正式结果；图 5-6 仍明确为单种子快速筛选。
输出：同名 SVG 矢量图 + 1200 DPI PNG。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.gridspec import GridSpec
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter, LogFormatterSciNotation

sys.path.insert(0, str(Path.home() / ".claude/skills/scipilot-figure-skill/scripts"))
try:
    from export_figure import export_figure  # noqa: E402
    from setup_style import setup_style  # noqa: E402
except ImportError:  # 无 skill 环境回退
    from _skill_compat import export_figure, setup_style  # noqa: E402

sys.path.insert(0, "src")

FIG_DIR = Path("outputs/figures")
FIG_DIR.mkdir(parents=True, exist_ok=True)
setup_style(journal="general", lang="zh")

BLUE = "#2C5F8A"
BLUE_L = "#8EABC0"
ORANGE = "#D08A3C"
ORANGE_L = "#E6C49E"
GRAY_D = "#404040"
GRAY_M = "#808080"
GRAY_L = "#C8C8C8"
GRAY_XL = "#E6E9EC"
RED = "#B05A4A"
GREEN = "#597A62"

def load_node_ids() -> list[str]:
    """Read the ordered node labels without importing the training stack."""
    with np.load("data/processed/SG-DATA-005-primary-tensor.npz", allow_pickle=False) as data:
        return [str(node_id) for node_id in data["node_ids"].tolist()]


def final(fig, name: str, size: tuple[float, float]) -> None:
    export_figure(
        fig,
        basename=str(FIG_DIR / name),
        formats=["svg", "png"],
        # Tight cropping leaves fig5_8 narrower than its nominal canvas. At
        # the thesis's 14.19 cm placement width, 1300 export DPI keeps its
        # effective raster density above 1200 PPI without changing geometry.
        dpi=1300 if name == "fig5_8_quantile_per_node" else 1200,
        size_inches=size,
        grayscale_preview=False,
    )
    # Matplotlib 把多行 path 数据写成带行尾空格的行；清理后 SVG 才能通过
    # 仓库的空白检查（git diff --check）。
    svg_path = FIG_DIR / f"{name}.svg"
    svg_path.write_text(
        "\n".join(line.rstrip() for line in svg_path.read_text(encoding="utf-8").splitlines()) + "\n",
        encoding="utf-8",
    )
    print(f"  ✅ {name}")


def clean_ax(ax, grid_axis: str = "y") -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(GRAY_D)
    ax.spines["bottom"].set_color(GRAY_D)
    ax.tick_params(labelsize=8, colors=GRAY_D)
    if grid_axis:
        ax.grid(axis=grid_axis, color=GRAY_L, lw=0.55, alpha=0.72, zorder=0)


def panel_label(ax, label: str, text: str) -> None:
    ax.text(-0.12, 1.06, label, transform=ax.transAxes, ha="left", va="bottom",
            fontsize=11, fontweight="bold", color=GRAY_D)
    ax.text(-0.05, 1.06, text, transform=ax.transAxes, ha="left", va="bottom",
            fontsize=8.8, color=GRAY_D)


def _mean_std(values: list[np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
    arr = np.asarray(values, dtype=float)
    return arr.mean(axis=0), arr.std(axis=0, ddof=1)


# fig5_7（共形覆盖率）的生成已迁移至 scripts/figures/batch6_te_coverage_enhance.py
# 的 fig5_7_coverage()。本脚本原先也写同名文件但产出不同内容（缺 A 面板橙线），
# 运行它会把正确版本静默覆盖，故删除。


def redraw_fig5_5() -> None:
    c = json.load(open("outputs/analysis/conformal_prediction/conformal_summary.json"))
    seeds = c["per_seed"]
    labels = load_node_ids()
    qg, qg_sd = _mean_std([np.asarray(s["q_global_per_node"]) for s in seeds])
    qs, qs_sd = _mean_std([np.asarray(s["q_stable_per_node"]) for s in seeds])
    qe, qe_sd = _mean_std([np.asarray(s["q_event_per_node"]) for s in seeds])
    ratio_all = np.asarray([np.asarray(s["q_event_per_node"]) /
                            np.maximum(np.asarray(s["q_global_per_node"]), 1e-12)
                            for s in seeds])
    ratio = ratio_all.mean(axis=0)
    ratio_sd = ratio_all.std(axis=0, ddof=1)
    order = np.argsort(ratio)[::-1]

    # 画布取论文显示尺寸：版心宽 14.66 cm = 5.77 in，图按 5.59 in 排版，
    # 故 figsize 直接等于纸面尺寸，fontsize 参数即为纸面字号。
    # 2026-10-26 重构（方案 8-甲）：双面板合并为单面板。原 A 中"全局"与
    # "规则未触发层"逐节点几乎重合（冗余双列），只保留全局（它也是倍数口径
    # 的分母，与正文倍数一致）；原 B 的倍数森林改为逐节点的点→统一值引导线
    # + 几何中点倍数标注，原 A 中蓝线与点云之间的三个数量级空旷区由此
    # 变成信息通道。
    fig = plt.figure(figsize=(5.59, 3.55), constrained_layout=False)
    ax = fig.add_axes([0.150, 0.155, 0.810, 0.700])

    y = np.arange(len(labels))
    qe_mean = qe.mean()
    # 统一事件层：蓝色竖线 + 跨种子 SD 淡色带
    ax.axvspan(max(qe_mean - qe_sd.mean(), 1e-5), qe_mean + qe_sd.mean(),
               color=BLUE, alpha=0.10, zorder=0)
    ax.axvline(qe_mean, color=BLUE, lw=1.6, ls="-", zorder=1)
    for yi, idx in zip(y, order):
        # 引导线跨越点与统一值之间的量级差；倍数标在几何中点（对数轴中点），
        # 自然形成一列，且不与点/线重叠
        ax.plot([qg[idx], qe_mean], [yi, yi], color=GRAY_L, lw=0.8,
                ls=(0, (1, 2)), zorder=2)
        ax.text(float(np.sqrt(qg[idx] * qe_mean)), yi, f"×{ratio[idx]:,.0f}",
                ha="center", va="center", fontsize=7.3, color=GRAY_D,
                bbox=dict(facecolor="white", edgecolor="none", alpha=0.85,
                          pad=0.4), zorder=3)
    ax.errorbar(qg[order], y, xerr=qg_sd[order], fmt="o", ms=5.2, mfc="white",
                mec=GRAY_D, ecolor=GRAY_D, capsize=2.0, lw=0.8, zorder=4)
    ax.set_xscale("log")
    ax.set_xlim(8e-5, 1.05)
    ax.xaxis.set_major_formatter(LogFormatterSciNotation())
    ax.set_yticks(y)
    ax.set_yticklabels([labels[i] for i in order], fontsize=7.8)
    ax.invert_yaxis()
    ax.set_xlabel("90% 残差分位数（kWh/15 min，对数轴）", fontsize=8.5)
    clean_ax(ax, "x")
    # 图例放顶部独立区域；统一值数值并入样张文字，不再另设面板标题
    fig.legend(handles=[Line2D([0], [0], marker="o", color="none",
                               markerfacecolor="white", markeredgecolor=GRAY_D,
                               markersize=5.3,
                               label="全局分位数（逐节点）"),
                        Line2D([0], [0], color=BLUE, lw=1.6,
                               label=f"规则触发层（统一值 ≈ {qe_mean:.2f}）")],
               fontsize=7.3, frameon=False, ncol=2, loc="upper center",
               bbox_to_anchor=(0.50, 0.985), columnspacing=1.2,
               handletextpad=0.35)
    final(fig, "fig5_8_quantile_per_node", (5.59, 3.55))


def redraw_fig5_6() -> None:
    napl = json.load(open("outputs/analysis/variant_quick_check/variant_napl.json"))
    gmi = json.load(open("outputs/analysis/variant_quick_check/variant_gate-mi.json"))
    base = float(napl["baseline_val_mae"])
    names = ["StaticGraph 基线", "NAPL\n节点差异化参数", "Gate-MI\n门控专业化"]
    vals = np.array([base, napl["val_mae"], gmi["val_mae"]], dtype=float)
    rel = (vals / base - 1.0) * 100.0
    colors = [GRAY_D, BLUE, ORANGE]

    fig = plt.figure(figsize=(10.2, 4.85), constrained_layout=False)
    gs = GridSpec(1, 2, figure=fig, width_ratios=[1.24, 1.0],
                  left=0.105, right=0.975, bottom=0.20, top=0.79, wspace=0.40)

    ax = fig.add_subplot(gs[0, 0])
    y = np.arange(3)[::-1]
    for yi, name, value, color in zip(y, names, vals, colors):
        ax.hlines(yi, 0, value, color=GRAY_XL, lw=3.0, zorder=1)
        ax.scatter(value, yi, s=75, facecolor="white" if yi == y[0] else color,
                   edgecolor=color, linewidth=1.5, zorder=4)
        ax.annotate(f"{value:.5f}", xy=(value, yi), xytext=(7, 0),
                    textcoords="offset points", va="center", fontsize=8.2,
                    color=GRAY_D,
                    bbox=dict(facecolor="white", edgecolor="none", alpha=0.84, pad=0.35))
    ax.axvline(base, color=GRAY_M, lw=1.0, ls="--", zorder=2)
    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=8.5)
    ax.set_xlim(0, 0.0178)
    ax.set_xlabel("验证集 MAE（kWh/15 min）", fontsize=8.8)
    clean_ax(ax, "x")
    panel_label(ax, "A", "绝对性能：验证集 MAE")
    fig.text(0.33, 0.925, "虚线：StaticGraph 基线参考；数值来自 seed-2024 快速验证",
             ha="center", va="center", fontsize=7.0, color=GRAY_M)

    ax = fig.add_subplot(gs[0, 1])
    y = np.arange(3)[::-1]
    for yi, name, delta, color in zip(y, names, rel, colors):
        ax.barh(yi, delta, height=0.45, color=color, alpha=0.88,
                edgecolor="white", linewidth=0.5, zorder=3)
        if delta < -0.4:
            # 负值标签放在条形内部，避免侵入左侧类别文字区域。
            ax.text(delta / 2.0, yi, f"{delta:+.1f}%", ha="center", va="center",
                    fontsize=8.5, color="white", fontweight="bold")
        else:
            ax.text(delta + 0.12, yi, f"{delta:+.1f}%", ha="left", va="center",
                    fontsize=8.5, color=color, fontweight="bold",
                    bbox=dict(facecolor="white", edgecolor="none", alpha=0.82, pad=0.25))
    ax.axvline(0, color=GRAY_D, lw=1.0)
    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=8.5)
    ax.set_xlim(-7.0, 1.0)
    ax.set_xlabel("相对基线变化（%）", fontsize=8.8)
    clean_ax(ax, "x")
    panel_label(ax, "B", "方向筛选：相对基线变化")
    fig.text(0.98, 0.95, "单种子（2024）· 快速验证集筛选材料 · 不作正式结论",
             ha="right", va="center", fontsize=7.0, color=GRAY_M)
    # 数据口径和单种子边界由图注承接；图面底部不再放密集脚注。
    final(fig, "fig5_6_mechanism_enhance", (10.2, 4.85))


def redraw_fig4_4() -> None:
    m = json.load(open("outputs/experiments/SG-EXP-004/20260731-102456/seed-2024/metrics.json"))
    fc = m["four_cell"]["cells"]
    cells = [
        ("target_event_triggered", "标签事件\n规则触发", BLUE),
        ("target_event_not_triggered", "标签事件\n规则未触发", ORANGE),
        ("stable_triggered", "标签非事件\n规则触发", GRAY_M),
        ("stable_not_triggered", "标签非事件\n规则未触发", GRAY_L),
    ]
    matrix = np.array([[fc["target_event_triggered"]["mae"], fc["target_event_not_triggered"]["mae"]],
                       [fc["stable_triggered"]["mae"], fc["stable_not_triggered"]["mae"]]])
    counts = np.array([[fc["target_event_triggered"]["count"], fc["target_event_not_triggered"]["count"]],
                       [fc["stable_triggered"]["count"], fc["stable_not_triggered"]["count"]]])
    rmse = np.array([[fc["target_event_triggered"]["rmse"], fc["target_event_not_triggered"]["rmse"]],
                     [fc["stable_triggered"]["rmse"], fc["stable_not_triggered"]["rmse"]]])
    total = counts.sum()

    # 上下两个等权部分：A 回答“哪一格误差大”，B 回答“规则触发样本由什么组成”。
    fig = plt.figure(figsize=(9.4, 6.5))

    # A：四格 MAE 主图，单元内只保留主指标，避免 RMSE/n/百分比堆叠。
    ax = fig.add_axes([0.11, 0.56, 0.76, 0.32])
    im = ax.imshow(matrix, cmap="Blues", vmin=0, vmax=0.30, aspect="auto")
    for pos in [-0.5, 0.5, 1.5]:
        ax.axhline(pos, color="white", lw=2.4)
        ax.axvline(pos, color="white", lw=2.4)
    for i in range(2):
        for j in range(2):
            text_color = "white" if matrix[i, j] > 0.16 else GRAY_D
            ax.text(j, i, f"{matrix[i, j]:.4f}", ha="center", va="center",
                    fontsize=17, fontweight="bold", color=text_color)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["规则触发", "规则未触发"], fontsize=9.5)
    ax.set_yticks([0, 1])
    ax.set_yticklabels(["标签事件", "标签非事件"], fontsize=9.5)
    ax.tick_params(length=0)
    ax.set_xlabel("单元 MAE（kWh/15 min；单种子口径见图注）", fontsize=9.0, labelpad=6)
    cax = fig.add_axes([0.89, 0.56, 0.022, 0.32])
    cbar = fig.colorbar(im, cax=cax)
    cbar.set_label("MAE（kWh/15 min）", fontsize=8.0)
    cbar.ax.tick_params(labelsize=7)
    panel_label(ax, "A", "事件标签 × 规则触发：单元 MAE")

    # B：规则触发覆盖了什么，直接显示两种样本集合的组成比例和基数。
    ax = fig.add_axes([0.11, 0.15, 0.82, 0.26])
    bars = [
        ("标签事件样本", [counts[0, 0], counts[0, 1]], [BLUE, ORANGE],
         ["触发", "漏触发"]),
        ("规则触发样本", [counts[0, 0], counts[1, 0]], [BLUE, GRAY_M],
         ["标签事件", "标签非事件"]),
    ]
    y = np.arange(2)[::-1]
    left = np.zeros(2)
    for seg_i in range(2):
        vals = np.array([bars[row][1][seg_i] for row in range(2)])
        color = [bars[row][2][seg_i] for row in range(2)]
        ax.barh(y, vals, left=left, color=color, height=0.42,
                edgecolor="white", linewidth=0.6)
        for pos_i, (yi, v, lft) in enumerate(zip(y, vals, left)):
            # vals 的第 pos_i 项对应 bars 的同一行；y 仅负责把两行上下反转。
            # 这里不能用 1-pos_i，否则会把两条堆叠条的组成比例交叉标注。
            row_i = pos_i
            fraction = v / (v + (bars[row_i][1][1 - seg_i]))
            if fraction >= 0.15:
                ax.text(lft + v / 2, yi, f"{fraction:.1%}",
                        ha="center", va="center", fontsize=7.2,
                        color="white" if seg_i == 0 else GRAY_D)
            else:
                # 极窄色块不把文字塞进色块内部，段外标注并以短线指回。
                ax.annotate(f"{fraction:.1%}", xy=(lft + v / 2, yi),
                            xytext=(lft + v + 150, yi - 0.17),
                            ha="left", va="center", fontsize=6.8, color=GRAY_D,
                            arrowprops=dict(arrowstyle="-", color=GRAY_D, lw=0.55))
        left += vals
    ax.set_yticks(y)
    ax.set_yticklabels([b[0] for b in bars[::-1]], fontsize=9.0)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, pos: f"{v / 1000:.0f}k"))
    ax.set_xlabel("样本数（堆叠显示组成）", fontsize=9.0, labelpad=3)
    ax.set_ylim(-0.48, 1.48)
    ax.text(0.0, 1.23, "蓝=事件触发   橙=事件漏触发   灰=非事件触发",
            transform=ax.transAxes, fontsize=7.5, color=GRAY_D, ha="left")
    ax.text(1.0, 1.23, f"总样本 n={total:,}", transform=ax.transAxes,
            fontsize=7.5, color=GRAY_M, ha="right")
    clean_ax(ax, "x")
    panel_label(ax, "B", "规则路由覆盖：样本组成与基数")
    final(fig, "fig4_4_four_cell", (9.4, 6.5))


def _training_logs():
    logs = {}
    for seed in ["2024", "2025", "2026"]:
        path = next(Path("outputs/experiments/SG-EXP-004").glob(f"*/seed-{seed}/training_log.csv"))
        logs[seed] = pd.read_csv(path)
    return logs


def redraw_fig3_5() -> None:
    logs = _training_logs()
    colors = {"2024": BLUE, "2025": GRAY_D, "2026": ORANGE}
    styles = {"2024": "-", "2025": "--", "2026": "-."}
    best = {}
    for seed, df in logs.items():
        bi = df["validation_mae_scaled"].idxmin()
        best[seed] = (int(df.loc[bi, "epoch"]), float(df.loc[bi, "validation_mae_scaled"]),
                      int(df["epoch"].iloc[-1]), float(df["validation_mae_scaled"].iloc[-1]))

    fig = plt.figure(figsize=(9.2, 4.25), constrained_layout=True)
    gs = GridSpec(1, 2, figure=fig, width_ratios=[1.7, 1.0], wspace=0.32)
    ax = fig.add_subplot(gs[0, 0])
    all_epochs = []
    for seed, df in logs.items():
        color = colors[seed]
        ax.plot(df["epoch"], df["validation_mae_scaled"], color=color,
                ls=styles[seed], lw=1.7, label=f"{seed} 运行", zorder=3)
        bi, bv, last_epoch, last_val = best[seed]
        ax.scatter(bi, bv, s=58, marker="*", color=color, edgecolor="white",
                   linewidth=0.5, zorder=5)
        ax.scatter(last_epoch, last_val, s=34, marker="D", color=color,
                   edgecolor="white", linewidth=0.5, zorder=5)
        ax.axvline(last_epoch, color=color, lw=0.65, ls=":", alpha=0.35, zorder=1)
        all_epochs.append(last_epoch)
    ax.set_xlabel("训练轮次（epoch）", fontsize=8.8)
    ax.set_ylabel("验证 MAE（标准化尺度）", fontsize=8.8)
    ax.set_xlim(0, max(all_epochs) + 2)
    ax.set_ylim(0.014, 0.057)
    ax.legend(fontsize=7.4, frameon=False, ncol=3, loc="upper right")
    ax.text(0.02, 0.04, "★ 最佳验证点   ◆ 最后一轮   · 运行日志停止轮次",
            transform=ax.transAxes, fontsize=7.0, color=GRAY_M)
    clean_ax(ax, "y")
    panel_label(ax, "A", "训练轨迹：最佳点与日志末轮")

    ax = fig.add_subplot(gs[0, 1])
    y = np.arange(3)[::-1]
    for yi, seed in zip(y, ["2024", "2025", "2026"]):
        be, bv, le, lv = best[seed]
        color = colors[seed]
        ax.plot([bv, lv], [yi, yi], color=GRAY_L, lw=2.4, zorder=2)
        ax.scatter(bv, yi, s=62, marker="*", color=color, edgecolor="white",
                   linewidth=0.5, zorder=4)
        ax.scatter(lv, yi, s=38, marker="D", color=color, edgecolor="white",
                   linewidth=0.5, zorder=4)
        delta = lv - bv
        ax.text(max(bv, lv) + 0.00012, yi, f"{lv:.4f}", va="center",
                fontsize=7.0, color=GRAY_D)
    ax.set_yticks(y)
    ax.set_yticklabels([f"{s} 运行" for s in ["2024", "2025", "2026"]], fontsize=8.0)
    ax.set_xlim(0.0145, 0.0205)
    ax.set_xlabel("验证 MAE（标准化尺度）", fontsize=8.4)
    # 形状含义已经在 A 面板的说明中给出；B 面板不再额外放图例，
    # 避免图例覆盖末轮点及其数值标签。
    clean_ax(ax, "x")
    panel_label(ax, "B", "训练结果：最佳与末轮差异")
    final(fig, "fig3_10_training_curve", (9.2, 4.25))


def redraw_fig3_6() -> None:
    data = json.load(open("outputs/analysis/bootstrap_significance.json"))
    label_map = {
        "TCN - StaticGraph": "StaticGraph\nvs TCN",
        "StaticGraph - AdaptiveGraph": "AdaptiveGraph\nvs StaticGraph",
        "AdaptiveGraph - EventResidual": "EventResidual\nvs AdaptiveGraph",
        "StaticGraph - MLP": "MLP\nvs StaticGraph",
        "TCN - MLP": "MLP\nvs TCN",
        "AdaptiveGraph - no_event_gate": "no-event-gate\nvs AdaptiveGraph",
    }
    groups = [("global", "全局窗口", "2.14M"), ("event_window", "事件窗口", "30,480")]
    fig = plt.figure(figsize=(8.4, 5.05), constrained_layout=False)
    gs = GridSpec(2, 1, figure=fig, height_ratios=[1.0, 1.08],
                  left=0.24, right=0.975, bottom=0.15, top=0.90, hspace=0.60)
    for row, (window, title, n_text) in enumerate(groups):
        ax = fig.add_subplot(gs[row, 0])
        rows = []
        for comp in data["comparisons"]:
            if window in comp["pooled"]:
                p = comp["pooled"][window]
                rows.append((label_map.get(comp["name"], comp["name"]),
                             p["observed_diff"], p["ci_lower"], p["ci_upper"],
                             p["p_value_one_sided"]))
        rows = rows[::-1]
        yy = np.arange(len(rows))
        for yi, (label, diff, lo, hi, pval) in enumerate(rows):
            color = BLUE if diff > 0 else GRAY_M
            ax.errorbar(diff, yi, xerr=[[diff - lo], [hi - diff]], fmt="o",
                        ms=5.7, mfc=color, mec=color, ecolor=GRAY_D,
                        capsize=3.0, lw=1.0, zorder=4)
            ax.annotate(f"{diff:+.4f}", xy=(diff, yi), xytext=(6, 0),
                        textcoords="offset points", va="center", ha="left",
                        fontsize=6.9, color=GRAY_D,
                        bbox=dict(facecolor="white", edgecolor="none", alpha=0.84, pad=0.5))
        ax.axvline(0, color=GRAY_D, lw=1.0, zorder=2)
        ax.set_yticks(yy)
        ax.set_yticklabels([r[0] for r in rows], fontsize=7.1, linespacing=0.95)
        if window == "global":
            ax.set_xlim(-0.010, 0.020)
        else:
            ax.set_xlim(-0.042, 0.041)
        ax.set_xlabel("MAE 差：后者 − 前者（kWh/15 min）\n"
                      "（正值 = 前者误差更低；比较对象见纵轴）", fontsize=7.9)
        ax.text(0.02, 0.92, f"pooled n={n_text}", transform=ax.transAxes,
                ha="left", va="top", fontsize=7.0, color=GRAY_M,
                bbox=dict(facecolor="white", edgecolor="none", alpha=0.85, pad=0.4))
        clean_ax(ax, "x")
        panel_label(ax, "AB"[row], f"{title}：Bootstrap 森林图")
    final(fig, "fig3_9_bootstrap_difference", (8.4, 5.05))


def redraw_fig3_7() -> None:
    logs = _training_logs()
    colors = {"2024": BLUE, "2025": GRAY_D, "2026": ORANGE}
    styles = {"2024": "-", "2025": "--", "2026": "-."}
    fig = plt.figure(figsize=(8.4, 5.15), constrained_layout=False)
    gs = GridSpec(2, 1, figure=fig, height_ratios=[1.25, 1.0],
                  left=0.13, right=0.975, bottom=0.10, top=0.90, hspace=0.16)
    ax = fig.add_subplot(gs[0, 0])
    series = []
    for seed, df in logs.items():
        alpha = df["adaptive_graph_alpha"].to_numpy()
        epochs = df["epoch"].to_numpy()
        series.append((epochs, alpha))
        ax.plot(epochs, alpha, color=colors[seed], ls=styles[seed], lw=1.7,
                label=f"{seed} 运行", zorder=3)
        best_i = df["validation_mae_scaled"].idxmin()
        ax.scatter(df.loc[best_i, "epoch"], df.loc[best_i, "adaptive_graph_alpha"],
                   marker="*", s=52, color=colors[seed], edgecolor="white",
                   linewidth=0.45, zorder=5)
        ax.scatter(epochs[-1], alpha[-1], marker="D", s=30, color=colors[seed],
                   edgecolor="white", linewidth=0.45, zorder=5)
    # 各 epoch 的跨种子范围，短运行用末值延伸只用于显示范围，不做额外推断。
    max_len = max(len(a) for _, a in series)
    aligned = np.full((len(series), max_len), np.nan)
    for i, (_, a) in enumerate(series):
        aligned[i, :len(a)] = a
    epochs = np.arange(1, max_len + 1)
    ax.fill_between(epochs, np.nanmin(aligned, axis=0), np.nanmax(aligned, axis=0),
                    color=BLUE_L, alpha=0.12, zorder=1)
    ax.axhline(0.20, color=GRAY_L, lw=0.9, ls=":")
    ax.set_xlabel("训练轮次（epoch）", fontsize=8.8)
    ax.set_ylabel("图混合权重 α = σ(w)", fontsize=8.8)
    ax.set_xlim(0, max_len + 1)
    ax.set_ylim(0.14, 0.48)
    ax.legend(fontsize=7.4, frameon=False, ncol=3, loc="upper right")
    clean_ax(ax, "y")
    panel_label(ax, "A", "训练轨迹：固定图/自适应图混合")

    ax = fig.add_subplot(gs[1, 0])
    stages = ["初始", "最佳验证点", "日志末轮"]
    xs = np.arange(3)
    for seed in ["2024", "2025", "2026"]:
        df = logs[seed]
        best_i = df["validation_mae_scaled"].idxmin()
        vals = [float(df["adaptive_graph_alpha"].iloc[0]),
                float(df.loc[best_i, "adaptive_graph_alpha"]),
                float(df["adaptive_graph_alpha"].iloc[-1])]
        ax.plot(xs, vals, color=colors[seed], lw=1.35, marker="o", ms=4.5,
                label=f"{seed} 运行", zorder=3)
    ax.set_xticks(xs)
    ax.set_xticklabels(stages, fontsize=7.8)
    ax.set_ylim(0.14, 0.48)
    ax.set_ylabel("α", fontsize=8.8)
    clean_ax(ax, "y")
    panel_label(ax, "B", "阶段摘要：三种子终值与最佳点")
    final(fig, "fig3_12_alpha_convergence", (8.4, 5.15))


if __name__ == "__main__":
    print("=== 批次 9：主文 4 张图重绘 ===")
    redraw_fig3_6()
    redraw_fig4_4()
    redraw_fig5_5()
    print("批次 9 完成")
