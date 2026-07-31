#!/usr/bin/env python3
"""配对 Bootstrap 显著性检验：量化模型间 MAE 差异的统计证据。

本脚本读取各实验 per-seed 的 predictions.csv.gz，按统一键做 inner join，
在 global / event_window / stable_window 三个窗口内执行 10,000 次有放回重采样，
报告 MAE(基线) - MAE(提议) 的 Bootstrap 分布、95% 百分位置信区间与单侧 p 值。

使用约定：
- 正值表示提议模型更优；p 值 = P(diff <= 0) 越小越显著。
- 键不一致时立即报错，禁止静默丢弃样本。
- 合并结果以 (seed, key) 为抽样单元池，等价于拼接后重采样。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd


# 预测文件统一主键与价值列
KEY_COLUMNS = ["split", "origin_index", "horizon", "node_id"]
VALUE_COLUMNS = ["y_true", "y_pred", "target_event", "rule_trigger"]


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--night-run-dir",
        type=Path,
        default=Path("outputs/night_run/20260730-171821"),
        help="SG-EXP-002~006 夜跑根目录",
    )
    parser.add_argument(
        "--mlp-run-dir",
        type=Path,
        default=Path("outputs/experiments/SG-EXP-009/20260731-095406"),
        help="SG-EXP-009 MLP 实验根目录",
    )
    parser.add_argument(
        "--ablation-run-dir",
        type=Path,
        default=Path(
            "outputs/night_run/20260730-171821/SG-EXP-006/20260730-183243/"
            "children/SG-EXP-006-ablation-no_event_gate/20260730-183243"
        ),
        help="SG-EXP-006 no_event_gate 消融实验根目录",
    )
    parser.add_argument(
        "--n-resamples",
        type=int,
        default=10000,
        help="Bootstrap 重采样次数",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=2024,
        help="Bootstrap 随机数种子，保证可复现",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("outputs/analysis/bootstrap_significance.json"),
        help="JSON 结果输出路径",
    )
    return parser.parse_args()


def load_predictions(path: Path) -> pd.DataFrame:
    """读取单个 seed 的 predictions.csv.gz 并校验必要列与类型。

    参数
    ----
    path: 预测文件路径，须为 gzip 压缩 CSV。

    返回
    ----
    解析后的 DataFrame，索引列 KEY_COLUMNS 已保留，数值列类型正确。

    异常
    ----
    FileNotFoundError: 文件不存在。
    ValueError: 缺少必要列、键重复或存在非有限值。
    """
    if not path.is_file():
        raise FileNotFoundError(f"预测文件不存在：{path}")

    # origin_index / horizon 为整数；y_true / y_pred 稍后强制转 float64
    df = pd.read_csv(
        path,
        dtype={"origin_index": int, "horizon": int},
    )

    missing = [col for col in KEY_COLUMNS + VALUE_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"预测文件缺少必要列：{missing}，文件={path}")

    if df.duplicated(KEY_COLUMNS).any():
        raise ValueError(f"预测文件存在重复键：{path}")

    for col in ("y_true", "y_pred"):
        values = pd.to_numeric(df[col], errors="coerce")
        if values.isna().any():
            raise ValueError(f"预测文件 {path} 的 {col} 存在非数值项")
        df[col] = values.astype(np.float64)

    for col in ("target_event", "rule_trigger"):
        # pandas 默认 astype(bool) 会把非空字符串与 NaN 都转为 True，
        # 因此先显式校验取值集合，禁止静默腐蚀事件窗口定义。
        unique = df[col].dropna().unique()
        allowed = {0, 1, True, False}
        if not set(unique).issubset(allowed):
            raise ValueError(
                f"预测文件 {path} 的 {col} 包含非法布尔值：{unique.tolist()}"
            )
        if df[col].isna().any():
            raise ValueError(f"预测文件 {path} 的 {col} 存在缺失值")
        df[col] = df[col].astype(bool)

    return df


def align_predictions(
    base_df: pd.DataFrame,
    prop_df: pd.DataFrame,
) -> Dict[str, np.ndarray]:
    """按统一主键 inner join 两个模型的预测，并返回对齐后的 NumPy 数组。

    参数
    ----
    base_df: 基线模型预测表。
    prop_df: 提议模型预测表。

    返回
    ----
    含 truth / base_pred / prop_pred / target_event / rule_trigger 的字典。

    异常
    ----
    ValueError: 键集合不一致、配对后为空、y_true 不匹配或存在非有限值。
    """
    base_keys = base_df.set_index(KEY_COLUMNS).index
    prop_keys = prop_df.set_index(KEY_COLUMNS).index

    base_only = base_keys.difference(prop_keys)
    prop_only = prop_keys.difference(base_keys)
    if len(base_only) > 0 or len(prop_only) > 0:
        raise ValueError(
            f"两模型预测键不一致：基线独有 {len(base_only)} 条，提议独有 {len(prop_only)} 条，"
            f"禁止静默丢弃样本"
        )

    merged = base_df[KEY_COLUMNS + VALUE_COLUMNS].merge(
        prop_df[KEY_COLUMNS + VALUE_COLUMNS],
        on=KEY_COLUMNS,
        how="inner",
        suffixes=("_base", "_prop"),
    )

    if len(merged) == 0:
        raise ValueError("配对后无共同键，无法执行 Bootstrap")

    truth = merged["y_true_base"].to_numpy(dtype=np.float64)
    base_pred = merged["y_pred_base"].to_numpy(dtype=np.float64)
    prop_pred = merged["y_pred_prop"].to_numpy(dtype=np.float64)
    target_event = merged["target_event_base"].to_numpy(dtype=bool)
    rule_trigger = merged["rule_trigger_base"].to_numpy(dtype=bool)

    prop_truth = merged["y_true_prop"].to_numpy(dtype=np.float64)
    if not np.array_equal(truth, prop_truth):
        diff_count = int(np.sum(truth != prop_truth))
        raise ValueError(
            f"配对后两模型对应的 y_true 不一致（{diff_count}/{truth.size} 处不同）"
        )
    if not np.array_equal(
        merged["target_event_base"].to_numpy(dtype=bool),
        merged["target_event_prop"].to_numpy(dtype=bool),
    ):
        raise ValueError("配对后两模型对应的 target_event 不一致")

    for arr, name in (
        (truth, "y_true"),
        (base_pred, "y_pred_base"),
        (prop_pred, "y_pred_prop"),
    ):
        if not np.isfinite(arr).all():
            raise ValueError(f"配对后 {name} 存在非有限值")

    return {
        "truth": truth,
        "base_pred": base_pred,
        "prop_pred": prop_pred,
        "target_event": target_event,
        "rule_trigger": rule_trigger,
    }


def window_mask(
    window: str,
    target_event: np.ndarray,
    rule_trigger: np.ndarray,
) -> np.ndarray:
    """按窗口类型返回布尔掩码。

    参数
    ----
    window: "global" / "event_window" / "stable_window"。
    target_event: 目标事件标志。
    rule_trigger: 规则触发标志（保留参数以统一接口，当前未参与掩码）。

    返回
    ----
    与 target_event 同形的布尔数组。
    """
    if window == "global":
        return np.ones_like(target_event, dtype=bool)
    if window == "event_window":
        return target_event
    if window == "stable_window":
        return ~target_event
    raise ValueError(f"未知窗口类型：{window}")


def paired_bootstrap_mae_diff(
    base_pred: np.ndarray,
    prop_pred: np.ndarray,
    truth: np.ndarray,
    mask: np.ndarray,
    n_resamples: int,
    rng: np.random.Generator,
) -> Dict[str, float]:
    """对配对样本执行 Bootstrap，返回 MAE(基线) - MAE(提议) 的统计量。

    参数
    ----
    base_pred: 基线预测值。
    prop_pred: 提议预测值。
    truth: 真实值。
    mask: 窗口掩码。
    n_resamples: 重采样次数。
    rng: NumPy 随机数生成器。

    返回
    ----
    含 n_samples、observed_diff、bootstrap_mean_diff、ci_lower、ci_upper、
    p_value_one_sided 的字典。

    异常
    ----
    ValueError: 窗口内无样本或数值非有限。
    """
    if n_resamples <= 0:
        raise ValueError(f"n_resamples 必须为正整数，收到 {n_resamples}")

    base_errors = np.abs(base_pred[mask] - truth[mask])
    prop_errors = np.abs(prop_pred[mask] - truth[mask])
    n = base_errors.size

    if n == 0:
        raise ValueError("窗口掩码内无样本")
    if not (np.isfinite(base_errors).all() and np.isfinite(prop_errors).all()):
        raise ValueError("窗口内存在非有限绝对误差")

    # diff_i = |基线误差|_i - |提议误差|_i，重采样后的均值即 MAE(基线) - MAE(提议)
    point_diffs = base_errors - prop_errors
    observed_diff = float(point_diffs.mean())

    # 批量生成 Bootstrap 重采样索引，降低 Python 层循环开销。
    # 单批索引数组内存控制在约 160MB 以内：batch_size * n * 8 <= 2e7 * 8。
    # 使用 int32 索引，n 远小于 2^31。
    batch_size = max(1, min(100, int(2e7 // n)))
    n_batches = (n_resamples + batch_size - 1) // batch_size
    diffs = np.empty(n_resamples, dtype=np.float64)
    start = 0
    for batch_idx in range(n_batches):
        current_batch = min(batch_size, n_resamples - batch_idx * batch_size)
        idx = rng.integers(0, n, size=(current_batch, n), dtype=np.int32)
        diffs[start : start + current_batch] = point_diffs[idx].mean(axis=1)
        start += current_batch
    ci_lower = float(np.percentile(diffs, 2.5))
    ci_upper = float(np.percentile(diffs, 97.5))
    bootstrap_mean = float(diffs.mean())
    # 单侧 p 值：提议不优于基线的概率，即 diff <= 0 的比例
    p_value = float(np.mean(diffs <= 0.0))

    return {
        "n_samples": int(n),
        "observed_diff": observed_diff,
        "bootstrap_mean_diff": bootstrap_mean,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "p_value_one_sided": p_value,
    }


def _load_aligned_pair(base_path: Path, prop_path: Path) -> Dict[str, np.ndarray]:
    """读取并配对单个 seed 的预测，返回对齐后的 NumPy 数组字典。"""
    return align_predictions(
        load_predictions(base_path), load_predictions(prop_path)
    )


def run_single_seed_comparison(
    base_path: Path,
    prop_path: Path,
    windows: List[str],
    n_resamples: int,
    rng: np.random.Generator,
) -> Dict[str, Dict[str, Any]]:
    """执行单个 seed 的一组比较（多窗口）。"""
    aligned = _load_aligned_pair(base_path, prop_path)

    results: Dict[str, Dict[str, Any]] = {}
    for window in windows:
        mask = window_mask(window, aligned["target_event"], aligned["rule_trigger"])
        results[window] = paired_bootstrap_mae_diff(
            aligned["base_pred"],
            aligned["prop_pred"],
            aligned["truth"],
            mask,
            n_resamples,
            rng,
        )
    return results


def run_pooled_comparison(
    base_paths: List[Path],
    prop_paths: List[Path],
    windows: List[str],
    n_resamples: int,
    rng: np.random.Generator,
) -> Dict[str, Dict[str, Any]]:
    """合并多个 seed 后执行 Bootstrap，抽样单元为 (seed, key)。"""
    if len(base_paths) != len(prop_paths):
        raise ValueError(
            f"基线与提议模型的 seed 路径数量不一致：{len(base_paths)} vs {len(prop_paths)}"
        )

    aligned_list = [
        _load_aligned_pair(base_path, prop_path)
        for base_path, prop_path in zip(base_paths, prop_paths)
    ]

    arrays = {
        key: np.concatenate([aligned[key] for aligned in aligned_list])
        for key in ("truth", "base_pred", "prop_pred", "target_event", "rule_trigger")
    }

    results: Dict[str, Dict[str, Any]] = {}
    for window in windows:
        mask = window_mask(window, arrays["target_event"], arrays["rule_trigger"])
        results[window] = paired_bootstrap_mae_diff(
            arrays["base_pred"],
            arrays["prop_pred"],
            arrays["truth"],
            mask,
            n_resamples,
            rng,
        )
    return results


def build_comparison_specs(args: argparse.Namespace) -> List[Dict[str, Any]]:
    """构建全部比较对的元信息。"""
    night_dir = args.night_run_dir.resolve()
    mlp_dir = args.mlp_run_dir.resolve()
    ablation_dir = args.ablation_run_dir.resolve()

    def night_path(exp_id: str, run_tag: str) -> Path:
        return night_dir / exp_id / run_tag

    # SG-EXP-002~005 夜跑共用同一 run_tag
    tcn_dir = night_path("SG-EXP-002", "20260730-171821")
    static_dir = night_path("SG-EXP-003", "20260730-171821")
    adaptive_dir = night_path("SG-EXP-004", "20260730-171821")
    residual_dir = night_path("SG-EXP-005", "20260730-171821")

    specs = [
        {
            "name": "TCN - StaticGraph",
            "baseline": "TCN (SG-EXP-002)",
            "proposed": "StaticGraph (SG-EXP-003)",
            "windows": ["global", "event_window"],
            "base_dir": tcn_dir,
            "prop_dir": static_dir,
        },
        {
            "name": "StaticGraph - AdaptiveGraph",
            "baseline": "StaticGraph (SG-EXP-003)",
            "proposed": "AdaptiveGraph (SG-EXP-004)",
            "windows": ["global", "event_window"],
            "base_dir": static_dir,
            "prop_dir": adaptive_dir,
        },
        {
            "name": "AdaptiveGraph - EventResidual",
            "baseline": "AdaptiveGraph (SG-EXP-004)",
            "proposed": "EventResidual (SG-EXP-005)",
            "windows": ["event_window"],
            "base_dir": adaptive_dir,
            "prop_dir": residual_dir,
        },
        {
            "name": "StaticGraph - MLP",
            "baseline": "StaticGraph (SG-EXP-003)",
            "proposed": "MLP (SG-EXP-009)",
            "windows": ["global", "event_window"],
            "base_dir": static_dir,
            "prop_dir": mlp_dir,
        },
        {
            "name": "TCN - MLP",
            "baseline": "TCN (SG-EXP-002)",
            "proposed": "MLP (SG-EXP-009)",
            "windows": ["global"],
            "base_dir": tcn_dir,
            "prop_dir": mlp_dir,
        },
        {
            "name": "AdaptiveGraph - no_event_gate",
            "baseline": "AdaptiveGraph (SG-EXP-004)",
            "proposed": "no_event_gate ablation (SG-EXP-006)",
            "windows": ["event_window"],
            "base_dir": adaptive_dir,
            "prop_dir": ablation_dir,
        },
    ]
    return specs


def seed_path(directory: Path, seed: int) -> Path:
    """构造 seed 目录下的 predictions.csv.gz 路径。"""
    return directory / f"seed-{seed}" / "predictions.csv.gz"


def run_all_comparisons(
    specs: List[Dict[str, Any]],
    seeds: List[int],
    n_resamples: int,
    rng_seed: int,
) -> Dict[str, Any]:
    """执行全部比较对的所有 seed 与 pooled 分析。"""
    rng = np.random.default_rng(rng_seed)
    comparison_results: List[Dict[str, Any]] = []

    for spec in specs:
        per_seed: Dict[str, Dict[str, Dict[str, Any]]] = {}
        base_paths = [seed_path(spec["base_dir"], s) for s in seeds]
        prop_paths = [seed_path(spec["prop_dir"], s) for s in seeds]
        if len(base_paths) != len(prop_paths):
            raise ValueError(
                f"{spec['name']} 的基线与提议路径数量不一致"
            )

        for seed, base_path, prop_path in zip(seeds, base_paths, prop_paths):
            per_seed[str(seed)] = run_single_seed_comparison(
                base_path,
                prop_path,
                spec["windows"],
                n_resamples,
                rng,
            )

        pooled = run_pooled_comparison(
            base_paths,
            prop_paths,
            spec["windows"],
            n_resamples,
            rng,
        )

        comparison_results.append(
            {
                "name": spec["name"],
                "baseline": spec["baseline"],
                "proposed": spec["proposed"],
                "windows": spec["windows"],
                "per_seed": per_seed,
                "pooled": pooled,
            }
        )

    return {
        "metadata": {
            "seeds": seeds,
            "n_resamples": n_resamples,
            "rng_seed": rng_seed,
            "note": "diff = MAE(baseline) - MAE(proposed)；正值表示提议模型更优",
        },
        "comparisons": comparison_results,
    }


def format_table(results: Dict[str, Any]) -> str:
    """将结果格式化为对齐文本表。"""
    header = (
        "Comparison",
        "Window",
        "Seed",
        "N",
        "MeanDiff",
        "CI_lower",
        "CI_upper",
        "p_one_sided",
    )
    rows: List[Tuple[str, ...]] = [header]

    for comp in results["comparisons"]:
        for window in comp["windows"]:
            for seed, seed_result in comp["per_seed"].items():
                r = seed_result[window]
                rows.append(
                    (
                        comp["name"],
                        window,
                        str(seed),
                        f"{r['n_samples']}",
                        f"{r['observed_diff']:.6f}",
                        f"{r['ci_lower']:.6f}",
                        f"{r['ci_upper']:.6f}",
                        f"{r['p_value_one_sided']:.4f}",
                    )
                )
            pool = comp["pooled"][window]
            rows.append(
                (
                    comp["name"],
                    window,
                    "pooled",
                    f"{pool['n_samples']}",
                    f"{pool['observed_diff']:.6f}",
                    f"{pool['ci_lower']:.6f}",
                    f"{pool['ci_upper']:.6f}",
                    f"{pool['p_value_one_sided']:.4f}",
                )
            )

    widths = [max(len(row[i]) for row in rows) for i in range(len(header))]
    lines = [
        "  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)) for row in rows
    ]
    lines.insert(1, "-" * len(lines[0]))
    return "\n".join(lines)


def main() -> int:
    """CLI 入口。"""
    args = parse_args()
    for label, directory in (
        ("--night-run-dir", args.night_run_dir),
        ("--mlp-run-dir", args.mlp_run_dir),
        ("--ablation-run-dir", args.ablation_run_dir),
    ):
        if not directory.exists():
            raise FileNotFoundError(
                f"{label} 指定的目录不存在：{directory.resolve()}，"
                f"请通过 {label} 指定正确路径"
            )
    args.output.parent.mkdir(parents=True, exist_ok=True)

    specs = build_comparison_specs(args)
    seeds = [2024, 2025, 2026]

    print(
        f"开始配对 Bootstrap 显著性检验：seeds={seeds}，"
        f"n_resamples={args.n_resamples}，rng_seed={args.seed}",
        file=sys.stderr,
    )

    results = run_all_comparisons(
        specs,
        seeds,
        args.n_resamples,
        args.seed,
    )

    args.output.write_text(
        json.dumps(results, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    table = format_table(results)
    print("\n" + table + "\n")
    print(f"结果已写入：{args.output.resolve()}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
