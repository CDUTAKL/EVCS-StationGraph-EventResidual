"""Small deterministic checks for the revision's algebra and frozen audit artifacts."""
import copy
import json
from pathlib import Path
import numpy as np
import pytest
import torch
from evcs_station_graph.models.graph import MultiRelationGatedGCN

def test_equal_beta_reparameterization_preserves_messages_and_layer():
    torch.manual_seed(2024)
    a=MultiRelationGatedGCN(hidden_dim=8,num_relations=3,dropout=0,relation_dropout=0).double().eval()
    b=copy.deepcopy(a)
    raw=torch.tensor([.3,-.2,.8],dtype=torch.float64)
    beta=raw.softmax(0)
    with torch.no_grad():
        for r,w in enumerate(b.W_r):
            w.weight.mul_(3*beta[r])
    h=torch.randn(2,5,8,dtype=torch.float64)
    adj=[torch.randn(5,5,dtype=torch.float64) for _ in range(3)]
    torch.testing.assert_close(a(h,adj,raw),b(h,adj,torch.zeros_like(raw)),rtol=1e-12,atol=1e-12)

def test_frozen_failure_audit_closes_keys_and_sources():
    p=Path('outputs/analysis/conformal_failure_audit/summary.json')
    if not p.exists():
        pytest.skip('Local frozen audit not distributed with source-only checkout')
    s=json.loads(p.read_text())
    assert len(s['seeds'])==3 and sum(x['n'] for x in s['four_cell_coverage'].values())==712360
    assert all(max(abs(v) for v in x['coverage_differences'].values())<1e-4 for x in s['seeds'])
    assert all(len(h)==64 for h in s['sources'].values())
    q=s['aggregate_quantiles']
    assert np.isclose(q['test']['p90']['mean']/q['validation']['p90']['mean'],3.502675,rtol=1e-5)
