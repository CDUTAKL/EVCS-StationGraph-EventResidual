"""阶段 B5：学习率调度对照实验（追加到 phase_b_results.json）。

读取 B1 最佳 TCN 配置，比较：
  - 无调度（当前基线）：固定 lr=1e-3，早停 patience=8
  - ReduceLROnPlateau：val MAE 连续 5 轮停滞 → lr *= 0.5，min_lr=1e-6
    早停 patience=12（给调度器降 lr 后继续搜索的空间）

两组使用完全相同的种子、数据顺序和初始权重（工厂模式），
差异仅来自 lr 调度——验证 lr 自适应是否带来额外收益。
"""

import json
import time
from pathlib import Path

import torch
from torch import nn

from evcs_station_graph.data import WindowSpec, load_tensor_bundle
from evcs_station_graph.evaluation import apply_frozen_event_rule, fit_frozen_event_rule
from evcs_station_graph.models.tcn import TemporalConvNet
from evcs_station_graph.reproducibility import set_global_seed

BUNDLE_PATH = "data/processed/SG-DATA-005-primary-tensor.npz"
RESULTS_FILE = "phase_b_results.json"
DEVICE = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
EPOCHS = 30
BATCH_SIZE = 256
LR = 1e-3
WEIGHT_DECAY = 1e-4

bundle = load_tensor_bundle(BUNDLE_PATH)
spec = WindowSpec(history_steps=96, forecast_steps=4)
NUM_NODES = len(bundle.node_ids)
INPUT_DIM = len(bundle.feature_names)
HORIZON = spec.forecast_steps
T = len(bundle.timestamps_ns)

rule = fit_frozen_event_rule(bundle, quantile=0.95, window_extension=2)
trigger_all = torch.from_numpy(rule.build_trigger_matrix(bundle, T)).to(DEVICE) if hasattr(rule, "build_trigger_matrix") else None
if trigger_all is None:
    import numpy as np
    trigger_all_np = np.zeros((T, NUM_NODES), dtype=bool)
    for split_name in ("train", "validation"):
        origins = bundle.split_origins[split_name]
        trigger_all_np[origins] = apply_frozen_event_rule(bundle, origins, rule)
    trigger_all = torch.from_numpy(trigger_all_np).to(DEVICE)

# GPU 常驻张量（与 phase_b_screen.py 相同）
X_GPU = torch.from_numpy(
    (bundle.features - bundle.feature_mean[None, None, :]) / bundle.feature_std[None, None, :]
).to(DEVICE)
Y_GPU = torch.from_numpy(
    (bundle.targets - bundle.target_mean[None, :]) / bundle.target_std[None, :]
).to(DEVICE)

SPLIT_IDX: dict = {}
for split_name in ("train", "validation"):
    origins_np = bundle.split_origins[split_name].astype("int64")
    origins = torch.from_numpy(origins_np).to(DEVICE)
    SPLIT_IDX[split_name] = {
        "origins": origins,
        "hist": origins[:, None] + torch.arange(-95, 1, device=DEVICE)[None, :],
        "fut": origins[:, None] + torch.arange(1, 1 + HORIZON, device=DEVICE)[None, :],
    }


def train_one(use_scheduler: bool, config_desc: dict, levels: int, hidden: int, seed: int = 2024) -> dict:
    patience = 12 if use_scheduler else 8
    set_global_seed(seed)
    model = TemporalConvNet(INPUT_DIM, HORIZON, hidden_dim=hidden, levels=levels, dropout=0.1).to(DEVICE)
    optimizer = torch.optim.AdamW(
        [p for p in model.parameters() if p.requires_grad],
        lr=LR, weight_decay=WEIGHT_DECAY,
    )
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="min", factor=0.5, patience=5, min_lr=1e-6,
    ) if use_scheduler else None
    criterion = nn.L1Loss()
    train_idx = SPLIT_IDX["train"]
    val_idx = SPLIT_IDX["validation"]
    n_train = len(train_idx["origins"])
    generator = torch.Generator().manual_seed(seed)

    best_val = float("inf")
    best_state = None
    stale = 0
    started = time.perf_counter()

    for epoch in range(1, EPOCHS + 1):
        model.train()
        perm = torch.randperm(n_train, generator=generator).to(DEVICE)
        for start in range(0, n_train, BATCH_SIZE):
            idx = perm[start: start + BATCH_SIZE]
            x = X_GPU[train_idx["hist"][idx]]
            y = Y_GPU[train_idx["fut"][idx]]
            trigger = trigger_all[train_idx["origins"][idx]]
            optimizer.zero_grad(set_to_none=True)
            loss = criterion(model(x, rule_trigger=trigger).prediction, y)
            if not torch.isfinite(loss):
                return {"config": config_desc, "error": "NaN loss"}
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            optimizer.step()

        # 验证
        model.eval()
        val_sum = val_count = 0.0
        with torch.no_grad():
            n_val = len(val_idx["origins"])
            for start in range(0, n_val, BATCH_SIZE):
                idx = torch.arange(start, min(start + BATCH_SIZE, n_val), device=DEVICE)
                x = X_GPU[val_idx["hist"][idx]]
                y = Y_GPU[val_idx["fut"][idx]]
                pred = model(x, rule_trigger=trigger_all[val_idx["origins"][idx]]).prediction
                val_sum += float((pred - y).abs().sum())
                val_count += pred.numel()
        val_mae = val_sum / max(val_count, 1)

        if scheduler is not None:
            scheduler.step(val_mae)
            current_lr = optimizer.param_groups[0]["lr"]
        else:
            current_lr = LR

        print(f"    epoch {epoch:2d}: val_mae={val_mae:.5f} lr={current_lr:.1e}",
              flush=True)

        if val_mae < best_val - 1e-8:
            best_val = val_mae
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            stale = 0
        else:
            stale += 1
            if stale >= patience:
                break

    return {
        "config": config_desc,
        "best_val_mae": best_val,
        "epochs_run": epoch,
        "wall_seconds": round(time.perf_counter() - started, 1),
    }


def main() -> None:
    results_path = Path(RESULTS_FILE)
    if not results_path.exists():
        print(f"错误：{RESULTS_FILE} 不存在，请等待阶段 B 完成后运行")
        return
    prev = json.loads(results_path.read_text(encoding="utf-8"))
    b1_best = prev.get("b1_best", {})
    best_levels = b1_best.get("levels", 3)
    best_hidden = b1_best.get("hidden_dim", 32)
    print(f"B1 最佳：levels={best_levels}, hidden={best_hidden}, val_mae={b1_best.get('val_mae')}")
    print("=" * 60)

    results = []
    for use_sched, label, patience in (
        (False, "B5-baseline-no-scheduler", 8),
        (True, "B5-ReduceLROnPlateau", 12),
    ):
        desc = {
            "stage": "B5", "model": "TCN", "levels": best_levels,
            "hidden_dim": best_hidden, "lr_scheduler": label,
            "patience": patience,
        }
        rec = train_one(use_sched, desc, best_levels, best_hidden)
        results.append(rec)
        print(f"  ✓ {label}: best_val_mae={rec['best_val_mae']:.5f} "
              f"(epochs={rec['epochs_run']}, {rec['wall_seconds']}s)", flush=True)

    prev["b5_lr_scheduler"] = results
    results_path.write_text(json.dumps(prev, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"B5 完成，结果已追加到 {RESULTS_FILE}")


if __name__ == "__main__":
    main()
