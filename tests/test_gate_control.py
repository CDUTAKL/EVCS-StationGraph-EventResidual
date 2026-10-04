import numpy as np
import torch
import json
from pathlib import Path
import subprocess
import sys

from evcs_station_graph.eventtime.models import build_model, count_parameters


def pair():
    graphs = np.stack([np.eye(10, dtype='float32')] * 3)
    torch.manual_seed(2024)
    full = build_model('mrg_full', graphs)
    torch.manual_seed(2024)
    shared = build_model('mrg_shared_gate', graphs)
    return full, shared


def test_shared_gate_preserves_parameters_and_initialization():
    full, shared = pair()
    assert count_parameters(full) == count_parameters(shared)
    assert full.state_dict().keys() == shared.state_dict().keys()
    for key in full.state_dict():
        torch.testing.assert_close(full.state_dict()[key], shared.state_dict()[key], rtol=0, atol=0)


def test_shared_gate_matches_full_for_identical_nodes():
    full, shared = pair()
    full.eval(); shared.eval()
    x = torch.randn(2, 96, 1, 7).expand(-1, -1, 10, -1)
    torch.testing.assert_close(full(x).prediction, shared(x).prediction, rtol=1e-5, atol=1e-6)


def test_shared_gate_uses_mean_logits_before_sigmoid_and_all_weights():
    _, shared = pair()
    shared.eval()
    h = torch.randn(2, 10, 32)
    adj = shared._get_adjacencies()
    layer = shared.gcn1
    logits = shared.relation_weights_gcn1
    beta = logits.softmax(0)
    message = torch.zeros_like(h)
    for r, (a, w) in enumerate(zip(adj, layer.W_r)):
        message += beta[r] * w(torch.einsum('nm,bmd->bnd', a, h))
    gate = layer.W_gate(torch.cat((h, message), -1)).mean(1, keepdim=True).sigmoid()
    expected = layer.norm(h + gate * message + (1-gate) * h)
    torch.testing.assert_close(layer(h, adj, logits), expected)
    y = shared(torch.randn(2, 96, 10, 7)).prediction
    assert y.shape == (2, 4, 10)
    y.square().mean().backward()
    for name, p in shared.named_parameters():
        if p.requires_grad:
            assert p.grad is not None and torch.isfinite(p.grad).all(), name
            assert p.grad.abs().sum() > 0, name


def test_dedicated_cli_freezes_six_pairs_without_old_suite():
    root = Path(__file__).resolve().parents[1]
    run = subprocess.run([sys.executable, str(root/'scripts/gate_control_experiment.py'),
                          'check'], cwd=root, capture_output=True, text=True, check=True)
    info = json.loads(run.stdout)
    assert info['formal_runs'] == 6
    configs = info['configuration']
    assert [(c['seed'], c['model']) for c in configs] == [
        (2024, 'mrg_full'), (2024, 'mrg_shared_gate'),
        (2025, 'mrg_full'), (2025, 'mrg_shared_gate'),
        (2026, 'mrg_full'), (2026, 'mrg_shared_gate')]
    assert len(set(info['parameters'].values())) == 1
    for c in configs:
        assert (c['max_epochs'], c['patience'], c['batch_size']) == (60, 8, 256)
        assert c['experiment'] == 'SG-EXP-027'
        assert c['train_limit'] is None and c['eval_limit'] is None
