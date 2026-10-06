#!/usr/bin/env python3
"""Publication result figures: relationship weights and exploratory TE structure.

Contract: quantitative grid, Python backend, thesis width 146.6 mm.
4-2 describes the layer-level allocation of three relations, not causality.
All 18 checkpoint weights are retained; center=mean, spread=sample SD, n=3 seeds.
5-2 retains the established top-15 network view and all 76 candidates in source
data. Coverage counts refer to all 45 undirected node pairs, not 15 shown edges.
No observations or analytical thresholds are changed for visual reasons.
"""
from __future__ import annotations

import csv
import hashlib
import itertools
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch
import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
FIG = ROOT / "outputs/figures"
STATIC = ROOT / "outputs/night_run/20260730-171821/SG-EXP-003/20260730-171821"
TE_SOURCE = ROOT / "outputs/analysis/transfer_entropy/transfer_entropy_summary.json"
BLUE = "#2C5F8A"
WARM = "#A89A88"
INK = "#343E45"
PALE = "#E8EDF0"
GRAY = "#879399"


def style():
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["PingFang SC", "Arial Unicode MS", "DejaVu Sans"],
        "font.size": 8.0, "axes.labelsize": 8.5,
        "axes.unicode_minus": False, "svg.fonttype": "none", "pdf.fonttype": 42,
        "text.color": INK, "axes.labelcolor": INK, "axes.edgecolor": INK,
        "xtick.color": INK, "ytick.color": INK,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.linewidth": 0.65, "legend.frameon": False,
    })


def export(fig, stem, sources, notes):
    kw = {"bbox_inches": "tight", "pad_inches": 0.045, "facecolor": "white"}
    fig.savefig(FIG / f"{stem}.svg", **kw)
    fig.savefig(FIG / f"{stem}.pdf", **kw)
    fig.savefig(FIG / f"{stem}.png", dpi=1200, **kw)
    fig.savefig(FIG / f"{stem}.tiff", dpi=600,
                pil_kwargs={"compression": "tiff_lzw"}, **kw)
    data = {
        "backend": "Python / matplotlib", "archetype": "quantitative grid",
        "script": str(Path(__file__).relative_to(ROOT)),
        "sources": [{"path": str(p.relative_to(ROOT)),
                     "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in sources],
        "outputs": {fmt: hashlib.sha256((FIG / f"{stem}.{fmt}").read_bytes()).hexdigest()
                    for fmt in ["png", "svg", "pdf", "tiff"]},
        **notes,
    }
    (FIG / f"{stem}_source.json").write_text(json.dumps(data, ensure_ascii=False, indent=2)+"\n")
    plt.close(fig)


def beta_profile():
    seeds = [2024, 2025, 2026]
    paths = [STATIC / f"seed-{s}/model.pt" for s in seeds]
    weights = []
    for p in paths:
        payload = torch.load(p, map_location="cpu", weights_only=True)
        state = payload.get("model_state", payload)
        layers = []
        for layer in ["gcn1", "gcn2"]:
            v = state[f"relation_weights_{layer}"].detach().cpu().numpy()
            assert v.shape == (3,) and np.isfinite(v).all()
            e = np.exp(v-v.max())
            layers.append(e/e.sum())
        weights.append(layers)
    values = np.asarray(weights, dtype=float)
    assert values.shape == (3, 2, 3)
    assert np.allclose(values.sum(axis=2), 1)
    names = ["负荷耦合", "行为共现", "轮廓相似"]
    with (FIG / "fig4_2_beta_profile_source.csv").open("w", newline="") as out:
        writer = csv.writer(out)
        writer.writerow(["seed", "layer", "relation", "softmax_weight"])
        for si, seed in enumerate(seeds):
            for li, ri in itertools.product(range(2), range(3)):
                writer.writerow([seed, li+1, names[ri], values[si, li, ri]])
    fig, ax = plt.subplots(figsize=(5.77, 3.05))
    fig.subplots_adjust(left=0.13, right=0.98, bottom=0.17, top=0.80)
    ax.axhline(1/3, color=GRAY, lw=0.8, ls=(0, (4, 3)), zorder=1)
    ax.text(2.42, 1/3+0.0015, "等权 1/3", fontsize=7, ha="right", va="bottom", color=GRAY)
    means = values.mean(axis=0)
    sds = values.std(axis=0, ddof=1)
    for li, (offset, color, marker) in enumerate(zip([-0.10, 0.10], [BLUE, WARM], ["o", "D"])):
        x = np.arange(3)+offset
        ax.plot(x, means[li], color=color, linewidth=1.65,
                linestyle="solid" if li == 0 else (0, (5, 2.5)), zorder=2)
        for si, jitter in enumerate([-0.047, 0, 0.047]):
            ax.scatter(x+jitter, values[si, li], marker=marker, s=18, facecolor="white",
                       edgecolor=color, linewidth=0.8, alpha=0.9, zorder=3)
        ax.errorbar(x, means[li], yerr=sds[li], fmt=marker, color=color,
                    markerfacecolor=color, markeredgecolor="white", markeredgewidth=0.7,
                    markersize=6.2, elinewidth=1.1, capsize=3, capthick=1, zorder=4)
        for ri in range(3):
            # Mean labels clear both seed observations and the SD endpoints.
            top = max(values[:, li, ri].max(), means[li, ri]+sds[li, ri])
            below = li == 1 and ri == 1
            bottom = min(values[:, li, ri].min(), means[li, ri]-sds[li, ri])
            ax.text(x[ri], bottom-0.005 if below else top+0.005,
                    f"{means[li, ri]:.3f}", fontsize=8,
                    color=color, ha="center", va="top" if below else "bottom",
                    bbox={"facecolor": "white", "edgecolor": "none", "pad": 0.8}, zorder=5)
    handles = [Line2D([], [], marker=m, color=c,
                      linestyle="solid" if li == 0 else (0, (5, 2.5)), linewidth=1.65, markersize=6,
                      label=f"第{li+1}层") for li, (m,c) in enumerate(zip(["o","D"],[BLUE,WARM]))]
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.115, 0.995),
               ncol=2, handletextpad=0.4, columnspacing=1.2)
    fig.text(0.98, 0.945, "空心：单种子　实心：均值 ± SD（n = 3）",
             ha="right", fontsize=7.2, color=INK)
    ax.set_xlim(-0.43, 2.43)
    ax.set_ylim(0.23, 0.425)
    ax.set_yticks([0.25, 0.30, 0.35, 0.40])
    ax.set_xticks(range(3), names)
    ax.set_ylabel("关系级权重 β")
    ax.tick_params(length=3, width=0.65)
    ax.grid(axis="y", color=PALE, linewidth=0.5, zorder=0)
    export(fig, "fig4_2_beta_profile", paths, {
        "claim": "第一层侧重行为共现，第二层的三关系分配更接近。",
        "replicates": seeds, "n": 3, "center": "mean", "spread": "sample SD (ddof=1)",
        "observations_plotted": 18, "means": means.tolist(), "sd": sds.tolist(),
        "layout": "layer mean profiles connected across fixed relation categories; solid blue / dashed warm gray",
        "exclusions": [], "interpretation": "observational parameter profile; not causal effects",
    })


def circular_order(nodes, edges):
    """Deterministic layout-only swaps reduce chord crossings; no edge filtering."""
    pairs = sorted({tuple(sorted([e["source"], e["target"]])) for e in edges})
    def score(order):
        idx = {n:i for i,n in enumerate(order)}
        crossing = 0
        for (a,b),(c,d) in itertools.combinations(pairs, 2):
            if len({a,b,c,d}) != 4:
                continue
            i,j = sorted([idx[a],idx[b]])
            crossing += ((i < idx[c] < j) != (i < idx[d] < j))
        length = sum(min(abs(idx[a]-idx[b]), len(nodes)-abs(idx[a]-idx[b])) for a,b in pairs)
        return crossing*100+length
    order = list(nodes)
    while True:
        current = score(order)
        best = order
        for i,j in itertools.combinations(range(1,len(order)),2):
            candidate = list(order)
            candidate[i],candidate[j] = candidate[j],candidate[i]
            if score(candidate) < score(best):
                best = candidate
        if score(best) >= current:
            return order, current
        order = best


def te_structure():
    te = json.loads(TE_SOURCE.read_text())
    edges = te["significant_edges"]
    nodes = sorted({e["source"] for e in edges} | {e["target"] for e in edges})
    drawn = sorted(edges, key=lambda e:e["te"])[-15:]
    assert len(edges) == 76 and len(drawn) == 15 and len(nodes) == 10
    order, score = circular_order(nodes, drawn)
    ov = te["overlap"]
    counts = [ov["undirected_pairs"], ov["covered_by_any_statistical_graph"], ov["exclusive_to_causal"]]
    assert counts == [45,33,12] and counts[1]+counts[2] == counts[0]
    with (FIG / "fig5_2_transfer_entropy_source.csv").open("w", newline="") as out:
        w = csv.writer(out)
        w.writerow(["source", "target", "te", "lag", "p_value", "shown_top15"])
        for e in edges:
            w.writerow([e[k] for k in ["source","target","te","lag","p_value"]]+[e in drawn])
    fig = plt.figure(figsize=(5.77,3.65))
    ax = fig.add_axes([0.015,0.22,0.54,0.72])
    bar = fig.add_axes([0.65,0.37,0.33,0.46])
    fig.text(0.025,0.945,"a  TE方向性候选", weight="bold", fontsize=9)
    fig.text(0.57,0.945,"b  统计关系覆盖", weight="bold", fontsize=9)
    pos = {n:np.array([np.cos(np.pi/2-2*np.pi*i/10),np.sin(np.pi/2-2*np.pi*i/10)]) for i,n in enumerate(order)}
    low, high = min(e["te"] for e in drawn), max(e["te"] for e in drawn)
    for e in drawn:
        s,t = pos[e["source"]],pos[e["target"]]
        unit = (t-s)/np.linalg.norm(t-s)
        start,end = s+unit*0.15,t-unit*0.15
        rel = (e["te"]-low)/(high-low)
        arrow = FancyArrowPatch(start,end,arrowstyle="-|>",mutation_scale=7,
                  color=BLUE, linewidth=0.65+1.45*rel, alpha=0.45+0.4*rel,
                  connectionstyle="arc3,rad=0.13", zorder=2)
        ax.add_patch(arrow)
    for n in order:
        x,y = pos[n]
        ax.scatter(x,y,s=230,facecolor="white",edgecolor=BLUE,linewidth=1.0,zorder=4)
        ax.text(x,y,n.split("-")[1],ha="center",va="center",fontsize=7,zorder=5)
    ax.set(xlim=(-1.2,1.2),ylim=(-1.2,1.2),aspect="equal")
    ax.axis("off")
    fig.text(0.285,0.21,"最强15条 / 全部76条有向候选边",ha="center",fontsize=7.2)
    key = fig.add_axes([0.07,0.09,0.43,0.07])
    for x,v in zip([0.16,0.49,0.82],[low,(low+high)/2,high]):
        rel = (v-low)/(high-low)
        key.plot([x-0.1,x+0.1],[0.75,0.75],color=BLUE,lw=0.65+1.45*rel,alpha=0.45+0.4*rel)
        key.text(x,0.18,f"{v*1000:.2f}",fontsize=7,ha="center",va="center")
    key.set(xlim=(0,1),ylim=(0,1)); key.axis("off")
    fig.text(0.285,0.052,r"线宽 / 深浅：TE（$\times 10^{-3}$）",ha="center",fontsize=7,color=GRAY)
    bar.barh([2,1,0],counts,height=0.48,color=[GRAY,BLUE,WARM],edgecolor="white",lw=0.6,zorder=3)
    bar.set_yticks([2,1,0],["候选总数","统计图\n覆盖","统计图\n未覆盖"],fontsize=7.5)
    bar.set_xlim(0,52); bar.set_ylim(-0.6,2.6)
    bar.set_xticks([0,15,30,45])
    bar.set_xlabel("无向节点对数",fontsize=8)
    bar.spines["left"].set_visible(False)
    bar.tick_params(axis="y",length=0,pad=5)
    bar.tick_params(axis="x",length=3,labelsize=7)
    bar.grid(axis="x",color=PALE,lw=0.5,zorder=0)
    for y,v in zip([2,1,0],counts):
        bar.text(v+1.3,y,str(v),ha="left",va="center",fontsize=8.5,color=INK)
    fig.text(0.79,0.20,"33 + 12 = 45 对",ha="center",fontsize=8,color=INK)
    fig.text(0.79,0.125,"覆盖率 73.3%",ha="center",fontsize=8,color=BLUE)
    export(fig,"fig5_2_transfer_entropy",[TE_SOURCE],{
        "claim": "TE候选结构与统计关系部分重合，同时包含未覆盖的节点对。",
        "all_directed_candidates":len(edges), "shown_directed_candidates":len(drawn),
        "display_selection":"highest TE 15; identical selection to previous figure",
        "other_directed_candidates_not_drawn":61,
        "all_candidates_retained_in_source_csv":True,
        "circular_node_order":order, "layout_score":score,
        "layout": "enlarged network and wider coverage panel with reduced horizontal gap",
        "shown_edges":drawn, "coverage_counts":counts,
        "coverage_unit":"undirected node pair; complete set of candidates",
        "statistics":"100 circular-shift permutations; no multiplicity correction; no error bars",
        "interpretation":"directional statistical candidates, not physical causality",
    })


if __name__ == "__main__":
    style()
    beta_profile()
    te_structure()
