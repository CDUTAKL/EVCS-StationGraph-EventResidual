#!/usr/bin/env python3
"""汇总 SG-EXP-002～006 正式流水线结果。

本脚本只读取实验产物，不修改预测、指标或模型文件。输出用于执行阶段的
快速核验，不替代后续论文级统计分析与结论审核。
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


EXPERIMENT_NAMES = {
    "SG-EXP-002": "TCN 默认时间模型",
    "SG-EXP-003": "固定站内交互图模型",
    "SG-EXP-004": "自适应图模型",
    "SG-EXP-005": "事件残差修正模型",
}
SCOPES = ("global", "event_window", "stable_window")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pipeline_root", type=Path, help="SG-PIPELINE-002-006 运行目录")
    return parser.parse_args()


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def select_mae(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for row in rows:
        if row.get("metric") != "mae" or row.get("scope") not in SCOPES:
            continue
        selected.append(
            {
                "experiment_id": row["experiment_id"],
                "experiment_name": EXPERIMENT_NAMES.get(
                    row["experiment_id"], row["experiment_id"]
                ),
                "scope": row["scope"],
                "mean": float(row["mean"]),
                "std": float(row["std"]),
                "four_cell_reconstruction_all_pass": row.get(
                    "four_cell_reconstruction_all_pass", ""
                ).lower()
                == "true",
            }
        )
    return selected


def rank_by_scope(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    return {
        scope: sorted(
            (row for row in rows if row["scope"] == scope),
            key=lambda row: row["mean"],
        )
        for scope in SCOPES
    }


def mechanism_best(rows: list[dict[str, str]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for scope in SCOPES:
        candidates = [
            row
            for row in rows
            if row.get("scope") == scope and row.get("metric") == "mae"
        ]
        if not candidates:
            continue
        best = min(candidates, key=lambda row: float(row["mean"]))
        result[scope] = {
            "variant": best["variant"],
            "mean": float(best["mean"]),
            "std": float(best["std"]),
            "four_cell_reconstruction_all_pass": best.get(
                "four_cell_reconstruction_all_pass", ""
            ).lower()
            == "true",
        }
    return result


def main() -> int:
    args = parse_args()
    root = args.pipeline_root.resolve()
    manifest_path = root / "pipeline_manifest.json"
    validation_path = root / "artifact_validation_report.json"
    metrics_path = root / "cross_experiment_metrics.csv"
    for path in (manifest_path, validation_path, metrics_path):
        if not path.is_file():
            raise FileNotFoundError(f"缺少正式流水线产物：{path}")

    manifest = read_json(manifest_path)
    validation = read_json(validation_path)
    rankings = rank_by_scope(select_mae(read_csv(metrics_path)))
    mechanism_path = Path(manifest["runs"]["SG-EXP-006"]) / "mechanism_summary.csv"
    mechanism = mechanism_best(read_csv(mechanism_path))
    failed_checks = [
        check["name"] for check in validation.get("checks", []) if not check.get("passed")
    ]

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "pipeline_root": str(root),
        "pipeline_id": manifest.get("pipeline_id"),
        "pipeline_tag": manifest.get("pipeline_tag"),
        "formal_ready": bool(validation.get("formal_ready")),
        "validation_passed": bool(validation.get("passed")),
        "failed_checks": failed_checks,
        "expected_seeds": validation.get("expected_seeds", []),
        "mae_rankings": rankings,
        "best_mechanism_variant_by_scope": mechanism,
        "interpretation_boundary": (
            "该摘要仅用于执行完成后的快速核验。正式论文结论必须继续核对逐键预测、"
            "三随机种子差异、四格样本量与统计显著性。"
        ),
    }
    (root / "automatic_result_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    scope_names = {
        "global": "全局",
        "event_window": "事件窗口",
        "stable_window": "稳定窗口",
    }
    lines = [
        "# SG-EXP-002～006 自动结果摘要",
        "",
        f"- 流水线：`{summary['pipeline_id']}` / `{summary['pipeline_tag']}`",
        f"- 正式产物就绪：`{summary['formal_ready']}`",
        f"- 产物校验通过：`{summary['validation_passed']}`",
        f"- 预期随机种子：`{summary['expected_seeds']}`",
        f"- 失败检查：`{failed_checks or '无'}`",
        "",
        "## 四个正式模型的 MAE 快速排序",
        "",
    ]
    for scope in SCOPES:
        lines.extend([f"### {scope_names[scope]}", ""])
        for index, row in enumerate(rankings[scope], start=1):
            lines.append(
                f"{index}. {row['experiment_id']} {row['experiment_name']}："
                f"{row['mean']:.8f} ± {row['std']:.8f}"
            )
        lines.append("")

    lines.extend(["## SG-EXP-006 机制变体最低 MAE", ""])
    for scope in SCOPES:
        item = mechanism.get(scope)
        if item:
            lines.append(
                f"- {scope_names[scope]}：`{item['variant']}`，"
                f"{item['mean']:.8f} ± {item['std']:.8f}"
            )
    lines.extend(["", "## 使用边界", "", summary["interpretation_boundary"], ""])
    (root / "automatic_result_summary.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["formal_ready"] and summary["validation_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
