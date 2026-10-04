"""Rank selection, route isolation, interval penalty and cluster pairing checks."""
import numpy as np
import pytest
from analyze_independent_calibration import order_quantile, fit_halfwidths, interval_metrics, bootstrap_ratio


def test_rank_uses_next_order_statistic_not_interpolation():
    q, n, rank = order_quantile(np.arange(10), .1)
    assert (q, n, rank) == (9, 10, 10)
    assert np.isinf(order_quantile([1, 2, 3], .1)[0])
    with pytest.raises(ValueError):
        order_quantile([], .1)


def test_behavior_routes_use_calibration_only_and_preserve_node_groups():
    e = np.stack([np.ones((20, 4)), np.full((20, 4), 10)], axis=-1)
    trigger = np.zeros_like(e, bool)
    trigger[:10, :, :] = True
    widths, ranks = fit_halfwidths(e, trigger, .1)
    np.testing.assert_array_equal(widths['node_standard'], [1, 10])
    np.testing.assert_array_equal(widths['stable'], [1, 10])
    assert widths['triggered'] == 10
    assert ranks[-1]['n'] == 80 and ranks[-1]['rank'] == 73


def test_interval_score_penalizes_misses_and_excess_width():
    m = interval_metrics(np.array([.5, 2]), np.array([1, 1]), .1)
    assert m == dict(coverage=.5, width=2., interval_score=12.)
    assert interval_metrics([0], [10], .1)['interval_score'] == 20


def test_cluster_ratio_preserves_counts_and_paired_sign():
    ci = bootstrap_ratio([2, 9], [2, 3], np.array([[0, 0], [1, 1], [0, 1]]))
    assert ci['estimate'] == 2.2 and ci['valid_resamples'] == 3
    assert 0 < ci['low'] <= ci['high']
    with pytest.raises(ValueError):
        bootstrap_ratio([0, 1], [0, 1], np.array([[0, 0]]))
