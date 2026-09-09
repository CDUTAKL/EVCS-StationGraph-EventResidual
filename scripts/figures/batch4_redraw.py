"""重绘 9 张问题图（对齐老论文素雅风格：灰阶 + 深蓝强调 + 低饱和）。

修复清单（用户 2026-08-01 反馈）：
- 现图2-5自相关：文字遮挡曲线 + 顶部空旷 → y 上限 0.8、标注移至空白区、宽线+浅网格
- fig2_5 分布：右上角文字删除 + 2.0 后空旷 → x 截断 0-2.5 + 对数 y
- fig2_6 事件时间线：堆叠面积丑陋 → 4 行子图共享 x 轴
- fig3_1 误差棒不明显 → 加粗 + 大 capsize + 深色
- fig3_6 点级 pooled Bootstrap 差异 → 描述性差异图（不作正式显著性宣称）
- fig4_4 四格 → 精致热力图（白网格线 + 大方格 + 双行标注）
- fig5_3 配色 → 深蓝/橙/灰素雅配色
- fig5_4 覆盖率 → 加大间距、标签不遮挡
- fig5_5 分位数 → 加大 figsize、布局舒展

统一规范：无标题、无文件名/代号、SVG+PNG 1200DPI。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import NullFormatter

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
# 素雅配色（对齐老论文：深蓝主色 + 灰阶 + 低饱和强调）
BLUE = "#2C5F8A"      # 深蓝（老论文 40,80,120）
ORANGE = "#D08A3C"    # 低饱和橙
GRAY_D = "#404040"    # 深灰
GRAY_M = "#808080"    # 中灰
GRAY_L = "#C8C8C8"    # 浅灰
RED_S = "#B05A4A"     # 低饱和红
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


# ========== ① 现图2-5自相关（重绘） ==========
def redraw_autocorrelation() -> None:
    nodes = ["CA-303", "CA-327", "CA-489"]
    # lag 1~672 步 = 0.25h~168h：覆盖 24h 日周期与 168h 周周期两个峰
    # （修复：原实现 lag 仅到 48h 却画了 168h 虚线——无数据支撑的内容错误）
    lags = np.arange(1, 673)
    fig, ax = plt.subplots(figsize=(6.8, 3.2))
    for n, c, ls, lw in zip(nodes, [BLUE, GRAY_D, GRAY_M], ["-", "--", "-."], [1.6, 1.4, 1.4]):
        idx = list(BUNDLE.node_ids).index(n)
        s = BUNDLE.targets[:, idx]
        acf = np.array([np.corrcoef(s[:-l], s[l:])[0, 1] for l in lags])
        ax.plot(lags / 4.0, acf, color=c, ls=ls, lw=lw, label=n)
    # 周期标注放在曲线下方空白（不遮挡）
    ax.axvline(24, color=GRAY_L, lw=0.9, ls="--")
    ax.axvline(168, color=GRAY_L, lw=0.9, ls="--")
    ax.text(24, 0.03, "24 h", fontsize=7.5, color=GRAY_M, ha="center")
    ax.text(168, 0.03, "168 h", fontsize=7.5, color=GRAY_M, ha="center")
    ax.set_xlabel("滞后（小时）", fontsize=9)
    ax.set_ylabel("自相关系数", fontsize=9)
    # 不截断 lag=0 的理论自相关峰；本图从 lag=1 开始绘制，仍保留 1.0 参照范围。
    ax.set_ylim(-0.05, 1.02)
    ax.legend(fontsize=8, frameon=False, ncol=3, loc="upper right")
    _clean_ax(ax)
    final(fig, "fig2_4_autocorrelation", (6.8, 3.2))


# ========== ② fig2_5 负荷分布（重绘） ==========
def redraw_distribution() -> None:
    vals = BUNDLE.targets.flatten()
    vals = vals[vals > 0]  # 非零负荷条件分布（零负荷占 78.4%，不参与直方图）
    nz_rate = 100.0 * vals.size / BUNDLE.targets.size
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    ax.hist(vals, bins=np.arange(0, 2.6, 0.05), color=BLUE,
            edgecolor="white", linewidth=0.3, zorder=3)
    ax.set_yscale("log")
    # Minor log ticks do not carry information in this distribution panel and
    # their default labels render below the thesis readability threshold.
    ax.yaxis.set_minor_formatter(NullFormatter())
    ax.set_xlabel("负荷（kWh/15 min）", fontsize=9)
    ax.set_ylabel("非零负荷样本数（对数轴）", fontsize=9)
    ax.set_xlim(0, 2.5)
    # 截断披露 + 非零率标注（必要说明，放右上空白区）
    ax.text(0.98, 0.97, f"非零负荷占比 {nz_rate:.1f}%\n仅显示 0–2.5，右尾截断",
            transform=ax.transAxes, ha="right", va="top", fontsize=7.5,
            color=GRAY_D)
    _clean_ax(ax)
    final(fig, "fig2_6_load_distribution", (6.4, 3.4))


# ========== ③ fig2_6 事件时段分布（聚合 3 年全部事件到 24h） ==========
def redraw_event_timeline() -> None:
    # 聚合口径：全部时间步中任一节点真实标签事件（event_labels）→ 按小时统计频率
    # 真实峰值（2026-08-01 数据核实）：深夜 0-3 时（6.0%~8.8%）与午后 15-16 时（7.3%/7.4%），
    # 8-11 时仅 ~1%（低谷）——原"早高峰 8-11 时"标注与数据相反，已修正
    ev = BUNDLE.event_labels.any(axis=1)  # [T] 任一节点发生标签事件
    # 原始时间戳按数据协议以 UTC 存储；日内分布必须先转换到站点当地时区，
    # 否则深夜/午后峰会整体平移。图中不把代理标签解释为物理事件发生时刻。
    local_ts = pd.to_datetime(BUNDLE.timestamps_ns, utc=True).tz_convert("America/Los_Angeles")
    hours = local_ts.hour[ev]
    freq = np.bincount(hours, minlength=24) / max(ev.sum(), 1)  # 各时段事件占比

    fig, ax = plt.subplots(figsize=(7.4, 3.7))
    x = np.arange(24)
    # 柱中心对应整数小时；高峰底纹按半小时边界铺开，避免分组与柱形错位。
    ax.bar(x, freq * 100, width=0.76, color=BLUE, edgecolor="white",
           linewidth=0.4, zorder=3)
    # 标注放在高峰区域上方的独立留白，避免文字进入柱体。
    ymax = float(freq.max() * 100) * 1.20
    ax.set_ylim(0, ymax)
    # 两个峰值说明使用同一基线高度，避免缩放后出现一高一低的视觉错位。
    label_y = ymax * 0.88
    peak_hour = int(np.argmax(freq))
    ax.text(peak_hour, label_y, f"{peak_hour:02d}时 · {freq[peak_hour]*100:.1f}%", fontsize=9,
            color=GRAY_D, ha="center", va="bottom")
    ax.set_xticks(range(0, 24, 2))
    ax.set_xlim(-0.5, 23.5)
    ax.set_xlabel("当地小时（America/Los_Angeles）", fontsize=8.6)
    ax.set_ylabel("事件时间步占比（%）", fontsize=9)
    ax.tick_params(labelsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color=GRAY_L, lw=0.5, alpha=0.6, zorder=0)
    final(fig, "fig2_8_event_hourly", (6.8, 3.4))


# ========== ④ fig3_1 误差棒加强（重绘） ==========
def redraw_model_comparison() -> None:
    # 数值与正文表 3-1 一致；随机模型给出三种子标准差，确定性模型不画误差棒。
    data = [
        ("MRG-GCN", 0.01376, 0.00023),
        ("EventResidual", 0.01390, 0.00015),
        ("AdaptiveGraph", 0.01396, 0.00017),
        ("GraphWaveNet\n（简化变体）", 0.01773, 0.00054),
        ("AGCRN\n（简化变体）", 0.02057, 0.00029),
        ("MLP", 0.02112, 0.00019),
        ("ARIMA(2,1,2)", 0.02260, None),
        ("TCN", 0.02952, 0.00014),
        ("GRU", 0.02965, 0.00003),
        ("LightGBM", 0.03758, None),
        ("XGBoost", 0.03873, None),
        ("Persistence", 0.07828, None),
    ]
    data.sort(key=lambda x: x[1])
    names = [d[0] for d in data]
    maes = [d[1] for d in data]
    stds = [d[2] for d in data]
    colors = [BLUE if i == 0 else GRAY_M for i in range(len(names))]

    fig, ax = plt.subplots(figsize=(7.2, 5.1))
    y = np.arange(len(names))
    bars = ax.barh(y, maes, height=0.62, color=colors,
                   edgecolor=GRAY_D, linewidth=0.5, zorder=3)
    # 误差棒：仅三种子随机方法有 std；确定性方法（ARIMA/LGBM/XGB/Persistence）无种子
    # 波动是科学事实，不加（审查 2026-08-01：主结果图需展示不确定性）
    for yi, (mae, std) in enumerate(zip(maes, stds)):
        if std is not None:
            ax.errorbar(mae, yi, xerr=std, fmt="none", ecolor=GRAY_D,
                        capsize=3, lw=0.9, zorder=4)
    for yi, mae in enumerate(maes):
        ax.text(mae + 0.0015, yi, f"{mae:.5f}", va="center", fontsize=8.5,
                color=GRAY_D)
    bars[0].set_color(BLUE)
    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=8.5)
    ax.set_xlabel("Global MAE（kWh/15 min）", fontsize=9)
    ax.set_xlim(0, 0.095)
    ax.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=BLUE),
                       plt.Rectangle((0, 0), 1, 1, color=GRAY_M)],
              labels=["本文主模型", "其他模型"], fontsize=8, frameon=False,
              loc="lower right")
    _clean_ax(ax)
    final(fig, "fig3_7_model_mae_comparison", (7.2, 5.1))


# ========== ⑤ fig3_6 点级 pooled Bootstrap 差异图（描述性） ==========
def redraw_bootstrap() -> None:
    d = json.load(open("outputs/analysis/bootstrap_significance.json"))
    # 标签 = "提议模型 vs 基线"（diff = MAE(基线) − MAE(提议)，正值 = 提议更优）
    labels = {
        "TCN - StaticGraph": "StaticGraph\nvs TCN",
        "StaticGraph - AdaptiveGraph": "AdaptiveGraph\nvs StaticGraph",
        "AdaptiveGraph - EventResidual": "EventResidual\nvs AdaptiveGraph",
        "StaticGraph - MLP": "MLP\nvs StaticGraph",
        "TCN - MLP": "MLP\nvs TCN",
        "AdaptiveGraph - no_event_gate": "no-event-gate\nvs AdaptiveGraph",
    }
    names, diffs, ps, cis = [], [], [], []
    for c in d["comparisons"]:
        # pooled = 三种子正确合并（修复：原实现 per-seed 平均 + min-p 统计错误）
        p = c["pooled"]
        win = "global" if "global" in p else "event_window"
        suffix = "（事件窗口）" if win == "event_window" else ""
        label = labels.get(c["name"], c["name"])
        if suffix:
            label += "\n" + suffix.strip("（）")
        names.append(label)
        diffs.append(p[win]["observed_diff"])
        ps.append(p[win]["p_value_one_sided"])
        cis.append((p[win]["ci_lower"], p[win]["ci_upper"]))

    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    x = np.arange(len(names))
    # 颜色只编码方向，不把 pooled p 值视觉化为“显著/不显著”。
    colors = [BLUE if dd > 0 else GRAY_M for dd in diffs]
    bars = ax.bar(x, diffs, width=0.58, color=colors,
                  edgecolor=GRAY_D, linewidth=0.5, zorder=3)
    # pooled 95% CI 误差棒（审查 2026-08-01：Bootstrap 图需展示不确定性区间）
    for xi, (dd, (lo, hi)) in enumerate(zip(diffs, cis)):
        ax.errorbar(xi, dd, yerr=[[dd - lo], [hi - dd]], fmt="none",
                    ecolor=GRAY_D, capsize=3.5, lw=1.0, zorder=4)
    for xi, (dd, p) in enumerate(zip(diffs, ps)):
        # 直接标注 p 值：正值柱上方、负值柱下方（y 轴已留白，不超出平面）
        label = "p<0.001" if p < 0.001 else f"p={p:.3f}"
        if dd >= 0:
            ax.text(xi, dd + 0.0007, label, ha="center", va="bottom",
                    fontsize=7.5, color=GRAY_D)
        else:
            ax.text(xi, dd - 0.0012, label, ha="center", va="top",
                    fontsize=7.5, color=GRAY_D)
    ax.axhline(0, color=GRAY_D, lw=1.0, zorder=2)
    # y 轴留白：正柱标注在上方、负柱标注在柱底下方，均需留足空间
    ax.set_ylim(min(diffs) * 1.4 - 0.0015, max(diffs) * 1.35 + 0.0018)
    ax.set_xticks(x)
    ax.set_xticklabels(names, fontsize=7.2, rotation=0, ha="center")
    ax.tick_params(axis="x", pad=4)
    ax.set_ylabel("MAE 差（kWh/15 min；基线 − 提议模型）", fontsize=8.5)
    ax.tick_params(axis="y", labelsize=8)
    # 统计口径披露（审查 2026-08-01）：点级 pooled Bootstrap、重采样单元为预测键
    ax.text(0.99, -0.30,
            "点级 pooled Bootstrap（10,000 次；预测键为重采样单元；三种子合并）\n"
            "误差棒：95% 百分位区间；p 值为描述性单侧比例，不作正式显著性结论",
            transform=ax.transAxes, ha="right", va="top", fontsize=6.5, color=GRAY_M)
    _clean_ax(ax)
    ax.grid(axis="y", color=GRAY_L, lw=0.5, alpha=0.6, zorder=0)
    fig.subplots_adjust(bottom=0.30)
    final(fig, "fig3_11_bootstrap_difference", (7.2, 4.0))


# ========== ⑥ fig4_4 四格诊断（重绘：Blues 色阶 + 分层标注） ==========
def redraw_four_cell() -> None:
    m = json.load(open("outputs/experiments/SG-EXP-004/20260731-102456/seed-2024/metrics.json"))
    fc = m["four_cell"]["cells"]
    matrix = np.array([
        [fc["target_event_triggered"]["mae"], fc["target_event_not_triggered"]["mae"]],
        [fc["stable_triggered"]["mae"], fc["stable_not_triggered"]["mae"]],
    ])
    counts = np.array([
        [fc["target_event_triggered"]["count"], fc["target_event_not_triggered"]["count"]],
        [fc["stable_triggered"]["count"], fc["stable_not_triggered"]["count"]],
    ])
    total = counts.sum()

    fig, ax = plt.subplots(figsize=(5.0, 4.6))
    # Blues 渐变（素雅学术）：低 MAE 浅蓝、高 MAE 深蓝
    cmap = plt.get_cmap("Blues")
    vmax = 0.30
    im = ax.imshow(matrix, cmap=cmap, aspect="equal", vmin=0, vmax=vmax)
    # 白色粗网格线分隔四格
    for i in range(3):
        ax.axhline(i - 0.5, color="white", lw=3.0)
    for j in range(3):
        ax.axvline(j - 0.5, color="white", lw=3.0)
    for i in range(2):
        for j in range(2):
            dark = matrix[i, j] > vmax * 0.55  # 深色格用白字
            text_c = "white" if dark else GRAY_D
            # MAE（粗体大字）
            ax.text(j, i - 0.13, f"{matrix[i, j]:.4f}", ha="center",
                    fontsize=13, fontweight="bold", color=text_c)
            # n（次级信息，小字）
            ax.text(j, i + 0.20, f"n = {counts[i, j]:,}", ha="center",
                    va="top", fontsize=8.5, color=text_c, alpha=0.85)
    # 行列语义（审查 2026-08-01：标签事件/可见规则触发组合，避免分类语义混淆）
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["规则触发", "规则未触发"], fontsize=10.5)
    ax.set_yticks([0, 1])
    ax.set_yticklabels(["标签事件", "标签非事件"], fontsize=10.5)
    ax.tick_params(length=0, labelsize=9)
    # 图底：种子 + 加权重建 MAE + 实际还原差值（审查 2026-08-01：显示真实 |Δ|）
    rebuilt = float((matrix * counts).sum() / counts.sum())
    g_mae = float(m["global"]["mae"])
    delta = abs(rebuilt - g_mae)
    ax.text(0.5, -0.13,
            f"seed 2024 · Σ(格MAE×n)/Σn = {rebuilt:.4f} · 全局 MAE = {g_mae:.4f}"
            f" · |Δ| = {delta:.2e}",
            transform=ax.transAxes, ha="center", va="top", fontsize=7.5,
            color=GRAY_D)
    final(fig, "fig4_4_four_cell", (5.0, 4.4))


# ========== ⑦ fig5_3 方向不对称（重设计：45° 对称散点） ==========
def redraw_asymmetry() -> None:
    te = json.load(open("outputs/analysis/transfer_entropy/transfer_entropy_summary.json"))
    node_ids = list(BUNDLE.node_ids)
    te_mat = np.array(te["te_matrix"])
    # 显著有向边集合（用于着色）
    sig_pairs = {(e["source"], e["target"]) for e in te["significant_edges"]}
    # 45 个无向节点对（i<j），双向 TE
    xs, ys, sigs, labels_top = [], [], [], []
    for i in range(len(node_ids)):
        for j in range(i + 1, len(node_ids)):
            xs.append(te_mat[i, j])
            ys.append(te_mat[j, i])
            sigs.append((node_ids[i], node_ids[j]) in sig_pairs
                        or (node_ids[j], node_ids[i]) in sig_pairs)
    xs, ys = np.array(xs), np.array(ys)
    sigs = np.array(sigs)

    fig, ax = plt.subplots(figsize=(6.2, 5.2))
    # 45° 对称参考线（完全对称 = 线上）
    vmax = max(xs.max(), ys.max())
    ax.plot([0, vmax * 1.1], [0, vmax * 1.1], color=GRAY_D, lw=1.0, ls="--", zorder=2)
    # 显著对（深蓝实心）与非显著对（浅灰空心）
    ax.scatter(xs[~sigs], ys[~sigs], s=55, facecolor="white", edgecolor=GRAY_L,
               linewidth=1.0, zorder=3)
    ax.scatter(xs[sigs], ys[sigs], s=75, facecolor=BLUE, edgecolor=GRAY_D,
               linewidth=0.6, zorder=4)
    # 高不对称对标注（top 3）
    asym = te["asymmetry"]["top_asymmetric_pairs"][:3]
    for p in asym:
        i, j = node_ids.index(p["node_i"]), node_ids.index(p["node_j"])
        ax.annotate(f"{p['node_i'].split('-')[1]} vs {p['node_j'].split('-')[1]}",
                    xy=(te_mat[i, j], te_mat[j, i]), xytext=(te_mat[i, j] + vmax * 0.06,
                                                              te_mat[j, i] + vmax * 0.04),
                    fontsize=7.5, color=GRAY_D,
                    arrowprops=dict(arrowstyle="-", color=GRAY_M, lw=0.7))
    # 不对称方向说明（必要说明文字）
    ax.text(vmax * 0.62, vmax * 1.0, "j→i 主导", fontsize=8, color=BLUE)
    ax.text(vmax * 0.08, vmax * 0.55, "i→j 主导", fontsize=8, color=BLUE)
    ax.text(vmax * 0.52, vmax * 0.30, "对称线", fontsize=7.5, color=GRAY_M)
    ax.set_xlabel("传递熵 TE(i → j)", fontsize=9)
    ax.set_ylabel("传递熵 TE(j → i)", fontsize=9)
    ax.set_xlim(0, vmax * 1.12)
    ax.set_ylim(0, vmax * 1.12)
    ax.tick_params(labelsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    # 图例（显著/非显著）
    ax.legend(handles=[plt.scatter([], [], s=75, facecolor=BLUE, edgecolor=GRAY_D,
                                   label="显著边"),
                       plt.scatter([], [], s=55, facecolor="white", edgecolor=GRAY_L,
                                   label="非显著边")],
              fontsize=8, frameon=False, loc="upper left")
    final(fig, "fig5_4_asymmetry", (6.2, 5.2))


# ========== ⑧ fig5_4 覆盖率（重设计：哑铃图） ==========
def redraw_coverage() -> None:
    c = json.load(open("outputs/analysis/conformal_prediction/conformal_summary.json"))
    groups = ["全局", "事件窗口", "稳定窗口"]
    std_v = [c["standard_overall_mean"], c["standard_event_mean"], c["standard_stable_mean"]]
    str_v = [c["stratified_overall_mean"], c["stratified_event_mean"], c["stratified_stable_mean"]]

    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    y = np.arange(len(groups))
    for yi, (s, v) in enumerate(zip(std_v, str_v)):
        # 连接线（标准 → 分层）
        ax.plot([s, v], [yi, yi], color=GRAY_L, lw=2.2, zorder=2)
        # 标准点（灰圆）
        ax.scatter([s], [yi], s=90, facecolor="white", edgecolor=GRAY_D,
                   linewidth=1.4, zorder=3, label="标准共形" if yi == 0 else None)
        # 分层点（深蓝圆）
        ax.scatter([v], [yi], s=110, facecolor=BLUE, edgecolor=GRAY_D,
                   linewidth=1.0, zorder=4, label="分层共形" if yi == 0 else None)
        # 数值标签：标准在左、分层在右（事件窗口重点强调）
        ax.text(s - 0.035, yi, f"{s:.1%}", ha="center", va="center",
                fontsize=8.5, color=GRAY_M)
        ax.text(v + 0.035, yi, f"{v:.1%}", ha="center", va="center",
                fontsize=8.5, color=GRAY_D, fontweight="bold" if yi == 1 else "normal")
    # 90% 目标线
    ax.axvline(0.9, color=RED_S, lw=1.2, ls="--", zorder=1)
    ax.text(0.905, 2.32, "90% 目标", fontsize=7.5, color=RED_S)
    # 事件窗口提升强调
    ax.annotate("", xy=(str_v[1], 1.25), xytext=(std_v[1], 1.25),
                arrowprops=dict(arrowstyle="->", color=ORANGE, lw=1.6))
    ax.text((std_v[1] + str_v[1]) / 2, 1.42, "1.9% → 86.1%", ha="center",
            fontsize=8, color=ORANGE)
    ax.set_yticks(y)
    ax.set_yticklabels(groups, fontsize=9.5)
    ax.set_xlabel("覆盖率（α = 0.1）", fontsize=9)
    ax.set_xlim(0, 1.0)
    ax.set_ylim(-0.55, 2.55)
    ax.tick_params(labelsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(fontsize=8, frameon=False, loc="lower left", ncol=2)
    final(fig, "fig5_8_coverage", (6.4, 3.2))


# ========== ⑨ fig5_5 分位数（重绘：舒展） ==========
def redraw_quantile() -> None:
    c = json.load(open("outputs/analysis/conformal_prediction/conformal_summary.json"))
    s0 = c["per_seed"][0]
    q_global = s0["q_global_per_node"]
    q_event = s0["q_event_per_node"]

    fig, ax = plt.subplots(figsize=(6.6, 3.4))
    x = np.arange(10)
    w = 0.34
    ax.bar(x - w / 2, q_global, w, label="全局分位数", color=GRAY_L,
           edgecolor=GRAY_D, linewidth=0.5, zorder=3)
    ax.bar(x + w / 2, q_event, w, label="事件层分位数", color=BLUE,
           edgecolor=GRAY_D, linewidth=0.5, zorder=3)
    ax.set_xticks(x)
    ax.set_xticklabels([n.split("-")[1] for n in BUNDLE.node_ids], fontsize=8.5)
    ax.set_ylabel("90% 分位数（标准化残差）", fontsize=8.5)
    ax.legend(fontsize=8, frameon=False, loc="upper left")
    _clean_ax(ax)
    final(fig, "fig5_9_quantile_per_node", (6.6, 3.4))


if __name__ == "__main__":
    print("=== 批次 4：主文 4 张图重绘 ===")
    redraw_autocorrelation()
    redraw_distribution()
    redraw_event_timeline()
    redraw_model_comparison()
    print("批次 4 完成")
