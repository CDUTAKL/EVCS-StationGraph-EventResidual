"""Hand-derived tiny fixtures; not scientific experiment evidence."""
import importlib
import numpy as np
import pytest


def api():
    assert importlib.util.find_spec('audit_gate_control') is not None, 'independent audit tool missing'
    return importlib.import_module('audit_gate_control')


def fixture():
    a = {'targets': np.arange(12).reshape(6, 2).astype(float),
         'target_event': np.array([[0,0],[1,0],[1,0],[0,1],[0,1],[0,0]], dtype=bool),
         'rule_trigger': np.array([[1,0],[0,1],[0,0],[0,0],[0,0],[0,0]], dtype=bool),
         'test_origins': np.array([0,1]), 'node_ids': np.array(['a','b']),
         'timestamps_ns': np.arange(6)*900000000000}
    idx = np.array([[1,2,3,4],[2,3,4,5]])
    p = dict(y_true=a['targets'][idx], y_pred=a['targets'][idx]+.5,
             origins=a['test_origins'].copy(), node_ids=a['node_ids'],
             target_event=a['target_event'][idx],
             rule_trigger=np.array([[[1,0]]*4,[[0,1]]*4], dtype=bool),
             target_timestamps_ns=a['timestamps_ns'][idx],
             origin_cutoff_ns=np.array([900000000000,1800000000000]))
    m = dict(n=16, mae=.5, rmse=.5, event_mae=.5, stable_mae=.5,
             by_horizon_mae=[.5]*4, by_node_mae=[.5]*2,
             four_cell_reconstruction_error=0,
             four_cells={f'target_{t}_trigger_{r}': dict(n=n,mae=.5,
                 sum_absolute_error=s,error_contribution=c)
                 for t,r,n,s,c in [(1,1,4,2.,.25),(1,0,3,1.5,.1875),
                                   (0,1,4,2.,.25),(0,0,5,2.5,.3125)]})
    return a,p,m


def test_independent_audit_restores_literal_error_and_cells():
    tool = api()
    a,p,m = fixture()
    result = tool.audit_predictions(a, 'test', p, m)
    assert result['mae'] == .5
    assert result['n'] == 16


def test_audit_rejects_shifted_truth_even_with_matching_reported_mae():
    tool = api()
    a,p,m = fixture()
    p['y_true'] = p['y_true'] + 1
    with pytest.raises(AssertionError):
        tool.audit_predictions(a, 'test', p, m)


def test_audit_rejects_wrong_metric():
    tool = api()
    a,p,m = fixture()
    m['mae'] = .49
    with pytest.raises(AssertionError):
        tool.audit_predictions(a, 'test', p, m)
