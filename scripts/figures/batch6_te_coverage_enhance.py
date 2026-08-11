"""论文图批次 6：fig5_3 / fig5_4 高信息密度重设计。

fig5_3 方向不对称（v4）：
- 主面板 45° 对称散点：符号化距离配色（线上方 j→i 主导蓝 / 下方 i→j 主导橙 / 对称带灰）
- 点面积编码平均 TE 强度；显著对有向边实心、非显著空心
- 近似对称带（±阈值）+ 45° 参考线
- 顶部 + 右侧边缘直方图明确标注为主图横轴/纵轴分布，并用 1/2/3 编号联动 top 3 不对称对
- 长节点对名称移至图下，主图仅保留编号，避免文字遮挡散点
- 统计注释（20/45 对不对称 = 44.4%）置于图下

fig5_4 覆盖率（v3）：
- 左面板哑铃图增强：均值点 + per-seed 三种子散点（抖动）+ Δ 差值标注 + 90% 目标线
- 右面板 per-horizon 覆盖率：三种子 min-max 阴影带 + 均值线（标准灰虚线 / 分层深蓝实线）

统一规范：无标题、无文件名/代号、SVG+PNG 1200DPI、文字不遮挡图形。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D

sys.path.insert(0, str(Path.home() / ".claude/skills/scipilot-figure-skill/scripts"))
try:
    from export_figure import export_figure  # noqa: E402
    from setup_style import setup_style  # noqa: E402
except ImportError:  # 无 skill 环境回退（审查 L-03）
    from _skill_compat import export_figure, setup_style  # noqa: E402

sys.path.insert(0, "src")
from evcs_station_graph.data import load_tensor_bundle  # noqa: E402

FIG_DIR = Path("outputs/figures")
FIG_DIR.mkdir(parents=True, exist_ok=True)

setup_style(journal="general", lang="zh")
# 素雅配色
BLUE = "#2C5F8A"      # 深蓝（j→i 主导 / 分层共形）
ORANGE = "#D08A3C"    # 低饱和橙（i→j 主导）
GRAY_D = "#404040"    # 深灰
GRAY_M = "#808080"    # 中灰
GRAY_L = "#C8C8C8"    # 浅灰
RED_S = "#B05A4A"     # 低饱和红（目标线）
BUNDLE = load_tensor_bundle("data/processed/SG-DATA-005-primary-tensor.npz")


def final(fig, name: str, size: tuple[float, float]) -> None:
    """统一导出：SVG 矢量 + PNG 1200 DPI（论文硬性约束）。"""
    export_figure(
        fig, basename=str(FIG_DIR / name),
        formats=["svg", "png"], dpi=1200, size_inches=size,
        grayscale_preview=False,
    )
    print(f"  ✅ {name}")


def _clean_ax(ax, xlabel=None, ylabel=None):
    """统一轴风格：细边框 + 浅网格 + 标签。"""
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color(GRAY_D)
    ax.tick_params(labelsize=8, colors=GRAY_D)
    ax.grid(axis="y", color=GRAY_L, lw=0.5, alpha=0.6, zorder=0)
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=9)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=9)


# ========== fig5_3 方向不对称（v4：编号联动主图 + 边缘分布） ==========
def fig5_4_asymmetry() -> None:
    te = json.load(open("outputs/analysis/transfer_entropy/transfer_entropy_summary.json"))
    node_ids = list(BUNDLE.node_ids)
    te_mat = np.array(te["te_matrix"])
    sig_pairs = {(e["source"], e["target"]) for e in te["significant_edges"]}

    xs, ys, sigs, pairs = [], [], [], []
    for i in range(len(node_ids)):
        for j in range(i + 1, len(node_ids)):
            xs.append(te_mat[i, j])
            ys.append(te_mat[j, i])
            sigs.append((node_ids[i], node_ids[j]) in sig_pairs
                        or (node_ids[j], node_ids[i]) in sig_pairs)
            pairs.append((node_ids[i], node_ids[j]))
    xs, ys, sigs = np.array(xs), np.array(ys), np.array(sigs)
    vmax = max(xs.max(), ys.max())
    d = ys - xs                      # 符号化距离：正 = j→i 主导
    asym = np.divide(np.abs(d), np.maximum(xs, ys),
                     out=np.zeros_like(d), where=np.maximum(xs, ys) > 0)
    avg = (xs + ys) / 2.0            # 平均 TE（点面积编码）
    asym_threshold = 0.30            # 与正文 ASYM > 0.3 判定完全一致

    fig = plt.figure(figsize=(11.2, 8.0))
    # 增大主图面积，同时把图例、方向判定条、顶部边缘分布拆成三层。
    # 方向说明不进入任何数据区，避免文字与直方图/散点发生覆盖。
    ax = fig.add_axes([0.11, 0.16, 0.68, 0.58])
    ax_top = fig.add_axes([0.11, 0.79, 0.68, 0.09], sharex=ax)
    ax_right = fig.add_axes([0.83, 0.16, 0.11, 0.58], sharey=ax)

    # ---- 主面板 ----
    # 对称带采用 ASYM <= 0.3 的比例边界，而不是固定绝对差带：
    # y >= x 时 y <= x/(1-0.3)，y < x 时 y >= (1-0.3)x。
    line_x = np.linspace(0, vmax * 1.15, 200)
    lower = (1.0 - asym_threshold) * line_x
    upper = line_x / (1.0 - asym_threshold)
    ax.fill_between(line_x, lower, upper, color="#E3E8EC", alpha=0.34, zorder=1)
    # 45° 参考线 + ASYM 阈值边界线
    ax.plot([0, vmax * 1.15], [0, vmax * 1.15], color=GRAY_D, lw=1.1, ls="--", zorder=2)
    ax.plot(line_x, lower, color=GRAY_L, lw=0.8, ls=":", zorder=1)
    ax.plot(line_x, upper, color=GRAY_L, lw=0.8, ls=":", zorder=1)
    # 散点：颜色 = 主导方向，深浅 = 不对称程度；面积 = 平均 TE；实心 = 显著对
    colors = np.where(asym <= asym_threshold, GRAY_M,
                      np.where(d > 0, BLUE, ORANGE))
    alphas = 0.35 + 0.65 * np.abs(d) / max(np.abs(d).max(), 1e-9)
    sizes = 26 + 130 * avg / max(avg.max(), 1e-9)
    for x, y, c, a, s, sig in zip(xs, ys, colors, alphas, sizes, sigs):
        ax.scatter(x, y, s=s, facecolor=c if sig else "white",
                   edgecolor=c, linewidth=1.0, alpha=a, zorder=4)
    # 只在主图中标出编号；节点对名称放在图底部，避免长标签压住散点。
    top3 = te["asymmetry"]["top_asymmetric_pairs"][:3]
    label_offsets = [(vmax * 0.060, vmax * 0.060),
                     (vmax * 0.030, vmax * 0.050),
                     (vmax * 0.050, -vmax * 0.055)]
    for k, (p, (dx, dy)) in enumerate(zip(top3, label_offsets), start=1):
        i, j = node_ids.index(p["node_i"]), node_ids.index(p["node_j"])
        px, py = te_mat[i, j], te_mat[j, i]
        ax.scatter([px], [py], s=105, facecolor="none", edgecolor=RED_S,
                   linewidth=1.2, zorder=6)
        ax.annotate(str(k), xy=(px, py), xytext=(px + dx, py + dy),
                    fontsize=8.0, color=RED_S, fontweight="bold", ha="center", va="center",
                    bbox=dict(boxstyle="circle,pad=0.18", facecolor="white",
                              edgecolor=RED_S, linewidth=0.8),
                    arrowprops=dict(arrowstyle="->", color=GRAY_M, lw=0.8,
                                    shrinkA=4, shrinkB=2))
    _clean_ax(ax)
    ax.set_xlabel("传递熵 TE(i → j)（nats）", fontsize=9)
    ax.set_ylabel("传递熵 TE(j → i)（nats）", fontsize=9)
    ax.set_xlim(0, vmax * 1.15)
    ax.set_ylim(0, vmax * 1.15)

    # 图例置于主图外的上边距，避免遮挡散点。
    handles = [
        Line2D([0], [0], marker="o", color="none", markerfacecolor=BLUE,
               markeredgecolor=BLUE, markersize=6, label="j→i 主导（y>x）"),
        Line2D([0], [0], marker="o", color="none", markerfacecolor=ORANGE,
               markeredgecolor=ORANGE, markersize=6, label="i→j 主导（x>y）"),
        Line2D([0], [0], marker="o", color="none", markerfacecolor=GRAY_M,
               markeredgecolor=GRAY_M, markersize=6, label="近似对称（ASYM≤0.3）"),
        Line2D([0], [0], marker="o", color="none", markerfacecolor="white",
               markeredgecolor=BLUE, markersize=6, label="未入选候选边"),
    ]
    fig.legend(handles=handles, fontsize=7.0, frameon=False, ncol=4,
               loc="upper center", bbox_to_anchor=(0.47, 0.985),
               handletextpad=0.3, columnspacing=0.8)

    # ---- 顶部边缘直方图：明确是主图横轴 TE(i→j) 的分布 ----
    for s in ax_top.spines.values():
        s.set_visible(False)
    top_n, _, _ = ax_top.hist(xs, bins=14, range=(0, vmax * 1.15), color=GRAY_M, alpha=0.75,
                edgecolor="white", linewidth=0.3)
    ax_top.axvline(xs.mean(), color=GRAY_D, lw=0.9, ls="--")
    for k, p in enumerate(top3, start=1):
        i, j = node_ids.index(p["node_i"]), node_ids.index(p["node_j"])
        px = te_mat[i, j]
        # 编号标记放到直方图上方的独立带，不再落在柱顶或柱体内部。
        xtrans = ax_top.get_xaxis_transform()
        ax_top.scatter([px], [1.08], transform=xtrans, marker="v", s=28,
                       color=RED_S, zorder=5, clip_on=False)
        ax_top.text(px, 1.18, str(k), transform=xtrans, ha="center", va="bottom",
                    fontsize=7.2, color=RED_S, fontweight="bold", clip_on=False)
    ax_top.set_ylim(0, max(top_n) * 1.02)
    # 说明放在顶部直方图之外；方向关系由上方图例中的 y>x / x>y 直接定义。
    fig.text(0.11, 0.945, "主图横轴边缘分布：TE(i → j)",
             ha="left", va="top", fontsize=8.0, color=GRAY_D)
    ax_top.set_ylabel("频数", fontsize=7.0)
    ax_top.tick_params(axis="x", labelbottom=False)
    ax_top.tick_params(axis="y", labelsize=6.5)

    # ---- 右侧边缘直方图：明确是主图纵轴 TE(j→i) 的分布 ----
    for s in ax_right.spines.values():
        s.set_visible(False)
    right_n, _, _ = ax_right.hist(ys, bins=14, range=(0, vmax * 1.15), color=GRAY_M, alpha=0.75,
                  edgecolor="white", linewidth=0.3, orientation="horizontal")
    ax_right.axhline(ys.mean(), color=GRAY_D, lw=0.9, ls="--")
    max_right_n = max(right_n)
    for k, p in enumerate(top3, start=1):
        i, j = node_ids.index(p["node_i"]), node_ids.index(p["node_j"])
        py = te_mat[j, i]
        ax_right.scatter([-max_right_n * 0.16], [py], marker="<", s=24, color=RED_S, zorder=4)
        ax_right.text(-max_right_n * 0.34, py, str(k), ha="center", va="center",
                      fontsize=7.2, color=RED_S, fontweight="bold")
    ax_right.set_xlim(-max_right_n * 0.48, max_right_n * 1.12)
    ax_right.text(0.5, 0.95, "TE(j → i)", transform=ax_right.transAxes,
                  ha="center", va="top", fontsize=7.2, color=GRAY_D)
    ax_right.set_xticks([])
    # 纵轴刻度已由主图提供；右侧边缘图不再重复绘制短刻度，避免形成误读。
    ax_right.set_yticks([])
    ax_right.tick_params(axis="y", left=False, right=False, labelleft=False, labelright=False)

    final(fig, "fig5_3_asymmetry", (11.2, 8.0))


# ========== fig5_4 覆盖率（v3：per-seed 散点 + horizon 面板） ==========
def fig5_8_coverage() -> None:
    c = json.load(open("outputs/analysis/conformal_prediction/conformal_summary.json"))
    seeds = c["per_seed"]
    groups = ["全局", "事件窗口", "稳定窗口"]
    key_map = {"全局": "overall", "事件窗口": "event_window",
               "稳定窗口": "stable_window"}

    # 三层证据结构：A 事件窗口放大，B 全局/稳定窗口，C 逐步长稳定性。
    fig = plt.figure(figsize=(8.4, 8.25), constrained_layout=False)
    gs = fig.add_gridspec(3, 1, height_ratios=[1.08, 1.0, 1.12],
                          left=0.14, right=0.975, bottom=0.08, top=0.95,
                          hspace=0.34)

    def panel_tag(ax, tag: str, title: str) -> None:
        ax.text(-0.13, 1.08, tag, transform=ax.transAxes, fontsize=13,
                fontweight="bold", color=GRAY_D, va="top")
        ax.set_title(title, loc="left", fontsize=10.2, color=GRAY_D, pad=8)

    # ---- A：事件窗口可部署覆盖率 + 独立 oracle 参考 ----
    inner = gs[0].subgridspec(1, 2, width_ratios=[2.15, 1.0], wspace=0.24)
    axA = fig.add_subplot(inner[0, 0])
    axA_ref = fig.add_subplot(inner[0, 1])
    event_key = key_map["事件窗口"]
    event_std = np.array([s["standard_conformal"][f"coverage_{event_key}"] for s in seeds])
    event_str = np.array([s["stratified_conformal"][f"coverage_{event_key}"] for s in seeds])
    event_means = [float(event_std.mean()), float(event_str.mean())]
    event_sds = [float(event_std.std(ddof=1)), float(event_str.std(ddof=1))]
    x = np.arange(2)
    jit = np.linspace(-0.09, 0.09, len(seeds))
    for xi, vals, mean, sd, color, face in [
        (0, event_std, event_means[0], event_sds[0], GRAY_D, "white"),
        (1, event_str, event_means[1], event_sds[1], BLUE, BLUE),
    ]:
        axA.scatter(np.full(len(vals), xi) + jit, vals, s=30,
                    facecolor=face, edgecolor=color, linewidth=0.8, alpha=0.75,
                    zorder=3)
        axA.errorbar(xi, mean, yerr=sd, fmt="o", ms=8.5, color=color,
                     markerfacecolor=face, markeredgecolor=GRAY_D,
                     markeredgewidth=1.0, capsize=3.0, lw=1.2, zorder=4)
        axA.text(xi, mean + sd + 0.006, f"{mean:.1%}", ha="center", va="bottom",
                 fontsize=8.2, color=GRAY_D)
    axA.plot(x, event_means, color=ORANGE, lw=1.2, alpha=0.75, zorder=2)
    axA.text(0.5, 0.96, f"规则路由相对标准：+{(event_means[1]-event_means[0])*100:.1f} pp",
             transform=axA.transAxes, ha="center", va="top", fontsize=8.5, color=ORANGE)
    axA.set_xticks(x)
    axA.set_xticklabels(["标准共形", "规则路由分层"], fontsize=8.8)
    axA.set_ylabel("事件窗口覆盖率", fontsize=8.8)
    axA.set_ylim(0, 0.10)
    axA.set_yticks([0, 0.02, 0.04, 0.06, 0.08, 0.10])
    axA.set_yticklabels(["0%", "2%", "4%", "6%", "8%", "10%"], fontsize=7.8)
    _clean_ax(axA)
    panel_tag(axA, "A", "事件窗口：可部署覆盖率（放大视图）")

    oracle_event = float(np.mean([
        s["stratified_oracle_upper"]["coverage_event_window"] for s in seeds]))
    target = 1.0 - float(c["alpha"])
    axA_ref.axhline(0.5, color=GRAY_L, lw=2.2, zorder=1)
    axA_ref.axvline(target, color=RED_S, lw=1.2, ls="--", zorder=2)
    axA_ref.plot(oracle_event, 0.5, marker="*", ms=15, color=RED_S,
                 markeredgecolor="white", markeredgewidth=0.7, zorder=3)
    axA_ref.text(oracle_event, 0.70, f"oracle\n{oracle_event:.1%}",
                 ha="center", va="bottom", fontsize=8.2, color=RED_S)
    axA_ref.text(target, 0.16, "目标", ha="center", va="top", fontsize=7.8,
                 color=RED_S)
    axA_ref.set_xlim(0.80, 0.92)
    axA_ref.set_ylim(0, 1)
    axA_ref.set_xticks([0.80, 0.85, 0.90])
    axA_ref.set_xticklabels(["80%", "85%", "90%"], fontsize=7.5)
    axA_ref.set_yticks([])
    axA_ref.set_xlabel("事后诊断参照（不可部署）", fontsize=8.2, labelpad=8)
    _clean_ax(axA_ref)

    # ---- B：全局/稳定窗口的三种子均值与标准差 ----
    axB = fig.add_subplot(gs[1, 0])
    groups_B = ["稳定窗口", "全局"]
    yB = np.arange(len(groups_B))
    for yi, g in zip(yB, groups_B):
        key = key_map[g]
        std_v = np.array([s["standard_conformal"][f"coverage_{key}"] for s in seeds])
        str_v = np.array([s["stratified_conformal"][f"coverage_{key}"] for s in seeds])
        s_mean, v_mean = float(std_v.mean()), float(str_v.mean())
        s_sd, v_sd = float(std_v.std(ddof=1)), float(str_v.std(ddof=1))
        axB.plot([s_mean, v_mean], [yi, yi], color=GRAY_L, lw=2.4, zorder=1)
        jitB = np.linspace(-0.10, 0.10, len(seeds))
        axB.scatter(std_v, yi + jitB, s=28, facecolor="white", edgecolor=GRAY_M,
                    linewidth=0.8, zorder=3)
        axB.scatter(str_v, yi + jitB, s=28, facecolor=BLUE, edgecolor=BLUE,
                    linewidth=0.5, alpha=0.7, zorder=3)
        axB.errorbar(s_mean, yi, xerr=s_sd, fmt="o", ms=8.5, color=GRAY_D,
                     markerfacecolor="white", markeredgecolor=GRAY_D,
                     capsize=3.0, lw=1.1, zorder=4,
                     label="标准共形" if yi == 0 else None)
        axB.errorbar(v_mean, yi, xerr=v_sd, fmt="o", ms=8.5, color=BLUE,
                     markerfacecolor=BLUE, markeredgecolor=GRAY_D,
                     capsize=3.0, lw=1.1, zorder=5,
                     label="规则路由分层" if yi == 0 else None)
        axB.text(0.825, yi, f"Δ{(v_mean-s_mean)*100:+.1f} pp", ha="right",
                 va="center", fontsize=8.2, color=ORANGE)
    axB.set_yticks(yB)
    axB.set_yticklabels(groups_B, fontsize=9.0)
    axB.set_xlabel("覆盖率（α = 0.1；3 种子）", fontsize=8.8)
    axB.set_xlim(0.60, 0.84)
    axB.set_xticks([0.60, 0.65, 0.70, 0.75, 0.80])
    axB.set_xticklabels(["60%", "65%", "70%", "75%", "80%"], fontsize=7.8)
    axB.set_ylim(-0.45, 1.45)
    _clean_ax(axB)
    axB.legend(fontsize=7.5, frameon=False, loc="upper right", ncol=2,
               handlelength=1.8, columnspacing=0.8)
    panel_tag(axB, "B", "全局与稳定窗口：标准/规则路由对比")

    # ---- C：逐步长覆盖率及三种子 min–max 范围 ----
    axC = fig.add_subplot(gs[2, 0])
    hx = np.arange(1, 5)
    std_mats = np.array([s["standard_conformal"]["coverage_by_horizon"] for s in seeds])
    str_mats = np.array([s["stratified_conformal"]["coverage_by_horizon"] for s in seeds])
    for mat, color, ls, label, z in [
        (std_mats, GRAY_M, "--", "标准共形", 2),
        (str_mats, BLUE, "-", "规则路由分层", 3),
    ]:
        lo, hi = mat.min(axis=0), mat.max(axis=0)
        axC.fill_between(hx, lo, hi, color=color, alpha=0.14, zorder=z - 1)
        axC.plot(hx, mat.mean(axis=0), color=color, ls=ls, lw=1.9, marker="o",
                 ms=4.8, label=label, zorder=z)
    axC.axhline(target, color=RED_S, lw=1.1, ls="--", zorder=1)
    axC.text(3.98, target + 0.004, "90% 目标", fontsize=7.8, color=RED_S, ha="right")
    axC.set_xticks(hx)
    axC.set_xlabel("预测步长（horizon；规则路由）", fontsize=8.8)
    axC.set_ylabel("全样本覆盖率", fontsize=8.8)
    axC.set_ylim(0.55, 0.93)
    axC.set_yticks([0.60, 0.70, 0.80, 0.90])
    axC.set_yticklabels(["60%", "70%", "80%", "90%"], fontsize=7.8)
    axC.set_xlim(0.8, 4.2)
    _clean_ax(axC)
    axC.legend(fontsize=7.5, frameon=True, facecolor="white", edgecolor="none",
               framealpha=0.88, loc="upper left", ncol=2,
               handlelength=1.8, columnspacing=0.8)
    panel_tag(axC, "C", "逐步长覆盖率：三种子范围与均值")

    final(fig, "fig5_8_coverage", (8.4, 8.25))


if __name__ == "__main__":
    print("=== 批次 6：图5-3方向不对称性重设计 ===")
    fig5_4_asymmetry()
    print("批次 6 完成")
