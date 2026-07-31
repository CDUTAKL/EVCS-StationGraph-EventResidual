#!/usr/bin/env python3
"""Track A1: no_event_gate 消融补跑。

只运行 SG-EXP-006 的 no_event_gate 变体（门控关闭），
验证修复后的 mechanism.py 是否正确处理。

输出：outputs/night_run/20260730-171821/SG-EXP-006/20260730-183243/children/
      SG-EXP-006-ablation-no_event_gate/20260730-183243/
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

# 确保能找到 evcs_station_graph
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from evcs_station_graph.config import load_experiment_config
from evcs_station_graph.data import load_tensor_bundle
from evcs_station_graph.experiments.mechanism import _build_variants
from evcs_station_graph.training import train_experiment

PROJECT_PATH = "configs/project.yaml"
BASE_CONFIG = "configs/experiments/SG-EXP-005-event-residual.yaml"
BUNDLE_PATH = "data/processed/SG-DATA-005-primary-tensor.npz"

# 使用与夜跑相同的 run_tag，确保输出到同一目录
RUN_TAG = "20260730-183243"
OUTPUT_ROOT = Path("outputs/night_run/20260730-171821/SG-EXP-006/20260730-183243/children")


def main() -> None:
    print("=" * 60)
    print("Track A1: no_event_gate 消融补跑")
    print("=" * 60)

    config = load_experiment_config(PROJECT_PATH, BASE_CONFIG)
    bundle = load_tensor_bundle(BUNDLE_PATH)
    print(f"数据加载完成: {len(bundle.node_ids)} 节点, {len(bundle.feature_names)} 特征")

    # 构建 no_event_gate 变体
    suite = {"ablations": {"no_event_gate": {"experiment.gate.enabled": False}}}
    variants = _build_variants(config, suite)

    for name, cfg, needs_ckpt in variants:
        print(f"\n变体: {name}")
        print(f"  needs_checkpoint: {needs_ckpt}")
        print(f"  freeze_base: {cfg['experiment']['model_params'].get('freeze_base')}")
        print(f"  gate.enabled: {cfg['experiment'].get('gate', {}).get('enabled')}")

        cfg["experiment"]["experiment_id"] = "SG-EXP-006-ablation-no_event_gate"
        cfg["experiment"]["run_tag"] = RUN_TAG
        cfg["experiment"]["result_authority"] = "formal_candidate"

        start = time.time()
        run_root = train_experiment(
            cfg,
            bundle,
            str(OUTPUT_ROOT),
            base_checkpoint=None,  # 不加载底座 checkpoint
        )
        elapsed = time.time() - start
        print(f"  ✓ 完成 ({elapsed:.1f}s): {run_root}")

        # 验证输出
        metrics_path = run_root / "metrics_summary.json"
        if metrics_path.exists():
            with open(metrics_path) as f:
                m = json.load(f)
            scopes = m["scopes"]
            print(f"  global MAE: {scopes['global']['mae']['mean']:.6f}")
            print(f"  event MAE:  {scopes['event_window']['mae']['mean']:.6f}")
            print(f"  stable MAE: {scopes['stable_window']['mae']['mean']:.6f}")
            print(f"  四格还原: {m.get('four_cell_reconstruction_all_pass')}")
        else:
            print("  ✗ metrics_summary.json 未生成")

    print("\n✓ Track A1 完成")


if __name__ == "__main__":
    main()
