"""论文图批次 2：⑥ 传递熵有向信息流 ⑦ 分层覆盖率对比 ⑧ CATE 分层热力图
⑨ 机制增强对比。输出 SVG + PNG(1200DPI) 到 outputs/figures/。

数据来源（本地已验证素材）：
- ⑥ outputs/analysis/transfer_entropy/transfer_entropy_summary.json
- ⑦ outputs/analysis/conformal_prediction/conformal_summary.json
- ⑧ outputs/analysis/counterfactual_cate/counterfactual_cate_summary.json
- ⑨ outputs/analysis/variant_quick_check/variant_napl.json + variant_gate-mi.json
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

FIG_DIR = Path("outputs/figures")
FIG_DIR.mkdir(parents=True, exist_ok=True)

setup_style(journal="general", lang="zh")
_colors = plt.rcParams["axes.prop_cycle"].by_key()["color"]
C1, C2, C3, C4, C5, C6 = _colors[:6]


def final(fig, name: str, size: tuple[float, float]) -> None:
    """统一导出：SVG 矢量 + PNG 1200 DPI（论文硬性约束）。"""
    export_figure(
        fig, basename=str(FIG_DIR / name),
        formats=["svg", "png"], dpi=1200, size_inches=size,
        grayscale_preview=False,
    )
    print(f"  ✅ {name}.svg / {name}.png（1200DPI）")


# ========== ⑥ 传递熵有向信息流 ==========
def fig_transfer_entropy() -> None:
    te = json.load(open("outputs/analysis/transfer_entropy/transfer_entropy_summary.json"))
    edges = te["significant_edges"]
    nodes = sorted({e["source"] for e in edges} | {e["target"] for e in edges})
    node_pos = {n: (np.cos(2 * np.pi * i / len(nodes)), np.sin(2 * np.pi * i / len(nodes)))
                for i, n in enumerate(nodes)}
    te_max = max(e["te"] for e in edges)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.2, 3.4),
                                   gridspec_kw={"width_ratios": [1.15, 1.0]})
    # (a) 有向信息流网络：圆环布局，箭头表示方向，线宽/色深表示 TE 强度
    for e in edges:
        s, t = node_pos[e["source"]], node_pos[e["target"]]
        w = 0.5 + 3.0 * e["te"] / te_max
        alpha = 0.35 + 0.6 * e["te"] / te_max
        ax1.annotate("", xy=t, xytext=s,
                     arrowprops=dict(arrowstyle="->", color=C1, lw=w, alpha=alpha,
                                     shrinkA=14, shrinkB=14,
                                     connectionstyle="arc3,rad=0.12"))
    for n, (x, y) in node_pos.items():
        ax1.scatter(x, y, s=320, color="white", edgecolor="0.3", zorder=5)
        ax1.text(x, y, n.split("-")[1], ha="center", va="center", fontsize=7.5, zorder=6)
    ax1.set_xlim(-1.25, 1.25)
    ax1.set_ylim(-1.25, 1.25)
    ax1.set_aspect("equal")
    ax1.axis("off")
    ax1.set_title(f"(a) 有向因果信息流（{te['overlap']['total_significant_edges']} 条显著边）",
                  fontsize=9, pad=6)

    # (b) 统计图覆盖 vs 因果独有边
    ov = te["overlap"]
    bars = ax2.bar(["显著因果边", "被统计图覆盖", "因果独有边"],
                   [ov["total_significant_edges"], ov["covered_by_any_statistical_graph"],
                    ov["exclusive_to_causal"]],
                   color=[C1, C3, C6], edgecolor="black", linewidth=0.4, width=0.55)
    for b, v in zip(bars, [ov["total_significant_edges"], ov["covered_by_any_statistical_graph"],
                           ov["exclusive_to_causal"]]):
        ax2.text(b.get_x() + b.get_width() / 2, v + 1, str(v), ha="center", fontsize=9)
    ax2.set_ylim(0, 90)
    ax2.set_ylabel("边数", fontsize=8.5)
    ax2.tick_params(axis="x", labelsize=8, rotation=12)
    ax2.tick_params(axis="y", labelsize=8)
    ax2.spines[["top", "right"]].set_visible(False)
    ax2.set_title(f"(b) 与统计图重叠（Jaccard 0.38–0.49）", fontsize=9, pad=6)

    fig.suptitle("传递熵方向性检验：76/90 显著边、44.4% 方向不对称",
                 fontsize=10, y=1.02)
    final(fig, "fig5_2_transfer_entropy", (7.2, 3.6))


# ========== ⑦ 分层覆盖率对比 ==========
def fig_coverage() -> None:
    c = json.load(open("outputs/analysis/conformal_prediction/conformal_summary.json"))
    groups = ["全局", "事件窗口", "稳定窗口"]
    std_v = [c["standard_overall_mean"], c["standard_event_mean"], c["standard_stable_mean"]]
    str_v = [c["stratified_overall_mean"], c["stratified_event_mean"], c["stratified_stable_mean"]]

    fig, ax = plt.subplots(figsize=(5.8, 3.5))
    x = np.arange(3)
    w = 0.34
    b1 = ax.bar(x - w / 2, std_v, w, label="标准共形", color="0.62",
                edgecolor="black", linewidth=0.4)
    b2 = ax.bar(x + w / 2, str_v, w, label="分层共形", color=C1,
                edgecolor="black", linewidth=0.4)
    for bars in (b1, b2):
        for b in bars:
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.01,
                    f"{b.get_height():.1%}", ha="center", fontsize=8)
    ax.axhline(0.9, color="0.3", lw=1.1, ls="--")
    ax.text(2.42, 0.905, "90% 目标覆盖率", fontsize=7.5, color="0.3", ha="right")
    # 事件窗口失效标注
    ax.annotate("标准共形失效\n1.9%", xy=(1 - w / 2, 0.019), xytext=(0.25, 0.18),
                fontsize=8, color="0.25",
                arrowprops=dict(arrowstyle="->", color="0.4", lw=0.8))
    ax.set_xticks(x)
    ax.set_xticklabels(groups, fontsize=9)
    ax.set_ylabel("覆盖率（α=0.1，3 种子合并）", fontsize=8.5)
    ax.set_ylim(0, 1.0)
    ax.tick_params(axis="y", labelsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(fontsize=8, frameon=False, loc="lower right")
    ax.set_title("分层共形：事件窗口覆盖率 1.9% → 86.1%", fontsize=10, pad=8)
    final(fig, "fig5_4_coverage", (5.8, 3.5))


# ========== ⑧ CATE 分层热力图 ==========
def fig_cate() -> None:
    cat = json.load(open("outputs/analysis/counterfactual_cate/counterfactual_cate_summary.json"))
    iv = cat["interventions"]
    names_cn = {
        "both_event": "全 event", "both_load": "全 load", "both_pattern": "全 pattern",
        "equal": "等权 1/3", "g1_load_g2_learn": "GCN1=load",
        "g1_learn_g2_pattern": "GCN2=pattern", "swapped": "交换两层",
    }
    order = [k for k in iv if k in names_cn]
    nodes = list(iv[order[0]]["node_deltas"].keys())

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.2, 3.8),
                                   gridspec_kw={"width_ratios": [1.0, 1.25]})
    # (a) 窗口分层条件效应：global/event/stable delta
    x = np.arange(len(order))
    w = 0.26
    g_d = [iv[k]["global_delta"] for k in order]
    e_d = [iv[k]["event_delta"] for k in order]
    s_d = [iv[k]["stable_delta"] for k in order]
    ax1.bar(x - w, g_d, w, label="全局", color=C1, edgecolor="black", linewidth=0.3)
    ax1.bar(x, e_d, w, label="事件窗口", color=C4, edgecolor="black", linewidth=0.3)
    ax1.bar(x + w, s_d, w, label="稳定窗口", color="0.62", edgecolor="black", linewidth=0.3)
    ax1.axhline(0, color="0.3", lw=0.8)
    ax1.set_xticks(x)
    ax1.set_xticklabels([names_cn[k] for k in order], fontsize=7.2, rotation=28, ha="right")
    ax1.set_ylabel("干预相对基线变化（正值 = 恶化）", fontsize=8)
    ax1.tick_params(axis="y", labelsize=7.5)
    ax1.spines[["top", "right"]].set_visible(False)
    ax1.legend(fontsize=7, frameon=False, loc="upper left")
    ax1.set_title("(a) 窗口分层条件效应", fontsize=9, pad=6)

    # (b) 节点敏感度热力图（7 干预 × 10 节点，相对变化倍数）
    matrix = np.array([[iv[k]["node_deltas"][n] for n in nodes] for k in order])
    im = ax2.imshow(matrix, cmap="YlOrRd", aspect="auto")
    ax2.set_xticks(range(len(nodes)))
    ax2.set_xticklabels([n.split("-")[1] for n in nodes], fontsize=7.5)
    ax2.set_yticks(range(len(order)))
    ax2.set_yticklabels([names_cn[k] for k in order], fontsize=7.5)
    for i in range(len(order)):
        for j in range(len(nodes)):
            v = matrix[i, j]
            ax2.text(j, i, f"{v:.1f}", ha="center", va="center", fontsize=6,
                     color="white" if v > matrix.max() * 0.6 else "0.2")
    cbar = fig.colorbar(im, ax=ax2, fraction=0.046, pad=0.03)
    cbar.set_label("MAE 相对变化（×）", fontsize=7.5)
    cbar.ax.tick_params(labelsize=7)
    ax2.set_title("(b) 节点敏感度（CA-303/317/304 最敏感 +409%/+361%/+350%）",
                  fontsize=8.5, pad=6)

    fig.suptitle("反事实分层归因：干预影响呈现窗口与节点条件效应",
                 fontsize=10, y=1.04)
    final(fig, "fig5_8_cate", (7.2, 4.0))


# ========== ⑨ 机制增强对比 ==========
def fig_mechanism_enhance() -> None:
    napl = json.load(open("outputs/analysis/variant_quick_check/variant_napl.json"))
    gmi = json.load(open("outputs/analysis/variant_quick_check/variant_gate-mi.json"))
    base = napl["baseline_val_mae"]

    fig, ax = plt.subplots(figsize=(5.6, 3.4))
    names = ["基线\n(StaticGraph)", "NAPL\n节点差异化参数", "Gate-MI\n门控专业化去相关"]
    vals = [base, napl["val_mae"], gmi["val_mae"]]
    colors = ["0.62", C1, C3]
    bars = ax.bar(names, vals, color=colors, edgecolor="black", linewidth=0.4, width=0.55)
    for b, v, name in zip(bars, vals, ["", "napl", "gate-mi"]):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.00035, f"{v:.4f}",
                ha="center", fontsize=9, fontweight="bold" if name else "normal")
    ax.annotate("−5.6%", xy=(1, napl["val_mae"]), xytext=(1, base + 0.0009),
                fontsize=9, color=C1, ha="center",
                arrowprops=dict(arrowstyle="->", color=C1, lw=1.0))
    ax.annotate("−5.3%", xy=(2, gmi["val_mae"]), xytext=(2, base + 0.0009),
                fontsize=9, color=C3, ha="center",
                arrowprops=dict(arrowstyle="->", color=C3, lw=1.0))
    ax.set_ylabel("验证集 MAE", fontsize=8.5)
    ax.set_ylim(0.0142, 0.0172)
    ax.tick_params(axis="x", labelsize=8)
    ax.tick_params(axis="y", labelsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_title("机制增强：NAPL 与门控专业化对比", fontsize=9.5, pad=8)
    final(fig, "fig5_6_mechanism_enhance", (5.6, 3.4))


if __name__ == "__main__":
    print("=== 批次 2：4 张图 ===")
    fig_transfer_entropy()
    fig_coverage()
    fig_cate()
    fig_mechanism_enhance()
    print("批次 2 完成")
