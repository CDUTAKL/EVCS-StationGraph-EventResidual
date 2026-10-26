"""第 3 章实验章新增 5 图：图 3-4、3-8、3-9、3-10、3-11。

- 图 3-4 逐预测步长 MAE：6 模型 × h1-h4 线图（三种子均值 ± SD 阴影）。
- 图 3-8 分层窗口 MAE：6 模型 × 全局/事件/稳定/非零负荷（log 轴点图）。
- 图 3-9 逐节点 MAE：10 节点 × 6 模型热力图（节点按训练期累计负荷排序）。
- 图 3-10 机制消融：基线（AdaptiveGraph）+ SG-EXP-006 四个消融变体全局 MAE。
- 图 3-11 事件窗口预测时序：测试集代表性事件窗口的真值 vs 预测曲线。

数据：SG-EXP-002/003（night_run/20260730-171821）、004/009/010
（outputs/experiments）的 seed-*/metrics.json 与 predictions.csv.gz。
输出：同名 SVG + 1200 DPI PNG。
"""

from __future__ import annotations

import glob
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
except ImportError:  # 无 skill 环境回退
    from _skill_compat import export_figure, setup_style  # noqa: E402

FIG_DIR = Path("outputs/figures")
FIG_DIR.mkdir(parents=True, exist_ok=True)
setup_style(journal="general", lang="zh")

sys.path.insert(0, "src")
from evcs_station_graph.data import load_tensor_bundle  # noqa: E402

BUNDLE = load_tensor_bundle("data/processed/SG-DATA-005-primary-tensor.npz")

BLUE = "#2C5F8A"
ORANGE = "#D08A3C"
GRAY_D = "#404040"
GRAY_M = "#808080"
GRAY_L = "#C8C8C8"
GRAY_XL = "#E6E9EC"
RED = "#B05A4A"
PURPLE = "#7A6FA0"  # AGCRN 线色（与 MLP 红区分）
GREEN = "#597A62"

SEEDS = ("2024", "2025", "2026")
# 6 个对比模型：实验 ID → 展示名 → 颜色（AGCRN 2026-08-04 核验入图）
MODELS = [
    ("SG-EXP-002", "TCN", GRAY_M),
    ("SG-EXP-003", "StaticGraph", ORANGE),
    ("SG-EXP-004", "AdaptiveGraph", BLUE),
    ("SG-EXP-009", "MLP", RED),
    ("SG-EXP-010", "GWN", GREEN),
    ("SG-EXP-008", "AGCRN", PURPLE),
]
# 窗口 scope → 展示名（与 metrics.json scopes 键一致）
SCOPES = [("global", "全局"), ("event_window", "事件窗口"),
          ("stable_window", "稳定窗口"), ("nonzero_load", "非零负荷")]


# 实验 → metrics.json 权威来源（审查 H2：SG-EXP-004 在 night_run 与 experiments
# 各有一个 run（MAE 差 ~1%），必须钉死与图 3-1 主对比一致的正式流水线 night_run；
# 009/010 仅 experiments 目录存在）
METRICS_SOURCES = {
    "SG-EXP-002": "outputs/night_run/20260730-171821/SG-EXP-002/*/seed-*/metrics.json",
    "SG-EXP-003": "outputs/night_run/20260730-171821/SG-EXP-003/*/seed-*/metrics.json",
    "SG-EXP-004": "outputs/night_run/20260730-171821/SG-EXP-004/*/seed-*/metrics.json",
    "SG-EXP-008": "outputs/experiments/SG-EXP-008/*/seed-*/metrics.json",
    "SG-EXP-009": "outputs/experiments/SG-EXP-009/*/seed-*/metrics.json",
    "SG-EXP-010": "outputs/experiments/SG-EXP-010/*/seed-*/metrics.json",
}


def _metrics_paths(exp_id: str) -> list:
    """返回该实验三种子的 metrics.json 路径（来源目录由 METRICS_SOURCES 钉死）。"""
    pattern = METRICS_SOURCES[exp_id]
    hits = sorted(glob.glob(pattern))
    if len(hits) != 3:
        raise FileNotFoundError(
            f"{exp_id} 三种子 metrics.json 不齐（{pattern} → {len(hits)} 个）")
    return hits


def _load_model_metrics(exp_id: str) -> dict:
    """按 seed 加载实验分层指标：{seed: {"by_horizon": {...}, "scopes": {...}, "by_node": {...}}}。"""
    out = {}
    for path in _metrics_paths(exp_id):
        seed = next((s for s in SEEDS if path.endswith(f"{s}/metrics.json")), None)
        if seed is None:
            continue
        d = json.load(open(path))
        # 契约断言（batch10 式）：分层键必须齐全，缺失即显式失败而非 NaN 静默吞
        missing = [k for k, _cn in SCOPES if k not in d]
        if missing:
            raise KeyError(f"{exp_id} {seed} metrics.json 缺 scope: {missing}")
        if set(d["by_node"].keys()) != set(BUNDLE.node_ids):
            raise KeyError(f"{exp_id} {seed} by_node 节点集不一致")
        if len(d["by_horizon"]) != 4:
            raise KeyError(f"{exp_id} {seed} by_horizon 步长数 != 4")
        out[seed] = {
            "by_horizon": {int(k): v["mae"] for k, v in d["by_horizon"].items()},
            "scopes": {k: d[k]["mae"] for k, _cn in SCOPES},
            "by_node": {k: v["mae"] for k, v in d["by_node"].items()},
        }
    return out


def _final(fig, name: str, size: tuple) -> None:
    """导出 SVG + 1200 DPI PNG。"""
    export_figure(fig, basename=str(FIG_DIR / name), formats=["svg", "png"],
                  dpi=1200, size_inches=size, grayscale_preview=False)
    # Matplotlib 把多行 path 数据写成带行尾空格的行；清理后 SVG 才能通过
    # 仓库的空白检查（git diff --check）。
    svg_path = FIG_DIR / f"{name}.svg"
    svg_path.write_text(
        "\n".join(line.rstrip() for line in svg_path.read_text(encoding="utf-8").splitlines()) + "\n",
        encoding="utf-8",
    )
    print(f"  ✅ {name}")


def _clean(ax, grid_axis="y") -> None:
    """去除上/右边框，网格线保持浅色。"""
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color(GRAY_D)
    ax.tick_params(labelsize=8, colors=GRAY_D)
    if grid_axis:
        ax.grid(axis=grid_axis, color=GRAY_L, lw=0.55, alpha=0.72, zorder=0)


def redraw_fig3_4() -> None:
    """图 3-4：逐预测步长 MAE（h1→h4，6 模型三种子均值 ± SD）。"""
    fig, ax = plt.subplots(figsize=(8.4, 4.65))
    fig.subplots_adjust(left=0.11, right=0.98, bottom=0.18, top=0.79)
    hs = np.arange(1, 5)
    markers = {"TCN": "o", "StaticGraph": "s", "AdaptiveGraph": "D",
               "MLP": "^", "GWN": "P", "AGCRN": "X"}
    for exp_id, label, color in MODELS:
        data = _load_model_metrics(exp_id)
        mat = np.asarray([[data[s]["by_horizon"][h] for h in hs] for s in SEEDS])
        mean, sd = mat.mean(axis=0), mat.std(axis=0, ddof=1)
        ax.plot(hs, mean, marker=markers[label], ms=6.0, lw=1.7, color=color,
                label=label, zorder=4)
        ax.fill_between(hs, mean - sd, mean + sd, color=color,
                        alpha=0.11, lw=0, zorder=2)
    ax.set_xlabel("预测步长 h（15 min）", fontsize=8.8)
    ax.set_ylabel("MAE（kWh/15 min）", fontsize=8.8)
    ax.set_xticks(hs)
    ax.set_xticklabels([f"h={h}" for h in hs], fontsize=8.2)
    ax.legend(fontsize=7.5, frameon=False, ncol=6, loc="upper center",
              bbox_to_anchor=(0.50, 1.18), columnspacing=1.0, handletextpad=0.35)
    _clean(ax)
    fig.text(0.50, 0.92, "点为三种子均值；浅色带为跨种子标准差",
             ha="center", va="center", fontsize=7.0, color=GRAY_M)
    _final(fig, "fig3_12_mae_by_horizon", (8.4, 4.65))
    return None


def redraw_fig3_8() -> None:
    """图 3-8：分层窗口 MAE 对比（log 轴分组柱，事件窗口量级远大于稳定窗口）。

    配色克制化：全部去掉 hatch 纹理，改用「主色 + 灰阶 + 低饱和色」的层次
    区分 6 个模型——主模型 StaticGraph（MRG-GCN）用 BLUE 突出，其余按
    灰阶（深→浅）与两个低饱和色（GWN 绿、AGCRN 紫）区分，与本项目
    fig3_9 / fig4_4 / fig5_2 的素雅风格一致。
    数值标注：4 窗口 × 6 模型共 24 根柱、柱宽仅约 13 pt，逐柱标注必然
    与相邻柱或误差棒重叠，故只标注主模型（论文主张所系）在 4 个窗口的
    MAE，白字竖排直接写入蓝色柱体内部；其余模型的分层数值由正文表 3-2
    承载。
    """
    # 画布取论文显示尺寸（版心宽 14.66 cm = 5.77 in，图按 5.59 in 排版），
    # fontsize 参数即为纸面字号；按大画布绘制再等比缩小会把 8pt 压到 3.9pt。
    fig, ax = plt.subplots(figsize=(5.59, 3.15))
    x = np.arange(len(SCOPES))
    width = 0.15
    # 本图专属配色映射（不改 MODELS 常量，以免影响共用它的 fig3_10/fig3_13）。
    # 与图 3-9 同一「灰阶承载基线、蓝色只给本文模型」的方案：
    # 主模型 StaticGraph 深蓝；本文变体 AdaptiveGraph 浅蓝（同 fig3_9 的
    # “本文变体”色）；四个基线为蓝灰阶（浅→深：TCN/MLP 为无图基线，
    # GWN/AGCRN 为图模型基线），相邻柱靠明度阶差 + 白边区分。
    palette = {
        "SG-EXP-003": BLUE,        # 主模型 StaticGraph（MRG-GCN）
        "SG-EXP-004": "#8EABC0",   # AdaptiveGraph（本文变体，浅蓝）
        "SG-EXP-002": "#AEB6BC",   # TCN（无图基线，浅蓝灰）
        "SG-EXP-009": "#8C979E",   # MLP（无图基线，中浅蓝灰）
        "SG-EXP-010": "#6E7A81",   # GWN（图模型基线，中深蓝灰）
        "SG-EXP-008": "#55606A",   # AGCRN（图模型基线，深蓝灰）
    }
    main_exp = "SG-EXP-003"
    main_idx = next(i for i, (e, _l, _c) in enumerate(MODELS) if e == main_exp)
    # 三种子均值 / 样本标准差矩阵，形状 [模型数, 窗口数]
    means = np.zeros((len(MODELS), len(SCOPES)))
    sds = np.zeros((len(MODELS), len(SCOPES)))
    for mi, (exp_id, label, _color) in enumerate(MODELS):
        data = _load_model_metrics(exp_id)
        for si, (scope_key, _cn) in enumerate(SCOPES):
            vals = np.asarray([data[s]["scopes"][scope_key] for s in SEEDS],
                              dtype=float)
            means[mi, si] = vals.mean()
            sds[mi, si] = vals.std(ddof=1)
        ax.bar(x + (mi - 2) * width, means[mi], width=width,
               color=palette[exp_id], edgecolor="white", lw=0.45,
               yerr=sds[mi], capsize=2.0,
               # 误差棒线宽/颜色须用 elinewidth / ecolor（lw 只作用于数据折线，
               # 对 bar 的误差棒无效，会退回 1.5 pt 默认值显得笨重）。
               error_kw=dict(elinewidth=0.7, capthick=0.7, ecolor=GRAY_D),
               label=label, zorder=3)
    ax.set_yscale("log")
    # Keep only major log labels; unlabeled minor ticks avoid tiny, noisy text
    # when the figure is reduced to the thesis text width.
    ax.yaxis.set_minor_formatter(NullFormatter())

    # 主模型数值标注：白字竖排写在主模型（蓝色）柱体内部，自柱顶向下排布。
    # 旧版把标注抬到全组最高柱之上再用细引导线连回主模型柱顶，悬空的蓝字
    # 与引导线视觉上像“游离元素”；柱内竖排标注不占用组间空隙，也不会与
    # 相邻柱的误差棒相交（事件窗口组各柱高度接近时尤为重要）。
    for gi in range(len(SCOPES)):
        xc = x[gi] + (main_idx - 2) * width
        ax.text(xc, means[main_idx, gi] * 0.90, f"{means[main_idx, gi]:.4f}",
                ha="center", va="top", rotation=90, fontsize=6.4,
                color="white", zorder=6)

    ax.set_xticks(x)
    ax.set_xticklabels([cn for _k, cn in SCOPES], fontsize=8.6)
    ax.set_ylabel("MAE（kWh/15 min，对数轴）", fontsize=8.8)
    # 无柱上标注后顶端只需为最高柱的误差棒留少量余量。
    ax.set_ylim(0.004, float((means + sds).max()) * 1.18)
    # 图例单行横排 6 项，从左到右与每组柱序（TCN→…→AGCRN）完全一致，
    # 位于数据区上方、不遮挡任何柱或标注。
    ax.legend(fontsize=7.2, frameon=False, ncol=6, loc="upper center",
              bbox_to_anchor=(0.50, 1.14), columnspacing=0.85,
              handlelength=1.9, handletextpad=0.35)
    _clean(ax)
    fig.subplots_adjust(left=0.135, right=0.99, bottom=0.175, top=0.775)
    _final(fig, "fig3_14_mae_by_window", (5.59, 3.15))
    return None


def redraw_fig3_9() -> None:
    """图 3-9：逐节点 MAE 热力图（10 节点 × 6 模型）。

    节点顺序由同一主张量测试期起点的累计代理负荷确定，并显式写入图注，
    避免手工顺序与热力图色块/正文节点表不一致。

    画布按论文显示尺寸（5.59 in 版心宽）绘制：figsize 直接取该尺寸后 fontsize
    参数即为纸面字号。旧版按 8.0×3.4 in 绘制、排版时整体压缩 ×0.69，7.2 pt
    落到约 5.0 pt（纸面约 1.8 mm）不可读。配色（Blues + 深格白字/浅格黑字）
    与模型清单沿用旧版，MODELS 常量由 fig3_10/fig3_12 共用，本函数不得改动。
    """
    test_origins = np.asarray(BUNDLE.split_origins["test"], dtype=int)
    order = np.argsort(-BUNDLE.targets[test_origins].sum(axis=0))
    node_order = [str(BUNDLE.node_ids[i]) for i in order]
    mat = np.zeros((len(MODELS), len(node_order)))
    for mi, (exp_id, _label, _color) in enumerate(MODELS):
        data = _load_model_metrics(exp_id)
        for ni, node in enumerate(node_order):
            vals = [data[s]["by_node"].get(node, float("nan")) for s in SEEDS]
            mat[mi, ni] = np.nanmean(vals)

    # ========== 画布与版面：直接取论文显示尺寸 ==========
    # 版心宽 14.66 cm = 5.77 in，图按 5.59 in 宽排版；figsize 直接取该量级后，
    # 下文的 fontsize 参数即为纸面真实字号。旧版按 8.0×3.4 in 绘制再被排版压缩
    # ×0.69，7.2 pt 落到约 5.0 pt（纸面约 1.8 mm），不可读。
    fig_w, fig_h = 5.49, 3.60
    # 手工 add_axes（不用 subplots + fig.colorbar 的分数布局）：y 轴模型名
    # （最长 "AdaptiveGraph" ≈ 0.79 in）与右侧色标 + 竖排单位标签（≈ 0.59 in）
    # 都长在 axes 之外，必须显式预留宽度，才能让墨迹恰好铺满 5.49 in 画布；
    # 交给 tight bbox 自动包含溢出部分会把成品顶出 5.59 in 版心。
    ax_left, ax_bottom = 0.81, 0.40
    ax_w, ax_h = 4.01, 3.16
    fig = plt.figure(figsize=(fig_w, fig_h))
    ax = fig.add_axes([ax_left / fig_w, ax_bottom / fig_h,
                       ax_w / fig_w, ax_h / fig_h])
    cax = fig.add_axes([4.88 / fig_w, ax_bottom / fig_h, 0.132 / fig_w, ax_h / fig_h])

    # ========== 热力图本体（配色与旧版一致：Blues 色阶 + 格内三位小数） ==========
    im = ax.imshow(mat, cmap="Blues", aspect="auto",
                   vmin=mat.min(), vmax=mat.max())
    ax.set_xticks(range(len(node_order)))
    # 节点标签 45° 斜排，字号已按纸面取值，不再依赖排版缩放
    ax.set_xticklabels(node_order, fontsize=7.8, rotation=45, ha="right")
    ax.set_yticks(range(len(MODELS)))
    ax.set_yticklabels([lbl for _e, lbl, _c in MODELS], fontsize=8.0)
    for mi in range(mat.shape[0]):
        for ni in range(mat.shape[1]):
            # 格内数值 8.0 pt：10 列共用 4.01 in → 每列 0.401 in；实测五字符
            # "0.026" 在 8 pt 下宽 0.284 in，左右各余 0.058 in，相邻数值间
            # 留白 ≈ 8.4 pt，60 个数值互不挤压（1200 DPI 位图逐格量测复核）
            ax.text(ni, mi, f"{mat[mi, ni]:.3f}", ha="center", va="center",
                    fontsize=8.0,
                    color="white" if mat[mi, ni] > mat.min() + .58 * (mat.max()-mat.min()) else GRAY_D)
    cbar = fig.colorbar(im, cax=cax)
    cbar.set_label("MAE（kWh/15 min，三种子均值）", fontsize=7.6)
    cbar.ax.tick_params(labelsize=7.2)
    ax.tick_params(length=0)
    _final(fig, "fig3_15_mae_by_node", (fig_w, fig_h))
    return None


def redraw_fig3_10() -> None:
    """图 3-10：机制消融（SG-EXP-006）——基线 vs 四个变体的全局 MAE。

    基线 = SG-EXP-005（event_residual 正式三种子，night_run 流水线产物）；
    注意 no_event_gate 变体的语义（mechanism.py）：gate 关闭后残差修正路径
    **无条件作用于所有样本**（非"无修正"）——其大幅恶化证明门控的选择性
    激活是必要的，而非事件修正本身带来的收益。

    配色编码"相对基线的退化程度"（本图专属，写在函数内以免影响共用 MODELS
    常量的 fig3_10/fig3_12/fig3_13）：完整模型是全文主张所系 → 全图唯一主色
    BLUE；仅保留单类关系的两变体相对基线只差 +2.5%/+2.3%（小于三种子标准差
    量级），语义是"与基线持平" → 浅蓝灰 #AEB6BC 后退；无图与门控关闭分别恶化
    +113.0%、+90.5%，语义是"致命消融" → 深蓝灰 #55606A 压重（与图 3-12 的
    蓝灰阶一致，避免近黑与浅灰的明暗跨度过大）。
    三级在灰度打印下的亮度序为 深蓝灰(约95) < 主色档 < 浅蓝灰(约182)，
    仍单调可区分。
    """
    # 退化程度三级色（语义见 docstring；不使用其它章节的橙/绿/红点缀色）
    C_BASE, C_MILD, C_SEVERE = BLUE, "#AEB6BC", "#55606A"
    # 柱序按退化程度排列（基线 → 持平变体 → 致命消融）：旧版把两根深蓝灰
    # 高柱插在第 2、5 位，颜色与柱高都呈交错跳变；重排后柱高单调分组、
    # 颜色成块，退化叙事从左到右一目了然。
    variants = [
        ("baseline", "完整模型\n（基线）", C_BASE),
        ("SG-EXP-006-ablation-static_graph_only", "仅固定图", C_MILD),
        ("SG-EXP-006-ablation-adaptive_graph_only", "仅自适应图", C_MILD),
        ("SG-EXP-006-ablation-no_graph", "无图\n（TCN 结构）", C_SEVERE),
        ("SG-EXP-006-ablation-no_event_gate", "门控关闭\n（全样本修正）", C_SEVERE),
    ]
    # 画布直接取论文显示尺寸（版心宽 14.66 cm = 5.59 in），fontsize 参数即为
    # 纸面字号；按大画布绘制再等比缩小会把 8 pt 压到不足 5 pt。
    fig, ax = plt.subplots(figsize=(5.59, 3.15))
    x = np.arange(len(variants))
    means, sds = [], []
    for xi, (key, label, color) in enumerate(variants):
        if key == "baseline":
            paths = sorted(glob.glob(
                "outputs/night_run/20260730-171821/SG-EXP-005/*/seed-*/metrics.json"))
        else:
            paths = sorted(glob.glob(
                f"outputs/night_run/20260730-171821/SG-EXP-006/*/children/{key}/*/seed-*/metrics.json"))
        if len(paths) != 3:
            raise FileNotFoundError(f"{key} 三种子 metrics.json 不齐（{len(paths)} 个）")
        vals = [json.load(open(p))["global"]["mae"] for p in paths]
        mean, sd = float(np.mean(vals)), float(np.std(vals, ddof=1))
        means.append(mean)
        sds.append(sd)
        # 误差棒颜色统一用深灰：浅灰柱若误差棒跟随柱色会淡到看不见
        ax.bar(xi, mean, width=0.55, color=color, edgecolor="white", lw=0.8,
               yerr=sd, capsize=2.6,
               error_kw=dict(elinewidth=0.8, capthick=0.8, ecolor=GRAY_D),
               zorder=3)
    # 柱顶标注：数值 + 相对基线退化率。0 起点坐标轴会把 +2% 与 +113% 压成
    # 相近的柱高，百分比是唯一能读出"哪些消融致命"的文字通道（与正文
    # +113.0% / +90.5% / +2.5% / +2.3% 同口径，均以基线三种子均值为分母）。
    base = means[0]
    for xi, (mean, sd) in enumerate(zip(means, sds)):
        txt = f"{mean:.4f}" if xi == 0 else f"{mean:.4f}  (+{100 * (mean - base) / base:.1f}%)"
        ax.text(xi, mean + sd + 0.0011, txt, ha="center", va="bottom",
                fontsize=6.8, color=GRAY_D)
    # ylim 数据定界（审查 C1：固定 0.017 会剪断 no_graph≈0.030 的柱子）；
    # 1.22 倍留白容纳误差棒之上的两段标注文字。
    ymax = max(m + s for m, s in zip(means, sds)) * 1.22
    # 基线参考虚线：锚定"未消融"位置，持平变体与致命消融的高差直接可读
    ax.axhline(base, color=GRAY_M, lw=0.8, ls=":", zorder=2)
    ax.set_xticks(x)
    # 标签分两行书写，避免 15° 斜排（斜排在小版心下既占高又难读）；
    # 字号交由 _clean() 统一设为 8 pt（须在 _clean 之后不再覆盖）
    ax.set_xticklabels([lbl for _k, lbl, _c in variants])
    ax.set_ylabel("全局 MAE（kWh/15 min）", fontsize=8.8)
    ax.set_ylim(0, ymax)
    _clean(ax)
    _final(fig, "fig3_16_mechanism_ablation", (5.59, 3.15))
    return None


def redraw_fig3_11() -> None:
    """图 3-11：测试集代表性事件窗口的真值 vs 预测时序（seed-2024）。"""
    df = pd.read_csv(
        "outputs/experiments/SG-EXP-004/20260731-102456/seed-2024/predictions.csv.gz")
    ev = df[(df["split"] == "test") & df["rule_trigger"]].copy()
    # 每 origin 有 4 个 horizon，rule_trigger 按 [O,N] 广播；先用触发段选择代表窗口，
    # 再回到完整 h=1 测试序列绘图，避免把不连续事件窗口直接连成一条假曲线。
    uniq = ev.drop_duplicates(["node_id", "origin_index"])[["node_id", "origin_index"]]
    # 选 rule_trigger 样本最密集的节点
    best_node = uniq["node_id"].value_counts().index[0]
    event_origins = np.sort(uniq.loc[uniq["node_id"] == best_node, "origin_index"].unique())
    # 选择连续触发段最长的一段，选择规则可复核且不依赖手工挑点。
    starts = np.r_[0, np.where(np.diff(event_origins) > 1)[0] + 1]
    ends = np.r_[np.where(np.diff(event_origins) > 1)[0], len(event_origins) - 1]
    best_seg = int(np.argmax(ends - starts + 1))
    event_start = int(event_origins[starts[best_seg]])
    event_end = int(event_origins[ends[best_seg]])
    # 取触发段前后各 5 步上下文（15 min/步），避开相邻事件段，
    # 并保留所有 h=1 测试点以展示真实的连续时间走势。
    context = 5
    sub = df[(df["split"] == "test") & (df["node_id"] == best_node)
             & (df["horizon"] == 1)].sort_values("origin_index")
    sub = sub[(sub["origin_index"] >= event_start - context)
              & (sub["origin_index"] <= event_end + context)].copy()
    if sub.empty:
        raise RuntimeError("图 3-11 代表事件窗口为空")

    # x 使用相对事件位置而非巨大的 target_index，避免横轴稀疏且留白过多。
    rel = sub["origin_index"].to_numpy() - event_start
    truth_pts = np.maximum(sub["y_true"].to_numpy(dtype=float), 0.0)
    pred_pts = sub["y_pred"].to_numpy(dtype=float)
    trigger = sub["rule_trigger"].to_numpy(dtype=bool)
    trigger_idx = np.flatnonzero(trigger)
    if len(trigger_idx) == 0:
        raise RuntimeError("图 3-11 代表窗口未找到规则触发点")

    # 显式预留顶部图例带，避免图例进入数据区遮挡峰值曲线。
    fig = plt.figure(figsize=(8.4, 3.9), constrained_layout=False)
    ax = fig.add_axes([0.115, 0.17, 0.86, 0.68])
    # 仅对真实规则触发段加浅橙底纹；底纹是窗口标识，不是误差或置信区间。
    ax.axvspan(-0.5, event_end - event_start + 0.5,
               color=ORANGE, alpha=0.12, zorder=0, label="规则触发段")
    ax.fill_between(rel, np.minimum(truth_pts, pred_pts),
                    np.maximum(truth_pts, pred_pts),
                    color=GRAY_XL, lw=0, zorder=1, label="绝对误差带")
    ax.plot(rel, truth_pts, color=GRAY_D, lw=1.7, marker="o", ms=3.2,
            label="真实负荷", zorder=3)
    ax.plot(rel, pred_pts, color=BLUE, lw=1.35, ls="--", marker="o", ms=3.0,
            label="预测（h=1）", zorder=4)
    # 用边界线强化触发段的左右边界，不在数据点旁添加小字。
    ax.axvline(-0.5, color=ORANGE, lw=0.8, alpha=0.65, zorder=2)
    ax.axvline(event_end - event_start + 0.5, color=ORANGE, lw=0.8,
               alpha=0.65, zorder=2)
    ticks = [-context, 0, event_end - event_start,
             event_end - event_start + context]
    labels = ["事件前", "触发开始", "触发结束", "事件后"]
    ax.set_xticks(ticks)
    ax.set_xticklabels(labels, fontsize=8.0)
    ax.set_xlabel("相对事件窗口位置（每步 15 min）", fontsize=8.8)
    ax.set_ylabel(f"{best_node} 负荷（kWh/15 min）", fontsize=8.8)
    handles, legend_labels = ax.get_legend_handles_labels()
    fig.legend(handles, legend_labels, fontsize=7.5, frameon=False,
               loc="upper left", bbox_to_anchor=(0.115, 0.985), ncol=4,
               handlelength=2.0, columnspacing=0.9, borderaxespad=0.0)
    ax.set_xlim(-context - 0.5, event_end - event_start + context + 0.5)
    ax.set_ylim(bottom=min(-0.02, float(pred_pts.min()) - 0.02))
    _clean(ax)
    _final(fig, "fig3_16_event_window_forecast", (8.4, 3.9))
    return None


if __name__ == "__main__":
    print("=== 批次 12：第 3 章主文 4 图 ===")
    redraw_fig3_4()
    redraw_fig3_8()
    redraw_fig3_9()
    redraw_fig3_10()
    print("批次 12 完成")
