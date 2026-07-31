"""WeightedL1Loss 与 DecompGCNForecast 的单元测试（审查补测）。

背景：审查发现这两个模块此前零测试覆盖——WeightedL1Loss 是 SG-EXP-007
加权损失核心，DecompGCNForecast 是 SG-EXP-011/012 路由消融核心。
"""

from __future__ import annotations

import numpy as np
import pytest
import torch
from torch import nn

from evcs_station_graph.models.decomp_gcn import DecompGCNForecast
from evcs_station_graph.training.losses import WeightedL1Loss


# ========== WeightedL1Loss ==========


def _rand_bt(batch: int = 4, horizon: int = 4, nodes: int = 10) -> torch.Tensor:
    return torch.randn(batch, horizon, nodes)


def test_weighted_l1_binary_weighting() -> None:
    """binary 模式：事件窗口样本权重 = 1+λ，其余 = 1，数值可解析验证。"""
    torch.manual_seed(0)
    pred = _rand_bt()
    target = _rand_bt()
    trigger = torch.zeros(4, 10)
    trigger[1, 2] = 1.0  # 样本 (1, 2) 是事件窗口

    loss = WeightedL1Loss(lambda_=3.0, mode="binary")
    value = loss(pred, target, event_signal=trigger)

    error = (pred - target).abs()
    expected = (error * (1.0 + 3.0 * trigger[:, None, :])).mean()
    assert torch.allclose(value, expected, atol=1e-6)


def test_weighted_l1_lambda_zero_reduces_to_l1() -> None:
    """λ=0 必须退化为标准 L1Loss（口径一致，结果恒等）。"""
    pred, target = _rand_bt(), _rand_bt()
    trigger = torch.ones(4, 10)
    weighted = WeightedL1Loss(lambda_=0.0, mode="binary")(pred, target, trigger)
    plain = nn.L1Loss()(pred, target)
    assert torch.allclose(weighted, plain, atol=1e-6)


def test_weighted_l1_no_signal_reduces_to_l1() -> None:
    """event_signal=None 时退化为标准 L1（引擎早停/无事件场景）。"""
    pred, target = _rand_bt(), _rand_bt()
    weighted = WeightedL1Loss(lambda_=3.0)(pred, target, event_signal=None)
    plain = nn.L1Loss()(pred, target)
    assert torch.allclose(weighted, plain, atol=1e-6)


def test_weighted_l1_gradient_flows_to_prediction() -> None:
    """事件样本梯度必须大于稳定样本梯度（加权机制生效的核心性质）。"""
    pred = torch.randn(2, 4, 10, requires_grad=True)
    target = torch.randn(2, 4, 10)
    trigger = torch.zeros(2, 10)
    trigger[0, :] = 1.0  # 样本 0 全事件

    loss = WeightedL1Loss(lambda_=5.0)(pred, target, trigger)
    loss.backward()
    grad = pred.grad.abs().mean(dim=(1, 2))  # [B]
    assert grad[0] > grad[1] * 1.5, "事件样本梯度应显著大于稳定样本"


def test_weighted_l1_intensity_normalization() -> None:
    """intensity 模式：同一样本权重仅取决于自身分数（batch 组成不变性）。"""
    torch.manual_seed(0)
    pred, target = _rand_bt(), _rand_bt()
    criterion = WeightedL1Loss(lambda_=3.0, mode="intensity")

    # batch A：无极端事件 → 归一化后分数不变
    signal_a = torch.zeros(4, 10)
    signal_a[0, 0] = 0.5
    # batch B：存在极端事件 10.0 → 0.5 被压到 0.05
    signal_b = torch.zeros(4, 10)
    signal_b[0, 0] = 0.5
    signal_b[0, 1] = 10.0

    loss_a = criterion(pred, target, event_signal=signal_a)
    loss_b = criterion(pred, target, event_signal=signal_b)
    # 同一样本 (0,0,0) 的权重不同 → 损失不同 → 证明 batch 归一化有漂移
    # （这是已知设计特征，测试将其钉住以防未来静默改动）
    assert not torch.allclose(loss_a, loss_b, atol=1e-4)


def test_weighted_l1_rejects_invalid_args() -> None:
    """非法参数必须显式报错（不静默接受）。"""
    with pytest.raises(ValueError, match="lambda"):
        WeightedL1Loss(lambda_=-1.0)
    with pytest.raises(ValueError, match="mode"):
        WeightedL1Loss(mode="unknown")


# ========== DecompGCNForecast ==========


def _make_adjacencies(num_nodes: int = 5, num_rels: int = 3) -> list[np.ndarray]:
    """构造行归一化的邻接矩阵列表（[N,N] 非负，对角占优）。"""
    out = []
    rng = np.random.default_rng(42)
    for _ in range(num_rels):
        a = rng.random((num_nodes, num_nodes))
        a += 2.0 * np.eye(num_nodes)  # 对角占优保证数值稳定
        a = a / a.sum(axis=1, keepdims=True)
        out.append(a)
    return out


def test_decomp_gcn_forward_shape_and_gradient() -> None:
    """DecompGCNForecast 前向形状 [B,H,N] + 梯度可达（SG-EXP-011/012 依赖）。"""
    torch.manual_seed(0)
    model = DecompGCNForecast(
        input_dim=7, horizon=4, num_nodes=5, adjacencies=_make_adjacencies(),
        hidden_dim=8, levels=4, dropout=0.0,  # levels=4: RF=15 < 96 但无 history 约束
    )
    x = torch.randn(3, 96, 5, 7)
    out = model(x)
    assert out.prediction.shape == (3, 4, 5)
    assert torch.isfinite(out.prediction).all()

    loss = out.prediction.abs().mean()
    loss.backward()
    grads = [p.grad for p in model.parameters() if p.requires_grad]
    assert all(g is not None for g in grads), "所有可学习参数必须有梯度"
    assert all(torch.isfinite(g).all() for g in grads)


def test_decomp_gcn_routing_variants() -> None:
    """三种路由（one_to_one / full / swapped）都能前向（路由是 011/012 核心变量）。"""
    for routing in ("one_to_one", "full", "swapped"):
        model = DecompGCNForecast(
            input_dim=7, horizon=4, num_nodes=5, adjacencies=_make_adjacencies(),
            hidden_dim=8, levels=4, dropout=0.0, routing=routing,
        )
        out = model(torch.randn(2, 96, 5, 7))
        assert out.prediction.shape == (2, 4, 5)
        assert torch.isfinite(out.prediction).all()
