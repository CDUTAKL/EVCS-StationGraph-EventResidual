"""Frozen MRG architecture ablations and equation-based full-core AGCRN adaptation.

AGCRN equations: Bai et al., NeurIPS 2020; official reference:
https://github.com/LeiBAI/AGCRN/tree/master/model
NAPL + DAGG + two recurrent layers are retained; task dimensions are 7 -> 4.
This is not a reproduction of the original traffic benchmark scores.
"""
from functools import lru_cache

import numpy as np
import torch
from torch import nn

from evcs_station_graph.models.common import ForecastOutput
from evcs_station_graph.models.graph import StaticGraphForecast
from evcs_station_graph.models.tcn import TemporalConvNet

PHASE1 = ('mrg_full', 'tcn', 'tcn_wide', 'mrg_self_loop', 'agcrn_full')
PHASE2 = ('mrg_equal_beta', 'mrg_fixed_gate', 'mrg_no_refine', 'mrg_no_skip',
          'mrg_load', 'mrg_event', 'mrg_pattern')
EXTRA = ('gru_behavior', 'agcrn_matched')
MODELS = PHASE1 + PHASE2 + EXTRA


class FixedGate(nn.Module):
    def __init__(self, original):
        super().__init__()
        self.W_r, self.norm, self.dropout = original.W_r, original.norm, original.dropout

    def forward(self, h, adj, logits):
        beta = logits.softmax(0)
        message = sum(beta[i] * w(torch.matmul(a, h)) for i, (a, w) in enumerate(zip(adj, self.W_r)))
        return self.norm(h + self.dropout(.5 * message + .5 * h))


class AblatedMRG(StaticGraphForecast):
    def __init__(self, name, graphs):
        super().__init__(7, 4, 10, list(graphs), hidden_dim=32, levels=6,
                         dropout=.1, relation_dropout=0., history_steps=96)
        self.variant = name
        if name == 'mrg_equal_beta' or len(graphs) == 1:
            self.relation_weights_gcn1.requires_grad_(False)
            self.relation_weights_gcn2.requires_grad_(False)
        if name == 'mrg_fixed_gate':
            self.gcn1, self.gcn2 = FixedGate(self.gcn1), FixedGate(self.gcn2)
        if name == 'mrg_no_refine':
            del self.graph_mlp_refine
        if name == 'mrg_no_skip':
            self.skip_fusion = nn.Linear(32, 32)

    def encode(self, x):
        h0 = self.tcn.encode(x)
        adj = self._get_adjacencies()
        h1 = self.gcn1(h0, adj, self.relation_weights_gcn1)
        refined = h1 if self.variant == 'mrg_no_refine' else h1 + self.graph_mlp_refine(h1)
        h2 = self.gcn2(refined, adj, self.relation_weights_gcn2)
        fused = h2 if self.variant == 'mrg_no_skip' else torch.cat((h0, h1, h2), dim=-1)
        return self.skip_dropout(self.skip_activation(self.skip_norm(self.skip_fusion(fused))))


class NodeAdaptiveConv(nn.Module):
    def __init__(self, input_dim, output_dim, cheb_k=2, embedding_dim=10):
        super().__init__()
        self.cheb_k = cheb_k
        self.weights_pool = nn.Parameter(torch.empty(embedding_dim, cheb_k, input_dim, output_dim))
        self.bias_pool = nn.Parameter(torch.empty(embedding_dim, output_dim))
        nn.init.xavier_uniform_(self.weights_pool)
        nn.init.xavier_uniform_(self.bias_pool)

    def prepare(self, embeddings):
        a = torch.softmax(torch.relu(embeddings @ embeddings.T), dim=-1)
        supports = [torch.eye(len(a), device=a.device, dtype=a.dtype)]
        if self.cheb_k > 1:
            supports.append(a)
        for _ in range(2, self.cheb_k):
            supports.append(2 * a @ supports[-1] - supports[-2])
        w = torch.einsum('ne,ekio->nkio', embeddings, self.weights_pool)
        return torch.stack(supports), w, embeddings @ self.bias_pool

    def apply_prepared(self, x, prepared):
        support, weight, bias = prepared
        messages = torch.einsum('knm,bmi->bnki', support, x)
        return torch.einsum('bnki,nkio->bno', messages, weight) + bias

    def forward(self, x, embeddings):
        return self.apply_prepared(x, self.prepare(embeddings))


class AdaptiveCell(nn.Module):
    def __init__(self, input_dim, hidden_dim, embedding_dim=10):
        super().__init__()
        self.gate = NodeAdaptiveConv(input_dim + hidden_dim, 2 * hidden_dim, embedding_dim=embedding_dim)
        self.update = NodeAdaptiveConv(input_dim + hidden_dim, hidden_dim, embedding_dim=embedding_dim)

    def forward(self, x, h, prepared):
        z, r = torch.sigmoid(self.gate.apply_prepared(torch.cat((x, h), -1), prepared[0])).chunk(2, -1)
        candidate = torch.tanh(self.update.apply_prepared(torch.cat((x, z*h), -1), prepared[1]))
        return r*h + (1-r)*candidate


class FullAGCRN(nn.Module):
    def __init__(self, embedding_dim=10, hidden_dim=32, num_nodes=10):
        super().__init__()
        self.num_nodes = num_nodes
        self.node_embeddings = nn.Parameter(torch.empty(num_nodes, embedding_dim))
        nn.init.xavier_uniform_(self.node_embeddings)
        self.cells = nn.ModuleList([AdaptiveCell(8, hidden_dim, embedding_dim),
                                    AdaptiveCell(hidden_dim, hidden_dim, embedding_dim)])
        self.head = nn.Conv2d(1, 4, (1, hidden_dim))

    def forward(self, x):
        # Cache within this forward only (not detached): exactly the same fixed
        # E-derived operators at all time steps, with full gradients to E/pools.
        sequence = x
        for cell in self.cells:
            prepared = (cell.gate.prepare(self.node_embeddings), cell.update.prepare(self.node_embeddings))
            h = x.new_zeros(x.shape[0], self.num_nodes, self.head.weight.shape[-1])
            states = []
            for t in range(sequence.shape[1]):
                h = cell(sequence[:, t], h, prepared)
                states.append(h)
            sequence = torch.stack(states, dim=1)
        base = x[:, -1, :, -1].unsqueeze(1)
        return ForecastOutput(prediction=base + self.head(h[:, None]).squeeze(-1))


def count_parameters(model):
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


@lru_cache(maxsize=1)
def matched_width():
    # Match capacity only, never validation/test performance; preserve caller RNG.
    with torch.random.fork_rng(devices=[]):
        target = count_parameters(AblatedMRG('mrg_full', np.stack([np.eye(10)]*3)))
        return min(range(32, 65), key=lambda w: abs(count_parameters(TemporalConvNet(
            7, 4, hidden_dim=w, levels=6, history_steps=96)) - target))


class GRUForecaster(nn.Module):
    """Plain per-node GRU over the same 7-channel behavioral input."""

    def __init__(self, hidden_dim=99):
        super().__init__()
        self.gru = nn.GRU(7, hidden_dim, batch_first=True)
        self.head = nn.Linear(hidden_dim, 4)

    def forward(self, x):
        b, t, n, f = x.shape
        sequence = x.permute(0, 2, 1, 3).reshape(b * n, t, f)
        _, h = self.gru(sequence)
        out = self.head(h[-1]).reshape(b, n, 4)
        return ForecastOutput(prediction=out.permute(0, 2, 1))


def _matched_agcrn_shape_cached(num_nodes):
    with torch.random.fork_rng(devices=[]):
        target = count_parameters(AblatedMRG('mrg_full', np.stack([np.eye(num_nodes)]*3)))
        best = None
        for e in range(2, 11):
            for h in range(4, 33, 2):
                params = count_parameters(FullAGCRN(embedding_dim=e, hidden_dim=h, num_nodes=num_nodes))
                gap = abs(params - target)
                if best is None or gap < best[0]:
                    best = (gap, e, h, params)
        return best[1], best[2]


@lru_cache(maxsize=8)
def matched_agcrn_shape(num_nodes=10):
    """Match MRG-GCN's capacity by shrinking embedding and hidden width."""
    return _matched_agcrn_shape_cached(num_nodes)


def build_model(name, graphs):
    if name == 'mrg_shared_gate':
        from .gate_control import SharedNodeGate
        model = AblatedMRG('mrg_full', graphs)
        model.gcn1 = SharedNodeGate(model.gcn1)
        model.gcn2 = SharedNodeGate(model.gcn2)
        return model
    if name not in MODELS:
        raise ValueError(f'Unknown model: {name}')
    if name == 'agcrn_full':
        return FullAGCRN(num_nodes=int(np.asarray(graphs).shape[-1]))
    if name == 'agcrn_matched':
        n = int(np.asarray(graphs).shape[-1])
        e, h = matched_agcrn_shape(n)
        return FullAGCRN(embedding_dim=e, hidden_dim=h, num_nodes=n)
    if name == 'gru_behavior':
        return GRUForecaster()
    if name in ('tcn', 'tcn_wide'):
        return ResidualTCN(8, 4, hidden_dim=32 if name == 'tcn' else matched_width(),
                               levels=6, dropout=.1, history_steps=96)
    if name == 'mrg_self_loop':
        graphs = np.stack([np.eye(10)]*3)
    elif name in ('mrg_load', 'mrg_event', 'mrg_pattern'):
        i = ('mrg_load', 'mrg_event', 'mrg_pattern').index(name)
        graphs = graphs[i:i+1]
    return AblatedMRG(name, graphs)


class ResidualTCN(nn.Module):
    """残差化 TCN：预测 = 最后一片负荷 + TCN 输出。"""

    def __init__(self, input_dim, horizon, **kw):
        super().__init__()
        self.net = TemporalConvNet(input_dim, horizon, **kw)
        self.horizon = horizon

    def forward(self, x):
        base = x[:, -1, :, -1].unsqueeze(1)          # [B,1,N]
        out = self.net(x)
        pred = out.prediction if hasattr(out, 'prediction') else out
        if pred.dim() == 4:
            pred = pred.squeeze(-1)
        return ForecastOutput(prediction=base + pred)
