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
    with pytest.raises(ValueError, match="冻结默认路径"):
        train_experiment(
            smoke_config,
            synthetic_bundle,
            tmp_path / "runs",
        )


def test_adaptive_alpha_extraction() -> None:
    """α 提取：自适应图直接持有、残差包装间接持有、其余模型为 None。

    训练日志中的 adaptive_graph_alpha 列是 SG-EXP-004 可视化
    （α 随 epoch 变化曲线）的唯一数据来源，提取路径必须覆盖
    EventResidualCorrection 包装自适应图的情形（SG-EXP-006 关系变体）。
    """
    import torch

    from evcs_station_graph.models import (
        AdaptiveGraphForecast,
        EventResidualCorrection,
        StaticGraphForecast,
        TemporalConvNet,
    )
    from evcs_station_graph.training.engine import _adaptive_alpha

    adjacencies = [np.eye(4, dtype=np.float32)] * 3
    adaptive = AdaptiveGraphForecast(
        7, 4, 4, adjacencies,
        hidden_dim=8, levels=2, dropout=0.0,
        embedding_dim=4, fixed_weight=0.5,
    )
    expected = float(torch.sigmoid(torch.tensor(0.5)))
    assert _adaptive_alpha(adaptive) == pytest.approx(expected)

    assert _adaptive_alpha(TemporalConvNet(7, 4, hidden_dim=8, levels=2)) is None
    assert _adaptive_alpha(
        StaticGraphForecast(7, 4, 4, adjacencies, hidden_dim=8, levels=2)
    ) is None

    feature_names = (
        "load", "access_count", "departure_count", "active_count",
        "occupancy_rate", "demand_intensity", "load_jump_flag",
    )
    wrapped = EventResidualCorrection(
        adaptive,
        adjacencies,
        horizon=4,
        hidden_dim=8,
        freeze_base=False,
        feature_names=feature_names,
    )
    assert _adaptive_alpha(wrapped) == pytest.approx(expected)
