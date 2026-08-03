"""论文图批次 5：8 张旧版图素雅重绘（提升复杂度 + 无遮挡）。

重绘清单（用户 2026-08-01 反馈"提升复杂度和美观度，图片文字不遮挡"）：
- fig2_3_load_heatmap   节点按活跃度排序 + Blues 色阶 + 天网格线 + 周末竖带
- fig2_4_weekly_curves  灰阶深蓝三节点 + 夜间底纹 + 周末底纹
- fig3_3_lre_matrices   统一节点标签 + 白网格线 + 关系名标注
- fig3_5_training_curve 素雅三曲线 + 早停虚线 + 不重叠终值标注
- fig3_7_alpha_convergence 素雅三曲线 + 收敛带 + 终值范围说明
- fig4_2_intervention   语义色（基线蓝/恶化红）+ 基线参考线 + 柱外百分比标注
- fig5_2_transfer_entropy 分层线宽圆环网络 + 强度图例 + 灰阶覆盖柱
- fig5_6_parameter_intervention 相对基线柱 + Blues 热力图 + 数值标注

统一规范：无标题、无文件名/代号、SVG+PNG 1200DPI、文字不遮挡图形。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

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
# 素雅配色（对齐 batch4：深蓝主色 + 灰阶 + 低饱和强调）
BLUE = "#2C5F8A"      # 深蓝（主色）
ORANGE = "#D08A3C"    # 低饱和橙
GRAY_D = "#404040"    # 深灰
GRAY_M = "#808080"    # 中灰
GRAY_L = "#C8C8C8"    # 浅灰
RED_S = "#B05A4A"     # 低饱和红（恶化）
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


# ========== ① fig2_3 节点负荷热力图（重绘） ==========
def fig_load_heatmap() -> None:
    t = 2688  # 连续 4 周
    mat = BUNDLE.targets[:t].T  # [N, T]
    vmax = mat.max(axis=1, keepdims=True)
    norm = mat / np.maximum(vmax, 1e-9)
    # 节点按总活跃度排序（高 → 低），让时间模式更有序
    order = np.argsort(-mat.sum(axis=1))
    norm = norm[order]
    node_ids = [BUNDLE.node_ids[i] for i in order]
    act = mat.sum(axis=1)[order]  # 总负荷，供右侧冗余编码

    fig, ax = plt.subplots(figsize=(7.4, 3.4))
    im = ax.imshow(norm, aspect="auto", cmap="Blues", extent=[0, t / 96, 0, 10],
                   vmin=0, vmax=1)
    # 天网格线（每 96 步一条，浅灰不干扰）
    for d in range(1, 29):
        ax.axvline(d, color="0.55", lw=0.5, alpha=0.45, zorder=3)
    # 周末竖带（每周第 5-6 天，浅橙底纹）
    for w in range(4):
        ax.axvspan(5 + 7 * w, 7 + 7 * w, color=ORANGE, alpha=0.10, zorder=1)
    # 行间分隔线（浅灰）
    for r in range(1, 10):
        ax.axhline(r, color="0.55", lw=0.5, alpha=0.35, zorder=3)
    # 右侧冗余编码：每节点总负荷 mini 条（专用区域 x∈(28,30.5]，不覆盖热力图）
    ax2 = ax.twinx()
    total_max = act.max()
    ax2.set_xlim(28, 30.5)
    for r in range(10):
        w_ = 2.1 * act[r] / total_max
        ax2.barh(r + 0.5, w_, left=28.1, height=0.96, color=BLUE, alpha=0.75,
                 zorder=4)
    ax2.set_yticks([])
    ax2.set_xticks([])
    for s in ax2.spines.values():
        s.set_visible(False)

    ax.set_yticks(np.arange(10) + 0.5)
    ax.set_yticklabels([n.split("-")[1] for n in node_ids], fontsize=8)
    ax.set_xticks(range(0, 29, 7))
    ax.set_xlabel("时间（天，周末浅橙底纹，节点按累计负荷降序）", fontsize=9)
    ax.tick_params(labelsize=8)
    cbar = fig.colorbar(im, ax=ax, fraction=0.028, pad=0.02)
    cbar.set_label("归一化负荷（按节点最大值）", fontsize=7.5)
    cbar.ax.tick_params(labelsize=7)
    # mini bar 标签（审查 2026-08-01：明确右侧条形语义，避免误读为时间轴延续）
    ax.text(29.25, 10.15, "节点累计负荷", fontsize=7.5, color=GRAY_D,
            ha="center")
    final(fig, "fig2_3_load_heatmap", (7.4, 3.4))


# ========== ② fig2_4 典型周曲线（重绘） ==========
def fig_weekly_curves() -> None:
    # 三节点：CA-303 最活跃（深蓝）、CA-489 居中（中灰）、CA-311 最低（浅灰点线）
    nodes = ["CA-303", "CA-489", "CA-311"]
    t0 = 96 * 30
    t = np.arange(96 * 7) / 96.0
    fig, ax = plt.subplots(figsize=(7.0, 3.2))
    # 夜间底纹：每日 0-6 时浅灰竖带（负荷低谷时段）
    for d in range(7):
        ax.axvspan(d, d + 0.25, color="0.88", alpha=0.55, zorder=0)
    # 周末底纹：第 6-7 天浅橙
    ax.axvspan(5, 7, color=ORANGE, alpha=0.10, zorder=0)
    for n, c, ls, lw in zip(nodes, [BLUE, GRAY_M, GRAY_D], ["-", "--", "-."],
                            [1.7, 1.4, 1.4]):
        idx = list(BUNDLE.node_ids).index(n)
        ax.plot(t, BUNDLE.targets[t0:t0 + 96 * 7, idx], color=c, ls=ls, lw=lw,
                label=n)
    ax.set_xlabel("时间（天；浅灰=夜间低谷时段，浅橙=周末）", fontsize=9)
    ax.set_ylabel("负荷（kWh/15 min）", fontsize=9)
    ax.set_xlim(0, 7)
    ax.set_xticks(range(8))
    ax.tick_params(labelsize=8)
    _clean_ax(ax)
    ax.legend(fontsize=8, frameon=False, ncol=3, loc="upper left",
              bbox_to_anchor=(0.0, 0.97))
    final(fig, "fig2_4_weekly_curves", (7.0, 3.2))


# ========== ③ fig3_3 三关系邻接矩阵（重绘） ==========
def fig_lre_matrices() -> None:
    d = np.load("outputs/experiments/SG-EXP-004/20260731-102456/relation_matrices.npz")
    # 图名精确化（审查 2026-08-01）：abs-Pearson / 余弦 / 轮廓欧氏指数核
    names = {"load": "负荷耦合（|Pearson|）", "event": "行为共现（cosine）",
             "pattern": "轮廓相似（指数核）"}
    vmax_all = max(d[k].max() for k in names)
    fig, axes = plt.subplots(1, 3, figsize=(7.6, 3.2))
    im = None
    for ax, (key, cn) in zip(axes, names.items()):
        mat = d[key]
        im = ax.imshow(mat, cmap="Blues", aspect="equal", vmin=0, vmax=vmax_all)
        # 白色 cell 网格线（热力图标准做法，分隔矩阵单元）
        ax.set_xticks(np.arange(10) - 0.5, minor=True)
        ax.set_yticks(np.arange(10) - 0.5, minor=True)
        ax.grid(which="minor", color="white", lw=1.4)
        ax.tick_params(which="minor", length=0)
        # 关系名放在每个面板上方，避免压住热力图单元。
        ax.text(0.5, 1.04, cn, transform=ax.transAxes, ha="center", va="bottom",
                fontsize=7.5, color=GRAY_D, fontweight="bold")
        ax.set_xticks(range(10))
        ax.set_xticklabels(BUNDLE.node_ids, fontsize=6.2, rotation=45, ha="right")
        ax.set_yticks(range(10))
        ax.set_yticklabels(BUNDLE.node_ids, fontsize=6.2)
        ax.tick_params(which="major", labelsize=6.2)
    cbar = fig.colorbar(im, ax=axes, fraction=0.022, pad=0.03)
    cbar.set_label("关系权重（统一色阶）", fontsize=7.5)
    cbar.ax.tick_params(labelsize=7)
    fig.subplots_adjust(bottom=0.30, top=0.86)
    final(fig, "fig3_3_lre_matrices", (7.6, 3.6))


# ========== ④ fig3_5 训练收敛曲线（重绘） ==========
def fig_training_curve() -> None:
    fig, ax = plt.subplots(figsize=(6.6, 3.4))
    seeds = ["2024", "2025", "2026"]
    styles = [(BLUE, "-"), (GRAY_D, "--"), (ORANGE, "-.")]
    stop_epochs = []
    for s, (c, ls) in zip(seeds, styles):
        f = next(Path("outputs/experiments/SG-EXP-004").glob(f"*/seed-{s}/training_log.csv"))
        df = pd.read_csv(f)
        epochs = df["epoch"]
        vals = df["validation_mae_scaled"]
        ax.plot(epochs, vals, color=c, ls=ls, lw=1.6, label=f"seed {s}")
        # 末端菱形标记；终值统一放到图内说明，避免不同 seed 标注相互覆盖。
        ax.plot(epochs.iloc[-1], vals.iloc[-1], marker="D", ms=4.5, color=c,
                zorder=5)
        stop_epochs.append(epochs.iloc[-1])
    # 早停虚线（取最晚早停轮次，落在数据范围内）
    ax.axvline(max(stop_epochs), color=GRAY_L, lw=0.9, ls="--", zorder=1)
    # 早停含义在图注中说明；图内保留竖虚线，避免文字与右上角图例重叠。
    ax.set_xlabel("训练轮次（epoch）", fontsize=9)
    ax.set_ylabel("验证 MAE（标准化尺度）", fontsize=9)
    ax.set_xlim(0, max(stop_epochs) + 6)
    _clean_ax(ax)
    ax.legend(fontsize=8, frameon=False, ncol=3, loc="upper right")
    terminal = "；".join(f"{s}={v:.4f}" for s, v in zip(seeds, [
        float(pd.read_csv(next(Path("outputs/experiments/SG-EXP-004").glob(f"*/seed-{s}/training_log.csv")))
              ["validation_mae_scaled"].iloc[-1]) for s in seeds]))
    ax.text(0.02, 0.04, f"末值（验证 MAE）：{terminal}", transform=ax.transAxes,
            fontsize=6.5, color=GRAY_M, ha="left")
    final(fig, "fig3_5_training_curve", (6.6, 3.4))


# ========== ⑤ fig3_7 α 混合系数收敛（重绘） ==========
def fig_alpha_convergence() -> None:
    fig, ax = plt.subplots(figsize=(6.6, 3.4))
    seeds = ["2024", "2025", "2026"]
    styles = [(BLUE, "-"), (GRAY_D, "--"), (ORANGE, "-.")]
    finals = []
    for s, (c, ls) in zip(seeds, styles):
        f = next(Path("outputs/experiments/SG-EXP-004").glob(f"*/seed-{s}/training_log.csv"))
        df = pd.read_csv(f)
        epochs = df["epoch"]
        alpha = df["adaptive_graph_alpha"]
        ax.plot(epochs, alpha, color=c, ls=ls, lw=1.6, label=f"seed {s}")
        ax.plot(epochs.iloc[-1], alpha.iloc[-1], marker="o", ms=4.5, color=c,
                zorder=5)
        finals.append(alpha.iloc[-1])
    # 收敛带：三种子末值范围。A_mix = α·A_fixed + (1-α)·A_adp（graph.py），
    # α 是固定图权重——α≈0.17-0.21 表示内部邻接混合以自适应为主；
    # 收缩措辞（审查 2026-08-01）：固定图还经门控层独立输入，α 不概括整网依赖
    lo, hi = min(finals), max(finals)
    ax.axhspan(lo, hi, color="0.88", alpha=0.7, zorder=0)
    ax.text(0.02, 0.04,
            f"α 终值范围 {lo:.3f}–{hi:.3f}（3 种子；内部邻接混合）",
            transform=ax.transAxes, fontsize=7, color=GRAY_M, ha="left")
    ax.set_xlabel("训练轮次（epoch）", fontsize=9)
    ax.set_ylabel("固定图混合权重 α = σ(w)", fontsize=9)
    ax.set_xlim(0, max(df["epoch"]) + 6)
    _clean_ax(ax)
    ax.legend(fontsize=8, frameon=False, ncol=3, loc="upper right")
    final(fig, "fig3_7_alpha_convergence", (6.6, 3.4))


# ========== ⑥ fig4_2 门控干预结果（重绘：语义色 + 柱外标注） ==========
def fig_intervention() -> None:
    d = json.load(open("outputs/analysis/gate_intervention/intervention_summary.json"))
    order = ["learned", "equal", "both_load", "both_pattern", "both_event",
             "g1_load_g2_learn", "g1_learn_g2_pattern", "swapped"]
    labels_cn = {
        "learned": "学习值（基线）", "equal": "等权 1/3",
        "both_load": "两层全负荷关系", "both_pattern": "两层全模式关系",
        "both_event": "两层全事件关系", "g1_load_g2_learn": "GCN1=负荷关系",
        "g1_learn_g2_pattern": "GCN2=模式关系", "swapped": "交换两层学习值",
    }
    maes = [d[k]["global_mae_mean"] for k in order]
    stds = [d[k]["global_mae_std"] for k in order]
    base = maes[0]

    fig, ax = plt.subplots(figsize=(7.0, 3.6))
    y = np.arange(len(order))
    # 语义色：基线深蓝，其余全部恶化 → 低饱和红
    colors = [BLUE if k == "learned" else RED_S for k in order]
    bars = ax.barh(y, maes, height=0.62, color=colors, edgecolor="white",
                   linewidth=0.5, zorder=3)
    ax.errorbar(maes, y, xerr=stds, fmt="none", ecolor=GRAY_D, capsize=3,
                lw=0.8, zorder=4)
    # 数值标注放柱外右侧（不遮挡柱体）
    for yi, (m, k) in enumerate(zip(maes, order)):
        if k == "learned":
            label = f"{m:.4f}（基准）"
        else:
            label = f"+{100 * (m / base - 1):.0f}%"
        ax.text(m + stds[yi] + 0.0012, yi, label, va="center", fontsize=8,
                color=GRAY_D)
    # 基线参考虚线（放柱顶端空白处标注）
    ax.axvline(base, color=GRAY_M, lw=1.0, ls=":", zorder=2)
    ax.set_yticks(y)
    ax.set_yticklabels([labels_cn[k] for k in order], fontsize=8)
    ax.set_xlabel("全局 MAE（kWh/15 min，3 种子均值 ± std）", fontsize=9)
    ax.set_xlim(0, max(maes) * 1.30)
    _clean_ax(ax)
    ax.grid(axis="y", color=GRAY_L, lw=0.5, alpha=0.6, zorder=0)
    final(fig, "fig4_2_intervention", (7.0, 3.6))


# ========== ⑦ fig5_2 传递熵方向性候选（探索性） ==========
def fig_transfer_entropy() -> None:
    te = json.load(open("outputs/analysis/transfer_entropy/transfer_entropy_summary.json"))
    edges = te["significant_edges"]
    nodes = sorted({e["source"] for e in edges} | {e["target"] for e in edges})
    node_pos = {n: (np.cos(2 * np.pi * i / len(nodes)), np.sin(2 * np.pi * i / len(nodes)))
                for i, n in enumerate(nodes)}
    te_max = max(e["te"] for e in edges)
    te_min = min(e["te"] for e in edges)
    # 边按强度排序：强边后画（压在上层），弱边先画（在下层）
    edges_sorted = sorted(edges, key=lambda e: e["te"])
    # 主图仅展示 TE 最强 15 条候选边（审查 2026-08-01：76 条全画成"毛线团"），
    # 完整边数在右侧柱状图保留
    edges_draw = edges_sorted[-15:]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.6, 3.8),
                                   gridspec_kw={"width_ratios": [1.3, 1.0]})
    # (a) 有向信息流网络：圆环布局，线宽+透明度双层编码 TE 强度（主图 top 15 边）
    for e in edges_draw:
        s, t = node_pos[e["source"]], node_pos[e["target"]]
        rel = (e["te"] - te_min) / max(te_max - te_min, 1e-9)
        w = 0.4 + 2.6 * rel
        alpha = 0.18 + 0.62 * rel
        ax1.annotate("", xy=t, xytext=s,
                     arrowprops=dict(arrowstyle="->", color=BLUE, lw=w, alpha=alpha,
                                     shrinkA=15, shrinkB=15,
                                     connectionstyle="arc3,rad=0.12"))
    for n, (x, y) in node_pos.items():
        ax1.scatter(x, y, s=330, color="white", edgecolor=BLUE, lw=1.2, zorder=5)
        ax1.text(x, y, n, ha="center", va="center", fontsize=6.2,
                 color=GRAY_D, zorder=6)
    # 强度图例（放左下空白区，不遮挡节点）
    import matplotlib.lines as mlines
    hi = mlines.Line2D([], [], color=BLUE, lw=2.8, alpha=0.75, ls="-")
    lo = mlines.Line2D([], [], color=BLUE, lw=0.6, alpha=0.25, ls="-")
    ax1.legend([hi, lo], ["TE 强（线宽大）", "TE 弱（线宽小）"], loc="lower left", fontsize=6.5,
               frameon=False, borderaxespad=0.2)
    ax1.set_xlim(-1.32, 1.32)
    ax1.set_ylim(-1.32, 1.32)
    ax1.set_aspect("equal")
    ax1.axis("off")
    ax1.text(0, -1.45,
             f"箭头表示方向性候选；主图展示 TE 最强 {len(edges_draw)} 条（共 {len(edges)} 条）",
             ha="center", fontsize=6.5, color=GRAY_M)

    # (b) 统计图覆盖 vs 因果独有边（灰阶柱 + 柱顶数值；措辞收敛为"候选"，
    # 审查 2026-08-01：TE 未做多重比较校正，不称"显著因果边"）
    ov = te["overlap"]
    vals = [ov["total_significant_edges"], ov["covered_by_any_statistical_graph"],
            ov["exclusive_to_causal"]]
    bars = ax2.bar(["TE 候选边", "统计图覆盖候选", "统计图未覆盖候选"], vals,
                   color=[GRAY_D, GRAY_M, GRAY_L], edgecolor="white",
                   linewidth=0.6, width=0.55, zorder=3)
    for b, v in zip(bars, vals):
        ax2.text(b.get_x() + b.get_width() / 2, v + 1.2, str(v), ha="center",
                 fontsize=9, color=GRAY_D)
    ax2.set_ylim(0, 90)
    ax2.set_ylabel("边数", fontsize=8.5)
    ax2.tick_params(axis="x", labelsize=8, rotation=12)
    _clean_ax(ax2)
    ax2.text(0.5, -0.22, "未做多重比较校正，正式因果结论以条件独立检验为准",
             transform=ax2.transAxes, ha="center", va="top", fontsize=6.5,
             color=GRAY_M)
    final(fig, "fig5_2_transfer_entropy", (7.6, 3.8))


# ========== ⑧ fig5_8 分层参数干预敏感度 ==========
def fig_parameter_intervention() -> None:
    cat = json.load(open("outputs/analysis/counterfactual_cate/counterfactual_cate_summary.json"))
    iv = cat["interventions"]
    names_cn = {
        "both_event": "全事件关系", "both_load": "全负荷关系", "both_pattern": "全模式关系",
        "equal": "等权 1/3", "g1_load_g2_learn": "GCN1=负荷关系",
        "g1_learn_g2_pattern": "GCN2=模式关系", "swapped": "交换两层学习值",
    }
    order = [k for k in iv if k in names_cn]
    nodes = list(iv[order[0]]["node_deltas"].keys())

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.8, 4.0),
                                   gridspec_kw={"width_ratios": [1.0, 1.35]})
    # (a) 分层参数干预敏感度：柱高 = 相对 MAE 变化率（%），正值表示退化。
    # 修复（审查 2026-08-01）：global_delta 已为 (MAE_iv−MAE_base)/MAE_base 变化率，
    # 绘图不得再减 1（原实现把 +149% 画成 +49%）
    x = np.arange(len(order))
    w = 0.26
    g_d = [100 * iv[k]["global_delta"] for k in order]
    e_d = [100 * iv[k]["event_delta"] for k in order]
    s_d = [100 * iv[k]["stable_delta"] for k in order]
    ax1.bar(x - w, g_d, w, label="全局", color=BLUE, edgecolor="white", linewidth=0.3)
    ax1.bar(x, e_d, w, label="事件窗口", color=ORANGE, edgecolor="white", linewidth=0.3)
    ax1.bar(x + w, s_d, w, label="稳定窗口", color=GRAY_M, edgecolor="white", linewidth=0.3)
    ax1.axhline(0, color=GRAY_D, lw=1.0)
    # 仅标注全局柱顶数值（避免 21 个标签互相遮挡）
    for xi, v in zip(x, g_d):
        ax1.text(xi, v + 3, f"{v:+.0f}%", ha="center", fontsize=7.2,
                 color=GRAY_D)
    ax1.set_xticks(x)
    ax1.set_xticklabels([names_cn[k] for k in order], fontsize=7.5, rotation=28,
                        ha="right")
    ax1.set_ylabel("相对 MAE 变化（%）", fontsize=8.5)
    # y 轴范围按全部窗口的最大/最小值确定（修复 2026-08-01：原按 max(g_d) 定上限，
    # 稳定窗口 delta 最大 317% 超出 285% 被 clip-path 裁切）
    all_deltas = np.concatenate([g_d, e_d, s_d])
    ymax = float(np.max(all_deltas))
    ymin = min(-8.0, float(np.min(all_deltas)) * 1.15)
    ax1.set_ylim(ymin, ymax * 1.15)
    _clean_ax(ax1)
    ax1.legend(fontsize=7.5, frameon=False, loc="upper left")

    # (b) 节点敏感度热力图（7 干预 × 10 节点，相对变化率 %；node_deltas 已为变化率，
    # 直接乘 100 显示百分比，不再做任何减 1）
    matrix = np.array([[100 * iv[k]["node_deltas"][n] for n in nodes] for k in order])
    im = ax2.imshow(matrix, cmap="Blues", aspect="auto", vmin=0,
                    vmax=matrix.max())
    # 白色 cell 网格线
    ax2.set_xticks(np.arange(len(nodes)) - 0.5, minor=True)
    ax2.set_yticks(np.arange(len(order)) - 0.5, minor=True)
    ax2.grid(which="minor", color="white", lw=1.4)
    ax2.tick_params(which="minor", length=0)
    ax2.set_xticks(range(len(nodes)))
    ax2.set_xticklabels([n.split("-")[1] for n in nodes], fontsize=7.5)
    ax2.set_yticks(range(len(order)))
    ax2.set_yticklabels([names_cn[k] for k in order], fontsize=7.5)
    for i in range(len(order)):
        for j in range(len(nodes)):
            v = matrix[i, j]
            ax2.text(j, i, f"{v:.0f}%", ha="center", va="center", fontsize=6.5,
                     color="white" if v > matrix.max() * 0.62 else GRAY_D)
    cbar = fig.colorbar(im, ax=ax2, fraction=0.045, pad=0.03)
    cbar.set_label("MAE 相对变化（%）", fontsize=7.5)
    cbar.ax.tick_params(labelsize=7)
    final(fig, "fig5_6_parameter_intervention", (7.8, 4.0))


if __name__ == "__main__":
    print("=== 批次 5：8 张图素雅重绘 ===")
    fig_load_heatmap()
    fig_weekly_curves()
    fig_lre_matrices()
    fig_training_curve()
    fig_alpha_convergence()
    fig_intervention()
    fig_transfer_entropy()
    fig_parameter_intervention()
    print("批次 5 完成")
