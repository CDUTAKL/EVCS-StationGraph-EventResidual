"""论文图批次 6：fig5_3 / fig5_4 高信息密度重设计（用户 2026-08-01 反馈"还不够完美"）。

fig5_3 方向不对称（v3）：
- 主面板 45° 对称散点：符号化距离配色（线上方 j→i 主导蓝 / 下方 i→j 主导橙 / 对称带灰）
- 点面积编码平均 TE 强度；显著对有向边实心、非显著空心
- 近似对称带（±阈值）+ 45° 参考线
- 顶部 + 右侧边缘直方图（双向 TE 分布）
- top 3 不对称对箭头标注（统一放右上空白区，不遮挡散点）
- 统计注释（20/45 对不对称 = 44.4%）

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

sys.path.insert(0, str(Path.home() / ".claude/skills/scipilot-figure-skill/scripts"))
from export_figure import export_figure  # noqa: E402
from setup_style import setup_style  # noqa: E402

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


# ========== fig5_3 方向不对称（v3：符号化距离 + 边缘直方图） ==========
def fig5_3_asymmetry() -> None:
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
    avg = (xs + ys) / 2.0            # 平均 TE（点面积编码）
    band = 0.12 * vmax               # 近似对称带半宽

    fig = plt.figure(figsize=(7.2, 6.2))
    gs = fig.add_gridspec(2, 2, width_ratios=[4.2, 1.0], height_ratios=[1.0, 4.2],
                          wspace=0.12, hspace=0.12)
    ax = fig.add_subplot(gs[1, 0])
    ax_top = fig.add_subplot(gs[0, 0], sharex=ax)
    ax_right = fig.add_subplot(gs[1, 1], sharey=ax)

    # ---- 主面板 ----
    # 对称带（|y-x| < band 区域浅灰填充，与两侧边界虚线一致）
    line_x = np.linspace(0, vmax * 1.15, 50)
    ax.fill_between(line_x, line_x - band, line_x + band, color="0.86", alpha=0.6,
                    zorder=1)
    # 45° 参考线 + 带边界线
    ax.plot([0, vmax * 1.15], [0, vmax * 1.15], color=GRAY_D, lw=1.1, ls="--", zorder=2)
    for off in (-band, band):
        ax.plot([0, vmax * 1.15], [off, vmax * 1.15 + off], color=GRAY_L, lw=0.8,
                ls=":", zorder=1)
    # 散点：颜色 = 主导方向，深浅 = 不对称程度；面积 = 平均 TE；实心 = 显著对
    colors = np.where(np.abs(d) < band, GRAY_M,
                      np.where(d > 0, BLUE, ORANGE))
    alphas = 0.35 + 0.65 * np.abs(d) / max(np.abs(d).max(), 1e-9)
    sizes = 26 + 130 * avg / max(avg.max(), 1e-9)
    for x, y, c, a, s, sig in zip(xs, ys, colors, alphas, sizes, sigs):
        ax.scatter(x, y, s=s, facecolor=c if sig else "white",
                   edgecolor=c, linewidth=1.0, alpha=a, zorder=4)
    # top 3 不对称对标注：分散放右上/顶部/右缘空白区，箭头连线（不遮挡散点）
    top3 = te["asymmetry"]["top_asymmetric_pairs"][:3]
    label_xy = [(vmax * 0.68, vmax * 1.06), (vmax * 0.92, vmax * 1.04),
                (vmax * 1.07, vmax * 0.86)]
    for p, (lx, ly) in zip(top3, label_xy):
        i, j = node_ids.index(p["node_i"]), node_ids.index(p["node_j"])
        px, py = te_mat[i, j], te_mat[j, i]
        ax.annotate(f"{p['node_i'].split('-')[1]}↔{p['node_j'].split('-')[1]}"
                    f"  (Δ={p['asymmetry']:.2f})",
                    xy=(px, py), xytext=(lx, ly),
                    fontsize=7.5, color=GRAY_D,
                    arrowprops=dict(arrowstyle="->", color=GRAY_M, lw=0.8,
                                    shrinkA=4, shrinkB=2))
    # 主导区说明（必要说明文字，放左下空白区）
    ax.text(vmax * 0.05, vmax * 0.94, "j→i 主导", fontsize=8, color=BLUE, ha="left")
    ax.text(vmax * 0.72, vmax * 0.06, "i→j 主导", fontsize=8, color=ORANGE, ha="left")
    ax.text(vmax * 0.06, vmax * 0.16, "近似对称", fontsize=7.5, color=GRAY_M)
    # 统计注释（措辞收敛：超过不对称阈值，非统计显著性——审查 2026-08-01）
    ax.text(vmax * 0.05, vmax * 0.045,
            f"45 对中 {te['asymmetry']['asymmetric_pair_count']} 对超过不对称阈值"
            f"（Δ>0.3，占 {100 * te['asymmetry']['asymmetry_rate']:.0f}%）",
            fontsize=7.5, color=GRAY_D, ha="left")
    _clean_ax(ax)
    ax.set_xlabel("传递熵 TE(i → j)（nats）", fontsize=9)
    ax.set_ylabel("传递熵 TE(j → i)（nats）", fontsize=9)
    ax.set_xlim(0, vmax * 1.15)
    ax.set_ylim(0, vmax * 1.15)

    # 图例（三层：主导方向 + 面积 + 实心空心；实心 = 至少一个方向入选 TE 候选边）
    handles = [
        plt.scatter([], [], s=70, facecolor=BLUE, edgecolor=BLUE, label="j→i 主导"),
        plt.scatter([], [], s=70, facecolor=ORANGE, edgecolor=ORANGE, label="i→j 主导"),
        plt.scatter([], [], s=70, facecolor=GRAY_M, edgecolor=GRAY_M, label="近似对称"),
        plt.scatter([], [], s=70, facecolor="white", edgecolor=BLUE,
                    linewidth=1.0, label="两方向均未入选候选边"),
    ]
    ax.legend(handles=handles, fontsize=7.5, frameon=False, ncol=2,
              loc="lower right", bbox_to_anchor=(1.0, 0.0),
              handletextpad=0.3, columnspacing=0.8)

    # ---- 顶部边缘直方图（TE(i→j) 分布） ----
    for s in ax_top.spines.values():
        s.set_visible(False)
    ax_top.hist(xs, bins=14, range=(0, vmax * 1.15), color=GRAY_M, alpha=0.75,
                edgecolor="white", linewidth=0.3)
    ax_top.axvline(xs.mean(), color=GRAY_D, lw=0.9, ls="--")
    ax_top.set_yticks([])
    ax_top.tick_params(axis="x", labelbottom=False)

    # ---- 右侧边缘直方图（TE(j→i) 分布） ----
    for s in ax_right.spines.values():
        s.set_visible(False)
    ax_right.hist(ys, bins=14, range=(0, vmax * 1.15), color=GRAY_M, alpha=0.75,
                  edgecolor="white", linewidth=0.3, orientation="horizontal")
    ax_right.axhline(ys.mean(), color=GRAY_D, lw=0.9, ls="--")
    ax_right.set_xticks([])
    ax_right.tick_params(axis="y", labelleft=False)

    final(fig, "fig5_3_asymmetry", (7.2, 6.2))


# ========== fig5_4 覆盖率（v3：per-seed 散点 + horizon 面板） ==========
def fig5_4_coverage() -> None:
    c = json.load(open("outputs/analysis/conformal_prediction/conformal_summary.json"))
    seeds = c["per_seed"]
    groups = ["全局", "事件窗口", "稳定窗口"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8.4, 3.9),
                                   gridspec_kw={"width_ratios": [1.5, 1.0]})
    y = np.arange(len(groups))
    d = 0.11  # per-seed 散点抖动半宽

    # ---- 左面板：哑铃图 + per-seed 散点 ----
    event_std_mean = event_str_mean = None
    for yi, g in enumerate(groups):
        key = {"全局": "overall", "事件窗口": "event_window",
               "稳定窗口": "stable_window"}[g]
        std_v = [s["standard_conformal"][f"coverage_{key}"] for s in seeds]
        str_v = [s["stratified_conformal"][f"coverage_{key}"] for s in seeds]
        s_mean, v_mean = float(np.mean(std_v)), float(np.mean(str_v))
        if yi == 1:
            event_std_mean, event_str_mean = s_mean, v_mean
        # 哑铃连接线（标准 → 分层）
        ax1.plot([s_mean, v_mean], [yi, yi], color=GRAY_L, lw=2.4, zorder=2)
        # per-seed 散点（抖动，不遮挡均值点）
        jit = np.linspace(-d, d, len(seeds))
        ax1.scatter(std_v, yi + jit, s=26, facecolor="white", edgecolor=GRAY_M,
                    linewidth=0.8, zorder=3)
        ax1.scatter(str_v, yi + jit, s=26, facecolor=BLUE, edgecolor=BLUE,
                    linewidth=0.4, alpha=0.55, zorder=3)
        # 均值点（大圆）
        ax1.scatter([s_mean], [yi], s=95, facecolor="white", edgecolor=GRAY_D,
                    linewidth=1.5, zorder=4, label="标准共形" if yi == 0 else None)
        ax1.scatter([v_mean], [yi], s=115, facecolor=BLUE, edgecolor=GRAY_D,
                    linewidth=1.0, zorder=5, label="分层共形" if yi == 0 else None)
        # 数值标签（均值点外侧，不遮挡）
        ax1.text(s_mean - 0.045, yi, f"{s_mean:.0%}", ha="center", va="center",
                 fontsize=8, color=GRAY_M)
        ax1.text(v_mean + 0.045, yi, f"{v_mean:.0%}", ha="center", va="center",
                 fontsize=8, color=GRAY_D, fontweight="bold" if yi == 1 else "normal")
        # Δ 提升标注（右侧空白区，橙色）
        delta = v_mean - s_mean
        ax1.text(0.975, yi, f"Δ+{delta * 100:.0f}pp", ha="right", va="center",
                 fontsize=8, color=ORANGE, fontweight="bold" if yi == 1 else "normal")
    # 90% 目标线 + 达标区底纹（0.85-1.0 浅灰蓝）
    ax1.axvspan(0.90, 1.0, color="0.94", zorder=0)
    ax1.axvline(0.9, color=RED_S, lw=1.2, ls="--", zorder=1)
    ax1.text(0.905, 2.36, "90% 目标", fontsize=7.5, color=RED_S)
    # 事件窗口：规则路由提升箭头（1.9% → 3.9%）+ oracle 事后上界标注。
    # 审查 2026-08-01：正式口径为可部署的规则路由；真实标签路由仅作上界诊断
    oracle_event = float(np.mean([
        s["stratified_oracle_upper"]["coverage_event_window"] for s in seeds]))
    # 提升箭头与文字由均值自动生成（审查 2026-08-01：不硬编码数值）
    ax1.annotate("", xy=(event_str_mean + 0.02, 1.28),
                 xytext=(max(event_std_mean - 0.01, 0.005), 1.28),
                 arrowprops=dict(arrowstyle="->", color=ORANGE, lw=1.7))
    ax1.text((event_std_mean + event_str_mean) / 2 + 0.08, 1.42,
             f"{event_std_mean:.0%} → {event_str_mean:.0%}（规则路由）",
             ha="center", fontsize=8, color=ORANGE)
    ax1.plot([oracle_event], [1], marker="*", ms=13, color=RED_S, zorder=6,
             markeredgecolor="white", markeredgewidth=0.6)
    ax1.text(oracle_event + 0.03, 1, f"oracle 上界 {oracle_event:.0%}",
             fontsize=7.5, color=RED_S, va="center")
    ax1.set_yticks(y)
    ax1.set_yticklabels(groups, fontsize=9.5)
    ax1.set_xlabel("覆盖率（α = 0.1，规则路由，3 种子）", fontsize=9)
    ax1.set_xlim(0, 1.02)
    ax1.set_ylim(-0.55, 2.55)
    _clean_ax(ax1)
    ax1.legend(fontsize=7.5, frameon=False, loc="lower left", ncol=2)

    # ---- 右面板：per-horizon 覆盖率（3 种子 min-max 带 + 均值线） ----
    hx = np.arange(1, 5)
    std_mats = np.array([s["standard_conformal"]["coverage_by_horizon"] for s in seeds])
    str_mats = np.array([s["stratified_conformal"]["coverage_by_horizon"] for s in seeds])
    for mat, c, ls, lbl, z in [(std_mats, GRAY_M, "--", "标准共形", 2),
                               (str_mats, BLUE, "-", "分层共形", 3)]:
        lo, hi = mat.min(axis=0), mat.max(axis=0)
        ax2.fill_between(hx, lo, hi, color=c, alpha=0.12, zorder=z - 1)
        ax2.plot(hx, mat.mean(axis=0), color=c, ls=ls, lw=1.8, marker="o",
                 ms=4.5, label=lbl, zorder=z)
    ax2.axhline(0.9, color=RED_S, lw=1.1, ls="--", zorder=1)
    ax2.set_xticks(hx)
    ax2.set_xlabel("预测步长（horizon，规则路由）", fontsize=9)
    # 右图按全样本统计（含稳定样本），明确标注避免误读为事件窗口（审查 2026-08-01）
    ax2.set_ylabel("全样本覆盖率", fontsize=9)
    ax2.set_ylim(0.55, 0.93)
    ax2.set_yticks([0.60, 0.70, 0.80, 0.90])
    _clean_ax(ax2)
    ax2.legend(fontsize=7.5, frameon=False, loc="lower left")
    ax2.text(4.03, 0.905, "90% 目标", fontsize=7, color=RED_S, ha="right")

    final(fig, "fig5_4_coverage", (8.4, 3.9))


if __name__ == "__main__":
    print("=== 批次 6：fig5_3 / fig5_4 高信息密度重设计 ===")
    fig5_3_asymmetry()
    fig5_4_coverage()
    print("批次 6 完成")
