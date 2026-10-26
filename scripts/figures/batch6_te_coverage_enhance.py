"""论文图批次 6：fig5_3 方向不对称性 / fig5_7 共形覆盖率 重设计。

函数名与输出文件名一致：fig5_3_asymmetry() -> fig5_3_asymmetry.*，
fig5_7_coverage() -> fig5_7_coverage.*（历史重编号期间两者曾错位）。

fig5_3 方向不对称（v5：复杂版恢复 + 版心尺寸适配，画布 5.59 in 宽）：
- 主面板 45° 对称散点：符号化距离配色（线上方 j→i 主导蓝 / 下方 i→j 主导橙 / 对称带灰）
- 点面积编码平均 TE 强度
- 近似对称带（ASYM≤0.30 的比例边界，两条点线界定 + 浅色填充）+ 45° 参考线
- 顶部 + 右侧边缘直方图（与主图共享坐标轴，明确标注为横轴/纵轴分布）
- 1/2/3 编号联动：主图带圈编号，两个边缘分布中同位置用红色三角呼应
- 主面板按等比例坐标铺满正方形面板，45° 线在纸面上确为 45°
- 45 个无向节点对全部至少一方向达名义阈值 → "两方向均未达阈值"类别为空集，
  既不绘制也不进图例（空类别照画会让图例宣告数据中不存在的类别）

fig5_7 共形覆盖率（v3）：
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
from matplotlib.patches import Rectangle

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
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Hiragino Sans GB", "Arial", "DejaVu Sans", "sans-serif"],
    "svg.fonttype": "none",
    "pdf.fonttype": 42,
})
# 素雅配色
BLUE = "#2C5F8A"      # 深蓝（j→i 主导 / 分层共形）
ORANGE = "#D08A3C"    # 低饱和橙（i→j 主导）
GRAY_D = "#404040"    # 深灰
GRAY_M = "#808080"    # 中灰
GRAY_L = "#C8C8C8"    # 浅灰
RED_S = "#B05A4A"     # 低饱和红（目标线 / top 3 编号联动标记）
BUNDLE = load_tensor_bundle("data/processed/SG-DATA-005-primary-tensor.npz")


def final(fig, name: str, size: tuple[float, float]) -> None:
    """统一导出：SVG 矢量 + PNG 1200 DPI（论文硬性约束）。

    输入：fig（绘制完成的 Figure）、name（不含扩展名的文件名）、
          size=(宽, 高)/英寸，取论文版心宽 5.59 in，使 fontsize 即纸面字号。
    输出：outputs/figures/<name>.svg、.pdf 与 .png（PNG为1200 DPI）。
    边界：bbox_inches="tight" 会把画布裁到内容外框，成品宽度随之小于 size；
          这里先铺一层覆盖整张画布的隐形矩形（figure 级 artist，计入 tight bbox），
          并令 pad_inches=0，导出尺寸才严格等于 size。SVG 中 matplotlib 会写出行尾
          空格，导出后统一清理以通过仓库空白检查。
    """
    fig.set_size_inches(*size)
    fig.add_artist(Rectangle((0.0, 0.0), 1.0, 1.0, transform=fig.transFigure,
                             facecolor="none", edgecolor="none", linewidth=0.0))
    export_figure(
        fig, basename=str(FIG_DIR / name),
        formats=["svg", "png", "pdf"], dpi=1200, size_inches=size,
        grayscale_preview=False, pad_inches=0.0,
    )
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


# ========== fig5_3 方向不对称（v5：复杂版恢复 + 版心尺寸适配） ==========
def fig5_3_asymmetry() -> None:
    """绘制 fig5_3：双向传递熵与方向不对称性（画布取论文版心宽 5.59 in）。

    输入：outputs/analysis/transfer_entropy/transfer_entropy_summary.json
          （训练期 10 节点 TE 矩阵、显著有向边、不对称度 top 对）
          与 SG-DATA-005 张量的节点清单。
    输出：outputs/figures/fig5_3_asymmetry.svg 与 .png（1200 DPI）。
    边界：45 个无向节点对中"两方向均未达名义阈值"在当前数据里为空集，该类别
          不绘制、不进图例；任何类别为空时一律跳过，绝不画出数据中不存在的类别。
    """
    te = json.load(open("outputs/analysis/transfer_entropy/transfer_entropy_summary.json"))
    node_ids = [str(n) for n in BUNDLE.node_ids]
    te_mat = np.array(te["te_matrix"])
    sig_pairs = {(e["source"], e["target"]) for e in te["significant_edges"]}

    # ========== 阶段 1：整理 45 个无向节点对 ==========
    # 遍历顺序与 analyze_transfer_entropy.py 完全一致（i < j），
    # 这样 top 不对称对的下标回查、坐标取值都与分析产物一一对应。
    xs, ys, pairs = [], [], []
    for i in range(len(node_ids)):
        for j in range(i + 1, len(node_ids)):
            xs.append(te_mat[i, j])
            ys.append(te_mat[j, i])
            pairs.append((node_ids[i], node_ids[j]))
    xs, ys = np.array(xs), np.array(ys)
    # 轴上限留 15% 余量，使 45° 线端点与最外侧散点之间仍有余量
    axis_limit = float(max(xs.max(), ys.max())) * 1.15
    d = ys - xs                       # 符号化距离：正 = j→i 主导
    denom = xs + ys
    asym = np.divide(np.abs(d), denom + 1e-12,
                     out=np.zeros_like(d), where=denom > 0)
    avg = (xs + ys) / 2.0              # 点面积编码：双向平均 TE（绝对强度）
    asym_threshold = 0.30              # 与正文 ASYM > 0.3 的判定阈值一致
    both_sig = np.array([(a, b) in sig_pairs and (b, a) in sig_pairs for a, b in pairs])

    # 版心宽 5.59 in：figsize 直接等于纸面尺寸，fontsize 即纸面字号。
    # 主面板按等比例坐标取正方形（宽高都用 3.76 in），45° 线在纸面上才是 45°。
    fig_w, fig_h = 5.59, 5.72
    ax_left, ax_w, ax_bottom = 0.105, 0.672, 0.168
    ax_h = (ax_w * fig_w) / fig_h
    fig = plt.figure(figsize=(fig_w, fig_h))
    ax = fig.add_axes([ax_left, ax_bottom, ax_w, ax_h])
    # 顶部/右侧边缘分布与主图共享坐标轴，保证分箱位置与散点位置严格对齐
    ax_top = fig.add_axes([ax_left, ax_bottom + ax_h + 0.012, ax_w, 0.055], sharex=ax)
    ax_right = fig.add_axes([0.806, ax_bottom, 0.132, ax_h], sharey=ax)

    # ========== 阶段 2：主面板（对称带 / 参考线 / 分类散点） ==========
    # 对称带取 ASYM <= 阈值的比例边界而非固定绝对差带：y >= x 时 y <= x/(1-阈值)，
    # y < x 时 y >= (1-阈值)x，带内即 ASYM <= 0.30。
    line_x = np.linspace(0, axis_limit, 200)
    lower = ((1.0 - asym_threshold) / (1.0 + asym_threshold)) * line_x
    upper = ((1.0 + asym_threshold) / (1.0 - asym_threshold)) * line_x
    ax.fill_between(line_x, lower, upper, color="#DCE4EA", alpha=0.55, lw=0, zorder=1)
    ax.plot(line_x, lower, color=GRAY_L, lw=0.7, ls=(0, (1.5, 1.5)), zorder=2)
    ax.plot(line_x, upper, color=GRAY_L, lw=0.7, ls=(0, (1.5, 1.5)), zorder=2)
    ax.plot([0, axis_limit], [0, axis_limit], color=GRAY_D, lw=1.0, ls="--", zorder=3)

    # 类别 = (图例名, 颜色, 掩码)；空掩码直接 continue，既不画点也不进图例。
    categories = [
        ("TE(j→i)较大",  BLUE,   (asym > asym_threshold) & (d > 0)),
        ("TE(i→j)较大",  ORANGE, (asym > asym_threshold) & (d < 0)),
        ("近似对称（ASYM≤0.30）", GRAY_M, asym <= asym_threshold),
    ]
    sizes = 18.0 + 95.0 * avg / avg.max()
    legend_handles = []
    drawn = 0
    for label, color, mask in categories:
        if not mask.any():
            continue
        ax.scatter(xs[mask], ys[mask], s=sizes[mask], facecolor=color,
                   edgecolor="white", linewidth=0.6, alpha=0.95, zorder=5)
        drawn += int(mask.sum())
        legend_handles.append(
            Line2D([0], [0], marker="o", color="none", markerfacecolor=color,
                   markeredgecolor=color, markersize=5, label=label))
    if drawn != xs.size:
        raise ValueError(f"分类未覆盖全部节点对：绘制 {drawn} / 共 {xs.size}")
    # 图例按列优先填充（ncol=3）：与参考线交错后，上行是三类描述性读数区间、下行是两条参考线
    ref_handles = [
        Line2D([0], [0], color=GRAY_D, lw=1.0, ls="--", label="双向相等"),
        Line2D([0], [0], color=GRAY_L, lw=0.9, ls=(0, (1.5, 1.5)), label="ASYM = 0.30 边界"),
    ]
    interleaved = []
    for idx in range(max(len(legend_handles), len(ref_handles))):
        interleaved += legend_handles[idx:idx + 1] + ref_handles[idx:idx + 1]
    legend_handles = interleaved

    # ---- top 3 不对称对：主图带圈编号 + 边缘分布三角标记 ----
    # 2026-10-26：标注色由低饱和红 RED_S 改为深蓝灰 ACCENT——红色系在全篇
    # 结果图中只保留给"目标/参照线"语义（如图 5-7 的 90% 目标线），top-3
    # 编号是数据强调而非目标参照，统一收敛到蓝灰房屋色系。
    ACCENT = "#55606A"
    top3 = te["asymmetry"]["top_asymmetric_pairs"][:3]
    top3_xy, top3_names, top3_ring = [], [], []
    for p in top3:
        i, j = node_ids.index(p["node_i"]), node_ids.index(p["node_j"])
        if i > j:                      # 防御：坐标必须按 i<j 的 (x, y) 顺序取用
            i, j = j, i
        px, py = te_mat[i, j], te_mat[j, i]
        top3_xy.append((px, py))
        # 主导方向按读数判定（不用 top 列表里的方向字段，避免口径漂移）
        top3_names.append(f"{node_ids[i]} → {node_ids[j]}" if px > py
                          else f"{node_ids[j]} → {node_ids[i]}")
        # 描圈取该点自身面积 + 固定外扩量，保证圈始终落在散点之外
        top3_ring.append(sizes[pairs.index((node_ids[i], node_ids[j]))] + 55.0)
    # 编号标签用 offset points 定位：主图左上角区域本身空，向左下偏移会压到 y 刻度。
    # 三个偏移按当前 top 3 的相对位置选（①③相邻、②最靠上），换数据需重新目视核对。
    label_offsets = [(17, 15), (-24, 7), (20, -14)]
    for k, ((px, py), (dx, dy), ring) in enumerate(
            zip(top3_xy, label_offsets, top3_ring), start=1):
        ax.scatter([px], [py], s=ring, facecolor="none", edgecolor=ACCENT,
                   linewidth=1.1, zorder=6)
        ax.annotate(str(k), xy=(px, py), xytext=(dx, dy), textcoords="offset points",
                    fontsize=6.6, color=ACCENT, fontweight="bold", ha="center", va="center",
                    bbox=dict(boxstyle="circle,pad=0.22", facecolor="white",
                              edgecolor=ACCENT, linewidth=0.7),
                    arrowprops=dict(arrowstyle="-", color=ACCENT, lw=0.7,
                                    shrinkA=5, shrinkB=3), zorder=7)

    ax.set_xlim(0, axis_limit)
    ax.set_ylim(0, axis_limit)
    # 刻度步长 0.001 nats：纸面上标签间距约 0.58 in，足够容纳 6.4 pt 的"0.000"
    ticks = np.arange(0.0, axis_limit, 0.001)
    ax.set_xticks(ticks)
    ax.set_yticks(ticks)
    ax.set_xticklabels([f"{t:.3f}" for t in ticks], fontsize=6.4)
    ax.set_yticklabels([f"{t:.3f}" for t in ticks], fontsize=6.4)
    ax.set_xlabel("传递熵 TE(i → j)（nats）", fontsize=7.4, labelpad=2)
    ax.set_ylabel("传递熵 TE(j → i)（nats）", fontsize=7.4, labelpad=2)
    ax.spines[["top", "right"]].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRAY_D)
        ax.spines[side].set_linewidth(0.7)
    ax.tick_params(colors=GRAY_D, length=2.2, width=0.6, pad=1.5)

    # ========== 阶段 3：顶部边缘分布（主图横轴 TE(i→j) 的分布） ==========
    # 与主图同一组分箱边界，保证柱位与散点横坐标可直接对照
    bin_edges = np.linspace(0, axis_limit, 15)
    ax_top.hist(xs, bins=bin_edges, color=GRAY_M, alpha=0.75,
                edgecolor="white", linewidth=0.3)
    # 顶部留 12% 余量：最高柱不顶到轴上沿，下游的三角标记带也不贴着柱顶
    ax_top.set_ylim(0, float(np.histogram(xs, bins=bin_edges)[0].max()) * 1.12)
    ax_top.set_yticks([0, 10])
    # 说明文字放本轴右上角的空白区（该区间柱高仅 1~2 根），不额外占用图外空间
    ax_top.text(0.985, 0.92, "TE(i → j) 边缘分布", transform=ax_top.transAxes,
                ha="right", va="top", fontsize=6.3, color=GRAY_D)
    ax_top.set_ylabel("频数", fontsize=6.3, labelpad=2.5)
    ax_top.tick_params(axis="x", labelbottom=False, length=0)
    ax_top.tick_params(axis="y", labelsize=6.0, length=2.0, width=0.6, colors=GRAY_D)
    for side in ax_top.spines.values():
        side.set_visible(False)
    # 三角标记放在轴上方的独立带（clip_on=False），不压在柱体上
    for k, (px, _) in enumerate(top3_xy, start=1):
        xtrans = ax_top.get_xaxis_transform()
        ax_top.scatter([px], [1.06], transform=xtrans, marker="v", s=16,
                       color=ACCENT, zorder=5, clip_on=False)
        ax_top.text(px, 1.13, str(k), transform=xtrans, ha="center", va="bottom",
                    fontsize=6.0, color=ACCENT, fontweight="bold", clip_on=False)

    # ========== 阶段 4：右侧边缘分布（主图纵轴 TE(j→i) 的分布） ==========
    ax_right.hist(ys, bins=bin_edges, color=GRAY_M, alpha=0.75,
                  edgecolor="white", linewidth=0.3, orientation="horizontal")
    right_max_n = float(np.histogram(ys, bins=bin_edges)[0].max())
    # 左侧留出编号带：三角与数字都画在 0 计数线之外，不覆盖柱体
    ax_right.set_xlim(-right_max_n * 0.52, right_max_n * 1.10)
    ax_right.set_xticks([])
    for side in ax_right.spines.values():
        side.set_visible(False)
    ax_right.tick_params(axis="y", left=False, right=False, labelleft=False, labelright=False)
    # 轴名放本轴右侧（旋转 90°），与顶部"TE(i→j) 边缘分布"形成对称标注
    ax_right.text(1.13, 0.5, "TE(j → i) 边缘分布", transform=ax_right.transAxes,
                  ha="center", va="center", rotation=90, fontsize=6.3,
                  color=GRAY_D, clip_on=False)
    # 编号 1 与 3 的纵坐标仅差约 0.0002（不足一个字号），文字按最小间距错开后
    # 整体回移保持居中；深色三角仍钉在原始读数处，与主图散点严格对齐。
    # 最小间距取轴长的 4.2%（纸面约 0.16 in），大于 6 pt 字高即可避让。
    order = sorted(range(len(top3_xy)), key=lambda idx: top3_xy[idx][1])
    spread = [top3_xy[idx][1] for idx in order]
    min_gap = axis_limit * 0.042
    for r in range(1, len(spread)):
        spread[r] = max(spread[r], spread[r - 1] + min_gap)
    shift = (sum(spread) - sum(py for _, py in top3_xy)) / len(spread)
    text_y = [0.0] * len(top3_xy)
    for r, idx in enumerate(order):
        text_y[idx] = spread[r] - shift
    for k, ((_, py), ty) in enumerate(zip(top3_xy, text_y), start=1):
        ax_right.scatter([-right_max_n * 0.15], [py], marker="<", s=16,
                         color=ACCENT, clip_on=False, zorder=5)
        ax_right.text(-right_max_n * 0.32, ty, str(k), ha="center", va="center",
                      fontsize=6.0, color=ACCENT, fontweight="bold")

    # ========== 阶段 5：图例与图下注记 ==========
    # 图例放画布顶部（figure 坐标，避免 axes 坐标换算出画布外导致导出被撑高）
    fig.legend(handles=legend_handles, fontsize=6.2, frameon=False, ncol=3,
               loc="upper left", bbox_to_anchor=(ax_left, 0.996),
               bbox_transform=fig.transFigure, handletextpad=0.35,
               handlelength=1.6, columnspacing=0.9, labelspacing=0.35)

    n_both = int(both_sig.sum())
    fig.text(ax_left, 0.058,
             f"{xs.size} 个无向节点对（训练期）；{n_both} 对双向均达名义阈值，"
             f"{xs.size - n_both} 对仅单方向达阈值；点面积编码双向平均 TE",
             ha="left", va="center", fontsize=6.2, color=GRAY_D)
    circled = "①②③"
    fig.text(ax_left, 0.026,
             "编号为不对称度最高的三个节点对（主导方向）："
             + "　".join(f"{circled[k]} {name}" for k, name in enumerate(top3_names)),
             ha="left", va="center", fontsize=6.2, color=GRAY_D)

    final(fig, "fig5_3_asymmetry", (fig_w, fig_h))


# ========== fig5_4 覆盖率（v3：per-seed 散点 + horizon 面板） ==========
def fig5_7_coverage() -> None:
    c = json.load(open("outputs/analysis/conformal_prediction/conformal_summary.json"))
    seeds = c["per_seed"]
    groups = ["全局", "事件窗口", "稳定窗口"]
    key_map = {"全局": "overall", "事件窗口": "event_window",
               "稳定窗口": "stable_window"}

    # 两层证据结构（2026-10-26 重构，方案 7-甲）：A 口径对比（全局/稳定/事件
    # 窗口统一 0–100% 轴，oracle 红星并入事件窗口列），B 逐步长稳定性。
    # 旧版三面板三种视觉语言、A 行内并置 0–10% 与 80–92% 两个互不相干的
    # 尺度，"没差别"的口径占去 2/3 版面；统一坐标系后 1.9% 与 86.1% 的
    # 落差在同一根轴上直接可读。
    # 画布取论文显示尺寸（版心宽 14.66 cm = 5.77 in，图按 5.59 in 排版），
    # 此后 fontsize 参数即为纸面字号。
    fig = plt.figure(figsize=(5.59, 4.90), constrained_layout=False)
    gs = fig.add_gridspec(2, 1, height_ratios=[1.45, 1.0],
                          left=0.105, right=0.975, bottom=0.085, top=0.955,
                          hspace=0.30)

    def panel_tag(ax, tag: str) -> None:
        """只画面板字母；A/B 的含义由论文图注承载。

        原实现用 set_title 在每面板顶部写长描述句，属项目明令禁止的图内标题。
        """
        ax.text(0.015, 0.965, tag, transform=ax.transAxes, fontsize=12,
                fontweight="bold", color=GRAY_D, va="top", ha="left")

    # ---- A：三口径 × 两方法覆盖率（统一 0–100% 轴） ----
    target = 1.0 - float(c["alpha"])
    axA = fig.add_subplot(gs[0, 0])
    groups_A = ["全局", "稳定窗口", "事件窗口"]
    dx = 0.13  # 两方法在每口径内的水平错位
    jit = np.linspace(-0.035, 0.035, len(seeds))
    for xi, g in enumerate(groups_A):
        key = key_map[g]
        std_v = np.array([s["standard_conformal"][f"coverage_{key}"] for s in seeds])
        str_v = np.array([s["stratified_conformal"][f"coverage_{key}"] for s in seeds])
        axA.scatter(xi - dx + jit, std_v, s=22, facecolor="white",
                    edgecolor=GRAY_M, linewidth=0.7, alpha=0.85, zorder=3)
        axA.scatter(xi + dx + jit, str_v, s=22, facecolor=BLUE,
                    edgecolor=BLUE, linewidth=0.5, alpha=0.7, zorder=3)
        s_mean, s_sd = float(std_v.mean()), float(std_v.std(ddof=1))
        v_mean, v_sd = float(str_v.mean()), float(str_v.std(ddof=1))
        axA.errorbar(xi - dx, s_mean, yerr=s_sd, fmt="o", ms=7.5, color=GRAY_D,
                     markerfacecolor="white", markeredgecolor=GRAY_D,
                     capsize=3.0, lw=1.1, zorder=4)
        axA.errorbar(xi + dx, v_mean, yerr=v_sd, fmt="o", ms=7.5, color=BLUE,
                     markerfacecolor=BLUE, markeredgecolor=GRAY_D,
                     capsize=3.0, lw=1.1, zorder=4)
        axA.text(xi - dx, s_mean + s_sd + 0.025, f"{s_mean:.1%}", ha="center",
                 va="bottom", fontsize=7.6, color=GRAY_D)
        axA.text(xi + dx, v_mean + v_sd + 0.025, f"{v_mean:.1%}", ha="center",
                 va="bottom", fontsize=7.6, color=BLUE)
    # oracle：事后诊断参照（不可部署），只有事件窗口口径，画在该列右侧
    oracle_event = float(np.mean([
        s["stratified_oracle_upper"]["coverage_event_window"] for s in seeds]))
    ox = len(groups_A) - 1 + 2 * dx + 0.16
    axA.plot(ox, oracle_event, marker="*", ms=13, color=RED_S,
             markeredgecolor="white", markeredgewidth=0.6, zorder=4)
    axA.text(ox, oracle_event - 0.05, f"oracle\n{oracle_event:.1%}", ha="center",
             va="top", fontsize=7.4, color=RED_S, linespacing=1.25)
    axA.axhline(target, color=RED_S, lw=1.1, ls="--", zorder=1)
    axA.text(len(groups_A) - 1 + 0.52, target + 0.012, "90% 目标",
             fontsize=7.4, color=RED_S, ha="right", va="bottom")
    axA.set_xticks(range(len(groups_A)))
    axA.set_xticklabels(groups_A, fontsize=8.8)
    axA.set_ylabel("覆盖率（α = 0.1；3 种子）", fontsize=8.8)
    axA.set_ylim(0, 1.0)
    axA.set_yticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])
    axA.set_yticklabels(["0%", "20%", "40%", "60%", "80%", "100%"], fontsize=7.8)
    axA.set_xlim(-0.45, len(groups_A) - 1 + 0.55)
    _clean_ax(axA)
    axA.legend(handles=[Line2D([0], [0], marker="o", color="none",
                               markerfacecolor="white", markeredgecolor=GRAY_D,
                               markersize=6, label="标准共形"),
                        Line2D([0], [0], marker="o", color="none",
                               markerfacecolor=BLUE, markeredgecolor=GRAY_D,
                               markersize=6, label="规则路由分层"),
                        Line2D([0], [0], marker="*", color="none",
                               markerfacecolor=RED_S, markeredgecolor="white",
                               markersize=9, label="oracle（事后诊断，不可部署）")],
               fontsize=7.4, frameon=False, loc="lower left",
               handlelength=1.6, handletextpad=0.4, labelspacing=0.45)
    panel_tag(axA, "A")

    # ---- B：逐步长覆盖率及三种子 min–max 范围 ----
    axC = fig.add_subplot(gs[1, 0])
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
               framealpha=0.88, loc="lower left", ncol=2,
               handlelength=1.8, columnspacing=0.8)
    panel_tag(axC, "B")

    final(fig, "fig5_7_coverage", (5.59, 4.90))


if __name__ == "__main__":
    print("=== 批次 6：图5-3 方向不对称性 + 图5-7 共形覆盖率 ===")
    fig5_3_asymmetry()
    fig5_7_coverage()      # 原漏调用，导致该图只能手工生成后改名
    print("批次 6 完成")
