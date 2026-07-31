"""传统基线实验（第 3 章主表对比，CPU）：Persistence / ARIMA / LightGBM / XGBoost。

目的（正式基线，测试集三种子无种子概念——传统基线不涉及随机初始化，
预测确定性，一次运行即可入表）：
  - Persistence：日周期持久化（预测 = 96 步前的值，复制 4 步）——最简基线
  - ARIMA(2,1,2)：逐节点拟合训练尾段序列，测试期 apply 滚动前向
  - LightGBM / XGBoost：手工特征（近期值 + 日周期 + 统计量）回归
评价：统一用 stratified_metrics（全局/事件/稳定窗口），输出 JSON。

用法（服务器 CPU 后台）：
  export PYTHONPATH=src
  .venv/bin/python scripts/run_traditional_baselines.py
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import Any, Callable

import numpy as np

from evcs_station_graph.data import (
    NodeWindowDataset,
    WindowSpec,
    load_tensor_bundle,
)
from evcs_station_graph.evaluation import (
    stratified_metrics,
)
from evcs_station_graph.reproducibility import write_json

# ARIMA 拟合用训练序列尾段长度（全序列 118K 步拟合过慢且近端权重更大）
ARIMA_FIT_LENGTH = 4096
# ARIMA 阶数：(p,d,q)=(2,1,2)，低阶固定（滚动 apply 快，参数搜索无必要）
ARIMA_ORDER = (2, 1, 2)
# LightGBM/XGBoost 特征：最近值 + 日周期值 + 窗口统计量
FEATURE_WINDOW = 96


def _build_feature_matrix(
    features: np.ndarray, origins: np.ndarray, node_ids: np.ndarray,
) -> np.ndarray:
    """为 (origin, node) 组合构建手工特征 [K, F_feat]。

    特征设计（不依赖未来，仅用历史窗口）：
      - 最近 4 步的 7 维特征（时间局部性）
      - 日周期（96 步前）的 4 步 7 维特征（周期模式）
      - 96 步窗口统计：均值/标准差/最大值/非零率（负荷/事件聚合）
    """
    features_flat = features.reshape(features.shape[0], -1)  # [T, N*F]
    nf = features.shape[2]
    rows = []
    for origin in origins:
        base = origin - FEATURE_WINDOW
        recent = features_flat[origin - 4: origin]  # [4, N*F] 最后 4 步
        daily = features_flat[origin - 95: origin - 91]  # [4, N*F] 一天前同时刻（对应预测目标 [O+1,O+5)）
        win = features[base: origin]  # [96, N, F]
        row = np.concatenate([
            recent.ravel(), daily.ravel(),
            win.mean(axis=0).ravel(), win.std(axis=0).ravel(),
            win.max(axis=0).ravel(), (win > 0).mean(axis=0).ravel(),
        ])  # [4*7*2 + 4*7*4] 维度
        rows.append(row)
    return np.stack(rows)


def _arima_node_worker(
    node_idx: int, dataset_path: str, origins: np.ndarray,
    fit_length: int, horizon: int,
) -> np.ndarray:
    """单节点 ARIMA 滚动预测 worker（独立进程，multiprocessing spawn 安全）。

    参数估计口径：在训练尾段拟合一次（近似假设 15 分钟粒度下近段序列平稳），
    测试期对每个预测起点用最近 96 步 apply 更新状态但不重估参数。
    返回 [S, H] 预测（物理量纲）。独立进程避免 GIL 与 statsmodels 内部状态串扰。
    """
    bundle = load_tensor_bundle(dataset_path)
    from statsmodels.tsa.arima.model import ARIMA

    train_end = int(bundle.split_origins["train"][-1])
    series = bundle.features[: train_end + 1, node_idx, 0]  # [T] 负荷特征
    tail = series[-fit_length:]
    model = ARIMA(tail, order=ARIMA_ORDER).fit(method_kwargs={"maxiter": 50})
    pred = np.zeros((len(origins), horizon), dtype=np.float32)
    for i, origin in enumerate(origins):
        # 以最近 96 步作为已知末端，apply 后前向 4 步
        hist = bundle.features[origin - 96: origin, node_idx, 0]
        fitted = model.apply(hist)
        pred[i] = np.asarray(fitted.forecast(horizon), dtype=np.float32)
    return pred


def _predict_all_origins(
    predict_origin: Callable[[int], np.ndarray],
    origins: np.ndarray, num_nodes: int, horizon: int,
) -> np.ndarray:
    """对每个 origin 预测 [S,H,N]，组装为 [S,H,N] 数组。"""
    out = np.zeros((len(origins), horizon, num_nodes), dtype=np.float32)
    for i, origin in enumerate(origins):
        out[i] = predict_origin(origin)
    return out


def _evaluate(
    prediction: np.ndarray, bundle: Any, origins: np.ndarray,
    name: str, output_dir: Path,
) -> dict[str, Any]:
    """统一评价：物理量纲 truth vs prediction → 分层指标（完整留存）。

    origins 为本次评价使用的预测起点（可能被 --max-validations 截断），
    truth 直接按 [S, H, N] 索引 targets，不再重新构造数据集。

    证据链留存（论文表 3-1 显著性检验与分层明细需要）：
      - 完整 metrics（global/nonzero_load/event/stable/by_horizon/by_node）
      - 预测长表 [S,H,N] + origin 索引（Bootstrap 显著性检验用），npz 格式
    """
    horizon = prediction.shape[1]
    # 与正式管线口径完全一致（data/dataset.py:78）：预测目标为 [O+1, O+1+H)
    offset = origins[:, None] + 1 + np.arange(horizon)[None, :]  # [S,H]
    truth = bundle.targets[offset]  # [S,H,N]
    target_event = bundle.event_labels[offset]  # [S,H,N] 真实事件标签（非规则触发掩码）
    metrics = stratified_metrics(
        truth, prediction,
        target_event=target_event, node_ids=bundle.node_ids.tolist(),
    )
    result = {
        "model": name,
        "global_mae": metrics["global"]["mae"],
        "global_rmse": metrics["global"]["rmse"],
        "event_mae": metrics["event_window"]["mae"],
        "stable_mae": metrics["stable_window"]["mae"],
        "nonzero_load_mae": metrics["nonzero_load"]["mae"],
        "by_horizon": metrics["by_horizon"],
        "by_node": metrics["by_node"],
    }
    # 预测长表落盘：origin 索引 + [S,H,N] 预测/真值（Bootstrap 显著性检验输入）
    save_path = output_dir / f"predictions_{name}.npz"
    np.savez_compressed(
        save_path, origins=origins,
        prediction=prediction.astype(np.float32), truth=truth.astype(np.float32),
        target_event=target_event.astype(bool),
    )
    result["predictions_file"] = str(save_path)
    print(f"  {name}: global={result['global_mae']:.5f} "
          f"event={result['event_mae']:.4f} stable={result['stable_mae']:.5f}", flush=True)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="传统基线（主表对比）")
    parser.add_argument("--dataset", default="data/processed/SG-DATA-005-primary-tensor.npz")
    parser.add_argument("--output-dir", default="outputs/analysis/traditional_baselines")
    parser.add_argument("--max-validations", type=int, default=0,
                        help="调试用：限制处理的预测起点数（0=全部）")
    parser.add_argument("--only", default="all",
                        choices=["all", "persistence", "lgbm", "xgb", "arima"],
                        help="只运行指定段（macOS 上 LGBM/XGB 同进程 80 个模型连续训练触发段错误，分段可断点续跑）")
    args = parser.parse_args()

    bundle = load_tensor_bundle(args.dataset)
    spec = WindowSpec(history_steps=96, forecast_steps=4)
    ds_test = NodeWindowDataset(bundle, "test", spec)
    origins = ds_test.origins
    num_nodes = len(bundle.node_ids)
    horizon = int(spec.forecast_steps)
    if args.max_validations:
        origins = origins[: args.max_validations]
    started = time.perf_counter()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, Any]] = []
    only = args.only

    # ---- 1. Persistence：日周期持久化 ----
    # 定义：预测 = 一天前（96 步）同时刻的 4 步负荷（y_hat[O+1+h] = y[O+1+h-96]）。
    # 预测目标为 [O+1, O+5)，日周期对应 [O-95, O-91)。
    # 与旧项目 EXP-108 的"最后可见值持续"口径不同，论文表 3-1 表注需注明。
    if only in ("all", "persistence"):
        print("=== Persistence（日周期）===", flush=True)
        persistence_origin = lambda origin: bundle.targets[origin - 95: origin - 91]
        results.append(_evaluate(
            _predict_all_origins(persistence_origin, origins, num_nodes, horizon),
            bundle, origins, "Persistence", output_dir,
        ))

    features_all = bundle.features  # [T,N,F]
    train_end = int(bundle.split_origins["train"][-1])

    # ---- 2. LightGBM / XGBoost（独立分段：同进程连续 80 个模型在 macOS
    # 上触发段错误，分进程运行 + 每模型进度打印以精确定位） ----
    if only in ("all", "lgbm", "xgb"):
        print(f"=== {only.upper() if only != 'all' else 'LGBM+XGB'} ===", flush=True)
        train_origins = bundle.split_origins["train"][FEATURE_WINDOW:]
        # float32：float64 的 83K×840 特征矩阵（560MB）+ LightGBM Dataset
        # 复制会触发内存峰值 → macOS 上 malloc 失败段错误（exit 139）
        x_train = np.ascontiguousarray(
            _build_feature_matrix(features_all, train_origins, bundle.node_ids),
            dtype=np.float32,
        )
        # 训练标签与正式管线一致：预测目标 [O+1, O+1+H)
        y_train = bundle.targets[train_origins[:, None] + 1 + np.arange(horizon)[None, :]]  # [K,H,N]

        x_test = np.ascontiguousarray(
            _build_feature_matrix(features_all, origins, bundle.node_ids),
            dtype=np.float32,
        )

        # 注意（审查后修复）：LightGBM 在非连续数组视图上构建 Dataset 会
        # 段错误（macOS exit 139，__init_from_np2d），故 x/y 一律
        # np.ascontiguousarray；每个 (n,h) 新建模型实例，避免实例复用。
        for name in (("LightGBM", "XGBoost") if only == "all" else
                     (("LightGBM",) if only == "lgbm" else ("XGBoost",))):
            if name == "LightGBM":
                import lightgbm as lgb
            else:
                import xgboost as xgb
            # 逐节点独立模型（与基线口径一致：节点级预测）
            pred = np.zeros((len(origins), horizon, num_nodes), dtype=np.float32)
            for n in range(num_nodes):
                for h in range(horizon):
                    y_h = np.ascontiguousarray(y_train[:, h, n])  # [K]
                    if name == "LightGBM":
                        # n_jobs=1：LightGBM OpenMP 多线程在特定数据上随机
                        # 段错误（n_jobs=4 时 n=8 h=0 必崩），单线程规避
                        model = lgb.LGBMRegressor(
                            n_estimators=300, learning_rate=0.05, max_depth=6,
                            num_leaves=31, random_state=2024, verbose=-1, n_jobs=1,
                        )
                        model.fit(x_train, y_h)
                    else:
                        model = xgb.XGBRegressor(
                            n_estimators=300, learning_rate=0.05, max_depth=6,
                            random_state=2024, verbosity=0, n_jobs=4,
                        )
                        model.fit(x_train, y_h)
                    pred[:, h, n] = model.predict(x_test)
                    print(f"  {name} n={n} h={h} 完成", flush=True)
            results.append(_evaluate(pred, bundle, origins, name, output_dir))

    # ---- 3. ARIMA(2,1,2) 滚动前向 ----
    # 参数估计口径：每个节点仅在训练尾段拟合一次（近似假设 15 分钟粒度下
    # 近段序列平稳），测试期对每个预测起点用最近 96 步 apply 更新状态但不重估参数。
    # 178K 次滚动预测单线程需 2-3 小时，按节点并行（10 进程）压到 ~20 分钟
    if only in ("all", "arima"):
        print("=== ARIMA(2,1,2) 并行（10 节点）===", flush=True)
        import multiprocessing as mp

        ctx = mp.get_context("spawn")
        with ctx.Pool(num_nodes) as pool:
            per_node = pool.starmap(
                _arima_node_worker,
                [(n, args.dataset, origins, ARIMA_FIT_LENGTH, horizon)
                 for n in range(num_nodes)],
            )
        pred = np.stack(per_node, axis=2)  # [S, H] × 10 → [S, H, N]
        print("  ARIMA 10 节点全部完成", flush=True)
        results.append(_evaluate(pred, bundle, origins, "ARIMA", output_dir))
    write_json({
        "analysis": "traditional baselines (chapter 3 main table)",
        "models": results,
        "num_origins": int(len(origins)),
        "elapsed_seconds": time.perf_counter() - started,
    }, output_dir / "traditional_baselines_summary.json")
    print(f"结果已写入：{output_dir / 'traditional_baselines_summary.json'}"
          f"（总耗时 {time.perf_counter() - started:.0f}s）", flush=True)


if __name__ == "__main__":
    main()
