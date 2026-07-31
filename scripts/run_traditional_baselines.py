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
    apply_frozen_event_rule,
    fit_frozen_event_rule,
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
        daily = features_flat[origin - 96: origin - 92]  # [4, N*F] 一天前同时刻（与目标时段对齐）
        win = features[base: origin]  # [96, N, F]
        row = np.concatenate([
            recent.ravel(), daily.ravel(),
            win.mean(axis=0).ravel(), win.std(axis=0).ravel(),
            win.max(axis=0).ravel(), (win > 0).mean(axis=0).ravel(),
        ])  # [4*7*2 + 4*7*4] 维度
        rows.append(row)
    return np.stack(rows)


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
    trigger_by_origin: np.ndarray, name: str, output_dir: Path,
) -> dict[str, Any]:
    """统一评价：物理量纲 truth vs prediction → 分层指标（完整留存）。

    origins 为本次评价使用的预测起点（可能被 --max-validations 截断），
    truth 直接按 [S, H, N] 索引 targets，不再重新构造数据集。

    证据链留存（论文表 3-1 显著性检验与分层明细需要）：
      - 完整 metrics（global/nonzero_load/event/stable/by_horizon/by_node）
      - 预测长表 [S,H,N] + origin 索引（Bootstrap 显著性检验用），npz 格式
    """
    horizon = prediction.shape[1]
    truth = bundle.targets[origins[:, None] + np.arange(horizon)[None, :]]  # [S,H,N]
    # 触发矩阵 [S,N] 广播到 [S,H,N]（与 engine._predict 的 target_event 形状一致）
    target_event = np.broadcast_to(
        (trigger_by_origin[origins] > 0)[:, None, :],
        (len(origins), horizon, truth.shape[2]),
    )
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

    # 事件规则（与正式评价一致）
    rule = fit_frozen_event_rule(bundle, quantile=0.95, window_extension=2)
    trigger_by_origin = np.zeros((len(bundle.timestamps_ns), len(bundle.node_ids)), dtype=bool)
    trigger_by_origin[origins] = apply_frozen_event_rule(bundle, origins, rule)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, Any]] = []

    # ---- 1. Persistence：日周期持久化 ----
    # 定义：预测 = 一天前（96 步）同时刻的 4 步负荷（y_hat[t+h] = y[t+h-96]）。
    # 与旧项目 EXP-108 的"最后可见值持续"口径不同，论文表 3-1 表注需注明。
    print("=== Persistence（日周期）===", flush=True)
    persistence_origin = lambda origin: bundle.targets[origin - 96: origin - 92]
    results.append(_evaluate(
        _predict_all_origins(persistence_origin, origins, num_nodes, horizon),
        bundle, origins, trigger_by_origin, "Persistence", output_dir,
    ))

    # ---- 2. LightGBM / XGBoost ----
    print("=== LightGBM / XGBoost ===", flush=True)
    features_all = bundle.features  # [T,N,F]
    train_end = int(bundle.split_origins["train"][-1])
    train_origins = bundle.split_origins["train"][FEATURE_WINDOW:]
    x_train = _build_feature_matrix(features_all, train_origins, bundle.node_ids)
    y_train = bundle.targets[train_origins[:, None] + np.arange(horizon)[None, :]]  # [K,H,N]

    x_test = _build_feature_matrix(features_all, origins, bundle.node_ids)

    import lightgbm as lgb
    import xgboost as xgb

    for name, fit_predict in [
        ("LightGBM", None), ("XGBoost", None),
    ]:
        # 逐节点独立模型（与基线口径一致：节点级预测）
        pred = np.zeros((len(origins), horizon, num_nodes), dtype=np.float32)
        for n in range(num_nodes):
            y_n = y_train[:, :, n]  # [K, H]
            if name == "LightGBM":
                model = lgb.LGBMRegressor(
                    n_estimators=300, learning_rate=0.05, max_depth=6,
                    num_leaves=31, random_state=2024, verbose=-1,
                )
                # 多输出：为每个 horizon 训练一个模型（简单可靠）
                for h in range(horizon):
                    model.fit(x_train, y_n[:, h])
                    pred[:, h, n] = model.predict(x_test)
            else:
                model = xgb.XGBRegressor(
                    n_estimators=300, learning_rate=0.05, max_depth=6,
                    random_state=2024, verbosity=0,
                )
                for h in range(horizon):
                    model.fit(x_train, y_n[:, h])
                    pred[:, h, n] = model.predict(x_test)
        results.append(_evaluate(pred, bundle, origins, trigger_by_origin, name, output_dir))

    # ---- 3. ARIMA(2,1,2) 滚动前向 ----
    # 参数估计口径：每个节点仅在训练尾段拟合一次（近似假设 15 分钟粒度下
    # 近段序列平稳），测试期对每个预测起点用最近 96 步 apply 更新状态但不重估参数。
    print("=== ARIMA(2,1,2) ===", flush=True)
    from statsmodels.tsa.arima.model import ARIMA

    train_series = bundle.features[: train_end + 1, :, 0]  # [T, N] 负荷特征
    pred = np.zeros((len(origins), horizon, num_nodes), dtype=np.float32)
    for n in range(num_nodes):
        series = train_series[:, n]
        tail = series[-ARIMA_FIT_LENGTH:]
        model = ARIMA(tail, order=ARIMA_ORDER).fit(method_kwargs={"maxiter": 50})
        for i, origin in enumerate(origins):
            # 以最近 96 步作为已知末端，apply 后前向 4 步
            hist = features_all[origin - 96: origin, n, 0]
            fitted = model.apply(hist)
            fc = fitted.forecast(horizon)
            pred[i, :, n] = np.asarray(fc, dtype=np.float32)
        print(f"  节点 {bundle.node_ids[n]} ARIMA 完成", flush=True)
    results.append(_evaluate(pred, bundle, origins, trigger_by_origin, "ARIMA", output_dir))
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
