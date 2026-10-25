#!/usr/bin/env python3
"""Replay SG-EXP-028 test predictions from the locked best checkpoints.

This audit performs inference only. It verifies the recovered bundle, frozen
dataset, checkpoint lock, prediction keys, archived test exports, and metrics.
It never trains a model or writes into the experiment archive.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np


DEFAULT_BUNDLE = Path(
    "/Users/xushuyuan/Documents/Codex/2026-10-05/sg-exp-028-jpl/"
    "outputs/recovered/SG-EXP-028/extracted"
)
DEFAULT_OUT = Path(__file__).resolve().parents[1] / "docs/thesis/content-review-20261011-revision/checkpoint-replay"
PREDICTION_ATOL = 5e-6
METRIC_ATOL = 5e-6


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def import_experiment(bundle: Path):
    sys.path.insert(0, str(bundle / "src"))
    module_path = bundle / "scripts/jpl_experiment.py"
    spec = importlib.util.spec_from_file_location("sgexp028_recovered_experiment", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import recovered runner: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def replay(bundle: Path) -> tuple[dict, list[dict]]:
    experiment = import_experiment(bundle)
    manifest = experiment.verify_bundle()
    experiment.validate_training_spec()
    data = experiment.FrozenJPLData(experiment.DATA_PATH)
    lock_path = bundle / "results/checkpoint_lock.json"
    state_path = bundle / "results/test_export_state.json"
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    state = json.loads(state_path.read_text(encoding="utf-8"))
    if lock.get("status") != "all_12_best_checkpoints_locked_before_test_export":
        raise ValueError("Checkpoint lock does not certify all 12 best checkpoints")
    if state.get("status") != "all_12_test_exports_completed_once":
        raise ValueError("Test export state is incomplete")
    if lock.get("dataset_sha256") != data.digest:
        raise ValueError("Checkpoint lock and frozen dataset hashes differ")

    import torch
    rows: list[dict] = []
    for record in lock["runs"]:
        model_name, seed = record["model"], int(record["seed"])
        run_dir = experiment.output_path(bundle / "results", model_name, seed)
        best_path = run_dir / "best.pt"
        last_path = run_dir / "last.pt"
        exported_path = run_dir / "predictions_test.npz"
        metrics_path = run_dir / "metrics.json"
        config_path = run_dir / "config_resolved.json"
        if sha256(best_path) != record["best_sha256"] or sha256(last_path) != record["last_sha256"]:
            raise ValueError(f"Checkpoint hash differs from lock: {model_name}/seed-{seed}")
        cfg = experiment.resolved_config(model_name, seed)
        best = torch.load(best_path, map_location="cpu", weights_only=True)
        if best.get("contract") != record["contract"]:
            raise ValueError(f"Checkpoint contract mismatch: {model_name}/seed-{seed}")
        saved_cfg = json.loads(config_path.read_text(encoding="utf-8"))
        if saved_cfg.get("contract") != record["contract"]:
            raise ValueError(f"Resolved config contract mismatch: {model_name}/seed-{seed}")
        mismatched_config = [key for key, value in cfg.items() if saved_cfg.get(key) != value]
        if mismatched_config:
            raise ValueError(f"Resolved config differs from frozen runner: {model_name}/seed-{seed}: {mismatched_config}")
        if saved_cfg.get("code_sha256") != experiment.runner.code_digest():
            raise ValueError(f"Model source digest differs from resolved config: {model_name}/seed-{seed}")
        run_summary = json.loads((run_dir / "run_summary.json").read_text(encoding="utf-8"))
        if run_summary.get("contract") != record["contract"] or int(run_summary.get("best_epoch", -1)) != int(best["epoch"]):
            raise ValueError(f"Run summary differs from checkpoint lock: {model_name}/seed-{seed}")

        experiment.runner.setup(seed, "cpu", cfg.get("threads", 2))
        model = experiment.build_model(model_name, data.arrays["graphs"]).to("cpu")
        model.load_state_dict(best["model"], strict=True)
        y_true, y_pred, origins = experiment.runner.predict(model, data, "test", cfg, "cpu")
        with np.load(exported_path, allow_pickle=False) as saved:
            checks = {
                "origins_exact": np.array_equal(origins, saved["origins"]),
                "node_ids_exact": np.array_equal(data.arrays["node_ids"], saved["node_ids"]),
                "y_true_exact": np.array_equal(y_true, saved["y_true"]),
            }
            target_event, rule_trigger = data.masks(origins)
            target_indices = origins[:, None] + np.arange(1, 5)
            timestamps = data.arrays["timestamps_ns"][target_indices]
            checks["target_event_exact"] = np.array_equal(target_event, saved["target_event"])
            checks["rule_trigger_exact"] = np.array_equal(rule_trigger, saved["rule_trigger"])
            checks["target_timestamps_exact"] = np.array_equal(timestamps, saved["target_timestamps_ns"])
            checks["origin_cutoff_exact"] = np.array_equal(
                data.arrays["timestamps_ns"][origins] + 900_000_000_000,
                saved["origin_cutoff_ns"],
            )
            pred_diff = np.abs(y_pred - saved["y_pred"])
            max_pred_diff = float(np.max(pred_diff))
            checks["prediction_within_cpu_gpu_tolerance"] = max_pred_diff <= PREDICTION_ATOL

        error = y_true.astype(np.float64) - y_pred.astype(np.float64)
        recomputed = {
            "mae": float(np.mean(np.abs(error))),
            "rmse": float(np.sqrt(np.mean(np.square(error)))),
            "event_mae": float(np.mean(np.abs(error)[target_event])),
            "stable_mae": float(np.mean(np.abs(error)[~target_event])),
            "by_horizon_mae": np.mean(np.abs(error), axis=(0, 2)).tolist(),
            "by_node_mae": np.mean(np.abs(error), axis=(0, 1)).tolist(),
        }
        saved_metrics = json.loads(metrics_path.read_text(encoding="utf-8"))["splits"]["test"]
        metric_diffs = {}
        for key, value in recomputed.items():
            expected_value = saved_metrics[key]
            difference = float(np.max(np.abs(np.asarray(value) - np.asarray(expected_value))))
            metric_diffs[key] = difference
            checks[f"metric_{key}_within_tolerance"] = difference <= METRIC_ATOL
        run_state = state.get("runs", {}).get(f"{model_name}/seed-{seed}", {})
        checks["export_hash_matches_state"] = (
            run_state.get("status") == "complete"
            and run_state.get("test_prediction_sha256") == sha256(exported_path)
            and run_state.get("metrics_sha256") == sha256(metrics_path)
        )
        row = {
            "model": model_name,
            "seed": seed,
            "best_epoch": int(best["epoch"]),
            "n_test_keys": int(y_true.size),
            "checkpoint_sha256": sha256(best_path),
            "prediction_export_sha256": sha256(exported_path),
            "replayed_mae": recomputed["mae"],
            "archived_mae": float(saved_metrics["mae"]),
            "mae_abs_diff": metric_diffs["mae"],
            "max_metric_abs_diff": max(metric_diffs.values()),
            "max_prediction_abs_diff_cpu_vs_archived": max_pred_diff,
            "checks": checks,
            "status": "PASS" if all(checks.values()) else "FAIL",
        }
        rows.append(row)
        print(f"{row['status']} {model_name}/seed-{seed}: best_epoch={best['epoch']}, "
              f"MAE={recomputed['mae']:.10f}, max|Δpred|={max_pred_diff:.3g}, "
              f"max_metric_diff={row['max_metric_abs_diff']:.3g}", flush=True)

    result = {
        "status": "PASS" if len(rows) == 12 and all(row["status"] == "PASS" for row in rows) else "FAIL",
        "experiment": "SG-EXP-028",
        "protocol": "SG-DATA-007-jpl-eventtime-v1",
        "n_runs": len(rows),
        "n_test_keys_per_run": sorted({r["n_test_keys"] for r in rows}),
        "frozen_dataset_sha256": data.digest,
        "bundle_manifest_file_count": len(manifest),
        "bundle_manifest_sha256": sha256(bundle / "BUNDLE_MANIFEST.json"),
        "checkpoint_lock_sha256": sha256(lock_path),
        "test_export_state_sha256": sha256(state_path),
        "prediction_tolerance_abs": PREDICTION_ATOL,
        "metric_tolerance_abs": METRIC_ATOL,
        "inference_device": "CPU replay of checkpoints trained/exported on CUDA; tolerance accounts for backend floating-point differences",
        "cuda_training_contract_recomputed_locally": False,
        "contract_check": "best/last hashes, checkpoint lock, saved resolved config, source digest, and run summary agree; original CUDA contract is read from the frozen lock",
        "retraining_performed": False,
    }
    return result, rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, default=DEFAULT_BUNDLE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    result, rows = replay(args.bundle.resolve())
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "sgexp028_checkpoint_replay.json").write_text(
        json.dumps({**result, "runs": rows}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    with (args.out / "sgexp028_checkpoint_replay.csv").open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=[
            "model", "seed", "best_epoch", "n_test_keys", "checkpoint_sha256",
            "prediction_export_sha256", "replayed_mae", "archived_mae", "mae_abs_diff",
            "max_metric_abs_diff", "max_prediction_abs_diff_cpu_vs_archived", "status",
        ])
        writer.writeheader()
        for row in rows:
            writer.writerow({key: value for key, value in row.items() if key != "checks"})
    lines = [
        "# SG-EXP-028 检查点到论文数值复算",
        "",
        "## 结果",
        "",
        f"状态：**{result['status']}**；从12个锁定best检查点在CPU上重新推理，逐一核对归档测试预测、时间键/标签/规则掩码，并重算MAE、RMSE、分层、逐目标片和逐节点指标。",
        "",
        f"冻结JPL张量SHA-256：`{result['frozen_dataset_sha256']}`。每次运行的测试键数：{result['n_test_keys_per_run'][0]:,}。",
        f"最大预测绝对差（CPU重放对归档GPU输出）：{max(r['max_prediction_abs_diff_cpu_vs_archived'] for r in rows):.3g}；最大MAE差：{max(r['mae_abs_diff'] for r in rows):.3g}。阈值分别为{PREDICTION_ATOL:g}与{METRIC_ATOL:g}。",
        "",
        "| 配置 | 种子 | best轮次 | 复算MAE | 归档MAE | 最大逐键预测差 | 结论 |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['model']} | {row['seed']} | {row['best_epoch']} | "
            f"{row['replayed_mae']:.10f} | {row['archived_mae']:.10f} | "
            f"{row['max_prediction_abs_diff_cpu_vs_archived']:.3g} | {row['status']} |"
        )
    lines += [
        "",
        "## 解释边界",
        "",
        "此次审计证明归档best检查点、冻结数据、归档逐键输出与论文指标之间可在数值容差内复算；CPU与CUDA浮点内核差异按逐预测键绝对容差处理。它不重建训练权重，也不验证另一环境能从头复现训练过程。",
        "",
        "机器可读逐运行结果见同目录JSON/CSV；复算入口为仓库脚本 `scripts/replay_sgexp028_checkpoints.py`，不写回实验归档。",
        "",
    ]
    (args.out / "sgexp028_checkpoint_replay.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote replay audit to {args.out}")


if __name__ == "__main__":
    main()
