"""SG-EXP-013：GCN→TCN 知识蒸馏验证实验。

验证图结构知识的不可替代性——以训练完成的 StaticGraph 为教师，
将预测信号蒸馏至同容量的 TCN 学生。若 TCN+KD 仍远不如 GCN，
则证明图结构知识无法被纯时序模型吸收，即图结构**不可替代**。

实验设计：
  - 教师：SG-EXP-003 StaticGraph（3 种子，已训练）
  - 学生：TCN（与 SG-EXP-002 同架构）
  - 损失：L = L1(pred, truth) + α * MSE(pred, teacher_pred)
  - α sweep: {0.1, 0.5, 1.0, 2.0}
  - 3 种子 × 4 α 值 = 12 次训练

用法：
  .venv/bin/python scripts/run_knowledge_distillation.py \
    --project configs/project.yaml \
    --teacher-root outputs/experiments/SG-EXP-003/<run_tag> \
    --output-root outputs/experiments/SG-EXP-013
"""

from __future__ import annotations

import argparse
import csv
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
)
from evcs_station_graph.graphs import build_relation_set
from evcs_station_graph.models.graph import StaticGraphForecast
from evcs_station_graph.models.tcn import TemporalConvNet
from evcs_station_graph.reproducibility import (
    environment_snapshot,
    set_global_seed,
    sha256_file,
    write_json,
)
from evcs_station_graph.training.engine import (
    _make_loader,
    _predict,
    _resolve_seed_checkpoint,
    _select_device,
    _write_predictions,
    _write_training_log,
)


def _load_teacher(teacher_dir: Path, device: torch.device, config: dict, adjacencies: list) -> nn.Module:
    """从 SG-EXP-003 种子目录加载训练完成的 StaticGraph 教师模型。"""
    checkpoint_path = teacher_dir / "model.pt"
    if not checkpoint_path.is_file():
        raise FileNotFoundError(f"教师检查点不存在：{checkpoint_path}")
    payload = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    state = payload.get("model_state", payload)
    params = config["experiment"].get("model_params", {})
    # 从 checkpoint 中提取 input_dim（Conv1d 权重形状为 [out, in, kernel]）
    conv_key = "tcn.network.0.conv.weight"
    if conv_key in state:
        inferred_input_dim = int(state[conv_key].shape[1])  # in_channels
    else:
        inferred_input_dim = 7  # 项目默认特征数
    teacher = StaticGraphForecast(
        input_dim=inferred_input_dim,
        horizon=int(config["project"]["forecast_steps"]),
        num_nodes=len(adjacencies[0]),
        adjacencies=adjacencies,
        hidden_dim=int(params.get("hidden_dim", 32)),
        levels=int(params.get("levels", 6)),
        dropout=float(params.get("dropout", 0.1)),
    )
    teacher.load_state_dict(state, strict=True)
    teacher.to(device)
    teacher.eval()
    for param in teacher.parameters():
        param.requires_grad = False
    return teacher


def train_kd_single_seed(
    config: dict,
    bundle: TensorBundle,
    seed: int,
    output_dir: Path,
    teacher: nn.Module,
    alpha: float,
    device: torch.device,
) -> dict:
    """训练单个种子的 TCN+KD 学生模型。"""
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

    # 学生模型：TCN（与 SG-EXP-002 同架构，levels=6）
    params_cfg = config["experiment"].get("model_params", {})
    student = TemporalConvNet(
        input_dim=len(bundle.feature_names),
        horizon=spec.forecast_steps,
        hidden_dim=int(params_cfg.get("hidden_dim", 32)),
        levels=int(params_cfg.get("levels", 6)),
        dropout=float(params_cfg.get("dropout", 0.1)),
    ).to(device)

    optimizer = torch.optim.AdamW(
        student.parameters(),
        lr=float(training.get("learning_rate", 1e-3)),
        weight_decay=float(training.get("weight_decay", 1e-4)),
    )
    criterion_l1 = nn.L1Loss()
    criterion_kd = nn.MSELoss()

    # 事件规则（用于 trigger 矩阵，非训练必需但保持一致性）
    rule = fit_frozen_event_rule(bundle, quantile=0.95, window_extension=2)
    trigger_by_origin = np.zeros((len(bundle.timestamps_ns), len(bundle.node_ids)), dtype=bool)
    for ds in datasets.values():
        trigger_by_origin[ds.origins] = apply_frozen_event_rule(bundle, ds.origins, rule)

    best_state = None
    best_validation = float("inf")
    patience = int(training.get("patience", 8))
    epochs = int(training.get("epochs", 60))
    stale = 0
    log_rows: list[dict] = []
    started = time.perf_counter()

    for epoch in range(1, epochs + 1):
        # ---- 训练 ----
        student.train()
        total_loss = 0.0
        total_count = 0
        for batch in loaders["train"]:
            x = batch["x"].to(device)
            y = batch["y"].to(device)
            n = len(x)

            with torch.no_grad():
                teacher_out = teacher(x, rule_trigger=torch.zeros(n, 0, device=device))
                teacher_pred = teacher_out.prediction

            optimizer.zero_grad(set_to_none=True)
            student_pred = student(x).prediction if hasattr(student(x), 'prediction') else student(x)
            # 重新前向（避免重复计算）
            optimizer.zero_grad(set_to_none=True)
            student_out = student(x)
            if hasattr(student_out, 'prediction'):
                student_pred = student_out.prediction
            else:
                student_pred = student_out

            loss_l1 = criterion_l1(student_pred, y)
            loss_kd = criterion_kd(student_pred, teacher_pred)
            loss = loss_l1 + alpha * loss_kd

            if not torch.isfinite(loss):
                raise FloatingPointError(f"KD 训练损失非有限值 (epoch={epoch})")
            loss.backward()
            torch.nn.utils.clip_grad_norm_(student.parameters(), max_norm=5.0)
            optimizer.step()
            total_loss += float(loss.detach()) * n
            total_count += n

        train_loss = total_loss / max(total_count, 1)

        # ---- 验证 ----
        student.eval()
        val_total = 0.0
        val_count = 0
        with torch.no_grad():
            for batch in loaders["validation"]:
                x = batch["x"].to(device)
                y = batch["y"].to(device)
                n = len(x)
                out = student(x)
                pred = out.prediction if hasattr(out, 'prediction') else out
                val_total += float(nn.L1Loss()(pred, y)) * n
                val_count += n
        val_loss = val_total / max(val_count, 1)

        log_rows.append({
            "epoch": epoch, "train_loss": train_loss,
            "validation_mae": val_loss, "alpha": alpha,
        })

        if val_loss < best_validation - 1e-8:
            best_validation = val_loss
            best_state = {k: v.detach().cpu().clone() for k, v in student.state_dict().items()}
            stale = 0
        else:
            stale += 1
            if stale >= patience:
                break

    if best_state is None:
        raise RuntimeError("KD 训练未生成有效检查点")
    student.load_state_dict(best_state)
    elapsed = time.perf_counter() - started

    # ---- 测试 ----
    predictions = _predict(student, loaders["test"], device, trigger_by_origin, bundle)
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
        "seed": seed, "alpha": alpha,
        "epochs_completed": len(log_rows),
        "best_validation_mae": best_validation,
        "elapsed_seconds": elapsed,
        "device": str(device),
        "trainable_parameters": sum(p.numel() for p in student.parameters() if p.requires_grad),
    }

    torch.save({
        "model_state": best_state, "seed": seed, "alpha": alpha,
        "best_validation_mae": best_validation,
    }, output_dir / "model.pt")
    _write_training_log(log_rows, output_dir / "training_log.csv")
    write_json(metrics, output_dir / "metrics.json")
    _write_predictions(bundle, datasets["test"].origins, predictions, output_dir / "predictions.csv.gz")

    return {"seed": seed, "alpha": alpha, "global": metrics["global"],
            "event_window": metrics["event_window"], "stable_window": metrics["stable_window"]}


def main() -> None:
    parser = argparse.ArgumentParser(description="SG-EXP-013 GCN→TCN 知识蒸馏")
    parser.add_argument("--project", required=True, help="项目配置文件路径")
    parser.add_argument("--teacher-root", required=True, help="SG-EXP-003 StaticGraph 运行根目录")
    parser.add_argument("--output-root", default="outputs/experiments/SG-EXP-013")
    parser.add_argument("--device", default="auto")
    parser.add_argument("--dataset", default="data/processed/SG-DATA-005-primary-tensor.npz")
    args = parser.parse_args()

    # 加载项目配置 + SG-EXP-013 实验配置
    exp_config_path = Path(__file__).resolve().parent.parent / "configs" / "experiments" / "SG-EXP-013-kd-distillation.yaml"
    config = load_experiment_config(Path(args.project), exp_config_path, ())
    bundle = load_tensor_bundle(args.dataset)
    device = _select_device(args.device)
    alphas = [0.1, 0.5, 1.0, 2.0]
    seeds = config["experiment"].get("seeds", [2024, 2025, 2026])

    # 构建关系图
    train_end = int(bundle.split_origins["train"][-1])
    graph_cfg = config["experiment"].get("graph", {})
    adjacencies = build_relation_set(
        bundle.features[: train_end + 1], bundle.targets[: train_end + 1],
        bundle.feature_names, top_k=int(graph_cfg.get("top_k", 3)),
    ).as_list()

    run_tag = time.strftime("%Y%m%d-%H%M%S")
    run_root = Path(args.output_root).expanduser().resolve() / run_tag
    run_root.mkdir(parents=True, exist_ok=True)
    dump_yaml(config, run_root / "config_resolved.yaml")
    write_json(environment_snapshot(), run_root / "environment.json")
    write_json({
        "experiment_id": "SG-EXP-013",
        "teacher_root": str(args.teacher_root),
        "alphas": alphas,
        "seeds": seeds,
    }, run_root / "manifest.json")

    teacher_root = Path(args.teacher_root).expanduser().resolve()
    all_summaries = []

    for alpha in alphas:
        for seed in seeds:
            tag = f"alpha-{alpha}_seed-{seed}"
            print(f"\n{'='*60}\nKD α={alpha} seed={seed}\n{'='*60}", flush=True)

            # 加载对应种子的教师
            teacher_dir = _resolve_seed_checkpoint(teacher_root, seed)
            if teacher_dir is None:
                print(f"  ⚠ 跳过：未找到 seed={seed} 的教师检查点", flush=True)
                continue
            # _resolve_seed_checkpoint 对目录返回 seed-<N>/model.pt
            teacher = _load_teacher(
                teacher_dir.parent if teacher_dir.name == "model.pt" else teacher_dir,
                device, config, adjacencies,
            )

            seed_dir = run_root / tag
            summary = train_kd_single_seed(
                config, bundle, seed, seed_dir, teacher, alpha, device,
            )
            all_summaries.append(summary)
            print(f"  ✓ global_mae={summary['global']['mae']:.5f} "
                  f"event_mae={summary['event_window']['mae']:.5f}", flush=True)
            gc.collect()
            torch.cuda.empty_cache()

    # 汇总
    write_json({
        "alphas": alphas, "seeds": seeds,
        "summaries": all_summaries,
        "best_config": min(all_summaries, key=lambda s: s["global"]["mae"])
            if all_summaries else None,
    }, run_root / "kd_summary.json")
    print(f"\n全部完成：{run_root}", flush=True)


if __name__ == "__main__":
    main()
