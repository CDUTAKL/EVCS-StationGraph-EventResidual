import numpy as np
import pandas as pd
import pytest
from analyze_rolling_calibration import eligible_mask, fit_rolling, DAY, STEP
from audit_proxy_engineering import completion_audit
from evcs_station_graph.evaluation.charging_decision import ChargingJob, plan_charging
from probe_matched_current_shapes import current_shape


def test_rolling_excludes_future_and_unfinished_labels():
    start = np.array([[DAY, DAY+STEP]])
    maturity = np.array([[[DAY+STEP], [4*DAY]]])
    m = eligible_mask(start, maturity, np.array([DAY]), 2*DAY, 14)
    assert m.tolist() == [[[True], [False]]]
    assert not eligible_mask(start, maturity, np.array([2*DAY]), 2*DAY, 14).any()


def test_future_scores_cannot_change_past_quantile():
    e = np.arange(40, dtype=float).reshape(10, 4, 1)
    eligible = np.zeros_like(e, bool); eligible[:5] = True
    t = np.zeros_like(eligible)
    fallback = dict(node_standard=[2], stable=[2], triggered=3)
    a, _ = fit_rolling(e, t, eligible, fallback, .1)
    e[5:] = 1e12
    b, _ = fit_rolling(e, t, eligible, fallback, .1)
    assert a == b and a['triggered'] == 3


def test_insufficient_rank_is_not_clamped():
    e = np.ones((1, 4, 1)); m = np.ones_like(e, bool)
    q, _ = fit_rolling(e, m, m, dict(node_standard=[2], stable=[3], triggered=4), .1)
    assert np.isinf(q['node_standard'][0]) and np.isinf(q['triggered'])
    assert q['stable'] == [3]


def test_completion_support_preserves_energy_not_claims_truth():
    f = pd.DataFrame([dict(sessionID='x', spaceID='N', connectionTime='2020-01-01T00:00:00Z',
                           disconnectTime='2020-01-01T01:00:00Z', doneChargingTime='2020-01-01T00:30:00Z', kWhDelivered=4)])
    g = pd.date_range('2020-01-01', periods=4, freq='15min', tz='UTC').asi8
    s, _, a, b = completion_audit(f, g, ['N'])
    # 00:30 equality excluded; only 00:45 bin is entirely strictly after completion.
    assert s['energy_assigned_strictly_after_completion_kwh'] == 1
    assert a.sum() == b.sum() == 4


def inputs():
    return dict(inelastic_kw=[1]*4, noncharging_kw=[1]*4, capacity_kw=[6]*4,
                reserve_kw=[1]*4, price_per_kwh=[4,3,2,1])


def test_decision_missing_real_mapping_refuses_commands():
    r = plan_charging(**inputs(), jobs=[])
    assert r['status'] == 'MATERIALS_REQUIRED' and not r['executable']


def test_decision_meets_service_and_capacity_in_scenario():
    r = plan_charging(**inputs(), jobs=[ChargingJob('A', 0, 4, 1, 3)], scenario=True)
    assert r['status'] == 'SHADOW_PLAN_SCENARIO'
    assert r['delivered_kwh'] == [1] and r['planned_cost'] == pytest.approx(1.25)
    assert r['realized_savings'] is None and not r['executable']
    assert max(r['total_kw']) <= 5


def test_decision_does_not_drop_infeasible_demand():
    r = plan_charging(**inputs(), jobs=[ChargingJob('A', 0, 1, 2, 3)], scenario=True)
    assert r['status'] == 'INFEASIBLE_SERVICE'


def test_decision_rejects_out_of_horizon_deadline():
    with pytest.raises(ValueError):
        plan_charging(**inputs(), jobs=[ChargingJob('A', 0, 5, 1, 3)], scenario=True)


def test_current_shape_is_normalized_charge_not_assumed_power():
    t = pd.date_range('2020-01-01', periods=1801, freq='s', tz='UTC')
    f = pd.DataFrame({'time': t, 'Charging Current (A)': np.r_[np.ones(900)*2, np.zeros(901)],
                      'Voltage (V)': np.nan, 'Power (kW)': np.nan})
    s, fraction, _ = current_shape(f, t[0], t[-1])
    np.testing.assert_array_equal(fraction, [1, 0])
    assert s['normalized_shape_total_variation'] == .5
    assert s['peak_bin_fraction_ratio_to_uniform'] == 2
    assert s['missing_power_rows'] == len(f)


def test_current_probe_rejects_long_unobserved_gaps():
    t = pd.date_range('2020-01-01', periods=2, freq='15min', tz='UTC')
    f = pd.DataFrame({'time': t, 'Charging Current (A)': [2, 0], 'Voltage (V)': [200]*2, 'Power (kW)': [0]*2})
    with pytest.raises(ValueError):
        current_shape(f, t[0], t[-1])
