#!/usr/bin/env python3
"""Paired, post-hoc audit of existing SG-EXP-019 relation-subset predictions.

This reads archived predictions only. It does not train models or alter sources.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np


REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / "outputs/evidence/checkpoint-replay-20261012/components/sg019/results/formal"
MODELS = ("mrg_full", "mrg_load", "mrg_event", "mrg_pattern")
SEEDS = (2024, 2025, 2026)
KEY_FIELDS = (
    "y_true", "origins", "node_ids", "target_event", "rule_trigger",
    "target_timestamps_ns", "origin_cutoff_ns",
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_run(model: str, seed: int) -> dict:
    path = SOURCE / model / f"seed-{seed}" / "predictions_test.npz"
    with np.load(path, allow_pickle=False) as z:
        out = {key: z[key].copy() for key in (*KEY_FIELDS, "y_pred")}
    return {"path": path, **out}


def local_block_index(origin_ns: np.ndarray) -> tuple[np.ndarray, list[str]]:
    tz = ZoneInfo("America/Los_Angeles")
    dates = [
        dt.datetime.fromtimestamp(int(ns) / 1e9, tz=dt.timezone.utc)
        .astimezone(tz).date()
        for ns in origin_ns
    ]
    start = min(dates)
    index = np.asarray([(d - start).days // 7 for d in dates], dtype=np.int64)
    labels = [
        f"{start + dt.timedelta(days=7 * i)}"
        for i in range(int(index.max()) + 1)
    ]
    return index, labels


def bootstrap_ratio(block_sums: np.ndarray, block_counts: np.ndarray,
                    draws: np.ndarray) -> dict:
    values = block_sums[draws].sum(axis=1) / block_counts[draws].sum(axis=1)
    return {
        "estimate": float(block_sums.sum() / block_counts.sum()),
        "ci95": [float(np.quantile(values, .025)), float(np.quantile(values, .975))],
        "bonferroni_98_3333": [
            float(np.quantile(values, 1 / 120)),
            float(np.quantile(values, 1 - 1 / 120)),
        ],
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=REPO / "outputs/analysis/SG-EXP-019-relation-value-20261013")
    ap.add_argument("--bootstrap-draws", type=int, default=10000)
    args = ap.parse_args()
    if args.out.exists() and any(args.out.iterdir()):
        raise SystemExit(f"Refusing to overwrite non-empty output directory: {args.out}")
    args.out.mkdir(parents=True, exist_ok=True)

    runs: dict[tuple[str, int], dict] = {}
    source_hashes: dict[str, str] = {}
    for model in MODELS:
        for seed in SEEDS:
            run = load_run(model, seed)
            runs[(model, seed)] = run
            source_hashes[str(run["path"].relative_to(REPO))] = sha256(run["path"])

    reference = runs[("mrg_full", SEEDS[0])]
    key_checks = []
    for model in MODELS:
        for seed in SEEDS:
            run = runs[(model, seed)]
            row = {"model": model, "seed": seed}
            for key in KEY_FIELDS:
                row[key + "_exact"] = bool(np.array_equal(reference[key], run[key]))
            row["prediction_shape"] = list(run["y_pred"].shape)
            row["predictions_finite"] = bool(np.isfinite(run["y_pred"]).all())
            key_checks.append(row)
    failed = [
        row for row in key_checks
        if not row["predictions_finite"] or any(
            not row.get(key + "_exact", True) for key in KEY_FIELDS
        )
    ]
    if failed:
        raise SystemExit("Key/source alignment failed; see printed rows: " + json.dumps(failed))

    origins = reference["origins"]
    block, block_labels = local_block_index(reference["origin_cutoff_ns"])
    n_blocks = len(block_labels)
    rng = np.random.default_rng(20261013)
    draws = rng.integers(0, n_blocks, size=(args.bootstrap_draws, n_blocks))
    full_errors = {
        seed: np.abs(runs[("mrg_full", seed)]["y_true"] - runs[("mrg_full", seed)]["y_pred"])
        for seed in SEEDS
    }
    comparison_rows = []
    block_rows = []
    comparisons = ("mrg_load", "mrg_event", "mrg_pattern")
    for model in comparisons:
        seed_delta = []
        seed_delta_event = []
        seed_delta_stable = []
        per_origin_delta = []
        for seed in SEEDS:
            run = runs[(model, seed)]
            err = np.abs(run["y_true"] - run["y_pred"])
            delta = err - full_errors[seed]  # positive means full has lower absolute error
            seed_delta.append(float(delta.mean()))
            evt = reference["target_event"]
            seed_delta_event.append(float(delta[evt].mean()))
            seed_delta_stable.append(float(delta[~evt].mean()))
            per_origin_delta.append(delta)

        key_delta = np.mean(np.stack(per_origin_delta, axis=0), axis=0)
        origin_sum = key_delta.sum(axis=(1, 2))
        counts = np.full(len(origins), key_delta.shape[1] * key_delta.shape[2], dtype=np.int64)
        block_sums = np.bincount(block, weights=origin_sum, minlength=n_blocks)
        block_counts = np.bincount(block, weights=counts, minlength=n_blocks)
        ci = bootstrap_ratio(block_sums, block_counts, draws)
        comparison_rows.append({
            "single_relation_model": model,
            "sign_convention": "single_relation_abs_error - mrg_full_abs_error; positive favors full",
            "seed_differences_kwh_per_15min": seed_delta,
            "mean_seed_difference_kwh_per_15min": float(np.mean(seed_delta)),
            "event_mean_seed_difference_kwh_per_15min": float(np.mean(seed_delta_event)),
            "stable_mean_seed_difference_kwh_per_15min": float(np.mean(seed_delta_stable)),
            "all_three_seed_differences_positive": bool(all(x > 0 for x in seed_delta)),
            "time_block_bootstrap": ci,
            "positive_time_blocks": int(np.count_nonzero(block_sums > 0)),
            "time_blocks": n_blocks,
        })
        for i, label in enumerate(block_labels):
            block_rows.append({
                "comparison": model,
                "local_block_start": label,
                "n_prediction_keys": int(block_counts[i]),
                "single_minus_full_abs_error_sum": float(block_sums[i]),
                "single_minus_full_mae": float(block_sums[i] / block_counts[i]),
            })

    seed_metric_rows = []
    for model in MODELS:
        for seed in SEEDS:
            run = runs[(model, seed)]
            err = np.abs(run["y_true"] - run["y_pred"])
            seed_metric_rows.append({
                "model": model,
                "seed": seed,
                "test_keys": int(err.size),
                "global_mae": float(err.mean()),
                "event_mae": float(err[run["target_event"]].mean()),
                "stable_mae": float(err[~run["target_event"]].mean()),
                "prediction_file_sha256": source_hashes[str(run["path"].relative_to(REPO))],
            })

    payload = {
        "audit_id": "SG-EXP-019-RELATION-VALUE-20261013",
        "status": "POST_HOC_DIAGNOSTIC",
        "training_performed": False,
        "source_root": str(SOURCE.relative_to(REPO)),
        "protocol": "SG-DATA-006-eventtime-v1 / SG-EXP-019",
        "source_manifest_sha256": sha256(REPO / "outputs/evidence/checkpoint-replay-20261012/MANIFEST.json"),
        "source_prediction_hashes": source_hashes,
        "comparison_models": list(comparisons),
        "n_seeds": len(SEEDS),
        "prediction_keys_per_seed": int(reference["y_true"].size),
        "all_key_arrays_exact_across_models_and_seeds": True,
        "time_block_design": {
            "unit": "seven consecutive local calendar days from first test origin date",
            "timezone": "America/Los_Angeles",
            "blocks": n_blocks,
            "block_labels": block_labels,
            "bootstrap_draws": args.bootstrap_draws,
            "random_seed": 20261013,
            "positive_difference": "single-relation absolute error minus full-model absolute error",
            "multiple_comparison_interval": "Bonferroni percentile interval for three post-hoc global comparisons",
        },
        "key_alignment_checks": key_checks,
        "seed_metrics": seed_metric_rows,
        "comparisons": comparison_rows,
        "interpretation_limits": [
            "Post-hoc analysis on an already inspected fixed test period; not preregistered confirmatory evidence.",
            "Single-relation-only comparisons do not estimate the unique marginal contribution of each relation conditional on the other two.",
            "Single-relation models have fewer trainable parameters than mrg_full; no parameter-matched control was trained.",
            "Three seeds and fixed-period time blocks do not establish new-site or future-period generalization.",
        ],
    }
    (args.out / "relation-value-audit.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    with (args.out / "seed-metrics.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(seed_metric_rows[0]))
        w.writeheader(); w.writerows(seed_metric_rows)
    with (args.out / "paired-time-blocks.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(block_rows[0]))
        w.writeheader(); w.writerows(block_rows)
    print(json.dumps({
        "out": str(args.out),
        "alignment_rows": len(key_checks),
        "blocks": n_blocks,
        "comparisons": comparison_rows,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
