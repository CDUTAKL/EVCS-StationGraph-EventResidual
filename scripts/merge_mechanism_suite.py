"""SG-EXP-006 机制套件汇总合并：遍历 children 下全部完整变体生成统一汇总。

在并行续跑（scripts/resume_partial.py）全部完成后执行一次：
按 8 个预期变体顺序读取各变体的 metrics_summary.json（四格还原通过者），
生成 mechanism_summary.csv 与 manifest.json，使 run 成为完整可核验产物。

用法（服务器，项目根目录执行）：
    .venv/bin/python scripts/merge_mechanism_suite.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from evcs_station_graph.experiments.mechanism import (
    _flatten_summary,
    _read_json,
    _write_rows,
)
from evcs_station_graph.reproducibility import write_json

RUN_TAG = "20260803-113723"
ROOT = Path("outputs/experiments/SG-EXP-006") / RUN_TAG
EXPECTED = [
    "relation-load",
    "relation-event",
    "relation-pattern",
    "relation-all",
    "topk-5",
    "topk-7",
    "dropout-0p2",
    "dropout-0p4",
]


def main() -> int:
    """合并所有已完整变体并生成 mechanism_summary.csv + manifest.json。"""
    children_root = ROOT / "children"
    rows = []
    child_runs = {}
    for name in EXPECTED:
        summary_path = (
            children_root / "SG-EXP-006-{}".format(name) / RUN_TAG / "metrics_summary.json"
        )
        if not summary_path.exists():
            print("[缺] {}".format(name))
            continue
        summary = _read_json(summary_path)
        ok = bool(summary.get("four_cell_reconstruction_all_pass"))
        print("[读] {} 四格还原={}".format(name, ok))
        if not ok:
            continue
        child_runs[name] = str(summary_path.parent)
        rows.extend(_flatten_summary(name, summary))

    if not rows:
        raise RuntimeError("没有任何完整变体可汇总，拒绝生成空结果文件")
    _write_rows(rows, ROOT / "mechanism_summary.csv")
    write_json(
        {
            "experiment_id": "SG-EXP-006",
            "run_tag": RUN_TAG,
            "variant_count": len(EXPECTED),
            "completed_variants": list(child_runs),
            "child_runs": child_runs,
            "summary_csv": "mechanism_summary.csv",
            "four_cell_reconstruction_all_pass": all(
                row["four_cell_reconstruction_all_pass"] for row in rows
            ),
            "merged": True,
        },
        ROOT / "manifest.json",
    )
    print("完成：{}/{} 变体已汇总".format(len(child_runs), len(EXPECTED)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
