"""SG-EXP-006 机制套件续跑脚本（服务器端）。

背景：20260803-113723 run 在 topk-5 第一个种子期间进程被中断，
relation-load/event/pattern/all 四个变体已三种子完整落盘，但根目录
mechanism_summary.csv 与 manifest.json 未生成。

本脚本复用 mechanism.run_mechanism_suite 的变体派生与汇总逻辑：
1. 对已有完整结果（metrics_summary.json 且四格还原通过）的变体跳过训练，
   直接读取既有汇总；
2. 对缺失变体（topk-5/7、dropout-0p2/0p4）调用统一训练入口补齐；
3. 沿用原 run_tag（20260803-113723），最终在 run 根目录生成
   mechanism_summary.csv 与 manifest.json，使该 run 成为完整可核验产物。

用法（服务器，项目根目录执行）：
    .venv/bin/python scripts/resume_mechanism_suite.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from evcs_station_graph.config import load_experiment_config, load_yaml
from evcs_station_graph.data import load_tensor_bundle
from evcs_station_graph.experiments.mechanism import (
    _build_variants,
    _flatten_summary,
    _read_json,
    _write_rows,
)
from evcs_station_graph.reproducibility import write_json
from evcs_station_graph.training import train_experiment

PROJECT = "configs/project.yaml"
SUITE = "configs/experiments/SG-EXP-006-mechanism-relations.yaml"
RUN_TAG = "20260803-113723"
OUTPUT_ROOT = Path("outputs/experiments/SG-EXP-006")
BASE_CHECKPOINT = "outputs/night_run/20260730-171821/SG-EXP-005/20260730-171821"


def main() -> int:
    """续跑缺失变体并在原 run 根目录生成统一汇总。"""
    suite = load_yaml(SUITE)
    base_config = load_experiment_config(PROJECT, suite["base_experiment_config"], ())
    suite_seeds = suite.get("seeds")
    if suite_seeds:
        base_config["experiment"]["seeds"] = list(suite_seeds)

    variants = _build_variants(base_config, suite)
    bundle = load_tensor_bundle(base_config["paths"]["dataset_artifact"])
    root = OUTPUT_ROOT / RUN_TAG
    children_root = root / "children"

    rows = []
    child_runs = {}
    for variant_name, config, needs_checkpoint in variants:
        config["experiment"]["experiment_id"] = "SG-EXP-006-{}".format(variant_name)
        config["experiment"]["run_tag"] = RUN_TAG
        child_dir = children_root / "SG-EXP-006-{}".format(variant_name) / RUN_TAG
        summary_path = child_dir / "metrics_summary.json"
        if summary_path.exists():
            summary = _read_json(summary_path)
            if summary.get("four_cell_reconstruction_all_pass"):
                print("[skip] {}（已有完整结果）".format(variant_name))
                child_runs[variant_name] = str(child_dir)
                rows.extend(_flatten_summary(variant_name, summary))
                continue
        print("[train] {} ...".format(variant_name))
        child_root = train_experiment(
            config,
            bundle,
            children_root,
            base_checkpoint=BASE_CHECKPOINT if needs_checkpoint else None,
        )
        child_runs[variant_name] = str(child_root)
        summary = _read_json(child_root / "metrics_summary.json")
        rows.extend(_flatten_summary(variant_name, summary))

    _write_rows(rows, root / "mechanism_summary.csv")
    write_json(
        {
            "experiment_id": suite["experiment_id"],
            "run_tag": RUN_TAG,
            "variant_count": len(variants),
            "child_runs": child_runs,
            "summary_csv": "mechanism_summary.csv",
            "four_cell_reconstruction_all_pass": all(
                row["four_cell_reconstruction_all_pass"] for row in rows
            ),
            "resumed": True,
        },
        root / "manifest.json",
    )
    print("完成：机制汇总已生成，变体数 = {}".format(len(child_runs)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
