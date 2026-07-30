"""统一训练、评价、模型保存与预测文件导出。

本模块是实现不可变研究边界（代码样式协议 §2）的关键执行点：
- 所有模型的训练循环完全相同，差异仅来自 config 字典
- 事件规则在验证集拟合后冻结，测试集仅执行已冻结规则
- 预测文件按 (split, origin_index, horizon, node_id) 四元组唯一标识
- 每种子的工件（模型、指标、预测文件）独立保存，确保可追溯

训练流程概览（``train_single_seed``）：
  [构建数据集] → [创建模型] → [拟合冻结事件规则] → [训练循环]
  → [测试集预测] → [分层评价+四格诊断] → [写出工件]
"""

from __future__ import annotations

import csv
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
from torch import nn
from torch.utils.data import DataLoader

from evcs_station_graph.config import dump_yaml
from evcs_station_graph.data import (
    NodeWindowDataset,
    TensorBundle,
    WindowSpec,
    build_prediction_key_frame,
)
from evcs_station_graph.evaluation import (
    apply_frozen_event_rule,
    fit_frozen_event_rule,
    four_cell_diagnostics,
    stratified_metrics,
    visible_event_scores,
)
from evcs_station_graph.graphs import RelationSet, build_relation_set
from evcs_station_graph.reproducibility import (
    environment_snapshot,
    set_global_seed,
    sha256_file,
    write_json,
)
from evcs_station_graph.training.factory import build_model
from evcs_station_graph.training.losses import WeightedL1Loss


def train_experiment(
    config: dict[str, Any],
    bundle: TensorBundle,
    output_root: str | Path,
    *,
    base_checkpoint: str | Path | None = None,
) -> Path:
    """按配置运行全部随机种子并汇总结果。"""
    experiment_id = config["experiment"]["experiment_id"]
    run_tag = config["experiment"].get("run_tag") or time.strftime("%Y%m%d-%H%M%S")
    run_root = Path(output_root).expanduser().resolve() / experiment_id / str(run_tag)
    run_root.mkdir(parents=True, exist_ok=True)
    dump_yaml(config, run_root / "config_resolved.yaml")
    write_json(environment_snapshot(), run_root / "environment.json")

    relation_set = _build_relations(config, bundle)
    np.savez_compressed(
        run_root / "relation_matrices.npz",
        **relation_set.as_dict(),
    )
    seed_summaries: list[dict[str, Any]] = []
    for seed in config["experiment"]["seeds"]:
        seed_dir = run_root / f"seed-{seed}"
        seed_checkpoint = _resolve_seed_checkpoint(base_checkpoint, int(seed))
        summary = train_single_seed(
            config,
            bundle,
            relation_set,
            seed=int(seed),
            output_dir=seed_dir,
            base_checkpoint=seed_checkpoint,
        )
        seed_summaries.append(summary)

    aggregate = _aggregate_seed_metrics(seed_summaries)
    write_json(aggregate, run_root / "metrics_summary.json")
    manifest = {
        "experiment_id": experiment_id,
        "run_tag": run_tag,
        "seeds": config["experiment"]["seeds"],
        "seed_directories": [f"seed-{seed}" for seed in config["experiment"]["seeds"]],
        "dataset_artifact": config["paths"]["dataset_artifact"],
        "dataset_sha256": sha256_file(config["paths"]["dataset_artifact"]),
        "outputs": [
            "config_resolved.yaml",
            "environment.json",
            "relation_matrices.npz",
            "metrics_summary.json",
        ],
        "result_authority": config["experiment"].get("result_authority", "formal_candidate"),
    }
    write_json(manifest, run_root / "manifest.json")
    return run_root


def train_single_seed(
    config: dict[str, Any],
    bundle: TensorBundle,
    relation_set: RelationSet,
    *,
    seed: int,
    output_dir: Path,
    base_checkpoint: str | Path | None = None,
) -> dict[str, Any]:
    """训练一个随机种子并输出完整证据文件。"""
    # ========== 阶段 1：数据集与数据加载器构建 ==========
    set_global_seed(seed)
    output_dir.mkdir(parents=True, exist_ok=True)
    runtime = config.get("runtime", {})
    training = config["experiment"].get("training", {})
    spec = WindowSpec(
        history_steps=int(config["project"]["history_steps"]),
        forecast_steps=int(config["project"]["forecast_steps"]),
    )
    max_samples = runtime.get("max_samples_per_split")
    datasets = {
        split: NodeWindowDataset(
            bundle,
            split,
            spec,
            max_samples=int(max_samples) if max_samples is not None else None,
        )
        for split in ("train", "validation", "test")
    }
    batch_size = int(training.get("batch_size", 256))
    # 训练集 shuffle=True 保证每轮遍历顺序不同；验证/测试集不 shuffle
    # 以保持结果可复现（相同的 seed → 相同的验证/测试批次顺序）
    loaders = {
        "train": _make_loader(datasets["train"], batch_size, True, seed),
        "validation": _make_loader(datasets["validation"], batch_size, False, seed),
        "test": _make_loader(datasets["test"], batch_size, False, seed),
    }
    # ========== 阶段 2：模型创建与冻结事件规则拟合 ==========
    # 默认使用全部三类关系；SG-EXP-006 的关系消融通过 config 指定子集
    graph_cfg = config["experiment"].get("graph", {})
    relation_names = graph_cfg.get("enabled_relations", ["load", "event", "pattern"])
    unknown = set(relation_names) - set(relation_set.as_dict())
    if unknown:
        raise ValueError(f"未知候选关系：{sorted(unknown)}")
    adjacencies = [relation_set.as_dict()[name] for name in relation_names]
    model = build_model(
        config,
        input_dim=len(bundle.feature_names),
        horizon=spec.forecast_steps,
        num_nodes=len(bundle.node_ids),
        adjacencies=adjacencies,
        base_checkpoint=base_checkpoint,
        feature_names=bundle.feature_names,
    )
    device = _select_device(str(runtime.get("device", "auto")))
    model.to(device)
    # 只优化 requires_grad=True 的参数，冻结参数（如基模型权重）不受影响
    parameters = [parameter for parameter in model.parameters() if parameter.requires_grad]
    if not parameters:
        raise RuntimeError("当前配置没有可训练参数，请检查模型冻结设置")
    # AdamW：带解耦权重衰减的 Adam，适合小规模时序预测任务
    # L1Loss（MAE）：比 MSE 对异常负荷峰值更鲁棒，适合充电负荷的尖峰特性
    optimizer = torch.optim.AdamW(
        parameters,
        lr=float(training.get("learning_rate", 1e-3)),
        weight_decay=float(training.get("weight_decay", 1e-4)),
    )
    # 损失函数：若配置了 loss 段则使用加权损失，否则回退到标准 L1
    loss_cfg = training.get("loss", {})
    use_weighted_loss = bool(loss_cfg)
    if use_weighted_loss:
        criterion: nn.Module = WeightedL1Loss(
            lambda_=float(loss_cfg.get("lambda", 3.0)),
            mode=str(loss_cfg.get("mode", "binary")),
            normalize_intensity=bool(loss_cfg.get("normalize_intensity", True)),
        )
    else:
        criterion = nn.L1Loss()

    # ---- 冻结事件规则拟合（仅使用验证集） ----
    # 阈值和窗口扩展参数在此确定后，后续训练和测试阶段绝不重新计算
    rule = fit_frozen_event_rule(
        bundle,
        quantile=float(config["dataset"]["event"].get("trigger_quantile", 0.95)),
        window_extension=int(config["dataset"]["event"].get("window_extension", 2)),
    )
    # 构建全时间轴的触发矩阵 [T, N]，训练时按 origin_index 索引
    trigger_by_origin = np.zeros(
        (len(bundle.timestamps_ns), len(bundle.node_ids)),
        dtype=np.bool_,
    )
    for ds in datasets.values():
        trigger_by_origin[ds.origins] = apply_frozen_event_rule(
            bundle,
            ds.origins,
            rule,
        )
    if not bool(config["experiment"].get("gate", {}).get("enabled", True)):
        # 无门控消融：保留修正模型结构，但所有样本均进入修正路径
        # 用于量化"门控本身是否有价值"——对比门控+修正 vs 全量修正
        trigger_by_origin[:] = True

    # 事件强度分数 [T, N]：仅在使用加权损失时计算，避免非必要的 I/O
    scores_by_origin: np.ndarray | None = None
    if use_weighted_loss:
        score_stats_np = {
            key: np.asarray(value, dtype=np.float32)
            for key, value in rule.score_stats.items()
        }
        scores_by_origin = np.zeros(
            (len(bundle.timestamps_ns), len(bundle.node_ids)),
            dtype=np.float32,
        )
        for ds in datasets.values():
            scores_by_origin[ds.origins] = visible_event_scores(
                bundle, ds.origins, score_stats=score_stats_np,
            )

    # ========== 阶段 3：训练循环（早停） ==========
    # 使用验证集 MAE 做早停：在 patience 轮内未改善则终止
    # 早停阈值 1e-8 防止浮点误差导致的伪改善（如 0.100000001 < 0.1）
    best_state: dict[str, torch.Tensor] | None = None
    best_validation = float("inf")
    patience = int(training.get("patience", 8))
    epochs = int(training.get("epochs", 50))
    stale_epochs = 0
    log_rows: list[dict[str, float | int]] = []
    started = time.perf_counter()
    for epoch in range(1, epochs + 1):
        train_loss = _train_epoch(
            model,
            loaders["train"],
            optimizer,
            criterion,
            device,
            trigger_by_origin,
            scores_by_origin,
        )
        # 早停始终基于标准 L1（不加权），因为泛化能力的评价应在原始分布上进行
        validation_loss = _validation_loss(
            model,
            loaders["validation"],
            nn.L1Loss(),
            device,
            trigger_by_origin,
            None,  # 早停不使用加权损失
        )
        log_rows.append(
            {"epoch": epoch, "train_mae_scaled": train_loss, "validation_mae_scaled": validation_loss}
        )
        if validation_loss < best_validation - 1e-8:
            best_validation = validation_loss
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
    elapsed = time.perf_counter() - started

    # ========== 阶段 4：测试集一次性评价 ==========
    # 注意：此阶段不调整模型参数、不更新阈值、不修改图关系
    # 测试集仅用于计算最终指标，绝不参与任何拟合或选择
    predictions = _predict(
        model,
        loaders["test"],
        device,
        trigger_by_origin,
        bundle,
    )
    metrics = stratified_metrics(
        predictions["truth"],
        predictions["prediction"],
        target_event=predictions["target_event"],
        node_ids=bundle.node_ids.tolist(),
    )
    four_cells = four_cell_diagnostics(
        predictions["truth"],
        predictions["prediction"],
        target_event=predictions["target_event"],
        rule_trigger=predictions["rule_trigger"],
    )
    metrics["four_cell"] = four_cells
    metrics["training"] = {
        "seed": seed,
        "epochs_completed": len(log_rows),
        "best_validation_mae_scaled": best_validation,
        "elapsed_seconds": elapsed,
        "device": str(device),
        "trainable_parameters": sum(parameter.numel() for parameter in parameters),
    }
    metrics["frozen_event_rule"] = {
        "thresholds": rule.thresholds.tolist(),
        "quantile": rule.quantile,
        "score_definition": rule.score_definition,
        "window_extension": rule.window_extension,
        "trigger_point_fraction": (
            rule.trigger_point_fraction.tolist()
            if hasattr(rule.trigger_point_fraction, "tolist")
            else list(rule.trigger_point_fraction)
        ),
        "event_window_fraction": (
            rule.event_window_fraction.tolist()
            if hasattr(rule.event_window_fraction, "tolist")
            else list(rule.event_window_fraction)
        ),
        "score_stats": rule.score_stats,
    }

    # ========== 阶段 5：工件写出 ==========
    # 每种子的工件独立保存（模型、指标、预测文件、训练日志、清单）
    # 确保任意单种子结果可独立审核和复现
    torch.save(
        {
            "model_state": best_state,
            "seed": seed,
            "best_validation_mae_scaled": best_validation,
        },
        output_dir / "model.pt",
    )
    _write_training_log(log_rows, output_dir / "training_log.csv")
    write_json(metrics, output_dir / "metrics.json")
    prediction_manifest = _write_predictions(
        bundle,
        datasets["test"].origins,
        predictions,
        output_dir / "predictions.csv.gz",
    )
    write_json(
        {
            "seed": seed,
            "model_file": "model.pt",
            "metrics_file": "metrics.json",
            "prediction_file": "predictions.csv.gz",
            "prediction_rows": int(predictions["truth"].size),
            **prediction_manifest,
            "test_origin_count": int(len(datasets["test"].origins)),
            "base_checkpoint": str(base_checkpoint) if base_checkpoint is not None else None,
        },
        output_dir / "manifest.json",
    )
    return {
        "seed": seed,
        "global": metrics["global"],
        "nonzero_load": metrics["nonzero_load"],
        "event_window": metrics["event_window"],
        "stable_window": metrics["stable_window"],
        "four_cell_reconstruction_pass": four_cells["reconstruction_pass"],
    }


def _build_relations(config: dict[str, Any], bundle: TensorBundle) -> RelationSet:
    train_end = int(bundle.split_origins["train"][-1])
    graph = config["experiment"].get("graph", {})
    return build_relation_set(
        bundle.features[: train_end + 1],
        bundle.targets[: train_end + 1],
        bundle.feature_names,
        top_k=int(graph.get("top_k", 5)),
    )


def _make_loader(
    dataset: NodeWindowDataset,
    batch_size: int,
    shuffle: bool,
    seed: int,
) -> DataLoader:
    generator = torch.Generator()
    generator.manual_seed(seed)
    return DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        num_workers=0,
        pin_memory=False,
        generator=generator,
    )


def _train_epoch(
    model: nn.Module,
    loader: DataLoader,
    optimizer: torch.optim.Optimizer,
    criterion: nn.Module,
    device: torch.device,
    trigger_by_origin: np.ndarray,
    scores_by_origin: np.ndarray | None = None,
) -> float:
    """执行一个训练轮次，返回该轮的平均训练损失（缩放后尺度）。

    梯度裁剪 max_norm=5.0 防止事件窗口内的极端残差导致梯度爆炸。
    触发矩阵 ``trigger_by_origin`` 在训练中控制哪些样本进入修正路径。

    当 ``criterion`` 为 ``WeightedL1Loss`` 时，根据其 mode 选择事件信号：
    - binary：使用 trigger 的二值掩码
    - intensity：使用 ``scores_by_origin`` 的连续事件分数
    """
    model.train()
    total_loss = 0.0
    total_count = 0
    for batch in loader:
        x = batch["x"].to(device)
        y = batch["y"].to(device)
        batch_size = len(x)
        origin_index = batch["origin_index"].numpy()
        trigger = torch.from_numpy(trigger_by_origin[origin_index]).to(device)
        optimizer.zero_grad(set_to_none=True)
        output = model(x, rule_trigger=trigger)

        if isinstance(criterion, WeightedL1Loss):
            # 根据权重模式选择事件信号
            if criterion.mode == "binary":
                event_signal = trigger.to(torch.float32)
            else:
                if scores_by_origin is None:
                    raise RuntimeError(
                        "intensity 模式下 scores_by_origin 不能为 None"
                    )
                event_signal = torch.from_numpy(
                    scores_by_origin[origin_index]
                ).to(device)
            loss = criterion(output.prediction, y, event_signal=event_signal)
        else:
            loss = criterion(output.prediction, y)

        if not torch.isfinite(loss):
            raise FloatingPointError("训练损失出现非有限值")
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
        optimizer.step()
        total_loss += float(loss.detach()) * batch_size
        total_count += batch_size
    if total_count == 0:
        raise RuntimeError("训练集没有可用样本")
    return total_loss / total_count


@torch.no_grad()
def _validation_loss(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    device: torch.device,
    trigger_by_origin: np.ndarray,
    scores_by_origin: np.ndarray | None = None,  # pylint: disable=unused-argument
) -> float:
    """计算验证集平均损失（不更新参数），用于早停判断。

    ``@torch.no_grad()`` 确保验证期间不计算梯度，节省显存。
    早停始终使用标准 L1Loss——泛化能力应在原始分布上评价。
    """
    model.eval()
    total_loss = 0.0
    total_count = 0
    for batch in loader:
        x = batch["x"].to(device)
        y = batch["y"].to(device)
        batch_size = len(x)
        origin_index = batch["origin_index"].numpy()
        trigger = torch.from_numpy(trigger_by_origin[origin_index]).to(device)
        loss = criterion(model(x, rule_trigger=trigger).prediction, y)
        if not torch.isfinite(loss):
            raise FloatingPointError("验证损失出现非有限值")
        total_loss += float(loss) * batch_size
        total_count += batch_size
    if total_count == 0:
        raise RuntimeError("验证集没有可用样本")
    return total_loss / total_count


@torch.no_grad()
def _predict(
    model: nn.Module,
    loader: DataLoader,
    device: torch.device,
    trigger_by_origin: np.ndarray,
    bundle: TensorBundle,
) -> dict[str, np.ndarray]:
    """在测试集上生成预测，返回反标准化后的真实值和预测值。

    反标准化使用训练集拟合的 per-node 参数：
      y_raw = y_scaled * target_std + target_mean
    这使得指标具有物理量纲（kWh/15min），便于理解和比较。

    返回的 dict 包含：
    - truth/prediction：形状 [S, H, N] 的反标准化负荷
    - target_event：真实事件标签（用于评价）
    - rule_trigger：规则触发矩阵（用于评价）
    """
    model.eval()
    truth_parts: list[np.ndarray] = []
    prediction_parts: list[np.ndarray] = []
    event_parts: list[np.ndarray] = []
    trigger_parts: list[np.ndarray] = []
    for batch in loader:
        x = batch["x"].to(device)
        batch_size = len(x)
        origin_index = batch["origin_index"].numpy()
        trigger_np = trigger_by_origin[origin_index]
        trigger = torch.from_numpy(trigger_np).to(device)
        output = model(x, rule_trigger=trigger)
        prediction_parts.append(output.prediction.cpu().numpy())
        truth_parts.append(batch["y"].numpy())
        event_parts.append(batch["target_event"].numpy())
        trigger_parts.append(trigger_np)
    if not truth_parts:
        raise RuntimeError("测试集没有可用样本，无法生成正式预测文件")
    truth_scaled = np.concatenate(truth_parts)
    prediction_scaled = np.concatenate(prediction_parts)
    truth = truth_scaled * bundle.target_std[None, None, :] + bundle.target_mean[None, None, :]
    prediction = (
        prediction_scaled * bundle.target_std[None, None, :]
        + bundle.target_mean[None, None, :]
    )
    return {
        "truth": truth.astype(np.float32),
        "prediction": prediction.astype(np.float32),
        "target_event": np.concatenate(event_parts).astype(bool),
        "rule_trigger": np.concatenate(trigger_parts).astype(bool),
    }


def _write_predictions(
    bundle: TensorBundle,
    origins: np.ndarray,
    arrays: dict[str, np.ndarray],
    path: Path,
) -> dict[str, Any]:
    """将预测结果与预测键合并写入 gzip CSV，并验证键唯一性和数值有效性。

    输出的 CSV 包含以下列：
    - 标识列：split, origin_index, horizon, node_id
    - 数值列：y_true（真实负荷）, y_pred（预测负荷）
    - 诊断列：target_event（真实事件标签）, rule_trigger（规则触发）

    rule_trigger 是 [S, N] 的，通过 broadcast_to 扩展为 [S, H, N]
    以匹配 target_event 的形状，确保两者可直接比较（四格诊断需要）。
    """
    keys = build_prediction_key_frame(
        bundle,
        "test",
        arrays["truth"].shape[1],
        origins=origins,
    )
    keys["y_true"] = arrays["truth"].reshape(-1)
    keys["y_pred"] = arrays["prediction"].reshape(-1)
    keys["target_event"] = arrays["target_event"].reshape(-1)
    repeated_trigger = np.broadcast_to(
        arrays["rule_trigger"][:, None, :],
        arrays["truth"].shape,
    )
    keys["rule_trigger"] = repeated_trigger.reshape(-1)
    key_columns = ["split", "origin_index", "horizon", "node_id"]
    duplicated = keys.duplicated(key_columns, keep=False)
    if duplicated.any():
        examples = keys.loc[duplicated, key_columns].head(5).to_dict("records")
        raise ValueError(f"预测键不唯一，示例：{examples}")
    if not np.isfinite(keys[["y_true", "y_pred"]].to_numpy()).all():
        raise FloatingPointError("预测文件包含非有限真实值或预测值")
    keys.to_csv(path, index=False, compression="gzip")
    return {
        "prediction_key_columns": key_columns,
        "prediction_key_unique": True,
        "prediction_rows": int(len(keys)),
    }


def _write_training_log(rows: list[dict[str, Any]], path: Path) -> None:
    """将逐轮训练指标写入 CSV，拒绝写出空日志。

    空日志代表训练循环未执行任何 epoch，通常是配置错误（如 epochs=0）
    或数据集为空——此时应立即终止而非静默产生不完整工件。
    """
    if not rows:
        raise RuntimeError("训练日志为空，拒绝写出不完整实验工件")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _select_device(requested: str) -> torch.device:
    """解析设备选择：'auto' 按 CUDA > MPS > CPU 优先级自动选择。

    MPS（Apple Silicon GPU）支持受限于 PyTorch 版本——部分算子可能回退 CPU，
    但不影响结果正确性，仅影响训练速度。
    """
    if requested != "auto":
        return torch.device(requested)
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def _resolve_seed_checkpoint(
    base_checkpoint: str | Path | None,
    seed: int,
) -> Path | None:
    """为每个随机种子解析对应的默认模型检查点。

    传入文件时仅适合单种子调试；正式三种子运行应传入 SG-EXP-002 的运行目录，
    目录内必须存在 ``seed-<seed>/model.pt``。
    """
    if base_checkpoint is None:
        return None
    candidate = Path(base_checkpoint).expanduser().resolve()
    if candidate.is_file():
        return candidate
    seed_file = candidate / f"seed-{seed}" / "model.pt"
    if seed_file.is_file():
        return seed_file
    raise FileNotFoundError(f"未找到随机种子 {seed} 的默认模型检查点：{seed_file}")


def _aggregate_seed_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        raise RuntimeError("随机种子结果为空，无法汇总实验")
    output: dict[str, Any] = {"seeds": [row["seed"] for row in rows], "scopes": {}}
    for scope in ("global", "nonzero_load", "event_window", "stable_window"):
        output["scopes"][scope] = {}
        for metric in ("mae", "rmse", "wape"):
            values = np.asarray([row[scope][metric] for row in rows], dtype=np.float64)
            output["scopes"][scope][metric] = {
                "mean": float(np.nanmean(values)),
                "std": float(np.nanstd(values, ddof=1)) if len(values) > 1 else 0.0,
            }
    output["four_cell_reconstruction_all_pass"] = all(
        row["four_cell_reconstruction_pass"] for row in rows
    )
    return output
