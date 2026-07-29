"""TCN、固定图、自适应图与事件残差模型测试。"""

from __future__ import annotations

import numpy as np
import torch

from evcs_station_graph.models import (
    AdaptiveGraphForecast,
    EventResidualCorrection,
    StaticGraphForecast,
    TemporalConvNet,
)


def test_all_model_output_shapes() -> None:
    """所有模型必须遵守统一的 [B,H,N] 输出约定。"""
    x = torch.randn(2, 96, 4, 7)
    adjacency = np.eye(4, dtype=np.float32)
    models = (
        TemporalConvNet(7, 4, hidden_dim=8, levels=2, dropout=0.0),
        StaticGraphForecast(
            7,
            4,
            adjacency,
            hidden_dim=8,
            levels=2,
            dropout=0.0,
        ),
        AdaptiveGraphForecast(
            7,
            4,
            4,
            hidden_dim=8,
            embedding_dim=4,
            levels=2,
            dropout=0.0,
            fixed_adjacency=adjacency,
        ),
    )
    for model in models:
        output = model(x)
        assert output.prediction.shape == (2, 4, 4)
        assert torch.isfinite(output.prediction).all()


def test_residual_correction_obeys_gate_and_bound() -> None:
    """未触发节点保持默认预测，触发节点的修正量不得越界。"""
    x = torch.randn(2, 96, 4, 7)
    base = TemporalConvNet(7, 4, hidden_dim=8, levels=2, dropout=0.0)
    model = EventResidualCorrection(
        base,
        np.eye(4, dtype=np.float32),
        horizon=4,
        hidden_dim=8,
        residual_bound=0.25,
        freeze_base=True,
    )
    no_trigger = torch.zeros(2, 4, dtype=torch.bool)
    no_trigger_output = model(x, rule_trigger=no_trigger)
    torch.testing.assert_close(
        no_trigger_output.prediction,
        no_trigger_output.base_prediction,
    )
    assert torch.count_nonzero(no_trigger_output.residual) == 0

    all_trigger = torch.ones(2, 4, dtype=torch.bool)
    triggered_output = model(x, rule_trigger=all_trigger)
    assert triggered_output.residual is not None
    assert float(triggered_output.residual.detach().abs().max()) <= 0.25 + 1e-6
