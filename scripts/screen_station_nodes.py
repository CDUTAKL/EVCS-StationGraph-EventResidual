#!/usr/bin/env python3
"""Screen station-internal nodes using coverage, stability, and split availability.

Selection uses training and validation data only. Test-period statistics are
reported after selection and never alter the frozen node lists.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def coefficient_of_variation(values: np.ndarray) -> float:
    mean = float(np.mean(values))
    if mean <= 0:
        return math.inf
    return float(np.std(values, ddof=0) / mean)


def max_zero_run(values: np.ndarray) -> int:
    best = current = 0
    for value in values:
        if value <= 0:
            current += 1
            best = max(best, current)
        else:
            current = 0
    return best


def build_timestamp_index(timeslice_path: Path) -> list[pd.Timestamp]:
    timestamps: list[pd.Timestamp] = []
    previous = None
    for chunk in pd.read_csv(
        timeslice_path, usecols=["timestamp"], chunksize=500_000
    ):
        for value in chunk["timestamp"]:
            if value != previous:
                timestamps.append(pd.Timestamp(value))
                previous = value
    return timestamps


def split_boundaries(
    split_path: Path, timestamps: list[pd.Timestamp]
) -> tuple[dict[str, dict[str, object]], dict[str, list[int]]]:
    split_indices = json.loads(split_path.read_text(encoding="utf-8"))
    boundaries: dict[str, dict[str, object]] = {}
    for split_name in ("train", "validation", "test"):
        indices = split_indices[split_name]
        boundaries[split_name] = {
            "start_index": min(indices),
            "end_index": max(indices),
            "origin_count": len(indices),
            "start": timestamps[min(indices)],
            "end": timestamps[max(indices)],
        }
    return boundaries, split_indices


def assign_split(
    timestamps: pd.Series, boundaries: dict[str, dict[str, object]]
) -> pd.Series:
    result = pd.Series(pd.NA, index=timestamps.index, dtype="string")
    for split_name in ("train", "validation", "test"):
        start = boundaries[split_name]["start"]
        end = boundaries[split_name]["end"]
        mask = timestamps.between(start, end, inclusive="both")
        result.loc[mask] = split_name
    return result


def aggregate_timeslice(
    timeslice_path: Path, boundaries: dict[str, dict[str, object]]
) -> tuple[pd.DataFrame, pd.DataFrame, dict[tuple[str, str], set[str]]]:
    split_parts: list[pd.DataFrame] = []
    month_parts: list[pd.DataFrame] = []
    active_days: dict[tuple[str, str], set[str]] = {}
    columns = [
        "timestamp",
        "node_id",
        "load",
        "access_count",
        "departure_count",
        "active_count",
    ]
    for chunk in pd.read_csv(timeslice_path, usecols=columns, chunksize=400_000):
        chunk["timestamp"] = pd.to_datetime(chunk["timestamp"])
        chunk["split"] = assign_split(chunk["timestamp"], boundaries)
        chunk = chunk.dropna(subset=["split"])
        if chunk.empty:
            continue
        chunk["nonzero_load"] = (chunk["load"] > 0).astype("int64")
        chunk["active_state"] = (chunk["active_count"] > 0).astype("int64")
        chunk["month"] = chunk["timestamp"].dt.to_period("M").astype(str)
        grouped = (
            chunk.groupby(["split", "node_id"], observed=True)
            .agg(
                row_count=("load", "size"),
                proxy_energy=("load", "sum"),
                nonzero_load_bins=("nonzero_load", "sum"),
                active_state_bins=("active_state", "sum"),
                access_events=("access_count", "sum"),
                departure_events=("departure_count", "sum"),
            )
            .reset_index()
        )
        split_parts.append(grouped)
        monthly = (
            chunk.groupby(["split", "node_id", "month"], observed=True)
            .agg(
                monthly_proxy_energy=("load", "sum"),
                monthly_access_events=("access_count", "sum"),
                monthly_nonzero_bins=("nonzero_load", "sum"),
            )
            .reset_index()
        )
        month_parts.append(monthly)
        positive = chunk.loc[chunk["load"] > 0, ["split", "node_id", "timestamp"]]
        if not positive.empty:
            positive = positive.assign(day=positive["timestamp"].dt.strftime("%Y-%m-%d"))
            for (split_name, node_id), group in positive.groupby(
                ["split", "node_id"], observed=True
            ):
                active_days.setdefault((str(split_name), str(node_id)), set()).update(
                    group["day"].tolist()
                )
    split_metrics = (
        pd.concat(split_parts, ignore_index=True)
        .groupby(["split", "node_id"], observed=True)
        .sum(numeric_only=True)
        .reset_index()
    )
    month_metrics = (
        pd.concat(month_parts, ignore_index=True)
        .groupby(["split", "node_id", "month"], observed=True)
        .sum(numeric_only=True)
        .reset_index()
    )
    return split_metrics, month_metrics, active_days


def complete_months(start: pd.Timestamp, end: pd.Timestamp) -> list[str]:
    return [str(period) for period in pd.period_range(start, end, freq="M")]


def make_node_table(
    split_metrics: pd.DataFrame,
    month_metrics: pd.DataFrame,
    active_days: dict[tuple[str, str], set[str]],
    boundaries: dict[str, dict[str, object]],
) -> pd.DataFrame:
    nodes = sorted(split_metrics["node_id"].astype(str).unique())
    rows: list[dict[str, object]] = []
    for node_id in nodes:
        row: dict[str, object] = {"node_id": node_id}
        for split_name in ("train", "validation", "test"):
            current = split_metrics[
                (split_metrics["split"] == split_name)
                & (split_metrics["node_id"].astype(str) == node_id)
            ]
            if current.empty:
                values = {
                    "row_count": 0,
                    "proxy_energy": 0.0,
                    "nonzero_load_bins": 0,
                    "active_state_bins": 0,
                    "access_events": 0,
                    "departure_events": 0,
                }
            else:
                values = current.iloc[0].to_dict()
            total_bins = int(boundaries[split_name]["origin_count"])
            for key in (
                "row_count",
                "nonzero_load_bins",
                "active_state_bins",
                "access_events",
                "departure_events",
            ):
                row[f"{split_name}_{key}"] = int(values[key])
            row[f"{split_name}_proxy_energy"] = float(values["proxy_energy"])
            row[f"{split_name}_nonzero_bin_ratio"] = (
                int(values["nonzero_load_bins"]) / total_bins if total_bins else 0.0
            )
            row[f"{split_name}_active_state_ratio"] = (
                int(values["active_state_bins"]) / total_bins if total_bins else 0.0
            )
            row[f"{split_name}_active_days"] = len(
                active_days.get((split_name, node_id), set())
            )

            months = complete_months(
                boundaries[split_name]["start"], boundaries[split_name]["end"]
            )
            monthly = month_metrics[
                (month_metrics["split"] == split_name)
                & (month_metrics["node_id"].astype(str) == node_id)
            ].set_index("month")
            energy = monthly["monthly_proxy_energy"].reindex(months, fill_value=0).to_numpy()
            access = monthly["monthly_access_events"].reindex(months, fill_value=0).to_numpy()
            active_months = int(np.count_nonzero(access > 0))
            row[f"{split_name}_calendar_months"] = len(months)
            row[f"{split_name}_active_months"] = active_months
            row[f"{split_name}_active_month_ratio"] = (
                active_months / len(months) if months else 0.0
            )
            row[f"{split_name}_monthly_energy_cv"] = coefficient_of_variation(energy)
            row[f"{split_name}_monthly_access_cv"] = coefficient_of_variation(access)
            row[f"{split_name}_max_missing_month_run"] = max_zero_run(access)
        rows.append(row)
    return pd.DataFrame(rows)


def evaluate_rule(row: pd.Series, rule: dict[str, float]) -> tuple[bool, list[str]]:
    checks = [
        (
            row["train_access_events"] >= rule["train_min_access_events"],
            "train_access_events",
        ),
        (
            row["validation_access_events"]
            >= rule["validation_min_access_events"],
            "validation_access_events",
        ),
        (
            row["train_nonzero_load_bins"]
            >= rule["train_min_nonzero_load_bins"],
            "train_nonzero_load_bins",
        ),
        (
            row["train_active_month_ratio"]
            >= rule["train_min_active_month_ratio"],
            "train_active_month_ratio",
        ),
        (
            row["validation_active_month_ratio"]
            >= rule["validation_min_active_month_ratio"],
            "validation_active_month_ratio",
        ),
        (
            row["train_monthly_energy_cv"]
            <= rule["train_max_monthly_energy_cv"],
            "train_monthly_energy_cv",
        ),
    ]
    failures = [name for passed, name in checks if not passed]
    return not failures, failures


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--project-root", required=True, type=Path)
    args = parser.parse_args()
    if args.config.suffix.lower() != ".json":
        raise ValueError("runtime config must be JSON; YAML is retained for review")
    config = json.loads(args.config.read_text(encoding="utf-8"))
    root = args.project_root.resolve()
    inputs = {key: Path(value) for key, value in config["inputs"].items()}
    outputs = {key: root / value for key, value in config["outputs"].items()}

    timestamps = build_timestamp_index(inputs["proxy_timeslice"])
    boundaries, split_indices = split_boundaries(inputs["split_indices"], timestamps)
    split_metrics, month_metrics, active_days = aggregate_timeslice(
        inputs["proxy_timeslice"], boundaries
    )
    node_table = make_node_table(
        split_metrics, month_metrics, active_days, boundaries
    )

    primary_results = node_table.apply(
        lambda row: evaluate_rule(row, config["screening"]["primary"]), axis=1
    )
    sensitivity_results = node_table.apply(
        lambda row: evaluate_rule(row, config["screening"]["sensitivity"]), axis=1
    )
    node_table["primary_selected_train_validation"] = [
        result[0] for result in primary_results
    ]
    node_table["primary_failure_reasons"] = [
        ";".join(result[1]) for result in primary_results
    ]
    node_table["sensitivity_selected_train_validation"] = [
        result[0] for result in sensitivity_results
    ]
    node_table["sensitivity_failure_reasons"] = [
        ";".join(result[1]) for result in sensitivity_results
    ]
    test_rule = config["screening"]["test_evaluable_flag"]
    node_table["test_evaluable"] = (
        (node_table["test_access_events"] >= test_rule["min_access_events"])
        & (
            node_table["test_nonzero_load_bins"]
            >= test_rule["min_nonzero_load_bins"]
        )
    )

    for path in outputs.values():
        path.parent.mkdir(parents=True, exist_ok=True)
    node_table.to_csv(outputs["node_metrics"], index=False)
    primary = node_table[node_table["primary_selected_train_validation"]].copy()
    sensitivity = node_table[
        node_table["sensitivity_selected_train_validation"]
    ].copy()
    primary[["node_id", "test_evaluable"]].to_csv(
        outputs["primary_nodes"], index=False
    )
    sensitivity[["node_id", "test_evaluable"]].to_csv(
        outputs["sensitivity_nodes"], index=False
    )

    boundary_json = {
        split_name: {
            key: (value.isoformat() if isinstance(value, pd.Timestamp) else value)
            for key, value in values.items()
        }
        for split_name, values in boundaries.items()
    }
    identifier_audit = json.loads(
        outputs["identifier_audit"].read_text(encoding="utf-8")
    )
    identifier_summary = identifier_audit["identifier_summary"]
    manifest = {
        "screening_id": "SG-DATA-002",
        "experiment_id": config["experiment_id"],
        "selection_information_boundary": (
            "primary and sensitivity lists use train and validation metrics only; "
            "test metrics only create a post-selection evaluability flag"
        ),
        "compatibility": config["compatibility"],
        "input_sha256": {key: sha256(path) for key, path in inputs.items()},
        "split_boundaries": boundary_json,
        "split_index_counts": {key: len(value) for key, value in split_indices.items()},
        "thresholds": config["screening"],
        "counts": {
            "all_nodes": int(len(node_table)),
            "primary_selected_train_validation": int(len(primary)),
            "primary_test_evaluable": int(primary["test_evaluable"].sum()),
            "sensitivity_selected_train_validation": int(len(sensitivity)),
            "sensitivity_test_evaluable": int(sensitivity["test_evaluable"].sum()),
        },
        "quality_gates": {
            "raw_and_timeslice_node_counts_match": bool(
                identifier_summary["unique_counts"]["stationID"] == len(node_table)
            ),
            "stationID_and_EVSEID_are_exact_aliases": bool(
                identifier_summary["equality_rates"]["stationID==EVSEID"] == 1.0
            ),
            "stationID_to_spaceID_is_one_to_one": bool(
                identifier_summary["mapping_summary"]["stationID->spaceID"][
                    "one_to_one"
                ]
            ),
            "complete_cartesian_rows_per_split": bool(
                all(
                    (
                        node_table[f"{split_name}_row_count"]
                        == boundaries[split_name]["origin_count"]
                    ).all()
                    for split_name in ("train", "validation", "test")
                )
            ),
            "split_indices_are_contiguous": bool(
                all(
                    indices
                    == list(range(min(indices), max(indices) + 1))
                    for indices in split_indices.values()
                )
            ),
            "split_indices_do_not_overlap": bool(
                not (
                    set(split_indices["train"]) & set(split_indices["validation"])
                    or set(split_indices["train"]) & set(split_indices["test"])
                    or set(split_indices["validation"]) & set(split_indices["test"])
                )
            ),
            "split_time_order_is_chronological": bool(
                boundaries["train"]["end"] < boundaries["validation"]["start"]
                < boundaries["validation"]["end"] < boundaries["test"]["start"]
            ),
            "primary_selection_respects_test_boundary": True,
            "sensitivity_selection_respects_test_boundary": True,
        },
        "outputs": {key: str(path.resolve()) for key, path in outputs.items()},
    }
    outputs["screening_manifest"].write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    failure_counts = (
        node_table.loc[
            ~node_table["primary_selected_train_validation"],
            "primary_failure_reasons",
        ]
        .str.get_dummies(sep=";")
        .sum()
        .sort_values(ascending=False)
    )
    report_lines = [
        "# SG-EXP-001 节点覆盖率与跨期可用性筛选报告",
        "",
        "## 口径",
        "",
        "- 与 EXP-111 共用 `chronological_70_15_15` 时间切分。",
        "- 与既有实验共用 15 min 节点代理负荷，不重新定义负荷。",
        "- 主分析与敏感性节点清单仅依据训练集和验证集冻结。",
        "- 测试集只生成 `test_evaluable` 标记，不参与门槛选择。",
        "",
        "## 时间边界",
        "",
    ]
    for split_name, values in boundary_json.items():
        report_lines.append(
            f"- {split_name}: {values['start']} 至 {values['end']}，"
            f"{values['origin_count']} 个预测起点。"
        )
    report_lines += [
        "",
        "## 筛选结果",
        "",
        f"- 全部候选节点：{len(node_table)}",
        f"- 主分析节点（训练集与验证集冻结）：{len(primary)}",
        f"- 主分析节点中测试期可评价：{int(primary['test_evaluable'].sum())}",
        f"- 敏感性节点（训练集与验证集冻结）：{len(sensitivity)}",
        f"- 敏感性节点中测试期可评价：{int(sensitivity['test_evaluable'].sum())}",
        f"- 主分析节点：{', '.join(primary['node_id'].astype(str).tolist())}",
        f"- 敏感性节点：{', '.join(sensitivity['node_id'].astype(str).tolist())}",
        "",
        "## 主分析筛选失败原因",
        "",
    ]
    if failure_counts.empty:
        report_lines.append("- 无")
    else:
        for key, value in failure_counts.items():
            report_lines.append(f"- `{key}`：{int(value)} 个节点")
    report_lines += [
        "",
        "## 质量门禁",
        "",
    ]
    for key, value in manifest["quality_gates"].items():
        report_lines.append(f"- `{key}`：{'通过' if value else '未通过'}")
    report_lines += [
        "",
        "## 证据边界",
        "",
        "该筛选仅证明节点具备进入后续站内图模型实验的最低数据条件，"
        "不证明节点标识一定对应独立物理充电桩，也不证明统计关系等同电气拓扑。",
    ]
    outputs["report"].write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    print(json.dumps(manifest["counts"], ensure_ascii=False))


if __name__ == "__main__":
    main()
