"""Verify figure ranges against per-seed results without importing a GUI stack."""
import ast
import csv
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/figures/fig3_17_proxy_label_stability.py"
DATA = ROOT / "outputs/analysis/SG-ANA-20261026-proxy-stability"


def load_parser():
    tree = ast.parse(SCRIPT.read_text())
    function = next(node for node in tree.body
                    if isinstance(node, ast.FunctionDef) and node.name == "parse_range")
    namespace = {"re": re}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(SCRIPT), "exec"), namespace)
    return namespace["parse_range"]


class ProxyLabelFigureRangeTest(unittest.TestCase):
    def setUp(self):
        self.parse = load_parser()

    def test_all_six_csv_ranges_match_per_seed_results(self):
        mapping = {
            "全局 MAE": "global_mae", "稳定窗口 MAE": "stable_mae",
            "零目标 MAE": "zero_mae", "固定均匀非零键 MAE": "nonzero_uniform_keys_mae",
            "标签事件 MAE": "event_mae", "非零目标 MAE（评价标签）": "nonzero_mae",
        }
        result = json.loads((DATA / "results.json").read_text())
        per_seed = result["exp19"]["ranking"]["per_seed_rank"]
        with (DATA / "table3_16_spearman.csv").open(newline="", encoding="utf-8-sig") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(len(rows), 6)
        for row in rows:
            key = mapping[row["evaluation_definition"]]
            values = [per_seed[str(seed)][key] for seed in (2024, 2025, 2026)]
            expected = tuple(float(f"{value:.3f}") for value in (min(values), max(values)))
            with self.subTest(metric=key):
                self.assertEqual(self.parse(row["spearman_per_seed_range"]), expected)

    def test_signed_endpoints_and_typographic_separators(self):
        for value, expected in [
            ("0.972-0.979", (0.972, 0.979)),
            ("-0.112-0.098", (-0.112, 0.098)),
            ("−0.112–0.098", (-0.112, 0.098)),
            ("-0.800--0.100", (-0.8, -0.1)),
        ]:
            with self.subTest(value=value):
                self.assertEqual(self.parse(value), expected)

    def test_invalid_reversed_or_out_of_domain_ranges_fail(self):
        for value in ["0.979-0.972", "0.972", "0.1-0.2-0.3", "nan-0.2", "-1.1-0.2"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.parse(value)


if __name__ == "__main__":
    unittest.main()
