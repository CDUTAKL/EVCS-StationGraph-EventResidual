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
        mean, sd = mat.mean(axis=0), mat.std(axis=0)
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
    _final(fig, "fig3_4_mae_by_horizon", (8.4, 4.65))
    return None


def redraw_fig3_8() -> None:
    """图 3-8：分层窗口 MAE 对比（log 轴分组柱，事件窗口量级远大于稳定窗口）。"""
    fig, ax = plt.subplots(figsize=(8.2, 4.2))
    x = np.arange(len(SCOPES))
    width = 0.15
    for mi, (exp_id, label, color) in enumerate(MODELS):
        data = _load_model_metrics(exp_id)
        means, sds = [], []
        for scope_key, _cn in SCOPES:
            vals = np.asarray([data[s]["scopes"][scope_key] for s in SEEDS],
                              dtype=float)
            means.append(vals.mean())
            sds.append(vals.std())
        ax.bar(x + (mi - 2) * width, means, width=width, color=color,
               edgecolor="white", lw=0.5, yerr=sds, capsize=2.2,
               error_kw=dict(lw=0.8), label=label, zorder=3)
    ax.set_yscale("log")
    ax.set_xticks(x)
    ax.set_xticklabels([cn for _k, cn in SCOPES], fontsize=8.6)
    ax.set_ylabel("MAE（kWh/15 min，对数轴）", fontsize=8.8)
    ax.set_ylim(0.004, 0.7)
    ax.legend(fontsize=7.4, frameon=False, ncol=6, loc="upper left")
    _clean(ax)
    _final(fig, "fig3_8_mae_by_window", (8.2, 4.2))
    return None


def redraw_fig3_9() -> None:
    """图 3-9：逐节点 MAE 热力图（10 节点 × 6 模型，节点按累计负荷排序）。"""
    # 节点按测试集累计负荷降序（与图 2-3 排序口径一致）
    node_order = ["CA-303", "CA-304", "CA-305", "CA-307", "CA-311",
                  "CA-315", "CA-317", "CA-321", "CA-327", "CA-489"]
    mat = np.zeros((len(MODELS), len(node_order)))
    for mi, (exp_id, _label, _color) in enumerate(MODELS):
        data = _load_model_metrics(exp_id)
        for ni, node in enumerate(node_order):
            vals = [data[s]["by_node"].get(node, float("nan")) for s in SEEDS]
            mat[mi, ni] = np.nanmean(vals)

    fig, ax = plt.subplots(figsize=(8.0, 3.4))
    im = ax.imshow(mat, cmap="YlOrRd", aspect="auto",
                   vmin=mat.min(), vmax=mat.max())
    ax.set_xticks(range(len(node_order)))
    ax.set_xticklabels(node_order, fontsize=7.2, rotation=45, ha="right")
    ax.set_yticks(range(len(MODELS)))
    ax.set_yticklabels([lbl for _e, lbl, _c in MODELS], fontsize=7.8)
    for mi in range(mat.shape[0]):
        for ni in range(mat.shape[1]):
            ax.text(ni, mi, f"{mat[mi, ni]:.3f}", ha="center", va="center",
                    fontsize=6.2,
                    color="white" if mat[mi, ni] > mat.mean() else GRAY_D)
    cbar = fig.colorbar(im, ax=ax, fraction=0.045, pad=0.03)
    cbar.set_label("MAE（kWh/15 min，三种子均值）", fontsize=7.6)
    cbar.ax.tick_params(labelsize=7.2)
    ax.tick_params(length=0)
    _final(fig, "fig3_9_mae_by_node", (8.0, 3.4))
    return None


def redraw_fig3_10() -> None:
    """图 3-10：机制消融（SG-EXP-006）——基线 vs 四个变体的全局 MAE。

    基线 = SG-EXP-005（event_residual 正式三种子，night_run 流水线产物）；
    注意 no_event_gate 变体的语义（mechanism.py）：gate 关闭后残差修正路径
    **无条件作用于所有样本**（非"无修正"）——其大幅恶化证明门控的选择性
    激活是必要的，而非事件修正本身带来的收益。
    """
    variants = [
        ("baseline", "完整模型（基线）", BLUE),
        ("SG-EXP-006-ablation-no_graph", "无图（TCN 结构）", GRAY_M),
        ("SG-EXP-006-ablation-static_graph_only", "仅固定图", ORANGE),
        ("SG-EXP-006-ablation-adaptive_graph_only", "仅自适应图", GREEN),
        ("SG-EXP-006-ablation-no_event_gate", "门控关闭\n（全样本修正）", RED),
    ]
    fig, ax = plt.subplots(figsize=(7.8, 3.8))
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
        mean, sd = float(np.mean(vals)), float(np.std(vals))
        means.append(mean)
        sds.append(sd)
        ax.bar(xi, mean, width=0.56, color=color, edgecolor="white",
               yerr=sd, capsize=3.0, error_kw=dict(lw=0.9), zorder=3)
        ax.text(xi, mean + 0.0009, f"{mean:.4f}", ha="center", va="bottom",
                fontsize=7.2, color=GRAY_D)
    # ylim 数据定界（审查 C1：固定 0.017 会剪断 no_graph≈0.030 的柱子）
    ymax = max(m + s for m, s in zip(means, sds)) * 1.15
    ax.set_xticks(x)
    ax.set_xticklabels([lbl for _k, lbl, _c in variants], fontsize=7.6,
                       rotation=15, ha="right")
    ax.set_ylabel("全局 MAE（kWh/15 min）", fontsize=8.8)
    ax.set_ylim(0, ymax)
    _clean(ax)
    _final(fig, "fig3_10_mechanism_ablation", (7.8, 3.8))
    return None


def redraw_fig3_11() -> None:
    """图 3-11：测试集代表性事件窗口的真值 vs 预测时序（seed-2024）。"""
    df = pd.read_csv(
        "outputs/experiments/SG-EXP-004/20260731-102456/seed-2024/predictions.csv.gz")
    ev = df[(df["split"] == "test") & df["rule_trigger"]].copy()
    # 每 origin 有 4 个 horizon，rule_trigger 按 [O,N] 广播——取每 origin 首个 horizon 判定
    uniq = ev.drop_duplicates(["node_id", "origin_index"])[["node_id", "origin_index"]]
    # 选 rule_trigger 样本最密集的节点
    best_node = uniq["node_id"].value_counts().index[0]
    sub = ev[ev["node_id"] == best_node].sort_values("origin_index")
    origins = sub["origin_index"].unique()
    # 取第一段连续 origin 作为展示窗口（事件窗口段；按段长取 max 与数据分布无关紧要）
    breaks = np.where(np.diff(origins) > 1)[0]
    seg_start = int(breaks[0]) + 1 if len(breaks) else 0
    # 展示窗固定 48 个连续 origin（= 12 小时，覆盖 1-3 个合并窗口的长度量级）
    seg_origins = origins[seg_start:seg_start + 48]

    # 只需 h=1 预测（对齐 t+1），先滤 horizon 再按 origin 一次取齐
    h1 = sub[sub["horizon"] == 1].set_index("origin_index")
    truth_pts = h1.loc[seg_origins, "y_true"].to_numpy()
    pred_pts = h1.loc[seg_origins, "y_pred"].to_numpy()
    times = h1.loc[seg_origins, "target_index"].to_numpy()

    fig, ax = plt.subplots(figsize=(8.2, 3.6))
    ts = np.asarray(times)
    ax.plot(ts, truth_pts, color=GRAY_D, lw=1.4, label="真实负荷", zorder=3)
    ax.plot(ts, pred_pts, color=BLUE, lw=1.2, ls="--", marker="o", ms=3.2,
            label="预测（h=1）", zorder=4)
    ax.fill_between(ts, np.minimum(truth_pts, pred_pts),
                    np.maximum(truth_pts, pred_pts),
                    color=GRAY_XL, lw=0, zorder=1)
    ax.set_xlabel("目标时间索引（15 min 步长）", fontsize=8.6)
    ax.set_ylabel(f"{best_node} 负荷（kWh/15 min）", fontsize=8.6)
    ax.legend(fontsize=7.6, frameon=False, loc="lower left")
    _clean(ax)
    _final(fig, "fig3_11_event_window_forecast", (8.2, 3.6))
    return None


if __name__ == "__main__":
    print("=== 批次 12：第 3 章实验章新增 5 图 ===")
    redraw_fig3_4()
    redraw_fig3_8()
    redraw_fig3_9()
    redraw_fig3_10()
    redraw_fig3_11()
    print("批次 12 完成")
