"""论文图批次 14：PCMCI+ 因果验证网络图（图 5-2b，SG-EXP-017）。

三面板设计（2026-08-03 用户要求"无比精致复杂"）：
- 左：验证网络图——圆环布局，节点大小编码累计负荷（冗余编码），
  三类边：TE 候选→PCMCI+ 确认（蓝色实线，线宽 ∝ |条件依赖系数|）、
  TE 候选→未确认（灰色虚线）、PCMCI+ 独有（橙色实线）；
  双向对用弧线正负曲率区分方向；自环（自回归滞后边）不绘制并在
  图注说明（10 条）。
- 中：验证漏斗——76 条 TE 候选 → 44 条确认（57.9%）→ 32 条未确认；
  PCMCI+ 独有 16 条拆为节点间 6 条 + 自回归 10 条。
- 右：节点级验证——10 节点确认/未确认边数堆叠条 + PCMCI+ 独有出边，
  按确认数降序，冗余标注节点编号。

统一规范：无标题、无文件代号、SVG+PNG 1200DPI、色盲安全 + 冗余编码。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

sys.path.insert(0, str(Path.home() / ".claude/skills/scipilot-figure-skill/scripts"))
try:
    from export_figure import export_figure  # noqa: E402
    from setup_style import setup_style  # noqa: E402
except ImportError:  # 无 skill 环境回退
    from _skill_compat import export_figure, setup_style  # noqa: E402

sys.path.insert(0, "src")
from evcs_station_graph.data import load_tensor_bundle  # noqa: E402

FIG_DIR = Path("outputs/figures")
FIG_DIR.mkdir(parents=True, exist_ok=True)
setup_style(journal="general", lang="zh")

BLUE = "#2C5F8A"      # 深蓝（主色：确认边）
ORANGE = "#D08A3C"    # 低饱和橙（PCMCI+ 独有）
RED_S = "#B05A4A"     # 低饱和红（未确认）
GRAY_D = "#404040"
GRAY_M = "#808080"
GRAY_L = "#C8C8C8"

BUNDLE = load_tensor_bundle("data/processed/SG-DATA-005-primary-tensor.npz")
NODE_ORDER = ["CA-303", "CA-304", "CA-305", "CA-307", "CA-311",
              "CA-315", "CA-317", "CA-321", "CA-327", "CA-489"]
NODE_IDS = list(BUNDLE.node_ids)
# 累计负荷（全时间窗），用于节点大小冗余编码
LOAD = np.array([BUNDLE.targets[:, NODE_IDS.index(n)].sum() for n in NODE_ORDER])
LOAD_N = (LOAD - LOAD.min()) / max(LOAD.max() - LOAD.min(), 1e-9)


def final(fig, name: str, size: tuple[float, float]) -> None:
    """统一导出：SVG 矢量 + PNG 1200 DPI（论文硬性约束）。"""
    export_figure(
        fig, basename=str(FIG_DIR / name),
        formats=["svg", "png"], dpi=1200, size_inches=size,
        grayscale_preview=False,
    )
    print("  ✅ {}".format(name))


def _network_panel(ax, data: dict) -> None:
    """左面板：验证网络图（圆环布局 + 三色边 + 节点大小编码负荷）。"""
    conf = [tuple(e) for e in data["confirmed_edges"] if e[0] != e[1]]
    te_only = [tuple(e) for e in data["te_only_edges"]]
    pcmci_only = [tuple(e) for e in data["pcmci_only_edges"] if e[0] != e[1]]
    coef_map = {
        (e["source"], e["target"]): e["coef"]
        for e in data["edges"] if e["source"] != e["target"]
    }
    n = len(NODE_ORDER)
    pos = {nd: (np.cos(2 * np.pi * i / n), np.sin(2 * np.pi * i / n))
           for i, nd in enumerate(NODE_ORDER)}

    def _arc(s, t, rad):
        ax.annotate("", xy=pos[t], xytext=pos[s],
                    arrowprops=dict(arrowstyle="->", color=BLUE, lw=w,
                                    alpha=alpha, shrinkA=16, shrinkB=16,
                                    connectionstyle="arc3,rad={}".format(rad)))

    # 未确认边最底层（灰虚线，细且淡——大量存在，压低视觉权重避免毛线团）
    for s, t in te_only:
        ax.annotate("", xy=pos[t], xytext=pos[s],
                    arrowprops=dict(arrowstyle="->", color=GRAY_M, lw=0.5,
                                    alpha=0.22, shrinkA=16, shrinkB=16,
                                    connectionstyle="arc3,rad=0.10"))
    # PCMCI+ 独有边（橙，中粗）
    for s, t in pcmci_only:
        ax.annotate("", xy=pos[t], xytext=pos[s],
                    arrowprops=dict(arrowstyle="->", color=ORANGE, lw=1.5,
                                    alpha=0.95, shrinkA=16, shrinkB=16,
                                    connectionstyle="arc3,rad=0.10"))
    # 确认边（蓝，线宽 ∝ |coef|；双向对用正负曲率区分方向）
    ab = {abs(x) for x in coef_map.values()}
    lo, hi = min(ab), max(ab)
    bidir_pairs = set()
    for s, t in conf:
        if (t, s) in set(conf):
            bidir_pairs.add(frozenset((s, t)))
    # 双向对弧线方向分配：源节点字母序小者凸正侧，反向凸负侧
    bidir_side = {}
    for s, t in conf:
        if frozenset((s, t)) in bidir_pairs:
            side = 1 if s < t else -1
            bidir_side[(s, t)] = side
            bidir_side[(t, s)] = -side
    for s, t in conf:
        c = abs(coef_map.get((s, t), lo))
        w = 0.7 + 2.8 * (c - lo) / max(hi - lo, 1e-9)
        alpha = 0.6 + 0.35 * (c - lo) / max(hi - lo, 1e-9)
        # 双向对两条弧线分别向两侧凸出（rad 正负），避免重叠成一束
        if frozenset((s, t)) in bidir_pairs:
            rad = 0.14 if (s, t) in bidir_side else -0.14
        else:
            rad = 0.05
        ax.annotate("", xy=pos[t], xytext=pos[s],
                    arrowprops=dict(arrowstyle="->", color=BLUE, lw=w,
                                    alpha=alpha, shrinkA=16, shrinkB=16,
                                    connectionstyle="arc3,rad={}".format(rad)))
    # 节点：大小 ∝ 累计负荷（冗余编码），编号 + CA 名双标注
    for i, nd in enumerate(NODE_ORDER):
        x, y = pos[nd]
        ax.scatter(x, y, s=260 + 420 * LOAD_N[i], color="white",
                   edgecolor=GRAY_D, lw=1.1, zorder=6)
        ax.text(x, y, str(i + 1), ha="center", va="center", fontsize=5.4,
                color=GRAY_D, zorder=7)
        ax.text(x * 1.34, y * 1.34, nd.replace("CA-", ""), ha="center",
                va="center", fontsize=4.8, color=GRAY_M, zorder=7)
    # 图例（左下角空白区）
    import matplotlib.lines as mlines
    handles = [
        mlines.Line2D([], [], color=BLUE, lw=2.2, alpha=0.9, ls="-",
                      label="TE→PCMCI+ 确认"),
        mlines.Line2D([], [], color=GRAY_M, lw=0.8, alpha=0.5, ls="--",
                      label="TE 候选未确认"),
        mlines.Line2D([], [], color=ORANGE, lw=1.5, alpha=0.95, ls="-",
                      label="PCMCI+ 独有"),
        mlines.Line2D([], [], marker="o", color="none", ms=6, mfc="white",
                      mec=GRAY_D, label="节点大小 ∝ 累计负荷"),
    ]
    ax.legend(handles=handles, loc="lower left", fontsize=5.6, frameon=False,
              handlelength=1.6, borderaxespad=0.1)
    ax.set_xlim(-1.62, 1.62)
    ax.set_ylim(-1.62, 1.62)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.text(0, -1.58, "箭头表示方向；线宽 ∝ |条件依赖系数|；自环（自回归滞后边 10 条）未绘制",
            ha="center", fontsize=5.8, color=GRAY_M)


def _funnel_panel(ax, data: dict) -> None:
    """中面板：验证漏斗（76 候选 → 44 确认 → 32 未确认；16 独有拆 6+10）。"""
    n_total = data["n_te_candidates"]           # 76
    n_conf = data["n_te_confirmed_by_pcmci"]    # 44
    n_te_only = data["n_te_candidates"] - n_conf
    n_pcmci_ns = sum(1 for e in data["pcmci_only_edges"] if e[0] != e[1])  # 6
    n_loop = len(data["pcmci_only_edges"]) - n_pcmci_ns                    # 10
    rows = [
        ("TE 候选边", n_total, BLUE, 0.0),
        ("PCMCI+ 确认", n_conf, BLUE, 0.25),
        ("未确认", n_te_only, RED_S, 0.0),
    ]
    y = np.arange(len(rows))[::-1]
    colors = [r[2] for r in rows]
    fracs = [r[1] / n_total for r in rows]
    widths = [max(0.10, 0.9 * f) for f in fracs]
    for yi, (name, val, color, _), wd, f in zip(y, rows, widths, fracs):
        ax.bar(yi, wd, width=0.5, color=color, alpha=0.85, edgecolor="white",
               linewidth=0.6, zorder=3)
        pct = "100" if f > 0.999 else "{:.0f}".format(100.0 * f)
        label = "{}\n{} 条（{}%）".format(name, val, pct) if val else name
        ax.text(yi, wd / 2, label, ha="center", va="center", fontsize=6.4,
                color="white", zorder=4)
    # 漏斗连接线（确认段到独有段的视觉导流）
    ax.plot([-0.32, -0.32], [y[1] + 0.25, y[2] - 0.25], color=GRAY_L, lw=0.8,
            ls=":", zorder=2)
    # PCMCI+ 独有（拆分标注）
    ax.text(0, y[0] - 0.85, "PCMCI+ 独有：节点间 {} 条 + 自回归滞后 {} 条".format(
        n_pcmci_ns, n_loop), ha="center", fontsize=6.8, color=ORANGE)
    ax.set_ylim(-1.4, len(rows) - 0.4)
    ax.set_xlim(-0.6, 0.6)
    ax.axis("off")
    ax.text(0, len(rows) + 0.75, "验证漏斗（TE 候选 → PCMCI+ 条件独立确认）",
            ha="center", fontsize=7.2, color=GRAY_D)


def _node_panel(ax, data: dict) -> None:
    """右面板：节点级验证堆叠条（确认/未确认 + PCMCI+ 独有出边）。"""
    from collections import Counter
    conf_out = Counter()
    te_out = Counter()
    pc_out = Counter()
    for s, t in data["confirmed_edges"]:
        conf_out[s] += 1
    for s, t in data["te_only_edges"]:
        te_out[s] += 1
    for s, t in data["pcmci_only_edges"]:
        pc_out[s] += 1
    rows = []
    for i, nd in enumerate(NODE_ORDER):
        rows.append((i + 1, nd, conf_out[nd], te_out[nd], pc_out[nd]))
    rows.sort(key=lambda r: -(r[2] + r[3]))  # 按候选出边总数降序
    y = np.arange(len(rows))
    for yi, (num, nd, c, t, p) in enumerate(rows):
        ax.barh(yi, c, height=0.62, color=BLUE, alpha=0.9, edgecolor="white",
                linewidth=0.5, zorder=3)
        ax.barh(yi, t, left=c, height=0.62, color=GRAY_M, alpha=0.7,
                edgecolor="white", linewidth=0.5, zorder=3)
        ax.barh(yi, p, left=c + t, height=0.62, color=ORANGE, alpha=0.95,
                edgecolor="white", linewidth=0.5, zorder=3)
        ax.text(0.4, yi, "{}".format(num), va="center", fontsize=5.6,
                color="white", zorder=4)
        ax.text(c + t + p + 0.6, yi, "{}".format(c + t + p), va="center",
                fontsize=5.4, color=GRAY_D, zorder=4)
    ax.set_yticks(y)
    ax.set_yticklabels([r[1].replace("CA-", "") for r in rows], fontsize=6.0)
    ax.set_ylim(-0.6, len(rows) - 0.4)
    ax.set_xlim(0, 16)
    ax.set_xlabel("出边数（确认 / 未确认 / PCMCI+ 独有）", fontsize=7.0)
    ax.tick_params(axis="x", labelsize=6.0)
    ax.spines[["top", "right"]].set_visible(False)
    # 堆叠图例（紧凑横排于顶部）
    import matplotlib.patches as mp
    handles = [
        mp.Patch(color=BLUE, label="确认"),
        mp.Patch(color=GRAY_M, label="TE 未确认"),
        mp.Patch(color=ORANGE, label="PCMCI+ 独有"),
    ]
    ax.legend(handles=handles, loc="lower right", fontsize=5.4, frameon=False,
              ncol=1, bbox_to_anchor=(1.0, 0.02))


def main() -> None:
    """绘制并导出三面板 PCMCI+ 验证网络图。"""
    data = json.load(open("outputs/analysis/pcmci/pcmci_summary.json"))
    fig, (ax1, ax2, ax3) = plt.subplots(
        1, 3, figsize=(10.4, 5.0),
        gridspec_kw={"width_ratios": [1.5, 0.9, 1.15], "wspace": 0.22},
    )
    _network_panel(ax1, data)
    _funnel_panel(ax2, data)
    _node_panel(ax3, data)
    final(fig, "fig5_2b_pcmci_validation_network", (10.4, 5.0))


if __name__ == "__main__":
    main()
