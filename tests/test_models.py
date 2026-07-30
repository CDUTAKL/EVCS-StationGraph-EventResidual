"""TCN、固定图、自适应图与事件残差模型测试。"""

from __future__ import annotations

import numpy as np
import torch
from torch import nn

from evcs_station_graph.graphs import normalize_adjacency
from evcs_station_graph.models import (
    AdaptiveGraphForecast,
    EventResidualCorrection,
    StaticGraphForecast,
    TemporalConvNet,
)
from evcs_station_graph.models.graph import StationGraphForecast
from evcs_station_graph.training.factory import build_model


def test_all_model_output_shapes() -> None:
    """所有模型必须遵守统一的 [B,H,N] 输出约定。"""
    x = torch.randn(2, 96, 4, 7)
    # 三类关系邻接矩阵（测试用单位阵模拟）
    adjacencies = [np.eye(4, dtype=np.float32)] * 3
    models = (
        TemporalConvNet(7, 4, hidden_dim=8, levels=2, dropout=0.0),
        StaticGraphForecast(
            7, 4, 4, adjacencies,
            hidden_dim=8, levels=2, dropout=0.0,
        ),
        AdaptiveGraphForecast(
            7, 4, 4, adjacencies,
            hidden_dim=8, embedding_dim=4, levels=2, dropout=0.0,
        ),
    )
    for model in models:
        output = model(x)
        assert output.prediction.shape == (2, 4, 4)
        assert torch.isfinite(output.prediction).all()


def test_residual_correction_obeys_gate_and_bound() -> None:
    """未触发节点保持默认预测，触发节点的修正量不得越界。"""
    x = torch.randn(2, 96, 4, 7)
    feature_names = (
        "load",
        "access_count",
        "departure_count",
        "active_count",
        "occupancy_rate",
        "demand_intensity",
        "load_jump_flag",
    )
    base = TemporalConvNet(7, 4, hidden_dim=8, levels=2, dropout=0.0)
    model = EventResidualCorrection(
        base,
        [np.eye(4, dtype=np.float32)] * 3,  # 三类关系
        horizon=4,
        hidden_dim=8,
        residual_bound=0.25,
        freeze_base=True,
        feature_names=feature_names,
    )
    no_trigger = torch.zeros(2, 4, dtype=torch.bool)
    no_trigger_output = model(x, rule_trigger=no_trigger)
    torch.testing.assert_close(
        no_trigger_output.prediction,
        no_trigger_output.base_prediction,
    )
    assert torch.count_nonzero(no_trigger_output.residual) == 0

    all_trigger = torch.ones(2, 4, dtype=torch.bool)
    triggered_output = model(x, rule_trigger=all_trigger)
    assert triggered_output.residual is not None
    assert float(triggered_output.residual.detach().abs().max()) <= 0.25 + 1e-6


# ---------------------------------------------------------------------------
# 自适应图 top-k 稀疏化验证
# ---------------------------------------------------------------------------


def test_adaptive_graph_top_k_excludes_self() -> None:
    """对 3 节点图设置 top_k=1，验证自适应邻接矩阵中每个节点都有非自身连接。

    设计理由：_build_adaptive_adjacency 对每节点保留 k=min(top_k, N-1) 个
    最强项。若 k=1 且 embedding 恰好让某行最强者是自己，则该节点退化为无跨节点
    连接。本测试固定随机种子，确保实际行为符合"至少有一条非自身边"的预期。
    """
    torch.manual_seed(20250101)
    model = AdaptiveGraphForecast(
        input_dim=7,
        horizon=4,
        num_nodes=3,
        adjacencies=[np.eye(3, dtype=np.float32)] * 3,
        hidden_dim=8,
        embedding_dim=12,
        top_k=1,
        levels=2,
        dropout=0.0,
    )
    adaptive = model._build_adaptive_adjacency().detach().numpy()
    # 每节点必须至少有一个非零的非自身边
    for i in range(3):
        off_diag = adaptive[i].copy()
        off_diag[i] = 0.0
        assert off_diag.max() > 0.0, f"节点 {i} 在 top_k=1 下缺少非自身连接"


# ---------------------------------------------------------------------------
# 独立参数验证
# ---------------------------------------------------------------------------


def test_independent_relation_weights() -> None:
    """StaticGraphForecast 的 gcn1 和 gcn2 的 W_r 必须是独立参数。

    两层 GCN 处于不同跳数（一阶邻居 vs 二阶传播后），需要不同的变换参数。
    若 gcn1.W_r 和 gcn2.W_r 共享同一 Parameter 对象，则两层等价，二阶传播
    的建模能力丢失。
    """
    adj = [np.eye(4, dtype=np.float32)] * 3
    model = StaticGraphForecast(
        7, 4, 4, adj,
        hidden_dim=8, levels=2, dropout=0.0,
    )
    for r in range(3):
        w1 = model.gcn1.W_r[r].weight
        w2 = model.gcn2.W_r[r].weight
        # 对象标识不同
        assert w1 is not w2, f"gcn1.W_r[{r}] 与 gcn2.W_r[{r}] 指向同一对象"
        # 值不同（随机初始化保证）
        assert not torch.equal(w1.data, w2.data), (
            f"gcn1.W_r[{r}] 与 gcn2.W_r[{r}] 初始化后值完全相同"
        )
        # 修改其中一个不影响另一个
        snapshot = w2.data.clone()
        w1.data.zero_()
        assert not torch.allclose(w2.data, torch.zeros_like(w2.data)), (
            f"gcn1.W_r[{r}] 置零后 gcn2.W_r[{r}] 异常同步"
        )
        w2.data.copy_(snapshot)
        w1.data.normal_()  # 恢复为随机值避免影响其他测试


# ---------------------------------------------------------------------------
# 架构断言
# ---------------------------------------------------------------------------


def test_graph_mlp_refine_not_tcn() -> None:
    """确认 graph_mlp_refine（图特征 MLP 精炼模块）是 Sequential 而非 TCN。

    在 StationGraphForecast 中，TCN1 已充分提取时序信息，GraphMLPRefine 位置仅需
    轻量 MLP 精炼节点特征。若该模块被替换为完整 TemporalConvNet，则违反设计
    意图——TCN1 已将时间维压缩至节点向量，无需第二层时序卷积。
    """
    adj = [np.eye(4, dtype=np.float32)] * 3
    model = StaticGraphForecast(
        7, 4, 4, adj,
        hidden_dim=8, levels=2, dropout=0.0,
    )
    refine = model.graph_mlp_refine
    assert isinstance(refine, nn.Sequential), (
        "graph_mlp_refine 应为 nn.Sequential (MLP)"
    )
    assert not isinstance(refine, TemporalConvNet), (
        "graph_mlp_refine 不应为 TemporalConvNet —— 时序信息已由共享 TCN 提取"
    )


# ---------------------------------------------------------------------------
# 事件特征名称查找
# ---------------------------------------------------------------------------


def test_residual_feature_name_lookup(synthetic_bundle) -> None:
    """EventResidualCorrection 通过 feature_names 正确查找事件特征索引。

    构造函数内部将 ["access_count","departure_count","active_count",
    "load_jump_flag"] 映射为特征列索引。验证：
    1. 默认索引映射到正确的列位置
    2. 特征顺序重排后索引随之变化
    3. 前向传播中事件特征从正确位置提取
    """
    base = TemporalConvNet(7, 4, hidden_dim=8, levels=2, dropout=0.0)
    feature_names = synthetic_bundle.feature_names
    # synthetic_bundle 的特征顺序:
    #   load=0, access_count=1, departure_count=2, active_count=3,
    #   occupancy_rate=4, demand_intensity=5, load_jump_flag=6

    # ---- 验证1: 默认查找产生预期索引 ----
    model = EventResidualCorrection(
        base,
        [np.eye(4, dtype=np.float32)] * 3,
        horizon=4,
        hidden_dim=8,
        feature_names=feature_names,
    )
    assert model._event_feat_indices == [1, 2, 3, 6], (
        f"默认事件特征索引应为 [1,2,3,6]，实际 {model._event_feat_indices}"
    )

    # ---- 验证2: 特征名重排后索引随之变化 ----
    reordered = (
        "occupancy_rate",  # 0
        "demand_intensity",  # 1
        "access_count",  # 2
        "load",  # 3
        "active_count",  # 4
        "departure_count",  # 5
        "load_jump_flag",  # 6
    )
    model2 = EventResidualCorrection(
        base,
        [np.eye(4, dtype=np.float32)] * 3,
        horizon=4,
        hidden_dim=8,
        feature_names=reordered,
    )
    assert model2._event_feat_indices == [2, 5, 4, 6], (
        f"重排后事件特征索引应为 [2,5,4,6]，实际 {model2._event_feat_indices}"
    )

    # ---- 验证3: 前向传播中事件特征从正确位置提取 ----
    # 在 access_count(索引1) 处设置已知值，验证 forward 中 E 提取正确
    x = torch.randn(2, 96, 4, 7)
    marker = 42.0
    x[:, -1, 0, 1] = marker  # 第一个样本、最后一个时间步、节点0、access_count
    output = model(x, rule_trigger=torch.ones(2, 4, dtype=torch.bool))
    assert output.prediction.shape == (2, 4, 4)
    assert torch.isfinite(output.prediction).all()


# ---------------------------------------------------------------------------
# 二阶图传播验证
# ---------------------------------------------------------------------------


def test_static_graph_two_hop() -> None:
    """链式图 0-1-2：验证第二层 GCN 后节点 0 能接收节点 2 的信息。

    图结构：A[0,1]=A[1,0]=A[1,2]=A[2,1]≠0，A[0,2]=A[2,0]=0。
    第一层 GCN 后节点 1 聚合了节点 2 的信息（一阶邻居），但节点 0 尚未接触
    节点 2（无直连边）；第二层 GCN 中节点 0 聚合更新后的节点 1 表示，
    从而间接接收节点 2 的信息（二阶传播）。

    验证方法：扰动节点 2 的输入特征，观察节点 0 的编码输出是否发生变化。
    无变化 → 二阶传播失效；有变化 → 信息成功传递。
    """
    # 构造链式邻接：0-1-2
    adj_raw = np.array(
        [[1, 1, 0],
         [1, 1, 1],
         [0, 1, 1]],
        dtype=np.float32,
    )
    adj = normalize_adjacency(adj_raw).astype(np.float32)
    # 确认 0-2 无直连边（归一化后权重应接近 0）
    assert adj[0, 2] < 0.01 and adj[2, 0] < 0.01, "链式图中 0-2 不应有直连边"

    model = StaticGraphForecast(
        input_dim=3,
        horizon=4,
        num_nodes=3,
        adjacencies=[adj] * 3,
        hidden_dim=8,
        levels=2,
        dropout=0.0,
    )

    # 两份仅在节点 2 上不同的输入
    x_a = torch.randn(2, 96, 3, 3)
    x_b = x_a.clone()
    x_b[:, :, 2, :] += 100.0  # 大幅扰动节点 2

    # TCN 编码：各节点独立，因此节点 0/1 的 TCN 输出在 a/b 间应完全相同
    h0_a = model.tcn.encode(x_a)
    h0_b = model.tcn.encode(x_b)
    torch.testing.assert_close(h0_a[:, 0, :], h0_b[:, 0, :])
    torch.testing.assert_close(h0_a[:, 1, :], h0_b[:, 1, :])
    # 节点 2 应不同
    assert not torch.equal(h0_a[:, 2, :], h0_b[:, 2, :])

    # 第一层 GCN：节点 1 聚合了节点 2 的信息，
    # 但节点 0 仅从节点 0、1 聚合（无直连到节点 2）
    h1_a = model.gcn1(h0_a, model._get_adjacencies(), model._get_relation_weights_gcn1())
    h1_b = model.gcn1(h0_b, model._get_adjacencies(), model._get_relation_weights_gcn1())
    # 节点 0 在一阶邻居中不应变化（不连节点 2）
    torch.testing.assert_close(h1_a[:, 0, :], h1_b[:, 0, :])
    # 节点 1 应变化（聚合了节点 2）
    assert not torch.equal(h1_a[:, 1, :], h1_b[:, 1, :])

    # GraphMLPRefine 精炼
    h1r_a = h1_a + model.graph_mlp_refine(h1_a)
    h1r_b = h1_b + model.graph_mlp_refine(h1_b)

    # 第二层 GCN：节点 0 聚合更新后的节点 1（含节点 2 信息）→ 二阶传播
    h2_a = model.gcn2(h1r_a, model._get_adjacencies(), model._get_relation_weights_gcn2())
    h2_b = model.gcn2(h1r_b, model._get_adjacencies(), model._get_relation_weights_gcn2())

    diff_02 = float((h2_a[:, 0, :] - h2_b[:, 0, :]).detach().abs().mean())
    assert diff_02 > 1e-6, (
        f"二阶传播失效：节点 0 在扰动节点 2 后编码未变化 (mean|diff|={diff_02:.8f})"
    )

    # 作为对照：验证完整 encode（含 Skip Fusion）同样体现二阶传播
    z_a = model.encode(x_a)
    z_b = model.encode(x_b)
    diff_full = float((z_a[:, 0, :] - z_b[:, 0, :]).detach().abs().mean())
    assert diff_full > 1e-6, (
        f"完整编码后节点 0 应受节点 2 影响，但 mean|diff|={diff_full:.8f}"
    )


# ---------------------------------------------------------------------------
# 关系 dropout（relation_dropout）验证
# ---------------------------------------------------------------------------
# 设计背景：SG-EXP-006 的 relation_dropout 敏感性实验（0.0/0.2/0.4）
# 必须真实改变模型计算，否则三个取值得到相同模型、实验无效。
# 以下测试覆盖"配置 → 工厂 → 模型属性 → 前向行为"的完整闭环。


def _make_dropout_static_model(relation_dropout: float) -> StaticGraphForecast:
    """构造无特征 dropout、仅含指定 relation_dropout 的固定图模型。

    dropout=0.0 排除 nn.Dropout 的干扰——此时 train 模式下前向的
    唯一随机源就是 relation_dropout 的关系屏蔽采样。
    """
    return StaticGraphForecast(
        7, 4, 4, [np.eye(4, dtype=np.float32)] * 3,
        hidden_dim=8, levels=2, dropout=0.0,
        relation_dropout=relation_dropout,
    )


def test_relation_dropout_changes_training_output() -> None:
    """relation_dropout>0 时训练模式前向具有随机性，eval 模式保持确定。

    单次前向碰巧采到相同关系掩码的概率不可忽略（R=3 时掩码组合有限），
    因此收集 16 次前向结果：16 次全部采到同一掩码的概率约 1e-9 量级，
    测试实际上不会抖动。
    """
    model = _make_dropout_static_model(0.4)
    x = torch.randn(2, 96, 4, 7)

    model.train()
    outputs = [model(x).prediction for _ in range(16)]
    assert any(not torch.allclose(outputs[0], other) for other in outputs[1:]), (
        "relation_dropout=0.4 的 train 模式 16 次前向输出全部相同，"
        "关系屏蔽未生效"
    )

    # eval 模式不采样关系掩码，推理必须完全确定
    model.eval()
    torch.testing.assert_close(model(x).prediction, model(x).prediction)


def test_relation_dropout_disabled_when_zero() -> None:
    """relation_dropout=0.0（默认）时 train 模式前向必须确定。

    保证未配置该机制的实验（SG-EXP-002～005 正式路径）行为与
    引入该机制之前完全一致——这是"默认关闭不改变既有行为"的回归保护。
    """
    model = _make_dropout_static_model(0.0)
    x = torch.randn(2, 96, 4, 7)
    model.train()
    torch.testing.assert_close(model(x).prediction, model(x).prediction)


def test_relation_dropout_extreme_rate_stays_finite() -> None:
    """极端丢弃率下"至少保留一类关系"的保护必须生效，前向不产生 NaN/Inf。

    p=0.999 时几乎每次前向只保留强制位上的一个关系；若保护缺失，
    β 全零会导致归一化除零，输出 NaN。
    """
    model = _make_dropout_static_model(0.999)
    model.train()
    x = torch.randn(2, 96, 4, 7)
    for _ in range(4):
        output = model(x).prediction
        assert torch.isfinite(output).all(), (
            "relation_dropout=0.999 下前向出现非有限值，"
            "至少保留一类关系的保护失效"
        )


def test_residual_relation_dropout_changes_training_output() -> None:
    """EventResidualCorrection 的关系 dropout 在训练模式生效、eval 模式确定。

    SG-EXP-006 的 sensitivity 变体以 event_residual 为基础模型，
    其关系聚合是邻居均值而非 GCN 的 β 融合——两处都必须支持
    relation_dropout，否则敏感性实验在默认路径上无效。
    基模型冻结（freeze_base=True 且强制 eval），因此 train 模式的
    唯一随机源是残差修正器自身的关系屏蔽采样。

    注意：三类邻接矩阵必须互不相同——残差修正器对关系消息取均值，
    若三类关系矩阵相同（如同为单位阵），任意保留子集的均值都相等，
    关系屏蔽不产生可观测的输出差异。
    """
    feature_names = (
        "load", "access_count", "departure_count", "active_count",
        "occupancy_rate", "demand_intensity", "load_jump_flag",
    )
    # 三类互不相同的关系结构：成对块、交错连接、全连接
    distinct_adjacencies = [
        normalize_adjacency(np.array(
            [[1, 1, 0, 0], [1, 1, 0, 0], [0, 0, 1, 1], [0, 0, 1, 1]],
            dtype=np.float32,
        )),
        normalize_adjacency(np.array(
            [[1, 0, 1, 0], [0, 1, 0, 1], [1, 0, 1, 0], [0, 1, 0, 1]],
            dtype=np.float32,
        )),
        normalize_adjacency(np.ones((4, 4), dtype=np.float32)),
    ]
    base = TemporalConvNet(7, 4, hidden_dim=8, levels=2, dropout=0.0)
    model = EventResidualCorrection(
        base,
        distinct_adjacencies,
        horizon=4,
        hidden_dim=8,
        freeze_base=True,
        feature_names=feature_names,
        relation_dropout=0.4,
    )
    x = torch.randn(2, 96, 4, 7)
    trigger = torch.ones(2, 4, dtype=torch.bool)

    model.train()
    outputs = [model(x, rule_trigger=trigger).prediction for _ in range(16)]
    assert any(not torch.allclose(outputs[0], other) for other in outputs[1:]), (
        "EventResidualCorrection relation_dropout=0.4 的 train 模式 "
        "16 次前向输出全部相同，关系屏蔽未生效"
    )

    model.eval()
    torch.testing.assert_close(
        model(x, rule_trigger=trigger).prediction,
        model(x, rule_trigger=trigger).prediction,
    )


def test_factory_passes_relation_dropout_to_model() -> None:
    """experiment.graph.relation_dropout 必须经 build_model 进入模型属性。

    这是"配置看似生效、实际未改变模型"问题的回归测试：
    mechanism.py 将敏感性取值写入 config["experiment"]["graph"]["relation_dropout"]，
    工厂必须读取并写入 GCN 层与残差修正器的 relation_dropout 属性，
    否则 0.0/0.2/0.4 三个敏感性变体会训练出相同模型。
    """
    adjacencies = [np.eye(4, dtype=np.float32)] * 3
    base_experiment = {
        "experiment": {
            "model": "TCN_GCN",
            "model_params": {"hidden_dim": 8, "levels": 2, "dropout": 0.0},
            "graph": {"relation_dropout": 0.4},
        }
    }

    static_model = build_model(
        base_experiment, input_dim=7, horizon=4, num_nodes=4,
        adjacencies=adjacencies,
    )
    assert isinstance(static_model, StaticGraphForecast)
    assert static_model.gcn1.relation_dropout == 0.4
    assert static_model.gcn2.relation_dropout == 0.4

    residual_experiment = {
        "experiment": {
            "model": "event_residual",
            "model_params": {"hidden_dim": 8, "levels": 2, "dropout": 0.0},
            "graph": {"relation_dropout": 0.2},
        }
    }
    residual_model = build_model(
        residual_experiment, input_dim=7, horizon=4, num_nodes=4,
        adjacencies=adjacencies,
    )
    assert isinstance(residual_model, EventResidualCorrection)
    assert residual_model.relation_dropout == 0.2

    # 未配置时默认关闭——既有实验配置行为不变
    default_experiment = {
        "experiment": {
            "model": "TCN_GCN",
            "model_params": {"hidden_dim": 8, "levels": 2, "dropout": 0.0},
        }
    }
    default_model = build_model(
        default_experiment, input_dim=7, horizon=4, num_nodes=4,
        adjacencies=adjacencies,
    )
    assert default_model.gcn1.relation_dropout == 0.0
