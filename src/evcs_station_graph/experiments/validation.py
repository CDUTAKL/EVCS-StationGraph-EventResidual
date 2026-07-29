"""正式实验工件一致性检查。

该模块不重新计算模型指标，而是检查正式流水线是否满足进入论文证据审核的
最低条件：三随机种子齐全、预测键唯一且跨方法一致、四格结果可加权还原，
以及所有子实验均明确声明结果权威级别。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from evcs_station_graph.reproducibility import write_json


EXPECTED_SEEDS = (2024, 2025, 2026)
KEY_COLUMNS = ("split", "origin_index", "horizon", "node_id")


def validate_pipeline_artifacts(
    pipeline_root: str | Path,
    run_paths: dict[str, Path],
) -> dict[str, Any]:
    """检查 SG-EXP-002～006 的正式流水线工件并写出审计报告。"""
    root = Path(pipeline_root).expanduser().resolve()
    checks: list[dict[str, Any]] = []
    reference_fingerprint: dict[str, Any] | None = None
    baseline_manifest = _read_json(Path(run_paths["SG-EXP-002"]) / "manifest.json")
    strict_formal = baseline_manifest.get("result_authority") == "formal_candidate"
    expected_seeds = (
        EXPECTED_SEEDS
        if strict_formal
        else tuple(int(seed) for seed in baseline_manifest.get("seeds", []))
    )

    for experiment_id in ("SG-EXP-002", "SG-EXP-003", "SG-EXP-004", "SG-EXP-005"):
        run_root = Path(run_paths[experiment_id])
        manifest = _read_json(run_root / "manifest.json")
        seeds = tuple(int(seed) for seed in manifest.get("seeds", []))
        checks.append(
            _check(
                f"{experiment_id}:three_seeds",
                seeds == expected_seeds,
                {"observed": seeds, "expected": expected_seeds},
            )
        )
        checks.append(
            _check(
                f"{experiment_id}:formal_authority",
                (
                    manifest.get("result_authority") == "formal_candidate"
                    if strict_formal
                    else manifest.get("result_authority") == "implementation_smoke_only"
                ),
                {
                    "observed": manifest.get("result_authority"),
                    "strict_formal": strict_formal,
                },
            )
        )

        summary = _read_json(run_root / "metrics_summary.json")
        checks.append(
            _check(
                f"{experiment_id}:four_cell_reconstruction",
                bool(summary.get("four_cell_reconstruction_all_pass")),
                {},
            )
        )

        for seed in expected_seeds:
            seed_root = run_root / f"seed-{seed}"
            seed_manifest = _read_json(seed_root / "manifest.json")
            prediction_path = seed_root / str(seed_manifest["prediction_file"])
            fingerprint = _prediction_key_fingerprint(prediction_path)
            checks.append(
                _check(
                    f"{experiment_id}:seed-{seed}:unique_prediction_key",
                    bool(fingerprint["unique"]),
                    fingerprint,
                )
            )
            if reference_fingerprint is None:
                reference_fingerprint = fingerprint
            checks.append(
                _check(
                    f"{experiment_id}:seed-{seed}:aligned_prediction_key",
                    _same_key_space(reference_fingerprint, fingerprint),
                    {
                        "reference": _compact_fingerprint(reference_fingerprint),
                        "observed": _compact_fingerprint(fingerprint),
                    },
                )
            )

    mechanism_manifest = _read_json(Path(run_paths["SG-EXP-006"]) / "manifest.json")
    checks.append(
        _check(
            "SG-EXP-006:variant_count",
            int(mechanism_manifest.get("variant_count", 0)) == 16,
            {"observed": mechanism_manifest.get("variant_count"), "expected": 16},
        )
    )
    checks.append(
        _check(
            "SG-EXP-006:four_cell_reconstruction",
            bool(mechanism_manifest.get("four_cell_reconstruction_all_pass")),
            {},
        )
    )

    report = {
        "pipeline_root": str(root),
        "passed": all(item["passed"] for item in checks),
        "strict_formal": strict_formal,
        "formal_ready": strict_formal and all(item["passed"] for item in checks),
        "expected_seeds": list(expected_seeds),
        "prediction_key_columns": list(KEY_COLUMNS),
        "checks": checks,
    }
    write_json(report, root / "artifact_validation_report.json")
    if not report["passed"]:
        failed = [item["name"] for item in checks if not item["passed"]]
        mode = "正式" if strict_formal else "冒烟"
        raise RuntimeError(f"{mode}流水线工件检查失败：{failed}")
    return report


def _prediction_key_fingerprint(path: Path) -> dict[str, Any]:
    """计算预测键的去重状态与顺序无关指纹。"""
    frame = pd.read_csv(path, usecols=list(KEY_COLUMNS))
    hashes = pd.util.hash_pandas_object(frame.loc[:, KEY_COLUMNS], index=False).to_numpy()
    return {
        "path": str(path),
        "rows": int(len(frame)),
        "unique": not bool(frame.duplicated(list(KEY_COLUMNS)).any()),
        "hash_sum": int(hashes.sum(dtype="uint64")),
        "hash_xor": int(np.bitwise_xor.reduce(hashes)) if len(hashes) else 0,
    }


def _same_key_space(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return (
        left["rows"] == right["rows"]
        and left["hash_sum"] == right["hash_sum"]
        and left["hash_xor"] == right["hash_xor"]
    )


def _compact_fingerprint(value: dict[str, Any]) -> dict[str, Any]:
    return {key: value[key] for key in ("rows", "unique", "hash_sum", "hash_xor")}


def _check(name: str, passed: bool, details: dict[str, Any]) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "details": details}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
