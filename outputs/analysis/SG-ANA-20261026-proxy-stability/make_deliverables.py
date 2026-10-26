#!/usr/bin/env python3
"""Build CSV tables and the combined candidate figure from results.json."""
from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

OUT = Path(__file__).resolve().parent
D = json.loads((OUT / "results.json").read_text(encoding="utf-8"))

METRIC_LABELS = {
    "global_mae": "全局 MAE",
    "stable_mae": "稳定窗口 MAE",
    "zero_mae": "零目标 MAE",
    "nonzero_uniform_keys_mae": "固定均匀非零键 MAE",
    "event_mae": "标签事件 MAE",
    "nonzero_mae": "非零目标 MAE（评价标签）",
}
FIG_LABELS = {
    "global_mae": "Global MAE",
    "stable_mae": "Stable window",
    "zero_mae": "Zero target",
    "nonzero_uniform_keys_mae": "Fixed uniform-nonzero",
    "event_mae": "Labeled event",
    "nonzero_mae": "Nonzero (eval-label)",
}


def write_csvs() -> None:
    by_metric = D["exp19"]["ranking"]["by_metric"]
    seed_rank = D["exp19"]["ranking"]["per_seed_rank"]

    def seed_range(key: str) -> str:
        vals = [seed_rank[str(s)][key] for s in (2024, 2025, 2026)]
        return f"{min(vals):.3f}-{max(vals):.3f}"

    with (OUT / "table3_16_spearman.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["evaluation_definition", "rho_of_seed_mean_mae_ranks",
                    "mean_of_seed_rhos", "spearman_per_seed_range"])
        for key, label in METRIC_LABELS.items():
            s = by_metric[key]["rho_of_seed_mean_mae_ranks"]
            m = by_metric[key]["mean_of_seed_rhos"]
            w.writerow([label, f"{s:.3f}", f"{m:.3f}", seed_range(key)])

    with (OUT / "tableA2_rank_stability.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["config", "uniform_mae", "alternative_mae",
                    "uniform_rank", "alternative_rank", "rank_delta"])
        for r in D["exp19"]["ranking"]["rows"]:
            w.writerow([r["config"], f"{r['uniform_mae']:.6f}",
                        f"{r['alternative_mae']:.6f}", r["uniform_rank"],
                        r["alternative_rank"], f"{r['rank_delta']:+d}"])

    with (OUT / "table2x2.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "cell", "mrg_global_mae", "tcn_global_mae", "global_gap",
            "global_gap_pct", "mrg_nonzero_eval", "tcn_nonzero_eval",
            "mrg_nonzero_uniform", "tcn_nonzero_uniform",
            "mrg_event", "tcn_event",
        ])
        for cell, s in D["two_by_two"]["summary"].items():
            w.writerow([
                cell, f"{s['mrg_global_mae']:.6f}", f"{s['tcn_global_mae']:.6f}",
                f"{s['global_gap_tcn_minus_mrg']:+.6f}",
                f"{s['global_gap_pct_of_tcn']:+.2f}%",
                f"{s['mrg_nonzero_eval_mae']:.6f}", f"{s['tcn_nonzero_eval_mae']:.6f}",
                f"{s['mrg_nonzero_uniform_keys_mae']:.6f}",
                f"{s['tcn_nonzero_uniform_keys_mae']:.6f}",
                f"{s['mrg_event_mae']:.6f}", f"{s['tcn_event_mae']:.6f}",
            ])

    with (OUT / "table_gate_per_seed.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["label", "seed", "node_gate_mae", "shared_gate_mae", "node_gate_improvement_pct"])
        for label in ("uniform", "alternative"):
            for p in D["exp27"]["gate"][label]["per_seed"]:
                w.writerow([
                    label, p["seed"], f"{p['full_global_mae']:.6f}",
                    f"{p['shared_global_mae']:.6f}", f"{p['node_improvement_pct']:+.5f}",
                ])


def combined_figure() -> None:
    plt.rcParams.update({
        "font.size": 8.5,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.dpi": 150,
        "savefig.dpi": 1200,
        "savefig.bbox": "tight",
    })
    colors = {"bar": "#0072B2", "line": "#4D4D4D", "highlight": "#D55E00"}
    by_metric = D["exp19"]["ranking"]["by_metric"]
    rows = D["exp19"]["ranking"]["rows"]

    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(7.6, 3.9), gridspec_kw={"width_ratios": [1.0, 1.15]}
    )

    order = ["global_mae", "stable_mae", "zero_mae",
             "nonzero_uniform_keys_mae", "event_mae", "nonzero_mae"]
    vals = [by_metric[k]["rho_of_seed_mean_mae_ranks"] for k in order]
    labels = [FIG_LABELS[k] for k in order]
    y = np.arange(len(vals))
    ax1.barh(y, vals, color=colors["bar"], height=0.62)
    ax1.set_yticks(y)
    ax1.set_yticklabels(labels)
    ax1.invert_yaxis()
    ax1.set_xlim(0, 1.05)
    for yi, v in zip(y, vals):
        ax1.text(v + 0.01, yi, f"{v:.3f}", va="center", fontsize=7)
    ax1.set_xlabel("Spearman of seed-mean-MAE rankings")
    ax1.set_title("A  Spearman of seed-mean-MAE rankings", loc="left", fontsize=9)
    global_seed_mean = by_metric["global_mae"]["mean_of_seed_rhos"]
    ax1.text(0.0, -0.30,
             "Spearman after averaging MAE across seeds; mean of per-seed "
             f"correlations differs (global {global_seed_mean:.3f}).",
             transform=ax1.transAxes, ha="left", va="top", fontsize=6.2)

    for r in rows:
        changed = r["rank_delta"] != 0
        ax2.plot([0, 1], [r["uniform_rank"], r["alternative_rank"]],
                 marker="o", ms=3.2, lw=1.1,
                 color=colors["highlight"] if changed else colors["line"],
                 alpha=0.9 if changed else 0.55)
        ax2.text(-0.04, r["uniform_rank"], f"{r['uniform_rank']}  {r['config']}",
                 ha="right", va="center", fontsize=6.3)
        ax2.text(1.04, r["alternative_rank"], f"{r['alternative_rank']}  {r['config']}",
                 ha="left", va="center", fontsize=6.3)
    ax2.set_xlim(-0.62, 1.62)
    ax2.set_ylim(len(rows) + 0.5, 0.5)
    ax2.set_yticks([])
    ax2.spines["left"].set_visible(False)
    ax2.set_xticks([0, 1])
    ax2.set_xticklabels(["Uniform\nlabel", "Completion-\ntruncated"])
    ax2.set_title("B  Twelve configurations (rows ordered by rank; 1 = lowest MAE)",
                  loc="left", fontsize=9)
    ax2.text(0.5, -0.19, "highlighted: rank changed", transform=ax2.transAxes,
             ha="center", va="top", fontsize=6.5, color=colors["highlight"])

    fig.suptitle("Proxy-label sensitivity of model ranking", y=1.02, fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT / "fig3_17_proxy_rank_stability_candidate.png")
    fig.savefig(OUT / "fig3_17_proxy_rank_stability_candidate.svg")
    plt.close(fig)


if __name__ == "__main__":
    write_csvs()
    combined_figure()
    print("wrote CSV tables and combined candidate figure")
