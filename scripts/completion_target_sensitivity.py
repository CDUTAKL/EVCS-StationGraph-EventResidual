#!/usr/bin/env python3
"""SG-EXP-032: completion-time-truncated proxy-target sensitivity experiment.

The frozen SG-DATA-006 input features, split origins, graph, event labels and
prediction keys are retained. Only the retrospective proxy target and its
train-prefix per-node scaler are changed. This measures sensitivity to the
allocation rule, not measured-power accuracy.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from evcs_station_graph.data.visibility_v2 import STEP, mature_prefix_end, proxy_targets
from evcs_station_graph.eventtime.data import Windows
from evcs_station_graph.eventtime.models import build_model, count_parameters, matched_width
from evcs_station_graph.eventtime.runner import (
    default_config, environment, export, predict, setup, train, write_json,
)

EXPERIMENT = "SG-EXP-032"
PROTOCOL = "SG-DATA-006-eventtime-v1-completion-truncated-v1"
SEEDS = (2024, 2025, 2026)
MODELS = ("mrg_full", "tcn_wide")
FROZEN_PATH = ROOT / "outputs/visibility/SG-DATA-006-eventtime-v1/dataset.npz"
ALTERNATIVE_PATH = ROOT / "outputs/analysis/SG-EXP-024-proxy-engineering/alternative_reconstruction.npz"
RAW_PATH = Path(json.loads((ROOT / "configs/data/SG-DATA-006-eventtime-v1.json").read_text())["source"])
RESULT_ROOT = ROOT / "outputs/experiments/SG-EXP-032"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def json_digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False).encode()).hexdigest()


def load_arrays(path: Path):
    with np.load(path, allow_pickle=False) as f:
        return {k: f[k] for k in f.files}


def alternative_maturity(frame, grid, nodes):
    """Label availability for the alternative support, using done or disconnect.

    For each session, the support is only knowable at its effective endpoint.
    Valid doneChargingTime is inclusive at both connection and disconnection;
    missing or out-of-range values fall back to disconnectTime.
    """
    import pandas as pd

    g = np.asarray(grid, dtype=np.int64)
    node_index = {str(n): i for i, n in enumerate(nodes)}
    maturity = np.broadcast_to(g[:, None] + STEP - 1, (len(g), len(nodes))).copy()
    for row in frame.itertuples(index=False):
        node = str(row.spaceID)
        if node not in node_index:
            continue
        c, d, done = row.connectionTime, row.disconnectTime, row.doneChargingTime
        c_ns, d_ns = pd.Timestamp(c).value, pd.Timestamp(d).value
        done_ns = pd.Timestamp(done).value if pd.notna(done) else None
        valid = done_ns is not None and c_ns <= done_ns <= d_ns
        endpoint = done_ns if valid else d_ns
        lo = (c_ns - int(g[0])) // STEP
        hi = (endpoint - int(g[0]) + STEP - 1) // STEP
        if hi <= lo:
            continue
        start, end = max(0, lo), min(len(g), hi)
        if start < end:
            n = node_index[node]
            maturity[start:end, n] = np.maximum(maturity[start:end, n], endpoint)
    return maturity


class SensitivityData:
    """Minimal runner-compatible wrapper with strict source/split contracts."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.digest = digest(self.path)
        self.arrays = load_arrays(self.path)
        a = self.arrays
        self.x = ((a["features"] - a["feature_mean"]) / a["feature_std"]).astype("float32")
        self.y = ((a["targets"] - a["target_mean"]) / a["target_std"]).astype("float32")

    def windows(self, split, limit=None):
        return Windows(self, split, limit)

    def masks(self, origins):
        idx = origins[:, None] + np.arange(1, 5)[None, :]
        target = self.arrays["target_event"][idx]
        trigger = np.repeat(self.arrays["rule_trigger"][origins, None, :], 4, axis=1)
        return target, trigger


def reconstruct_alt_targets(frozen, frame):
    # Reuse the established SG-EXP-024 target implementation so the sensitivity
    # run tests the accepted support array instead of inventing a second rule.
    from audit_proxy_engineering import completion_audit

    stats, rows, original, alternative = completion_audit(
        frame, frozen["timestamps_ns"], frozen["node_ids"].astype(str).tolist())
    return stats, rows, original, alternative


def prediction_key_fingerprint(origins, node_ids, horizon=4):
    origins = np.asarray(origins, dtype=np.int64)
    nodes = np.asarray(node_ids).astype("U")
    oi = np.repeat(origins, horizon * len(nodes))
    hi = np.tile(np.repeat(np.arange(1, horizon + 1, dtype=np.int16), len(nodes)), len(origins))
    ni = np.tile(nodes, len(origins) * horizon)
    h = hashlib.sha256()
    h.update(oi.astype("<i8", copy=False).tobytes())
    h.update(hi.astype("<i2", copy=False).tobytes())
    h.update("\0".join(ni.tolist()).encode())
    return int(len(oi)), h.hexdigest()


def build_contract(out: Path):
    if out.exists():
        raise FileExistsError(f"Refusing to overwrite frozen contract output: {out}")
    import pandas as pd
    from evcs_station_graph.graphs.relations import build_relation_set

    frozen = load_arrays(FROZEN_PATH)
    altpack = load_arrays(ALTERNATIVE_PATH)
    frame = pd.read_csv(RAW_PATH)
    for col in ("connectionTime", "disconnectTime", "doneChargingTime"):
        frame[col] = pd.to_datetime(frame[col], utc=True, errors="coerce")
    frame = frame.loc[frame.spaceID.astype(str).isin(frozen["node_ids"].astype(str))].copy()

    if not np.array_equal(altpack["timestamps_ns"], frozen["timestamps_ns"]):
        raise ValueError("SG-EXP-024 alternative timestamp grid differs from SG-DATA-006")
    if not np.array_equal(altpack["node_ids"], frozen["node_ids"]):
        raise ValueError("SG-EXP-024 alternative node order differs from SG-DATA-006")
    np.testing.assert_allclose(altpack["original"], frozen["targets"], rtol=0, atol=1e-12)
    stats, session_rows, independently_reconstructed, alt = reconstruct_alt_targets(frozen, frame)
    np.testing.assert_allclose(independently_reconstructed, frozen["targets"], rtol=0, atol=1e-12)
    np.testing.assert_allclose(altpack["completion_support"], alt, rtol=0, atol=1e-12)
    if stats["max_node_energy_difference_kwh"] > 1e-7:
        raise ValueError("Completion-time reconstruction fails per-node energy conservation")

    original_maturity = frozen["label_available_at_ns"]
    alt_maturity = alternative_maturity(frame, frozen["timestamps_ns"], frozen["node_ids"])
    if np.any(alt_maturity > original_maturity):
        raise ValueError("Alternative label maturity became later than original disconnect maturity")
    train_end = 83198
    alt_fit_end = mature_prefix_end(alt_maturity, frozen["timestamps_ns"], train_end)
    old_fit_end = mature_prefix_end(original_maturity, frozen["timestamps_ns"], train_end)
    if alt_fit_end < old_fit_end:
        raise ValueError("Alternative mature train prefix is shorter than frozen original prefix")

    # Keep every original origin and event/trigger label. Verify that each
    # unchanged forecast window remains inside its original segment and mature.
    bounds = {"train": (0, 83198), "tuning": (83198, 92101),
              "calibration": (92101, 101005), "test": (101005, 118818)}
    split_counts, split_zero, split_key_hashes = {}, {}, {}
    for split, (lo, hi) in bounds.items():
        origins = frozen[f"{split}_origins"]
        if not np.array_equal(origins, load_arrays(FROZEN_PATH)[f"{split}_origins"]):
            raise ValueError(f"Original split origins changed: {split}")
        target_indices = origins[:, None] + np.arange(1, 5)[None, :]
        if np.any(origins - 95 < lo) or np.any(origins + 4 >= hi):
            raise ValueError(f"Input/target window escaped fixed split: {split}")
        if np.any(alt_maturity[target_indices] >= int(frozen["timestamps_ns"][hi - 1]) + STEP):
            raise ValueError(f"Alternative labels are not mature under original split: {split}")
        nkeys, khash = prediction_key_fingerprint(origins, frozen["node_ids"])
        split_counts[split] = {"origins": int(len(origins)), "forecast_keys": nkeys,
                               "original_zero_fraction": float(np.mean(frozen["targets"][target_indices] == 0)),
                               "completion_zero_fraction": float(np.mean(alt[target_indices] == 0)),
                               "target_event_fraction": float(np.mean(frozen["target_event"][target_indices]))}
        split_zero[split] = split_counts[split]["completion_zero_fraction"]
        split_key_hashes[split] = khash

    # Recompute original topology exactly from its documented mature train
    # prefix. Graph fitting used only training-prefix x/y, never held-out labels.
    rebuilt = np.stack(build_relation_set(frozen["features"][:old_fit_end],
                                          frozen["targets"][:old_fit_end],
                                          tuple(frozen["feature_names"]), top_k=5).as_list())
    np.testing.assert_array_equal(rebuilt, frozen["graphs"])
    graph_hash = hashlib.sha256(np.ascontiguousarray(frozen["graphs"]).tobytes()).hexdigest()

    arrays = dict(frozen)
    arrays["targets"] = alt.astype(np.float64)
    arrays["label_available_at_ns"] = alt_maturity.astype(np.int64)
    arrays["target_mean"] = alt[:alt_fit_end].mean(axis=0, dtype=np.float64)
    arrays["target_std"] = alt[:alt_fit_end].std(axis=0, dtype=np.float64)
    arrays["target_std"] = np.where(arrays["target_std"] < 1e-6, 1., arrays["target_std"])
    arrays["schema"] = np.array("SG-EXP-032-completion-truncated-target")

    out.mkdir(parents=True)
    dataset = out / "dataset.npz"
    np.savez_compressed(dataset, **arrays)
    config = {
        "experiment": EXPERIMENT, "protocol": PROTOCOL,
        "models": list(MODELS), "seeds": list(SEEDS),
        "target_rule": "Use valid doneChargingTime when connectionTime<=doneChargingTime<=disconnectTime; otherwise retain disconnectTime; equal-bin energy allocation is truncated at the effective endpoint; session kWh conserved.",
        "input_protocol": "Freeze SG-DATA-006 7-channel event-time behavior/calendar features; no proxy target or future load enters features.",
        "event_labels": "Keep SG-DATA-006 target_event and rule_trigger arrays unchanged; evaluation strata only; not training input, weighting, filtering, checkpoint selection, or seed selection.",
        "split_policy": "Exact frozen SG-DATA-006 origins and segments; exact forecast key set; conservative alternative maturity checked at every original window.",
        "graph_policy": "Freeze and hash SG-DATA-006 top-k=5 graph. Reconstructed byte-for-byte from the original mature training prefix only. This isolates target-label sensitivity at fixed topology; it does not test rebuilding topology under the alternative target.",
        "target_scaler": "Per-node mean/std recomputed from completion-truncated target in the alternative mature train prefix only.",
        "optimizer": "AdamW", "learning_rate": 0.001, "weight_decay": 0.0001,
        "batch_size": 256, "max_epochs": 60, "patience": 8,
        "selection": "full tuning MAE in original kWh/15min units",
        "precision": "float32 deterministic; TF32 off", "same_hardware": "AutoDL RTX4090 D, PyTorch2.8.0+cu128, NumPy2.3.2",
        "measurement_validation": False, "test_period_previously_viewed": True,
    }
    write_json(out / "config_frozen.json", config)
    evidence = {
        "status": "contract_frozen_pending_smoke",
        "experiment": EXPERIMENT, "input_protocol": "SG-DATA-006-eventtime-v1",
        "raw_session_sha256": digest(RAW_PATH),
        "frozen_dataset_sha256": digest(FROZEN_PATH),
        "existing_completion_support_sha256": digest(ALTERNATIVE_PATH),
        "new_dataset_sha256": digest(dataset),
        "completion_support_reconstruction": stats,
        "session_count": int(len(frame)),
        "completion_valid_inclusive": int(stats["valid_completion"]),
        "completion_missing": int(stats["missing_completion"]),
        "completion_invalid": int(stats["invalid_nonmissing_completion"]),
        "old_mature_fit_end": int(old_fit_end), "alternative_mature_fit_end": int(alt_fit_end),
        "split_counts": split_counts,
        "graph_sha256": graph_hash,
        "graph_rebuilt_from_original_train_prefix": True,
        "original_event_labels_sha256": hashlib.sha256(frozen["target_event"].tobytes()).hexdigest(),
        "feature_sha256": hashlib.sha256(frozen["features"].tobytes()).hexdigest(),
        "origin_sha256": {s: hashlib.sha256(frozen[f"{s}_origins"].tobytes()).hexdigest()
                           for s in bounds},
        "target_key_overlap_fraction_nonzero": float(np.mean((frozen["targets"] != 0) == (alt != 0))),
        "total_energy_original_kwh": float(frozen["targets"].sum()),
        "total_energy_completion_kwh": float(alt.sum()),
        "global_mean_abs_target_difference_kwh_per_slice": float(np.abs(frozen["targets"] - alt).mean()),
        "note": "Target-reconstruction difference is not model error, target uncertainty bound, or a model-vs-target MAE comparison.",
    }
    write_json(out / "contract_audit.json", evidence)
    manifest = {p.name: digest(p) for p in sorted(out.iterdir()) if p.is_file() and p.name != "manifest.json"}
    write_json(out / "manifest.json", manifest)
    return evidence


def verify_contract(bundle: Path):
    manifest = json.loads((bundle / "manifest.json").read_text())
    for name, expected in manifest.items():
        if digest(bundle / name) != expected:
            raise ValueError(f"Frozen local contract artifact hash mismatch: {name}")
    data = SensitivityData(bundle / "dataset.npz")
    counts = {m: count_parameters(build_model(m, data.arrays["graphs"])) for m in MODELS}
    width = matched_width()
    if counts != {"mrg_full": 32714, "tcn_wide": 32674}:
        raise ValueError(f"Unexpected parameter counts: {counts}; width={width}")
    expected = json.loads((bundle / "config_frozen.json").read_text())
    if expected["seeds"] != list(SEEDS) or expected["models"] != list(MODELS):
        raise ValueError("Model/seed matrix changed")
    return data, counts


def run_smoke(bundle: Path, out: Path, device="cpu"):
    import torch
    if out.exists():
        raise FileExistsError(f"Refusing to overwrite smoke output: {out}")
    data, params = verify_contract(bundle)
    cfg = default_config("mrg_full", 2024, smoke=True)
    cfg.update(experiment=EXPERIMENT, protocol=PROTOCOL, mode="CPU_CONTRACT_SMOKE_ONLY",
               max_epochs=1, batch_size=8, train_limit=32, eval_limit=16,
               completion_dataset_sha256=data.digest,
               wrapper_source_sha256=digest(Path(__file__)))
    setup(2024, device, cfg["threads"])
    folder = out / "mrg_full" / "seed-2024"
    train(data, cfg, folder, device=device, stop_after=1)
    # Smoke uses only tuning data; no calibration/test export.
    # Reload the trained best checkpoint and calculate a finite, bounded
    # tuning prediction without touching the held-out test split.
    model = build_model("mrg_full", data.arrays["graphs"]).to(device)
    ckpt = torch.load(folder / "best.pt", map_location="cpu", weights_only=True)
    model.load_state_dict(ckpt["model"], strict=True)
    y, pred, origins = predict(model, data, "tuning", cfg, device)
    if not np.isfinite(y).all() or not np.isfinite(pred).all():
        raise FloatingPointError("Nonfinite smoke prediction")
    record = {"status": "passed", "device": device, "training_not_formal": True,
              "trainable_parameters": params["mrg_full"], "train_rows": int(cfg["train_limit"]),
              "tuning_origins": int(len(origins)), "prediction_shape": list(pred.shape),
              "tuning_mae": float(np.abs(y - pred).mean()),
              "prediction_finite": True, "test_export_performed": False,
              "dataset_sha256": data.digest, "wrapper_source_sha256": digest(Path(__file__))}
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "smoke_summary.json", record)
    return record


def config_for(model, seed, data):
    cfg = default_config(model, seed, smoke=False)
    cfg.update(experiment=EXPERIMENT, protocol=PROTOCOL,
               mode="formal_completion_target_sensitivity",
               completion_dataset_sha256=data.digest,
               wrapper_source_sha256=digest(Path(__file__)),
               target_rule="completion_truncate_valid_done_else_disconnect",
               graph_sha256=hashlib.sha256(np.ascontiguousarray(data.arrays["graphs"]).tobytes()).hexdigest(),
               event_labels_sha256=hashlib.sha256(data.arrays["target_event"].tobytes()).hexdigest())
    return cfg


def run_formal(bundle: Path, out: Path, device="cuda", only_model=None, only_seed=None, resume=False):
    data, params = verify_contract(bundle)
    names = (only_model,) if only_model else MODELS
    seeds = (only_seed,) if only_seed else SEEDS
    out.mkdir(parents=True, exist_ok=True)
    for model in names:
        if model not in MODELS:
            raise ValueError(model)
        for seed in seeds:
            if seed not in SEEDS:
                raise ValueError(seed)
            cfg = config_for(model, seed, data)
            folder = out / model / f"seed-{seed}"
            train(data, cfg, folder, device=device, resume=resume)
            export(data, cfg, folder, device=device)
            print(json.dumps({"completed": f"{model}/seed-{seed}", "parameters": params[model],
                              "best_epoch": json.loads((folder / "run_summary.json").read_text())["best_epoch"]},
                             ensure_ascii=False), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=("prepare", "check", "smoke", "train", "all"))
    ap.add_argument("--bundle", type=Path, default=RESULT_ROOT / "frozen-contract")
    ap.add_argument("--out", type=Path, default=RESULT_ROOT / "formal")
    ap.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    ap.add_argument("--model", choices=MODELS)
    ap.add_argument("--seed", type=int, choices=SEEDS)
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args()
    if args.command == "prepare":
        print(json.dumps(build_contract(args.bundle), indent=2, ensure_ascii=False))
    elif args.command == "check":
        data, counts = verify_contract(args.bundle)
        print(json.dumps({"status": "contract_passed_training_not_started",
                          "data_sha256": data.digest, "models": counts,
                          "origins": {s: len(data.arrays[f"{s}_origins"])
                                      for s in ("train", "tuning", "calibration", "test")}},
                         indent=2, ensure_ascii=False))
    elif args.command == "smoke":
        print(json.dumps(run_smoke(args.bundle, args.out, args.device), indent=2, ensure_ascii=False))
    else:
        run_formal(args.bundle, args.out, args.device, args.model, args.seed, args.resume)


if __name__ == "__main__":
    main()
