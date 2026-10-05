#!/usr/bin/env python3
"""Isolated SG-EXP-028 JPL runner; test exports are gated on all 12 locked checkpoints."""
from __future__ import annotations

import argparse
from collections import deque
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from evcs_station_graph.eventtime import runner  # noqa: E402
from evcs_station_graph.eventtime.models import build_model, count_parameters  # noqa: E402
from evcs_station_graph.jpl_eventtime.data import (  # noqa: E402
    DATA_SHA256, FrozenJPLData, sha256,
)

EXPERIMENT = "SG-EXP-028"
PROTOCOL = "SG-DATA-007-jpl-eventtime-v1"
MODELS = ("mrg_full", "tcn_wide", "agcrn_full", "mrg_shared_gate")
SEEDS = (2024, 2025, 2026)
DATA_PATH = ROOT / "data/jpl/dataset.npz"
PROTOCOL_PATH = ROOT / "metadata/SG-DATA-007-protocol.json"
DATA_SPEC_PATH = ROOT / "configs/SG-DATA-007-data.json"
EXPERIMENT_SPEC_PATH = ROOT / "configs/SG-EXP-028-experiment.json"
FREEZE_PATH = ROOT / "metadata/JPL-validation-freeze-20261005.json"
MANIFEST_PATH = ROOT / "BUNDLE_MANIFEST.json"


def json_bytes(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def verify_bundle() -> dict:
    manifest = load_json(MANIFEST_PATH)
    for rel, expected in manifest.items():
        path = ROOT / rel
        if not path.is_file() or sha256(path) != expected:
            raise ValueError(f"Bundle file is missing or changed: {rel}")
    if sha256(DATA_PATH) != DATA_SHA256:
        raise ValueError("Packaged JPL dataset does not match the frozen SHA256")
    freeze = load_json(FREEZE_PATH)
    if freeze.get("status") != "data_and_design_frozen_no_training":
        raise ValueError("The frozen design record is missing or has an unexpected status")
    if freeze.get("protocol") != PROTOCOL or freeze.get("experiment") != EXPERIMENT:
        raise ValueError("JPL freeze record identity mismatch")
    frozen_map = {
        "configs/data/SG-DATA-007-jpl-eventtime-v1.json": DATA_SPEC_PATH,
        "configs/experiments/SG-EXP-028-jpl-independent-site.json": EXPERIMENT_SPEC_PATH,
        "docs/thesis/SG-EXP-028-jpl-independent-site-validation.md": ROOT / "metadata/SG-EXP-028-validation.md",
    }
    for rel in (
        "src/evcs_station_graph/eventtime/models.py",
        "src/evcs_station_graph/eventtime/gate_control.py",
        "src/evcs_station_graph/eventtime/runner.py",
        "src/evcs_station_graph/models/graph.py",
        "src/evcs_station_graph/models/tcn.py",
        "src/evcs_station_graph/models/common.py",
    ):
        frozen_map[rel] = ROOT / rel
    required_frozen = {
        "configs/data/SG-DATA-007-jpl-eventtime-v1.json",
        "configs/experiments/SG-EXP-028-jpl-independent-site.json",
        "docs/thesis/SG-EXP-028-jpl-independent-site-validation.md",
        "src/evcs_station_graph/eventtime/models.py",
        "src/evcs_station_graph/eventtime/gate_control.py",
        "src/evcs_station_graph/eventtime/runner.py",
        "src/evcs_station_graph/models/graph.py",
        "src/evcs_station_graph/models/tcn.py",
        "src/evcs_station_graph/models/common.py",
    }
    for original in required_frozen:
        expected = freeze["frozen_files"][original]
        packaged = frozen_map.get(original, ROOT / original)
        if not packaged.is_file() or sha256(packaged) != expected:
            raise ValueError(f"Frozen source hash mismatch in upload bundle: {original}")
    if sha256(ROOT / "metadata/SG-DATA-007-source-manifest.json") != freeze["data_manifest_sha256"]:
        raise ValueError("Packaged source/data manifest differs from the frozen data manifest")
    return manifest


def validate_training_spec() -> dict:
    spec = load_json(EXPERIMENT_SPEC_PATH)
    training = spec["training"]
    expected = {
        "optimizer": "AdamW", "learning_rate": 0.001, "weight_decay": 0.0001,
        "batch_size": 256, "max_epochs": 60, "patience": 8,
        "loss": "standardized_L1", "selection": "tuning MAE in original proxy units",
        "gradient_clip": 5, "precision": "float32", "deterministic": True,
        "num_workers": 0, "threads": 2,
    }
    if spec.get("experiment_id") != EXPERIMENT or spec.get("protocol_id") != PROTOCOL:
        raise ValueError("Frozen experiment/protocol identity mismatch")
    if spec.get("primary_models") != list(MODELS[:3]) or spec.get("secondary_models") != [MODELS[3]]:
        raise ValueError("Frozen model list mismatch")
    if spec.get("seeds") != list(SEEDS) or spec.get("planned_runs") != 12:
        raise ValueError("Frozen 12-run seed plan mismatch")
    if training != expected:
        raise ValueError("Runner training defaults differ from the frozen SG-EXP-028 config")
    return spec


def resolved_config(model: str, seed: int, *, smoke: bool = False) -> dict:
    validate_training_spec()
    cfg = runner.default_config(model, seed, smoke=smoke)
    cfg.update(
        protocol=PROTOCOL,
        experiment=EXPERIMENT,
        jpl_dataset_sha256=DATA_SHA256,
        jpl_loader_sha256=sha256(ROOT / "src/evcs_station_graph/jpl_eventtime/data.py"),
        jpl_entrypoint_sha256=sha256(Path(__file__)),
        jpl_protocol_sha256=sha256(PROTOCOL_PATH),
        jpl_data_spec_sha256=sha256(DATA_SPEC_PATH),
        jpl_experiment_spec_sha256=sha256(EXPERIMENT_SPEC_PATH),
        jpl_bundle_manifest_sha256=sha256(MANIFEST_PATH),
    )
    return cfg


def smoke_config() -> dict:
    cfg = resolved_config("mrg_full", 2024, smoke=True)
    cfg.update(max_epochs=2, patience=2, batch_size=4, train_limit=16, eval_limit=8,
               mode="SMOKE_NOT_SCIENTIFIC_EVIDENCE")
    return cfg


def preflight() -> None:
    manifest = verify_bundle()
    spec = validate_training_spec()
    data = FrozenJPLData(DATA_PATH)
    if data.digest != spec["dataset_sha256"]:
        raise ValueError("Dataset hash differs between frozen experiment config and tensor")
    params = {}
    for name in MODELS:
        model = build_model(name, data.arrays["graphs"])
        params[name] = count_parameters(model)
    print(json.dumps({
        "status": "preflight_passed_no_training",
        "protocol": PROTOCOL,
        "dataset_sha256": data.digest,
        "dataset_shape": list(data.arrays["features"].shape),
        "origin_counts": {s: int(len(data.arrays[f"{s}_origins"])) for s in ("train", "tuning", "calibration", "test")},
        "mature_fit_prefix_end": data.fit_prefix_end,
        "models": list(MODELS), "trainable_parameters": params,
        "bundle_file_count": len(manifest),
        "test_predictions_created": False,
        "training_performed": False,
    }, indent=2), flush=True)


def run_one(model: str, seed: int, out: Path, *, smoke: bool = False, resume: bool = False) -> None:
    if model not in MODELS or seed not in SEEDS:
        raise ValueError("Run is outside the frozen JPL model/seed matrix")
    data = FrozenJPLData(DATA_PATH)
    if smoke:
        if model != "mrg_full" or seed != 2024:
            raise ValueError("The frozen smoke is mrg_full/seed-2024 only")
        cfg = smoke_config()
    else:
        cfg = resolved_config(model, seed)
    runner.train(data, cfg, out, device="cuda", resume=resume)


def output_path(results: Path, model: str, seed: int, stage: str = "formal") -> Path:
    return results / stage / model / f"seed-{seed}"


def run_smoke(results: Path) -> None:
    preflight()
    if not __import__("torch").cuda.is_available():
        raise RuntimeError("GPU smoke requested but CUDA is unavailable; refusing CPU fallback")
    out = output_path(results, "mrg_full", 2024, "smoke")
    run_one("mrg_full", 2024, out, smoke=True)
    import torch
    data = FrozenJPLData(DATA_PATH)
    cfg = smoke_config()
    last = torch.load(out / "last.pt", map_location="cpu", weights_only=True)
    expected_contract = runner.contract(data, cfg, "cuda")
    if not last.get("complete") or last.get("contract") != expected_contract:
        raise ValueError("GPU smoke checkpoint is incomplete or violates the frozen contract")
    marker = {"status": "passed", "experiment": EXPERIMENT, "protocol": PROTOCOL,
              "model": "mrg_full", "seed": 2024, "contract": expected_contract,
              "checkpoint_sha256": sha256(out / "last.pt"),
              "dataset_sha256": data.digest, "uses_test_split": False}
    marker_path = results / "smoke/gpu_smoke_passed.json"
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    marker_path.write_bytes(json_bytes(marker))
    print(json.dumps({"status": "gpu_smoke_complete", "output": str(out),
                      "test_predictions_created": False, "formal_runs_started": False}, indent=2), flush=True)


def require_gpu_smoke(results: Path) -> None:
    import torch
    marker_path = results / "smoke/gpu_smoke_passed.json"
    if not marker_path.is_file():
        raise RuntimeError("Formal execution blocked: first complete the frozen GPU smoke")
    marker = load_json(marker_path)
    out = output_path(results, "mrg_full", 2024, "smoke")
    data = FrozenJPLData(DATA_PATH)
    expected = runner.contract(data, smoke_config(), "cuda")
    last_path = out / "last.pt"
    last = torch.load(last_path, map_location="cpu", weights_only=True)
    if (marker.get("status") != "passed" or marker.get("protocol") != PROTOCOL or
            marker.get("dataset_sha256") != DATA_SHA256 or marker.get("uses_test_split") is not False or
            marker.get("contract") != expected or marker.get("checkpoint_sha256") != sha256(last_path) or
            not last.get("complete") or last.get("contract") != expected):
        raise ValueError("GPU smoke evidence is stale, incomplete, or bound to another package/data contract")


def parse_gpus(value: str) -> tuple[int, ...]:
    try:
        ids = tuple(int(item.strip()) for item in value.split(",") if item.strip())
    except ValueError as exc:
        raise ValueError("GPU IDs must be comma-separated non-negative integers") from exc
    if not ids or len(set(ids)) != len(ids) or any(gpu < 0 for gpu in ids):
        raise ValueError("Supply one or more distinct non-negative GPU IDs")
    return ids


def train_matrix(results: Path, gpu_ids: tuple[int, ...], resume: bool) -> None:
    import torch
    if not torch.cuda.is_available():
        raise RuntimeError("Formal JPL training requires CUDA; refusing CPU fallback")
    results.mkdir(parents=True, exist_ok=True)
    matrix = [dict(model=model, seed=seed) for model in MODELS for seed in SEEDS]
    matrix_path = results / "frozen_run_matrix.json"
    matrix_bytes = json_bytes({"experiment": EXPERIMENT, "protocol": PROTOCOL,
                               "dataset_sha256": DATA_SHA256, "runs": matrix})
    if matrix_path.exists() and matrix_path.read_bytes() != matrix_bytes:
        raise ValueError("Existing run matrix differs; refusing overwrite")
    matrix_path.write_bytes(matrix_bytes)
    logs = results / "worker_logs"
    logs.mkdir(exist_ok=True)
    pending = deque(matrix)
    active = {}

    def launch(gpu: int, item: dict) -> None:
        model, seed = item["model"], item["seed"]
        log_path = logs / f"{model}-seed-{seed}-gpu-{gpu}.log"
        log = log_path.open("a", encoding="utf-8")
        env = os.environ.copy()
        env["CUDA_VISIBLE_DEVICES"] = str(gpu)
        env.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
        command = [sys.executable, str(Path(__file__).resolve()), "_train-one",
                   "--model", model, "--seed", str(seed), "--out",
                   str(output_path(results, model, seed)), "--resume"]
        if not resume:
            command.remove("--resume")
        process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=log,
                                   stderr=subprocess.STDOUT, text=True)
        active[gpu] = (process, log, item)
        print(json.dumps({"event": "started", **item, "gpu": gpu,
                          "log": str(log_path)}), flush=True)

    try:
        for gpu in gpu_ids:
            if pending:
                launch(gpu, pending.popleft())
        finished = 0
        while active:
            progressed = False
            for gpu, (process, log, item) in list(active.items()):
                code = process.poll()
                if code is None:
                    continue
                progressed = True
                log.close()
                del active[gpu]
                if code != 0:
                    raise RuntimeError(f"JPL run failed: {item}, GPU={gpu}, exit={code}")
                finished += 1
                print(json.dumps({"event": "completed", **item, "gpu": gpu,
                                  "completed": finished, "total": len(matrix)}), flush=True)
                if pending:
                    launch(gpu, pending.popleft())
            if not progressed:
                time.sleep(1)
    except BaseException:
        for child, child_log, _ in active.values():
            child.terminate()
        for child, child_log, _ in active.values():
            try:
                child.wait(timeout=30)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
            child_log.close()
        raise


def checkpoint_contract(data: FrozenJPLData, model: str, seed: int, out: Path) -> dict:
    import torch
    cfg = resolved_config(model, seed)
    if not (out / "best.pt").is_file() or not (out / "last.pt").is_file():
        raise FileNotFoundError(f"Missing checkpoints for {model}/seed-{seed}")
    expected = runner.contract(data, cfg, "cuda")
    last = torch.load(out / "last.pt", map_location="cpu", weights_only=True)
    best = torch.load(out / "best.pt", map_location="cpu", weights_only=True)
    if not last.get("complete") or last.get("contract") != expected or best.get("contract") != expected:
        raise ValueError(f"Incomplete or mismatched checkpoint: {model}/seed-{seed}")
    return {"model": model, "seed": seed, "contract": expected,
            "best_sha256": sha256(out / "best.pt"), "last_sha256": sha256(out / "last.pt"),
            "best_epoch": int(best["epoch"])}


def export_matrix(results: Path) -> None:
    data = FrozenJPLData(DATA_PATH)
    records = [checkpoint_contract(data, model, seed, output_path(results, model, seed))
               for model in MODELS for seed in SEEDS]
    lock_path = results / "checkpoint_lock.json"
    lock_bytes = json_bytes({"status": "all_12_best_checkpoints_locked_before_test_export",
                             "experiment": EXPERIMENT, "protocol": PROTOCOL,
                             "dataset_sha256": data.digest, "runs": records})
    if lock_path.exists() and lock_path.read_bytes() != lock_bytes:
        raise ValueError("Checkpoint lock exists but differs from current checkpoints")
    lock_path.write_bytes(lock_bytes)
    # Recheck all checkpoint hashes immediately before the first test split is read.
    locked = load_json(lock_path)
    for record in locked["runs"]:
        out = output_path(results, record["model"], record["seed"])
        if sha256(out / "best.pt") != record["best_sha256"] or sha256(out / "last.pt") != record["last_sha256"]:
            raise ValueError("A checkpoint changed after the all-run lock was created")
    state_path = results / "test_export_state.json"
    state = load_json(state_path) if state_path.exists() else {
        "status": "test_export_in_progress", "runs": {},
    }

    def save_state() -> None:
        tmp = state_path.with_suffix(".json.tmp")
        tmp.write_bytes(json_bytes(state))
        os.replace(tmp, state_path)

    def complete_artifacts(out: Path) -> bool:
        return all((out / name).is_file() for name in (
            "predictions_tuning.npz", "predictions_calibration.npz", "predictions_test.npz",
            "metrics.json", "manifest.json", "exit_code.txt", "run_summary.json",
        ))

    for model in MODELS:
        for seed in SEEDS:
            key = f"{model}/seed-{seed}"
            out = output_path(results, model, seed)
            status = state["runs"].get(key, {}).get("status")
            if status == "complete":
                if not complete_artifacts(out):
                    raise ValueError(f"Previously exported run is missing artifacts: {key}; refusing repeat evaluation")
                continue
            if status == "started":
                if complete_artifacts(out):
                    state["runs"][key] = {"status": "complete", "recovered_without_reexport": True}
                    save_state()
                    continue
                raise ValueError(f"Export was interrupted for {key}; refusing to evaluate its test set twice")
            state["runs"][key] = {"status": "started"}
            save_state()  # A crash after this point cannot silently trigger a second test evaluation.
            runner.export(data, resolved_config(model, seed), out, device="cuda")
            if not complete_artifacts(out):
                raise RuntimeError(f"Export artifacts incomplete for {key}")
            state["runs"][key] = {"status": "complete",
                                  "test_prediction_sha256": sha256(out / "predictions_test.npz"),
                                  "metrics_sha256": sha256(out / "metrics.json")}
            save_state()
    state["status"] = "all_12_test_exports_completed_once"
    save_state()
    print(json.dumps({"status": "all_12_exported_after_checkpoint_lock",
                      "test_exports": 12, "lock": str(lock_path)}, indent=2), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("preflight", help="hash/schema/architecture check only; no training or test predictions")
    commands.add_parser("smoke", help="small GPU smoke using train/tuning only; not scientific evidence")
    suite = commands.add_parser("run-suite", help="run the frozen 12-run matrix then gated exports")
    suite.add_argument("--gpus", default="0", help="distinct visible physical GPU IDs")
    suite.add_argument("--results", type=Path, default=ROOT / "results")
    suite.add_argument("--resume", action="store_true")
    one = commands.add_parser("_train-one", help=argparse.SUPPRESS)
    one.add_argument("--model", choices=MODELS, required=True)
    one.add_argument("--seed", type=int, choices=SEEDS, required=True)
    one.add_argument("--out", type=Path, required=True)
    one.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.command == "preflight":
        preflight()
    elif args.command == "smoke":
        run_smoke(ROOT / "results")
    elif args.command == "_train-one":
        data = FrozenJPLData(DATA_PATH)
        run_one(args.model, args.seed, args.out, resume=args.resume)
    elif args.command == "run-suite":
        verify_bundle()
        require_gpu_smoke(args.results)
        train_matrix(args.results, parse_gpus(args.gpus), args.resume)
        export_matrix(args.results)


if __name__ == "__main__":
    main()
