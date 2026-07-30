"""SG-EXP-006 消融、候选关系与敏感性实验。

本模块只负责派生配置和汇总结果，不在代码中隐藏训练参数。每个子实验仍调用
统一训练入口，因此预测键、评价口径和模型保存格式与 SG-EXP-002～005 完全一致。
"""

from __future__ import annotations

import copy
import csv
import time
from pathlib import Path
from typing import Any

from evcs_station_graph.config import dump_yaml, load_experiment_config, load_yaml
from evcs_station_graph.data import TensorBundle
from evcs_station_graph.reproducibility import write_json
from evcs_station_graph.training import train_experiment


def run_mechanism_suite(
    project_path: str | Path,
    suite_path: str | Path,
    bundle: TensorBundle,
    output_root: str | Path,
    *,
    base_checkpoint: str | Path,
    overrides: tuple[str, ...] = (),
) -> Path:
    """运行 SG-EXP-006 的全部机制子实验并生成统一汇总。"""
    suite = load_yaml(suite_path)
    base_path = suite["base_experiment_config"]
    base_config = load_experiment_config(project_path, base_path, overrides)
    suite_seeds = suite.get("seeds")
    seeds_explicitly_overridden = any(
        item.split("=", 1)[0].strip() == "experiment.seeds"
        for item in overrides
        if "=" in item
    )
    if suite_seeds and not seeds_explicitly_overridden:
        if not all(isinstance(seed, int) for seed in suite_seeds):
            raise ValueError("SG-EXP-006 的随机种子必须全部为整数")
        base_config["experiment"]["seeds"] = list(suite_seeds)
    run_tag = time.strftime("%Y%m%d-%H%M%S")
    root = (
        Path(output_root).expanduser().resolve()
        / str(suite["experiment_id"])
        / run_tag
    )
    root.mkdir(parents=True, exist_ok=True)
    dump_yaml({"suite": suite, "base": base_config}, root / "config_resolved.yaml")

    variants = _build_variants(base_config, suite)
    if not variants:
        raise ValueError("SG-EXP-006 未配置任何消融、候选关系或敏感性子实验")
    rows: list[dict[str, Any]] = []
    child_runs: dict[str, str] = {}
    for variant_name, config, needs_checkpoint in variants:
        config["experiment"]["experiment_id"] = f"SG-EXP-006-{variant_name}"
        config["experiment"]["run_tag"] = run_tag
        config["experiment"]["result_authority"] = config["experiment"].get(
            "result_authority",
            suite.get("result_authority", "formal_candidate"),
        )
        child_root = train_experiment(
            config,
            bundle,
            root / "children",
            base_checkpoint=base_checkpoint if needs_checkpoint else None,
        )
        child_runs[variant_name] = str(child_root)
        summary = _read_json(child_root / "metrics_summary.json")
        rows.extend(_flatten_summary(variant_name, summary))

    _write_rows(rows, root / "mechanism_summary.csv")
    write_json(
        {
            "experiment_id": suite["experiment_id"],
            "run_tag": run_tag,
            "variant_count": len(variants),
            "child_runs": child_runs,
            "summary_csv": "mechanism_summary.csv",
            "four_cell_reconstruction_all_pass": all(
                row["four_cell_reconstruction_all_pass"] for row in rows
            ),
        },
        root / "manifest.json",
    )
    return root


def _build_variants(
    base: dict[str, Any],
    suite: dict[str, Any],
) -> list[tuple[str, dict[str, Any], bool]]:
    variants: list[tuple[str, dict[str, Any], bool]] = []
    model_without_checkpoint = {"TCN", "TCN_GCN", "adaptive_graph"}

    for name, override_map in suite.get("ablations", {}).items():
        config = copy.deepcopy(base)
        for key, value in override_map.items():
            _set_dotted(config, key, value)
        model_name = str(config["experiment"]["model"])
        variants.append((f"ablation-{name}", config, model_name not in model_without_checkpoint))

    # 关系消融：指定 graph.relations（单个关系名）来消融到单关系
    for relation in suite.get("relations", []):
        config = copy.deepcopy(base)
        config["experiment"]["graph"]["relations"] = [relation]
        variants.append((f"relation-{relation}", config, True))

    sensitivity = suite.get("sensitivity", {})
    for top_k in sensitivity.get("top_k", []):
        config = copy.deepcopy(base)
        config["experiment"]["graph"]["top_k"] = int(top_k)
        variants.append((f"topk-{top_k}", config, True))
    for smoothing in sensitivity.get("graph_smoothing", []):
        config = copy.deepcopy(base)
        config["experiment"]["graph"]["smoothing"] = float(smoothing)
        label = str(smoothing).replace(".", "p")
        variants.append((f"smoothing-{label}", config, True))
    return variants


def _flatten_summary(variant: str, summary: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    reconstruction = bool(summary["four_cell_reconstruction_all_pass"])
    for scope, metrics in summary["scopes"].items():
        for metric, values in metrics.items():
            rows.append(
                {
                    "variant": variant,
                    "scope": scope,
                    "metric": metric,
                    "mean": values["mean"],
                    "std": values["std"],
                    "four_cell_reconstruction_all_pass": reconstruction,
                }
            )
    return rows


def _write_rows(rows: list[dict[str, Any]], path: Path) -> None:
    if not rows:
        raise RuntimeError("机制实验汇总为空，拒绝生成空结果文件")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _read_json(path: Path) -> dict[str, Any]:
    import json

    return json.loads(path.read_text(encoding="utf-8"))


def _set_dotted(config: dict[str, Any], dotted_key: str, value: Any) -> None:
    cursor = config
    for part in dotted_key.split(".")[:-1]:
        cursor = cursor[part]
    cursor[dotted_key.split(".")[-1]] = value
