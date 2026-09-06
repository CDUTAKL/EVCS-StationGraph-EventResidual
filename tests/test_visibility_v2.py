"""Independent hand-checked fixtures for forecast-time input safety (not accuracy)."""
import numpy as np
import pandas as pd
import pytest

from evcs_station_graph.data import visibility_v2 as v


def fixture():
    grid = pd.date_range('2020-01-01', periods=16, freq='15min').asi8
    rows = pd.DataFrame({
        'spaceID': ['A', 'A', 'B'],
        'connectionTime': pd.to_datetime(['2020-01-01 00:05', '2020-01-01 00:30', '2020-01-01 02:00']),
        'disconnectTime': pd.to_datetime(['2020-01-01 00:30', '2020-01-01 02:00', '2020-01-01 03:00']),
        'kWhDelivered': [2., 6., 4.],
    })
    return rows, grid


def test_events_on_boundary_are_not_visible_in_preceding_bin():
    r, g = fixture()
    x = v.event_features(r, g, ['A', 'B'])
    np.testing.assert_array_equal(x[:3, 0, :3], [[1, 0, 1], [0, 0, 1], [1, 1, 1]])


def test_future_energy_and_disconnect_do_not_change_input():
    r, g = fixture()
    x = v.event_features(r, g[:4], ['A', 'B'])
    r.loc[1:, 'disconnectTime'] = pd.Timestamp('2030-01-01')
    r['kWhDelivered'] *= 1000
    np.testing.assert_array_equal(x, v.event_features(r, g[:4], ['A', 'B']))


def test_censored_event_replay_matches_full_history():
    r, g = fixture()
    cutoff = pd.Timestamp('2020-01-01 01:00')
    censored = r[r.connectionTime < cutoff].copy()
    censored.loc[censored.disconnectTime >= cutoff, 'disconnectTime'] = pd.NaT
    censored = censored.drop(columns='kWhDelivered')
    np.testing.assert_array_equal(v.event_features(r, g[:4], ['A', 'B']),
                                  v.event_features(censored, g[:4], ['A', 'B']))


def test_proxy_conserves_energy_and_carries_label_maturity():
    r, g = fixture()
    y, maturity = v.proxy_targets(r, g, ['A', 'B'])
    np.testing.assert_allclose(y.sum(axis=0), [8, 4])
    np.testing.assert_allclose(y[:3, 0], [1, 1, 1])
    assert maturity[2, 0] == pd.Timestamp('2020-01-01 02:00').value


def test_fit_prefix_excludes_sessions_ending_after_fit_boundary():
    r, g = fixture()
    y, m = v.proxy_targets(r, g, ['A', 'B'])
    assert v.mature_prefix_end(m, g, 6) == 2


def test_windows_do_not_cross_segment_or_label_availability_boundary():
    r, g = fixture()
    _, m = v.proxy_targets(r, g, ['A', 'B'])
    assert v.safe_origins(g, m, 0, 6, 2, 1).size == 0
    np.testing.assert_array_equal(v.safe_origins(g, m, 8, 16, 2, 1), np.arange(9, 15))


def test_fitted_statistics_do_not_use_held_out_values():
    r, g = fixture()
    x = v.event_features(r, g, ['A', 'B'])
    y, _ = v.proxy_targets(r, g, ['A', 'B'])
    a = v.fit_preprocessing(x, y, 4)
    x[4:] = 9999; y[4:] = 9999
    b = v.fit_preprocessing(x, y, 4)
    for key in a:
        np.testing.assert_array_equal(a[key], b[key])


def test_rule_extension_is_forward_only():
    scores = np.array([[0.], [0.], [3.], [0.], [0.], [0.]])
    np.testing.assert_array_equal(v.apply_rule(scores, np.array([2.]), 2).ravel(),
                                  [False, False, True, True, True, False])


def test_invalid_grid_and_nonfinite_training_targets_fail_closed():
    r, g = fixture()
    with pytest.raises(ValueError):
        v.event_features(r, g[[0, 2]], ['A', 'B'])
    x = v.event_features(r, g, ['A', 'B'])
    y = np.zeros((len(g), 2)); y[0, 0] = np.nan
    with pytest.raises(ValueError):
        v.fit_preprocessing(x, y, 4)
