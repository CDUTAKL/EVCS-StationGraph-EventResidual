"""变体快速验证（D6-4）：门控专业化 / BiTCN / 节点差异化参数，单种子对比。

目的（决策工具，非正式实验）：
  为第 5 章消融增强（5.3 候选）快速筛选三个变体，与 D6-2 的从头训练
  基线（验证 MAE=0.016328，同流程同种子）对比：
    --variant gate-mi  门控专业化：损失加关系消息去相关项（高斯近似下的
                      互信息最小化代理），迫使三条边各司其职
    --variant bitcn    BiTCN：时间编码器升级为双向 TCN（正向 + 时间反转），
                      历史窗口内合法（无未来泄漏）
    --variant napl     节点差异化参数：GCN1/GCN2 输出后加 per-node 投影
                      （单位阵初始化 = 残差式，初始等于无差异化）
    --variant gru      GRU 时序基线（第 3 章主表对照，无图逐节点独立）

判定逻辑（各变体独立）：
  gate-mi：去相关损失显著下降（>30%）且验证 MAE 恶化 <5% → 专业化可行
  bitcn/napl：验证 MAE 相对基线下降 ≥1% → 通过；恶化 <5% → 持平（消融素材）；
              更差 → 降级

用法（服务器 GPU，三变体并行）：
  export PYTHONPATH=src
  CUDA_VISIBLE_DEVICES=0 nohup .venv/bin/python scripts/validate_variant_single_seed.py \
    --variant gate-mi > outputs/variant_gate_mi.log 2>&1 &
  CUDA_VISIBLE_DEVICES=1 nohup .venv/bin/python scripts/validate_variant_single_seed.py \
    --variant bitcn > outputs/variant_bitcn.log 2>&1 &
  CUDA_VISIBLE_DEVICES=0 nohup .venv/bin/python scripts/validate_variant_single_seed.py \
    --variant napl > outputs/variant_napl.log 2>&1 &
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader

from evcs_station_graph.data import (
    NodeWindowDataset,
    WindowSpec,
    load_tensor_bundle,
)
from evcs_station_graph.evaluation import (
    apply_frozen_event_rule,
    fit_frozen_event_rule,
    stratified_metrics,
)
from evcs_station_graph.graphs import build_relation_set
from evcs_station_graph.models.common import (
    ForecastModel,
    ForecastOutput,
    sample_relation_keep_mask,
)
from evcs_station_graph.models.graph import StaticGraphForecast, MultiRelationGatedGCN
from evcs_station_graph.models.tcn import TemporalConvNet
from evcs_station_graph.reproducibility import set_global_seed, write_json
from evcs_station_graph.training.engine import _make_loader, _predict, _select_device

# D6-2 同流程同种子（2024）从头训练基线：验证 MAE（scaled 空间）
BASELINE_VAL_MAE = 0.016328
# 判定阈值：通过 = 相对基线下降 ≥1%；持平 = 恶化 <5%；更差 = 降级
GAIN_THRESHOLD = 0.01
DEGRADE_LIMIT = 0.05


# ========== 变体 A：门控专业化（消息记录 GCN + 去相关损失） ==========

class MessageRecordingGCN(MultiRelationGatedGCN):
    """覆写 forward 记录逐关系加权消息（互信息/去相关分析用），权重结构不变。"""

    def forward(
        self,
        H: torch.Tensor,
        adjacencies: list[torch.Tensor],
        relation_weights: torch.Tensor,
    ) -> torch.Tensor:
        beta = torch.softmax(relation_weights, dim=0)  # [R]
        # 关系 dropout（与父类 forward 一致，默认 0.0 时无影响）
        if self.training and self.relation_dropout > 0.0:
            keep = sample_relation_keep_mask(
                beta.numel(), self.relation_dropout, beta.device,
            )
            beta = beta * keep
            beta = beta / beta.sum().clamp(min=1e-12)
        messages: List[torch.Tensor] = []
        for r, (adj, W) in enumerate(zip(adjacencies, self.W_r)):
            neighbor_msg = torch.einsum("nm,bmd->bnd", adj, H)
            messages.append(beta[r] * W(neighbor_msg))
        self.recorded_messages = messages  # 供训练循环取去相关损失
        M = sum(messages)
        gate_input = torch.cat([H, M], dim=-1)  # [B, N, 2D]
        G = torch.sigmoid(self.W_gate(gate_input))
        H_tilde = G * M + (1.0 - G) * H
        return self.norm(H + self.dropout(H_tilde))


def _decoupling_loss(messages: List[torch.Tensor]) -> torch.Tensor:
    """关系消息去相关损失：逐对消息的 Pearson 相关平方和。

    高斯近似下互信息 I(u;v) = -0.5·log(1-r²) 是相关性的单调函数，
    最小化 r² 等价于最小化高斯互信息——作为互信息专业化的实用代理。
    梯度可直接回传到模型（对消息可微）。
    """
    total = torch.zeros((), device=messages[0].device)
    for i in range(len(messages)):
        for j in range(i + 1, len(messages)):
            a = messages[i].flatten()
            b = messages[j].flatten()
            a_centered = a - a.mean()
            b_centered = b - b.mean()
            numerator = (a_centered * b_centered).sum()
            denominator = (a_centered.square().sum() * b_centered.square().sum()).sqrt()
            r = numerator / denominator.clamp(min=1e-12)
            total = total + r.square()
    return total


class GateMiGraphForecast(StaticGraphForecast):
    """门控专业化变体：GCN1/GCN2 替换为消息记录版本（从头训练）。"""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        dropout = float(kwargs.get("dropout", 0.1))
        super().__init__(*args, **kwargs)
        self.gcn1 = MessageRecordingGCN(self.latent_dim, self._num_relations, dropout)
        self.gcn2 = MessageRecordingGCN(self.latent_dim, self._num_relations, dropout)


# ========== 变体 B：BiTCN 时间编码 ==========

class BiTemporalConvNet(nn.Module):
    """双向 TCN：正向编码 + 时间反转编码后融合。

    反转对象是 96 步历史窗口内部（x 的 T 维），不涉及预测目标，
    因此是合法的双向——窗口内的"未来"（靠近预测起点的步）已经发生。
    """

    def __init__(
        self,
        input_dim: int,
        horizon: int,
        *,
        hidden_dim: int = 32,
        levels: int = 6,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        self.forward_net = TemporalConvNet(
            input_dim, horizon, hidden_dim=hidden_dim,
            levels=levels, dropout=dropout,
        )
        self.backward_net = TemporalConvNet(
            input_dim, horizon, hidden_dim=hidden_dim,
            levels=levels, dropout=dropout,
        )
        # head 不使用（与 StationGraphForecast 一致，删除避免死参数）
        del self.forward_net.head, self.backward_net.head
        self.fusion = nn.Linear(hidden_dim * 2, hidden_dim)
        self.latent_dim = hidden_dim
        self.horizon = horizon

    def encode(self, x: torch.Tensor) -> torch.Tensor:
        h_forward = self.forward_net.encode(x)  # [B,N,D]
        h_backward = self.backward_net.encode(torch.flip(x, dims=[1]))  # 时间反转
        return self.fusion(torch.cat([h_forward, h_backward], dim=-1))  # [B,N,D]


class BitcnGraphForecast(StaticGraphForecast):
    """BiTCN 变体：仅替换时间编码器，GCN/融合/预测头结构不变。"""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        input_dim = int(self.tcn.network[0].conv.in_channels)
        self.tcn = BiTemporalConvNet(
            input_dim, self.horizon,
            hidden_dim=int(kwargs.get("hidden_dim", 32)),
            levels=int(kwargs.get("levels", 6)),
            dropout=float(kwargs.get("dropout", 0.1)),
        )


# ========== 变体 C：节点差异化参数（NAPL 简化版） ==========

class NaplGraphForecast(StaticGraphForecast):
    """节点差异化参数：GCN1/GCN2 输出后加 per-node 投影。

    投影初始化为单位矩阵（残差式：初始输出等于无差异化），
    训练学习每个节点的特异性变换。参数量 2×N×D×D = 20K（10 节点可忽略）。
    """

    def __init__(
        self, input_dim: int, horizon: int, num_nodes: int,
        adjacencies: List[Any], **kwargs: Any,
    ) -> None:
        super().__init__(input_dim, horizon, num_nodes, adjacencies, **kwargs)
        hidden = self.latent_dim
        eye = torch.eye(hidden)
        self.node_proj1 = nn.Parameter(eye.repeat(num_nodes, 1, 1))
        self.node_proj2 = nn.Parameter(eye.repeat(num_nodes, 1, 1))

    def encode(self, x: torch.Tensor) -> torch.Tensor:
        h0 = self.tcn.encode(x)  # [B,N,D]
        adjacencies = self._get_adjacencies()
        h1 = self.gcn1(h0, adjacencies, self._get_relation_weights_gcn1())
        # per-node 投影：einsum("bnd,ndd->bnd")——每个节点用独立变换矩阵
        h1 = torch.einsum("bnd,ndd->bnd", h1, self.node_proj1)
        h1_refined = h1 + self.graph_mlp_refine(h1)
        h2 = self.gcn2(h1_refined, adjacencies, self._get_relation_weights_gcn2())
        h2 = torch.einsum("bnd,ndd->bnd", h2, self.node_proj2)
        h_fused = self.skip_fusion(torch.cat([h0, h1, h2], dim=-1))
        h_fused = self.skip_norm(h_fused)
        return self.skip_dropout(self.skip_activation(h_fused))


# ========== GRU 时序基线（无图对照，表 1 主表基线） ==========

class GruForecast(ForecastModel):
    """GRU 时序基线：逐节点独立 GRU 编码 → 预测头（无图）。

    与 TCN 基线同口径（逐节点独立预测），用于第 3 章主表对比：
    GRU 是循环时序基线，与 TCN（卷积时序基线）互为对照。
    """

    def __init__(
        self, input_dim: int, horizon: int, num_nodes: int,
        *,
        hidden_dim: int = 32, num_layers: int = 1,
    ) -> None:
        super().__init__()
        # 逐节点共享同一 GRU（与 TCN 的逐节点独立卷积口径一致）
        self.gru = nn.GRU(input_dim, hidden_dim, num_layers, batch_first=True)
        self.head = nn.Linear(hidden_dim, horizon)
        self.latent_dim = hidden_dim
        self.horizon = horizon

    def encode(self, x: torch.Tensor) -> torch.Tensor:
        """[B,T,N,F] → [B,N,D]：节点维展开为批维，GRU 编码后取最后一步。"""
        batch, time, nodes, features = x.shape
        # permute/reshape：[B,T,N,F] → [B*N,T,F]（逐节点独立序列）
        per_node = x.permute(0, 2, 1, 3).reshape(batch * nodes, time, features)
        output, _ = self.gru(per_node)  # [B*N,T,D]
        return output[:, -1, :].reshape(batch, nodes, -1)  # [B,N,D]

    def forecast_from_latent(self, latent: torch.Tensor) -> torch.Tensor:
        return self.head(latent).permute(0, 2, 1).contiguous()

    def forward(self, x: torch.Tensor, **_: torch.Tensor) -> ForecastOutput:
        prediction = self.forecast_from_latent(self.encode(x))
        return ForecastOutput(prediction=prediction)


# ========== 通用训练 ==========

def _build_model(variant: str, bundle: Any, top_k: int) -> StaticGraphForecast:
    """按变体构建模型（hidden=32, levels=6, 与 SG-EXP-003 口径一致）。"""
    train_end = int(bundle.split_origins["train"][-1])
    relation_set = build_relation_set(
        bundle.features[: train_end + 1],
        bundle.targets[: train_end + 1],
        bundle.feature_names,
        top_k=top_k,
    )
    common = dict(
        input_dim=len(bundle.feature_names),
        horizon=4,
        num_nodes=len(bundle.node_ids),
        adjacencies=relation_set.as_list(),
        hidden_dim=32,
        levels=6,
        dropout=0.1,
    )
    if variant == "gate-mi":
        return GateMiGraphForecast(**common)
    if variant == "bitcn":
        return BitcnGraphForecast(**common)
    if variant == "napl":
        return NaplGraphForecast(**common)
    if variant == "gru":
        # GRU 时序基线：无图，不需要邻接矩阵
        return GruForecast(
            input_dim=len(bundle.feature_names), horizon=4,
            num_nodes=len(bundle.node_ids), hidden_dim=32,
        )
    raise ValueError(f"未知变体：{variant}")


@torch.no_grad()
def _validation_mae(model: nn.Module, loader: DataLoader, device: torch.device) -> float:
    model.eval()
    total_loss = 0.0
    total_count = 0
    for batch in loader:
        x = batch["x"].to(device)
        y = batch["y"].to(device)
        batch_size = len(x)
        total_loss += float(nn.functional.l1_loss(model(x).prediction, y)) * batch_size
        total_count += batch_size
    if total_count == 0:
        raise RuntimeError("验证集没有可用样本")
    return total_loss / total_count


def _run_training(
    model: StaticGraphForecast,
    loaders: Dict[str, DataLoader],
    device: torch.device,
    *,
    variant: str, epochs: int, patience: int, lr: float, decouple_lambda: float,
) -> Dict[str, Any]:
    """训练变体模型（早停），返回最优验证 MAE 与去相关损失轨迹。"""
    parameters = [p for p in model.parameters() if p.requires_grad]
    if not parameters:
        raise RuntimeError("没有可训练参数")
    optimizer = torch.optim.AdamW(parameters, lr=lr, weight_decay=1e-4)
    criterion = nn.L1Loss()

    best_validation = float("inf")
    best_state: Dict[str, torch.Tensor] | None = None
    stale_epochs = 0
    decouple_history: List[float] = []
    for _ in range(1, epochs + 1):
        model.train()
        epoch_decouple = 0.0
        for batch in loaders["train"]:
            x = batch["x"].to(device)
            y = batch["y"].to(device)
            optimizer.zero_grad(set_to_none=True)
            loss = criterion(model(x).prediction, y)
            if variant == "gate-mi":
                messages = model.gcn1.recorded_messages
                decouple = _decoupling_loss(messages)
                loss = loss + decouple_lambda * decouple
                epoch_decouple += float(decouple.detach()) / len(loaders["train"])
            if not torch.isfinite(loss):
                raise FloatingPointError("训练损失出现非有限值")
            loss.backward()
            torch.nn.utils.clip_grad_norm_(parameters, max_norm=5.0)
            optimizer.step()
        decouple_history.append(epoch_decouple)
        validation = _validation_mae(model, loaders["validation"], device)
        if validation < best_validation - 1e-8:
            best_validation = validation
            best_state = {
                key: value.detach().cpu().clone()
                for key, value in model.state_dict().items()
            }
            stale_epochs = 0
        else:
            stale_epochs += 1
            if stale_epochs >= patience:
                break
    if best_state is None:
        raise RuntimeError("训练未生成有效检查点")
    model.load_state_dict(best_state)
    return {
        "best_validation_mae": best_validation,
        "decouple_history": decouple_history,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="D6-4 变体快速验证")
    parser.add_argument("--variant", required=True,
                        choices=["gate-mi", "bitcn", "napl", "gru"])
    parser.add_argument("--dataset", default="data/processed/SG-DATA-005-primary-tensor.npz")
    parser.add_argument("--output-dir", default="outputs/analysis/variant_quick_check")
    parser.add_argument("--seed", type=int, default=2024)
    parser.add_argument("--epochs", type=int, default=60)
    parser.add_argument("--patience", type=int, default=8)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--decouple-lambda", type=float, default=0.05,
                        help="gate-mi 去相关损失权重（λ）")
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--device", default="auto")
    args = parser.parse_args()

    set_global_seed(args.seed)
    bundle = load_tensor_bundle(args.dataset)
    device = _select_device(args.device)
    spec = WindowSpec(history_steps=96, forecast_steps=4)
    datasets = {
        split: NodeWindowDataset(bundle, split, spec)
        for split in ("train", "validation", "test")
    }
    loaders = {
        "train": _make_loader(datasets["train"], 256, True, args.seed),
        "validation": _make_loader(datasets["validation"], 256, False, args.seed),
        "test": _make_loader(datasets["test"], 256, False, args.seed),
    }
    # 事件规则与 trigger 矩阵（与正式评价口径一致，测试集仅执行冻结规则）
    rule = fit_frozen_event_rule(bundle, quantile=0.95, window_extension=2)
    trigger_by_origin = np.zeros((len(bundle.timestamps_ns), len(bundle.node_ids)), dtype=bool)
    for ds in datasets.values():
        trigger_by_origin[ds.origins] = apply_frozen_event_rule(bundle, ds.origins, rule)
    started = time.perf_counter()

    model = _build_model(args.variant, bundle, args.top_k).to(device)
    result = _run_training(
        model, loaders, device, variant=args.variant,
        epochs=args.epochs, patience=args.patience,
        lr=args.lr, decouple_lambda=args.decouple_lambda,
    )
    # ---- 测试集评价（全局/事件/稳定窗口，物理量纲） ----
    predictions = _predict(model, loaders["test"], device, trigger_by_origin, bundle)
    test_metrics = stratified_metrics(
        predictions["truth"], predictions["prediction"],
        target_event=predictions["target_event"],
        node_ids=bundle.node_ids.tolist(),
    )
    test_report = {
        "global_mae": test_metrics["global"]["mae"],
        "global_rmse": test_metrics["global"]["rmse"],
        "event_mae": test_metrics["event_window"]["mae"],
        "stable_mae": test_metrics["stable_window"]["mae"],
    }
    val_mae = result["best_validation_mae"]
    relative = (val_mae - BASELINE_VAL_MAE) / BASELINE_VAL_MAE

    # ---- 判定（按变体） ----
    if args.variant == "gate-mi":
        decouple = result["decouple_history"]
        first, last = decouple[0], decouple[-1]
        drop = (first - last) / max(first, 1e-12)
        if drop > 0.30 and relative < DEGRADE_LIMIT:
            verdict = (f"通过：去相关损失下降 {drop:.0%} 且 MAE 恶化仅 {relative:.1%}"
                       f"（<{DEGRADE_LIMIT:.0%}）→ 专业化可行")
        else:
            verdict = (f"未通过：去相关损失变化 {drop:.0%}（目标 >30%），"
                       f"MAE 相对基线 {relative:+.1%}")
        extra = {"decouple_first": first, "decouple_last": last,
                 "decouple_drop": drop}
    else:
        if relative <= -GAIN_THRESHOLD:
            verdict = f"通过：验证 MAE 相对基线下降 {-relative:.1%}（≥{GAIN_THRESHOLD:.0%}）"
        elif relative < DEGRADE_LIMIT:
            verdict = f"持平：验证 MAE 相对基线 {relative:+.1%}（作消融素材）"
        else:
            verdict = f"未通过：验证 MAE 相对基线恶化 {relative:.1%}（≥{DEGRADE_LIMIT:.0%}）"
        extra = {}

    print(f"变体 {args.variant}：验证 MAE={val_mae:.6f}（基线 {BASELINE_VAL_MAE:.6f}，"
          f"相对 {relative:+.1%}）")
    print(f"测试集：global={test_report['global_mae']:.5f} "
          f"event={test_report['event_mae']:.4f} stable={test_report['stable_mae']:.5f}")
    if extra:
        print(f"  去相关损失：首轮 {extra['decouple_first']:.4f} → 末轮 "
              f"{extra['decouple_last']:.4f}（下降 {extra['decouple_drop']:.0%}）")
    print(f"判定：{verdict}")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json({
        "analysis": "D6-4 variant quick check",
        "variant": args.variant,
        "seed": args.seed,
        "device": str(device),
        "baseline_val_mae": BASELINE_VAL_MAE,
        "val_mae": val_mae,
        "relative_change": relative,
        "verdict": verdict,
        "test_metrics": test_report,
        **extra,
        "elapsed_seconds": time.perf_counter() - started,
    }, output_dir / f"variant_{args.variant}.json")
    print(f"结果已写入：{output_dir / f'variant_{args.variant}.json'}", flush=True)


if __name__ == "__main__":
    main()
