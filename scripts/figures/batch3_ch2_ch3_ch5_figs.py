"""论文图批次 3：第 2 章数据特征 5 张 + 第 3 章方法 2 张 + 第 5 章补充 2 张。

数据来源：
- ①~⑤ bundle（data/processed/SG-DATA-005-primary-tensor.npz）
- ⑥ outputs/experiments/SG-EXP-004/*/relation_matrices.npz（LRE 三关系矩阵）
- ⑦ SG-EXP-004 */seed-*/training_log.csv（validation MAE 收敛）
- ⑧ outputs/analysis/transfer_entropy/transfer_entropy_summary.json（方向不对称）
- ⑨ outputs/analysis/conformal_prediction/conformal_summary.json（per-node 分位数）
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

sys.path.insert(0, "src")
from evcs_station_graph.data import load_tensor_bundle  # noqa: E402

FIG_DIR = Path("outputs/figures")
FIG_DIR.mkdir(parents=True, exist_ok=True)

setup_style(journal="general", lang="zh")
_colors = plt.rcParams["axes.prop_cycle"].by_key()["color"]
C1, C2, C3, C4, C5, C6 = _colors[:6]

BUNDLE = load_tensor_bundle("data/processed/SG-DATA-005-primary-tensor.npz")


def final(fig, name: str, size: tuple[float, float]) -> None:
    """统一导出：SVG 矢量 + PNG 1200 DPI（论文硬性约束）。"""
    export_figure(
        fig, basename=str(FIG_DIR / name),
        formats=["svg", "png"], dpi=1200, size_inches=size,
        grayscale_preview=False,
    )
    print(f"  ✅ {name}.svg / {name}.png（1200DPI）")


# ========== ① 节点负荷热力图 ==========
def fig_load_heatmap() -> None:
    # 取连续 4 周（2018-05 前后 2688 步）10 节点负荷，行归一化显示模式
    t = 2688
    mat = BUNDLE.targets[:t].T  # [N, T]
    # 行归一化（0-1），突出时间模式而非量级差异
    vmax = mat.max(axis=1, keepdims=True)
    norm = mat / np.maximum(vmax, 1e-9)

    fig, ax = plt.subplots(figsize=(7.2, 3.0))
    im = ax.imshow(norm, aspect="auto", cmap="YlOrRd", extent=[0, t / 96, 0, 10],
                   vmin=0, vmax=1)
    ax.set_yticks(np.arange(10) + 0.5)
    ax.set_yticklabels([n.split("-")[1] for n in BUNDLE.node_ids], fontsize=8)
    ax.set_xlabel("时间（天）", fontsize=9)
    ax.set_xticks(range(0, 29, 4))
    ax.set_xticklabels(range(0, 29, 4), fontsize=8)
    cbar = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    cbar.set_label("归一化负荷", fontsize=7.5)
    cbar.ax.tick_params(labelsize=7)
    ax.set_title("10 节点负荷热力图（4 周，行归一化）", fontsize=10, pad=8)
    final(fig, "fig2_3_load_heatmap", (7.2, 3.0))


# ========== ② 典型周曲线 ==========
def fig_weekly_curves() -> None:
    # CA-303（最活跃 31.45%）与 CA-311（最低 14.62%）一周负荷
    nodes = ["CA-303", "CA-311", "CA-489"]
    t0 = 96 * 30  # 取 30 天后的完整一周
    t = np.arange(96 * 7) / 96.0  # 天
    fig, ax = plt.subplots(figsize=(6.8, 3.0))
    for n, c, ls in zip(nodes, [C1, C3, C6], ["-", "--", "-."]):
        idx = list(BUNDLE.node_ids).index(n)
        ax.plot(t, BUNDLE.targets[t0:t0 + 96 * 7, idx], color=c, ls=ls, lw=1.0,
                label=n)
    ax.set_xlabel("时间（天）", fontsize=9)
    ax.set_ylabel("负荷（kWh/15min）", fontsize=9)
    ax.tick_params(labelsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(fontsize=8, frameon=False, ncol=3, loc="upper left")
    ax.set_title("典型节点周负荷曲线（活跃度最高/最低/中等）", fontsize=10, pad=8)
    final(fig, "fig2_4_weekly_curves", (6.8, 3.0))


# ========== ③ 负荷分布（稀疏性） ==========
def fig_load_distribution() -> None:
    vals = BUNDLE.targets.flatten()
    vals = vals[vals > 0]  # 非零部分
    fig, ax = plt.subplots(figsize=(6.2, 3.2))
    ax.hist(vals, bins=80, color=C1, edgecolor="white", linewidth=0.2)
    ax.set_xlabel("负荷（kWh/15min）", fontsize=9)
    ax.set_ylabel("样本数（非零）", fontsize=9)
    ax.tick_params(labelsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    # 标注稀疏性
    ax.text(0.98, 0.95, f"全局非零率 21.59%\n峰均比 ≈ 38", transform=ax.transAxes,
            ha="right", va="top", fontsize=8.5, color="0.25")
    ax.set_title("节点负荷分布：极端稀疏（78% 样本为零）", fontsize=10, pad=8)
    final(fig, "fig2_5_load_distribution", (6.2, 3.2))


# ========== ④ 事件分数时间线 ==========
def fig_event_timeline() -> None:
    # 4 分量：access_count / departure_count / active_count 一阶差分 / load_jump_flag
    f = BUNDLE.features
    components = {
        "access": f[:, 0, 1], "departure": f[:, 0, 2],
        "active_delta": np.abs(np.diff(f[:, 0, 3], prepend=f[0, 0, 3])),
        "load_delta": f[:, 0, 6].astype(float),
    }
    # per-node std 归一化后求和（与事件分数口径一致）
    t0, t1 = 96 * 20, 96 * 21  # 取一天
    fig, ax = plt.subplots(figsize=(6.8, 3.0))
    bottom = np.zeros(t1 - t0)
    for name, (c, alpha) in zip(components, [(C1, 0.55), (C3, 0.55), (C6, 0.55), (C4, 0.55)]):
        seg = components[name][t0:t1]
        std = seg.std()
        seg_n = seg / std if std > 0 else seg
        ax.fill_between(np.arange(t1 - t0) / 4.0, bottom, bottom + seg_n,
                        color=c, alpha=alpha, label=name, step="mid")
        bottom = bottom + seg_n
    ax.set_xlabel("时间（小时）", fontsize=9)
    ax.set_ylabel("归一化事件分数分量", fontsize=9)
    ax.tick_params(labelsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(fontsize=7.5, frameon=False, ncol=4, loc="upper right")
    ax.set_title("事件分数 4 分量时间线（单日，CA-303）", fontsize=10, pad=8)
    final(fig, "fig2_6_event_timeline", (6.8, 3.0))


# ========== ⑤ 周期自相关 ==========
def fig_autocorrelation() -> None:
    from scipy import signal

    nodes = ["CA-303", "CA-327", "CA-489"]
    lags = np.arange(1, 193)  # 1~192 步 = 0.25h~48h
    fig, ax = plt.subplots(figsize=(6.8, 3.0))
    for n, c in zip(nodes, [C1, C3, C6]):
        idx = list(BUNDLE.node_ids).index(n)
        s = BUNDLE.targets[:, idx]
        acf = np.array([np.corrcoef(s[:-l], s[l:])[0, 1] for l in lags])
        ax.plot(lags / 4.0, acf, color=c, lw=1.0, label=n)
    ax.axvline(24, color="0.4", lw=0.8, ls="--")
    ax.axvline(7 * 24, color="0.4", lw=0.8, ls="--")
    ax.text(24, 0.92, "24h", fontsize=7.5, color="0.35", ha="center")
    ax.text(7 * 24, 0.92, "168h", fontsize=7.5, color="0.35", ha="center")
    ax.set_xlabel("滞后（小时）", fontsize=9)
    ax.set_ylabel("自相关系数", fontsize=9)
    ax.set_ylim(-0.05, 1.0)
    ax.tick_params(labelsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(fontsize=8, frameon=False, ncol=3, loc="upper right")
    ax.set_title("负荷自相关：24h 与 168h 周期显著", fontsize=10, pad=8)
    final(fig, "fig2_3b_autocorrelation", (6.8, 3.0))


# ========== ⑥ LRE 三关系矩阵热力图 ==========
def fig_lre_matrices() -> None:
    d = np.load("outputs/experiments/SG-EXP-004/20260731-102456/relation_matrices.npz")
    names = {"load": "负荷相关图（Pearson）", "event": "事件共现图（Jaccard）",
             "pattern": "时序模式图（DTW）"}
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.8))
    for ax, (key, title) in zip(axes, names.items()):
        mat = d[key]
        im = ax.imshow(mat, cmap="YlOrRd", aspect="equal", vmin=0,
                       vmax=mat.max() if mat.max() > 0 else 1)
        ax.set_xticks(range(10))
        ax.set_xticklabels([n.split("-")[1] for n in BUNDLE.node_ids], fontsize=6.5)
        ax.set_yticks(range(10))
        ax.set_yticklabels([n.split("-")[1] for n in BUNDLE.node_ids], fontsize=6.5)
        ax.set_title(title, fontsize=8.5, pad=5)
    cbar = fig.colorbar(im, ax=axes, fraction=0.025, pad=0.03)
    cbar.set_label("邻接权重（对称归一化）", fontsize=7.5)
    cbar.ax.tick_params(labelsize=7)
    fig.suptitle("LRE 三类关系图（top-k 稀疏化后）", fontsize=10, y=1.03)
    final(fig, "fig3_3_lre_matrices", (7.2, 2.9))


# ========== ⑦ 训练收敛曲线 ==========
def fig_training_curve() -> None:
    fig, ax = plt.subplots(figsize=(6.2, 3.2))
    seeds = ["2024", "2025", "2026"]
    for s, c, ls in zip(seeds, [C1, C3, C6], ["-", "--", "-."]):
        f = next(Path("outputs/experiments/SG-EXP-004").glob(f"*/seed-{s}/training_log.csv"))
        df = pd.read_csv(f)
        ax.plot(df["epoch"], df["validation_mae_scaled"], color=c, ls=ls, lw=1.5,
                label=f"seed {s}")
    ax.set_xlabel("训练轮次 (epoch)", fontsize=9)
    ax.set_ylabel("验证 MAE（标准化尺度）", fontsize=9)
    ax.tick_params(labelsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(fontsize=8, frameon=False, loc="upper right")
    ax.set_title("验证损失收敛（早停 patience=8，~38 轮）", fontsize=10, pad=8)
    final(fig, "fig3_5_training_curve", (6.2, 3.2))


# ========== ⑧ 方向不对称条形图 ==========
def fig_asymmetry() -> None:
    te = json.load(open("outputs/analysis/transfer_entropy/transfer_entropy_summary.json"))
    pairs = te["asymmetry"]["top_asymmetric_pairs"][:5]
    names = [f"{p['node_i'].split('-')[1]}→{p['node_j'].split('-')[1]}" for p in pairs]
    te_ij = [p["te_i_to_j"] for p in pairs]
    te_ji = [p["te_j_to_i"] for p in pairs]
    asym = [p["asymmetry"] for p in pairs]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.2, 3.0),
                                   gridspec_kw={"width_ratios": [1.5, 1.0]})
    x = np.arange(len(names))
    w = 0.36
    ax1.bar(x - w / 2, te_ij, w, label="i→j", color="0.62", edgecolor="black", linewidth=0.3)
    ax1.bar(x + w / 2, te_ji, w, label="j→i", color=C1, edgecolor="black", linewidth=0.3)
    for xi, (a, b) in enumerate(zip(te_ij, te_ji)):
        ax1.text(xi, max(a, b) + 0.0002, f"{max(a,b)/max(min(a,b),1e-9):.0f}×",
                 ha="center", fontsize=7)
    ax1.set_xticks(x)
    ax1.set_xticklabels(names, fontsize=8)
    ax1.set_ylabel("传递熵（nats）", fontsize=8.5)
    ax1.tick_params(axis="y", labelsize=7.5)
    ax1.spines[["top", "right"]].set_visible(False)
    ax1.legend(fontsize=7.5, frameon=False, loc="upper left")
    ax1.set_title("(a) 前 5 不对称方向对", fontsize=9, pad=6)

    ax2.barh(np.arange(len(pairs)), asym, color=C3, edgecolor="black", linewidth=0.3)
    ax2.set_yticks(range(len(pairs)))
    ax2.set_yticklabels(names, fontsize=8)
    ax2.set_xlabel("不对称度", fontsize=8.5)
    ax2.set_xlim(0, 1)
    ax2.tick_params(axis="x", labelsize=7.5)
    ax2.spines[["top", "right"]].set_visible(False)
    ax2.set_title("(b) 不对称度（0.44–0.84）", fontsize=9, pad=6)

    fig.suptitle("方向不对称性：信息流存在主导方向（44.4% 边不对称）",
                 fontsize=10, y=1.05)
    final(fig, "fig5_3_asymmetry", (7.2, 3.2))


# ========== ⑨ per-node 共形分位数对比 ==========
def fig_quantile_per_node() -> None:
    c = json.load(open("outputs/analysis/conformal_prediction/conformal_summary.json"))
    s0 = c["per_seed"][0]
    q_global = s0["q_global_per_node"]
    q_event = s0["q_event_per_node"]

    fig, ax = plt.subplots(figsize=(6.2, 3.2))
    x = np.arange(10)
    w = 0.36
    ax.bar(x - w / 2, q_global, w, label="全局分位数", color="0.62",
           edgecolor="black", linewidth=0.3)
    ax.bar(x + w / 2, q_event, w, label="事件层分位数", color=C1,
           edgecolor="black", linewidth=0.3)
    ax.set_xticks(x)
    ax.set_xticklabels([n.split("-")[1] for n in BUNDLE.node_ids], fontsize=8)
    ax.set_ylabel("90% 分位数（标准化残差）", fontsize=8.5)
    ax.tick_params(axis="y", labelsize=7.5)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(fontsize=7.5, frameon=False, loc="upper left")
    ax.set_title("事件层 vs 全局分位数（per-node，分层共形校准基础）", fontsize=9.5, pad=8)
    final(fig, "fig5_5_quantile_per_node", (6.2, 3.2))


if __name__ == "__main__":
    print("=== 批次 3：9 张图 ===")
    fig_load_heatmap()
    fig_weekly_curves()
    fig_load_distribution()
    fig_event_timeline()
    fig_autocorrelation()
    fig_lre_matrices()
    fig_training_curve()
    fig_asymmetry()
    fig_quantile_per_node()
    print("批次 3 完成")
