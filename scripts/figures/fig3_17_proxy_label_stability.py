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
    grid = fig.add_gridspec(1, 2, width_ratios=(1.02, 1.30), wspace=0.30,
                            left=0.12, right=0.985, top=0.79, bottom=0.23)
    ax_a = fig.add_subplot(grid[0, 0])
    ax_b = fig.add_subplot(grid[0, 1])

    fig.suptitle("代理标签定义下的模型排序敏感性", fontsize=11.2, fontweight="semibold", y=0.97)
    ax_a.set_title("A  不同评价口径的排序相关", loc="left", fontweight="semibold", pad=8)
    ax_b.set_title("B  12种配置的全局MAE排名", loc="left", fontweight="semibold", pad=8)

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

    # Panel B: all ranks are retained; only the self-loop and TCN ranks change.
    display = {
        "agcrn_full": "完整AGCRN", "mrg_equal_beta": "等权β",
        "mrg_full": "MRG-GCN", "mrg_no_skip": "无跳连",
        "mrg_no_refine": "无细化", "mrg_pattern": "轮廓关系",
        "mrg_fixed_gate": "固定门控", "mrg_load": "负荷关系",
        "mrg_event": "行为关系", "mrg_self_loop": "自环替换",
        "tcn": "TCN", "tcn_wide": "宽版TCN",
    }
    ax_b.set_xlim(0, 1)
    ax_b.set_ylim(12.65, 0.35)
    ax_b.set_yticks([])
    ax_b.set_xticks([0.44, 0.66], ["均匀分摊", "完成时刻\n截断"])
    ax_b.tick_params(axis="x", length=0, pad=6)
    ax_b.spines["left"].set_visible(False)
    ax_b.spines["bottom"].set_visible(False)
    ax_b.set_axisbelow(True)
    for rank in range(1, 13):
        ax_b.axhline(rank, color=COLORS["grid"], linewidth=0.55, zorder=0)
    for row in ranks:
        name = row["config"]
        before = int(row["uniform_rank"])
        after = int(row["alternative_rank"])
        changed = before != after
        color = COLORS["orange"] if changed else (
            COLORS["blue"] if name.startswith("mrg_") else COLORS["gray"]
        )
        ax_b.plot([0.44, 0.66], [before, after], color=color,
                  linewidth=1.6 if changed else 1.0,
                  alpha=0.95 if changed else 0.72, zorder=2)
        ax_b.scatter([0.44, 0.66], [before, after], s=18 if changed else 13,
                     color=color, edgecolor="white", linewidth=0.45, zorder=3)
        ax_b.text(0.39, before, display[name], ha="right", va="center",
                  fontsize=7.0, color=color if changed else COLORS["text"])
        ax_b.text(0.76, after, display[name], ha="left", va="center",
                  fontsize=7.0, color=color if changed else COLORS["text"])
        ax_b.text(0.425, before, str(before), ha="right", va="center",
                  fontsize=6.5, color=COLORS["gray"])
        ax_b.text(0.715, after, str(after), ha="left", va="center",
                  fontsize=6.5, color=COLORS["gray"])

    fig.text(0.12, 0.105,
             "A：圆点为先平均三种子MAE再排序；方点与横线为逐种子相关均值及范围。",
             ha="left", va="center", fontsize=6.8, color=COLORS["gray"])
    fig.text(0.12, 0.065,
             "B：橙色表示排名变化。逐种子范围为三次相关系数的最小值—最大值，不是置信区间。",
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
