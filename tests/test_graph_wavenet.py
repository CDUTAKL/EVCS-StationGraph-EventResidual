"""GraphWaveNet 模型单元测试。"""

from __future__ import annotations

import numpy as np
import pytest
import torch

from evcs_station_graph.models.graph_wavenet import GraphWaveNetForecast


NUM_NODES = 10
HISTORY = 96
FORECAST = 4
FEATURES = 7
BATCH = 2


def _make_adjacencies(num_nodes: int = NUM_NODES, value: float = 1.0) -> list[np.ndarray]:
    """构造三类固定关系邻接矩阵，用于预定义图测试。"""
    return [np.eye(num_nodes, dtype=np.float32) * value for _ in range(3)]


def _build_model(adjacencies, seed: int = 42) -> GraphWaveNetForecast:
    """按固定随机种子构造 GraphWaveNet 模型。"""
    torch.manual_seed(seed)
    return GraphWaveNetForecast(
        input_dim=FEATURES,
        horizon=FORECAST,
        num_nodes=NUM_NODES,
        adjacencies=adjacencies,
        hidden_dim=32,
        embedding_dim=12,
        dropout=0.1,
        kernel_size=2,
    )


def test_forward_output_shape():
    """forward 应返回 [B, H, N] 预测。"""
    model = _build_model(_make_adjacencies())
    x = torch.randn(BATCH, HISTORY, NUM_NODES, FEATURES)
    out = model(x)
    assert out.prediction.shape == (BATCH, FORECAST, NUM_NODES)


def test_encode_output_shape():
    """encode 应返回 [B, N, D] 节点隐表示。"""
    model = _build_model(_make_adjacencies())
    x = torch.randn(BATCH, HISTORY, NUM_NODES, FEATURES)
    latent = model.encode(x)
    assert latent.shape == (BATCH, NUM_NODES, model.latent_dim)


def test_all_parameters_receive_gradients():
    """所有可学习参数（含 E1/E2）都应在反向传播后获得梯度。"""
    model = _build_model(_make_adjacencies())
    model.train()
    x = torch.randn(BATCH, HISTORY, NUM_NODES, FEATURES)
    out = model(x).prediction
    loss = out.sum()
    loss.backward()
    for name, param in model.named_parameters():
        assert param.grad is not None, f"参数 {name} 没有梯度"
        assert not torch.all(param.grad == 0), f"参数 {name} 梯度全零"


def test_causality():
    """因果性：中间时刻隐表示不受未来输入扰动；最后输出受输入扰动影响。"""
    model = _build_model(_make_adjacencies())
    model.eval()
    x = torch.randn(BATCH, HISTORY, NUM_NODES, FEATURES)

    mid = 48  # 取中间时刻作为因果性检查点
    # 完整序列的中间时刻隐表示
    full_features = model._temporal_features(x)  # [B, N, D, T]
    mid_full = full_features[..., mid]

    # 截断序列到 mid 时刻，其最后时刻应等于完整序列的 mid 时刻（无未来信息泄漏）
    x_trunc = x[:, : mid + 1, :, :]
    trunc_features = model._temporal_features(x_trunc)
    mid_trunc = trunc_features[..., -1]
    assert torch.allclose(mid_full, mid_trunc, atol=1e-5)

    # 扰动最后 10 步未来输入，完整序列的末尾隐表示应改变
    x_pert = x.clone()
    x_pert[:, -10:, :, :] += 1.0
    out = model.encode(x)
    out_pert = model.encode(x_pert)
    assert not torch.allclose(out, out_pert, atol=1e-6)


def test_predefined_graph_affects_output():
    """预定义图参与计算：全零邻接与非零邻接产生不同输出。"""
    seed = 123
    x = torch.randn(BATCH, HISTORY, NUM_NODES, FEATURES)
    model_zero = _build_model([np.zeros((NUM_NODES, NUM_NODES), dtype=np.float32)] * 3, seed=seed)
    model_eye = _build_model(_make_adjacencies(value=1.0), seed=seed)
    model_zero.eval()
    model_eye.eval()
    out_zero = model_zero(x).prediction
    out_eye = model_eye(x).prediction
    assert not torch.allclose(out_zero, out_eye, atol=1e-6)


def test_rule_trigger_kwarg_accepted():
    """forward 接受并忽略 rule_trigger 等额外关键字参数。"""
    model = _build_model(_make_adjacencies())
    x = torch.randn(BATCH, HISTORY, NUM_NODES, FEATURES)
    trigger = torch.ones(BATCH, HISTORY, dtype=torch.float32)
    out = model(x, rule_trigger=trigger)
    assert out.prediction.shape == (BATCH, FORECAST, NUM_NODES)


def test_invalid_input_dimension():
    """输入维度错误时应直接抛出异常。"""
    model = _build_model(_make_adjacencies())
    x = torch.randn(BATCH, HISTORY, NUM_NODES)  # 缺少特征维
    with pytest.raises(ValueError):
        model.encode(x)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"num_nodes": 0},
        {"horizon": 0},
        {"input_dim": 0},
        {"hidden_dim": 0},
        {"embedding_dim": 0},
        {"kernel_size": 0},
        {"dropout": -0.1},
        {"dropout": 1.5},
    ],
)
def test_invalid_constructor_hyperparameters(kwargs):
    """非法构造参数应直接抛出异常，避免后续产生隐晦的 PyTorch 错误。"""
    base = {
        "input_dim": FEATURES,
        "horizon": FORECAST,
        "num_nodes": NUM_NODES,
        "adjacencies": _make_adjacencies(),
        "hidden_dim": 32,
        "embedding_dim": 12,
        "dropout": 0.1,
        "kernel_size": 2,
    }
    base.update(kwargs)
    with pytest.raises(ValueError):
        GraphWaveNetForecast(**base)


def test_empty_adjacencies():
    """空邻接矩阵序列应直接抛出异常。"""
    with pytest.raises(ValueError):
        GraphWaveNetForecast(
            input_dim=FEATURES,
            horizon=FORECAST,
            num_nodes=NUM_NODES,
            adjacencies=[],
        )


def test_mismatched_adjacency_shape():
    """邻接矩阵形状与 num_nodes 不一致时应直接抛出异常。"""
    bad_adj = [np.eye(NUM_NODES + 1, dtype=np.float32) for _ in range(3)]
    with pytest.raises(ValueError):
        GraphWaveNetForecast(
            input_dim=FEATURES,
            horizon=FORECAST,
            num_nodes=NUM_NODES,
            adjacencies=bad_adj,
        )


def test_input_node_count_mismatch():
    """输入节点数与模型不一致时应直接抛出异常。"""
    model = _build_model(_make_adjacencies())
    x = torch.randn(BATCH, HISTORY, NUM_NODES + 1, FEATURES)
    with pytest.raises(ValueError):
        model.encode(x)


def test_input_feature_mismatch():
    """输入特征维与模型不一致时应直接抛出异常。"""
    model = _build_model(_make_adjacencies())
    x = torch.randn(BATCH, HISTORY, NUM_NODES, FEATURES + 1)
    with pytest.raises(ValueError):
        model.encode(x)
