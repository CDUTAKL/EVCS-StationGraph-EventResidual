"""合并 GBM worker 输出并评价（与 run_traditional_baselines.py 口径一致）。

读 run_gbm_loop.sh 产生的 80 个单列 npz，组装 [S,H,N] 预测数组，
调用 run_traditional_baselines._evaluate 输出分层指标并落盘 predictions_*.npz。

用法：.venv/bin/python scripts/run_gbm_merge.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

from evcs_station_graph.data import NodeWindowDataset, WindowSpec, load_tensor_bundle

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_traditional_baselines import _evaluate  # noqa: E402

OUT = Path("outputs/analysis/traditional_baselines")


def main() -> None:
    bundle = load_tensor_bundle("data/processed/SG-DATA-005-primary-tensor.npz")
    spec = WindowSpec(history_steps=96, forecast_steps=4)
    ds_test = NodeWindowDataset(bundle, "test", spec)
    origins = ds_test.origins
    num_nodes = len(bundle.node_ids)
    horizon = 4
    results = []

    for model in ("LightGBM", "XGBoost"):
        pred = np.zeros((len(origins), horizon, num_nodes), dtype=np.float32)
        for n in range(num_nodes):
            for h in range(horizon):
                path = OUT / f"{model}_pred_{n}_{h}.npz"
                if not path.exists():
                    raise RuntimeError(f"缺少 {path}，请先跑 run_gbm_loop.sh")
                pred[:, h, n] = np.load(path)["pred"]
        results.append(_evaluate(pred, bundle, origins, model, OUT))

    # 汇总（追加到 traditional_baselines_summary.json，保留已有模型如 ARIMA）
    summary_path = OUT / "traditional_baselines_summary.json"
    if summary_path.exists():
        import json
        existing = json.loads(summary_path.read_text())
    else:
        existing = {"analysis": "traditional baselines (chapter 3 main table)"}
    existing_models = {m["model"]: m for m in existing.get("models", [])}
    for r in results:
        existing_models[r["model"]] = r
    existing["models"] = list(existing_models.values())
    existing["num_origins"] = int(len(origins))
    summary_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2))
    print(f"汇总已更新：{summary_path}（{list(existing_models)}）")


if __name__ == "__main__":
    main()
