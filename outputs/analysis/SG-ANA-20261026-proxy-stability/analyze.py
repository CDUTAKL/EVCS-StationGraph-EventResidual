#!/usr/bin/env python3
"""Proxy-label sensitivity and model-ranking stability analysis.

Reads existing frozen ACN thesis predictions. Writes to the directory
containing this script. In this repository evidence copy, outputs stay within
the registered analysis folder. No training, no network, no raw-session data.
"""
from __future__ import annotations

import json
import os
import tarfile
import tempfile
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

PACKAGE_ROOT = Path(__file__).resolve().parent
CONFIG_PATH = PACKAGE_ROOT / "config.json"
CONFIG = json.loads(CONFIG_PATH.read_text(encoding="utf-8")) if CONFIG_PATH.exists() else {}


def _project_root() -> Path:
    env = os.environ.get("EVCS_PROJECT_ROOT")
    raw = env if env else CONFIG.get("project_root", ".")
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = (PACKAGE_ROOT / path).resolve()
    return path


ROOT = _project_root()
OUT = PACKAGE_ROOT
LOCAL = OUT / "inputs"


def _pick(local: Path, external: Path) -> Path:
    """Prefer the self-contained copy; fall back to the project for provenance."""
    return local if local.exists() else external


EXP19 = _pick(LOCAL / "exp019",
              ROOT / "outputs/recovered/SG-EXP-019/unpacked/results/formal")
EXP27 = _pick(LOCAL / "exp027",
              ROOT / "outputs/experiments/SG-EXP-027/recovered/formal")
UNI_DS = _pick(LOCAL / "datasets/uniform.npz",
               ROOT / "outputs/visibility/SG-DATA-006-eventtime-v1/dataset.npz")
ALT_DS = _pick(LOCAL / "datasets/alternative.npz",
               ROOT / "outputs/experiments/SG-EXP-032/frozen-contract/dataset.npz")

SEEDS = (2024, 2025, 2026)
CONFIGS19 = (
    "agcrn_full", "mrg_equal_beta", "mrg_full", "mrg_no_skip",
    "mrg_no_refine", "mrg_pattern", "mrg_fixed_gate", "mrg_load",
    "mrg_event", "mrg_self_loop", "tcn", "tcn_wide",
)
CONFIGS27 = ("mrg_full", "mrg_shared_gate")
CONFIGS32 = ("mrg_full", "tcn_wide")


def _resolve_exp32() -> Path:
    """Prefer local inputs; if absent, extract the six members from the project tar."""
    local = LOCAL / "exp032"
    if local.exists():
        return local
    tar_path = ROOT / "outputs/experiments/SG-EXP-032/recovered/SG-EXP-032-results.tar.gz"
    if not tar_path.exists():
        return local
    tmp = Path(tempfile.mkdtemp(prefix="acn_exp032_"))
    with tarfile.open(tar_path, "r:gz") as tf:
        for config in CONFIGS32:
            for seed in SEEDS:
                member = f"closeout/results/formal/{config}/seed-{seed}/predictions_test.npz"
                dst = tmp / config / f"seed-{seed}" / "predictions_test.npz"
                dst.parent.mkdir(parents=True, exist_ok=True)
                f = tf.extractfile(member)
                if f is None:
                    raise KeyError(member)
                dst.write_bytes(f.read())
    return tmp


EXP32 = _resolve_exp32()

# These NPZ files are locally generated frozen arrays from this project. Their
# contents are numeric arrays and fixed-width Unicode node IDs, so pickle is not
# needed; keep allow_pickle=False to avoid executing any object payload.
uni = np.load(UNI_DS, allow_pickle=False)
alt = np.load(ALT_DS, allow_pickle=False)
assert np.array_equal(uni["timestamps_ns"], alt["timestamps_ns"])
TSMAP = {int(t): i for i, t in enumerate(uni["timestamps_ns"])}
NODE_IDS = [str(n) for n in uni["node_ids"]]
assert [str(n) for n in alt["node_ids"]] == NODE_IDS


def targets_for(pred):
    pnodes = [str(n) for n in pred["node_ids"]]
    if pnodes != NODE_IDS:
        order = [NODE_IDS.index(n) for n in pnodes]
    else:
        order = list(range(len(NODE_IDS)))
    idx = np.empty(pred["target_timestamps_ns"].shape, dtype=np.int64)
    for h in range(4):
        idx[:, h] = [TSMAP[int(t)] for t in pred["target_timestamps_ns"][:, h]]
    return uni["targets"][idx][:, :, order], alt["targets"][idx][:, :, order]


def load_pred(path: Path):
    d = np.load(path, allow_pickle=False)
    u, a = targets_for(d)
    max_u = float(np.max(np.abs(u - d["y_true"])))
    max_a = float(np.max(np.abs(a - d["y_true"])))
    protocol = "uniform" if max_u <= max_a else "alternative"
    if min(max_u, max_a) > 1e-9:
        raise ValueError(f"target alignment failed: {path} {max_u} {max_a}")
    return d, u, a, protocol


def metrics(y_pred, y_true, event_mask, uniform_nonzero):
    err = y_pred - y_true
    ae = np.abs(err)
    out = {}
    out["n_keys"] = int(ae.size)
    out["global_mae"] = float(ae.mean())
    out["global_rmse"] = float(np.sqrt(np.mean(err ** 2)))
    denom = float(np.abs(y_true).sum())
    out["global_wape"] = float(ae.sum() / denom) if denom > 0 else None
    zero = y_true == 0
    nz = y_true > 0
    out["zero_n"] = int(zero.sum())
    out["nonzero_n"] = int(nz.sum())
    out["zero_rate"] = float(zero.mean())
    out["zero_mae"] = float(ae[zero].mean()) if zero.any() else None
    out["nonzero_mae"] = float(ae[nz].mean()) if nz.any() else None
    out["nonzero_uniform_keys_mae"] = (
        float(ae[uniform_nonzero].mean()) if uniform_nonzero.any() else None
    )
    out["event_n"] = int(event_mask.sum())
    out["event_mae"] = float(ae[event_mask].mean()) if event_mask.any() else None
    out["stable_mae"] = float(ae[~event_mask].mean()) if (~event_mask).any() else None
    return out


def aggregate(rows):
    keys = [
        k for k, v in rows[0].items()
        if isinstance(v, (int, float)) and v is not None
    ]
    out = {}
    for k in keys:
        vals = np.array([r[k] for r in rows], dtype=float)
        out[k] = {
            "mean": float(vals.mean()),
            "sd": float(vals.std(ddof=1)) if len(vals) > 1 else 0.0,
            "values": [float(x) for x in vals],
        }
    return out


def evaluate(base: Path, configs, label: str):
    result = {}
    for c in configs:
        rows = []
        protocols = set()
        for s in SEEDS:
            path = base / c / f"seed-{s}" / "predictions_test.npz"
            d, u, a, protocol = load_pred(path)
            protocols.add(protocol)
            tgt = u if label == "uniform" else a
            rows.append(metrics(d["y_pred"], tgt, d["target_event"], u > 0))
        result[c] = {"aggregate": aggregate(rows), "protocols": sorted(protocols)}
    return result


def rankdata(x):
    x = np.asarray(x, float)
    order = np.argsort(x, kind="mergesort")
    ranks = np.empty(len(x), float)
    i = 0
    while i < len(x):
        j = i
        while j + 1 < len(x) and x[order[j + 1]] == x[order[i]]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2.0 + 1.0
        i = j + 1
    return ranks


def ranking(metrics_by_config, key):
    vals = {
        c: metrics_by_config[c]["aggregate"][key]["mean"]
        for c in metrics_by_config
    }
    order = sorted(vals, key=lambda c: vals[c])
    ranks = {c: i + 1 for i, c in enumerate(order)}
    return vals, order, ranks


def compare_cell(base: Path, config: str, label: str):
    rows = []
    for s in SEEDS:
        path = base / config / f"seed-{s}" / "predictions_test.npz"
        d, u, a, _ = load_pred(path)
        tgt = u if label == "uniform" else a
        rows.append(metrics(d["y_pred"], tgt, d["target_event"], u > 0))
    return aggregate(rows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    print("evaluating SG-EXP-019 ...", flush=True)
    res19_u = evaluate(EXP19, CONFIGS19, "uniform")
    res19_a = evaluate(EXP19, CONFIGS19, "alternative")

    print("evaluating SG-EXP-027 ...", flush=True)
    res27_u = evaluate(EXP27, CONFIGS27, "uniform")
    res27_a = evaluate(EXP27, CONFIGS27, "alternative")

    print("evaluating SG-EXP-032 ...", flush=True)
    res32_u = evaluate(EXP32, CONFIGS32, "uniform")
    res32_a = evaluate(EXP32, CONFIGS32, "alternative")

    # Ranking stability across the 12 configurations trained on the uniform label.
    vals_u, order_u, ranks_u = ranking(res19_u, "global_mae")
    vals_a, order_a, ranks_a = ranking(res19_a, "global_mae")
    common = list(CONFIGS19)
    rho = float(np.corrcoef(
        rankdata([ranks_u[c] for c in common]),
        rankdata([ranks_a[c] for c in common]),
    )[0, 1])
    rank_rows = []
    for c in common:
        rank_rows.append({
            "config": c,
            "uniform_mae": vals_u[c],
            "alternative_mae": vals_a[c],
            "uniform_rank": ranks_u[c],
            "alternative_rank": ranks_a[c],
            "rank_delta": ranks_a[c] - ranks_u[c],
            "mae_delta": vals_a[c] - vals_u[c],
        })
    rank_rows.sort(key=lambda r: r["uniform_rank"])
    top1 = {"uniform": order_u[0], "alternative": order_a[0]}
    top3_overlap = len(set(order_u[:3]) & set(order_a[:3]))
    max_rank_change = max(abs(r["rank_delta"]) for r in rank_rows)

    # Same ranking check on a fixed-composition subgroup: keys that are nonzero
    # under the uniform label. This separates error change from composition change.
    vals_u_nz, order_u_nz, ranks_u_nz = ranking(res19_u, "nonzero_uniform_keys_mae")
    vals_a_nz, order_a_nz, ranks_a_nz = ranking(res19_a, "nonzero_uniform_keys_mae")
    rho_nz = float(np.corrcoef(
        rankdata([ranks_u_nz[c] for c in common]),
        rankdata([ranks_a_nz[c] for c in common]),
    )[0, 1])

    # Rank stability under several evaluation definitions. Global and stable
    # windows are dominated by zeros; active/event subgroups can reorder models.
    metrics_rank = {}
    for key in ("global_mae", "zero_mae", "nonzero_mae",
                "nonzero_uniform_keys_mae", "event_mae", "stable_mae"):
        _, order_u_k, ranks_u_k = ranking(res19_u, key)
        _, order_a_k, ranks_a_k = ranking(res19_a, key)
        metrics_rank[key] = {
            # Spearman between rankings of the three-seed mean MAE: average MAE
            # across seeds first, then rank the 12 configurations.
            "rho_of_seed_mean_mae_ranks": float(np.corrcoef(
                rankdata([ranks_u_k[c] for c in common]),
                rankdata([ranks_a_k[c] for c in common]),
            )[0, 1]),
            "uniform_order": order_u_k,
            "alternative_order": order_a_k,
        }

    # Seed-level rank correlations: the three-seed average can hide instability.
    seed_rank = {}
    for i, seed in enumerate(SEEDS):
        seed_rank[str(seed)] = {}
        for key in ("global_mae", "zero_mae", "nonzero_mae",
                    "nonzero_uniform_keys_mae", "event_mae", "stable_mae"):
            u_vals = [res19_u[c]["aggregate"][key]["values"][i] for c in common]
            a_vals = [res19_a[c]["aggregate"][key]["values"][i] for c in common]
            seed_rank[str(seed)][key] = float(np.corrcoef(
                rankdata(u_vals), rankdata(a_vals))[0, 1])

    # Distinguish two statistics: (i) Spearman after averaging MAE across seeds,
    # and (ii) the arithmetic mean of the three per-seed Spearman values.
    for key in metrics_rank:
        metrics_rank[key]["mean_of_seed_rhos"] = float(np.mean(
            [seed_rank[str(s)][key] for s in SEEDS]))

    # 2x2: training label x evaluation label, for the two models present in both.
    cells = {}
    for model in CONFIGS32:
        cells[model] = {
            "U->U": compare_cell(EXP19, model, "uniform"),
            "U->A": compare_cell(EXP19, model, "alternative"),
            "A->A": compare_cell(EXP32, model, "alternative"),
            "A->U": compare_cell(EXP32, model, "uniform"),
        }
    cell_summary = {}
    for cell in ("U->U", "U->A", "A->A", "A->U"):
        mrg = cells["mrg_full"][cell]["global_mae"]["mean"]
        tcn = cells["tcn_wide"][cell]["global_mae"]["mean"]
        mrg_nz = cells["mrg_full"][cell]["nonzero_uniform_keys_mae"]["mean"]
        tcn_nz = cells["tcn_wide"][cell]["nonzero_uniform_keys_mae"]["mean"]
        mrg_nz_eval = cells["mrg_full"][cell]["nonzero_mae"]["mean"]
        tcn_nz_eval = cells["tcn_wide"][cell]["nonzero_mae"]["mean"]
        mrg_ev = cells["mrg_full"][cell]["event_mae"]["mean"]
        tcn_ev = cells["tcn_wide"][cell]["event_mae"]["mean"]
        cell_summary[cell] = {
            "mrg_global_mae": mrg,
            "tcn_global_mae": tcn,
            "global_gap_tcn_minus_mrg": tcn - mrg,
            "global_gap_pct_of_tcn": (tcn - mrg) / tcn * 100.0,
            "mrg_nonzero_eval_mae": mrg_nz_eval,
            "tcn_nonzero_eval_mae": tcn_nz_eval,
            "nonzero_eval_gap_tcn_minus_mrg": tcn_nz_eval - mrg_nz_eval,
            "mrg_nonzero_uniform_keys_mae": mrg_nz,
            "tcn_nonzero_uniform_keys_mae": tcn_nz,
            "nonzero_gap_tcn_minus_mrg": tcn_nz - mrg_nz,
            "mrg_event_mae": mrg_ev,
            "tcn_event_mae": tcn_ev,
            "event_gap_tcn_minus_mrg": tcn_ev - mrg_ev,
        }

    # Node-gate comparison under both labels.
    gate = {}
    for label, res in (("uniform", res27_u), ("alternative", res27_a)):
        full = res["mrg_full"]["aggregate"]
        shared = res["mrg_shared_gate"]["aggregate"]
        gate[label] = {
            "full_global_mae": full["global_mae"]["mean"],
            "shared_global_mae": shared["global_mae"]["mean"],
            "global_gap_shared_minus_full": shared["global_mae"]["mean"] - full["global_mae"]["mean"],
            "global_gap_pct_of_shared": (
                (shared["global_mae"]["mean"] - full["global_mae"]["mean"])
                / shared["global_mae"]["mean"] * 100.0
            ),
            "full_nonzero_mae": full["nonzero_mae"]["mean"],
            "shared_nonzero_mae": shared["nonzero_mae"]["mean"],
            "full_event_mae": full["event_mae"]["mean"],
            "shared_event_mae": shared["event_mae"]["mean"],
            "per_seed": [
                {
                    "seed": seed,
                    "full_global_mae": full["global_mae"]["values"][i],
                    "shared_global_mae": shared["global_mae"]["values"][i],
                    "node_improvement_pct": (
                        (shared["global_mae"]["values"][i] - full["global_mae"]["values"][i])
                        / shared["global_mae"]["values"][i] * 100.0
                    ),
                }
                for i, seed in enumerate(SEEDS)
            ],
        }

    # Label-difference statistics on the test keys and on the full grid.
    d0, u0, a0, _ = load_pred(EXP19 / "mrg_full" / "seed-2024" / "predictions_test.npz")
    test_abs = np.abs(a0 - u0)
    test_diff = a0 - u0
    full_abs = np.abs(alt["targets"] - uni["targets"])
    transitions = {
        "both_zero": int(((u0 == 0) & (a0 == 0)).sum()),
        "uniform_zero_alt_positive": int(((u0 == 0) & (a0 > 0)).sum()),
        "uniform_positive_alt_zero": int(((u0 > 0) & (a0 == 0)).sum()),
        "both_positive": int(((u0 > 0) & (a0 > 0)).sum()),
    }
    subgroup_masks = {
        "all": np.ones_like(test_abs, dtype=bool),
        "uniform_nonzero": u0 > 0,
        "event": d0["target_event"],
        "stable": ~d0["target_event"],
        "uniform_zero": u0 == 0,
    }
    by_subgroup = {}
    for name, mask in subgroup_masks.items():
        x = test_abs[mask]
        by_subgroup[name] = {
            "n": int(x.size),
            "mean_abs_diff": float(x.mean()) if x.size else None,
            "median_abs_diff": float(np.median(x)) if x.size else None,
            "p90_abs_diff": float(np.quantile(x, 0.90)) if x.size else None,
            "p95_abs_diff": float(np.quantile(x, 0.95)) if x.size else None,
            "max_abs_diff": float(x.max()) if x.size else None,
        }
    label_diff = {
        "test_keys": {
            "n": int(test_abs.size),
            "mean_abs_diff": float(test_abs.mean()),
            "median_abs_diff": float(np.median(test_abs)),
            "p90_abs_diff": float(np.quantile(test_abs, 0.90)),
            "p95_abs_diff": float(np.quantile(test_abs, 0.95)),
            "max_abs_diff": float(test_abs.max()),
            "mean_signed_diff": float(test_diff.mean()),
            "corr": float(np.corrcoef(u0.ravel(), a0.ravel())[0, 1]),
            "uniform_zero_rate": float((u0 == 0).mean()),
            "alternative_zero_rate": float((a0 == 0).mean()),
            "transitions": transitions,
            "by_subgroup": by_subgroup,
        },
        "full_grid": {
            "n": int(full_abs.size),
            "mean_abs_diff": float(full_abs.mean()),
            "median_abs_diff": float(np.median(full_abs)),
            "p90_abs_diff": float(np.quantile(full_abs, 0.90)),
            "p95_abs_diff": float(np.quantile(full_abs, 0.95)),
            "max_abs_diff": float(full_abs.max()),
        },
    }

    result = {
        "analysis": "proxy-label sensitivity and ranking stability",
        "created_at_utc": "2026-10-26",
        "inputs": {
            "uniform_dataset": str(UNI_DS),
            "alternative_dataset": str(ALT_DS),
            "exp19_predictions": str(EXP19),
            "exp27_predictions": str(EXP27),
            "exp32_predictions": str(EXP32),
        },
        "label_difference": label_diff,
        "exp19": {
            "uniform": res19_u,
            "alternative": res19_a,
            "ranking": {
                "uniform_order": order_u,
                "alternative_order": order_a,
                "rho_of_seed_mean_mae_ranks": rho,
                "top1": top1,
                "top3_overlap": top3_overlap,
                "max_abs_rank_change": max_rank_change,
                "rows": rank_rows,
                "by_metric": metrics_rank,
                "per_seed_rank": seed_rank,
                "nonzero_uniform_keys": {
                    "uniform_order": order_u_nz,
                    "alternative_order": order_a_nz,
                    "rho_of_seed_mean_mae_ranks": rho_nz,
                },
            },
        },
        "exp27": {"uniform": res27_u, "alternative": res27_a, "gate": gate},
        "exp32": {"uniform": res32_u, "alternative": res32_a},
        "two_by_two": {"cells": cells, "summary": cell_summary},
        "caveats": [
            "No new training: SG-EXP-019 predictions were trained on the uniform label and evaluated on both labels.",
            "SG-EXP-032 predictions were trained on the completion-truncated label and evaluated on both labels.",
            "The event mask is the fixed target_event label and is not rebuilt for the alternative target.",
            "Only the Caltech event-time protocol is analyzed; JPL uses a different protocol and keys.",
            "The test period has been inspected; this is a fixed-period label-sensitivity analysis, not an unseen-period validation.",
            "The alternative label is another session-allocation rule, not measured power.",
        ],
    }
    (OUT / "results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    # Markdown report.
    lines = []
    lines.append("# 代理标签敏感性与模型排序稳定性分析\n")
    lines.append("日期：2026-10-26｜范围：Caltech 事件时刻协议｜不训练、不联网\n")
    lines.append("## 目的\n")
    lines.append(
        "回答两个问题：①把会话电量分配规则从“均匀分摊”改为“完成时刻截断”，"
        "测试预测键上的绝对误差和模型排序是否改变；②节点门控与 MRG-GCN/TCN "
        "的结论是否对标签定义敏感。该分析只使用已有冻结预测，不把代理标签当作实测功率。\n"
    )
    lines.append("## 标签差异\n")
    ld = label_diff["test_keys"]
    lines.append(
        f"- 测试键：{ld['n']:,}；均匀标签零值率 {ld['uniform_zero_rate']:.2%}，"
        f"完成时刻截断标签零值率 {ld['alternative_zero_rate']:.2%}。\n"
        f"- 逐键绝对差：均值 {ld['mean_abs_diff']:.6f}，中位数 {ld['median_abs_diff']:.6f}，"
        f"P90 {ld['p90_abs_diff']:.6f}，P95 {ld['p95_abs_diff']:.6f}，"
        f"最大 {ld['max_abs_diff']:.6f} kWh/15 min。\n"
        f"- 零值迁移：两者均零 {ld['transitions']['both_zero']:,}；"
        f"均匀零→截断正 {ld['transitions']['uniform_zero_alt_positive']:,}；"
        f"均匀正→截断零 {ld['transitions']['uniform_positive_alt_zero']:,}；"
        f"两者均正 {ld['transitions']['both_positive']:,}。\n"
    )
    lines.append(
        f"- 全网格逐节点时间片绝对差均值 {label_diff['full_grid']['mean_abs_diff']:.6f} "
        f"kWh/15 min（用于核对论文中的 0.0477816）。\n"
    )

    widths = {"standard": 0.02757, "behavior": 0.03951}
    nz = by_subgroup["uniform_nonzero"]
    ev = by_subgroup["event"]
    lines.append("\n### 标签差异与区间宽度的描述性量级对照（不同统计集合，不作覆盖推断）\n")
    lines.append(
        f"- 非零键：标签差异均值 {nz['mean_abs_diff']:.6f}，P95 {nz['p95_abs_diff']:.6f}；"
        f"事件键：均值 {ev['mean_abs_diff']:.6f}，P95 {ev['p95_abs_diff']:.6f} kWh/15 min。\n"
        f"- 5.3 节冻结区间平均宽度：标准 {widths['standard']:.5f}，行为分层 {widths['behavior']:.5f} kWh/15 min。"
        "该两值引自论文表 5-2，未在本包重算；仅作量级参考。\n"
        "- 两者统计集合不同（非零/事件键 vs 全体键的区间宽度），比例只作描述性量级对照；"
        "不能据此推断逐键覆盖率或实测覆盖。\n"
        "- 本文未针对同步实测值校准或评价区间；现有覆盖结果仅针对所定义的代理标签。\n"
    )

    lines.append("\n## 12 个配置的排序稳定性（均在均匀标签上训练）\n")
    lines.append("| 配置 | 均匀标签 MAE | 截断标签 MAE | 均匀排名 | 截断排名 | 排名变化 |\n")
    lines.append("|---|---:|---:|---:|---:|---:|\n")
    for r in rank_rows:
        lines.append(
            f"| {r['config']} | {r['uniform_mae']:.6f} | {r['alternative_mae']:.6f} | "
            f"{r['uniform_rank']} | {r['alternative_rank']} | {r['rank_delta']:+d} |\n"
        )
    lines.append(
        f"\n三种子平均 MAE 排序的 Spearman = **{rho:.3f}**"
        f"（逐种子相关均值 {metrics_rank['global_mae']['mean_of_seed_rhos']:.3f}）；"
        f"Top-1：均匀 {top1['uniform']} → 截断 {top1['alternative']}；"
        f"Top-3 重合 {top3_overlap}/3；最大排名变化 {max_rank_change} 位。"
        f"固定“均匀非零键”子集上，三种子平均 MAE 排序的 Spearman = **{rho_nz:.3f}**"
        f"（逐种子相关均值 {metrics_rank['nonzero_uniform_keys_mae']['mean_of_seed_rhos']:.3f}）。\n"
    )

    metric_labels = {
        "global_mae": "全局 MAE",
        "zero_mae": "零目标 MAE",
        "stable_mae": "稳定窗口 MAE",
        "nonzero_mae": "非零目标 MAE（评估标签定义）",
        "nonzero_uniform_keys_mae": "固定均匀非零键 MAE",
        "event_mae": "标签事件 MAE",
    }
    seed_ranges = {}
    for key in metric_labels:
        vals = [seed_rank[str(s)][key] for s in SEEDS]
        seed_ranges[key] = (min(vals), max(vals))
    lines.append("\n## 不同评价口径的排序相关性（描述性，不设通过阈值）\n")
    lines.append("| 评价口径 | 三种子平均 MAE 排序的 Spearman（先平均 MAE 再排序） | 逐种子 Spearman 均值 | 逐种子范围 |\n")
    lines.append("|---|---:|---:|---:|\n")
    for key, label in metric_labels.items():
        s = metrics_rank[key]["rho_of_seed_mean_mae_ranks"]
        mean_s = metrics_rank[key]["mean_of_seed_rhos"]
        lo, hi = seed_ranges[key]
        lines.append(f"| {label} | {s:.3f} | {mean_s:.3f} | {lo:.3f} ～ {hi:.3f} |\n")
    g_rank = metrics_rank["global_mae"]
    nz_rank = metrics_rank["nonzero_mae"]
    ev_rank = metrics_rank["event_mae"]
    fnz_rank = metrics_rank["nonzero_uniform_keys_mae"]
    lines.append(
        f"\n注：第一列是“先对三种子 MAE 取平均、再对 12 个配置排序”的 Spearman；"
        f"第二列是三个逐种子 Spearman 的算术均值。两者不同：全局 "
        f"{g_rank['rho_of_seed_mean_mae_ranks']:.3f} vs {g_rank['mean_of_seed_rhos']:.3f}，"
        f"非零 {nz_rank['rho_of_seed_mean_mae_ranks']:.3f} vs {nz_rank['mean_of_seed_rhos']:.3f}。"
        "不得混称。相关值仅描述本已查看测试期；"
        "脚本未设通过/不通过阈值，原 0.9/0.6 分类已删除。\n"
    )

    lines.append("\n## 关键发现\n")
    lines.append(
        f"1. **三种子平均 MAE 排序基本保持，但仅限所检范围**：先平均 MAE 再排序的全局 Spearman "
        f"{g_rank['rho_of_seed_mean_mae_ranks']:.3f}，逐种子相关均值 {g_rank['mean_of_seed_rhos']:.3f}"
        f"（逐种子 0.972/0.972/0.979）；Top-3 3/3，最大排名变化 1 位。"
        "结论限于 12 个配置、两套代理标签和已查看 Caltech 测试期，"
        "不外推到其他模型或实测效度。\n"
        f"2. **种子层面非零排序更敏感**：非零（评价标签）先平均 MAE 再排序的 Spearman "
        f"{nz_rank['rho_of_seed_mean_mae_ranks']:.3f}，逐种子相关均值 {nz_rank['mean_of_seed_rhos']:.3f}"
        f"（逐种子 −0.112/0.098/0.014）；事件 {ev_rank['rho_of_seed_mean_mae_ranks']:.3f}"
        f"（逐种子 0.007–0.608）；固定非零 {fnz_rank['rho_of_seed_mean_mae_ranks']:.3f}"
        "（0.629–0.727）。不能笼统称“排序稳健”。\n"
        "3. **MRG vs TCN 全局差在四种训练/评估组合下均为正**（11.44%–16.06%）；"
        "这是所检条件下的描述；2×2 不是四个独立确认实验。\n"
        "4. **非零/事件结论依赖子集定义**：评估标签非零与固定均匀非零的排名不同；"
        "A->A 中固定子集甚至反转。论文应同时报告两种定义，并保留分母与冻结掩码。\n"
        "5. **节点门控三种子平均 2.69%→1.65%，但 seed-2024 反转**："
        "均匀标签 +1.73%，截断标签 −0.91%；不能写“方向不变/各次一致”。"
        "仍限于当前预算与代理目标。\n"
        "6. **标签差异与区间宽度仅作描述性对照**：非零/事件键的标签差异大于代理区间宽度，"
        "但统计集合不同；不能推断实测覆盖。实测覆盖尚未验证。\n"
    )

    lines.append("\n## 2×2：训练标签 × 评估标签（全局 MAE）\n")
    lines.append("| 训练→评估 | MRG | TCN | TCN−MRG | 占 TCN 比例 |\n")
    lines.append("|---|---:|---:|---:|---:|\n")
    for cell in ("U->U", "U->A", "A->A", "A->U"):
        s = cell_summary[cell]
        lines.append(
            f"| {cell} | {s['mrg_global_mae']:.6f} | {s['tcn_global_mae']:.6f} | "
            f"{s['global_gap_tcn_minus_mrg']:+.6f} | {s['global_gap_pct_of_tcn']:+.2f}% |\n"
        )

    lines.append("\n## 2×2：非零与事件分层\n")
    lines.append("| 训练→评估 | MRG 非零（评估标签） | TCN 非零（评估标签） | MRG 非零（固定均匀键） | TCN 非零（固定均匀键） | MRG 事件 | TCN 事件 |\n")
    lines.append("|---|---:|---:|---:|---:|---:|---:|\n")
    for cell in ("U->U", "U->A", "A->A", "A->U"):
        s = cell_summary[cell]
        lines.append(
            f"| {cell} | {s['mrg_nonzero_eval_mae']:.6f} | {s['tcn_nonzero_eval_mae']:.6f} | "
            f"{s['mrg_nonzero_uniform_keys_mae']:.6f} | {s['tcn_nonzero_uniform_keys_mae']:.6f} | "
            f"{s['mrg_event_mae']:.6f} | {s['tcn_event_mae']:.6f} |\n"
        )
    lines.append(
        "\n注：非零分母：U->U/A->U 为 90,356 键；U->A/A->A 为 40,588 键；"
        "事件键 10,204；事件掩码固定。不同分母的数值不作直接跨格比较。\n"
    )

    lines.append("\n## 节点门控在两种标签下的对照\n")
    lines.append("| 标签 | 节点级门控 MAE | 共享门控 MAE | 共享−节点级 | 占共享比例 |\n")
    lines.append("|---|---:|---:|---:|---:|\n")
    for label in ("uniform", "alternative"):
        g = gate[label]
        lines.append(
            f"| {label} | {g['full_global_mae']:.6f} | {g['shared_global_mae']:.6f} | "
            f"{g['global_gap_shared_minus_full']:+.6f} | {g['global_gap_pct_of_shared']:+.2f}% |\n"
        )
    lines.append("\n## 节点门控的逐种子相对改善\n")
    lines.append("| 种子 | 均匀标签 | 截断标签 |\n")
    lines.append("|---|---:|---:|\n")
    uni_seed = {p["seed"]: p["node_improvement_pct"] for p in gate["uniform"]["per_seed"]}
    alt_seed = {p["seed"]: p["node_improvement_pct"] for p in gate["alternative"]["per_seed"]}
    for seed in SEEDS:
        lines.append(f"| {seed} | {uni_seed[seed]:+.2f}% | {alt_seed[seed]:+.2f}% |\n")
    lines.append(
        "\n注：正值表示节点级门控 MAE 更低。三种子平均 2.69%→1.65%；"
        "seed-2024 在截断标签下由 +1.73% 变为 −0.91%，发生反转。"
        "该表不是替代目标下两类门控重新训练的比较，也未排除共享门控预算触顶。\n"
    )

    lines.append("\n## 建议的论文写法\n")
    lines.append(
        "建议新增 3.8.5（或 5.4.6）“代理标签的排序稳定性”，写四点：\n\n"
        "1. 在本任务所检 12 个配置、两套代理标签和已查看 Caltech 测试期内，"
        "三种子平均全局 MAE 排序基本保持；不能外推到所有模型筛选或实测效度。\n"
        "2. 非零/事件排序对标签和样本集合更敏感；三种子平均 0.420/0.559/0.671，"
        "逐种子非零 −0.112～0.098。不把全局优势外推为活跃片段优势。\n"
        "3. 节点门控三种子平均 2.69%→1.65%，但 seed-2024 由 +1.73% 变为 −0.91%；"
        "必须披露种子反转，结论仍限于当前预算与代理目标。\n"
        "4. 标签差异与区间宽度的比较仅作描述性对照；本文未针对同步实测值校准或评价区间。\n"
    )

    lines.append("\n## 解释与限制\n")
    lines.append(
        "- SG-EXP-019 的 12 个配置都在均匀标签上训练；把它们放到截断标签上评估，"
        "只改变评估标签，不改变预测，因此测的是“标签定义敏感性”。\n"
        "- SG-EXP-032 的 mrg_full/tcn_wide 在截断标签上训练；2×2 用来区分"
        "“训练标签变化”和“评估标签变化”，不是四个独立确认实验。\n"
        "- 事件掩码沿用冻结的 target_event，不随截断目标重建；这与论文 3.8.4 节口径一致。\n"
        "- 该分析只覆盖 Caltech 事件时刻协议；JPL 使用不同协议和预测键，不能合并。\n"
        "- 测试期已查看；这是固定时期的标签敏感性分析，不是未见时期验证，也不是实测功率验证。\n"
        "- 种子层面相关低于三种子平均，不能只用平均值替代逐种子读数。\n"
        "- 本文未针对同步实测值校准或评价区间；现有覆盖结果仅针对所定义的代理标签。\n"
        "- 708,560 个预测键含重叠目标，不作为独立统计样本。\n"
    )

    (OUT / "report.md").write_text("".join(lines), encoding="utf-8")

    # Figures.
    plt.rcParams.update({
        "font.size": 9,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.dpi": 150,
        "savefig.dpi": 200,
        "savefig.bbox": "tight",
    })
    colors = {"mrg": "#0072B2", "tcn": "#D55E00", "accent": "#009E73", "gray": "#666666"}

    fig, ax = plt.subplots(figsize=(5.2, 4.6))
    xs = [vals_u[c] for c in common]
    ys = [vals_a[c] for c in common]
    ax.scatter(xs, ys, s=28, color=colors["mrg"], zorder=3)
    lo = min(xs + ys) * 0.97
    hi = max(xs + ys) * 1.03
    ax.plot([lo, hi], [lo, hi], color=colors["gray"], lw=0.8, ls="--", zorder=1)
    for c, x, y in zip(common, xs, ys):
        ax.annotate(c, (x, y), xytext=(3, 3), textcoords="offset points", fontsize=6.5)
    ax.set_xlabel("Global MAE under uniform label (kWh/15 min)")
    ax.set_ylabel("Global MAE under completion-truncated label (kWh/15 min)")
    ax.set_title("Caltech event-time: label sensitivity of 12 configurations")
    fig.savefig(OUT / "fig_ranking_scatter.png")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(5.2, 4.8))
    for i, r in enumerate(rank_rows):
        ax.plot([0, 1], [r["uniform_rank"], r["alternative_rank"]],
                marker="o", ms=3.5, lw=1.0, color=colors["mrg"], alpha=0.75)
        ax.text(-0.03, r["uniform_rank"], r["config"], ha="right", va="center", fontsize=6.5)
        ax.text(1.03, r["alternative_rank"], r["config"], ha="left", va="center", fontsize=6.5)
    ax.set_xlim(-0.35, 1.35)
    ax.set_ylim(len(common) + 0.5, 0.5)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["Uniform label", "Completion-truncated label"])
    ax.set_ylabel("Rank (1 = lowest MAE)")
    ax.set_title("Rank stability across label definitions")
    fig.savefig(OUT / "fig_rank_slope.png")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(5.0, 4.0))
    labels = ["Uniform", "Completion-truncated"]
    x = np.arange(len(labels))
    full_vals = [gate["uniform"]["full_global_mae"], gate["alternative"]["full_global_mae"]]
    shared_vals = [gate["uniform"]["shared_global_mae"], gate["alternative"]["shared_global_mae"]]
    w = 0.34
    ax.bar(x - w/2, full_vals, w, label="Node-specific gate", color=colors["mrg"])
    ax.bar(x + w/2, shared_vals, w, label="Shared gate", color=colors["tcn"])
    for i, (f, s) in enumerate(zip(full_vals, shared_vals)):
        ax.text(i - w/2, f, f"{f:.4f}", ha="center", va="bottom", fontsize=7)
        ax.text(i + w/2, s, f"{s:.4f}", ha="center", va="bottom", fontsize=7)
        pct = (s - f) / s * 100.0
        ax.text(i, max(f, s) * 1.02, f"gap {pct:+.2f}%", ha="center", va="bottom", fontsize=7)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Global MAE (kWh/15 min)")
    ax.set_title("Node-gate comparison under two labels")
    ax.legend(frameon=False, fontsize=7.5)
    fig.savefig(OUT / "fig_gate_label_sensitivity.png")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(5.2, 3.8))
    vals = test_abs[test_abs > 0]
    ax.hist(vals, bins=np.logspace(np.log10(max(vals.min(), 1e-6)), np.log10(vals.max()), 50),
            color=colors["mrg"], alpha=0.85)
    ax.set_xscale("log")
    ax.set_xlabel("|completion-truncated label − uniform label| (kWh/15 min, log scale)")
    ax.set_ylabel("Test keys")
    ax.set_title("Label difference on the 708,560 test keys")
    fig.savefig(OUT / "fig_label_diff_hist.png")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(5.8, 3.6))
    order_keys = ["global_mae", "stable_mae", "zero_mae",
                  "nonzero_uniform_keys_mae", "event_mae", "nonzero_mae"]
    order_labels = ["Global MAE", "Stable window", "Zero target",
                    "Fixed uniform-nonzero", "Labeled event", "Nonzero (eval-label)"]
    vals = [metrics_rank[k]["rho_of_seed_mean_mae_ranks"] for k in order_keys]
    y = np.arange(len(vals))
    ax.barh(y, vals, color=colors["mrg"], height=0.6)
    ax.set_yticks(y)
    ax.set_yticklabels(order_labels)
    ax.invert_yaxis()
    ax.set_xlim(0, 1.05)
    ax.set_xlabel("Spearman rank correlation (uniform vs completion-truncated)")
    ax.set_title("Rank correlation by evaluation definition")
    for yi, v in zip(y, vals):
        ax.text(v + 0.01, yi, f"{v:.3f}", va="center", fontsize=7)
    fig.savefig(OUT / "fig_rank_stability_by_metric.png", dpi=300)
    plt.close(fig)

    print("wrote", OUT / "results.json")
    print("wrote", OUT / "report.md")
    print("rho_of_seed_mean_mae_ranks", round(rho, 4),
          "top1", top1, "top3", top3_overlap)
    for cell, s in cell_summary.items():
        print(cell, "mrg", round(s["mrg_global_mae"], 6), "tcn", round(s["tcn_global_mae"], 6),
              "gap%", round(s["global_gap_pct_of_tcn"], 3))
    for label, g in gate.items():
        print("gate", label, "gap%", round(g["global_gap_pct_of_shared"], 3))


if __name__ == "__main__":
    main()
