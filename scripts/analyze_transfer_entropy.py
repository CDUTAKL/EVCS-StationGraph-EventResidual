"""传递熵有向信息流快速验证（D6-1）：节点间有向信息的探索性证据。

目的（决策工具，非正式实验）：
  判断"以方向性信息补充统计图"方向（第 5 章 5.1 候选主线）是否值得投入
  PCMCI+ 精细发现——如果节点间存在三类统计图（load/event/pattern）
  未覆盖的候选有向信息流，说明方向性分析能提供新信息；否则及时止损，
  主线转向预训练/共形预测。

方法：
  1. 仅使用训练期负荷序列（与 build_relation_set 口径一致，无泄漏）
  2. 分位分箱（8 bins，处理 78% 零值堆积与长尾；逐节点分位点，
     因为节点负荷量级差异超过 2 倍）
  3. lag∈{1,2,4} 逐对计算传递熵 TE(X→Y)，每对取最大 TE
  4. 循环平移置换检验（100 次；保留序列周期结构，只破坏 X-Y 相位配对）得 p 值
  5. p<0.05 记为 TE 候选有向边（探索性，未做多重比较校正——审查 H-06；
     字段名 significant_edges 为历史遗留，语义=候选边），
     与三类统计图边集（top_k=3）做重叠度分析

判定逻辑：
  候选边数量可观（≥10 条）且被三类统计图覆盖比例低（Jaccard < 0.5）
  → TE 候选边提供统计图未覆盖的方向信息，值得投入 PCMCI+ 正式因果发现
  否则 → 方向性分析降级为分析素材，主线转向预训练/共形预测

用法：
  .venv/bin/python scripts/analyze_transfer_entropy.py \
    [--dataset data/processed/SG-DATA-005-primary-tensor.npz] \
    [--output-dir outputs/analysis/transfer_entropy] \
    [--bins 8] [--n-perm 100] [--top-k 3]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

import numpy as np

from evcs_station_graph.data import load_tensor_bundle
from evcs_station_graph.graphs import build_relation_set
from evcs_station_graph.reproducibility import write_json

# 分箱数：8 bins 在 118K 样本下每箱约 1 万样本，联合计数（8^3=512 项）统计稳定；
# 更细的 16 bins 会加剧稀疏（部分箱组合为 0），对 TE 估计反而引入偏差。
DEFAULT_BINS = 8
# 显著性阈值：快速验证采用单检验 0.05，不做多重比较校正——
# 本脚本是决策工具，宁可多保留候选边供 PCMCI+ 复核，也不误杀真实信息流。
P_VALUE_THRESHOLD = 0.05
# 快速验证的因果边数量门槛：10 节点最多 90 条有向边，若显著边少于 10 条，
# 说明节点间有向交互稀疏，因果图信息量不足。
MIN_SIGNIFICANT_EDGES = 10
# 判定"TE 候选边提供新方向信息"的 Jaccard 上限：与统计图重叠度低于 0.5 视为提供新信息
JACCARD_THRESHOLD = 0.5


def _quantile_bins(series: np.ndarray, n_bins: int) -> np.ndarray:
    """按分位数将连续序列离散为 [0, n_bins) 的箱索引。

    使用分位数而非等宽分箱的理由：负荷序列 78% 为 0、非零值呈长尾分布，
    等宽分箱会把绝大多数样本挤进第一个箱。分位数分箱保证每箱样本量均衡。
    """
    edges = np.quantile(
        series, np.linspace(0.0, 1.0, n_bins + 1)[1:-1]
    )
    # 去重后若分位点不足 n_bins-1 个（如全零序列），用 digitize 保证结果合法
    edges = np.unique(edges)
    return np.digitize(series, edges)


def _transfer_entropy(x: np.ndarray, y: np.ndarray, yp: np.ndarray, n_bins: int) -> float:
    """向量化计算 lag 传递熵 TE(X→Y) = H(Y'|Y) - H(Y'|Y,X)。

    x：源序列的过去值箱索引（形状 [T']）
    y：目标序列的过去值箱索引（形状 [T']）
    yp：目标序列的当前值箱索引（形状 [T']）

    TE = Σ p(yp,y,x) log[ p(yp,y,x)·p(y) / (p(y,x)·p(yp,y)) ]
    联合计数用 bincount 一次完成，避免三层嵌套循环。
    """
    joint = np.bincount(
        yp * n_bins * n_bins + y * n_bins + x, minlength=n_bins ** 3
    ).astype(np.float64)
    p = joint.reshape(n_bins, n_bins, n_bins) / joint.sum()  # [yp, y, x]
    p_yx = p.sum(axis=0)     # [y, x]
    p_ypy = p.sum(axis=2)    # [yp, y]
    p_y = p_ypy.sum(axis=0)  # [y]
    with np.errstate(divide="ignore", invalid="ignore"):
        log_term = (
            np.log(p) + np.log(p_y)[None, :, None]
            - np.log(p_yx)[None, :, :] - np.log(p_ypy)[:, :, None]
        )
    # p>0 处概率质量为正 ⇒ 对应边缘 p_yx、p_ypy 也必然为正，log_term 有限
    nonzero = p > 0
    te = float(np.sum(p[nonzero] * log_term[nonzero]))
    return max(te, 0.0)


def _permuted_p_value(
    x: np.ndarray, y: np.ndarray, yp: np.ndarray, n_bins: int,
    n_perm: int, rng: np.random.Generator, perm_mode: str = "circular",
) -> float:
    """置换检验：破坏源序列与目标的配对后重算 TE，得到 p 值。

    必须使用循环平移（circular）而非完全打乱（shuffle）：
    负荷序列具有强日内/周周期，shuffle 会破坏自相关结构，
    使置换 TE 系统性偏小 → 假阳性（所有边都"显著"）。
    循环平移保留序列内部周期结构，只破坏 X 与 Y 的相位配对，
    检验的是"X 的相位信息是否定向预测 Y"。

    p = (1 + #{TE_perm ≥ TE_obs}) / (1 + n_perm)，
    加 1 保证 p 值最小为 1/(1+n_perm)，避免零 p 值。
    平移偏移量下限取 96（一个完整日周期），避免小偏移与观测
    高度重叠产生保守偏差。
    """
    observed = _transfer_entropy(x, y, yp, n_bins)
    count = 0
    length = len(x)
    min_offset = min(96, max(length - 1, 1))
    for _ in range(n_perm):
        if perm_mode == "shuffle":
            permuted = x[rng.permutation(length)]
        else:
            offset = int(rng.integers(min_offset, length))
            permuted = np.roll(x, offset)
        if _transfer_entropy(permuted, y, yp, n_bins) >= observed:
            count += 1
    return (count + 1) / (n_perm + 1)


def _lag_te_pairs(
    source: np.ndarray, target: np.ndarray, lag: int,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """构造 lag 滞后三元组 (X[t-lag], Y[t-lag], Y[t])。"""
    return source[:-lag], target[:-lag], target[lag:]


def _significant_edges(
    te_matrix: np.ndarray, p_matrix: np.ndarray, lag_matrix: np.ndarray,
    node_ids: Sequence[str],
) -> List[Dict[str, Any]]:
    """汇总 p<0.05 的 TE 候选有向边（探索性，未校正；字段名 historical 保留）。"""
    edges: List[Dict[str, Any]] = []
    n = len(node_ids)
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            if p_matrix[i, j] < P_VALUE_THRESHOLD:
                edges.append({
                    "source": str(node_ids[i]),
                    "target": str(node_ids[j]),
                    "te": float(te_matrix[i, j]),
                    "p_value": float(p_matrix[i, j]),
                    "lag": int(lag_matrix[i, j]),
                })
    edges.sort(key=lambda e: e["p_value"])
    return edges


def _edge_set(adjacency: np.ndarray, node_ids: Sequence[str]) -> set:
    """提取邻接矩阵的非对角边集（节点对无序）。"""
    pairs: set = set()
    n = len(node_ids)
    for i in range(n):
        for j in range(i + 1, n):
            if adjacency[i, j] > 0 and adjacency[j, i] > 0:
                pairs.add(frozenset((str(node_ids[i]), str(node_ids[j]))))
    return pairs


def _asymmetry_analysis(
    te_matrix: np.ndarray, p_matrix: np.ndarray, node_ids: Sequence[str],
) -> Dict[str, Any]:
    """方向不对称性分析：TE(i→j) vs TE(j→i)。

    判别逻辑：若节点对的信息耦合完全来自共享外部驱动（站级活动、日周期），
    TE 矩阵近似对称（两个方向信息量相同）；若存在定向信息流
    （一个节点的活动模式预测另一个节点），两个方向差异显著。

    返回按不对称度排序的节点对列表与总体不对称率。
    """
    n = len(node_ids)
    pairs: List[Dict[str, Any]] = []
    for i in range(n):
        for j in range(i + 1, n):
            forward, backward = te_matrix[i, j], te_matrix[j, i]
            denominator = max(forward + backward, 1e-12)
            asymmetry = abs(forward - backward) / denominator
            pairs.append({
                "node_i": str(node_ids[i]),
                "node_j": str(node_ids[j]),
                "te_i_to_j": round(float(forward), 5),
                "te_j_to_i": round(float(backward), 5),
                "asymmetry": round(float(asymmetry), 3),
                "dominant_direction": (
                    "i→j" if forward > backward else ("j→i" if backward > forward else "对称")
                ),
            })
    pairs.sort(key=lambda p: p["asymmetry"], reverse=True)
    asymmetric = [p for p in pairs if p["asymmetry"] > 0.3]
    return {
        "top_asymmetric_pairs": pairs[:10],
        "asymmetric_pair_count": len(asymmetric),
        "total_pairs": len(pairs),
        "asymmetry_rate": round(len(asymmetric) / len(pairs), 3),
    }


def _overlap_analysis(
    edges: List[Dict[str, Any]],
    relation_set: Any,
    node_ids: Sequence[str],
) -> Dict[str, Any]:
    """显著因果边与三类统计图边集的重叠度分析。

    Jaccard = |因果边 ∩ 统计边| / |因果边 ∪ 统计边|。
    "统计图未覆盖候选" = TE 候选边（未校正）但三类统计图（top_k=3）均未覆盖的节点对。
    """
    causal_pairs = {frozenset((e["source"], e["target"])) for e in edges}
    stats = {
        name: _edge_set(getattr(relation_set, name), node_ids)
        for name in ("load", "event", "pattern")
    }
    any_stat = set().union(*stats.values())
    overlap = {
        name: (len(causal_pairs & pairs) / len(causal_pairs | pairs)
               if causal_pairs | pairs else 0.0)
        for name, pairs in stats.items()
    }
    covered = len(causal_pairs & any_stat)
    exclusive = len(causal_pairs - any_stat)
    return {
        "total_significant_edges": len(edges),
        "undirected_pairs": len(causal_pairs),
        "jaccard_load": round(overlap["load"], 4),
        "jaccard_event": round(overlap["event"], 4),
        "jaccard_pattern": round(overlap["pattern"], 4),
        "covered_by_any_statistical_graph": covered,
        "exclusive_to_causal": exclusive,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="D6-1 传递熵有向信息流快速验证（探索性）")
    parser.add_argument("--dataset", default="data/processed/SG-DATA-005-primary-tensor.npz")
    parser.add_argument("--output-dir", default="outputs/analysis/transfer_entropy")
    parser.add_argument("--bins", type=int, default=DEFAULT_BINS)
    parser.add_argument("--n-perm", type=int, default=100)
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--perm-mode", choices=["circular", "shuffle"], default="circular",
                        help="置换方式：circular=循环平移（默认，保留周期结构）；"
                             "shuffle=完全打乱（仅诊断用）")
    parser.add_argument("--seed", type=int, default=2024)
    args = parser.parse_args()

    bundle = load_tensor_bundle(args.dataset)
    node_ids = bundle.node_ids.tolist()
    n_nodes = len(node_ids)
    # 仅使用训练期数据（与关系图构建口径一致，无验证/测试泄漏）
    train_end = int(bundle.split_origins["train"][-1])
    targets = bundle.targets[: train_end + 1]
    print(f"训练期样本：{len(targets)} 步 × {n_nodes} 节点", flush=True)

    # 逐节点分位分箱（per-node 分位点，节点量级差异大）
    binned = np.stack(
        [_quantile_bins(targets[:, i], args.bins) for i in range(n_nodes)], axis=1
    )

    lags = [1, 2, 4]
    rng = np.random.default_rng(args.seed)
    te_matrix = np.zeros((n_nodes, n_nodes), dtype=np.float64)
    p_matrix = np.ones((n_nodes, n_nodes), dtype=np.float64)
    lag_matrix = np.zeros((n_nodes, n_nodes), dtype=np.int64)

    started_ns = np.datetime64("now")
    total_pairs = n_nodes * (n_nodes - 1)
    done = 0
    for i in range(n_nodes):
        for j in range(n_nodes):
            if i == j:
                continue
            best_te, best_p, best_lag = 0.0, 1.0, 1
            for lag in lags:
                x, y, yp = _lag_te_pairs(binned[:, i], binned[:, j], lag)
                te = _transfer_entropy(x, y, yp, args.bins)
                p = _permuted_p_value(
                    x, y, yp, args.bins, args.n_perm, rng, args.perm_mode)
                if p < best_p:
                    best_te, best_p, best_lag = te, p, lag
            te_matrix[i, j] = best_te
            p_matrix[i, j] = best_p
            lag_matrix[i, j] = best_lag
            done += 1
            if done % 10 == 0:
                print(f"  进度 {done}/{total_pairs} 对", flush=True)

    edges = _significant_edges(te_matrix, p_matrix, lag_matrix, node_ids)
    print(f"\nTE 候选有向边（p<{P_VALUE_THRESHOLD}，探索性）：{len(edges)} 条", flush=True)
    for e in edges[:15]:
        print(f"  {e['source']} → {e['target']}  TE={e['te']:.4f}  "
              f"p={e['p_value']:.3f}  lag={e['lag']}", flush=True)

    # 与现有三类统计图的重叠度（top-k 稀疏化后的边集）
    graph_cfg = {}
    adjacencies = build_relation_set(
        bundle.features[: train_end + 1], targets,
        bundle.feature_names, top_k=args.top_k,
    )
    overlap = _overlap_analysis(edges, adjacencies, node_ids)
    asymmetry = _asymmetry_analysis(te_matrix, p_matrix, node_ids)

    print(f"\n方向不对称性（信息流方向证据）：")
    print(f"  不对称节点对（>0.3）：{asymmetry['asymmetric_pair_count']}/"
          f"{asymmetry['total_pairs']}（比例 {asymmetry['asymmetry_rate']:.1%}）")
    for p in asymmetry["top_asymmetric_pairs"][:6]:
        print(f"  {p['node_i']}↔{p['node_j']}: {p['te_i_to_j']:.4f} vs "
              f"{p['te_j_to_i']:.4f} 不对称度={p['asymmetry']:.2f} "
              f"主导方向={p['dominant_direction']}")

    verdict = (
        "通过：候选有向边提供统计图未覆盖的方向信息，值得投入 PCMCI+ 正式检验"
        if overlap["total_significant_edges"] >= MIN_SIGNIFICANT_EDGES
        and overlap["exclusive_to_causal"] > 0
        and overlap["jaccard_load"] < JACCARD_THRESHOLD
        else "未通过：候选边稀疏或与统计图高度重叠，方向分析降级为素材"
    )
    overlap["verdict"] = verdict
    print(f"\n重叠度：load Jaccard={overlap['jaccard_load']:.3f} "
          f"event={overlap['jaccard_event']:.3f} pattern={overlap['jaccard_pattern']:.3f}")
    print(f"被统计图覆盖：{overlap['covered_by_any_statistical_graph']} 对；"
          f"统计图未覆盖候选：{overlap['exclusive_to_causal']} 对")
    print(f"判定：{verdict}")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json({
        "analysis": "D6-1 transfer entropy quick check",
        "lags": lags,
        "bins": args.bins,
        "n_perm": args.n_perm,
        "seed": args.seed,
        "te_matrix": te_matrix.tolist(),
        "p_matrix": p_matrix.tolist(),
        "lag_matrix": lag_matrix.tolist(),
        "significant_edges": edges,
        "overlap": overlap,
        "asymmetry": asymmetry,
        "elapsed_seconds": float((np.datetime64("now") - started_ns) / np.timedelta64(1, "s")),
    }, output_dir / "transfer_entropy_summary.json")
    print(f"\n结果已写入：{output_dir / 'transfer_entropy_summary.json'}", flush=True)


if __name__ == "__main__":
    main()
