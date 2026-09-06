#!/usr/bin/env python3
"""Audit recovered SG-EXP-019 eventtime formal results without changing them.

The script intentionally writes only to --out. It does not edit formal run folders,
checkpoints, manuscript files, or the old SG-EXP-003 evidence.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
from pathlib import Path

import torch


MODELS = (
    "mrg_full", "tcn", "tcn_wide", "mrg_self_loop", "agcrn_full",
    "mrg_equal_beta", "mrg_fixed_gate", "mrg_no_refine", "mrg_no_skip",
    "mrg_load", "mrg_event", "mrg_pattern",
)
SEEDS = (2024, 2025, 2026)
REQUIRED_FILES = (
    "config_resolved.json", "environment.json", "train_log.json", "best.pt",
    "last.pt", "metrics.json", "run_summary.json", "manifest.json",
    "environment.txt", "exit_code.txt",
    "predictions_tuning.npz", "predictions_calibration.npz", "predictions_test.npz",
)


def load_json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def finite(value) -> bool:
    if isinstance(value, bool) or value is None:
        return value is not None
    if isinstance(value, (int, float)):
        return math.isfinite(float(value))
    if isinstance(value, list):
        return all(finite(item) for item in value)
    if isinstance(value, dict):
        return all(finite(item) for item in value.values())
    return True


def find_formal(root: Path) -> Path:
    candidate = root / "formal"
    return candidate if candidate.is_dir() else root


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def audit_run(path: Path, model: str, seed: int) -> tuple[dict, list[str]]:
    problems: list[str] = []
    missing = [name for name in REQUIRED_FILES if not (path / name).is_file()]
    if missing:
        problems.append("missing:" + ",".join(missing))
        return {"model": model, "seed": seed, "path": str(path), "problems": problems}, problems

    cfg = load_json(path / "config_resolved.json")
    metrics = load_json(path / "metrics.json")
    summary = load_json(path / "run_summary.json")
    history = load_json(path / "train_log.json")
    manifest = load_json(path / "manifest.json")
    manifest_verified = True
    for name, expected_digest in manifest.items():
        candidate = path / name
        if not candidate.is_file() or sha256_file(candidate) != expected_digest:
            manifest_verified = False
            problems.append("manifest_digest_mismatch:" + name)
    if manifest_verified is False:
        problems.append("manifest_not_verified")
    try:
        last_ckpt = torch.load(path / "last.pt", map_location="cpu", weights_only=True)
        best_ckpt = torch.load(path / "best.pt", map_location="cpu", weights_only=True)
    except Exception as exc:  # pragma: no cover - exercised on recovered artifacts
        last_ckpt, best_ckpt = {}, {}
        problems.append("checkpoint_load_failed:" + type(exc).__name__)
    if last_ckpt.get("complete") is not True:
        problems.append("last_checkpoint_not_complete")
    if last_ckpt.get("epoch") != (history[-1].get("epoch") if history else None):
        problems.append("last_checkpoint_epoch_mismatch")
    if summary.get("status") != "complete":
        problems.append("run_summary.status_not_complete")
    if not isinstance(history, list) or not history:
        problems.append("empty_train_log")
    epochs = [row.get("epoch") for row in history if isinstance(row, dict)]
    if not epochs or not all(isinstance(epoch, int) for epoch in epochs):
        problems.append("invalid_train_epochs")
    selected = metrics.get("selected_epoch")
    best_epoch = summary.get("best_epoch")
    if selected != best_epoch:
        problems.append("selected_epoch_mismatch")
    if best_ckpt.get("epoch") != selected:
        problems.append("best_checkpoint_epoch_mismatch")
    if cfg.get("model") != model or cfg.get("seed") != seed:
        problems.append("config_identity_mismatch")
    if cfg.get("contract") and last_ckpt.get("contract") != cfg.get("contract"):
        problems.append("last_checkpoint_contract_mismatch")
    if cfg.get("contract") and best_ckpt.get("contract") != cfg.get("contract"):
        problems.append("best_checkpoint_contract_mismatch")
    if selected not in epochs:
        problems.append("selected_epoch_not_in_train_log")
    if any(not finite(row) for row in history):
        problems.append("nonfinite_train_log")
    test = metrics.get("splits", {}).get("test", {})
    if not test:
        problems.append("missing_test_metrics")
    reconstruction = test.get("four_cell_reconstruction_error")
    if reconstruction is None or reconstruction > 1e-9:
        problems.append("four_cell_reconstruction_failed")
    if not finite(metrics):
        problems.append("nonfinite_metrics")

    report = {
        "model": model,
        "seed": seed,
        "path": str(path),
        "protocol": cfg.get("protocol"),
        "dataset_sha256": cfg.get("dataset_sha256"),
        "code_sha256": cfg.get("code_sha256"),
        "trainable_parameters": cfg.get("trainable_parameters"),
        "max_epochs": cfg.get("max_epochs"),
        "history_epochs": len(history),
        "stop_epoch": epochs[-1] if epochs else None,
        "selected_epoch": selected,
        "stale_at_stop": last_ckpt.get("stale"),
        "stop_reason": (
            "max_epochs" if epochs and epochs[-1] == cfg.get("max_epochs") and last_ckpt.get("stale", 0) < cfg.get("patience", 0)
            else "early_stopping" if last_ckpt.get("stale", 0) >= cfg.get("patience", 0)
            else "unknown"
        ),
        "best_at_stop": bool(epochs and selected == epochs[-1]),
        "checkpoint_complete": last_ckpt.get("complete"),
        "manifest_verified": manifest_verified,
        "global_mae": test.get("mae"),
        "event_mae": test.get("event_mae"),
        "stable_mae": test.get("stable_mae"),
        "four_cell_reconstruction_error": reconstruction,
        "problems": problems,
    }
    return report, problems


def mean_sd(values: list[float]) -> tuple[float | None, float | None]:
    values = [float(value) for value in values if value is not None]
    if not values:
        return None, None
    return statistics.mean(values), statistics.stdev(values) if len(values) > 1 else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="recovered output root or its formal/ directory")
    parser.add_argument("--out", type=Path, required=True, help="new directory for audit products")
    args = parser.parse_args()
    formal = find_formal(args.root)
    args.out.mkdir(parents=True, exist_ok=True)

    runs: list[dict] = []
    for model in MODELS:
        for seed in SEEDS:
            report, _ = audit_run(formal / model / f"seed-{seed}", model, seed)
            runs.append(report)

    expected = {(model, seed) for model in MODELS for seed in SEEDS}
    complete = [row for row in runs if not row.get("problems")]
    common = {}
    for key in ("protocol", "dataset_sha256", "code_sha256", "max_epochs"):
        values = sorted({row.get(key) for row in complete})
        common[key] = {"values": values, "consistent": len(values) <= 1}

    summaries = []
    for model in MODELS:
        rows = [row for row in complete if row.get("model") == model]
        record = {"model": model, "n_runs": len(rows)}
        for metric in ("global_mae", "event_mae", "stable_mae"):
            avg, sd = mean_sd([row.get(metric) for row in rows])
            record[f"{metric}_mean"] = avg
            record[f"{metric}_sd"] = sd
        params = sorted({row.get("trainable_parameters") for row in rows})
        record["trainable_parameters"] = params[0] if len(params) == 1 else params
        record["selected_epochs"] = [row.get("selected_epoch") for row in rows]
        record["problems"] = sorted({problem for row in rows for problem in row.get("problems", [])})
        summaries.append(record)

    by_model = {row["model"]: row for row in summaries}
    mrg_params = by_model.get("mrg_full", {}).get("trainable_parameters")
    fairness = {
        "capacity_matched_candidate": "tcn_wide",
        "mrg_full_parameters": mrg_params,
        "tcn_wide_parameters": by_model.get("tcn_wide", {}).get("trainable_parameters"),
        "agcrn_full_parameters": by_model.get("agcrn_full", {}).get("trainable_parameters"),
        "missing_same_protocol_baselines": ["gru_or_mlp", "linear_or_mean_lower_bound"],
        "agcrn_capacity_matched_version_present": False,
    }
    if isinstance(mrg_params, (int, float)) and isinstance(fairness["tcn_wide_parameters"], (int, float)):
        fairness["tcn_wide_relative_parameter_gap"] = abs(fairness["tcn_wide_parameters"] - mrg_params) / mrg_params
    if isinstance(mrg_params, (int, float)) and isinstance(fairness["agcrn_full_parameters"], (int, float)):
        fairness["agcrn_to_mrg_parameter_ratio"] = fairness["agcrn_full_parameters"] / mrg_params

    payload = {
        "experiment": "SG-EXP-019",
        "protocol": "SG-DATA-006-eventtime-v1",
        "formal_root": str(formal.resolve()),
        "expected_runs": len(expected),
        "discovered_complete_runs": len(complete),
        "all_expected_paths_complete": len(complete) == len(expected),
        "common_contract": common,
        "fairness": fairness,
        "runs": runs,
        "summaries": summaries,
    }
    (args.out / "audit.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    fields = ["model", "n_runs", "global_mae_mean", "global_mae_sd", "event_mae_mean", "event_mae_sd", "stable_mae_mean", "stable_mae_sd", "trainable_parameters", "selected_epochs", "problems"]
    with (args.out / "summary.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in summaries:
            writer.writerow({field: json.dumps(row.get(field), ensure_ascii=False) if isinstance(row.get(field), (list, dict)) else row.get(field) for field in fields})
    print(json.dumps({"status": "passed" if payload["all_expected_paths_complete"] and all(not row["problems"] for row in runs) else "needs_review", "complete": len(complete), "expected": len(expected), "out": str(args.out)}, ensure_ascii=False))
    return 0 if payload["all_expected_paths_complete"] and all(not row["problems"] for row in runs) else 2


if __name__ == "__main__":
    raise SystemExit(main())
