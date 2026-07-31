#!/usr/bin/env python3
"""SG-EXP-007 汇总与 007b 续跑脚本。

背景：sg_exp_007_screen.py 曾在 λ 筛选全部训练完成后、汇总阶段因
``_check_stop_conditions`` 的指标层级 bug（``["mae"]`` 缺 ``["mean"]``）崩溃。
四个 λ（0/2/3/5）× 三种子的训练工件完整，本脚本复用既有工件：
  1. 从 ``007a_screening/`` 读取各 λ 的 metrics_summary.json
  2. 复用 sg_exp_007_screen 的停止条件与最优 λ 选择逻辑
  3. 仅训练 SG-EXP-007b（intensity 模式）
  4. 写出与完整运行一致的 experiment_report.json

用法（项目根目录下）：
  python scripts/sg_exp_007_resume.py outputs/sg_exp_007/20260731-092508
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# scripts/ 目录下的兄弟模块导入（python scripts/xxx.py 时该目录自动入 sys.path，
# 显式写出以便其他入口调用时也能找到）
sys.path.insert(0, str(Path(__file__).resolve().parent))

from sg_exp_007_screen import (  # noqa: E402
    LAMBDA_VALUES,
    _conclude,
    _run_007b,
    _save_report,
    _select_best_lambda,
)


def _load_007a_results(root: Path) -> dict[int, dict]:
    """从既有 007a 筛选目录读取各 λ 的汇总指标。

    目录结构：``007a_screening/SG-EXP-007a-lambda<λ>/<run_tag>/metrics_summary.json``。
    任一 λ 的汇总文件缺失时显式报错——不完整的结果集不得进入最优 λ 选择。
    """
    screening = root / "007a_screening"
    if not screening.is_dir():
        raise FileNotFoundError(f"007a 筛选目录不存在：{screening}")
    results: dict[int, dict] = {}
    for lambda_val in LAMBDA_VALUES:
        candidates = sorted(
            screening.glob(f"SG-EXP-007a-lambda{lambda_val}/*/metrics_summary.json")
        )
        if not candidates:
            raise FileNotFoundError(
                f"λ={lambda_val} 的 metrics_summary.json 未找到于 {screening}"
            )
        if len(candidates) > 1:
            raise RuntimeError(
                f"λ={lambda_val} 存在多份汇总文件，无法确定权威版本：{candidates}"
            )
        with open(candidates[0]) as f:
            results[lambda_val] = json.load(f)["scopes"]
        print(f"  已加载 λ={lambda_val}: {candidates[0].parent.parent.name}")
    return results


def main() -> None:
    """续跑入口：复用 007a 工件 → 选择最优 λ → 训练 007b → 写报告。"""
    if len(sys.argv) != 2:
        raise SystemExit("用法：python scripts/sg_exp_007_resume.py <outputs/sg_exp_007/标签目录>")
    root = Path(sys.argv[1])
    if not root.is_dir():
        raise FileNotFoundError(f"工件目录不存在：{root}")

    print(f"SG-EXP-007 续跑：复用 {root} 的 007a 工件")
    results_007a = _load_007a_results(root)

    selection = _select_best_lambda(results_007a)
    if selection is None:
        print("\n✗ 所有 λ 均未通过停止条件。SG-EXP-007 终止。")
        _save_report(root, "FAILED", results_007a, None, None)
        return
    best_lambda, best_result = selection

    results_007b = _run_007b(best_lambda, root)
    _conclude(root, results_007a, best_lambda, best_result, results_007b)


if __name__ == "__main__":
    main()
