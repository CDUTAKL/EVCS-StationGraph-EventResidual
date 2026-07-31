"""GBM 单模型 worker（macOS 段错误规避）：每个 (model, node, horizon) 独立进程。

背景：LightGBM/XGBoost 在同一进程连续训练多个模型时，在 macOS 上
随机触发段错误（exit 139，C 层崩溃无 traceback，可能与 OpenMP 线程池
与 40 个 Booster 的创建/销毁累积有关）。独立进程完全隔离，逐模型可靠。

用法：
  .venv/bin/python scripts/run_gbm_worker.py <LightGBM|XGBoost> <node_idx> <horizon> <outdir>
输出：<outdir>/<model>_pred_<node>_<horizon>.npz（仅预测列，[S]）
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np

from evcs_station_graph.data import NodeWindowDataset, WindowSpec, load_tensor_bundle

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_traditional_baselines import _build_feature_matrix  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("model", choices=["LightGBM", "XGBoost"])
    parser.add_argument("node", type=int)
    parser.add_argument("horizon", type=int)
    parser.add_argument("outdir")
    args = parser.parse_args()

    dataset = "data/processed/SG-DATA-005-primary-tensor.npz"
    bundle = load_tensor_bundle(dataset)
    spec = WindowSpec(history_steps=96, forecast_steps=4)
    ds_test = NodeWindowDataset(bundle, "test", spec)
    origins = ds_test.origins
    features_all = bundle.features
    train_origins = bundle.split_origins["train"][96:]

    # float32 减半内存（float64 大数据集曾触发 malloc 失败段错误）
    x_train = np.ascontiguousarray(
        _build_feature_matrix(features_all, train_origins, bundle.node_ids),
        dtype=np.float32,
    )
    y_train = bundle.targets[train_origins[:, None] + 1 + np.arange(4)[None, :]]
    x_test = np.ascontiguousarray(
        _build_feature_matrix(features_all, origins, bundle.node_ids),
        dtype=np.float32,
    )
    y_h = np.ascontiguousarray(y_train[:, args.horizon, args.node])

    if args.model == "LightGBM":
        import lightgbm as lgb
        # n_jobs=1：LightGBM 多线程（OpenMP）在特定数据上随机段错误
        #（已验证 n_jobs=4 时 n=8 h=0 必崩、n_jobs=1 稳定），单线程规避
        model = lgb.LGBMRegressor(
            n_estimators=300, learning_rate=0.05, max_depth=6,
            num_leaves=31, random_state=2024, verbose=-1, n_jobs=1,
        )
    else:
        import xgboost as xgb
        model = xgb.XGBRegressor(
            n_estimators=300, learning_rate=0.05, max_depth=6,
            random_state=2024, verbosity=0, n_jobs=1,
        )
    model.fit(x_train, y_h)
    pred = model.predict(x_test).astype(np.float32)

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    out_path = outdir / f"{args.model}_pred_{args.node}_{args.horizon}.npz"
    np.savez_compressed(out_path, pred=pred)
    print(f"{args.model} node={args.node} h={args.horizon} OK", flush=True)


if __name__ == "__main__":
    main()
