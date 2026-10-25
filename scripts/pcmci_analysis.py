"""SG-EXP-017：PCMCI+ 因果发现（探索性，5.2 章决策依据）。

以训练段 10 节点原始负荷序列（83,198 个观测点；窗口化预测口径为 83,103 个预测起点）运行 PCMCI+
（tigramite，parcorr 条件独立性检验），输出显著滞后依赖边；
与传递熵候选边（transfer_entropy_summary.json）对比，统计 PCMCI+
确认的 TE 候选占比，为 5.2 章"方向性探索 vs 正式验证"提供决策证据。

口径说明（探索性定位）：
- 仅训练集（与 TE 一致），PCMCI+ 为事后分析、模型无关；
- 输出为条件独立性意义下的滞后依赖证据，不解释为物理因果；
- 与 TE 同为探索性证据，未做多重比较校正的正式结论另议。

用法（本地 CPU，与服务器训练并行）：
  .venv/bin/python scripts/pcmci_analysis.py

输出：outputs/analysis/pcmci/pcmci_summary.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, "src")
from evcs_station_graph.data import load_tensor_bundle  # noqa: E402

try:
    from tigramite import data_processing as pp
    from tigramite.pcmci import PCMCI
    from tigramite.independence_tests.parcorr import ParCorr  # 5.2.x 位于子模块
except ImportError:  # 无 tigramite 环境显式失败（不静默跳过）
    raise ImportError("需要 tigramite：.venv/bin/pip install tigramite")

OUT = Path("outputs/analysis/pcmci")
MAX_LAG = 4  # 与 TE 分析最大滞后一致（lags=[1,2,4] 的上界）


def main() -> None:
    """运行 PCMCI+ 并输出显著边与 TE 候选对比。"""
    bundle = load_tensor_bundle("data/processed/SG-DATA-005-primary-tensor.npz")
    # 原始时间点口径：切至训练集最后一个预测起点，含起点对应的观测行。
    # 因输入历史窗口先占用若干时间点，预测起点数会少于原始观测行数。
    train_end = int(bundle.split_origins["train"][-1])
    targets = bundle.targets[: train_end + 1]  # [T, N]，原始物理量纲
    n_raw_observations = int(targets.shape[0])
    n_forecast_origins = int(len(bundle.split_origins["train"]))
    node_ids = list(bundle.node_ids)

    frame = pp.DataFrame(targets, var_names=node_ids)
    parcorr = ParCorr(significance="analytic")
    pcmci = PCMCI(dataframe=frame, cond_ind_test=parcorr, verbosity=0)
    results = pcmci.run_pcmciplus(tau_min=1, tau_max=MAX_LAG, pc_alpha=0.05)

    # 提取显著边：results['val_matrix'][i, j, tau] 为 i_{t-tau} → j_t 的系数
    val = results["val_matrix"]
    pval = results["p_matrix"]
    n = len(node_ids)
    edges = []
    for j in range(n):
        for i in range(n):
            for tau in range(1, MAX_LAG + 1):
                if pval[i, j, tau] < 0.05 and not np.isnan(val[i, j, tau]):
                    edges.append({
                        "source": node_ids[i], "target": node_ids[j],
                        "lag": int(tau), "coef": float(val[i, j, tau]),
                        "p_value": float(pval[i, j, tau]),
                    })
    edges.sort(key=lambda e: abs(e["coef"]), reverse=True)

    # 与 TE 候选对比（TE significant_edges 为 {source,target,lag,te} 列表）
    te = json.load(open("outputs/analysis/transfer_entropy/transfer_entropy_summary.json"))
    pcmci_set = {(e["source"], e["target"]) for e in edges}
    te_set = {(e["source"], e["target"]) for e in te.get("significant_edges", [])}
    confirmed = sorted(te_set & pcmci_set)
    te_only = sorted(te_set - pcmci_set)
    pcmci_only = sorted(pcmci_set - te_set)

    summary = {
        "analysis": (
            "PCMCI+ 条件滞后依赖探索（训练段 "
            f"{n_raw_observations:,} 个原始观测点；对应 {n_forecast_origins:,} 个预测起点，"
            "ParCorr，lag 1-4，α=0.05）"
        ),
        "n_train_raw_observations": n_raw_observations,
        "n_train_forecast_origins": n_forecast_origins,
        "max_lag": MAX_LAG,
        "n_edges_pcmci": len(edges),
        "n_te_candidates": len(te_set),
        "n_te_confirmed_by_pcmci": len(confirmed),
        "confirmation_rate": round(len(confirmed) / max(len(te_set), 1), 3),
        "confirmed_edges": confirmed,
        "te_only_edges": te_only,
        "pcmci_only_edges": pcmci_only,
        "edges": edges,
        "verdict": (
            "TE 候选被 PCMCI+ 确认比例（探索性证据）："
            f"{len(confirmed)}/{len(te_set)} = {len(confirmed)/max(len(te_set),1):.1%}"
        ),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "pcmci_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"✅ 已写入 {OUT / 'pcmci_summary.json'}")
    print(f"  训练原始观测 {n_raw_observations:,} 个 | 预测起点 {n_forecast_origins:,} 个")
    print(f"  PCMCI+ 显著边 {len(edges)} 条 | TE 候选 {len(te_set)} 条 | "
          f"确认 {len(confirmed)} 条（{summary['confirmation_rate']:.1%}）")
    return None


if __name__ == "__main__":
    main()
