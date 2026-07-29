"""节点张量窗口与预测键测试。"""

from __future__ import annotations

import numpy as np

from evcs_station_graph.data import (
    NodeWindowDataset,
    WindowSpec,
    build_prediction_key_frame,
)


def test_window_shape_and_information_boundary(synthetic_bundle) -> None:
    """历史输入必须在预测起点结束，目标必须从下一时间片开始。"""
    spec = WindowSpec(history_steps=96, forecast_steps=4)
    dataset = NodeWindowDataset(synthetic_bundle, "test", spec)
    item = dataset[0]
    origin = int(item["origin_index"])

    assert item["x"].shape == (96, 4, 7)
    assert item["y"].shape == (4, 4)
    assert item["target_event"].shape == (4, 4)

    expected_last_input = (
        synthetic_bundle.features[origin] - synthetic_bundle.feature_mean
    ) / synthetic_bundle.feature_std
    expected_first_target = (
        synthetic_bundle.targets[origin + 1] - synthetic_bundle.target_mean
    ) / synthetic_bundle.target_std
    np.testing.assert_allclose(item["x"][-1].numpy(), expected_last_input, atol=1e-6)
    np.testing.assert_allclose(item["y"][0].numpy(), expected_first_target, atol=1e-6)


def test_prediction_keys_are_unique_and_aligned(synthetic_bundle) -> None:
    """逐点预测键应按起点、步长、节点一一对应。"""
    origins = synthetic_bundle.split_origins["test"][:3]
    frame = build_prediction_key_frame(
        synthetic_bundle,
        "test",
        forecast_steps=4,
        origins=origins,
    )
    assert len(frame) == 3 * 4 * 4
    assert not frame.duplicated(
        ["split", "origin_index", "horizon", "node_id"]
    ).any()
    first = frame.iloc[0]
    assert first["origin_index"] == int(origins[0])
    assert first["horizon"] == 1
    assert first["node_id"] == "N001"
    assert first["target_index"] == int(origins[0]) + 1
