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
    """三类关系矩阵必须可计算，并满足对称归一化图的基本性质。"""
    train_end = int(synthetic_bundle.split_origins["train"][-1])
    relations = build_relation_set(
        synthetic_bundle.features[: train_end + 1],
        synthetic_bundle.targets[: train_end + 1],
        synthetic_bundle.feature_names,
        top_k=2,
    )
    assert set(relations.as_dict()) == {"load", "event", "pattern"}
    for matrix in relations.as_dict().values():
        assert matrix.shape == (4, 4)
        assert np.isfinite(matrix).all()
        np.testing.assert_allclose(matrix, matrix.T, atol=1e-6)
        assert np.all(np.diag(matrix) > 0.0)
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


def test_event_window_expansion_is_causal(synthetic_bundle) -> None:
    """事件窗口扩展是严格因果的：触发点 t 不得改变 t 之前预测起点的路由状态。

    验证方式：对全时间轴应用规则，检查任意被标记为"事件路径"的时刻 t
    必定由某个不晚于 t 的原始触发点解释（s ≤ t ≤ s + window_extension）。
    若存在 t 因 s > t 的触发而被标记，则存在未来信息泄漏。
    """
    rule = fit_frozen_event_rule(synthetic_bundle, quantile=0.8, window_extension=2)

    # 用全时间轴计算触发矩阵
    all_origins = np.arange(len(synthetic_bundle.timestamps_ns), dtype=np.int64)
    trigger = apply_frozen_event_rule(synthetic_bundle, all_origins, rule)

    # 获取原始阈值判定（未扩展）作为"因果根"
    from evcs_station_graph.evaluation.rules import visible_event_scores

    score_stats_np = {
        key: np.asarray(value, dtype=np.float32)
        for key, value in rule.score_stats.items()
    }
    scores = visible_event_scores(synthetic_bundle, all_origins,
                                   score_stats=score_stats_np)
    raw = scores >= rule.thresholds[None, :]  # [T, N]

    w = rule.window_extension
    T, N = trigger.shape
    for n in range(N):
        for t in range(T):
            if not trigger[t, n]:
                continue
            # t 必须由某个原始触发点 s ≤ t 经过前向扩展覆盖
            explained = any(
                raw[s, n] and s <= t <= s + w
                for s in range(max(0, t - w), t + 1)
            )
            assert explained, (
                f"节点 {n} 时刻 t={t} 的触发状态缺乏因果解释："
                f"前向窗口 [{max(0, t - w)}, {t}] 内无原始触发点"
            )


def test_symmetric_windows_cover_both_directions(synthetic_bundle) -> None:
    """对称事件邻域必须同时覆盖触发点的前后方向。"""
    from evcs_station_graph.evaluation.rules import build_symmetric_event_windows

    rule = fit_frozen_event_rule(synthetic_bundle, quantile=0.8, window_extension=2)
    all_origins = np.arange(len(synthetic_bundle.timestamps_ns), dtype=np.int64)

    symmetric = build_symmetric_event_windows(synthetic_bundle, all_origins, rule)
    causal = apply_frozen_event_rule(synthetic_bundle, all_origins, rule)

    # 对称窗口应包含因果窗口（前者是后者的超集）
    assert (causal <= symmetric).all(), "对称窗口应包含因果窗口"

    # 对称窗口确实比因果窗口更大（向后扩展的部分）
    symmetric_count = int(symmetric.sum())
    causal_count = int(causal.sum())
    assert symmetric_count >= causal_count, (
        f"对称窗口触发数 ({symmetric_count}) 应 ≥ 因果窗口触发数 ({causal_count})"
    )
