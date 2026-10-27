#!/usr/bin/env python3
"""Recreate Fig. 3-17 from the frozen proxy-label stability CSV summaries."""
from __future__ import annotations

import csv
import re
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "outputs/analysis/SG-ANA-20261026-proxy-stability"
OUT = ROOT / "outputs/figures/fig3_17_proxy_label_stability"

COLORS = {
    "blue": "#52758C",
    "blue_light": "#AABBC5",
    "gray": "#7B858B",
    "grid": "#D9E0E4",
    "orange": "#C87952",
    "text": "#26333A",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def parse_range(value: str) -> tuple[float, float]:
    # Consume the separator explicitly: findall would read the separator in
    # 0.972-0.979 as a negative sign on the second endpoint.
    number = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)"
    match = re.fullmatch(rf"\s*({number})\s*[-–—~～]\s*({number})\s*",
                         value.replace("−", "-"))
    if match is None:
        raise ValueError(f"expected two numeric endpoints in range {value!r}")
    lower, upper = map(float, match.groups())
    if not -1 <= lower <= upper <= 1:
        raise ValueError(f"invalid ordered Spearman range {value!r}")
    return lower, upper


def build_figure() -> plt.Figure:
    corr = read_csv(DATA / "table3_16_spearman.csv")
    ranks = read_csv(DATA / "tableA2_rank_stability.csv")
    if len(corr) != 6 or len(ranks) != 12:
        raise ValueError(f"unexpected rows: correlations={len(corr)}, ranks={len(ranks)}")

    mpl.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["PingFang SC", "Noto Sans CJK SC", "Microsoft YaHei", "SimHei", "sans-serif"],
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "font.size": 8.2,
        "axes.titlesize": 9.4,
        "axes.labelsize": 8.2,
        "xtick.labelsize": 7.8,
        "ytick.labelsize": 7.8,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.linewidth": 0.8,
        "axes.labelcolor": COLORS["text"],
        "text.color": COLORS["text"],
        "xtick.color": COLORS["text"],
        "ytick.color": COLORS["text"],
        "savefig.facecolor": "white",
        "figure.facecolor": "white",
    })

    fig = plt.figure(figsize=(6.45, 4.40), constrained_layout=False)
    # 不设通栏大标题：全篇图件只有 A/B 面板标号，标题语义由论文图注承载；
    # gridspec top 相应上移，收回原大标题占用的空白带。
    grid = fig.add_gridspec(1, 2, width_ratios=(1.02, 1.30), wspace=0.30,
                            left=0.12, right=0.985, top=0.87, bottom=0.23)
    ax_a = fig.add_subplot(grid[0, 0])
    ax_b = fig.add_subplot(grid[0, 1])

    ax_a.set_title("A  不同评价口径的排序相关", loc="left", fontweight="semibold", pad=8)
    ax_b.set_title("B  两套标签的全局MAE对照", loc="left", fontweight="semibold", pad=8)

    # Panel A: distinguish correlations of mean-seed rankings from the mean of
    # per-seed correlations; per-seed ranges are shown as ranges, not intervals.
    labels = [
        "总体 MAE", "稳定窗口 MAE", "零目标 MAE",
        "固定均匀非零键", "标签事件 MAE", "非零目标 MAE",
    ]
    y = np.arange(len(corr))
    aggregate = np.array([float(row["rho_of_seed_mean_mae_ranks"]) for row in corr])
    per_seed_mean = np.array([float(row["mean_of_seed_rhos"]) for row in corr])
    ranges = [parse_range(row["spearman_per_seed_range"]) for row in corr]

    for i, (lo, hi) in enumerate(ranges):
        ax_a.plot([lo, hi], [y[i] + 0.12, y[i] + 0.12], color=COLORS["blue_light"],
                  linewidth=2.2, solid_capstyle="round", zorder=1)
        ax_a.scatter(per_seed_mean[i], y[i] + 0.12, marker="s", s=28,
                     facecolor=COLORS["blue_light"], edgecolor=COLORS["blue"],
                     linewidth=0.7, zorder=3)
        ax_a.scatter(aggregate[i], y[i] - 0.12, marker="o", s=35,
                     facecolor=COLORS["blue"], edgecolor="white", linewidth=0.6, zorder=4)
        ax_a.text(min(1.02, aggregate[i] + 0.035), y[i] - 0.12,
                  f"{aggregate[i]:.3f}", va="center", ha="left", fontsize=7.2,
                  color=COLORS["text"])
    ax_a.set_yticks(y, labels)
    ax_a.invert_yaxis()
    ax_a.set_xlim(-0.19, 1.19)
    # Omit a -0.1 tick: it is too close to zero and collides at print scale.
    ax_a.set_xticks([0.0, 0.25, 0.5, 0.75, 1.0])
    ax_a.set_xlabel("Spearman ρ")
    ax_a.axvline(0, color=COLORS["grid"], linewidth=0.8, zorder=0)
    ax_a.grid(axis="x", color=COLORS["grid"], linewidth=0.6, alpha=0.75)
    ax_a.set_axisbelow(True)
    ax_a.tick_params(axis="y", length=0, pad=5)

    # Panel B：两套标签下的全局 MAE 对照散点（2026-10-27 重构，替代排名
    # bump 图——12 个配置双列排名中 11 个不变，信息密度过低）。点按"均匀
    # 分摊名次"用浅灰折线依次相连：排序完全不变时折线严格单调上升，唯一的
    # 名次互换（自环替换 ↔ TCN，第 10↔11 位）在折线上形成可见的局部回折。
    display = {
        "agcrn_full": "完整AGCRN", "mrg_equal_beta": "等权β",
        "mrg_full": "MRG-GCN", "mrg_no_skip": "无跳连",
        "mrg_no_refine": "无细化", "mrg_pattern": "轮廓关系",
        "mrg_fixed_gate": "固定门控", "mrg_load": "负荷关系",
        "mrg_event": "行为关系", "mrg_self_loop": "自环替换",
        "tcn": "TCN", "tcn_wide": "宽版TCN",
    }
    ax_b.set_xlabel("均匀分摊标签  全局MAE（kWh/15 min）", fontsize=7.8)
    ax_b.set_ylabel("完成时刻截断标签  全局MAE（kWh/15 min）", fontsize=7.8)
    um = np.array([float(r["uniform_mae"]) for r in ranks])
    am = np.array([float(r["alternative_mae"]) for r in ranks])
    order_u = np.argsort(um)  # 按均匀分摊名次（= MAE 升序）连接
    ax_b.plot(um[order_u], am[order_u], color=COLORS["grid"], lw=0.9,
              zorder=1)
    for r in ranks:
        name = display[r["config"]]
        u, a = float(r["uniform_mae"]), float(r["alternative_mae"])
        changed = int(r["rank_delta"]) != 0
        color = COLORS["orange"] if changed else (
            COLORS["blue"] if r["config"].startswith("mrg_") else COLORS["gray"])
        ax_b.scatter(u, a, s=30 if changed else 22, facecolor=color,
                     edgecolor="white", linewidth=0.6, zorder=3)
        if changed:
            ax_b.annotate(name, (u, a), xytext=(6, -8 if "TCN" in name else 7),
                          textcoords="offset points", fontsize=7.0,
                          color=COLORS["orange"], fontweight="bold")
    ax_b.text(0.03, 0.97, "仅 自环替换 与 TCN 名次互换（第10、11位），\n"
                          "其余 10 种配置名次不变", transform=ax_b.transAxes,
              ha="left", va="top", fontsize=7.0, color=COLORS["gray"],
              linespacing=1.4)
    ax_b.grid(axis="both", color=COLORS["grid"], linewidth=0.6, alpha=0.75)
    ax_b.set_axisbelow(True)

    fig.text(0.12, 0.105,
             "A：圆点为先平均三种子MAE再排序；方点与横线为逐种子相关均值及范围（最小—最大值，不是置信区间）。",
             ha="left", va="center", fontsize=6.8, color=COLORS["gray"])
    fig.text(0.12, 0.065,
             "B：灰线按均匀分摊名次连接各配置，单调上升即排序不变；橙色为唯一互换名次的配置（自环替换与TCN）。",
             ha="left", va="center", fontsize=6.8, color=COLORS["gray"])
    fig.align_ylabels([ax_a])
    return fig


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    figure = build_figure()
    figure.savefig(OUT.with_suffix(".svg"), bbox_inches="tight")
    figure.savefig(OUT.with_suffix(".pdf"), bbox_inches="tight")
    figure.savefig(OUT.with_suffix(".png"), dpi=1200, bbox_inches="tight")
    plt.close(figure)
    print(OUT.with_suffix(".svg"))
    print(OUT.with_suffix(".pdf"))
    print(OUT.with_suffix(".png"))


if __name__ == "__main__":
    main()
