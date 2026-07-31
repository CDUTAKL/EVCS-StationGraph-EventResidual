"""AGCRN 基线模型（SG-EXP-008）测试。"""

from __future__ import annotations

import numpy as np
import pytest
import torch
import torch.nn.functional as F

from evcs_station_graph.models.agcrn import AGCRNForecast


def _make_model(num_nodes: int = 4) -> AGCRNForecast:
    """构造小型 AGCRN 模型供测试使用。"""
    return AGCRNForecast(
        input_dim=7,
        horizon=4,
        num_nodes=num_nodes,
        adjacencies=[np.eye(num_nodes, dtype=np.float32)] * 3,
        hidden_dim=8,
        embedding_dim=4,
        dropout=0.0,
    )


def test_agcrn_output_shape() -> None:
    """AGCRN 必须遵守统一的 [B, H, N] 输出约定。"""
    model = _make_model(num_nodes=4)
    x = torch.randn(2, 96, 4, 7)
    output = model(x)
    assert output.prediction.shape == (2, 4, 4)
    assert torch.isfinite(output.prediction).all()


def test_agcrn_encode_shape() -> None:
    """encode 必须返回 [B, N, D] 节点隐表示。"""
    model = _make_model(num_nodes=4)
    x = torch.randn(2, 96, 4, 7)
    latent = model.encode(x)
    assert latent.shape == (2, 4, model.latent_dim)
    assert torch.isfinite(latent).all()


def test_agcrn_gradient_flow() -> None:
    """反向传播必须到达所有参数，包括节点嵌入 E。"""
    model = _make_model(num_nodes=4)
    model.train()
    x = torch.randn(2, 96, 4, 7)
    y = torch.randn(2, 4, 4)
    loss = F.l1_loss(model(x).prediction, y)
    loss.backward()

    params = list(model.named_parameters())
    assert len(params) > 0, "AGCRN 必须存在可学习参数"
    for name, param in params:
        assert param.grad is not None, f"参数 {name} 未收到梯度"
        assert torch.isfinite(param.grad).all(), f"参数 {name} 梯度含非有限值"
        assert param.grad.abs().max() > 0, f"参数 {name} 梯度全零，梯度流被截断"


def test_adaptive_adjacency_probability_matrix() -> None:
    """自适应邻接 A_adp 形状为 [N, N] 且逐行和为 1。"""
    model = _make_model(num_nodes=4)
    x = torch.randn(2, 96, 4, 7)

    # 前向两次，验证 adjacency 一致且满足概率矩阵约束
    out1 = model(x)
    out2 = model(x)
    adj1 = out1.adjacency
    adj2 = out2.adjacency

    assert adj1 is not None, "ForecastOutput 应包含 adjacency"
    assert adj1.shape == (4, 4), f"A_adp 形状应为 [4, 4]，实际 {adj1.shape}"
    torch.testing.assert_close(adj1, adj2)
    torch.testing.assert_close(
        adj1.sum(dim=-1), torch.ones(4, dtype=adj1.dtype),
    )
    assert (adj1 >= 0).all(), "A_adp 作为 Softmax 输出不得含负值"


def test_adaptive_adjacency_is_data_driven() -> None:
    """A_adp 必须随节点嵌入变化而变化，体现数据驱动特性。"""
    model = _make_model(num_nodes=4)
    adj_before = model._build_adaptive_adjacency().detach().clone()

    # 修改节点嵌入后重新生成邻接矩阵
    with torch.no_grad():
        model.node_embedding.add_(torch.randn_like(model.node_embedding) * 0.5)
    adj_after = model._build_adaptive_adjacency().detach().clone()

    assert not torch.allclose(adj_before, adj_after), (
        "A_adp 在节点嵌入改变后未变化，不是数据驱动"
    )


def test_forward_accepts_rule_trigger_kwargs() -> None:
    """forward 应接受 rule_trigger 等额外关键字参数且不报错。"""
    model = _make_model(num_nodes=4)
    x = torch.randn(2, 96, 4, 7)
    trigger = torch.zeros(2, 4, dtype=torch.bool)
    output = model(x, rule_trigger=trigger)
    assert output.prediction.shape == (2, 4, 4)
    assert torch.isfinite(output.prediction).all()


def test_agcrn_rejects_wrong_num_nodes() -> None:
    """输入节点数与模型声明不一致时必须显式报错。"""
    model = _make_model(num_nodes=4)
    x = torch.randn(2, 96, 5, 7)  # 5 个节点，与模型声明的 4 不符
    with pytest.raises(ValueError, match="节点数"):
        model.encode(x)


def test_agcrn_rejects_non_4d_input() -> None:
    """encode 收到非 4 维输入时必须显式报错。"""
    model = _make_model(num_nodes=4)
    x = torch.randn(2, 96, 4)  # 缺失特征维
    with pytest.raises(ValueError, match="AGCRNForecast"):
        model.encode(x)
