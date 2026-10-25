#!/usr/bin/env python3
"""Verify paired node-gate predictions and test leave-one-node-out sensitivity.

This is a post-hoc sensitivity analysis on the existing SG-EXP-027 and
SG-EXP-028 test predictions. It does not train models or make a new-period
generalization claim.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SG027_MODELS = ("mrg_full", "mrg_shared_gate")
SEEDS = (2024, 2025, 2026)
EXPECTED_SG006 = "f663b510c75e203c8150f57c3765645f92b9a941e0745227c6ea078008a0dc8f"
EXPECTED_JPL = "1bfc42fab6f127b2ec1735b3821bb272a444185f1861bfe95f489d15e78738af"
STEP_NS = 15 * 60 * 1_000_000_000


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_frozen_data(path: Path, expected_digest: str) -> dict[str, np.ndarray]:
    digest = sha256(path)
    if digest != expected_digest:
        raise ValueError(f"Frozen tensor SHA256 mismatch: {path} ({digest})")
    with np.load(path, allow_pickle=False) as archive:
        return {key: archive[key] for key in archive.files}


def verify_run(folder: Path, data: dict[str, np.ndarray], *, expected_models: tuple[str, ...],
               expected_origins: int) -> tuple[dict, dict[str, np.ndarray]]:
    manifest_path = folder / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    pred_path = folder / "predictions_test.npz"
    for name, digest in manifest.items():
        if Path(name).name != name:
            raise ValueError(f"Unsafe manifest path in {manifest_path}: {name}")
        path = folder / name
        if not path.is_file() or sha256(path) != digest:
            raise ValueError(f"Run artifact hash mismatch: {path}")
    if manifest.get(pred_path.name) != sha256(pred_path):
        raise ValueError(f"Prediction hash mismatch: {pred_path}")
    with np.load(pred_path, allow_pickle=False) as archive:
        p = {key: archive[key] for key in archive.files}

    required = {"y_true", "y_pred", "origins", "node_ids", "target_event", "rule_trigger",
                "target_timestamps_ns", "origin_cutoff_ns"}
    if set(p) != required:
        raise ValueError(f"Prediction schema mismatch at {pred_path}: {set(p) ^ required}")

    origins = p["origins"]
    nodes = p["node_ids"]
    h = np.arange(1, 5)[None, :]
    idx = origins[:, None] + h
    frozen_origins = data["test_origins"]
    if len(frozen_origins) != expected_origins or not np.array_equal(origins, frozen_origins):
        raise ValueError(f"Test-origin mismatch at {pred_path}")
    if not np.array_equal(nodes, data["node_ids"]):
        raise ValueError(f"Node-order mismatch at {pred_path}")
    if len(set(nodes.tolist())) != len(nodes):
        raise ValueError(f"Duplicate node ID at {pred_path}")
    if p["y_true"].shape != (len(origins), 4, len(nodes)) or p["y_pred"].shape != p["y_true"].shape:
        raise ValueError(f"Prediction tensor shape mismatch at {pred_path}")
    if not np.array_equal(p["y_true"], data["targets"][idx]):
        raise ValueError(f"Ground truth differs from frozen target tensor at {pred_path}")
    if not np.array_equal(p["target_event"], data["target_event"][idx]):
        raise ValueError(f"Event-mask mismatch at {pred_path}")
    expected_rule = np.repeat(data["rule_trigger"][origins, None, :], 4, axis=1)
    if not np.array_equal(p["rule_trigger"], expected_rule):
        raise ValueError(f"Rule-mask mismatch at {pred_path}")
    if not np.array_equal(p["target_timestamps_ns"], data["timestamps_ns"][idx]):
        raise ValueError(f"Target-time mismatch at {pred_path}")
    if not np.array_equal(p["origin_cutoff_ns"], data["timestamps_ns"][origins] + STEP_NS):
        raise ValueError(f"Forecast-origin cutoff mismatch at {pred_path}")
    if not np.isfinite(p["y_true"]).all() or not np.isfinite(p["y_pred"]).all():
        raise ValueError(f"Nonfinite target or prediction at {pred_path}")
    if origins.ndim != 1 or np.any(np.diff(origins) <= 0):
        raise ValueError(f"Duplicate or unordered origins at {pred_path}")

    errors = np.abs(p["y_true"].astype(np.float64) - p["y_pred"].astype(np.float64))
    metric_path = folder / "metrics.json"
    reported = json.loads(metric_path.read_text())["splits"]["test"]
    computed = {
        "n": int(errors.size),
        "mae": float(errors.mean()),
        "rmse": float(np.sqrt(np.mean((p["y_true"].astype(np.float64) - p["y_pred"].astype(np.float64)) ** 2))),
        "event_mae": float(errors[p["target_event"]].mean()),
        "stable_mae": float(errors[~p["target_event"]].mean()),
        "by_horizon_mae": errors.mean(axis=(0, 2)),
        "by_node_mae": errors.mean(axis=(0, 1)),
    }
    if reported["n"] != computed["n"]:
        raise ValueError(f"Reported test-key count differs at {metric_path}")
    for name in ("mae", "rmse", "event_mae", "stable_mae", "by_horizon_mae", "by_node_mae"):
        if not np.allclose(computed[name], reported[name], atol=1e-12, rtol=0):
            raise ValueError(f"Independent {name} recomputation differs at {metric_path}")
    cell_count = 0
    cell_error_sum = 0.0
    for event_value, trigger_value in ((1, 1), (1, 0), (0, 1), (0, 0)):
        mask = (p["target_event"] == event_value) & (p["rule_trigger"] == trigger_value)
        name = f"target_{event_value}_trigger_{trigger_value}"
        cell = reported["four_cells"][name]
        n, total = int(mask.sum()), float(errors[mask].sum())
        if cell["n"] != n or not np.isclose(cell["sum_absolute_error"], total, atol=1e-9, rtol=0):
            raise ValueError(f"Four-cell reconstruction differs at {metric_path}: {name}")
        cell_count += n
        cell_error_sum += total
    if cell_count != errors.size or not np.isclose(cell_error_sum / cell_count, computed["mae"], atol=1e-12, rtol=0):
        raise ValueError(f"Four-cell weighted MAE does not reconstruct at {metric_path}")

    model = folder.parent.name
    if model not in expected_models:
        raise ValueError(f"Unexpected model directory: {model}")
    seed = int(folder.name.removeprefix("seed-"))
    record = {
        "model": model,
        "seed": seed,
        "keys": int(p["y_true"].size),
        "origins": int(len(origins)),
        "nodes": int(len(nodes)),
        "manifest_sha256": sha256(manifest_path),
        "test_prediction_sha256": sha256(pred_path),
        "test_mae": computed["mae"],
        "metrics_sha256": sha256(metric_path),
        "test_metrics_recomputed": ["n", "mae", "rmse", "event_mae", "stable_mae",
                                    "by_horizon_mae", "by_node_mae", "four_cells"],
    }
    return record, p


def evaluate_site(site: str, data_path: Path, run_root: Path, models: tuple[str, ...],
                  expected_digest: str, origin_count: int) -> dict:
    data = load_frozen_data(data_path, expected_digest)
    errors: dict[str, dict[int, np.ndarray]] = {model: {} for model in models}
    records = []
    reference: dict | None = None
    reference_keys: dict[str, np.ndarray] | None = None
    expected_dirs = {(model, seed) for model in models for seed in SEEDS}
    for model in models:
        for seed in SEEDS:
            folder = run_root / model / f"seed-{seed}"
            rec, p = verify_run(folder, data, expected_models=models, expected_origins=origin_count)
            if (model, seed) not in expected_dirs:
                raise ValueError(f"Unexpected run: {model}/seed-{seed}")
            key_arrays = {name: p[name] for name in ("origins", "node_ids", "y_true", "target_event",
                                                       "rule_trigger", "target_timestamps_ns", "origin_cutoff_ns")}
            if reference_keys is None:
                reference_keys = key_arrays
            else:
                for name, arr in key_arrays.items():
                    if not np.array_equal(arr, reference_keys[name]):
                        raise ValueError(f"Cross-run key/label mismatch ({name}) at {folder}")
            if reference is None:
                reference = p
            errors[model][seed] = np.abs(p["y_true"].astype(np.float64) - p["y_pred"].astype(np.float64))
            records.append(rec)

    if len(records) != len(expected_dirs):
        raise ValueError(f"Incomplete run matrix for {site}: {len(records)}/{len(expected_dirs)}")
    full, shared = models
    n_nodes = int(len(reference["node_ids"]))
    node_names = [str(x) for x in reference["node_ids"].tolist()]
    mean_errors = {
        model: np.mean([errors[model][seed] for seed in SEEDS], axis=0)
        for model in models
    }

    def summarize(mask: np.ndarray, omitted_node: str | None) -> dict:
        a = mean_errors[full][:, :, mask].mean()
        b = mean_errors[shared][:, :, mask].mean()
        # Positive values mean the node-specific gate has lower MAE.
        return {
            "omitted_node": omitted_node,
            "evaluated_nodes": int(mask.sum()),
            "mrg_full_mae": float(a),
            "mrg_shared_gate_mae": float(b),
            "shared_minus_node_gate_mae": float(b - a),
            "relative_node_gate_improvement_pct": float(100.0 * (b - a) / b),
        }

    rows = [summarize(np.ones(n_nodes, dtype=bool), None)]
    for i, node in enumerate(node_names):
        mask = np.ones(n_nodes, dtype=bool)
        mask[i] = False
        rows.append(summarize(mask, node))
    return {
        "site_protocol": site,
        "dataset_sha256": expected_digest,
        "verified_runs": len(records),
        "expected_runs": len(expected_dirs),
        "keys_per_run": int(reference["y_true"].size),
        "node_ids": node_names,
        "per_seed_mae": [r for r in records],
        "all_nodes_and_leave_one_node_out": rows,
        "sensitivity_classification": "post-hoc, same historical test period; descriptive, no new independent sample",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jpl-root", type=Path, required=True,
                        help="SG-EXP-028 bundle extracted/ directory")
    parser.add_argument("--out", type=Path, required=True,
                        help="New output directory; existing directory is never overwritten")
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError(f"Refusing to overwrite: {args.out}")

    from evcs_station_graph.eventtime.data import FrozenData

    sg006_data = ROOT / "outputs/visibility/SG-DATA-006-eventtime-v1/dataset.npz"
    sg006 = FrozenData(sg006_data)
    if sg006.digest != EXPECTED_SG006:
        raise ValueError("SG-DATA-006 frozen tensor identity mismatch")

    jpl_manifest = json.loads((args.jpl_root / "BUNDLE_MANIFEST.json").read_text())
    jpl_data_path = args.jpl_root / "data/jpl/dataset.npz"
    jpl_run_root = args.jpl_root / "results/formal"
    if jpl_manifest.get("data/jpl/dataset.npz") != sha256(jpl_data_path):
        raise ValueError("JPL frozen dataset differs from the bundle manifest")
    archive = args.jpl_root.parent / "SG-EXP-028-20261005T065256Z.tar.gz"
    archive_sha_file = archive.with_suffix(".sha256")
    if not archive.is_file() or not archive_sha_file.is_file():
        raise FileNotFoundError("JPL recovery archive or its SHA256 record is missing")
    archive_sha_record = archive_sha_file.read_text().split()[0]
    if sha256(archive) != archive_sha_record:
        raise ValueError("JPL recovery archive SHA256 mismatch")

    sg027 = evaluate_site(
        "SG-EXP-027 / Caltech event-time gate control", sg006_data,
        ROOT / "outputs/experiments/SG-EXP-027/recovered/formal", SG027_MODELS,
        EXPECTED_SG006, 17714,
    )
    jpl = evaluate_site(
        "SG-EXP-028 / JPL refit gate control", jpl_data_path,
        jpl_run_root, ("mrg_full", "mrg_shared_gate"), EXPECTED_JPL, 15816,
    )
    result = {
        "analysis": "paired all-node and leave-one-node-out sensitivity of the node-specific gate",
        "status": "PASS",
        "script_sha256": sha256(Path(__file__)),
        "jpl_bundle_manifest_sha256": sha256(args.jpl_root / "BUNDLE_MANIFEST.json"),
        "jpl_recovery_archive_sha256": archive_sha_record,
        "sg027": sg027,
        "jpl": jpl,
        "interpretation_limit": "Post-hoc robustness reanalysis on already observed historical test periods; no new data, model fit, independent site, or confirmatory significance test.",
    }
    args.out.mkdir(parents=True)
    (args.out / "sensitivity.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    csv_rows = []
    for site_name, site in (("sg027", sg027), ("jpl", jpl)):
        for row in site["all_nodes_and_leave_one_node_out"]:
            csv_rows.append({"site": site_name, **row})
    import csv
    with (args.out / "leave_one_node_out.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(csv_rows[0]))
        writer.writeheader()
        writer.writerows(csv_rows)
    print(json.dumps({
        "status": "PASS",
        "runs_verified": sg027["verified_runs"] + jpl["verified_runs"],
        "sg027_full_improvement_pct": sg027["all_nodes_and_leave_one_node_out"][0]["relative_node_gate_improvement_pct"],
        "sg027_leave_one_out_min_pct": min(r["relative_node_gate_improvement_pct"] for r in sg027["all_nodes_and_leave_one_node_out"][1:]),
        "jpl_full_improvement_pct": jpl["all_nodes_and_leave_one_node_out"][0]["relative_node_gate_improvement_pct"],
        "jpl_leave_one_out_min_pct": min(r["relative_node_gate_improvement_pct"] for r in jpl["all_nodes_and_leave_one_node_out"][1:]),
        "out": str(args.out),
    }, indent=2))


if __name__ == "__main__":
    main()
