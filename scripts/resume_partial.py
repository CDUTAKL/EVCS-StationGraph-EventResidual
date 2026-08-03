"""SG-EXP-006 机制套件并行续跑：仅训练指定变体子集。

与 resume_mechanism_suite.py 的区别：本脚本通过 --variants 只处理
变体列表的一个子集，供双 GPU 并行（各自写各自的 children 子目录，
互不冲突）；汇总合并由 scripts/merge_mechanism_suite.py 统一完成。

用法（服务器，项目根目录执行）：
    CUDA_VISIBLE_DEVICES=0 .venv/bin/python scripts/resume_partial.py \\
        --variants topk-5,topk-7
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from evcs_station_graph.config import load_experiment_config, load_yaml
from evcs_station_graph.data import load_tensor_bundle
from evcs_station_graph.experiments.mechanism import _build_variants, _read_json
from evcs_station_graph.training import train_experiment

PROJECT = "configs/project.yaml"
SUITE = "configs/experiments/SG-EXP-006-mechanism-relations.yaml"
RUN_TAG = "20260803-113723"
OUTPUT_ROOT = Path("outputs/experiments/SG-EXP-006")
BASE_CHECKPOINT = "outputs/night_run/20260730-171821/SG-EXP-005/20260730-171821"


def main() -> int:
    """训练指定变体子集，跳过已有完整结果的变体。"""
    parser = argparse.ArgumentParser(description="SG-EXP-006 并行续跑（变体子集）")
    parser.add_argument("--variants", required=True, help="逗号分隔的变体名")
    args = parser.parse_args()
    wanted = {item.strip() for item in args.variants.split(",")}

    suite = load_yaml(SUITE)
    base_config = load_experiment_config(PROJECT, suite["base_experiment_config"], ())
    suite_seeds = suite.get("seeds")
    if suite_seeds:
        base_config["experiment"]["seeds"] = list(suite_seeds)

    variants = _build_variants(base_config, suite)
    bundle = load_tensor_bundle(base_config["paths"]["dataset_artifact"])
    children_root = OUTPUT_ROOT / RUN_TAG / "children"

    for variant_name, config, needs_checkpoint in variants:
        if variant_name not in wanted:
            continue
        child_dir = children_root / "SG-EXP-006-{}".format(variant_name) / RUN_TAG
        summary_path = child_dir / "metrics_summary.json"
        if summary_path.exists() and _read_json(summary_path).get(
            "four_cell_reconstruction_all_pass"
        ):
            print("[skip] {}（已有完整结果）".format(variant_name))
            continue
        config["experiment"]["experiment_id"] = "SG-EXP-006-{}".format(variant_name)
        config["experiment"]["run_tag"] = RUN_TAG
        print("[train] {} ...".format(variant_name))
        train_experiment(
            config,
            bundle,
            children_root,
            base_checkpoint=BASE_CHECKPOINT if needs_checkpoint else None,
        )
        print("[done] {}".format(variant_name))
    print("子集训练完成")
    return 0


if __name__ == "__main__":
    sys.exit(main())
