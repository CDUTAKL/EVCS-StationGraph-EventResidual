"""阶段 B：超参数预筛选（仅训练集+验证集，单种子 2024，不触碰测试集）。

四阶段序贯筛选，每阶段的选择基于验证集 MAE 并可解释：
  B1  TCN 时间编码：levels ∈ {3,5,6} × hidden ∈ {32,64}
      （levels 决定感受野：15/63/127 步，用户硬性比较要求）
  B2  StaticGraph：top_k ∈ {3,5,7}（关系构建强度，B1 最佳时间编码）
  B3  AdaptiveGraph：embedding_dim ∈ {8,12,16} → fixed_weight ∈ {0.2,0.3,0.5}
  B4  EventResidual：residual_hidden ∈ {16,32,64} → residual_bound ∈ {0.3,0.5,1.0}
      （base = B1 最佳 TCN，内存复用 best_state，冻结）

纪律：
- 事件触发矩阵只对 train/validation origins 计算，测试集绝不参与
- relation_dropout 固定 0.0（属于 SG-EXP-006 敏感性实验，非预筛选维度）
- 每配置：AdamW + L1Loss + clip 5.0，早停 patience=8（min delta 1e-8），≤30 epochs
- 结果写 phase_b_results.json：每配置含验证集整体/事件窗口/稳定窗口 MAE、
  实际训练轮数、耗时；失败配置（NaN）也记录，不静默丢弃

性能说明：整个特征张量仅 ~33MB，全量常驻 GPU，批次通过向量化索引
（origins[:,None] + arange 偏移）直接从 GPU 张量 gather，
窗口语义与 NodeWindowDataset 逐位等价（历史 [origin-95, origin]，
未来 (origin, origin+4]，标准化参数相同）——消除单线程 Python
数据加载瓶颈（实测每 epoch 80-100s → 10-15s）。
"""

from __future__ import annotations

import gc
import json
import os
import time
from pathlib import Path

import numpy as np
import torch
from torch import nn

from evcs_station_graph.data import WindowSpec, load_tensor_bundle
from evcs_station_graph.evaluation import apply_frozen_event_rule, fit_frozen_event_rule
from evcs_station_graph.graphs import build_relation_set
from evcs_station_graph.models.graph import AdaptiveGraphForecast, StaticGraphForecast
from evcs_station_graph.models.residual import EventResidualCorrection
from evcs_station_graph.models.tcn import TemporalConvNet
from evcs_station_graph.reproducibility import set_global_seed

BUNDLE_PATH = "data/processed/SG-DATA-005-primary-tensor.npz"
RESULTS_FILE = "phase_b_results.json"
SEED = 2024
# 设备选择：默认 cuda:1。GPU0 被 vLLM 主进程与 ASR 服务共享，
# 同步等待模式下 kernel 被抢占（实测单步 3.3s）；GPU1 计算空闲
# （vLLM 仅占显存），实测同步模式 13.3ms/step。
DEVICE = torch.device(
    os.environ.get("PHASE_B_DEVICE", "cuda:1" if torch.cuda.is_available() else "cpu")
)
EPOCHS = 30
PATIENCE = 8
BATCH_SIZE = 256
LR = 1e-3
WEIGHT_DECAY = 1e-4

bundle = load_tensor_bundle(BUNDLE_PATH)
spec = WindowSpec(history_steps=96, forecast_steps=4)
NUM_NODES = len(bundle.node_ids)
INPUT_DIM = len(bundle.feature_names)
HORIZON = spec.forecast_steps
train_end = int(bundle.split_origins["train"][-1])
T = len(bundle.timestamps_ns)

# ---- 冻结事件规则（验证集拟合，仅 train/val origins 应用） ----
rule = fit_frozen_event_rule(bundle, quantile=0.95, window_extension=2)
trigger_all = np.zeros((T, NUM_NODES), dtype=bool)
for split_name in ("train", "validation"):
    origins = bundle.split_origins[split_name]
    trigger_all[origins] = apply_frozen_event_rule(bundle, origins, rule)

# ---- GPU 常驻张量（标准化与 NodeWindowDataset 相同公式） ----
X_GPU = torch.from_numpy(
    (bundle.features - bundle.feature_mean[None, None, :]) / bundle.feature_std[None, None, :]
).to(DEVICE)                                        # [T, N, F]
Y_GPU = torch.from_numpy(
    (bundle.targets - bundle.target_mean[None, :]) / bundle.target_std[None, :]
).to(DEVICE)                                        # [T, N]
TRIG_GPU = torch.from_numpy(trigger_all).to(DEVICE)  # [T, N]

# 预构建向量化窗口索引（train/val 各自的 origins）
SPLIT_IDX: dict[str, dict[str, torch.Tensor]] = {}
for split_name in ("train", "validation"):
    origins_np = bundle.split_origins[split_name].astype(np.int64)
    origins = torch.from_numpy(origins_np).to(DEVICE)
    hist_offsets = torch.arange(-95, 1, device=DEVICE)          # [96]
    fut_offsets = torch.arange(1, 1 + HORIZON, device=DEVICE)   # [H]
    SPLIT_IDX[split_name] = {
        "origins": origins,                                     # [S]
        "hist": origins[:, None] + hist_offsets[None, :],       # [S, 96]
        "fut": origins[:, None] + fut_offsets[None, :],         # [S, H]
    }
print(f"数据常驻 GPU 完成：train={len(SPLIT_IDX['train']['origins'])} origins, "
      f"val={len(SPLIT_IDX['validation']['origins'])} origins, "
      f"显存 {int(torch.cuda.memory_allocated() / 2**20) if DEVICE.type == 'cuda' else 0} MiB",
      flush=True)


def build_adjacencies(top_k: int) -> list[np.ndarray]:
    """按 top_k 重建训练期三类关系矩阵（B2 每个取值独立构建）。"""
    relation_set = build_relation_set(
        bundle.features[: train_end + 1],
        bundle.targets[: train_end + 1],
        bundle.feature_names,
        top_k=top_k,
    )
    return relation_set.as_list()


def train_and_eval(model_factory, config_desc: dict) -> dict:
    """单配置训练 + 验证集评价（早停），返回验证指标记录。

    ``model_factory`` 是零参数可调用对象：先重置全局种子、再构造模型，
    保证每个超参数配置的初始权重与数据顺序完全相同（公平性要求——
    若在重置种子前构造模型，初始权重会依赖前一配置训练后的 RNG 状态）。
    """
    set_global_seed(SEED)
    model = model_factory().to(DEVICE)
    optimizer = torch.optim.AdamW(
        [p for p in model.parameters() if p.requires_grad],
        lr=LR, weight_decay=WEIGHT_DECAY,
    )
    criterion = nn.L1Loss()
    train_idx = SPLIT_IDX["train"]
    val_idx = SPLIT_IDX["validation"]
    n_train = len(train_idx["origins"])
    generator = torch.Generator().manual_seed(SEED)

    best_val = float("inf")
    best_state = None
    best_metrics: dict = {}
    stale = 0
    started = time.perf_counter()
    record: dict = {"config": config_desc}

    for epoch in range(1, EPOCHS + 1):
        # ---- 训练轮（GPU 内向量化取批，shuffle 顺序由固定种子 generator 决定） ----
        model.train()
        perm = torch.randperm(n_train, generator=generator).to(DEVICE)
        train_sum = 0.0
        for start in range(0, n_train, BATCH_SIZE):
            idx = perm[start: start + BATCH_SIZE]
            x = X_GPU[train_idx["hist"][idx]]       # [b, 96, N, F]
            y = Y_GPU[train_idx["fut"][idx]]        # [b, H, N]
            trigger = TRIG_GPU[train_idx["origins"][idx]]  # [b, N]
            optimizer.zero_grad(set_to_none=True)
            loss = criterion(model(x, rule_trigger=trigger).prediction, y)
            if not torch.isfinite(loss):
                record["error"] = f"epoch {epoch} 损失非有限"
                return record
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            optimizer.step()
            train_sum += float(loss.detach()) * len(idx)

        # ---- 验证集评价（整体 + 事件/稳定窗口分层，顺序遍历不打乱） ----
        model.eval()
        val_sum = val_count = 0.0
        ev_sum = ev_count = 0.0
        st_sum = st_count = 0.0
        n_val = len(val_idx["origins"])
        with torch.no_grad():
            for start in range(0, n_val, BATCH_SIZE):
                idx = torch.arange(start, min(start + BATCH_SIZE, n_val), device=DEVICE)
                x = X_GPU[val_idx["hist"][idx]]
                y = Y_GPU[val_idx["fut"][idx]]
                trigger = TRIG_GPU[val_idx["origins"][idx]]
                pred = model(x, rule_trigger=trigger).prediction
                abs_err = (pred - y).abs()          # [b, H, N]
                val_sum += float(abs_err.sum())
                val_count += abs_err.numel()
                gate = trigger.to(abs_err.dtype)[:, None, :].expand_as(abs_err)
                ev_sum += float((abs_err * gate).sum())
                ev_count += float(gate.sum())
                st_sum += float((abs_err * (1 - gate)).sum())
                st_count += float((1 - gate).sum())
        val_mae = val_sum / max(val_count, 1)
        epoch_time = time.perf_counter() - started
        print(f"    epoch {epoch:2d}: train_mae={train_sum / n_train:.5f} "
              f"val_mae={val_mae:.5f} ({epoch_time:.0f}s)", flush=True)
        if val_mae < best_val - 1e-8:
            best_val = val_mae
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            best_metrics = {
                "val_mae_event_window": ev_sum / max(ev_count, 1),
                "val_mae_stable_window": st_sum / max(st_count, 1),
            }
            stale = 0
        else:
            stale += 1
            if stale >= PATIENCE:
                break

    record.update(
        best_val_mae=best_val,
        epochs_run=epoch,
        wall_seconds=round(time.perf_counter() - started, 1),
        **best_metrics,
    )
    record["_best_state"] = best_state  # 内部复用（B4 base），不写入 JSON
    return record


def cleanup() -> None:
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def main() -> None:
    results: list[dict] = []
    started_all = time.perf_counter()

    # ==================== B1：TCN levels × hidden ====================
    print("=" * 60, flush=True)
    print("B1：TCN 时间编码（levels∈{3,5,6} × hidden∈{32,64}）", flush=True)
    b1_records = []
    for levels in (3, 5, 6):
        for hidden in (32, 64):
            desc = {"stage": "B1", "model": "TCN", "levels": levels, "hidden_dim": hidden}
            print(f"  ▶ {desc}", flush=True)
            rec = train_and_eval(
                lambda: TemporalConvNet(INPUT_DIM, HORIZON, hidden_dim=hidden, levels=levels, dropout=0.1),
                desc,
            )
            b1_records.append(rec)
            results.append({k: v for k, v in rec.items() if k != "_best_state"})
            print(f"  ✓ levels={levels} hidden={hidden}: best_val_mae={rec.get('best_val_mae', float('nan')):.5f} "
                  f"(epochs={rec.get('epochs_run')}, {rec.get('wall_seconds')}s)", flush=True)
            cleanup()
    b1_best = min(b1_records, key=lambda r: r.get("best_val_mae", float("inf")))
    best_levels = b1_best["config"]["levels"]
    best_hidden = b1_best["config"]["hidden_dim"]
    print(f"  → B1 最佳：levels={best_levels}, hidden={best_hidden}, val_mae={b1_best['best_val_mae']:.5f}",
          flush=True)

    # B1 最佳 TCN 重建并加载 best_state，作为 B4 的冻结 base
    best_tcn = TemporalConvNet(INPUT_DIM, HORIZON, hidden_dim=best_hidden, levels=best_levels, dropout=0.1)
    best_tcn.load_state_dict(b1_best["_best_state"])

    # ==================== B2：StaticGraph top_k ====================
    print("=" * 60, flush=True)
    print(f"B2：StaticGraph top_k∈{{3,5,7}}（levels={best_levels}, hidden={best_hidden}）", flush=True)
    for top_k in (3, 5, 7):
        adjacencies = build_adjacencies(top_k)
        desc = {"stage": "B2", "model": "StaticGraph", "top_k": top_k,
                "levels": best_levels, "hidden_dim": best_hidden}
        print(f"  ▶ {desc}", flush=True)
        rec = train_and_eval(
            lambda: StaticGraphForecast(
                INPUT_DIM, HORIZON, NUM_NODES, adjacencies,
                hidden_dim=best_hidden, levels=best_levels, dropout=0.1,
            ),
            desc,
        )
        results.append({k: v for k, v in rec.items() if k != "_best_state"})
        print(f"  ✓ top_k={top_k}: best_val_mae={rec.get('best_val_mae', float('nan')):.5f} "
              f"(epochs={rec.get('epochs_run')}, {rec.get('wall_seconds')}s)", flush=True)
        cleanup()

    # ==================== B3：AdaptiveGraph embedding → fixed_weight ====================
    print("=" * 60, flush=True)
    print("B3：AdaptiveGraph embedding_dim∈{8,12,16} → fixed_weight∈{0.2,0.5}", flush=True)
    adjacencies = build_adjacencies(5)
    b3_embed_records = []
    for embed_dim in (8, 12, 16):
        desc = {"stage": "B3a", "model": "AdaptiveGraph", "embedding_dim": embed_dim,
                "fixed_weight": 0.3, "levels": best_levels, "hidden_dim": best_hidden}
        print(f"  ▶ {desc}", flush=True)
        rec = train_and_eval(
            lambda: AdaptiveGraphForecast(
                INPUT_DIM, HORIZON, NUM_NODES, adjacencies,
                hidden_dim=best_hidden, embedding_dim=embed_dim,
                levels=best_levels, dropout=0.1, fixed_weight=0.3, top_k=5,
            ),
            desc,
        )
        b3_embed_records.append(rec)
        results.append({k: v for k, v in rec.items() if k != "_best_state"})
        print(f"  ✓ embedding_dim={embed_dim}: best_val_mae={rec.get('best_val_mae', float('nan')):.5f}", flush=True)
        cleanup()
    best_embed = min(b3_embed_records, key=lambda r: r.get("best_val_mae", float("inf")))["config"]["embedding_dim"]
    for fixed_weight in (0.2, 0.5):
        desc = {"stage": "B3b", "model": "AdaptiveGraph", "embedding_dim": best_embed,
                "fixed_weight": fixed_weight, "levels": best_levels, "hidden_dim": best_hidden}
        print(f"  ▶ {desc}", flush=True)
        rec = train_and_eval(
            lambda: AdaptiveGraphForecast(
                INPUT_DIM, HORIZON, NUM_NODES, adjacencies,
                hidden_dim=best_hidden, embedding_dim=best_embed,
                levels=best_levels, dropout=0.1, fixed_weight=fixed_weight, top_k=5,
            ),
            desc,
        )
        results.append({k: v for k, v in rec.items() if k != "_best_state"})
        print(f"  ✓ fixed_weight={fixed_weight} (embed={best_embed}): best_val_mae={rec.get('best_val_mae', float('nan')):.5f}",
              flush=True)
        cleanup()

    # ==================== B4：EventResidual hidden → bound ====================
    print("=" * 60, flush=True)
    print("B4：EventResidual residual_hidden∈{16,32,64} → residual_bound∈{0.3,1.0}", flush=True)
    print(f"    （冻结 base = B1 最佳 TCN：levels={best_levels}, hidden={best_hidden}）", flush=True)
    b4_hidden_records = []
    for res_hidden in (16, 32, 64):
        desc = {"stage": "B4a", "model": "EventResidual", "residual_hidden_dim": res_hidden,
                "residual_bound": 0.5, "base": f"TCN-l{best_levels}-h{best_hidden}"}
        print(f"  ▶ {desc}", flush=True)
        rec = train_and_eval(
            lambda: EventResidualCorrection(
                best_tcn, build_adjacencies(5), HORIZON,
                hidden_dim=res_hidden, residual_bound=0.5, freeze_base=True,
                feature_names=bundle.feature_names, base_model_type="temporal",
            ),
            desc,
        )
        b4_hidden_records.append(rec)
        results.append({k: v for k, v in rec.items() if k != "_best_state"})
        print(f"  ✓ residual_hidden={res_hidden}: best_val_mae={rec.get('best_val_mae', float('nan')):.5f}", flush=True)
        cleanup()
    best_res_hidden = min(b4_hidden_records, key=lambda r: r.get("best_val_mae", float("inf")))["config"]["residual_hidden_dim"]
    for res_bound in (0.3, 1.0):
        desc = {"stage": "B4b", "model": "EventResidual", "residual_hidden_dim": best_res_hidden,
                "residual_bound": res_bound, "base": f"TCN-l{best_levels}-h{best_hidden}"}
        print(f"  ▶ {desc}", flush=True)
        rec = train_and_eval(
            lambda: EventResidualCorrection(
                best_tcn, build_adjacencies(5), HORIZON,
                hidden_dim=best_res_hidden, residual_bound=res_bound, freeze_base=True,
                feature_names=bundle.feature_names, base_model_type="temporal",
            ),
            desc,
        )
        results.append({k: v for k, v in rec.items() if k != "_best_state"})
        print(f"  ✓ residual_bound={res_bound} (hidden={best_res_hidden}): best_val_mae={rec.get('best_val_mae', float('nan')):.5f}",
              flush=True)
        cleanup()

    # ==================== 汇总 ====================
    summary = {
        "seed": SEED,
        "device": str(DEVICE),
        "batch_size": BATCH_SIZE,
        "lr": LR,
        "weight_decay": WEIGHT_DECAY,
        "epochs_max": EPOCHS,
        "patience": PATIENCE,
        "total_wall_minutes": round((time.perf_counter() - started_all) / 60, 1),
        "b1_best": {"levels": best_levels, "hidden_dim": best_hidden,
                    "val_mae": b1_best["best_val_mae"]},
        "b3_best_embedding_dim": best_embed,
        "b4_best_residual_hidden": best_res_hidden,
        "records": results,
        "discipline": "仅训练集+验证集；测试集未参与任何筛选；单种子 2024",
    }
    Path(RESULTS_FILE).write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8",
    )
    print("=" * 60, flush=True)
    print(f"全部完成：{len(results)} 个配置，总耗时 {summary['total_wall_minutes']} 分钟", flush=True)
    print(f"结果已写入 {RESULTS_FILE}", flush=True)


if __name__ == "__main__":
    main()
