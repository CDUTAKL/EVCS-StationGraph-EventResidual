"""统一训练入口的端到端冒烟测试。"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from evcs_station_graph.training import train_experiment


def test_tcn_training_writes_traceable_artifacts(
    synthetic_bundle,
    smoke_config,
    tmp_path,
) -> None:
    """短跑训练必须写出配置、模型、指标、日志和逐点预测。"""
    data_path = tmp_path / "synthetic-data.npz"
    np.savez_compressed(data_path, placeholder=np.asarray([1]))
    run_root = train_experiment(
        smoke_config,
        synthetic_bundle,
        tmp_path / "runs",
    )
    seed_dir = run_root / "seed-2024"
    for path in (
        run_root / "manifest.json",
        run_root / "metrics_summary.json",
        run_root / "relation_matrices.npz",
        seed_dir / "model.pt",
        seed_dir / "metrics.json",
        seed_dir / "training_log.csv",
        seed_dir / "predictions.csv.gz",
        seed_dir / "manifest.json",
    ):
        assert path.is_file(), path

    predictions = pd.read_csv(seed_dir / "predictions.csv.gz")
    assert len(predictions) == 8 * 4 * 4
    assert not predictions.duplicated(
        ["split", "origin_index", "horizon", "node_id"]
    ).any()
    metrics = json.loads((seed_dir / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["four_cell"]["reconstruction_pass"]


def test_frozen_residual_requires_base_checkpoint(
    synthetic_bundle,
    smoke_config,
    tmp_path,
) -> None:
    """冻结默认路径的残差模型不得在缺少基线检查点时静默运行。"""
    data_path = tmp_path / "synthetic-data.npz"
    np.savez_compressed(data_path, placeholder=np.asarray([1]))
    smoke_config["experiment"]["experiment_id"] = "SG-TEST-RESIDUAL"
    smoke_config["experiment"]["model"] = "event_residual"
    smoke_config["experiment"]["model_params"]["freeze_base"] = True
    with pytest.raises(ValueError, match="SG-EXP-002"):
        train_experiment(
            smoke_config,
            synthetic_bundle,
            tmp_path / "runs",
        )
