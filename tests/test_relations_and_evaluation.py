"""候选关系统计与统一评价协议测试。"""

from __future__ import annotations

import numpy as np

from evcs_station_graph.evaluation import (
    apply_frozen_event_rule,
    fit_frozen_event_rule,
    four_cell_diagnostics,
)
from evcs_station_graph.graphs import build_relation_set


def test_relation_matrices_are_finite_and_symmetrically_normalized(
    synthetic_bundle,
) -> None:
    """五类候选关系都必须可计算，并满足对称归一化图的基本性质。"""
    train_end = int(synthetic_bundle.split_origins["train"][-1])
    relations = build_relation_set(
        synthetic_bundle.features[: train_end + 1],
        synthetic_bundle.targets[: train_end + 1],
        synthetic_bundle.feature_names,
        top_k=2,
        smoothing=0.5,
    )
    assert set(relations.as_dict()) == {
        "current_event",
        "historical_event",
        "load_correlation",
        "temporal_profile",
        "fused",
    }
    for matrix in relations.as_dict().values():
        assert matrix.shape == (4, 4)
        assert np.isfinite(matrix).all()
        np.testing.assert_allclose(matrix, matrix.T, atol=1e-6)
        assert np.all(np.diag(matrix) > 0.0)
        # 对称归一化邻接矩阵的谱半径不应超过 1；它不要求逐行和为 1。
        assert float(np.abs(np.linalg.eigvalsh(matrix)).max()) <= 1.0 + 1e-5


def test_four_cell_metrics_reconstruct_global_mae() -> None:
    """四个互斥单元加权后必须精确还原全局 MAE。"""
    truth = np.arange(24, dtype=np.float64).reshape(2, 3, 4)
    prediction = truth + np.linspace(-0.5, 0.6, 24).reshape(2, 3, 4)
    target_event = (truth.astype(int) % 2) == 0
    rule_trigger = np.asarray(
        [[True, False, True, False], [False, True, False, True]],
        dtype=bool,
    )
    diagnostics = four_cell_diagnostics(
        truth,
        prediction,
        target_event=target_event,
        rule_trigger=rule_trigger,
    )
    assert diagnostics["reconstruction_pass"]
    assert diagnostics["total_count"] == truth.size


def test_event_rule_is_fit_once_on_validation(synthetic_bundle) -> None:
    """测试起点变化不得反向改变验证集冻结阈值。"""
    rule = fit_frozen_event_rule(synthetic_bundle, quantile=0.8)
    thresholds = rule.thresholds.copy()
    trigger = apply_frozen_event_rule(
        synthetic_bundle,
        synthetic_bundle.split_origins["test"],
        rule,
    )
    assert trigger.shape == (20, 4)
    np.testing.assert_array_equal(rule.thresholds, thresholds)
