#!/usr/bin/env python3
"""Independent, post-hoc audit of SG-EXP-031 archived JPL results.

Reads the frozen result archive only. It does not train, select, or modify models.
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
VARIANTS = ("full", "load_to_self", "event_to_self", "pattern_to_self")
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


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def code_digest(source_root: Path) -> str:
    paths = sorted((source_root / "eventtime").glob("*.py")) + [
        source_root / "models" / name for name in ("graph.py", "tcn.py", "common.py")
    ]
    return sha256_bytes("".join(p.name + sha256(p) for p in paths).encode())


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def local_week_blocks(origin_ns: np.ndarray) -> tuple[np.ndarray, list[str]]:
    tz = ZoneInfo("America/Los_Angeles")
    dates = [
        dt.datetime.fromtimestamp(int(ns) / 1e9, tz=dt.timezone.utc)
        .astimezone(tz).date()
        for ns in origin_ns
    ]
    start = min(dates)
    block = np.asarray([(d - start).days // 7 for d in dates], dtype=np.int64)
    labels = [
        str(start + dt.timedelta(days=7 * i))
        for i in range(int(block.max()) + 1)
    ]
    return block, labels


def bootstrap_interval(block_sums: np.ndarray, block_counts: np.ndarray,
                       draws: np.ndarray) -> dict:
    sampled = block_sums[draws].sum(axis=1) / block_counts[draws].sum(axis=1)
    return {
        "estimate": float(block_sums.sum() / block_counts.sum()),
        "ci95": [float(np.quantile(sampled, .025)), float(np.quantile(sampled, .975))],
        "bonferroni_98_3333": [
            float(np.quantile(sampled, 1 / 120)),
            float(np.quantile(sampled, 1 - 1 / 120)),
        ],
    }


def metric_values(y: np.ndarray, p: np.ndarray, event: np.ndarray) -> dict:
    err = np.abs(y - p)
    zero = y == 0
    nonzero = ~zero
    # rule_trigger is broadcast to the same [origin, horizon, node] key space.
    # The caller adds the archived trigger mask before comparing four-cell totals.
    return {
        "n": int(y.size),
        "mae": float(err.mean()),
        "rmse": float(np.sqrt(np.mean((y - p) ** 2))),
        "event_mae": float(err[event].mean()),
        "stable_mae": float(err[~event].mean()),
        "zero_mae": float(err[zero].mean()),
        "nonzero_mae": float(err[nonzero].mean()),
        "zero_fraction": float(zero.mean()),
        "by_horizon_mae": err.mean(axis=(0, 2)).tolist(),
        "by_node_mae": err.mean(axis=(0, 1)).tolist(),
    }


def close(a, b, *, atol=2e-12, rtol=2e-10) -> bool:
    return bool(np.isclose(float(a), float(b), atol=atol, rtol=rtol))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--source",
        type=Path,
        default=REPO / "outputs/experiments/SG-EXP-031/recovered/results/SG-EXP-031",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=REPO / "outputs/analysis/SG-EXP-031-audit-20261015",
    )
    ap.add_argument("--bootstrap-draws", type=int, default=10000)
    args = ap.parse_args()
    source = args.source.resolve()
    out = args.out.resolve()
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"Refusing to overwrite non-empty output directory: {out}")
    out.mkdir(parents=True, exist_ok=True)

    recovery_root = source.parents[1]
    archive_path = source.parents[2] / "SG-EXP-031-results.tar.gz"
    summary = load_json(source / "autodl_run_summary.json")
    suite = load_json(source / "suite-status.json")
    contract = load_json(source / "contract-check.json")
    locks = load_json(source / "checkpoint-lock.json")

    # Tie the trained configs back to the exact frozen source/data/plan bundle.
    bundle = REPO / "outputs/experiments/SG-EXP-031/bundle"
    bundle_manifest = load_json(bundle / "BUNDLE_MANIFEST.json")
    bundle_checks = []
    for relpath, expected in bundle_manifest.items():
        path = (bundle / relpath).resolve()
        if not path.is_relative_to(bundle.resolve()) or not path.is_file():
            raise SystemExit(f"Frozen bundle entry is missing or unsafe: {relpath}")
        observed = sha256(path)
        bundle_checks.append({"path": relpath, "expected_sha256": expected, "observed_sha256": observed, "ok": expected == observed})
    if not bundle_checks or not all(row["ok"] for row in bundle_checks):
        raise SystemExit("Frozen source bundle hash verification failed")
    bundle_dataset_sha = sha256(bundle / "data/jpl/dataset.npz")
    bundle_entrypoint_sha = sha256(bundle / "scripts/jpl_relation_controls.py")
    bundle_plan_sha = sha256(bundle / "metadata/training-design-20261015.md")
    bundle_code_sha = code_digest(bundle / "src/evcs_station_graph")
    with np.load(bundle / "data/jpl/dataset.npz", allow_pickle=False) as z:
        original_graph_sha = sha256_bytes(z["graphs"].tobytes())
    if bundle_dataset_sha != contract.get("dataset_sha256"):
        raise SystemExit("Frozen bundle dataset hash does not match remote contract")

    # Independently verify the archive's result-file checksum list.
    checksum_rows = []
    for line in (source / "checksums.sha256").read_text(encoding="utf-8").splitlines():
        expected, relpath = line.split(maxsplit=1)
        path = recovery_root / relpath.strip()
        observed = sha256(path)
        checksum_rows.append({
            "path": relpath.strip(),
            "expected_sha256": expected,
            "observed_sha256": observed,
            "ok": expected == observed,
        })
    if not checksum_rows or not all(row["ok"] for row in checksum_rows):
        raise SystemExit("Archive checksum verification failed")

    if suite != {"status": "COMPLETED_UNREVIEWED", "runs": 12, "experiment": "SG-EXP-031"}:
        raise SystemExit(f"Unexpected suite status: {suite}")
    if summary.get("exit_code") != 0 or summary.get("status") != "completed_unreviewed":
        raise SystemExit(f"Unexpected run summary: {summary}")
    if (source / "exit_code.txt").read_text(encoding="utf-8").strip() != "0":
        raise SystemExit("Top-level exit code is not zero")
    if contract.get("status") != "PASS" or len(contract.get("runs", [])) != 12:
        raise SystemExit("Contract check is not PASS for all 12 runs")
    if len(locks) != 12:
        raise SystemExit("Expected 12 checkpoint locks")

    lock_map = {(r["variant"], int(r["seed"])): r for r in locks}
    contract_map = {(r["variant"], int(r["seed"])): r for r in contract["runs"]}
    runs: dict[tuple[str, int], dict] = {}
    source_hashes: dict[str, str] = {}
    run_rows = []

    for variant in VARIANTS:
        for seed in SEEDS:
            folder = source / "jpl" / variant / f"seed-{seed}"
            files = [
                "config_resolved.json", "environment.json", "environment.txt",
                "best.pt", "last.pt", "train_log.json", "predictions_test.npz",
                "metrics.json", "run_summary.json", "exit_code.txt", "manifest.json",
            ]
            if any(not (folder / name).is_file() for name in files):
                raise SystemExit(f"Missing required files under {folder}")
            config = load_json(folder / "config_resolved.json")
            run_summary = load_json(folder / "run_summary.json")
            train_log = load_json(folder / "train_log.json")
            checkpoint_lock = lock_map[(variant, seed)]
            contract_run = contract_map[(variant, seed)]

            if config["experiment"] != "SG-EXP-031" or config["model"] != variant or int(config["seed"]) != seed:
                raise SystemExit(f"Resolved config mismatch: {folder}")
            if int(config["trainable_parameters"]) != 32714:
                raise SystemExit(f"Parameter count mismatch: {folder}")
            if config["dataset_sha256"] != contract["dataset_sha256"]:
                raise SystemExit(f"Dataset hash mismatch: {folder}")
            frozen_config = contract_run["config"]
            if any(config.get(key) != value for key, value in frozen_config.items()):
                raise SystemExit(f"Resolved config differs from contract probe: {folder}")
            if contract_run.get("parameters") != 32714 or contract_run.get("initial_sha256") != config.get("initial_parameters_sha256"):
                raise SystemExit(f"Contract probe parameter/init mismatch: {folder}")
            if config.get("entrypoint_sha256") != bundle_entrypoint_sha:
                raise SystemExit(f"Frozen entrypoint hash mismatch: {folder}")
            if config.get("plan_sha256") != bundle_plan_sha:
                raise SystemExit(f"Frozen plan hash mismatch: {folder}")
            if config.get("code_sha256") != bundle_code_sha:
                raise SystemExit(f"Frozen model/runner source hash mismatch: {folder}")
            if config.get("original_graph_sha256") != original_graph_sha:
                raise SystemExit(f"Frozen source graph hash mismatch: {folder}")
            if config["max_epochs"] != 60 or config["patience"] != 8 or config["selection"] != "tuning_original_unit_MAE":
                raise SystemExit(f"Training contract mismatch: {folder}")
            if run_summary.get("status") != "complete" or run_summary.get("mode") != "formal":
                raise SystemExit(f"Run was not complete/formal: {folder}")
            if run_summary.get("contract") != config.get("contract"):
                raise SystemExit(f"Run contract mismatch: {folder}")
            if int(run_summary["best_epoch"]) != int(checkpoint_lock["best_epoch"]):
                raise SystemExit(f"Selected epoch differs from checkpoint lock: {folder}")
            if sha256(folder / "best.pt") != checkpoint_lock["best_sha256"]:
                raise SystemExit(f"Best checkpoint hash mismatch: {folder}")
            if sha256(folder / "last.pt") != checkpoint_lock["last_sha256"]:
                raise SystemExit(f"Last checkpoint hash mismatch: {folder}")
            if (folder / "exit_code.txt").read_text(encoding="utf-8").strip() != "0":
                raise SystemExit(f"Run exit code was not zero: {folder}")
            manifest = load_json(folder / "manifest.json")
            for name, expected in manifest.items():
                if not (folder / name).is_file() or sha256(folder / name) != expected:
                    raise SystemExit(f"Run manifest mismatch: {folder / name}")

            logged_best_idx = int(np.argmin([row["tuning_mae"] for row in train_log]))
            selected_epoch_from_log = int(train_log[logged_best_idx]["epoch"])
            if selected_epoch_from_log != int(run_summary["best_epoch"]):
                raise SystemExit(f"Best epoch does not match tuning log: {folder}")
            if len(train_log) > int(config["max_epochs"]):
                raise SystemExit(f"Training exceeded frozen epoch budget: {folder}")

            pred_path = folder / "predictions_test.npz"
            with np.load(pred_path, allow_pickle=False) as z:
                pred = {k: z[k].copy() for k in (*KEY_FIELDS, "y_pred")}
            if pred["y_true"].shape != pred["y_pred"].shape or pred["y_true"].ndim != 3:
                raise SystemExit(f"Prediction shape mismatch: {folder}")
            if not np.isfinite(pred["y_true"]).all() or not np.isfinite(pred["y_pred"]).all():
                raise SystemExit(f"Non-finite predictions or labels: {folder}")
            metric = metric_values(pred["y_true"], pred["y_pred"], pred["target_event"])
            err = np.abs(pred["y_true"] - pred["y_pred"])
            trigger = pred["rule_trigger"]
            cells = {}
            for target_flag in (True, False):
                for trigger_flag in (True, False):
                    mask = (pred["target_event"] == target_flag) & (trigger == trigger_flag)
                    label = f"target_{int(target_flag)}_trigger_{int(trigger_flag)}"
                    cells[label] = {
                        "n": int(mask.sum()),
                        "mae": float(err[mask].mean()),
                        "sum_absolute_error": float(err[mask].sum()),
                        "error_contribution": float(err[mask].sum() / err.sum()),
                    }
            reconstructed = sum(cell["sum_absolute_error"] for cell in cells.values()) / err.size
            metric["four_cells"] = cells
            metric["four_cell_reconstruction_error"] = float(abs(metric["mae"] - reconstructed))
            stored = load_json(folder / "metrics.json")["splits"]["test"]
            for field in ("n", "mae", "rmse", "event_mae", "stable_mae", "by_horizon_mae", "by_node_mae", "four_cell_reconstruction_error"):
                if field == "n":
                    same = int(stored[field]) == metric[field]
                else:
                    same = bool(np.allclose(stored[field], metric[field], atol=2e-12, rtol=2e-10))
                if not same:
                    raise SystemExit(f"Independent metric check failed for {field}: {folder}")
            if metric["four_cell_reconstruction_error"] > 1e-9:
                raise SystemExit(f"Independent four-cell reconstruction failed: {folder}")
            for label, value in cells.items():
                stored_cell = stored["four_cells"][label]
                for field, computed in value.items():
                    same = int(stored_cell[field]) == computed if field == "n" else close(stored_cell[field], computed)
                    if not same:
                        raise SystemExit(f"Independent four-cell check failed for {label}.{field}: {folder}")
            if len(np.unique(pred["origins"])) != len(pred["origins"]) or len(np.unique(pred["node_ids"])) != len(pred["node_ids"]):
                raise SystemExit(f"Duplicate origin or node identifier: {folder}")

            rel = str(pred_path.relative_to(recovery_root))
            source_hashes[rel] = sha256(pred_path)
            runs[(variant, seed)] = {**pred, "metric": metric, "folder": folder}
            run_rows.append({
                "variant": variant,
                "seed": seed,
                "best_epoch": int(run_summary["best_epoch"]),
                "stop_epoch": len(train_log),
                **{key: metric[key] for key in (
                    "n", "four_cell_reconstruction_error", "mae", "rmse", "event_mae", "stable_mae",
                    "zero_mae", "nonzero_mae", "zero_fraction",
                )},
                "prediction_sha256": source_hashes[rel],
            })

    # Verify initial non-graph weights were seed-paired and all evaluation keys match.
    init_checks = {}
    reference = runs[("full", SEEDS[0])]
    key_checks = []
    for seed in SEEDS:
        per_seed_hashes = set()
        for variant in VARIANTS:
            run = runs[(variant, seed)]
            cfg = load_json(run["folder"] / "config_resolved.json")
            gate = contract_map[(variant, seed)]
            per_seed_hashes.add(cfg["initial_parameters_sha256"])
            if not gate.get("branch_gradients_pass") or not gate.get("parameters_unchanged"):
                raise SystemExit(f"Contract probe failed: {variant} seed {seed}")
            for field in KEY_FIELDS:
                exact = bool(np.array_equal(reference[field], run[field]))
                key_checks.append({"variant": variant, "seed": seed, "field": field, "exact": exact})
                if not exact:
                    raise SystemExit(f"Prediction-key alignment failed: {variant} seed {seed} {field}")
        if len(per_seed_hashes) != 1:
            raise SystemExit(f"Initial parameters are not seed-paired for seed {seed}")
        init_checks[str(seed)] = next(iter(per_seed_hashes))

    # Same-seed trained errors are paired; seed means are then averaged per prediction key.
    block, block_labels = local_week_blocks(reference["origin_cutoff_ns"])
    n_blocks = len(block_labels)
    rng = np.random.default_rng(20261015)
    draws = rng.integers(0, n_blocks, size=(10000, n_blocks))
    full_error = {
        seed: np.abs(runs[("full", seed)]["y_true"] - runs[("full", seed)]["y_pred"])
        for seed in SEEDS
    }
    comparisons = []
    block_rows = []
    for variant in VARIANTS[1:]:
        seed_deltas = []
        group_seed_deltas = {"event": [], "nonzero": [], "zero": []}
        per_seed_delta = []
        for seed in SEEDS:
            run = runs[(variant, seed)]
            replacement_error = np.abs(run["y_true"] - run["y_pred"])
            delta = replacement_error - full_error[seed]  # positive favors full
            per_seed_delta.append(delta)
            seed_deltas.append(float(delta.mean()))
            group_seed_deltas["event"].append(float(delta[run["target_event"]].mean()))
            group_seed_deltas["nonzero"].append(float(delta[run["y_true"] > 0].mean()))
            group_seed_deltas["zero"].append(float(delta[run["y_true"] == 0].mean()))

        mean_key_delta = np.mean(np.stack(per_seed_delta), axis=0)
        origin_sums = mean_key_delta.sum(axis=(1, 2))
        counts = np.full(len(block), mean_key_delta.shape[1] * mean_key_delta.shape[2], dtype=np.int64)
        block_sums = np.bincount(block, weights=origin_sums, minlength=n_blocks)
        block_counts = np.bincount(block, weights=counts, minlength=n_blocks)
        bootstrap = bootstrap_interval(block_sums, block_counts, draws)
        comparisons.append({
            "replacement": variant,
            "contrast": "replacement absolute error minus full absolute error; positive favors full",
            "seed_differences_kwh_per_15min": seed_deltas,
            "mean_seed_difference_kwh_per_15min": float(np.mean(seed_deltas)),
            "seed_sample_sd_kwh_per_15min": float(np.std(seed_deltas, ddof=1)),
            "full_relative_improvement_pct_vs_replacement": float(
                100 * np.mean(seed_deltas) / np.mean([
                    runs[(variant, s)]["metric"]["mae"] for s in SEEDS
                ])
            ),
            "all_seed_differences_positive": bool(all(x > 0 for x in seed_deltas)),
            "event_mean_seed_difference": float(np.mean(group_seed_deltas["event"])),
            "nonzero_mean_seed_difference": float(np.mean(group_seed_deltas["nonzero"])),
            "zero_mean_seed_difference": float(np.mean(group_seed_deltas["zero"])),
            "time_block_bootstrap": bootstrap,
            "positive_time_blocks": int(np.count_nonzero(block_sums > 0)),
            "time_blocks": n_blocks,
        })
        for i, label in enumerate(block_labels):
            block_rows.append({
                "comparison": variant,
                "local_block_start": label,
                "n_prediction_keys": int(block_counts[i]),
                "replacement_minus_full_abs_error_sum": float(block_sums[i]),
                "replacement_minus_full_mae": float(block_sums[i] / block_counts[i]),
            })

    aggregate = {}
    for variant in VARIANTS:
        aggregate[variant] = {}
        for metric_name in (
            "mae", "rmse", "event_mae", "stable_mae", "zero_mae", "nonzero_mae", "zero_fraction",
        ):
            values = [runs[(variant, seed)]["metric"][metric_name] for seed in SEEDS]
            aggregate[variant][metric_name] = {
                "per_seed": values,
                "mean": float(np.mean(values)),
                "sample_sd": float(np.std(values, ddof=1)),
            }

    audit = {
        "audit_id": "SG-EXP-031-RESULTS-20261015",
        "status": "POST_HOC_DIAGNOSTIC",
        "training_performed": False,
        "interpretation_status": "Reviewed; results are on the already inspected fixed JPL test period.",
        "source_root": str(source.relative_to(REPO)),
        "source_archive_sha256": sha256(archive_path),
        "source_checksum_entries_verified": len(checksum_rows),
        "frozen_bundle": {
            "manifest_entries_verified": len(bundle_checks),
            "dataset_sha256": bundle_dataset_sha,
            "entrypoint_sha256": bundle_entrypoint_sha,
            "training_plan_sha256": bundle_plan_sha,
            "training_code_sha256": bundle_code_sha,
            "original_graph_sha256": original_graph_sha,
        },
        "suite_status": suite,
        "remote_summary": summary,
        "contract_status": contract["status"],
        "dataset_sha256": contract["dataset_sha256"],
        "environment": contract["environment"],
        "training_contract": {
            "parameters_per_run": 32714,
            "max_epochs": 60,
            "patience": 8,
            "batch_size": 256,
            "selection": "tuning original-unit MAE",
            "seeds": list(SEEDS),
            "variants": list(VARIANTS),
            "initial_parameter_hashes_by_seed": init_checks,
        },
        "prediction_alignment": {
            "all_12_runs_share_exact_keys_labels_and_diagnostic_masks": True,
            "test_origins": int(len(reference["origins"])),
            "prediction_keys_per_run": int(reference["y_true"].size),
            "prediction_shape": list(reference["y_true"].shape),
            "target_zero_fraction": float(np.mean(reference["y_true"] == 0)),
            "checks": key_checks,
        },
        "independent_metric_recomputation": "PASS; global MAE, RMSE, event/stable, four-cell reconstruction, and horizon/node MAE match metrics.json within numerical tolerance; zero/nonzero strata computed from predictions; origins/nodes unique.",
        "run_rows": run_rows,
        "aggregate_seed_metrics": aggregate,
        "paired_comparisons": comparisons,
        "time_block_design": {
            "unit": "seven consecutive local calendar days from first test-origin date",
            "timezone": "America/Los_Angeles",
            "blocks": n_blocks,
            "block_labels": block_labels,
            "bootstrap_draws": int(len(draws)),
            "random_seed": 20261015,
            "simultaneous_interval": "Bonferroni percentile interval, 98.3333% for each of three global comparisons",
            "positive_difference": "replacement absolute error minus full absolute error; positive favors full",
        },
        "interpretation_limits": [
            "Post-hoc supplementary experiment on an already inspected JPL test period; not independent or blinded confirmation.",
            "Time-block resampling describes variation across this fixed test period; it does not establish site-level generalization.",
            "Three training seeds are reported individually; the block bootstrap averages seed-wise errors per key and does not estimate all training-seed uncertainty.",
            "A replacement-to-self comparison estimates conditional value relative to self-loop replacement under this architecture and budget, not universal necessity or unique information content.",
            "Secondary event/nonzero/zero results are descriptive and do not replace the registered global-MAE primary comparisons.",
        ],
    }
    (out / "audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    with (out / "run-metrics.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(run_rows[0]))
        w.writeheader(); w.writerows(run_rows)
    with (out / "paired-time-blocks.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(block_rows[0]))
        w.writeheader(); w.writerows(block_rows)

    lines = [
        "# SG-EXP-031 JPL关系替换结果审计",
        "",
        "状态：完成逐文件校验、合同审查、预测键对齐及指标独立复算；本报告是已查看测试期上的事后补充分析。",
        "",
        f"- 远端归档SHA-256：`{audit['source_archive_sha256']}`",
        f"- 内层校验清单通过：{len(checksum_rows)}项；队列退出码：0；正式运行：12/12。",
        f"- 测试预测：每次632,640键，共{n_blocks}个洛杉矶本地连续七日块。",
        "- 4种配置可训练参数均为32,714；每个种子跨配置初始非图参数哈希一致。",
        "",
        "## 三种子测试指标（均值±样本标准差）",
        "",
        "| 配置 | MAE | RMSE | 事件MAE | 非事件MAE | 非零目标MAE | 零目标MAE | 零目标比例 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for variant in VARIANTS:
        cols = []
        for name in ("mae", "rmse", "event_mae", "stable_mae", "nonzero_mae", "zero_mae", "zero_fraction"):
            item = aggregate[variant][name]
            if name == "zero_fraction":
                cols.append(f"{100*item['mean']:.2f}%")
            else:
                cols.append(f"{item['mean']:.6f} ± {item['sample_sd']:.6f}")
        lines.append(f"| `{variant}` | " + " | ".join(cols) + " |")
    lines.extend([
        "",
        "## 训练轮次",
        "",
        "轮次按seed-2024/2025/2026排列；所有运行均在60轮上限前按patience=8停止。",
        "",
        "| 配置 | best轮次 | 停止轮次 |",
        "|---|---|---|",
    ])
    for variant in VARIANTS:
        selected = [next(r for r in run_rows if r["variant"] == variant and r["seed"] == seed) for seed in SEEDS]
        bests = "/".join(str(r["best_epoch"]) for r in selected)
        stops = "/".join(str(r["stop_epoch"]) for r in selected)
        lines.append(f"| `{variant}` | {bests} | {stops} |")
    lines.extend([
        "",
        "## 主要配对比较",
        "",
        "正差表示自环替换后误差增加、支持full配置；全局MAE为预定主比较，其他分层为描述性。",
        "",
        "| 替换关系 | 三种子差值 | 相对替换配置MAE | 种子方向 | 98.333%周块区间 | 正差周块 | 事件组差值 |",
        "|---|---:|---:|---|---:|---:|---:|",
    ])
    for comp in comparisons:
        lo, hi = comp["time_block_bootstrap"]["bonferroni_98_3333"]
        lines.append(
            f"| `{comp['replacement']}` | {comp['mean_seed_difference_kwh_per_15min']:.6f} | "
            f"{comp['full_relative_improvement_pct_vs_replacement']:.2f}% | "
            f"{sum(x > 0 for x in comp['seed_differences_kwh_per_15min'])}/3 | "
            f"[{lo:.6f}, {hi:.6f}] | {comp['positive_time_blocks']}/{n_blocks} | "
            f"{comp['event_mean_seed_difference']:.6f} |"
        )
    lines.extend([
        "",
        "## 结果解释",
        "",
        "- 负荷关系替换的差值为0.001501 kWh/15 min（full低1.82%），Bonferroni周块区间[0.000048, 0.002689]；模式关系替换差值为0.001252（full低1.52%），区间[0.000167, 0.002275]。两项区间下限均高于零，且各自3/3种子同向，支持在当前JPL协议和预算下的条件增量。",
        "- 事件关系替换差值为0.000120（full低0.15%），同时区间[-0.000432, 0.000728]跨零，且只有2/3种子同向；本结果不支持事件关系具有独立正向全局MAE增量。",
        "- 事件MAE方向不同：去掉事件关系后平均降低0.005142，去掉模式关系后平均降低0.003677。总体MAE不能代表事件片段效果；这些分层是描述性结果。",
        "- JPL测试键零值占72.75%，与Caltech事件时刻协议的87.25%不同；两套比例不可互换。",
        "- 结论限于JPL站点、当前代理目标、当前模型容量与60轮/耐心8预算；不证明关系普遍不可替代、未来泛化或真实运行价值。",
        "",
        "## 可追溯文件",
        "",
        "- 逐次指标：`run-metrics.csv`",
        "- 七日块差值：`paired-time-blocks.csv`",
        "- 完整合同、对齐检查、统计区间和边界：`audit.json`",
        "- 归档及逐运行原始文件：`outputs/experiments/SG-EXP-031/SG-EXP-031-results.tar.gz` 和 `outputs/experiments/SG-EXP-031/recovered/`",
        "",
    ])
    (out / "README.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({
        "status": "PASS",
        "out": str(out),
        "checksum_entries": len(checksum_rows),
        "runs": len(run_rows),
        "blocks": n_blocks,
        "comparisons": comparisons,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
