"""SG-EXP-023: audited frozen predictions, independent calibration, no training.

Run: PYTHONPATH=src:scripts .venv/bin/python scripts/analyze_independent_calibration.py
All scientific outputs go to a new directory; source runs are strictly read-only.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from fractions import Fraction
import json
import math
from pathlib import Path
import platform

import numpy as np
import pandas as pd

from analyze_demand_warning import sha256_file, write_json, write_csv
from evcs_station_graph.eventtime.data import FrozenData, SEGMENTS

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "configs/analysis/SG-EXP-023-independent-calibration.json"


def order_quantile(values, alpha):
    """Conservative split-conformal rank, without interpolation or rank clamping."""
    scores = np.asarray(values, dtype=np.float64).ravel()
    if not 0 < alpha < 1 or not scores.size or not np.isfinite(scores).all():
        raise ValueError("Invalid alpha or calibration scores")
    if np.any(scores < 0):
        raise ValueError("Absolute residuals must be nonnegative")
    rank = math.ceil(Fraction(scores.size + 1) * (1 - Fraction(str(alpha))))
    q = float(np.partition(scores, rank - 1)[rank - 1]) if rank <= scores.size else math.inf
    return q, int(scores.size), rank


def fit_halfwidths(residuals, triggers, alpha):
    """Only calibration residuals and frozen origin behavior triggers enter fit."""
    e = np.asarray(residuals, dtype=np.float64)
    t = np.asarray(triggers, dtype=bool)
    if e.ndim != 3 or e.shape != t.shape:
        raise ValueError("Expected equal [origins,horizons,nodes] arrays")
    node, stable, ranks = [], [], []
    for n in range(e.shape[2]):
        q, count, rank = order_quantile(e[:, :, n], alpha)
        node.append(q)
        ranks.append(dict(group="node_standard", node_index=n, n=count, rank=rank, q=q))
        q, count, rank = order_quantile(e[:, :, n][~t[:, :, n]], alpha)
        stable.append(q)
        ranks.append(dict(group="behavior_untriggered", node_index=n, n=count, rank=rank, q=q))
    qt, count, rank = order_quantile(e[t], alpha)
    ranks.append(dict(group="behavior_triggered_pooled", node_index=-1, n=count, rank=rank, q=qt))
    return dict(node_standard=np.array(node), stable=np.array(stable), triggered=qt), ranks


def interval_metrics(error, halfwidth, alpha):
    """Symmetric, unclipped intervals: width + outside-distance penalty."""
    e, q = np.broadcast_arrays(np.asarray(error), np.asarray(halfwidth))
    if not np.isfinite(e).all() or not np.isfinite(q).all() or np.any(q < 0):
        raise ValueError("Nonfinite or negative interval data")
    return dict(coverage=float(np.mean(e <= q)), width=float(np.mean(2 * q)),
                interval_score=float(np.mean(2 * q + (2 / alpha) * np.maximum(e - q, 0))))


def bootstrap_ratio(sums, counts, draws):
    """Paired cluster ratio; empty resamples cause a loud failure, never deletion."""
    s = np.asarray(sums, dtype=np.float64)
    c = np.asarray(counts, dtype=np.float64)
    numerator = s[draws].sum(axis=1)
    denominator = c[draws].sum(axis=1)
    if np.any(denominator == 0):
        raise ValueError("Empty bootstrap denominator; revise the recorded design")
    values = numerator / denominator
    return dict(estimate=float(s.sum() / c.sum()), low=float(np.quantile(values, .025)),
                high=float(np.quantile(values, .975)), valid_resamples=len(values))


def read_prediction(folder, split, data, sources, reference=None):
    path = folder / f"predictions_{split}.npz"
    manifest = json.loads((folder / "manifest.json").read_text())
    digest = sha256_file(path)
    if digest != manifest[path.name]:
        raise ValueError(f"Prediction source digest mismatch: {path}")
    sources[str(path.relative_to(ROOT))] = digest
    with np.load(path, allow_pickle=False) as f:
        a = {k: f[k] for k in f.files}
    k = data.arrays[split + "_origins"]
    indices = k[:, None] + np.arange(1, 5)
    target, trigger = data.masks(k)
    expected = dict(origins=k, node_ids=data.arrays["node_ids"],
                    target_timestamps_ns=data.arrays["timestamps_ns"][indices],
                    origin_cutoff_ns=data.arrays["timestamps_ns"][k] + 900_000_000_000,
                    y_true=data.arrays["targets"][indices], target_event=target, rule_trigger=trigger)
    for key, value in expected.items():
        if not np.array_equal(a[key], value):
            raise ValueError(f"Frozen key/truth/mask mismatch: {path}, {key}")
        if reference is not None and not np.array_equal(a[key], reference[key]):
            raise ValueError(f"Cross-run alignment mismatch: {key}")
    if a["y_pred"].shape != a["y_true"].shape or not np.isfinite(a["y_pred"]).all():
        raise ValueError(f"Invalid predictions: {path}")
    metric = json.loads((folder / "metrics.json").read_text())["splits"][split]
    if not np.isclose(np.abs(a["y_true"] - a["y_pred"]).mean(), metric["mae"], atol=1e-12, rtol=0):
        raise ValueError(f"Archived MAE mismatch: {path}")
    return a


def masks(a):
    event, trigger = a["target_event"], a["rule_trigger"]
    return dict(all=np.ones(event.shape, bool), event=event, stable=~event,
                zero=a["y_true"] == 0, nonzero=a["y_true"] != 0,
                cell11=event & trigger, cell10=event & ~trigger,
                cell01=~event & trigger, cell00=~event & ~trigger)


def mean_sd(rows, keys, metrics):
    groups = {}
    for row in rows:
        groups.setdefault(tuple(row[k] for k in keys), []).append(row)
    out = []
    for key, selected in groups.items():
        if len(selected) != 3 or len({r["seed"] for r in selected}) != 3:
            raise ValueError("Expected exactly three independent training seeds per summary")
        row = dict(zip(keys, key))
        if "n" in selected[0]:
            if len({r["n"] for r in selected}) != 1:
                raise ValueError("Seed sample counts differ")
            row["n"] = selected[0]["n"]
        for field in metrics:
            values = [r[field] for r in selected]
            row[field + "_mean"] = float(np.mean(values))
            row[field + "_sd"] = float(np.std(values, ddof=1))
        out.append(row)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    cfg = json.loads(args.config.read_text())
    out = args.out or ROOT / cfg["output"]
    if out.exists():
        raise FileExistsError(f"Refusing to overwrite prior evidence: {out}")
    data = FrozenData(ROOT / cfg["data"])
    source_root = ROOT / cfg["source_root"]
    sources = {str(args.config.relative_to(ROOT)): sha256_file(args.config),
               cfg["data"]: data.digest}
    # Audit all original run manifests, including checkpoints and metadata.
    timings = []
    for folder in sorted(source_root.glob("*/seed-*")):
        manifest = json.loads((folder / "manifest.json").read_text())
        for name, expected in manifest.items():
            p = folder / name
            actual = sha256_file(p)
            if actual != expected:
                raise ValueError(f"Original run artifact changed: {p}")
            sources[str(p.relative_to(ROOT))] = actual
        history = json.loads((folder / "train_log.json").read_text())
        env = json.loads((folder / "environment.json").read_text())
        timings.append(dict(model=folder.parent.name, seed=int(folder.name.split("-")[-1]),
                            gpu=env["gpu"], epochs=len(history),
                            median_epoch_seconds=float(np.median([x["seconds"] for x in history])),
                            training_tuning_minutes=sum(x["seconds"] for x in history) / 60))
    if len(timings) != 36:
        raise ValueError("Expected 36 verified original formal runs")
    references, residuals, archives = {}, {}, {}
    for name in cfg["innovation_models"]:
        residuals[name] = []
        for seed in cfg["seeds"]:
            a = read_prediction(source_root / name / f"seed-{seed}", "test", data, sources, references.get("test"))
            references.setdefault("test", a)
            residuals[name].append(np.abs(a["y_true"] - a["y_pred"]))
            if name == "mrg_full":
                archives[(seed, "test")] = a
                archives[(seed, "calibration")] = read_prediction(
                    source_root / name / f"seed-{seed}", "calibration", data, sources, references.get("calibration"))
                references.setdefault("calibration", archives[(seed, "calibration")])
    a = references["test"]
    cal = references["calibration"]
    if np.intersect1d(cal["target_timestamps_ns"], a["target_timestamps_ns"]).size:
        raise ValueError("Calibration/test target overlap")
    if cal["target_timestamps_ns"].max() >= a["target_timestamps_ns"].min():
        raise ValueError("Calibration must chronologically precede test")
    dates = pd.to_datetime(a["origin_cutoff_ns"], utc=True).tz_convert("America/Los_Angeles").tz_localize(None).normalize()
    day = ((dates - dates.min()) / pd.Timedelta(days=1)).to_numpy(dtype=np.int64)
    block = day // cfg["bootstrap"]["block_days"]
    bcount = int(block.max()) + 1
    draws = np.random.default_rng(cfg["bootstrap"]["seed"]).integers(
        0, bcount, size=(cfg["bootstrap"]["resamples"], bcount))
    mm = masks(a)
    innovation_rows, node_rows, month_rows, paired = [], [], [], []
    months = pd.to_datetime(a["origin_cutoff_ns"], utc=True).tz_convert("America/Los_Angeles").strftime("%Y-%m").to_numpy()
    mean_errors = {}
    for name, errors in residuals.items():
        mean_errors[name] = np.mean(errors, axis=0)
        for seed, error in zip(cfg["seeds"], errors):
            for group in ("all", "event", "stable", "zero", "nonzero"):
                m = mm[group]
                innovation_rows.append(dict(model=name, seed=seed, group=group, n=int(m.sum()), mae=float(error[m].mean())))
            for n, node in enumerate(a["node_ids"]):
                node_rows.append(dict(model=name, seed=seed, node=str(node), n=error.shape[0] * 4, mae=float(error[:, :, n].mean())))
            for month in np.unique(months):
                m = months == month
                month_rows.append(dict(model=name, seed=seed, month=str(month), n=int(m.sum()) * 40, mae=float(error[m].mean())))
    block_rows = []
    for name in cfg["innovation_models"]:
        if name == "mrg_full":
            continue
        diff = mean_errors[name] - mean_errors["mrg_full"]
        for group in ("all", "event", "stable", "zero", "nonzero"):
            m = mm[group]
            s = np.bincount(block, weights=np.where(m, diff, 0).sum(axis=(1, 2)), minlength=bcount)
            count = np.bincount(block, weights=m.sum(axis=(1, 2)), minlength=bcount)
            ci = bootstrap_ratio(s, count, draws)
            paired.append(dict(baseline=name, group=group, primary=name in cfg["primary_comparisons"],
                               n=int(m.sum()), blocks=bcount, **ci))
            block_rows.extend(dict(baseline=name, group=group, block=i, sum_seed_mean_difference=float(s[i]), n=int(count[i])) for i in range(bcount))
    coverage_rows, rank_rows, ci_rows, quantile_rows = [], [], [], []
    interval_outputs = []
    for seed in cfg["seeds"]:
        calibration, test = archives[(seed, "calibration")], archives[(seed, "test")]
        ce = np.abs(calibration["y_true"] - calibration["y_pred"])
        te = np.abs(test["y_true"] - test["y_pred"])
        halfwidth, ranks = fit_halfwidths(ce, calibration["rule_trigger"], cfg["alpha"])
        for row in ranks:
            rank_rows.append(dict(seed=seed, node=str(a["node_ids"][row["node_index"]]) if row["node_index"] >= 0 else "pooled", **row))
        saved = dict(origins=test["origins"], node_ids=test["node_ids"], target_timestamps_ns=test["target_timestamps_ns"], origin_cutoff_ns=test["origin_cutoff_ns"])
        for method in cfg["calibration_methods"]:
            q = np.broadcast_to(halfwidth["node_standard"][None, None, :], te.shape) if method == "node_standard" else np.where(test["rule_trigger"], halfwidth["triggered"], halfwidth["stable"][None, None, :])
            saved[method + "_lower"] = test["y_pred"] - q
            saved[method + "_upper"] = test["y_pred"] + q
            saved[method + "_halfwidth"] = q
            for group, mask in mm.items():
                coverage_rows.append(dict(seed=seed, method=method, group=group, n=int(mask.sum()), **interval_metrics(te[mask], q[mask], cfg["alpha"])))
            for n, node in enumerate(test["node_ids"]):
                coverage_rows.append(dict(seed=seed, method=method, group="node:" + str(node), n=te.shape[0] * 4, **interval_metrics(te[:, :, n], q[:, :, n], cfg["alpha"])))
            for h in range(4):
                coverage_rows.append(dict(seed=seed, method=method, group=f"horizon:{h + 1}", n=te.shape[0] * 10, **interval_metrics(te[:, h], q[:, h], cfg["alpha"])))
        for split, err in (("calibration", ce), ("test", te)):
            quantile_rows.append(dict(seed=seed, split=split, n=err.size, p50=float(np.quantile(err, .5)), p90=float(np.quantile(err, .9)), p95=float(np.quantile(err, .95))))
        interval_outputs.append((seed, saved))
    coverage_summary = mean_sd(coverage_rows, ["method", "group"], ["coverage", "width", "interval_score"])
    for method in cfg["calibration_methods"]:
        # Use the same residual <= q tie rule as the metrics (bound arithmetic
        # can introduce an extra float64 rounding error at exact equality).
        covered = np.mean([np.abs(archives[(s, "test")]["y_true"] - archives[(s, "test")]["y_pred"]) <=
                           saved[method + "_halfwidth"] for s, saved in interval_outputs], axis=0)
        for group in ("all", "event", "stable"):
            m = mm[group]
            sums = np.bincount(block, weights=np.where(m, covered, 0).sum(axis=(1, 2)), minlength=bcount)
            counts = np.bincount(block, weights=m.sum(axis=(1, 2)), minlength=bcount)
            ci_rows.append(dict(method=method, group=group, blocks=bcount, **bootstrap_ratio(sums, counts, draws)))
    raw = Path(cfg["raw_sessions"])
    sources[str(raw)] = sha256_file(raw)
    sessions = pd.read_csv(raw)
    selected = sessions[sessions.spaceID.isin(data.arrays["node_ids"])]
    energy_rows = []
    for i, node in enumerate(data.arrays["node_ids"]):
        e = float(selected.loc[selected.spaceID == node, "kWhDelivered"].sum())
        target_e = float(data.arrays["targets"][:, i].sum())
        if not np.isclose(e, target_e, atol=1e-8, rtol=0):
            raise ValueError(f"Energy allocation conservation failure: {node}")
        energy_rows.append(dict(node=str(node), sessions=int((selected.spaceID == node).sum()), session_energy_kwh=e,
                               proxy_energy_kwh=target_e, absolute_gap_kwh=abs(e - target_e)))
    out.mkdir(parents=True)
    write_json(out / "config_resolved.json", cfg)
    for name, rows in (("innovation_by_group.csv", innovation_rows), ("innovation_by_node.csv", node_rows),
                       ("innovation_by_month.csv", month_rows), ("paired_blocks.csv", block_rows),
                       ("paired_block_ci.csv", paired), ("coverage_per_seed.csv", coverage_rows),
                       ("calibration_quantiles.csv", rank_rows), ("coverage_summary.csv", coverage_summary),
                       ("coverage_block_ci.csv", ci_rows), ("residual_quantiles.csv", quantile_rows),
                       ("energy_conservation.csv", energy_rows), ("training_timing.csv", timings)):
        write_csv(out / name, rows)
    for seed, arrays in interval_outputs:
        np.savez_compressed(out / f"intervals_seed-{seed}.npz", **arrays)
    summary = dict(analysis_id=cfg["analysis_id"], status="passed", created_utc=datetime.now(timezone.utc).isoformat(),
                   protocol=cfg["protocol"], original_runs_verified=len(timings), source_hashes=sources,
                   origin_counts={s: len(data.arrays[s + "_origins"]) for s in SEGMENTS},
                   calibration_test_target_overlap=0, test_blocks=bcount,
                   full_test_keys=a["y_true"].size, calibration_keys=cal["y_true"].size,
                   energy=dict(selected_sessions=len(selected), session_total_kwh=float(selected.kWhDelivered.sum()),
                               proxy_total_kwh=float(data.arrays["targets"].sum()), max_node_gap_kwh=max(r["absolute_gap_kwh"] for r in energy_rows)),
                   innovation_summary=mean_sd(innovation_rows, ["model", "group"], ["mae"]),
                   node_summary=mean_sd(node_rows, ["model", "node"], ["mae"]),
                   paired_block_ci=paired, coverage_summary=coverage_summary, coverage_block_ci=ci_rows,
                   quantile_summary=mean_sd(quantile_rows, ["split"], ["p50", "p90", "p95"]),
                   environment=dict(python=platform.python_version(), numpy=np.__version__, pandas=pd.__version__),
                   limitations=["Previously inspected test; posthoc exploration, not untouched confirmation",
                                "Independent calibration segment, not statistically independent observations",
                                "Overlapping windows and temporal shift; no unconditional 90% coverage guarantee",
                                "Time-block CIs descriptive; no multiple-endpoint correction or future-period guarantee",
                                "Event-time availability assumes immediate reporting; target remains retrospective proxy",
                                "Energy conservation does not validate measured peaks or metered power",
                                "No training, measured-power data or dispatch benefit added"])
    # Recheck source hashes after computation so accidental mutation cannot pass.
    for name, digest in sources.items():
        p = Path(name) if Path(name).is_absolute() else ROOT / name
        if sha256_file(p) != digest:
            raise ValueError(f"Source changed during analysis: {p}")
    write_json(out / "summary.json", summary)
    write_json(out / "manifest.json", dict(script_sha256=sha256_file(Path(__file__)),
               files={p.name: sha256_file(p) for p in sorted(out.iterdir()) if p.is_file()}, sources=sources))
    print(json.dumps({"status": "passed", "energy": summary["energy"],
                      "coverage": [r for r in coverage_summary if r["group"] in ("all", "event", "stable")],
                      "primary_comparisons": [r for r in paired if r["primary"]]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
