"""一次性夜跑：B6 三底座对照 → SG-EXP-002～006 正式实验。

执行顺序：
  B6   三底座 EventResidual 对照（StaticGraph/AdaptiveGraph，各 1 种子验证）
        TCN base 结果复用 B4 已有数据
  ─── 选择最优底座 → 写入 SG-EXP-005 配置 ───
  SG-EXP-002  TCN（levels=6, hidden=32, 3 种子）
  SG-EXP-003  StaticGraph（levels=6, hidden=32, top_k=3, 3 种子）
  SG-EXP-004  AdaptiveGraph（levels=6, hidden=32, embed=12, fixed_weight=0.5, 3 种子）
  SG-EXP-005  EventResidual（B6 最优底座, 3 种子, 冻结）
  SG-EXP-006  机制实验（15 变体 × 3 种子）

超参数来源：阶段 B 预筛选结果（phase_b_results.json）。
底座选择：B6 验证集 event_window MAE 最低者。
所有配置写入 outputs/night_run_YYYYMMDD/，含 resolved config。
测试集仅用于最终评价，不参与任何超参数选择。
"""

from __future__ import annotations

import copy
import gc
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch import nn

# ── GPU 配置 ──
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "1")
DEVICE = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

from evcs_station_graph.config import load_experiment_config
from evcs_station_graph.data import WindowSpec, load_tensor_bundle
from evcs_station_graph.evaluation import apply_frozen_event_rule, fit_frozen_event_rule
from evcs_station_graph.experiments.mechanism import run_mechanism_suite
from evcs_station_graph.graphs import build_relation_set
from evcs_station_graph.models.graph import AdaptiveGraphForecast, StaticGraphForecast
from evcs_station_graph.models.residual import EventResidualCorrection
from evcs_station_graph.models.tcn import TemporalConvNet
from evcs_station_graph.reproducibility import set_global_seed, write_json
from evcs_station_graph.training import train_experiment

PROJECT_PATH = Path("configs/project.yaml")
BUNDLE_PATH = "data/processed/SG-DATA-005-primary-tensor.npz"
B_RESULTS = Path("phase_b_results.json")

# ── B 阶段最优超参数 ──
B1_BEST = {"levels": 6, "hidden_dim": 32}
B2_BEST_TOP_K = 3
B3_BEST = {"embedding_dim": 12, "fixed_weight": 0.5}
B4_BEST = {"residual_hidden_dim": 64, "residual_bound": 1.0}

SEEDS = [2024, 2025, 2026]
SPEC = WindowSpec(history_steps=96, forecast_steps=4)
EPOCHS_B6 = 30
PATIENCE_B6 = 8
BATCH = 256
LR = 1e-3
WD = 1e-4

bundle = load_tensor_bundle(BUNDLE_PATH)
NUM_NODES = len(bundle.node_ids)
INPUT_DIM = len(bundle.feature_names)
T = len(bundle.timestamps_ns)
train_end = int(bundle.split_origins["train"][-1])

# ── 冻结事件规则 ──
rule = fit_frozen_event_rule(bundle, quantile=0.95, window_extension=2)
trigger_all = np.zeros((T, NUM_NODES), dtype=bool)
for s in ("train", "validation"):
    trigger_all[bundle.split_origins[s]] = apply_frozen_event_rule(bundle, bundle.split_origins[s], rule)

# ── GPU 常驻张量 ──
X_GPU = torch.from_numpy(
    (bundle.features - bundle.feature_mean[None, None, :]) / bundle.feature_std[None, None, :]
).to(DEVICE)
Y_GPU = torch.from_numpy(
    (bundle.targets - bundle.target_mean[None, :]) / bundle.target_std[None, :]
).to(DEVICE)
TRIG_GPU = torch.from_numpy(trigger_all).to(DEVICE)

SPLIT_IDX: dict[str, dict[str, torch.Tensor]] = {}
for split_name in ("train", "validation"):
    origins_np = bundle.split_origins[split_name].astype(np.int64)
    origins = torch.from_numpy(origins_np).to(DEVICE)
    SPLIT_IDX[split_name] = {
        "origins": origins,
        "hist": origins[:, None] + torch.arange(-95, 1, device=DEVICE)[None, :],
        "fut": origins[:, None] + torch.arange(1, 1 + SPEC.forecast_steps, device=DEVICE)[None, :],
    }

# ── 三类固定关系（top_k=3，B2 最优）──
FIXED_ADJS = build_relation_set(
    bundle.features[: train_end + 1], bundle.targets[: train_end + 1],
    bundle.feature_names, top_k=B2_BEST_TOP_K,
).as_list()


# ══════════════════════════════════════════════════════════════════
# B6：三底座 EventResidual 对照
# ══════════════════════════════════════════════════════════════════

def _train_b6_model(model_factory, label: str) -> dict:
    set_global_seed(2024)
    model = model_factory().to(DEVICE)
    optimizer = torch.optim.AdamW(
        [p for p in model.parameters() if p.requires_grad], lr=LR, weight_decay=WD)
    criterion = nn.L1Loss()
    train_idx = SPLIT_IDX["train"]
    val_idx = SPLIT_IDX["validation"]
    n_train = len(train_idx["origins"])
    gen = torch.Generator().manual_seed(2024)

    best_val = float("inf")
    best_ev = float("inf")
    best_state = None
    stale = 0
    t0 = time.perf_counter()
    for epoch in range(1, EPOCHS_B6 + 1):
        model.train()
        perm = torch.randperm(n_train, generator=gen).to(DEVICE)
        for start in range(0, n_train, BATCH):
            idx = perm[start: start + BATCH]
            x = X_GPU[train_idx["hist"][idx]]
            y = Y_GPU[train_idx["fut"][idx]]
            trig = TRIG_GPU[train_idx["origins"][idx]]
            optimizer.zero_grad(set_to_none=True)
            loss = criterion(model(x, rule_trigger=trig).prediction, y)
            if not torch.isfinite(loss):
                return {"label": label, "error": "NaN", "val_mae": float("nan"), "event_mae": float("nan")}
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            optimizer.step()

        model.eval()
        val_sum = ev_sum = 0.0
        val_cnt = ev_cnt = 0.0
        with torch.no_grad():
            n_val = len(val_idx["origins"])
            for start in range(0, n_val, BATCH):
                idx = torch.arange(start, min(start + BATCH, n_val), device=DEVICE)
                x = X_GPU[val_idx["hist"][idx]]
                y = Y_GPU[val_idx["fut"][idx]]
                trig = TRIG_GPU[val_idx["origins"][idx]]
                pred = model(x, rule_trigger=trig).prediction
                err = (pred - y).abs()
                val_sum += float(err.sum()); val_cnt += err.numel()
                gate = trig.to(err.dtype)[:, None, :].expand_as(err)
                ev_sum += float((err * gate).sum()); ev_cnt += float(gate.sum())
        val_mae = val_sum / max(val_cnt, 1)
        ev_mae = ev_sum / max(ev_cnt, 1)
        if val_mae < best_val - 1e-8:
            best_val, best_ev = val_mae, ev_mae
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            stale = 0
        else:
            stale += 1
            if stale >= PATIENCE_B6:
                break
    print(f"  {label}: val_mae={best_val:.5f} event_mae={best_ev:.5f} "
          f"epochs={epoch} time={time.perf_counter()-t0:.0f}s", flush=True)
    gc.collect(); torch.cuda.empty_cache()
    return {"label": label, "val_mae": best_val, "event_mae": best_ev,
            "epochs": epoch, "_best_state": best_state}


def run_b6() -> str:
    """运行 B6 三底座对照，返回最优底座类型名。"""
    print("=" * 60, flush=True)
    print("B6：三底座 EventResidual 对照", flush=True)

    results = {}
    # TCN base：复用 B4 实测结果
    tcn_b4 = {"label": "temporal", "val_mae": 0.05947, "event_mae": 0.97450}
    results["temporal"] = tcn_b4
    print(f"  temporal (复用 B4): val_mae={tcn_b4['val_mae']:.5f} "
          f"event_mae={tcn_b4['event_mae']:.5f}", flush=True)

    # StaticGraph base
    print("  ▶ static_graph base ...", flush=True)
    sg_base = StaticGraphForecast(
        INPUT_DIM, SPEC.forecast_steps, NUM_NODES, FIXED_ADJS,
        hidden_dim=B1_BEST["hidden_dim"], levels=B1_BEST["levels"], dropout=0.1,
    )
    rec_sg = _train_b6_model(
        lambda: EventResidualCorrection(
            sg_base, FIXED_ADJS, SPEC.forecast_steps,
            hidden_dim=B4_BEST["residual_hidden_dim"],
            residual_bound=B4_BEST["residual_bound"],
            freeze_base=True, feature_names=bundle.feature_names,
            base_model_type="static_graph",
        ),
        "static_graph",
    )
    results["static_graph"] = rec_sg

    # AdaptiveGraph base
    print("  ▶ adaptive_graph base ...", flush=True)
    ag_base = AdaptiveGraphForecast(
        INPUT_DIM, SPEC.forecast_steps, NUM_NODES, FIXED_ADJS,
        hidden_dim=B1_BEST["hidden_dim"], embedding_dim=B3_BEST["embedding_dim"],
        levels=B1_BEST["levels"], dropout=0.1,
        fixed_weight=B3_BEST["fixed_weight"], top_k=5,
    )
    rec_ag = _train_b6_model(
        lambda: EventResidualCorrection(
            ag_base, FIXED_ADJS, SPEC.forecast_steps,
            hidden_dim=B4_BEST["residual_hidden_dim"],
            residual_bound=B4_BEST["residual_bound"],
            freeze_base=True, feature_names=bundle.feature_names,
            base_model_type="adaptive_graph",
        ),
        "adaptive_graph",
    )
    results["adaptive_graph"] = rec_ag

    # 选择 event_window MAE 最低者
    valid = {k: v for k, v in results.items() if v.get("event_mae", float("inf")) < float("inf")}
    winner = min(valid, key=lambda k: valid[k]["event_mae"])
    print(f"  → B6 最优底座: {winner} (event_mae={valid[winner]['event_mae']:.5f})", flush=True)

    write_json({
        "stage": "B6", "results": {k: {kk: vv for kk, vv in v.items() if kk != "_best_state"}
                                   for k, v in results.items()},
        "winner": winner,
    }, NIGHT_ROOT / "b6_results.json")
    return winner


# ══════════════════════════════════════════════════════════════════
# 阶段 D：SG-EXP-002～006
# ══════════════════════════════════════════════════════════════════

def _apply_b_params(config: dict, **extra: Any) -> dict:
    """将 B 阶段最优超参数注入实验配置。"""
    cfg = copy.deepcopy(config)
    mp = cfg["experiment"].setdefault("model_params", {})
    mp["levels"] = B1_BEST["levels"]
    mp["hidden_dim"] = B1_BEST["hidden_dim"]
    mp["dropout"] = 0.1
    for k, v in extra.items():
        mp[k] = v
    graph = cfg["experiment"].setdefault("graph", {})
    graph.setdefault("top_k", B2_BEST_TOP_K)
    graph.setdefault("enabled_relations", ["load", "event", "pattern"])
    cfg["experiment"]["run_tag"] = NIGHT_TAG
    cfg["experiment"]["seeds"] = SEEDS
    return cfg


def run_phase_d(winner: str) -> None:
    print("=" * 60, flush=True)
    print("阶段 D：SG-EXP-002～006 正式实验", flush=True)
    overrides: tuple[str, ...] = ()

    # ── SG-EXP-002: TCN ──
    print("\n▶ SG-EXP-002 TCN", flush=True)
    cfg002 = _apply_b_params(load_experiment_config(
        PROJECT_PATH, "configs/experiments/SG-EXP-002-temporal-baseline.yaml", overrides))
    r002 = train_experiment(cfg002, bundle, str(NIGHT_ROOT))
    print(f"  ✓ {r002}", flush=True)

    # ── SG-EXP-003: StaticGraph ──
    print("\n▶ SG-EXP-003 StaticGraph", flush=True)
    cfg003 = _apply_b_params(load_experiment_config(
        PROJECT_PATH, "configs/experiments/SG-EXP-003-static-graph.yaml", overrides))
    cfg003["experiment"]["graph"]["top_k"] = B2_BEST_TOP_K
    r003 = train_experiment(cfg003, bundle, str(NIGHT_ROOT))
    print(f"  ✓ {r003}", flush=True)

    # ── SG-EXP-004: AdaptiveGraph ──
    print("\n▶ SG-EXP-004 AdaptiveGraph", flush=True)
    cfg004 = _apply_b_params(load_experiment_config(
        PROJECT_PATH, "configs/experiments/SG-EXP-004-adaptive-graph.yaml", overrides),
        embedding_dim=B3_BEST["embedding_dim"], fixed_weight=B3_BEST["fixed_weight"])
    r004 = train_experiment(cfg004, bundle, str(NIGHT_ROOT))
    print(f"  ✓ {r004}", flush=True)

    # ── SG-EXP-005: EventResidual（B6 最优底座）──
    print(f"\n▶ SG-EXP-005 EventResidual (base={winner})", flush=True)
    cfg005 = _apply_b_params(load_experiment_config(
        PROJECT_PATH, "configs/experiments/SG-EXP-005-event-residual.yaml", overrides),
        residual_hidden_dim=B4_BEST["residual_hidden_dim"],
        residual_bound=B4_BEST["residual_bound"],
        base_model_type=winner,
    )
    cfg005["experiment"]["model_params"]["freeze_base"] = True

    # 确定检查点根目录
    if winner == "temporal":
        base_root = r002
    elif winner == "static_graph":
        base_root = r003
    else:
        base_root = r004
    r005 = train_experiment(cfg005, bundle, str(NIGHT_ROOT), base_checkpoint=base_root)
    print(f"  ✓ {r005}", flush=True)

    # ── SG-EXP-006: 机制实验 ──
    print("\n▶ SG-EXP-006 机制实验 (15 变体 × 3 种子)", flush=True)
    r006 = run_mechanism_suite(
        PROJECT_PATH,
        "configs/experiments/SG-EXP-006-mechanism.yaml",
        bundle,
        str(NIGHT_ROOT),
        base_checkpoint=base_root,
        overrides=overrides,
    )
    print(f"  ✓ {r006}", flush=True)

    # ── 汇总 ──
    write_json({
        "night_tag": NIGHT_TAG,
        "b6_winner": winner,
        "b_params": {"levels": B1_BEST["levels"], "hidden_dim": B1_BEST["hidden_dim"],
                      "top_k": B2_BEST_TOP_K, "embedding_dim": B3_BEST["embedding_dim"],
                      "fixed_weight": B3_BEST["fixed_weight"],
                      "residual_hidden": B4_BEST["residual_hidden_dim"],
                      "residual_bound": B4_BEST["residual_bound"]},
        "runs": {"SG-EXP-002": str(r002), "SG-EXP-003": str(r003),
                 "SG-EXP-004": str(r004), "SG-EXP-005": str(r005),
                 "SG-EXP-006": str(r006)},
    }, NIGHT_ROOT / "night_manifest.json")
    print(f"\n全部完成！工件目录：{NIGHT_ROOT}", flush=True)


# ══════════════════════════════════════════════════════════════════
# 主流程
# ══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    NIGHT_TAG = time.strftime("%Y%m%d-%H%M%S")
    NIGHT_ROOT = Path("outputs/night_run") / NIGHT_TAG
    NIGHT_ROOT.mkdir(parents=True, exist_ok=True)
    print(f"夜跑开始：{NIGHT_TAG}", flush=True)
    print(f"工件目录：{NIGHT_ROOT}", flush=True)
    print(f"设备：{DEVICE}", flush=True)

    t_start = time.perf_counter()

    # B6
    winner = run_b6()

    # 阶段 D
    run_phase_d(winner)

    elapsed = (time.perf_counter() - t_start) / 60
    print(f"\n总耗时：{elapsed:.1f} 分钟", flush=True)
