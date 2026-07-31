"""测试公共数据夹具。

合成数据只用于验证代码结构、张量形状和实验工件，不作为论文性能证据。
"""

from __future__ import annotations

import numpy as np
import pytest

from evcs_station_graph.data import TensorBundle


@pytest.fixture()
def synthetic_bundle() -> TensorBundle:
    """构造包含稳定段、接入事件和离站事件的小型节点张量。"""
    rng = np.random.default_rng(20240729)
    time_steps = 180
    node_count = 4
    feature_names = (
        "load",
        "access_count",
        "departure_count",
        "active_count",
        "occupancy_rate",
        "demand_intensity",
        "load_jump_flag",
    )
    timestamps = (
        np.datetime64("2024-01-01T00:00:00", "ns")
        + np.arange(time_steps) * np.timedelta64(15, "m")
    ).astype("datetime64[ns]")

    phase = np.linspace(0.0, 8.0 * np.pi, time_steps, dtype=np.float32)
    features = np.zeros(
        (time_steps, node_count, len(feature_names)),
        dtype=np.float32,
    )
    for node in range(node_count):
        load = (
            2.0
            + 0.35 * node
            + 0.7 * np.sin(phase + 0.3 * node)
            + rng.normal(0.0, 0.03, time_steps)
        )
        features[:, node, 0] = load
        features[:, node, 3] = np.clip(np.round(load), 0, None)
        features[:, node, 4] = np.clip(load / 5.0, 0.0, 1.0)
        features[:, node, 5] = np.maximum(load, 0.0)

    # 在验证集和测试集都布置事件，确保冻结阈值与四格诊断可执行。
    event_times = (112, 126, 145, 156)
    for index, time_index in enumerate(event_times):
        node = index % node_count
        features[time_index, node, 1] = 2.0
        features[time_index + 1, node, 2] = 1.0
        features[time_index, node, 3] += 2.0
        features[time_index, node, 6] = 1.0
        features[time_index:, node, 0] += 0.45

    targets = features[:, :, 0].copy()
    event_labels = (
        (features[:, :, 1] > 0)
        | (features[:, :, 2] > 0)
        | (features[:, :, 6] > 0)
    )
    train_end = 119
    feature_mean = features[: train_end + 1].mean(axis=(0, 1))
    feature_std = features[: train_end + 1].std(axis=(0, 1))
    feature_std = np.where(feature_std < 1e-6, 1.0, feature_std)
    target_mean = targets[: train_end + 1].mean(axis=0)
    target_std = targets[: train_end + 1].std(axis=0)
    target_std = np.where(target_std < 1e-6, 1.0, target_std)

    return TensorBundle(
        timestamps_ns=timestamps.astype(np.int64),
        node_ids=np.asarray(["N001", "N002", "N003", "N004"]),
        feature_names=feature_names,
        features=features,
        targets=targets,
        event_labels=event_labels,
        split_origins={
            "train": np.arange(95, 120, dtype=np.int64),
            "validation": np.arange(120, 140, dtype=np.int64),
            "test": np.arange(140, 160, dtype=np.int64),
        },
        feature_mean=feature_mean.astype(np.float32),
        feature_std=feature_std.astype(np.float32),
        target_mean=target_mean.astype(np.float32),
        target_std=target_std.astype(np.float32),
    )


@pytest.fixture()
def smoke_config(tmp_path) -> dict:
    """生成可供统一训练入口使用的最小配置。"""
    return {
        "project": {
            "history_steps": 96,
            "forecast_steps": 4,
        },
        "paths": {
            "dataset_artifact": str(tmp_path / "synthetic-data.npz"),
        },
        "runtime": {
            "device": "cpu",
            "max_samples_per_split": 8,
        },
        "dataset": {
            "event": {
                "trigger_quantile": 0.8,
            },
        },
        "experiment": {
            "experiment_id": "SG-TEST-001",
            "run_tag": "smoke",
            "model": "TCN",
            "seeds": [2024],
            "result_authority": "implementation_smoke_only",
            "model_params": {
                "hidden_dim": 8,
                # levels=6 与正式口径一致（RF=127 ≥ history_steps=96）；
                # 低于 6 会触发 TCN 感受野校验报错（tcn.py 硬约束）
                "levels": 6,
                "dropout": 0.0,
            },
            "training": {
                "epochs": 2,
                "patience": 1,
                "batch_size": 4,
                "learning_rate": 0.001,
                "weight_decay": 0.0,
            },
            "graph": {
                "top_k": 2,
            },
            "gate": {
                "enabled": True,
            },
        },
    }
