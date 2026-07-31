"""单种子掩码重建预训练快速验证（D6-2）：预训练 → 冻结底座微调 vs 从头训练。

目的（决策工具，非正式实验）：
  判断"同域掩码重建预训练"方向（第 5 章 5.2 候选主线）是否值得投入
  正式三种子实验——比较验证集 MAE：
    路线 A：掩码重建预训练 → 冻结 TCN/GCN 底座 → 只训练预测头
    路线 B：从头训练（标准流程对照）

方法（与正式实验口径一致的部分）：
  - 数据：NodeWindowDataset（标准化特征/目标、冻结切分、无泄漏）
  - 关系图：build_relation_set（训练期、top_k=3、与 SG-EXP-003 一致）
  - 模型：StaticGraphForecast（input_dim=7, horizon=4, hidden=32, levels=6）
  - 评价：验证集 scaled MAE（与 engine 早停口径一致）

预训练细节：
  - 任务：输入 96 步窗口，随机 mask 15% 时间步（跨节点一致，保持图结构
    完整——让 GCN 学会用邻居信息补全缺失时刻，这正是预训练的目标信号）
  - mask 位置置 0（标准化空间近似"缺失"占位符），MSE 仅计算 mask 位置
  - 重建头：Linear(latent_dim, H×F)，重建全部 7 维特征
  - 固定轮数（默认 30），不做早停——快速验证先看信号

判定逻辑：
  路线 A 验证 MAE 比路线 B 低 ≥1% → 预训练有正信号，值得正式实验
  0~1% → 边际，正式实验收益不确定
  更差 → 无信号，方向降级为消融素材

用法（服务器 GPU）：
  export PYTHONPATH=src
  CUDA_VISIBLE_DEVICES=0 python scripts/validate_pretrain_single_seed.py
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
from evcs_station_graph.graphs import build_relation_set
from evcs_station_graph.models.graph import StaticGraphForecast
from evcs_station_graph.reproducibility import set_global_seed, write_json
from evcs_station_graph.training.engine import _make_loader, _select_device

# mask 比例 15%（BERT 掩码语言模型的常用比例）：
# 太低则重建任务太容易（仅靠相邻步插值），太高则上下文不足无法重建
DEFAULT_MASK_RATIO = 0.15
# 预训练轮数：快速验证固定 30 轮（约 2-3 分钟），不做早停——
# 先看正负信号，正式实验再引入早停与三种子
DEFAULT_PRETRAIN_EPOCHS = 30
# 增益阈值：验证 MAE 相对改善 ≥1% 视为正信号（远高于种子间噪声 0.0002）
GAIN_THRESHOLD = 0.01


class MaskedPretrainWrapper(nn.Module):
    """TCN+GCN 底座 + 掩码重建头（[B,N,D] → [B,N,H,F]）。

    预训练阶段使用：输入被 mask 的历史窗口，重建全部 7 维特征。
    微调阶段弃用本包装，直接使用底座模型的预测头。
    """

    def __init__(self, base_model: StaticGraphForecast,
                 history_steps: int, num_features: int) -> None:
        super().__init__()
        self.base = base_model
        self.history_steps = history_steps
        self.num_features = num_features
        # 重建头：latent [B,N,D] → [B,N,H×F]，reshape 为 [B,N,H,F]
        self.recon_head = nn.Linear(base_model.latent_dim, history_steps * num_features)

    def forward(self, x: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        """重建被 mask 的特征。

        x：标准化特征窗口 [B,H,N,F]（mask 位置已置 0）
        mask：[B,H] 布尔，True 表示该时间步被 mask
        返回重建结果 [B,N,H,F]。
        """
        latent = self.base.encode(x)  # [B,N,D]
        recon = self.recon_head(latent)  # [B,N,H×F]
        return recon.reshape(
            latent.shape[0], latent.shape[1], self.history_steps, self.num_features
        )


def _sample_masks(
    batch_size: int, history_steps: int, device: torch.device,
    rng: np.random.Generator, mask_ratio: float,
) -> torch.Tensor:
    """为一批样本采样跨节点一致的 mask（每样本独立，[B,H] bool）。

    跨节点一致（mask 同一时间步的全部节点）的理由：保留图结构信息——
    被 mask 的时刻其他节点仍可见，GCN 需要学会用邻居补全，这正是
    预训练要强化的表示能力。
    """
    r = rng.random((batch_size, history_steps))
    mask = (r < mask_ratio)
    # 双向防御（审查发现：原注释与代码相反且只覆盖一半）：
    # 1. 整窗全可见（mask 全 False，mask_ratio 极端小时）→ 强制遮住一步，
    #    保证预训练确实有重建目标
    # 2. 整窗全遮（mask 全 True）→ 强制留一步可见，保证重建有输入依据
    for i in range(batch_size):
        if not mask[i].any():
            mask[i, int(rng.integers(history_steps))] = True
        elif mask[i].all():
            mask[i, int(rng.integers(history_steps))] = False
    return torch.from_numpy(mask).to(device)


def _run_pretrain(
    wrapper: MaskedPretrainWrapper,
    loader: DataLoader,
    device: torch.device,
    rng: np.random.Generator,
    *,
    epochs: int, mask_ratio: float, lr: float,
) -> List[float]:
    """掩码重建预训练（固定轮数），返回逐轮 MSE。"""
    optimizer = torch.optim.AdamW(
        wrapper.parameters(), lr=lr, weight_decay=1e-4,
    )
    history = []
    for _ in range(epochs):
        wrapper.train()
        total_loss = 0.0
        total_count = 0
        for batch in loader:
            x = batch["x"].to(device)  # [B,H,N,F]
            batch_size = len(x)
            mask = _sample_masks(batch_size, wrapper.history_steps, device, rng, mask_ratio)
            # mask 位置置 0：标准化空间（0≈全局均值）近似"缺失"占位
            x_masked = x * (~mask)[:, :, None, None].float()
            recon = wrapper(x_masked, mask)  # [B,N,H,F]
            target = x.permute(0, 2, 1, 3)  # [B,N,H,F]
            weight = mask[:, None, :, None].float()  # [B,1,H,1]
            loss = ((recon - target) ** 2 * weight).sum() / weight.sum().clamp(min=1.0)
            if not torch.isfinite(loss):
                raise FloatingPointError("预训练损失出现非有限值")
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(wrapper.parameters(), max_norm=5.0)
            optimizer.step()
            total_loss += float(loss.detach()) * batch_size
            total_count += batch_size
        history.append(total_loss / total_count)
    return history


@torch.no_grad()
def _validation_mae(model: nn.Module, loader: DataLoader, device: torch.device) -> float:
    """验证集 scaled MAE（与 engine 早停口径一致：标准 L1、缩放空间）。"""
    model.eval()
    total_loss = 0.0
    total_count = 0
    for batch in loader:
        x = batch["x"].to(device)
        y = batch["y"].to(device)
        batch_size = len(x)
        loss = nn.functional.l1_loss(model(x).prediction, y)
        total_loss += float(loss) * batch_size
        total_count += batch_size
    if total_count == 0:
        raise RuntimeError("验证集没有可用样本")
    return total_loss / total_count


def _run_finetune(
    model: StaticGraphForecast,
    loaders: Dict[str, DataLoader],
    device: torch.device,
    *,
    freeze_base: bool, epochs: int, patience: int, lr: float,
) -> Dict[str, Any]:
    """训练预测头（可选冻结底座），早停取验证最优，返回最优验证 MAE。"""
    if freeze_base:
        # 冻结 TCN/GCN/融合全部底座参数，仅预测头可训练（含关系权重 β，
        # 它们属于 encode 路径，一并冻结——预训练已为它们定形）
        for parameter in model.parameters():
            parameter.requires_grad = False
        model.head.weight.requires_grad = True
        model.head.bias.requires_grad = True
    parameters = [p for p in model.parameters() if p.requires_grad]
    if not parameters:
        raise RuntimeError("没有可训练参数")
    optimizer = torch.optim.AdamW(parameters, lr=lr, weight_decay=1e-4)
    criterion = nn.L1Loss()

    best_validation = float("inf")
    best_state: Dict[str, torch.Tensor] | None = None
    stale_epochs = 0
    for _ in range(1, epochs + 1):
        model.train()
        for batch in loaders["train"]:
            x = batch["x"].to(device)
            y = batch["y"].to(device)
            optimizer.zero_grad(set_to_none=True)
            loss = criterion(model(x).prediction, y)
            if not torch.isfinite(loss):
                raise FloatingPointError("训练损失出现非有限值")
            loss.backward()
            torch.nn.utils.clip_grad_norm_(parameters, max_norm=5.0)
            optimizer.step()
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
    return {"best_validation_mae": best_validation}


def _build_model(bundle: Any, config_top_k: int) -> StaticGraphForecast:
    """构建 SG-EXP-003 口径的 StaticGraphForecast（hidden=32, levels=6）。"""
    train_end = int(bundle.split_origins["train"][-1])
    relation_set = build_relation_set(
        bundle.features[: train_end + 1],
        bundle.targets[: train_end + 1],
        bundle.feature_names,
        top_k=config_top_k,
    )
    model = StaticGraphForecast(
        input_dim=len(bundle.feature_names),
        horizon=4,
        num_nodes=len(bundle.node_ids),
        adjacencies=relation_set.as_list(),
        hidden_dim=32,
        levels=6,
        dropout=0.1,
    )
    return model


def main() -> None:
    parser = argparse.ArgumentParser(description="D6-2 单种子掩码重建预训练快速验证")
    parser.add_argument("--dataset", default="data/processed/SG-DATA-005-primary-tensor.npz")
    parser.add_argument("--output-dir", default="outputs/analysis/pretrain_quick_check")
    parser.add_argument("--seed", type=int, default=2024)
    parser.add_argument("--pretrain-epochs", type=int, default=DEFAULT_PRETRAIN_EPOCHS)
    parser.add_argument("--finetune-epochs", type=int, default=60)
    parser.add_argument("--patience", type=int, default=8)
    parser.add_argument("--mask-ratio", type=float, default=DEFAULT_MASK_RATIO)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--device", default="auto")
    args = parser.parse_args()

    set_global_seed(args.seed)
    bundle = load_tensor_bundle(args.dataset)
    device = _select_device(args.device)
    spec = WindowSpec(history_steps=96, forecast_steps=4)
    datasets = {
        split: NodeWindowDataset(bundle, split, spec)
        for split in ("train", "validation")
    }
    loaders = {
        "train": _make_loader(datasets["train"], 256, True, args.seed),
        "validation": _make_loader(datasets["validation"], 256, False, args.seed),
    }
    rng = np.random.default_rng(args.seed)
    started = time.perf_counter()

    # ========== 路线 A：预训练 → 冻结底座微调 ==========
    print(f"=== 路线 A：掩码重建预训练（{args.pretrain_epochs} 轮）→ 冻结微调 ===", flush=True)
    pretrain_model = _build_model(bundle, args.top_k).to(device)
    wrapper = MaskedPretrainWrapper(
        pretrain_model, spec.history_steps, len(bundle.feature_names),
    ).to(device)
    pretrain_history = _run_pretrain(
        wrapper, loaders["train"], device, rng,
        epochs=args.pretrain_epochs, mask_ratio=args.mask_ratio, lr=args.lr,
    )
    print(f"  预训练结束，末轮 MSE={pretrain_history[-1]:.6f}", flush=True)
    finetune_result = _run_finetune(
        pretrain_model, loaders, device,
        freeze_base=True, epochs=args.finetune_epochs,
        patience=args.patience, lr=args.lr,
    )
    val_pretrain = finetune_result["best_validation_mae"]
    print(f"  冻结微调最优验证 MAE={val_pretrain:.6f}", flush=True)

    # ========== 路线 B：从头训练（对照） ==========
    print(f"=== 路线 B：从头训练（对照） ===", flush=True)
    scratch_model = _build_model(bundle, args.top_k).to(device)
    scratch_result = _run_finetune(
        scratch_model, loaders, device,
        freeze_base=False, epochs=args.finetune_epochs,
        patience=args.patience, lr=args.lr,
    )
    val_scratch = scratch_result["best_validation_mae"]
    print(f"  从头训练最优验证 MAE={val_scratch:.6f}", flush=True)

    # ========== 比较与判定 ==========
    improvement = (val_scratch - val_pretrain) / val_scratch
    if improvement >= GAIN_THRESHOLD:
        verdict = f"通过：预训练验证 MAE 相对下降 {improvement:.1%}，值得正式三种子实验"
    elif improvement > 0:
        verdict = f"边际：预训练相对下降 {improvement:.1%}（<{GAIN_THRESHOLD:.0%}），正式实验收益不确定"
    else:
        verdict = f"未通过：预训练相对变化 {improvement:.1%}（更差），方向降级为消融素材"
    print(f"\n验证 MAE：预训练路线 {val_pretrain:.6f} vs 从头 {val_scratch:.6f}"
          f"（相对 {improvement:+.1%}）")
    print(f"判定：{verdict}")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json({
        "analysis": "D6-2 masked reconstruction pretrain quick check",
        "seed": args.seed,
        "device": str(device),
        "mask_ratio": args.mask_ratio,
        "pretrain_epochs": args.pretrain_epochs,
        "pretrain_last_mse": float(pretrain_history[-1]),
        "pretrain_mse_history": pretrain_history,
        "val_mae_pretrain_route": val_pretrain,
        "val_mae_from_scratch": val_scratch,
        "relative_improvement": improvement,
        "verdict": verdict,
        "elapsed_seconds": time.perf_counter() - started,
    }, output_dir / "pretrain_quick_check.json")
    print(f"结果已写入：{output_dir / 'pretrain_quick_check.json'}", flush=True)


if __name__ == "__main__":
    main()
