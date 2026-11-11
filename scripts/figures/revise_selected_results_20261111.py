"""Data-preserving redesign of three result figures and the enlarged TE panel.

Every plotted observation is loaded from the existing frozen evidence records.
No new statistical tests or model evaluations are performed here.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import FancyBboxPatch, Rectangle
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/figures"
sys.path.insert(0, str(Path(__file__).resolve().parent))
import batch23_jpl_figs as jpl
import fig5_9_acn_current_shape as current
import fig5_3_te_relation_scatter as te_source

INK = "#243C4B"
MUTED = "#607582"
GRID = "#E3EBEF"
TEAL = "#1F8FAE"
CORAL = "#EF786D"
SKY = "#70ACDE"
GOLD = "#D9AD51"
PAPER = "#F5F9FA"
plt.rcParams.update({
    "font.family": ["Arial", "PingFang SC"],
    "font.sans-serif": ["Arial", "PingFang SC", "Heiti SC", "DejaVu Sans"],
    "font.size": 9, "axes.labelsize": 9, "xtick.labelsize": 8,
    "ytick.labelsize": 8.5, "axes.unicode_minus": False,
    "svg.fonttype": "none", "pdf.fonttype": 42,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.linewidth": .6, "text.color": INK, "axes.labelcolor": INK,
    "xtick.color": MUTED, "ytick.color": INK, "figure.facecolor": "white",
    "figure.constrained_layout.use": False, "figure.autolayout": False,
})
SOURCES: dict = {}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def heading(fig, x, y, letter, title, subtitle=None, color=TEAL):
    fig.text(x, y, letter, fontsize=12, weight="bold", color=color, va="center")
    fig.text(x + .035, y, title, fontsize=10.4, weight="bold", va="center")
    if subtitle:
        fig.text(x + .035, y - .052, subtitle, fontsize=8, color=MUTED, va="center")


def clean(ax, axis="x"):
    ax.set_axisbelow(True)
    ax.grid(axis=axis, color=GRID, lw=.65)
    ax.tick_params(length=0, pad=5)
    for side in ("bottom", "left"):
        ax.spines[side].set_color("#B6C6CE")


def export(fig, stem, data):
    """SVG editable text; archival PNG 1200 DPI; modest-size QA preview."""
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / f"{stem}.svg", bbox_inches=None)
    fig.savefig(OUT / f"{stem}.png", dpi=1200, bbox_inches=None)
    preview = ROOT / "tmp/figure-review-20261111"
    preview.mkdir(parents=True, exist_ok=True)
    fig.savefig(preview / f"{stem}.png", dpi=300, bbox_inches=None)
    plt.close(fig)
    SOURCES[stem] = data
    (OUT / f"{stem}_source.json").write_text(json.dumps(data, ensure_ascii=False, indent=2))


def draw_jpl():
    frame = jpl._load_per_seed()
    intervals = jpl._load_intervals()
    models = [("mrg_full", "MRG-GCN", TEAL),
              ("tcn_wide", "TCN", CORAL),
              ("agcrn_full", "完整 AGCRN", SKY),
              ("mrg_shared_gate", "共享门控", GOLD)]
    fig = plt.figure(figsize=(6.45, 3.55))
    heading(fig, .035, .945, "A", "整体预测误差", "3个训练种子 · 菱形为均值 ± SD")
    heading(fig, .568, .945, "B", "相对 MRG-GCN 的误差差", "对照 − MRG-GCN · 正值表示 MRG-GCN 更低")
    left = fig.add_axes([.145, .255, .285, .55])
    right = fig.add_axes([.650, .255, .250, .55])
    marks = ["o", "s", "^"]
    offsets = [-.17, 0, .17]
    for row, (model, label, color) in enumerate(models):
        if row == 0:
            left.axhspan(-.40, .40, color="#EAF6F7", zorder=0)
        vals = frame.loc[frame.model == model].set_index("seed").loc[list(jpl.SEEDS), "mae"].to_numpy()
        mean, sd = float(vals.mean()), float(vals.std(ddof=1))
        left.hlines(row, mean-sd, mean+sd, color=color, lw=2, zorder=3)
        left.plot([mean-sd, mean+sd], [row, row], "|", color=color, ms=7, mew=1.2)
        for val, off, marker in zip(vals, offsets, marks):
            left.scatter(val, row+off, s=22, marker=marker, color=color,
                         edgecolor="white", linewidth=.5, zorder=4)
        left.scatter(mean, row, s=47, marker="D", color=color,
                     edgecolor="white", linewidth=.9, zorder=5)
        left.text(1.055, row, f"{mean:.5f}", transform=left.get_yaxis_transform(),
                  ha="left", va="center", fontsize=8.2, color=INK)
    left.set_yticks(range(4), [m[1] for m in models])
    left.set_ylim(3.5, -.5)
    left.set_xlim(.08025, .08465)
    left.set_xticks([.081, .082, .083, .084])
    left.set_xlabel("MAE（kWh/15 min）", labelpad=10)
    clean(left)

    right.axvspan(0, .00615, color="#F1F8F8", zorder=0)
    mrg = frame.loc[frame.model == "mrg_full"].set_index("seed")["mae"]
    effects = []
    for row, (model, _label, color) in enumerate(models[1:]):
        item = intervals.loc[model]
        d, lo, hi = [float(item[k]) for k in ["difference", "ci98_333333_lower", "ci98_333333_upper"]]
        vals = frame.loc[frame.model == model].set_index("seed")["mae"]
        paired = np.asarray([vals.loc[seed]-mrg.loc[seed] for seed in jpl.SEEDS])
        right.hlines(row, lo, hi, color=color, lw=2.7, zorder=3)
        right.plot([lo, hi], [row, row], "|", color=color, ms=8, mew=1)
        for val, off, marker in zip(paired, [-.14, 0, .14], marks):
            right.scatter(val, row+off, s=18, marker=marker, color=color,
                          edgecolor="white", linewidth=.5, zorder=4)
        right.scatter(d, row, s=48, color=color, edgecolor="white", linewidth=.9, zorder=5)
        reduction = float(item["relative_mae_reduction_percent"])
        right.text(1.025, row, f"{reduction:.2f}%", transform=right.get_yaxis_transform(),
                   va="center", ha="left", color=color, weight="bold", fontsize=9)
        effects.append({"model": model, "difference": d, "interval": [lo, hi], "seed_differences": paired.tolist()})
    right.set_ylim(2.5, -.5)
    right.set_yticks(range(3), [m[1] for m in models[1:]])
    right.set_xlim(-.00035, .00615)
    right.set_xticks([0, .002, .004, .006], ["0", ".002", ".004", ".006"])
    right.axvline(0, color="#81949F", lw=.8, zorder=2)
    right.set_xlabel("MAE 差（kWh/15 min）", labelpad=10)
    clean(right)
    fig.text(.956, .825, "MAE降低", ha="center", fontsize=7.7, color=MUTED)
    handles = [Line2D([], [], marker=mk, color=MUTED, linestyle="none", markersize=4,
                      label=str(seed)) for seed, mk in zip(jpl.SEEDS, marks)]
    fig.legend(handles=handles, loc="lower left", bbox_to_anchor=(.13, .010),
               ncol=3, frameon=False, fontsize=8, handletextpad=.4, columnspacing=1.2)
    fig.text(.96, .075, "右侧粗线：七日块 98.33% 校正区间", ha="right", fontsize=7.8, color=MUTED)
    fig.text(.96, .030, "种子离散程度与时间块区间分别呈现", ha="right", fontsize=7.8, color=MUTED)
    export(fig, "fig3_9_jpl_mae_primary", {
        "sources": {str(p.resolve().relative_to(ROOT)): digest(p) for p in [jpl.PER_SEED_CSV, jpl.INTERVALS_CSV, jpl.SUMMARY_CSV]},
        "n_seeds": 3, "left_spread": "sample SD", "right_interval": "Bonferroni 98.333% percentile, 24 seven-day blocks, 10000 resamples",
        "effect_rows": effects, "observations_excluded": 0})


def draw_current():
    results, _ = current.load_evidence()
    nodes = sorted(results, key=lambda node: -results[node]["tv_distance"])
    tv = np.asarray([results[n]["tv_distance"] for n in nodes])
    peak = np.asarray([results[n]["peak_share_ratio"] for n in nodes])
    fig = plt.figure(figsize=(6.25, 3.90))
    heading(fig, .035, .945, "A", "会话内形态差异", "电流积分份额与均匀份额的总变差距离")
    heading(fig, .550, .945, "B", "峰值片集中度", "最大电流份额 / 同会话均匀份额", color=CORAL)
    axes = [fig.add_axes([.145, .180, .342, .635]),
            fig.add_axes([.565, .180, .360, .635])]
    for ax, data, base, color, tint, limits, ticks in [
        (axes[0], tv, 0, TEAL, "#DCEFF2", (-.015, .70), [0, .2, .4, .6]),
        (axes[1], peak, 1, CORAL, "#FAE3DB", (.85, 5.03), [1, 2, 3, 4, 5])]:
        for row, val in enumerate(data):
            if row % 2 == 0:
                ax.axhspan(row-.46, row+.46, color=PAPER, zorder=0)
            ax.hlines(row, base, val, color=tint, lw=4.0, zorder=2)
            ax.scatter(val, row, s=44, color=color, edgecolor="white", linewidth=.7, zorder=4)
            ax.annotate(f"{val:.3f}" if base == 0 else f"{val:.2f}×", (val, row),
                        xytext=(6, 0), textcoords="offset points", va="center", color=INK, fontsize=8.6)
        median = float(np.median(data))
        ax.axvline(median, color=color, linestyle=(0, (3, 3)), lw=.9, alpha=.8, zorder=1)
        if base == 1:
            ax.axvline(1, color="#81949F", lw=.8, zorder=1)
        ax.set_ylim(7.65, -.65)
        ax.set_xlim(*limits)
        ax.set_xticks(ticks)
        ax.set_yticks(range(8), nodes if base == 0 else [""]*8)
        ax.spines["left"].set_visible(False)
        clean(ax)
        label = f"中位数 {median:.3f}" if base == 0 else f"中位数 {median:.2f}×"
        ax.text(.02, -.18, label, transform=ax.transAxes, color=color, weight="bold", fontsize=9)
    fig.text(.5, .018, "8个有效会话；两面板保持相同顺序", ha="center", color=MUTED, fontsize=8)
    export(fig, "fig5_8_acn_current_shape", {
        "sources": {str(current.REPLAY_PATH.relative_to(ROOT)): digest(current.REPLAY_PATH)},
        "eligible": 8, "preselected": 10, "excluded": 2,
        "exclusion_rule": "Existing frozen quality or availability failure; no new selection",
        "order": "descending TVD; same node order in both panels",
        "rows": [{"node": n, "tv_distance": float(t), "peak_share_ratio": float(v)} for n, t, v in zip(nodes, tv, peak)],
        "median_tv": float(np.median(tv)), "median_peak": float(np.median(peak)),
        "inference": "descriptive convenience sample; no error bars or hypothesis test"})


def draw_pcmci():
    path = ROOT / "outputs/analysis/pcmci/pcmci_summary.json"
    data = json.loads(path.read_text())
    groups = [{tuple(e) for e in data[k] if e[0] != e[1]} for k in
              ["confirmed_edges", "te_only_edges", "pcmci_only_edges"]]
    assert [len(g) for g in groups] == [44, 32, 6]
    assert all(not groups[i] & groups[j] for i in range(3) for j in range(i))
    ids = sorted({n for g in groups for edge in g for n in edge})
    matrix = np.zeros((10, 10), dtype=int)
    for kind, group in enumerate(groups, 1):
        for source, target in group:
            matrix[ids.index(source), ids.index(target)] = kind
    np.fill_diagonal(matrix, -1)
    assert int(np.count_nonzero(matrix == 0)) == 8
    styles = {1: (TEAL, "o", "两法均达"), 2: (CORAL, "s", "仅TE达"),
              3: (GOLD, "^", "仅PCMCI+达"), 0: ("#B4C1C9", "o", "两法均未达")}
    fig = plt.figure(figsize=(6.30, 4.05))
    heading(fig, .035, .955, "A", "有向节点对归类", "行是源节点，列是目标节点")
    heading(fig, .590, .955, "B", "名义阈值交集", "同一批90个非对角有向对")
    ax = fig.add_axes([.128, .198, .425, .66])
    for i in range(10):
        for j in range(10):
            kind = int(matrix[i, j])
            ax.add_patch(Rectangle((j-.48, i-.48), .96, .96,
                                  facecolor="#EDF2F4" if kind == -1 else "#F6F9FA", edgecolor="none"))
            if kind == -1:
                ax.plot(j, i, marker="x", color="#B9C5CC", ms=4, mew=.6)
            else:
                color, marker, _ = styles[kind]
                ax.scatter(j, i, s=31 if kind else 20, marker=marker,
                           facecolor=color if kind else "white", edgecolor=color, linewidth=.7)
    ax.set_xlim(-.55, 9.55); ax.set_ylim(9.55, -.55)
    ax.set_xticks(range(10), [n.removeprefix("CA-") for n in ids], fontsize=7.7)
    ax.set_yticks(range(10), ids, fontsize=8)
    ax.set_xlabel("目标节点（CA-）", fontsize=8.5, labelpad=7)
    ax.set_ylabel("源节点", fontsize=8.5, labelpad=4)
    ax.tick_params(length=0, pad=4)
    for spine in ax.spines.values():
        spine.set_visible(False)

    cross = fig.add_axes([.650, .290, .305, .477])
    cross.set_xlim(-.65, 2.0); cross.set_ylim(2.0, -.42); cross.axis("off")
    cross.text(1.0, -.32, "PCMCI+", ha="center", fontsize=9, weight="bold")
    cross.text(1.5, -.32, "", ha="center")
    for j, label in enumerate(["达阈值", "未达阈值"]):
        cross.text(j+.5, -.10, label, ha="center", va="center", fontsize=8.2, color=MUTED)
    cross.text(-.53, 1, "TE", ha="center", va="center", weight="bold", fontsize=9)
    for i, label in enumerate(["达阈值", "未达阈值"]):
        cross.text(-.12, i+.5, label, ha="right", va="center", fontsize=8.2, color=MUTED, rotation=90)
    counts = np.array([[44, 32], [6, 8]])
    kinds = [[1, 2], [3, 0]]
    for i in range(2):
        for j in range(2):
            kind = kinds[i][j]; color, _marker, _ = styles[kind]
            cross.add_patch(FancyBboxPatch((j+.04, i+.06), .91, .88,
                                          boxstyle="round,pad=0.012,rounding_size=.06",
                                          linewidth=.65, edgecolor=color, facecolor=matplotlib.colors.to_rgba(color,.10)))
            cross.text(j+.50, i+.44, str(counts[i,j]), ha="center", va="center",
                       fontsize=21, weight="bold", color=color if kind else MUTED)
            cross.text(j+.50, i+.72, f"{100*counts[i,j]/90:.1f}%", ha="center", va="center", fontsize=8.4, color=MUTED)
    fig.text(.785, .227, "44 / 76 条TE候选同时达阈值", ha="center", fontsize=8.5, color=INK)
    handles = [Line2D([], [], linestyle="none", marker=styles[k][1], ms=5,
                      mfc=styles[k][0] if k else "white", mec=styles[k][0],
                      label=styles[k][2]) for k in [1,2,3,0]]
    fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(.5,.050), ncol=4,
               fontsize=8, frameon=False, columnspacing=1.05, handletextpad=.3)
    fig.text(.5,.030,"历史未校正计数；对角线10个自回归对排除",ha="center",fontsize=8,color=MUTED)
    export(fig, "fig5_4_pcmci_validation_network", {
        "sources": {str(path.relative_to(ROOT)): digest(path)}, "nodes": ids,
        "matrix": matrix.tolist(), "cross_tab": counts.tolist(), "counts": [44,32,6,8],
        "excluded_self_pairs": 10, "family": "90 ordered off-diagonal pairs",
        "threshold": "Historical nominal alpha=.05; no multiple-test correction; not a new validation run"})


def draw_te_enlarged():
    te, rel, pairs, directed, _ = te_source.load_and_validate()
    fig, axes = plt.subplots(3, 1, figsize=(6.1, 6.15), sharex=True, sharey=True)
    fig.subplots_adjust(left=.145, right=.965, bottom=.113, top=.905, hspace=.45)
    fig.text(.145,.966,"45个节点对 · 双向TE共90个观测",fontsize=9,color=MUTED)
    summary = {}
    for panel, (ax, (key,label,color)) in enumerate(zip(axes, te_source.RELATIONS)):
        x = np.asarray([rel[key][i,j] for i,j in directed])
        y = np.asarray([te[i,j] for i,j in directed])
        rho = float(spearmanr(x,y).statistic)
        for i,j in pairs:
            w = rel[key][i,j]
            ax.plot([w,w],[te[i,j],te[j,i]],color="#A9B8C1",alpha=.55,lw=.7,zorder=1)
        for direction, marker in [(0,"o"),(1,"^")]:
            ax.scatter(x[direction::2],y[direction::2],s=27,marker=marker,color=color,
                       alpha=.85,edgecolor="white",linewidth=.4,zorder=3)
        ax.text(0,1.12,f"{chr(65+panel)}  {label}",transform=ax.transAxes,fontsize=10,weight="bold",color=color)
        ax.text(1,1.12,f"Spearman ρ = {rho:.2f}",transform=ax.transAxes,ha="right",fontsize=9)
        ax.set_ylabel("TE（nats）",labelpad=7)
        ax.set_yticks([0,.002,.004,.006])
        ax.set_ylim(0, .0068); ax.set_xlim(-.006,.205)
        ax.set_xticks([0,.05,.10,.15,.20])
        clean(ax,axis="both")
        summary[key] = {"n":90,"rho":rho,"weights":x.tolist(),"te":y.tolist()}
    axes[-1].set_xlabel("对应 LRE 关系矩阵权值",labelpad=8)
    handles = [Line2D([],[],marker=m,ls="none",color=MUTED,ms=4.7,label=l) for m,l in
               [("o","i → j（i < j）"),("^","j → i（i < j）")]]
    fig.legend(handles=handles,loc="lower center",bbox_to_anchor=(.54,.008),ncol=2,frameon=False,fontsize=8.7)
    export(fig,"fig5_3_te_vs_relations",{
        "sources":{str(p.relative_to(ROOT)):digest(p) for p in [te_source.TE_PATH,te_source.REL_PATH,te_source.RUN_MANIFEST,te_source.BUNDLE_PATH]},
        "observations_excluded":0,"pairs":45,"directed_observations":90,"summaries":summary,
        "layout":"three full-width rows; no jitter or filtering; shared scales"})


if __name__ == "__main__":
    frozen = OUT / "fig3_4_lre_construction_imagegen.png"
    graph_hash = digest(frozen)
    draw_jpl()
    draw_current()
    draw_pcmci()
    draw_te_enlarged()
    assert digest(frozen) == graph_hash, "The audit-only architecture figure changed"
    manifest = ROOT / "outputs/analysis/figure-revision-20261111"
    manifest.mkdir(parents=True, exist_ok=True)
    (manifest/"source-and-render-manifest.json").write_text(json.dumps({
        "backend":"python", "no_new_model_evaluation":True,
        "unmodified_graph3_4_sha256": graph_hash, "figures":SOURCES,
        "output_sha256":{f.name:digest(f) for stem in SOURCES for f in [OUT/(stem+".svg"),OUT/(stem+".png")]}
    },ensure_ascii=False,indent=2))
    print("Exported four SVG/PNG figure pairs; graph 3-4 unchanged.")
