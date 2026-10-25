#!/usr/bin/env python3
"""Independent file, contract, prediction-key and metric audit for SG-EXP-032."""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SEEDS = (2024, 2025, 2026)
MODELS = ("mrg_full", "tcn_wide")
NODES = 10
HORIZON = 4
UNIT = "kWh/15 min"


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def load_json(path):
    return json.loads(Path(path).read_text())


def load_npz(path):
    with np.load(path, allow_pickle=False) as z:
        return {k: z[k] for k in z.files}


def check_manifest(folder):
    manifest = load_json(folder / "manifest.json")
    rows = []
    for name, expected in manifest.items():
        p = folder / name
        observed = sha(p) if p.is_file() else None
        rows.append({"path": str(p), "expected": expected, "observed": observed,
                     "ok": observed == expected})
    if not rows or not all(r["ok"] for r in rows):
        raise ValueError(f"Run manifest mismatch: {folder}")
    return rows


def block_ids(origin_cutoff_ns):
    tz = ZoneInfo("America/Los_Angeles")
    dates = [dt.datetime.fromtimestamp(int(ns) / 1e9, tz=dt.timezone.utc).astimezone(tz).date()
             for ns in origin_cutoff_ns]
    first = min(dates)
    labels = [str((d - first).days // 7) for d in dates]
    unique = sorted(set(labels), key=int)
    lookup = {v: i for i, v in enumerate(unique)}
    return np.asarray([lookup[v] for v in labels], dtype=np.int64), [
        str(first + dt.timedelta(days=7 * int(v))) for v in unique]


def _close(a, b, tol=2e-12):
    return bool(np.isclose(float(a), float(b), rtol=2e-10, atol=tol))


def metrics(y, pred, event, trigger):
    e = np.abs(y.astype(np.float64) - pred.astype(np.float64))
    groups = {"all": np.ones(y.shape, bool), "event": event,
              "non_event": ~event, "zero": y == 0, "nonzero": y != 0,
              "event_zero": event & (y == 0), "event_nonzero": event & (y != 0)}
    out = {"n": int(y.size), "mae": float(e.mean()),
           "rmse": float(np.sqrt(np.mean((y.astype(np.float64)-pred.astype(np.float64)) ** 2))),
           "by_horizon_mae": e.mean(axis=(0, 2)).tolist(),
           "by_node_mae": e.mean(axis=(0, 1)).tolist(),
           "target_zero_fraction": float(np.mean(y == 0)),
           "event_fraction": float(event.mean()),
           "trigger_fraction": float(trigger.mean())}
    for name, mask in groups.items():
        out[name + "_count"] = int(mask.sum())
        out[name + "_mae"] = float(e[mask].mean()) if mask.any() else None
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, default=ROOT / "outputs/experiments/SG-EXP-032/recovered/closeout/closeout/results/formal")
    ap.add_argument("--data", type=Path, default=ROOT / "outputs/experiments/SG-EXP-032/frozen-contract/dataset.npz")
    ap.add_argument("--out", type=Path, default=ROOT / "outputs/analysis/SG-EXP-032-target-audit")
    ap.add_argument("--bootstrap-draws", type=int, default=10000)
    args = ap.parse_args()
    source, out = args.source.resolve(), args.out.resolve()
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"Refusing to overwrite non-empty audit output: {out}")
    frozen = load_npz(args.data)
    runs, run_rows, all_file_checks = {}, [], []
    for model in MODELS:
        for seed in SEEDS:
            folder = source / model / f"seed-{seed}"
            required = ("config_resolved.json", "environment.json", "environment.txt", "best.pt", "last.pt",
                        "train_log.json", "predictions_tuning.npz", "predictions_calibration.npz",
                        "predictions_test.npz", "metrics.json", "run_summary.json", "exit_code.txt", "manifest.json")
            missing = [n for n in required if not (folder / n).is_file()]
            if missing:
                raise ValueError(f"Missing artifacts {missing}: {folder}")
            checks = check_manifest(folder)
            all_file_checks.extend(checks)
            cfg = load_json(folder / "config_resolved.json")
            summary = load_json(folder / "run_summary.json")
            log = load_json(folder / "train_log.json")
            reported = load_json(folder / "metrics.json")
            if (cfg.get("experiment") != "SG-EXP-032" or cfg.get("model") != model
                    or int(cfg.get("seed")) != seed or cfg.get("mode") != "formal_completion_target_sensitivity"):
                raise ValueError(f"Resolved config identity mismatch: {folder}")
            if cfg.get("completion_dataset_sha256") != sha(args.data):
                raise ValueError(f"Dataset hash mismatch: {folder}")
            expected_params = 32714 if model == "mrg_full" else 32674
            if int(cfg.get("trainable_parameters")) != expected_params:
                raise ValueError(f"Parameter count mismatch: {folder}")
            if (cfg.get("max_epochs") != 60 or cfg.get("patience") != 8 or cfg.get("batch_size") != 256
                    or cfg.get("lr") != .001 or cfg.get("weight_decay") != .0001
                    or cfg.get("selection") != "tuning_original_unit_MAE"):
                raise ValueError(f"Training contract mismatch: {folder}")
            if summary.get("status") != "complete" or summary.get("mode") != "formal_completion_target_sensitivity":
                raise ValueError(f"Run not complete/formal: {folder}")
            if Path(folder / "exit_code.txt").read_text().strip() != "0":
                raise ValueError(f"Nonzero run exit: {folder}")
            epochs = [int(row["epoch"]) for row in log]
            if not epochs or epochs != list(range(1, epochs[-1] + 1)) or epochs[-1] > 60:
                raise ValueError(f"Epoch log is incomplete/invalid: {folder}")
            best_epoch = int(np.argmin([float(row["tuning_mae"]) for row in log])) + 1
            if best_epoch != int(summary["best_epoch"]) or best_epoch != int(reported["selected_epoch"]):
                raise ValueError(f"Best checkpoint epoch does not match tuning log: {folder}")

            splits = {}
            for split in ("tuning", "calibration", "test"):
                predfile = load_npz(folder / f"predictions_{split}.npz")
                origins = frozen[f"{split}_origins"]
                if not np.array_equal(predfile["origins"], origins):
                    raise ValueError(f"Origin keys changed for {split}: {folder}")
                idx = origins[:, None] + np.arange(1, HORIZON + 1)[None, :]
                y_expected = frozen["targets"][idx]
                event_expected = frozen["target_event"][idx]
                trigger_expected = np.repeat(frozen["rule_trigger"][origins, None, :], HORIZON, axis=1)
                timestamps_expected = frozen["timestamps_ns"][idx]
                checks_exact = {
                    "node_ids": np.array_equal(predfile["node_ids"], frozen["node_ids"]),
                    "y_true": np.array_equal(predfile["y_true"], y_expected),
                    "target_event": np.array_equal(predfile["target_event"], event_expected),
                    "rule_trigger": np.array_equal(predfile["rule_trigger"], trigger_expected),
                    "target_timestamps_ns": np.array_equal(predfile["target_timestamps_ns"], timestamps_expected),
                    "origin_cutoff_ns": np.array_equal(predfile["origin_cutoff_ns"], frozen["timestamps_ns"][origins] + 900_000_000_000),
                }
                if not all(checks_exact.values()):
                    raise ValueError(f"Label/event/timestamp key mismatch {split}: {folder} {checks_exact}")
                if not np.isfinite(predfile["y_pred"]).all() or not np.isfinite(predfile["y_true"]).all():
                    raise ValueError(f"Nonfinite predictions: {folder}/{split}")
                m = metrics(predfile["y_true"], predfile["y_pred"],
                            predfile["target_event"], predfile["rule_trigger"])
                for name in ("mae", "rmse", "event_mae", "stable_mae"):
                    if name in reported["splits"][split] and not _close(m[name] if name not in ("event_mae", "stable_mae") else m["event_mae" if name == "event_mae" else "non_event_mae"],
                                                                           reported["splits"][split][name]):
                        raise ValueError(f"Metric mismatch {name} {split}: {folder}")
                splits[split] = predfile
                if split == "test":
                    runs[(model, seed)] = {"folder": folder, "arrays": predfile, "metric": m,
                                           "reported": reported["splits"][split], "epochs": epochs[-1],
                                           "best_epoch": best_epoch, "train_seconds": float(sum(x["seconds"] for x in log))}
                    run_rows.append({"model": model, "seed": seed, "parameters": expected_params,
                                     "epochs": epochs[-1], "best_epoch": best_epoch,
                                     "train_seconds": runs[(model, seed)]["train_seconds"],
                                     "mae": m["mae"], "rmse": m["rmse"],
                                     "event_mae": m["event_mae"], "non_event_mae": m["non_event_mae"],
                                     "zero_mae": m["zero_mae"], "nonzero_mae": m["nonzero_mae"],
                                     "zero_fraction": m["target_zero_fraction"],
                                     "event_fraction": m["event_fraction"],
                                     "zero_count": m["zero_count"], "nonzero_count": m["nonzero_count"]})

    # All six runs must have exactly common keys and labels, even across seeds.
    ref = runs[(MODELS[0], SEEDS[0])]["arrays"]
    key_fields = ("origins", "node_ids", "y_true", "target_event", "rule_trigger",
                  "target_timestamps_ns", "origin_cutoff_ns")
    key_audit = []
    for model in MODELS:
        for seed in SEEDS:
            arr = runs[(model, seed)]["arrays"]
            for field in key_fields:
                exact = bool(np.array_equal(arr[field], ref[field]))
                key_audit.append({"model": model, "seed": seed, "field": field, "exact": exact})
                if not exact:
                    raise ValueError(f"Cross-run key mismatch: {model}/{seed}/{field}")

    # Primary paired contrast: TCN abs error - MRG abs error, positive favors MRG.
    seed_delta = {}
    all_key_deltas = []
    event_mask = ref["target_event"]
    zero_mask = ref["y_true"] == 0
    nonzero_mask = ~zero_mask
    for seed in SEEDS:
        mrg = runs[("mrg_full", seed)]["arrays"]
        tcn = runs[("tcn_wide", seed)]["arrays"]
        delta = np.abs(tcn["y_true"] - tcn["y_pred"]) - np.abs(mrg["y_true"] - mrg["y_pred"])
        seed_delta[seed] = {"global": float(delta.mean()),
                            "event": float(delta[event_mask].mean()),
                            "non_event": float(delta[~event_mask].mean()),
                            "zero": float(delta[zero_mask].mean()),
                            "nonzero": float(delta[nonzero_mask].mean())}
        all_key_deltas.append(delta)
    mean_key_delta = np.mean(np.stack(all_key_deltas, axis=0), axis=0)
    bid, blabels = block_ids(ref["origin_cutoff_ns"])
    nblocks = len(blabels)
    if nblocks < 12:
        raise ValueError(f"Too few seven-day blocks for interval: {nblocks}")
    origin_sums = mean_key_delta.sum(axis=(1, 2))
    block_sums = np.bincount(bid, weights=origin_sums, minlength=nblocks)
    block_counts = np.bincount(bid, weights=np.full(len(bid), mean_key_delta.shape[1] * mean_key_delta.shape[2]), minlength=nblocks)
    rng = np.random.default_rng(20261015)
    draws = rng.integers(0, nblocks, size=(args.bootstrap_draws, nblocks))
    sampled = block_sums[draws].sum(axis=1) / block_counts[draws].sum(axis=1)
    interval = {"estimate": float(block_sums.sum() / block_counts.sum()),
                "ci95": [float(np.quantile(sampled, .025)), float(np.quantile(sampled, .975))],
                "positive_blocks": int(np.count_nonzero(block_sums > 0)),
                "blocks": nblocks, "draws": int(args.bootstrap_draws), "seed": 20261015,
                "block_definition": "contiguous 7-day blocks by America/Los_Angeles origin-cutoff calendar date, anchored at first observed test date"}
    aggregate = {}
    for model in MODELS:
        aggregate[model] = {}
        for metric in ("mae", "rmse", "event_mae", "non_event_mae", "zero_mae", "nonzero_mae", "target_zero_fraction"):
            values = [runs[(model, s)]["metric"][metric] for s in SEEDS]
            aggregate[model][metric] = {"per_seed": values, "mean": float(np.mean(values)),
                                        "sample_sd": float(np.std(values, ddof=1))}
    out.mkdir(parents=True, exist_ok=True)
    with (out / "run-metrics.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(run_rows[0])); w.writeheader(); w.writerows(run_rows)
    with (out / "paired-seven-day-blocks.csv").open("w", newline="", encoding="utf-8") as f:
        fields = ("block_start_local", "prediction_keys", "tcn_minus_mrg_abs_error_sum", "tcn_minus_mrg_mae")
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
        for i, label in enumerate(blabels):
            w.writerow({"block_start_local": label, "prediction_keys": int(block_counts[i]),
                        "tcn_minus_mrg_abs_error_sum": float(block_sums[i]),
                        "tcn_minus_mrg_mae": float(block_sums[i] / block_counts[i])})
    audit = {
        "audit_id": "SG-EXP-032-RESULTS-20261015", "status": "PASS",
        "posthoc_fixed_test_period": True, "training_completed": True,
        "source_results_root": str(source), "data_sha256": sha(args.data),
        "run_count": len(runs), "required_run_count": 6,
        "verified_result_manifest_entries": len(all_file_checks),
        "all_file_hashes_pass": True, "all_predictions_finite": True,
        "test_prediction_keys_per_run": int(ref["y_true"].size),
        "common_keys_exact_across_all_runs": True, "key_audit": key_audit,
        "aggregate_by_model": aggregate,
        "primary_contrast": "per-seed paired TCN absolute error minus MRG absolute error on exact common (origin,horizon,node) keys; positive favors MRG-GCN",
        "paired_seed_differences_kwh_per_15min": {str(k): v for k, v in seed_delta.items()},
        "mean_paired_test_mae_difference_kwh_per_15min": float(np.mean([seed_delta[s]["global"] for s in SEEDS])),
        "time_block_bootstrap": interval,
        "event_zero_nonzero_strata": "Frozen original SG-DATA-006 target_event for event strata; zero/nonzero defined by completion-truncated target; all are evaluation-only.",
        "scope_limits": [
            "The Caltech fixed test period has previously been inspected; this is a post-hoc sensitivity experiment, not untouched confirmation.",
            "The completion-truncated target is still session-derived proxy energy, not metered power.",
            "The experiment freezes the original train-prefix graph to isolate target-label sensitivity; it does not test topology rebuilt from the alternative target.",
            "Seven-day blocks describe within-period temporal variation and do not establish a new site, period, or full training-seed population.",
            "Do not compare the 0.0477816 target-reconstruction difference numerically against model MAE as if they estimated the same quantity."
        ]}
    (out / "audit.json").write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n")
    rows = [f"# SG-EXP-032 result audit", "", "Audit status: PASS; six complete runs, exact common forecast keys and labels, per-file checksums, finite predictions, and independent metric recalculation verified.", "",
            "## Test-set summary (mean ± sample SD across three seeds)", "",
            "| Model | MAE | RMSE | Event MAE | Non-event MAE | Zero MAE | Nonzero MAE |", "|---|---:|---:|---:|---:|---:|---:|"]
    for model in MODELS:
        a = aggregate[model]
        rows.append("| {} | {}±{} | {}±{} | {}±{} | {}±{} | {}±{} | {}±{} |".format(
            model, *[f"{a[m]['mean']:.6f}" for m in ("mae",)], f"{a['mae']['sample_sd']:.6f}",
            f"{a['rmse']['mean']:.6f}", f"{a['rmse']['sample_sd']:.6f}",
            f"{a['event_mae']['mean']:.6f}", f"{a['event_mae']['sample_sd']:.6f}",
            f"{a['non_event_mae']['mean']:.6f}", f"{a['non_event_mae']['sample_sd']:.6f}",
            f"{a['zero_mae']['mean']:.6f}", f"{a['zero_mae']['sample_sd']:.6f}",
            f"{a['nonzero_mae']['mean']:.6f}", f"{a['nonzero_mae']['sample_sd']:.6f}"))
    ci = interval["ci95"]
    rows += ["", "## Paired primary contrast", "",
             f"Mean TCN−MRG test MAE difference: {audit['mean_paired_test_mae_difference_kwh_per_15min']:.6f} {UNIT}; 95% paired 7-day-block bootstrap interval [{ci[0]:.6f}, {ci[1]:.6f}], {interval['positive_blocks']}/{nblocks} blocks positive.",
             "", "Positive values favor MRG-GCN. The primary comparison uses the same 17,714 forecast origins × 4 target slices × 10 nodes = 708,560 keys under the new target. Event strata use the unchanged original event labels; zero/nonzero strata use the new target.",
             "", "## Limits", "",
             "This is post-hoc analysis on an already viewed Caltech period. The alternate target is a session-derived proxy, not measured power. The graph was held fixed to isolate label sensitivity. The 0.0477816 kWh/15 min target-definition difference is not a model-error bound and is not directly comparable to model MAE.",
             "", "Detailed evidence is in `audit.json`, per-run results in `run-metrics.csv`, and block differences in `paired-seven-day-blocks.csv`."]
    (out / "README.md").write_text("\n".join(rows) + "\n")
    print(json.dumps({"status": "PASS", "runs": len(runs), "common_test_keys": int(ref["y_true"].size),
                      "primary_difference": audit["mean_paired_test_mae_difference_kwh_per_15min"],
                      "ci95": interval["ci95"], "blocks": nblocks, "output": str(out)}, indent=2))


if __name__ == "__main__":
    main()
