"""论文图批次 5：8 张旧版图素雅重绘（提升复杂度 + 无遮挡）。

重绘清单（用户 2026-08-01 反馈"提升复杂度和美观度，图片文字不遮挡"）：
- fig2_4_load_heatmap   节点按活跃度排序 + Blues 色阶 + 天网格线 + 周末竖带
- fig2_6_weekly_curves  灰阶深蓝三节点 + 夜间底纹 + 周末底纹
- fig3_6_lre_matrices   统一节点标签 + 白网格线 + 关系名标注
- fig3_10_training_curve 素雅三曲线 + 早停虚线 + 不重叠终值标注
- fig3_12_alpha_convergence 素雅三曲线 + 收敛带 + 终值范围说明
- fig4_2_intervention   基线唯一强调（蓝）+ 干预中性灰 + 基线参考线 + 柱外百分比标注
- fig5_3_transfer_entropy 分层线宽圆环网络 + 强度图例 + 灰阶覆盖柱
- fig5_11_parameter_intervention 相对基线柱 + Blues 热力图 + 数值标注

统一规范：无标题、无文件名/代号、SVG+PNG 1200DPI、文字不遮挡图形。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.patheffects as pe
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
    # Matplotlib 把多行 path 数据写成带行尾空格的行；清理后 SVG 才能通过
    # 仓库的空白检查（git diff --check）。
    svg_path = FIG_DIR / f"{name}.svg"
    svg_path.write_text(
        "\n".join(line.rstrip() for line in svg_path.read_text(encoding="utf-8").splitlines()) + "\n",
        encoding="utf-8",
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
    # 节点按总活跃度排序（高 → 低）。显示时反转数组，使最高负荷节点位于图面顶部；
    # 热力图、右侧条形和节点标签共享同一 y 坐标，避免旧图中三者错位。
    order = np.argsort(-mat.sum(axis=1))
    display_order = order[::-1]
    norm = norm[display_order]
    node_ids = [BUNDLE.node_ids[i] for i in display_order]
    act = mat.sum(axis=1)[display_order]  # 总负荷，供右侧冗余编码

    fig, ax = plt.subplots(figsize=(7.4, 3.4))
    im = ax.imshow(norm, aspect="auto", cmap="Blues", origin="lower",
                   extent=[0, t / 96, 0, 10], vmin=0, vmax=1, interpolation='nearest')
    # 天网格线（每 96 步一条，浅灰不干扰）
    for d in range(1, 29):
        ax.axvline(d, color="0.55", lw=0.5, alpha=0.45, zorder=3)
    # 周末竖带按当地日历确定，而不是假定第 6、7 天必为周末。
    local_ts = pd.to_datetime(BUNDLE.timestamps_ns[:t], utc=True).tz_convert("America/Los_Angeles")
    x_days = (local_ts - local_ts[0]).total_seconds() / 86400.0
    first_day = local_ts[0].normalize()
    for day in pd.date_range(local_ts[0].normalize(), local_ts[-1].normalize(), freq="D"):
        if day.weekday() >= 5:
            x0 = (day - local_ts[0]).total_seconds() / 86400.0
            ax.axvspan(x0, x0 + 1.0, color=ORANGE, alpha=0.10, zorder=1)
    # 行间分隔线（浅灰）
    for r in range(1, 10):
        ax.axhline(r, color="0.55", lw=0.5, alpha=0.35, zorder=3)
    # 右侧冗余编码：在同一坐标轴中绘制 mini 条，确保与热力图行严格对齐。
    total_max = act.max()
    for r in range(10):
        w_ = 2.1 * act[r] / total_max
        ax.barh(r + 0.5, w_, left=28.1, height=0.86, color=BLUE, alpha=0.75,
                 zorder=4)

    ax.set_yticks(np.arange(10) + 0.5)
    ax.set_yticklabels([n.split("-")[1] for n in node_ids], fontsize=8)
    ax.set_xlim(0, 30.5)
    ax.set_xticks(range(0, 29, 7))
    ax.set_xlabel("距首个样本的时间（天；浅橙为当地周末）", fontsize=8.6)
    ax.tick_params(labelsize=8)
    cbar = fig.colorbar(im, ax=ax, fraction=0.028, pad=0.02)
    cbar.set_label("归一化负荷（按节点最大值）", fontsize=7.5)
    cbar.ax.tick_params(labelsize=7)
    # mini bar 标签（审查 2026-08-01：明确右侧条形语义，避免误读为时间轴延续）
    ax.text(29.25, 10.15, "累计负荷", fontsize=7.5, color=GRAY_D,
            ha="center")
    final(fig, "fig2_3_load_heatmap", (7.4, 3.4))


# ========== ② fig2_4 典型周曲线（重绘） ==========
def fig_weekly_curves() -> None:
    # 三节点：CA-303 最活跃（深蓝）、CA-489 居中（中灰）、CA-311 最低（浅灰点线）
    nodes = ["CA-303", "CA-489", "CA-311"]
    t0 = 96 * 30
    local_ts = pd.to_datetime(BUNDLE.timestamps_ns[t0:t0 + 96 * 7], utc=True).tz_convert("America/Los_Angeles")
    t = (local_ts - local_ts[0]).total_seconds() / 86400.0
    fig, ax = plt.subplots(figsize=(7.0, 3.2))
    # 夜间与周末按当地时钟绘制，避免起始样本不是周一时发生日历错位。
    first_day = local_ts[0].normalize()
    for day in pd.date_range(local_ts[0].normalize(), local_ts[-1].normalize(), freq="D"):
        x0 = (day - local_ts[0]).total_seconds() / 86400.0
        ax.axvspan(x0, x0 + 0.25, color="0.88", alpha=0.55, zorder=0)
        if day.weekday() >= 5:
            ax.axvspan(x0, x0 + 1.0, color=ORANGE, alpha=0.10, zorder=0)
    for n, c, ls, lw in zip(nodes, [BLUE, GRAY_M, GRAY_D], ["-", "--", "-."],
                            [1.7, 1.4, 1.4]):
        idx = list(BUNDLE.node_ids).index(n)
        ax.plot(t, BUNDLE.targets[t0:t0 + 96 * 7, idx], color=c, ls=ls, lw=lw,
                label=n)
    ax.set_xlabel("距首个样本的时间（天；浅灰为当地00–06时，浅橙为周末）", fontsize=9)
    ax.set_ylabel("负荷（kWh/15 min）", fontsize=9)
    ax.set_xlim(0, 7)
    ax.set_xticks(range(8))
    ax.tick_params(labelsize=8)
    _clean_ax(ax)
    ax.legend(fontsize=8, frameon=False, ncol=3, loc="upper left",
              bbox_to_anchor=(0.0, 0.97))
    final(fig, "fig2_5_weekly_curves", (7.0, 3.2))


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
    final(fig, "fig3_5_lre_matrices", (7.6, 3.6))


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
        ax.plot(epochs, vals, color=c, ls=ls, lw=1.6, label=f"{s} 运行")
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
    final(fig, "fig3_10_training_curve", (6.6, 3.4))


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
        ax.plot(epochs, alpha, color=c, ls=ls, lw=1.6, label=f"{s} 运行")
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
    final(fig, "fig3_12_alpha_convergence", (6.6, 3.4))


# ========== ⑥ fig4_2 门控干预结果（重绘：基线唯一强调 + 干预中性灰） ==========
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

    # 画布直接取论文版心尺寸（版心宽 14.66 cm，图按 5.59 in 排版），fontsize 参数
    # 即为纸面字号；若按 7.0 in 画布绘制再等比压到版心，8 pt 会被压成约 6.4 pt。
    # 用 fig.add_axes 而非 plt.subplots：matplotlib 3.11 下由 subplots 创建的
    # axes 在 dpi=1200 导出 PNG 时 get_tightbbox 会被算成整幅画布（实测 PNG 宽
    # 5.736 in，而 SVG 为 5.424 in，同图两格式不一致），add_axes 无此问题。
    fig = plt.figure(figsize=(5.72, 3.60), constrained_layout=False)
    # 左侧留白须容纳最长标签“两层全负荷关系”（约 0.92 in，含刻度间距）且不被
    # bbox_inches="tight" 计入图宽；右侧 0.975 由数值标注的伸展空间决定。
    ax = fig.add_axes([0.1765, 0.163, 0.7985, 0.812])
    y = np.arange(len(order))
    # 颜色语义：蓝色只属于“学习值”基线（模型实际部署的门控配置）；7 个干预变体
    # 同属“被迫偏离学习门控”一类，统一用中性灰承载。理由：(1) 大面积高饱和红会
    # 造成压迫感，且红色在学术图中通常暗示“错误/危险”，处处红等于处处不红；
    # (2) 干预行序并非按退化幅度排列（单层类→两层全换类→等权类），按幅度打灰阶
    # 会与柱长重复编码，并把明暗噪声误读为分组信息；(3) 选比 GRAY_M 更浅的
    # #B4B4B4（L*≈73）是为压低整版灰度体量、同时保证转灰度后基线（L*≈39）
    # 仍是全场最深条，清晰可辨。
    iv_gray = "#B4B4B4"
    colors = [BLUE if k == "learned" else iv_gray for k in order]
    ax.barh(y, maes, height=0.58, color=colors, edgecolor=GRAY_M,
            linewidth=0.4, zorder=3)
    # 误差棒：干预柱为浅灰底，深灰误差棒本就清晰，不加描边（描边会让误差棒
    # 在高倍放大下显出“空心白框”）。仅基线误差棒（±0.00019）几乎整段压在
    # 深蓝柱上、与柱色对比不足，单独补白色描边，使其在蓝柱与白底上都可读。
    ax.errorbar(maes[1:], y[1:], xerr=stds[1:], fmt="none", ecolor=GRAY_D,
                capsize=2.5, lw=0.9, zorder=4)
    eb0 = ax.errorbar(maes[0], y[0], xerr=stds[0], fmt="none", ecolor=GRAY_D,
                      capsize=2.5, lw=0.9, zorder=4)
    for artist in list(eb0[1]) + list(eb0[2]):
        artist.set_path_effects([pe.Stroke(linewidth=1.5, foreground="white"),
                                 pe.Normal()])
    # 数值标注放柱外右侧（不遮挡柱体与误差棒）；文字颜色随所属条形，
    # 与颜色编码形成呼应，同时保证不依赖颜色也能读出数值。
    for yi, (m, k) in enumerate(zip(maes, order)):
        if k == "learned":
            label = f"{m:.4f}（基准）"
        else:
            label = f"+{100 * (m / base - 1):.0f}%"
        ax.text(m + stds[yi] + 0.0012, yi, label, va="center", fontsize=8.5,
                color=BLUE if k == "learned" else GRAY_D)
    # 基线参考虚线：落在学习值处，与蓝色基线柱共同锚定“未干预”参考位置
    ax.axvline(base, color=GRAY_M, lw=1.0, ls=":", zorder=2)
    ax.set_yticks(y)
    ax.set_yticklabels([labels_cn[k] for k in order], fontsize=8.5)
    ax.set_xlim(0, max(maes) * 1.30)
    _clean_ax(ax, xlabel="全局 MAE（kWh/15 min，3 种子均值 ± std）")
    ax.tick_params(axis="x", labelsize=8.5)
    final(fig, "fig4_3_intervention", (5.72, 3.60))


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

    # 画布取论文显示尺寸（版心宽 14.66 cm = 5.77 in，图按 5.59 in 排版），
    # fontsize 参数即为纸面字号；按 7.6 in 画布绘制再等比缩小会把 6.4pt 压到 5.0pt。
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(5.59, 3.40),
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
        ax1.scatter(x, y, s=400, color="white", edgecolor=BLUE, lw=1.2, zorder=5)
        # 节点圆直径约 22 pt，容不下"CA-313"这类 6 字符标签，故只留编号
        # （与图 5-3、5-5 的节点写法一致，站点前缀见图注）。
        ax1.text(x, y, n.split("-")[1], ha="center", va="center", fontsize=6.4,
                 color=GRAY_D, zorder=6)
    # 节点铺满整个圆周：图例置于图内任一角落都会与节点相撞（左下压 321、左上压 307），
    # 故不设图例，线宽语义并入图下说明文字。
    ax1.set_xlim(-1.32, 1.32)
    ax1.set_ylim(-1.32, 1.32)
    ax1.set_aspect("equal")
    ax1.axis("off")
    # 分两行：单行约 45 字在 2.9 in 宽的面板内会被裁切。
    ax1.text(0, -1.42,
             "箭头表示方向性候选，线宽表示 TE 强度\n"
             f"主图展示 TE 最强 {len(edges_draw)} 条有向边（共 {len(edges)} 条）",
             ha="center", va="top", fontsize=6.8, color=GRAY_M, linespacing=1.6)

    # (b) 统计图覆盖 vs 因果独有边（灰阶柱 + 柱顶数值；措辞收敛为"候选"，
    # 审查 2026-08-01：TE 未做多重比较校正，不称"显著因果边"；
    # 审查 2026-08-03：统一无向对口径——覆盖统计仅有无向对维度
    # （33+12=45=undirected_pairs），76 为有向边数，混用会误导）
    ov = te["overlap"]
    vals = [ov["undirected_pairs"], ov["covered_by_any_statistical_graph"],
            ov["exclusive_to_causal"]]
    bars = ax2.bar(["TE 候选对", "统计图覆盖对", "统计图未覆盖对"], vals,
                   color=["#55606A", "#8C979E", "#C8C8C8"], edgecolor="white",
                   linewidth=0.6, width=0.55, zorder=3)
    for b, v in zip(bars, vals):
        ax2.text(b.get_x() + b.get_width() / 2, v + 1.2, str(v), ha="center",
                 fontsize=9, color=GRAY_D)
    ax2.set_ylim(0, 60)
    ax2.set_ylabel("边数", fontsize=8.5)
    ax2.tick_params(axis="x", labelsize=8, rotation=12)
    _clean_ax(ax2)
    # 左右口径不同（左为有向边、右为无向对），此处只保留口径澄清；
    # 置换检验与校正说明已由图注承担，避免长脚注撑破面板宽度。
    ax2.text(0.5, -0.20, "右图按无向节点对统计（左图为有向边）",
             transform=ax2.transAxes, ha="center", va="top", fontsize=6.5,
             color=GRAY_M)
    final(fig, "fig5_2_transfer_entropy", (5.59, 3.40))


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

    # 画布取论文显示尺寸：版心宽 14.66 cm = 5.77 in，图按 5.59 in 排版，
    # 故 fontsize 参数即为纸面字号。本图内容量最大，改用上下布局——横向分割时
    # 热图 10 列每列仅约 0.28 in，容不下格内百分比数值；上下布局下每列约 0.44 in。
    fig = plt.figure(figsize=(5.72, 6.52), constrained_layout=False)
    # y 轴标签最长为“GCN2=模式关系”（约 0.68 in），须在 axes 内显式预留宽度，
    # 否则标签溢出会被 bbox_inches="tight" 计入图宽，使成品宽于版心。
    ax1 = fig.add_axes([0.132, 0.598, 0.745, 0.330])
    ax2 = fig.add_axes([0.132, 0.082, 0.745, 0.400])
    # (a) 分层参数干预敏感度：柱高 = 相对 MAE 变化率（%），正值表示退化。
    # 修复（审查 2026-08-01）：global_delta 已为 (MAE_iv−MAE_base)/MAE_base 变化率，
    # 绘图不得再减 1（原实现把 +149% 画成 +49%）
    y = np.arange(len(order))
    w = 0.25
    g_d = [100 * iv[k]["global_delta"] for k in order]
    e_d = [100 * iv[k]["event_delta"] for k in order]
    s_d = [100 * iv[k]["stable_delta"] for k in order]
    ax1.barh(y - w, g_d, w, label="全局", color=BLUE, edgecolor="white", linewidth=0.3)
    ax1.barh(y, e_d, w, label="事件窗口", color=ORANGE, edgecolor="white", linewidth=0.3)
    ax1.barh(y + w, s_d, w, label="稳定窗口", color=GRAY_M, edgecolor="white", linewidth=0.3)
    ax1.axvline(0, color=GRAY_D, lw=1.0)
    # 仅标注全局柱数值：三类窗口全标会互相压盖，且事件/稳定窗口的对比已由柱长表达。
    for yi, v in zip(y, g_d):
        ax1.text(v + 6, yi - w, f"{v:+.0f}%", va="center", fontsize=6.8,
                 color=GRAY_D)
    ax1.set_yticks(y)
    ax1.set_yticklabels([names_cn[k] for k in order], fontsize=7.2)
    ax1.invert_yaxis()
    ax1.set_xlabel("相对 MAE 变化（%）", fontsize=8.0)
    # y 轴范围按全部窗口的最大/最小值确定（修复 2026-08-01：原按 max(g_d) 定上限，
    # 稳定窗口 delta 最大 317% 超出 285% 被 clip-path 裁切）
    all_deltas = np.concatenate([g_d, e_d, s_d])
    ymax = float(np.max(all_deltas))
    ymin = min(-8.0, float(np.min(all_deltas)) * 1.15)
    ax1.set_xlim(ymin, ymax * 1.16)
    # 水平条形图需竖向网格线，故不使用 _clean_ax 的 grid(axis="y")。
    ax1.spines[["top", "right"]].set_visible(False)
    ax1.spines[["left", "bottom"]].set_color(GRAY_D)
    ax1.tick_params(labelsize=7.2, colors=GRAY_D)
    ax1.grid(axis="x", color=GRAY_L, lw=0.55, alpha=0.72)
    ax1.set_axisbelow(True)
    ax1.legend(fontsize=7.2, frameon=False, loc="lower right")
    ax1.text(0.0, 1.05, "(a) 分层干预敏感度（正值表示相对学习值退化）",
             transform=ax1.transAxes, ha="left", va="bottom", fontsize=8.6,
             fontweight="bold", color=GRAY_D)

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
    ax2.set_xticklabels([n.split("-")[1] for n in nodes], fontsize=7.2)
    ax2.set_yticks(range(len(order)))
    ax2.set_yticklabels([names_cn[k] for k in order], fontsize=7.2)
    for i in range(len(order)):
        for j in range(len(nodes)):
            v = matrix[i, j]
            ax2.text(j, i, f"{v:.0f}%", ha="center", va="center", fontsize=6.5,
                     color="white" if v > matrix.max() * 0.62 else GRAY_D)
    ax2.set_xlabel("节点编号", fontsize=8.0)
    cbar = fig.colorbar(im, ax=ax2, fraction=0.032, pad=0.022)
    cbar.set_label("MAE 相对变化（%）", fontsize=7.2)
    cbar.ax.tick_params(labelsize=6.8)
    ax2.text(0.0, 1.05, "(b) 逐节点干预敏感度（7 种干预 × 10 节点）",
             transform=ax2.transAxes, ha="left", va="bottom", fontsize=8.6,
             fontweight="bold", color=GRAY_D)
    final(fig, "fig5_9_parameter_intervention", (5.72, 6.52))


if __name__ == "__main__":
    print("=== 批次 5：主文 6 张图素雅重绘 ===")
    fig_load_heatmap()
    fig_weekly_curves()
    fig_lre_matrices()
    fig_intervention()
    fig_transfer_entropy()
    fig_parameter_intervention()
    print("批次 5 完成")
