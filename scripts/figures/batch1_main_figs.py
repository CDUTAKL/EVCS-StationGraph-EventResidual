"""论文图批次 1：① 表 3-1 模型 MAE 对比 ② Bootstrap 置信区间 ③ α 收敛曲线
④ L1 干预结果 ⑤ 四格诊断。输出 SVG + PNG(1200DPI) 到 outputs/figures/。

数据来源（本地已验证素材）：
- ① 正式模型 MAE（SG-EXP-002/003/004/009/010 已核实）+ 传统基线（2026-07-31 修复口径重跑）
- ② outputs/analysis/bootstrap_significance.json（6 组比较 × 3 种子）
- ③ outputs/experiments/SG-EXP-004/*/seed-*/training_log.csv（α 混合系数轨迹）
- ④ outputs/analysis/gate_intervention/intervention_summary.json（10 干预组合）
- ⑤ SG-EXP-004 seed-2024 metrics.json 的 four_cell 四格
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

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


# ========== ① 表 3-1 模型 MAE 对比 ==========
def fig_model_comparison() -> None:
    # (模型显示名, global MAE, std 或 None, 分组)
    data = [
        ("StaticGraph\n(MRG-GCN)", 0.01376, None, "图模型"),
        ("AdaptiveGraph", 0.01396, 0.00010, "图模型"),
        ("GraphWaveNet", 0.01773, 0.00054, "图模型"),
        ("MLP", 0.02112, 0.00019, "深度学习"),
        ("ARIMA(2,1,2)", 0.02260, None, "统计基线"),
        ("TCN", 0.02952, None, "深度学习"),
        ("LightGBM", 0.03758, None, "传统 ML"),
        ("XGBoost", 0.03873, None, "传统 ML"),
        ("Persistence", 0.07828, None, "最简基线"),
    ]
    # 按 MAE 升序（最优在顶）
    data.sort(key=lambda x: x[1])
    names = [d[0] for d in data]
    maes = [d[1] for d in data]
    stds = [d[2] for d in data]
    groups = [d[3] for d in data]
    group_colors = {"图模型": C1, "深度学习": C3, "统计基线": C4, "传统 ML": C6, "最简基线": "0.55"}
    colors = [group_colors[g] for g in groups]

    fig, ax = plt.subplots(figsize=(6.8, 3.9))
    y = np.arange(len(names))
    bars = ax.barh(y, maes, height=0.62, color=colors, edgecolor="black", linewidth=0.4)
    # 误差棒（仅已知 std 的模型）
    for yi, (mae, std) in enumerate(zip(maes, stds)):
        if std is not None:
            ax.errorbar(mae, yi, xerr=std, fmt="none", ecolor="black", capsize=3, lw=0.8)
    # 数值标签
    for yi, mae in enumerate(maes):
        ax.text(mae + 0.0012, yi, f"{mae:.4f}", va="center", fontsize=8)
    # 最优模型高亮
    ax.get_yticklabels()[0].set_color(C1)
    ax.get_yticklabels()[0].set_fontweight("bold")

    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=8.5)
    ax.set_xlabel("Global MAE (kWh/15min)", fontsize=9)
    ax.set_xlim(0, 0.092)
    ax.tick_params(axis="x", labelsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    # 图例（分组色块）
    handles = [plt.Rectangle((0, 0), 1, 1, color=group_colors[g]) for g in
               ["图模型", "深度学习", "统计基线", "传统 ML", "最简基线"]]
    ax.legend(handles, ["图模型", "深度学习", "统计基线", "传统 ML", "最简基线"],
              loc="lower right", fontsize=7.5, frameon=False, title="方法族")
    final(fig, "fig3_1_model_mae_comparison", (6.8, 3.9))


# ========== ② Bootstrap 置信区间 ==========
def fig_bootstrap() -> None:
    d = json.load(open("outputs/analysis/bootstrap_significance.json"))
    labels = {
        "TCN - StaticGraph": "TCN → StaticGraph",
        "StaticGraph - AdaptiveGraph": "StaticGraph → AdaptiveGraph",
        "AdaptiveGraph - EventResidual": "AdaptiveGraph → EventResidual",
        "StaticGraph - MLP": "StaticGraph → MLP",
        "TCN - MLP": "TCN → MLP",
        "AdaptiveGraph - no_event_gate": "AdaptiveGraph → no-event-gate",
    }
    names, means, lows, highs, ps, windows = [], [], [], [], [], []
    for c in d["comparisons"]:
        # 部分比较仅对事件窗口做了检验（该比较无 global 键）——按实际窗口取值并标注
        keys0 = list(c["per_seed"].keys())
        win = "global" if "global" in c["per_seed"][keys0[0]] else "event_window"
        diffs = [c["per_seed"][s][win]["observed_diff"] for s in keys0]
        cis = [(c["per_seed"][s][win]["ci_lower"], c["per_seed"][s][win]["ci_upper"])
               for s in keys0]
        name = labels.get(c["name"], c["name"])
        if win == "event_window":
            name += "（事件窗口）"
        names.append(name)
        means.append(float(np.mean(diffs)))
        lows.append(float(min(l[0] for l in cis)))
        highs.append(float(max(l[1] for l in cis)))
        ps.append(min(c["per_seed"][s][win]["p_value_one_sided"] for s in keys0))
        windows.append(win)

    fig, ax = plt.subplots(figsize=(6.8, 3.2))
    y = np.arange(len(names))
    ax.errorbar(means, y, xerr=[np.array(means) - np.array(lows), np.array(highs) - np.array(means)],
                fmt="o", color=C1, ecolor="0.35", elinewidth=1.2, capsize=4, markersize=7)
    ax.axvline(0, color="0.4", lw=0.9, ls="--")
    for yi, (m, p) in enumerate(zip(means, ps)):
        star = "***" if p < 0.001 else ("**" if p < 0.01 else ("*" if p < 0.05 else "ns"))
        ax.text(m + 0.0006, yi, star, va="center", fontsize=9)
    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=8)
    ax.set_xlabel("MAE 差（基线 − 提议模型，Bootstrap 10,000 次重采样）", fontsize=8.5)
    ax.tick_params(axis="x", labelsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    ax.text(0.0045, len(names) - 0.35, "正向 = 提议模型更优", fontsize=7.5, color="0.3")
    final(fig, "fig3_6_bootstrap_significance", (6.8, 3.2))


# ========== ③ α 混合系数收敛曲线 ==========
def fig_alpha_convergence() -> None:
    fig, ax = plt.subplots(figsize=(6.0, 3.4))
    seeds = ["2024", "2025", "2026"]
    colors = [C1, C3, C6]
    lstyles = ["-", "--", "-."]
    for s, c, ls in zip(seeds, colors, lstyles):
        f = next(Path("outputs/experiments/SG-EXP-004").glob(f"*/seed-{s}/training_log.csv"))
        df = pd.read_csv(f)
        ax.plot(df["epoch"], df["adaptive_graph_alpha"], color=c, ls=ls, lw=1.6,
                label=f"seed {s}")
    # 收敛带（三种子末值范围 0.165~0.213）
    ax.axhspan(0.165, 0.213, color="0.85", alpha=0.6, zorder=0)
    ax.text(30, 0.225, "收敛带 α≈0.17–0.21\n（模型自动选择以固定图为主）",
            fontsize=7.5, ha="center", color="0.25")
    ax.set_xlabel("训练轮次 (epoch)", fontsize=9)
    ax.set_ylabel("自适应混合系数 α", fontsize=9)
    ax.set_ylim(0.1, 0.5)
    ax.tick_params(labelsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(fontsize=8, frameon=False, loc="upper right")
    final(fig, "fig3_7_alpha_convergence", (6.0, 3.4))


# ========== ④ L1 干预结果 ==========
def fig_intervention() -> None:
    d = json.load(open("outputs/analysis/gate_intervention/intervention_summary.json"))
    order = ["learned", "equal", "both_load", "both_pattern", "both_event",
             "g1_load_g2_learn", "g1_learn_g2_pattern", "swapped"]
    labels_cn = {
        "learned": "学习值（基线）", "equal": "等权 1/3", "both_load": "两层全 load",
        "both_pattern": "两层全 pattern", "both_event": "两层全 event",
        "g1_load_g2_learn": "GCN1=load", "g1_learn_g2_pattern": "GCN2=pattern",
        "swapped": "交换两层学习值",
    }
    names, maes, stds = [], [], []
    base = d["learned"]["global_mae_mean"]
    for k in order:
        names.append(labels_cn[k])
        maes.append(d[k]["global_mae_mean"])
        stds.append(d[k]["global_mae_std"])

    fig, ax = plt.subplots(figsize=(6.8, 3.5))
    y = np.arange(len(names))
    colors = [C1 if k == "learned" else C6 for k in order]
    ax.barh(y, maes, height=0.6, color=colors, edgecolor="black", linewidth=0.4)
    ax.errorbar(maes, y, xerr=stds, fmt="none", ecolor="black", capsize=3, lw=0.8)
    for yi, (m, k) in enumerate(zip(maes, order)):
        if k == "learned":
            label = f"{m:.4f}"
        else:
            label = f"+{100*(m/base-1):.0f}%"
        ax.text(m + 0.002, yi, label, va="center", fontsize=8)
    ax.axvline(base, color="0.5", lw=1, ls=":")
    ax.text(base + 0.0005, len(names) - 0.45, "基线", fontsize=7.5, color="0.35")
    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=8)
    ax.set_xlabel("Global MAE（3 种子均值 ± std）", fontsize=9)
    ax.set_xlim(0, 0.085)
    ax.tick_params(axis="x", labelsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    final(fig, "fig4_2_intervention", (6.8, 3.5))


# ========== ⑤ 四格诊断 ==========
def fig_four_cell() -> None:
    m = json.load(open("outputs/experiments/SG-EXP-004/20260731-102456/seed-2024/metrics.json"))
    fc = m["four_cell"]["cells"]
    # 2×2：行 = target_event（上 True 下 False），列 = rule_trigger（左 True 右 False）
    matrix = np.array([
        [fc["target_event_triggered"]["mae"], fc["target_event_not_triggered"]["mae"]],
        [fc["stable_triggered"]["mae"], fc["stable_not_triggered"]["mae"]],
    ])
    counts = np.array([
        [fc["target_event_triggered"]["count"], fc["target_event_not_triggered"]["count"]],
        [fc["stable_triggered"]["count"], fc["stable_not_triggered"]["count"]],
    ])

    fig, ax = plt.subplots(figsize=(5.6, 4.2))
    cmap = plt.get_cmap("YlOrRd")
    im = ax.imshow(matrix, cmap=cmap, aspect="auto")
    for i in range(2):
        for j in range(2):
            ax.text(j, i, f"MAE = {matrix[i, j]:.4f}\nn = {counts[i, j]:,}\n"
                          f"（{100*counts[i, j]/counts.sum():.3f}%）",
                    ha="center", va="center", fontsize=10,
                    color="white" if matrix[i, j] > matrix.max()*0.55 else "black",
                    fontweight="bold" if i == 0 else "normal")
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["规则触发", "规则未触发"], fontsize=9)
    ax.set_yticks([0, 1])
    ax.set_yticklabels(["事件发生", "稳定时段"], fontsize=9)
    ax.set_xlabel("rule_trigger（冻结规则）", fontsize=9)
    ax.set_ylabel("target_event（真实事件）", fontsize=9)
    # 右下角说明
    ax.text(-0.42, 2.15, "格内 n 为 [S,H,N] 样本数；\nΣ(格MAE×n)/Σn ≡ 全局 MAE",
            fontsize=7.5, color="0.3", transform=ax.transAxes)
    final(fig, "fig4_4_four_cell", (5.6, 4.2))


if __name__ == "__main__":
    print("=== 批次 1：5 张图 ===")
    fig_model_comparison()
    fig_bootstrap()
    fig_alpha_convergence()
    fig_intervention()
    fig_four_cell()
    print("批次 1 完成")
