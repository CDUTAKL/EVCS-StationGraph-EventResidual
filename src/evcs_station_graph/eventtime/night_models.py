"""夜间原创方向实验（SG-EXP-033/034）：QMH 分位数混合头 + 关系边注意力。

设计纪律
--------
- 不改动任何冻结模型（graph.py / tcn.py / agcrn.py 只读复用）。
- 只输出标准化空间预测；反标准化由 runner.predict 统一完成（RA-Hurdle 曾因模型内
  再反标准化一次造成双重变换，本模块严格避免）。
- 关系边注意力零初始化：attn_a = 0 时 α 精确退化为输入邻接 Â，起点等价 MRG-GCN。
"""

from __future__ import annotations

import math

import numpy as np

import torch
from torch import nn
from torch.nn import functional as F

from evcs_station_graph.models.common import ForecastOutput
from evcs_station_graph.eventtime.models import FullAGCRN
from evcs_station_graph.models.graph import MultiRelationGatedGCN, StaticGraphForecast


# ============================================================ QMH

class QuantileMixHead(nn.Module):
    """门控 + 单调分位网格 + 闭式中位数组合器。

    输出 = g · Interp(Q̂, τ(p))，g = min(1, p/0.5)，
    τ(p) = 0 (p<0.5) 或 1-1/(2p) (p>=0.5)，
    Q̂ 为 τ∈[0,0.5] 上 K+1 个单调分位点（累积 softplus 保证不交叉）。
    """

    def __init__(self, dim: int, horizon: int = 4, levels: int = 8,
                 zero_level: float = -0.267) -> None:
        super().__init__()
        self.horizon, self.levels = horizon, levels
        self.register_buffer('zero_level', torch.as_tensor(zero_level, dtype=torch.float32))
        self.gate = nn.Linear(dim, horizon)
        self.grid = nn.Linear(dim, horizon * (levels + 1))
        # 初始 p=0.5 → g=1, τ=0；grid 零初始化使初始分位网格 = 0.127·(k+1)，
        # 即 0.13–1.14（标准化空间），覆盖活跃键中位数区间而不依赖隐层量级。
        nn.init.zeros_(self.gate.weight); nn.init.zeros_(self.gate.bias)
        nn.init.zeros_(self.grid.weight)
        nn.init.constant_(self.grid.bias, -2.0)

    def forward(self, latent: torch.Tensor):
        """latent [B,N,D] → 预测 [B,H,N]、门控 p [B,H,N]、分位 q [B,H,N,K+1]。"""
        b, n, _ = latent.shape
        h, k = self.horizon, self.levels
        p = torch.sigmoid(self.gate(latent)).transpose(1, 2)              # [B,H,N]
        inc = F.softplus(self.grid(latent)).view(b, n, h, k + 1)
        z0_inc = self.zero_level.to(latent.dtype).reshape(1, n, 1, 1)      # [1,N,1,1]
        q = (z0_inc + torch.cumsum(inc, dim=-1)).permute(0, 2, 1, 3)      # [B,H,N,K+1]
        tau = torch.arange(k + 1, device=latent.device, dtype=latent.dtype) / (2 * k)
        # 目标分位水平（可微）
        tgt = torch.where(p >= 0.5, 1.0 - 1.0 / (2.0 * p.clamp(min=1e-6)),
                          torch.zeros_like(p)).clamp(0.0, 0.5)
        idx = (tgt * (2 * k)).clamp(0, k)
        lo = idx.floor().long().clamp(0, k - 1)
        frac = (idx - lo.to(idx.dtype)).unsqueeze(-1)
        q_lo = torch.gather(q, -1, lo.unsqueeze(-1))
        q_hi = torch.gather(q, -1, (lo + 1).unsqueeze(-1))
        q_t = q_lo + frac * (q_hi - q_lo)                                  # [B,H,N,1]
        g = (p / 0.5).clamp(max=1.0).unsqueeze(-1)
        # 零键回落到 zero_level（标准化空间的原点 0），而不是 0 分位点
        z0_out = self.zero_level.to(latent.dtype).reshape(1, 1, -1, 1)     # [1,1,N,1]
        delta = (g * q_t + (1.0 - g) * z0_out).squeeze(-1)                 # [B,H,N] 残差
        return delta, p, q, tau


class QMHForecast(StaticGraphForecast):
    """MRG-GCN 主干 + QMH 头。loss 由 night_runner 通过 compute_loss 调用。"""

    def __init__(self, name, graphs, levels=8, zero_level=-0.267):
        num_nodes = int(list(graphs)[0].shape[0])
        super().__init__(8, 4, num_nodes, list(graphs), hidden_dim=32, levels=6,
                         dropout=.1, relation_dropout=0., history_steps=96)
        del self.head
        self.qmh = QuantileMixHead(self.latent_dim, self.horizon, levels, zero_level)
        self._aux = None

    def forward(self, x, **_):
        latent = self.encode(x)
        delta, p, q, tau = self.qmh(latent)
        # 残差化：预测 = 最后一片负荷（load_lag1，标准化空间）+ 头输出的残差
        base = x[:, -1, :, -1].unsqueeze(1)          # [B,1,N] → 广播到 [B,H,N]
        pred = base + delta
        self._aux = (p, q, tau)
        return ForecastOutput(prediction=pred, adjacency=self._get_adjacencies()[0],
                              relation_weights_gcn1=self.relation_weights_gcn1.detach(),
                              relation_weights_gcn2=self.relation_weights_gcn2.detach())

    def compute_loss(self, pred, y, lam=1.0, thresh=-0.267, beta=1.0, bce=10.0):
        """全局保真项（=全局 MAE 本身）+ 活跃键分位项 + 门控 BCE。

        门控必须显式监督：g=(p/0.5).clamp(max=1) 在 p>0.5 后对 p 的梯度恒为 0，
        若不加 BCE，p 只能靠噪声漂移（实测漂到 0.86、零键与活跃键几乎不可分）。
        """
        l1 = F.l1_loss(pred, y)
        if not self._aux:
            return l1
        p, q, tau = self._aux
        thresh_t = torch.as_tensor(thresh, dtype=y.dtype, device=y.device).reshape(1, 1, -1) if not torch.is_tensor(thresh) else thresh.to(y.dtype).reshape(1, 1, -1)
        mask = (y > thresh_t).to(y.dtype)
        gate_loss = F.binary_cross_entropy(p.clamp(1e-6, 1 - 1e-6), mask)
        if float(mask.sum()) < 1:
            return lam * l1 + bce * gate_loss
        diff = y.unsqueeze(-1) - q                       # [B,H,N,K+1]
        pin = torch.maximum(tau * diff, (tau - 1.0) * diff)
        pin = (pin * mask.unsqueeze(-1)).sum() / (mask.sum() * q.shape[-1])
        return lam * l1 + beta * pin + bce * gate_loss


# ============================================================ 关系边注意力

class EdgeAttnGCN(nn.Module):
    """在关系支持集内做边级注意力，零初始化严格退化为 Â。"""

    def __init__(self, hidden_dim, num_relations, dropout=.1, use_edge_feature=True,
                 full_support=False, score_scale=1.0):
        super().__init__()
        self.W_r = nn.ModuleList([nn.Linear(hidden_dim, hidden_dim, bias=False)
                                  for _ in range(num_relations)])
        self.W_gate = nn.Linear(hidden_dim * 2, hidden_dim)
        self.norm = nn.LayerNorm(hidden_dim)
        self.dropout = nn.Dropout(dropout)
        self.leaky = nn.LeakyReLU(0.2)
        self.use_edge_feature = use_edge_feature
        self.full_support = full_support
        self.score_scale = float(score_scale)
        self.attn_a = nn.Parameter(torch.zeros(num_relations, hidden_dim * 2))

    def forward(self, H, adjs, rel_w):
        beta = torch.softmax(rel_w, dim=0)
        b, n, d = H.shape
        M = torch.zeros_like(H)
        for r, (A, W) in enumerate(zip(adjs, self.W_r)):
            Wh = W(H)                                             # [B,N,D]
            pair = torch.cat([Wh.unsqueeze(2).expand(-1, -1, n, -1),
                              Wh.unsqueeze(1).expand(-1, n, -1, -1)], dim=-1)
            score = self.score_scale * self.leaky((pair * self.attn_a[r]).sum(-1))  # [B,N,N]
            support = (torch.ones_like(A, dtype=torch.bool) if self.full_support
                       else (A > 0))
            logits = score
            if self.use_edge_feature:
                logits = logits + torch.log(A.clamp(min=1e-12))
            logits = logits.masked_fill(~support, -1e9)
            alpha = torch.softmax(logits, dim=-1)
            # 无支持边的行 → 消息保持为 0（与原实现一致）
            has_edge = support.any(-1, keepdim=True).to(alpha.dtype)
            alpha = alpha * has_edge
            msg = torch.einsum('bnm,bmd->bnd', alpha, Wh)
            M = M + beta[r] * msg
        G = torch.sigmoid(self.W_gate(torch.cat([H, M], dim=-1)))
        H_t = G * M + (1.0 - G) * H
        return self.norm(H + self.dropout(H_t))


class QMHFullAGCRN(FullAGCRN):
    """完整 AGCRN 主干 + QMH 输出头（归因隔离实验）。

    与 FullAGCRN 的唯一差别是预测头：原 head 为 Conv2d 直接回归，
    这里替换为 QuantileMixHead（门控 + 分位网格 + 闭式组合器）。
    主干结构、hidden/embedding 维度、层数完全一致，用于检验 QMH 的增益
    是否跨主干成立。本类只用于归因对照，不进入主结果。
    """

    def __init__(self, name, graphs, levels=8, zero_level=-0.267,
                 embedding_dim=10, hidden_dim=32):
        num_nodes = int(np.asarray(graphs).shape[-1]) if not isinstance(graphs, list) else int(graphs[0].shape[0])
        super().__init__(embedding_dim=embedding_dim, hidden_dim=hidden_dim, num_nodes=num_nodes)
        self.name = name
        self._hidden_dim = hidden_dim
        self.use_linear = name.endswith('_lin') or name.endswith('_lin48')
        self.qmh = QuantileMixHead(hidden_dim, 4, levels, zero_level)
        self._aux = None

    def forward(self, x):
        sequence = x
        for cell in self.cells:
            prepared = (cell.gate.prepare(self.node_embeddings),
                        cell.update.prepare(self.node_embeddings))
            h = x.new_zeros(x.shape[0], self.num_nodes, self._hidden_dim)
            states = []
            for t in range(sequence.shape[1]):
                h = cell(sequence[:, t], h, prepared)
                states.append(h)
            sequence = torch.stack(states, dim=1)
        base = x[:, -1, :, -1].unsqueeze(1)          # [B,1,N]
        if self.use_linear:
            # 纯线性头 + 残差（不使用分位网格）
            delta = self.head(h).permute(0, 2, 1)    # [B,4,N]
            self._aux = ()
            return ForecastOutput(prediction=base + delta)
        pred, p, q, tau = self.qmh(h)
        pred = base + pred
        self._aux = (p, q, tau)
        return ForecastOutput(prediction=pred)

    def compute_loss(self, pred, y, lam=1.0, thresh=-0.267, beta=1.0, bce=10.0):
        """同 QMHForecast：lam·L1 + beta·pinball(全网格) + bce·BCE。"""
        l1 = F.l1_loss(pred, y)
        if not self._aux:
            return l1
        p, q, tau = self._aux
        thresh_t = (torch.as_tensor(thresh, dtype=y.dtype, device=y.device).reshape(1, 1, -1)
                    if not torch.is_tensor(thresh)
                    else thresh.to(y.dtype).reshape(1, 1, -1))
        mask = (y > thresh_t).to(y.dtype)
        gate_loss = F.binary_cross_entropy(p.clamp(1e-6, 1 - 1e-6), mask)
        if float(mask.sum()) < 1:
            return lam * l1 + bce * gate_loss
        diff = y.unsqueeze(-1) - q
        pin = torch.maximum(tau * diff, (tau - 1.0) * diff)
        pin = (pin * mask.unsqueeze(-1)).sum() / (mask.sum() * q.shape[-1])
        return lam * l1 + beta * pin + bce * gate_loss


class EdgeAttnForecast(StaticGraphForecast):
    """MRG-GCN 的 GCN1/GCN2 换成零初始化边注意力；其余结构不变。"""

    def __init__(self, name, graphs, use_edge_feature=True, full_support=False,
                 score_scale=1.0):
        num_nodes = int(list(graphs)[0].shape[0])
        super().__init__(8, 4, num_nodes, list(graphs), hidden_dim=32, levels=6,
                         dropout=.1, relation_dropout=0., history_steps=96)
        self.gcn1 = EdgeAttnGCN(self.latent_dim, self._num_relations, dropout=.1,
                                use_edge_feature=use_edge_feature, full_support=full_support,
                                score_scale=score_scale)
        self.gcn2 = EdgeAttnGCN(self.latent_dim, self._num_relations, dropout=.1,
                                use_edge_feature=use_edge_feature, full_support=full_support,
                                score_scale=score_scale)


# ============================================================ 参数量对照

class WideHeadMRG(StaticGraphForecast):
    """参数量对照：MRG 原结构，head 换成两层 MLP 以匹配 QMH 的额外参数。"""

    def __init__(self, name, graphs):
        num_nodes = int(list(graphs)[0].shape[0])
        hd = 48 if name.endswith('_lin48') else 32
        super().__init__(8, 4, num_nodes, list(graphs), hidden_dim=hd, levels=6,
                         dropout=.1, relation_dropout=0., history_steps=96)
        self.head = nn.Sequential(nn.Linear(hd, 40), nn.GELU(), nn.Linear(40, 4))


# ============================================================ 构建

def build_night_model(name, graphs, zero_level=-0.267):
    if name in ('agcrn_matched', 'agcrn_full', 'gru_behavior', 'tcn', 'tcn_wide'):
        from evcs_station_graph.eventtime.models import build_model as build_frozen
        return build_frozen(name, graphs)
    if name in ('qnh_adp', 'adaptive_qmh'):
        from evcs_station_graph.eventtime.night_adaptive import build_adaptive_qmh
        return build_adaptive_qmh(name, graphs, zero_level)
    if name == 'qnh_agcrn':
        return QMHFullAGCRN(name, graphs, levels=8, zero_level=zero_level)
    if name == 'qnh_param_matched':
        return WideHeadMRG(name, graphs)
    if name in ('mrg_lin', 'mrg_lin48'):
        return WideHeadMRG(name, graphs)
    if name.startswith('qnh'):
        levels = int(name.split('_k')[-1]) if '_k' in name else 8
        return QMHForecast(name, graphs, levels=levels, zero_level=zero_level)
    if name.startswith('eattn'):
        scale = 0.1 if 'v2' in name else 1.0
        return EdgeAttnForecast(name, graphs,
                                use_edge_feature='nofeat' not in name,
                                full_support='fullsupport' in name,
                                score_scale=scale)
    raise ValueError(f'unknown night model {name}')
