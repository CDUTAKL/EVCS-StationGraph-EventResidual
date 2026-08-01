"""SG-EXP-002～006 正式实验流水线。

流水线只负责固定执行顺序和记录工件位置，不改变各实验配置。SG-EXP-005
与 SG-EXP-006 会按随机种子加载 SG-EXP-002 的对应检查点，避免种子错配。

⚠️ 历史路线标注（审查 2026-08-01，Codex）：SG-EXP-005（残差修正，事件增益
+0.02% 已终止）与 SG-EXP-006（no_event_gate 复合变体）绑定 TCN（SG-EXP-002）
底座——属早期"TCN 底座 + 修正器"叙事；当前论文叙事以图底座（SG-EXP-003/
004）为主。正式实验时 SG-EXP-005/006 的检查点依赖仅用于历史对照，勿把
其结果当作图底座路线的证据；如需基于图底座的残差/消融，走 SG-EXP-005
的 base_model_type=static_graph 配置路径。
"""

from __future__ import annotations

import csv
import time
from pathlib import Path
from typing import Any

from evcs_station_graph.config import load_experiment_config
from evcs_station_graph.data import TensorBundle
from evcs_station_graph.experiments.mechanism import run_mechanism_suite
from evcs_station_graph.experiments.validation import validate_pipeline_artifacts
from evcs_station_graph.reproducibility import write_json
from evcs_station_graph.training import train_experiment


# 前三个实验（002-004）独立运行，不依赖前置检查点。
# SG-EXP-005/006 在流水线中单独处理，因为它们需要加载 SG-EXP-002 的
# 每种子检查点作为默认预测路径。这种拆分避免了配置文件中的循环依赖。
DEFAULT_EXPERIMENTS = (
    "configs/experiments/SG-EXP-002-temporal-baseline.yaml",
    "configs/experiments/SG-EXP-003-static-graph.yaml",
    "configs/experiments/SG-EXP-004-adaptive-graph.yaml",
)


def run_formal_pipeline(
    project_path: str | Path,
    bundle: TensorBundle,
    output_root: str | Path,
    *,
    mechanism_suite_path: str | Path,
    overrides: tuple[str, ...] = (),
) -> Path:
    """顺序运行 SG-EXP-002～006，并生成跨实验索引。

    参数 ``overrides`` 主要用于受控调试。正式运行不得覆盖随机种子、数据切分
    或结果权威级别，相关约束由调用方和运行清单共同审计。
    """
    root = Path(output_root).expanduser().resolve()
    pipeline_tag = time.strftime("%Y%m%d-%H%M%S")
    pipeline_root = root / "SG-PIPELINE-002-006" / pipeline_tag
    pipeline_root.mkdir(parents=True, exist_ok=True)

    run_paths: dict[str, Path] = {}
    for experiment_path in DEFAULT_EXPERIMENTS:
        config = load_experiment_config(project_path, experiment_path, overrides)
        experiment_id = str(config["experiment"]["experiment_id"])
        config["experiment"]["run_tag"] = pipeline_tag
        run_paths[experiment_id] = train_experiment(config, bundle, root)

    baseline_root = run_paths["SG-EXP-002"]
    residual_config = load_experiment_config(
        project_path,
        "configs/experiments/SG-EXP-005-event-residual.yaml",
        overrides,
    )
    residual_config["experiment"]["run_tag"] = pipeline_tag
    run_paths["SG-EXP-005"] = train_experiment(
        residual_config,
        bundle,
        root,
        base_checkpoint=baseline_root,
    )
    run_paths["SG-EXP-006"] = run_mechanism_suite(
        project_path,
        mechanism_suite_path,
        bundle,
        root,
        base_checkpoint=baseline_root,
        overrides=overrides,
    )

    rows = _collect_metric_rows(run_paths)
    _write_rows(rows, pipeline_root / "cross_experiment_metrics.csv")
    write_json(
        {
            "pipeline_id": "SG-PIPELINE-002-006",
            "pipeline_tag": pipeline_tag,
            "runs": {key: str(value) for key, value in run_paths.items()},
            "baseline_checkpoint_root": str(baseline_root),
            "summary_csv": "cross_experiment_metrics.csv",
            "formal_result_notice": (
                "仅当所有子实验均使用完整数据、三随机种子且 result_authority "
                "为 formal_candidate 时，本清单才可进入论文证据审核"
            ),
        },
        pipeline_root / "pipeline_manifest.json",
    )
    validate_pipeline_artifacts(pipeline_root, run_paths)
    return pipeline_root


def _collect_metric_rows(run_paths: dict[str, Path]) -> list[dict[str, Any]]:
    """提取 SG-EXP-002～005 的统一汇总指标。"""
    import json

    rows: list[dict[str, Any]] = []
    for experiment_id in ("SG-EXP-002", "SG-EXP-003", "SG-EXP-004", "SG-EXP-005"):
        summary_path = run_paths[experiment_id] / "metrics_summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        for scope, scope_metrics in summary["scopes"].items():
            for metric, values in scope_metrics.items():
                rows.append(
                    {
                        "experiment_id": experiment_id,
                        "scope": scope,
                        "metric": metric,
                        "mean": values["mean"],
                        "std": values["std"],
                        "four_cell_reconstruction_all_pass": summary[
                            "four_cell_reconstruction_all_pass"
                        ],
                    }
                )
    return rows


def _write_rows(rows: list[dict[str, Any]], path: Path) -> None:
    if not rows:
        raise RuntimeError("跨实验指标为空")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
