#!/usr/bin/env python3
"""Refresh the two quantitative figures 2-5 and 3-5 from their frozen sources.

Run from the repository root with the Python backend used by the figure project.
No smoothing, aggregation, or resampling is applied to the plotted observations.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Patch
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
FIG = ROOT / "outputs/figures"
BUNDLE = ROOT / "data/processed/SG-DATA-005-primary-tensor.npz"
RELATIONS = ROOT / "outputs/experiments/SG-EXP-004/20260731-102456/relation_matrices.npz"
BLUE = "#2C5F8A"
BLUE_DARK = "#234A66"
BLUE_MID = "#8EABC0"
BLUE_PALE = "#EAF0F3"
INK = "#343E45"
GRAY = "#858D92"
GRAY_LIGHT = "#D8DEE2"
WARM_PALE = "#F3E9DF"


def configure_style() -> None:
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["PingFang SC", "Arial Unicode MS", "SimHei", "DejaVu Sans"],
        "axes.unicode_minus": False,
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "axes.edgecolor": INK,
        "axes.labelcolor": INK,
        "xtick.color": INK,
        "ytick.color": INK,
        "text.color": INK,
        "savefig.facecolor": "white",
    })


def export(fig: plt.Figure, stem: str) -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / f"{stem}.svg", bbox_inches="tight", pad_inches=0.025,
                facecolor="white")
    fig.savefig(FIG / f"{stem}.pdf", bbox_inches="tight", pad_inches=0.025,
                facecolor="white")
    fig.savefig(FIG / f"{stem}.png", dpi=1200, bbox_inches="tight", pad_inches=0.025,
                facecolor="white")
    fig.savefig(FIG / f"{stem}.tiff", dpi=600, bbox_inches="tight", pad_inches=0.025,
                facecolor="white", pil_kwargs={"compression": "tiff_lzw"})
    svg = FIG / f"{stem}.svg"
    svg.write_text("\n".join(x.rstrip() for x in svg.read_text(encoding="utf-8").splitlines()) + "\n",
                   encoding="utf-8")


def _runs(mask: np.ndarray) -> list[tuple[int, int]]:
    """Return half-open contiguous true runs."""
    padded = np.r_[False, mask, False].astype(np.int8)
    starts = np.flatnonzero(np.diff(padded) == 1)
    stops = np.flatnonzero(np.diff(padded) == -1)
    return list(zip(starts.tolist(), stops.tolist()))


def fig2_5_weekly_curves() -> None:
    with np.load(BUNDLE, allow_pickle=False) as d:
        timestamps = d["timestamps_ns"]
        node_ids = d["node_ids"].astype(str).tolist()
        targets = d["targets"]

    start = 96 * 30
    end = start + 96 * 7
    stamps = timestamps[start:end]
    nodes = ["CA-303", "CA-489", "CA-311"]
    series = [targets[start:end, node_ids.index(name)] for name in nodes]
    tz = ZoneInfo("America/Los_Angeles")
    local = [datetime.fromtimestamp(int(ns) / 1e9, tz=timezone.utc).astimezone(tz)
             for ns in stamps]
    night = np.array([t.hour < 6 for t in local], dtype=bool)
    weekend = np.array([t.weekday() >= 5 for t in local], dtype=bool)
    edges = np.arange(96 * 7 + 1, dtype=float) / 96.0

    fig, ax = plt.subplots(figsize=(7.2, 3.55))
    for a, b in _runs(night):
        ax.axvspan(edges[a], edges[b], color="#D6DDE2", alpha=0.32, lw=0, zorder=0)
    for a, b in _runs(weekend):
        ax.axvspan(edges[a], edges[b], color="#E9DED4", alpha=0.36, lw=0, zorder=0)
    # Preserve the common-axis comparison. Color and line pattern distinguish
    # observations without smoothing or shifting any series.
    for name, values, color, pattern in zip(
            nodes, series, [BLUE, "#A89A88", "#606D76"],
            ["solid", (0, (5, 2.5)), (0, (5, 2, 1, 2))]):
        ax.stairs(values, edges, color=color, linewidth=1.25,
                  linestyle=pattern, label=name, baseline=None, zorder=3)
    ax.set_xlim(0, 7)
    ax.set_ylim(-0.025, 1.56)
    ax.set_yticks(np.arange(0, 1.51, 0.3))
    ax.set_xticks(range(8))
    ax.set_ylabel("负荷（kWh/15 min）", fontsize=10, labelpad=5)
    ax.set_xlabel("距首个样本的时间（天）", fontsize=10, labelpad=5)
    ax.grid(axis="y", color="#E1E6E9", linewidth=0.45, zorder=0)
    ax.spines[["top", "right"]].set_visible(False)
    for side in ["left", "bottom"]:
        ax.spines[side].set_linewidth(0.7)
    ax.tick_params(labelsize=9, length=3, width=0.65)
    curve_legend = ax.legend(loc="lower left", bbox_to_anchor=(0, 1.015),
                             ncol=3, frameon=False, fontsize=9,
                             handlelength=2.6, columnspacing=1.3, borderaxespad=0)
    ax.add_artist(curve_legend)
    ax.legend(handles=[Patch(facecolor="#D6DDE2", alpha=0.5, label="当地00–06时"),
                       Patch(facecolor="#E9DED4", alpha=0.6, label="当地周末")],
              loc="lower right", bbox_to_anchor=(1, 1.015), ncol=2,
              frameon=False, fontsize=8, handlelength=1.1,
              columnspacing=0.8, handletextpad=0.4, borderaxespad=0)
    fig.subplots_adjust(left=0.11, right=0.985, top=0.88, bottom=0.17)
    export(fig, "fig2_5_weekly_curves")
    plt.close(fig)


def fig3_5_lre_matrices() -> None:
    with np.load(BUNDLE, allow_pickle=False) as d:
        node_ids = d["node_ids"].astype(str).tolist()
    with np.load(RELATIONS, allow_pickle=False) as d:
        relations = [("load", "负荷耦合", "|Pearson|"),
                     ("event", "行为共现", "cosine"),
                     ("pattern", "轮廓相似", "指数核")]
        mats = [np.asarray(d[key], dtype=float) for key, _, _ in relations]

    training_manifest = json.loads((RELATIONS.parent / "manifest.json").read_text())
    bundle_hash = hashlib.sha256(BUNDLE.read_bytes()).hexdigest()
    if bundle_hash != training_manifest["dataset_sha256"]:
        raise ValueError("Current node labels do not come from the frozen training tensor")
    if len(set(node_ids)) != len(node_ids) or any(
            m.shape != (len(node_ids), len(node_ids)) for m in mats):
        raise ValueError("Relation shape or unique node-label count is inconsistent")

    # Preserve one common node order and one common scale for direct visual comparison.
    vmax = max(float(np.nanmax(x)) for x in mats)
    cmap = LinearSegmentedColormap.from_list(
        "paper_blue_gray", ["#F8FBFD", "#E5EFF6", "#BDD5E5", "#83B0CB",
                            "#4E87AA", BLUE, "#163D60"])
    fig = plt.figure(figsize=(7.2, 3.2))
    axes = [fig.add_axes([x, 0.25, 0.20, 0.45]) for x in [0.09, 0.385, 0.68]]
    ims = []
    labels = node_ids

    for ax, mat, (_, title, method) in zip(axes, mats, relations):
        im = ax.imshow(mat, cmap=cmap, vmin=0, vmax=vmax, interpolation="nearest",
                       aspect="equal")
        ims.append(im)
        ax.set_title(f"{title}\n{method}", fontsize=10, fontweight="normal",
                     color=INK, pad=7, linespacing=1.15)
        # A rotated right-anchored label is visually shifted away from its
        # column center. Vertical, center-anchored IDs make the mapping exact.
        ax.set_xticks(np.arange(len(labels)), labels, rotation=90,
                      ha="center", va="top", rotation_mode="default")
        ax.set_yticks(np.arange(len(labels)), labels)
        for tick in ax.get_xticklabels() + ax.get_yticklabels():
            tick.set_fontfamily("DejaVu Sans Mono")
        for tick in ax.get_yticklabels():
            tick.set_verticalalignment("center")
            tick.set_horizontalalignment("right")
        ax.tick_params(axis="both", labelsize=8.2, length=2.2, width=0.6, pad=2)
        ax.set_xticks(np.arange(-0.5, len(labels), 1), minor=True)
        ax.set_yticks(np.arange(-0.5, len(labels), 1), minor=True)
        ax.grid(which="minor", color="white", linewidth=0.55)
        ax.tick_params(which="minor", bottom=False, left=False)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        ax.spines["left"].set_color(GRAY)
        ax.spines["bottom"].set_color(GRAY)
        ax.spines["left"].set_linewidth(0.7)
        ax.spines["bottom"].set_linewidth(0.7)

    # Reserve a separate column for the shared colorbar so it cannot overlap
    # the rightmost heatmap or its node labels at thesis-page width.
    cax = fig.add_axes([0.918, 0.25, 0.018, 0.45])
    cbar = fig.colorbar(ims[-1], cax=cax,
                        ticks=[0.0, 0.2, 0.4, 0.6, round(vmax, 2)])
    cbar.set_label("关系权重（统一色阶）", fontsize=9, labelpad=5)
    cbar.ax.tick_params(labelsize=8.2, length=2.5, width=0.6)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    checks = []
    panel_bounds = [ax.get_window_extent(renderer).bounds for ax in axes]
    if not np.allclose(np.array(panel_bounds)[:, 1:], panel_bounds[0][1:], atol=1e-7):
        raise ValueError("Heatmap panel bottoms, widths or heights are misaligned")
    for ax, mat, (key, _, _) in zip(axes, mats, relations):
        if not np.array_equal(np.asarray(ax.images[0].get_array()), mat):
            raise ValueError("Plotted matrix changed from its frozen source")
        if ax.get_xticklabels()[0].get_text() != labels[0]:
            raise ValueError("First column label does not match source node order")
        for i, (xt, yt) in enumerate(zip(ax.get_xticklabels(), ax.get_yticklabels())):
            cell_x, cell_y = ax.transData.transform((i, i))
            xb, yb = xt.get_window_extent(renderer), yt.get_window_extent(renderer)
            xerror = abs((xb.x0 + xb.x1) / 2 - cell_x)
            yerror = abs((yb.y0 + yb.y1) / 2 - cell_y)
            if xt.get_text() != labels[i] or yt.get_text() != labels[i]:
                raise ValueError(f"{key}: node order mismatch at index {i}")
            if xerror > 0.05 or yerror > 0.05:
                raise ValueError(f"{key}/{labels[i]}: label center is misaligned")
            checks.append({"matrix": key, "node": labels[i], "index": i,
                           "column_label_error_px": xerror,
                           "row_label_error_px": yerror})
    (FIG / "fig3_5_lre_matrices_alignment_audit.json").write_text(
        json.dumps({"node_order": labels, "training_dataset_sha256": bundle_hash,
                    "frozen_source_match": True, "identical_panel_geometry": True,
                    "label_checks": checks}, ensure_ascii=False, indent=2) + "\n")
    export(fig, "fig3_5_lre_matrices")
    plt.close(fig)


def main() -> None:
    configure_style()
    fig2_5_weekly_curves()
    fig3_5_lre_matrices()
    print("Updated fig2_5_weekly_curves and fig3_5_lre_matrices from frozen data sources.")


if __name__ == "__main__":
    main()
