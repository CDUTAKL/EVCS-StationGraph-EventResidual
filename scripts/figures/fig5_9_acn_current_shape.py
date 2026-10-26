"""Reproduce a bounded ACN current-shape comparison figure.

This figure compares normalized measured-current shares with the uniform-share
proxy used in the thesis target construction. It does not compare model
forecasts with metered kWh or power.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
FIG_DIR = ROOT / "outputs/figures"
EVIDENCE_DIR = ROOT / "docs/thesis/revision-20261025-practice"
FIGURE_ID = "fig5_9_acn_current_shape"
REPLAY_PATH = EVIDENCE_DIR / "acn-current-shape-replay.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load_evidence() -> tuple[dict[str, dict], dict]:
    """Read the de-identified frozen summary, not session-level source data."""
    with REPLAY_PATH.open(encoding="utf-8") as stream:
        replay = json.load(stream)
    sample = replay.get("sample", {})
    if replay.get("record_id") != "ACN-CURRENT-SHAPE-REPLAY-20261025":
        raise ValueError("Unexpected replay record")
    if (sample.get("selected"), sample.get("eligible"), sample.get("failed_quality_or_unavailable")) != (10, 8, 2):
        raise ValueError("Frozen sample counts changed")
    if sample.get("representative") is not False:
        raise ValueError("The convenience sample must not be marked representative")
    if replay.get("measure") != "Normalized integral of charging current (A); not power or kWh.":
        raise ValueError("Measured quantity metadata changed")
    if not any("Voltage and power were absent" in item for item in replay.get("limitations", [])):
        raise ValueError("Metered-power limitation is missing")

    results = replay.get("statistics", {}).get("per_node", {})
    if set(results) != set(sample.get("nodes", [])) or len(results) != 8:
        raise ValueError("Frozen per-node summary does not match eligible nodes")
    for node, record in results.items():
        if int(record.get("bins", 0)) < 1:
            raise ValueError(f"Invalid bin count: {node}")
        values = np.asarray([record.get("tv_distance"), record.get("peak_share_ratio")], dtype=float)
        if not np.isfinite(values).all() or not 0 <= values[0] <= 1 or values[1] <= 0:
            raise ValueError(f"Invalid frozen summary values: {node}")
    stats = replay["statistics"]
    tv = np.asarray([record["tv_distance"] for record in results.values()])
    peak = np.asarray([record["peak_share_ratio"] for record in results.values()])
    checks = {
        "tv_distance_min": float(tv.min()),
        "tv_distance_median": float(np.median(tv)),
        "tv_distance_max": float(tv.max()),
        "peak_share_ratio_min": float(peak.min()),
        "peak_share_ratio_median": float(np.median(peak)),
        "peak_share_ratio_max": float(peak.max()),
    }
    for name, value in checks.items():
        if not np.isclose(value, float(stats[name]), atol=1e-12, rtol=0):
            raise ValueError(f"Frozen summary aggregate mismatch: {name}")
    return results, replay


def render(results: dict[str, dict]) -> tuple[Path, Path]:
    mpl.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["STHeiti", "Arial Unicode MS", "Arial", "Helvetica", "DejaVu Sans"],
        "font.size": 8,
        "axes.labelsize": 8,
        "axes.titlesize": 9,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "axes.spines.right": False,
        "axes.spines.top": False,
        "axes.linewidth": 0.8,
        "legend.frameon": False,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
    })
    nodes = list(results)
    x = np.arange(len(nodes))
    tv = np.asarray([results[node]["tv_distance"] for node in nodes])
    peak = np.asarray([results[node]["peak_share_ratio"] for node in nodes])
    blue = "#496A82"
    amber = "#C68B45"
    gray = "#87939D"

    fig, axes = plt.subplots(1, 2, figsize=(7.25, 3.05), constrained_layout=True)
    ax = axes[0]
    ax.scatter(x, tv, s=34, color=blue, edgecolor="white", linewidth=0.6, zorder=3)
    median_tv = float(np.median(tv))
    ax.axhline(median_tv, color=gray, linewidth=1, linestyle=(0, (3, 2)), zorder=1)
    ax.set_title("A  形态差异", loc="left", fontweight="normal")
    ax.set_ylabel("总变差距离")
    ax.set_ylim(0, max(0.66, float(tv.max()) * 1.12))
    ax.text(0.98, 0.96, f"n = {len(nodes)}；中位数 = {median_tv:.3f}",
            transform=ax.transAxes, ha="right", va="top", fontsize=7, color="#34495E")

    ax = axes[1]
    ax.scatter(x, peak, s=34, color=amber, edgecolor="white", linewidth=0.6, zorder=3)
    median_peak = float(np.median(peak))
    ax.axhline(1.0, color=gray, linewidth=1, linestyle=(0, (1, 2)), zorder=1)
    ax.axhline(median_peak, color=gray, linewidth=1, linestyle=(0, (3, 2)), zorder=1)
    ax.set_title("B  峰值片集中度", loc="left", fontweight="normal")
    ax.set_ylabel("实测电流份额 / 均匀份额")
    ax.set_ylim(0.75, max(4.8, float(peak.max()) * 1.12))
    ax.text(0.98, 0.96, f"n = {len(nodes)}；中位数 = {median_peak:.2f}×",
            transform=ax.transAxes, ha="right", va="top", fontsize=7, color="#34495E")

    for ax in axes:
        ax.set_xticks(x, nodes, rotation=35, ha="right")
        ax.grid(axis="y", color="#E7EBEF", linewidth=0.6)
        ax.set_axisbelow(True)
        ax.set_xlabel("预定Caltech节点样本")
        ax.tick_params(length=3, width=0.7, color="#77838C")
    fig.text(0.5, -0.015,
             "历史探索性电流形态样本；非模型预测或实测电量验证",
             ha="center", va="top", fontsize=7, color="#56616A")

    FIG_DIR.mkdir(parents=True, exist_ok=True)
    svg = FIG_DIR / f"{FIGURE_ID}.svg"
    pdf = FIG_DIR / f"{FIGURE_ID}.pdf"
    png = FIG_DIR / f"{FIGURE_ID}.png"
    fig.savefig(svg, bbox_inches="tight")
    fig.savefig(pdf, bbox_inches="tight")
    fig.savefig(png, dpi=1200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return svg, pdf, png


def main() -> None:
    results, replay = load_evidence()
    svg, pdf, png = render(results)
    source = {
        "figure": "图5-9",
        "figure_id": FIGURE_ID,
        "evidence_id": "DATA-024-CURRENT-PROBE",
        "inputs": {
            "frozen_deidentified_replay": {
                "path": REPLAY_PATH.relative_to(ROOT).as_posix(),
                "sha256": sha256(REPLAY_PATH),
            }
        },
        "script": {"path": "scripts/figures/fig5_9_acn_current_shape.py",
                   "sha256": sha256(Path(__file__))},
        "replay_record": {"path": "docs/thesis/revision-20261025-practice/acn-current-shape-replay.json",
                          "sha256": sha256(REPLAY_PATH)},
        "source_statements": {
            "core_conclusion": "Within the eight eligible convenience-sample sessions, measured-current shape differs from the equal-share proxy; this is not model validation.",
            "archetype": "quantitative grid",
            "panel_map": {"A": "per-session total variation distance", "B": "per-session peak-bin share ratio"},
            "statistics": "Eight individual sessions; descriptive medians and ranges; no inferential interval or significance test.",
            "privacy": "The figure is rebuilt from a frozen de-identified per-node summary; no session-level rows or identifiers are needed.",
        },
        "outputs": {p.name: {"sha256": sha256(p), "bytes": p.stat().st_size,
                              "pixel_size": list(Image.open(p).size) if p.suffix == ".png" else None,
                              "dpi": 1200 if p.suffix == ".png" else None}
                    for p in (svg, pdf, png)},
    }
    source_path = FIG_DIR / f"{FIGURE_ID}_source.json"
    source_path.write_text(json.dumps(source, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"replay": str(REPLAY_PATH), "figure": [str(svg), str(pdf), str(png)],
                      "source": str(source_path), "eligible": len(results),
                      "tv_range": [replay["statistics"]["tv_distance_min"], replay["statistics"]["tv_distance_max"]],
                      "peak_ratio_range": [replay["statistics"]["peak_share_ratio_min"], replay["statistics"]["peak_share_ratio_max"]]},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
