"""SG-EXP-014：EERM 环境不变学习分析实验。

将训练数据按事件状态划分为两个环境（稳定窗口 vs 事件窗口），
在训练时施加跨环境表示不变性惩罚，验证"事件特征是否为伪相关"。

实验设计：
  - 模型：StaticGraph（与 SG-EXP-003 同架构）
  - 环境标记：event_score > 0 → 事件环境(e=1)，否则 → 稳定环境(e=0)
  - 不变性惩罚：L_inv = ||mean(H_e0) - mean(H_e1)||²
    强制两个环境的隐表示均值接近
  - 总损失：L = L_pred + λ * L_inv
  - λ sweep: {0.0, 0.01, 0.1, 1.0, 10.0}
  - 3 种子 × 5 λ 值 = 15 次训练

预期结果：
  若 λ 增大 → event 环境 MAE 显著上升而 stable 环境不变 →
  事件特征对通用预测是"伪相关"，强制不变性会丢弃事件特征。
  这从根本上解释了 EventResidual 和加权损失为何失败。

用法：
  .venv/bin/python scripts/run_eerm_invariant.py \
    --project configs/project.yaml \
    --output-root outputs/experiments/SG-EXP-014
"""

from __future__ import annotations

import argparse
import gc
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader

from evcs_station_graph.config import dump_yaml, load_experiment_config
from evcs_station_graph.data import NodeWindowDataset, TensorBundle, WindowSpec, load_tensor_bundle
from evcs_station_graph.evaluation import (
    apply_frozen_event_rule,
    fit_frozen_event_rule,
    four_cell_diagnostics,
    stratified_metrics,
    visible_event_scores,
)
from evcs_station_graph.graphs import build_relation_set
from evcs_station_graph.models.graph import StaticGraphForecast
from evcs_station_graph.reproducibility import (
    environment_snapshot,
    set_global_seed,
    write_json,
)
from evcs_station_graph.training.engine import (
    _make_loader,
    _predict,
    _select_device,
    _write_predictions,
    _write_training_log,
)


def _build_environment_labels(
    bundle: TensorBundle,
    datasets: dict[str, NodeWindowDataset],
) -> dict[str, np.ndarray]:
    """为每个 split 构建环境标签：0=稳定, 1=事件。

    事件分数 > 0 的时间步被标记为事件环境。
    标签形状为 [num_samples]（每个预测起点一个标签）。
    """
    rule = fit_frozen_event_rule(bundle, quantile=0.95, window_extension=2)
    # 计算全时间轴的事件分数
    score_stats = {
        key: np.asarray(value, dtype=np.float32)
        for key, value in rule.score_stats.items()
    }
    all_scores = np.zeros((len(bundle.timestamps_ns), len(bundle.node_ids)), dtype=np.float32)
    for split_name, ds in datasets.items():
        all_scores[ds.origins] = visible_event_scores(
            bundle, ds.origins, score_stats=score_stats,
        )
    # 每个 origin 的环境标签：任一节点有事件分数 > 0 即为事件环境
    env_labels: dict[str, np.ndarray] = {}
    for split_name, ds in datasets.items():
        origin_scores = all_scores[ds.origins]  # [N_origins, N_nodes]
        # 对每个预测起点，取所有节点的最大事件分数
        max_scores = origin_scores.max(axis=1)  # [N_origins]
        env_labels[split_name] = (max_scores > 0).astype(np.int64)
        n_event = int(env_labels[split_name].sum())
        n_total = len(env_labels[split_name])
        print(f"  {split_name}: {n_event}/{n_total} 事件环境样本 "
              f"({100*n_event/max(n_total,1):.1f}%)", flush=True)
    return env_labels


def _mean_hidden_representation(
    model: StaticGraphForecast,
    X: torch.Tensor,
) -> torch.Tensor:
    """计算输入 batch 的隐表示均值 [D]。

    通过 encode 获取 [B, N, D]，在 batch 和 node 维取平均。
    """
    latent = model.encode(X)  # [B, N, D]
    return latent.mean(dim=(0, 1))  # [D]


def train_eerm_single_seed(
    config: dict,
    bundle: TensorBundle,
    seed: int,
    output_dir: Path,
    env_labels: dict[str, np.ndarray],
    lam: float,
    device: torch.device,
) -> dict:
    """训练单个种子的 EERM 不变学习模型。"""
    set_global_seed(seed)
    output_dir.mkdir(parents=True, exist_ok=True)
    training = config["experiment"].get("training", {})
    spec = WindowSpec(
        history_steps=int(config["project"]["history_steps"]),
        forecast_steps=int(config["project"]["forecast_steps"]),
    )
    datasets = {
        split: NodeWindowDataset(bundle, split, spec)
        for split in ("train", "validation", "test")
    }
    batch_size = int(training.get("batch_size", 256))
    loaders = {
        "train": _make_loader(datasets["train"], batch_size, True, seed),
        "validation": _make_loader(datasets["validation"], batch_size, False, seed),
        "test": _make_loader(datasets["test"], batch_size, False, seed),
    }

    # 模型（与 SG-EXP-003 同架构）
    graph_cfg = config["experiment"].get("graph", {})
    params_cfg = config["experiment"].get("model_params", {})
    adjacencies = build_relation_set(
        bundle.features[: int(bundle.split_origins["train"][-1]) + 1],
        bundle.targets[: int(bundle.split_origins["train"][-1]) + 1],
        bundle.feature_names,
        top_k=int(graph_cfg.get("top_k", 3)),
    ).as_list()
    model = StaticGraphForecast(
        input_dim=len(bundle.feature_names),
        horizon=spec.forecast_steps,
        num_nodes=len(bundle.node_ids),
        adjacencies=adjacencies,
        hidden_dim=int(params_cfg.get("hidden_dim", 32)),
        levels=int(params_cfg.get("levels", 6)),
        dropout=float(params_cfg.get("dropout", 0.1)),
    ).to(device)

    optimizer = torch.optim.AdamW(
        [p for p in model.parameters() if p.requires_grad],
        lr=float(training.get("learning_rate", 1e-3)),
        weight_decay=float(training.get("weight_decay", 1e-4)),
    )
    criterion = nn.L1Loss()

    # 事件规则
    rule = fit_frozen_event_rule(bundle, quantile=0.95, window_extension=2)
    trigger_by_origin = np.zeros((len(bundle.timestamps_ns), len(bundle.node_ids)), dtype=bool)
    for ds in datasets.values():
        trigger_by_origin[ds.origins] = apply_frozen_event_rule(bundle, ds.origins, rule)

    # 训练集的环境标签映射（origin_index → env_label）
    # 注意：batch 的 origin_index 是绝对时间步索引（0..T_total-1），
    # 而 env_labels["train"] 是相对长度 [N_train]——必须展开为 [T_total] 绝对索引数组，
    # 否则按绝对索引取值会越界（ISSUE：origin_index > N_train）
    train_env = np.zeros(len(bundle.timestamps_ns), dtype=np.int64)
    train_env[datasets["train"].origins] = env_labels["train"]

    best_state = None
    best_validation = float("inf")
    patience = int(training.get("patience", 8))
    epochs = int(training.get("epochs", 60))
    stale = 0
    log_rows: list[dict] = []
    started = time.perf_counter()

    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0
        total_l1 = 0.0
        total_inv = 0.0
        total_count = 0

        for batch in loaders["train"]:
            x = batch["x"].to(device)
            y = batch["y"].to(device)
            n = len(x)
            origin_idx = batch["origin_index"].numpy()
            batch_env = torch.from_numpy(train_env[origin_idx]).to(device)  # [B]

            optimizer.zero_grad(set_to_none=True)
            pred = model(x, rule_trigger=torch.zeros(n, 0, device=device)).prediction
            loss_l1 = criterion(pred, y)

            # 不变性惩罚：稳定环境与事件环境的隐表示均值差的 L2 范数
            loss_inv = torch.tensor(0.0, device=device)
            mask_e0 = (batch_env == 0)
            mask_e1 = (batch_env == 1)
            if mask_e0.any() and mask_e1.any():
                # 分别计算两个环境的隐表示（需要重新 encode 以获取中间表示）
                h_e0 = _mean_hidden_representation(model, x[mask_e0])
                h_e1 = _mean_hidden_representation(model, x[mask_e1])
                loss_inv = (h_e0 - h_e1).pow(2).sum()

            loss = loss_l1 + lam * loss_inv

            if not torch.isfinite(loss):
                raise FloatingPointError(f"EERM 训练损失非有限值 (epoch={epoch})")
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
            optimizer.step()

            total_loss += float(loss.detach()) * n
            total_l1 += float(loss_l1.detach()) * n
            total_inv += float(loss_inv.detach()) * n
            total_count += n

        # ---- 验证 ----
        model.eval()
        val_total = 0.0
        val_count = 0
        with torch.no_grad():
            for batch in loaders["validation"]:
                x = batch["x"].to(device)
                y = batch["y"].to(device)
                n = len(x)
                out = model(x, rule_trigger=torch.zeros(n, 0, device=device))
                val_total += float(criterion(out.prediction, y)) * n
                val_count += n
        val_loss = val_total / max(val_count, 1)

        log_rows.append({
            "epoch": epoch, "train_loss": total_loss / max(total_count, 1),
            "train_l1": total_l1 / max(total_count, 1),
            "train_inv": total_inv / max(total_count, 1),
            "validation_mae": val_loss, "lambda": lam,
        })

        if val_loss < best_validation - 1e-8:
            best_validation = val_loss
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            stale = 0
        else:
            stale += 1
            if stale >= patience:
                break

    if best_state is None:
        raise RuntimeError("EERM 训练未生成有效检查点")
    model.load_state_dict(best_state)
    elapsed = time.perf_counter() - started

    # ---- 测试 ----
    predictions = _predict(model, loaders["test"], device, trigger_by_origin, bundle)
    metrics = stratified_metrics(
        predictions["truth"], predictions["prediction"],
        target_event=predictions["target_event"],
        node_ids=bundle.node_ids.tolist(),
    )
    four_cells = four_cell_diagnostics(
        predictions["truth"], predictions["prediction"],
        target_event=predictions["target_event"],
        rule_trigger=predictions["rule_trigger"],
    )
    metrics["four_cell"] = four_cells
    metrics["training"] = {
        "seed": seed, "lambda": lam,
        "epochs_completed": len(log_rows),
        "best_validation_mae": best_validation,
        "elapsed_seconds": elapsed,
        "device": str(device),
        "trainable_parameters": sum(p.numel() for p in model.parameters() if p.requires_grad),
    }

    torch.save({
        "model_state": best_state, "seed": seed, "lambda": lam,
        "best_validation_mae": best_validation,
    }, output_dir / "model.pt")
    _write_training_log(log_rows, output_dir / "training_log.csv")
    write_json(metrics, output_dir / "metrics.json")
    _write_predictions(bundle, datasets["test"].origins, predictions, output_dir / "predictions.csv.gz")

    return {"seed": seed, "lambda": lam, "global": metrics["global"],
            "event_window": metrics["event_window"], "stable_window": metrics["stable_window"]}


def main() -> None:
    parser = argparse.ArgumentParser(description="SG-EXP-014 EERM 不变学习分析")
    parser.add_argument("--project", required=True, help="项目配置文件路径")
    parser.add_argument("--output-root", default="outputs/experiments/SG-EXP-014")
    parser.add_argument("--device", default="auto")
    parser.add_argument("--dataset", default="data/processed/SG-DATA-005-primary-tensor.npz")
    args = parser.parse_args()

    # 加载项目配置 + SG-EXP-014 实验配置
    exp_config_path = Path(__file__).resolve().parent.parent / "configs" / "experiments" / "SG-EXP-014-eerm-invariant.yaml"
    config = load_experiment_config(Path(args.project), exp_config_path, ())
    bundle = load_tensor_bundle(args.dataset)
    device = _select_device(args.device)
    lambdas = [0.0, 0.01, 0.1, 1.0, 10.0]
    seeds = config["experiment"].get("seeds", [2024, 2025, 2026])

    # 环境标签
    spec = WindowSpec(
        history_steps=int(config["project"]["history_steps"]),
        forecast_steps=int(config["project"]["forecast_steps"]),
    )
    datasets = {
        split: NodeWindowDataset(bundle, split, spec)
        for split in ("train", "validation", "test")
    }
    env_labels = _build_environment_labels(bundle, datasets)

    run_tag = time.strftime("%Y%m%d-%H%M%S")
    run_root = Path(args.output_root).expanduser().resolve() / run_tag
    run_root.mkdir(parents=True, exist_ok=True)
    dump_yaml(config, run_root / "config_resolved.yaml")
    write_json(environment_snapshot(), run_root / "environment.json")
    write_json({
        "experiment_id": "SG-EXP-014",
        "lambdas": lambdas,
        "seeds": seeds,
        "env_label_stats": {
            split: {"total": int(len(env_labels[split])),
                     "event": int(env_labels[split].sum())}
            for split in env_labels
        },
    }, run_root / "manifest.json")

    all_summaries = []
    for lam in lambdas:
        for seed in seeds:
            tag = f"lambda-{lam}_seed-{seed}"
            print(f"\n{'='*60}\nEERM λ={lam} seed={seed}\n{'='*60}", flush=True)
            seed_dir = run_root / tag
            summary = train_eerm_single_seed(
                config, bundle, seed, seed_dir, env_labels, lam, device,
            )
            all_summaries.append(summary)
            print(f"  ✓ global_mae={summary['global']['mae']:.5f} "
                  f"event_mae={summary['event_window']['mae']:.5f} "
                  f"stable_mae={summary['stable_window']['mae']:.5f}", flush=True)
            gc.collect()
            torch.cuda.empty_cache()

    # 汇总并找到关键拐点
    baseline = [s for s in all_summaries if s["lambda"] == 0.0]
    nonzero = [s for s in all_summaries if s["lambda"] > 0.0]
    write_json({
        "lambdas": lambdas, "seeds": seeds,
        "summaries": all_summaries,
        "baseline_avg_global_mae": np.mean([s["global"]["mae"] for s in baseline]) if baseline else None,
        "analysis": "若 λ 增大时 event_mae 上升而 stable_mae 不变，"
                    "说明事件特征是伪相关——强制不变性会丢弃事件特征。",
    }, run_root / "eerm_summary.json")
    print(f"\n全部完成：{run_root}", flush=True)


if __name__ == "__main__":
    main()
