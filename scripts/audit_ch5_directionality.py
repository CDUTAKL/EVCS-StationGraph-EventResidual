#!/usr/bin/env python3
"""Audit Chapter 5 TE selection and PCMCI+ multiple-testing evidence.

The TE part audits the preserved 100-permutation summary without rerunning or
overwriting it. The PCMCI+ part reruns only the training-segment analysis under
the currently installed Tigramite and applies Holm correction to all finite
off-diagonal lag 1..4 tests. It does not train a forecasting model.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import sys
from pathlib import Path

import numpy as np
from statsmodels.stats.multitest import multipletests


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs/thesis/content-review-20261011-revision/directionality"
EXPECTED_DATA_SHA256 = "082ce06d6be9fd9d97916cf25a729b48b446894505e9eb12faf912e4579d4df4"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)

    data_path = ROOT / "data/processed/SG-DATA-005-primary-tensor.npz"
    te_path = ROOT / "outputs/analysis/transfer_entropy/transfer_entropy_summary.json"
    sys.path.insert(0, str(ROOT / "src"))
    from evcs_station_graph.data import load_tensor_bundle
    bundle = load_tensor_bundle(data_path)
    te = json.loads(te_path.read_text(encoding="utf-8"))
    data_hash = sha256(data_path)
    if data_hash != EXPECTED_DATA_SHA256:
        raise ValueError(f"Frozen SG-DATA-005 hash changed: {data_hash}")
    if int(te.get("n_perm", -1)) != 100 or int(te.get("bins", -1)) != 8:
        raise ValueError("Unexpected legacy TE run settings")
    p_min = np.asarray(te["p_matrix"], dtype=float)
    te_matrix = np.asarray(te["te_matrix"], dtype=float)
    lag_matrix = np.asarray(te["lag_matrix"], dtype=int)
    node_ids = list(bundle.node_ids)
    n = len(node_ids)
    if p_min.shape != (n, n) or te_matrix.shape != p_min.shape or lag_matrix.shape != p_min.shape:
        raise ValueError("TE matrices do not match the archived node order")
    lag_rows = []
    asym_rows = []
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            raw = float(p_min[i, j])
            # The archived cell is already min(p_lag1, p_lag2, p_lag4).
            # Bonferroni over 3 lags x 90 directed pairs restores the full family.
            adjusted = min(raw * (3 * n * (n - 1)), 1.0)
            lag_rows.append({
                "source": node_ids[i], "target": node_ids[j],
                "selected_lag_by_min_p": int(lag_matrix[i, j]),
                "te_at_selected_lag": float(te_matrix[i, j]),
                "archived_min_p_over_3_lags": raw,
                "bonferroni_p_over_270_tests": adjusted,
                "nominal_p_lt_0_05": raw < 0.05,
                "familywise_p_lt_0_05": adjusted < 0.05,
            })
    for i in range(n):
        for j in range(i + 1, n):
            forward = float(te_matrix[i, j])
            backward = float(te_matrix[j, i])
            denominator = forward + backward
            asym = abs(forward - backward) / max(denominator, 1e-12)
            asym_rows.append({
                "node_i": node_ids[i], "node_j": node_ids[j],
                "te_i_to_j": forward, "lag_i_to_j": int(lag_matrix[i, j]),
                "te_j_to_i": backward, "lag_j_to_i": int(lag_matrix[j, i]),
                "asymmetry_abs_diff_over_sum": asym,
                "above_0_30": asym > 0.30,
            })
    write_csv(out / "te_legacy_pair_audit.csv", lag_rows, list(lag_rows[0]))
    write_csv(out / "te_asymmetry_recomputed.csv", asym_rows, list(asym_rows[0]))

    # Rerun current Tigramite only to expose the complete lagged p-value family.
    from tigramite import data_processing as pp
    from tigramite.pcmci import PCMCI
    from tigramite.independence_tests.parcorr import ParCorr

    train_end = int(bundle.split_origins["train"][-1])
    targets = bundle.targets[: train_end + 1]
    current = PCMCI(
        dataframe=pp.DataFrame(targets, var_names=list(bundle.node_ids)),
        cond_ind_test=ParCorr(significance="analytic"),
        verbosity=0,
    ).run_pcmciplus(tau_min=1, tau_max=4, pc_alpha=0.05)
    pval = np.asarray(current["p_matrix"], dtype=float)
    coef = np.asarray(current["val_matrix"], dtype=float)
    tests = []
    for source in range(n):
        for target in range(n):
            if source == target:
                continue
            for lag in range(1, 5):
                p = float(pval[source, target, lag])
                value = float(coef[source, target, lag])
                if np.isfinite(p) and np.isfinite(value):
                    tests.append({
                        "source": node_ids[source], "target": node_ids[target],
                        "lag": lag, "parcorr_value": value, "p_raw": p,
                    })
    adjusted = multipletests([row["p_raw"] for row in tests], alpha=0.05, method="holm")[1]
    for row, adj in zip(tests, adjusted):
        row["p_holm"] = float(adj)
        row["nominal_p_lt_0_05"] = row["p_raw"] < 0.05
        row["holm_p_lt_0_05"] = float(adj) < 0.05
    write_csv(out / "pcmci_current_env_full_family.csv", tests, list(tests[0]))

    old_pcmci = json.loads((ROOT / "outputs/analysis/pcmci/pcmci_summary.json").read_text(encoding="utf-8"))
    raw_cell_count = sum(row["nominal_p_lt_0_05"] for row in tests)
    holm_cell_count = sum(row["holm_p_lt_0_05"] for row in tests)
    raw_pairs = {(row["source"], row["target"]) for row in tests if row["nominal_p_lt_0_05"]}
    holm_pairs = {(row["source"], row["target"]) for row in tests if row["holm_p_lt_0_05"]}
    legacy_te_count = sum(row["nominal_p_lt_0_05"] for row in lag_rows)
    corrected_te_count = sum(row["familywise_p_lt_0_05"] for row in lag_rows)
    asymmetry_count = sum(row["above_0_30"] for row in asym_rows)
    runtime_versions = {
        "tigramite": importlib.metadata.version("tigramite"),
        "statsmodels": importlib.metadata.version("statsmodels"),
        "numpy": np.__version__,
    }
    summary = {
        "status": "AUDIT_COMPLETE_EXPLORATORY_ONLY",
        "data_sha256": data_hash,
        "dataset": "SG-DATA-005-primary-tensor.npz",
        "training_raw_observations": int(targets.shape[0]),
        "training_origins": int(len(bundle.split_origins["train"])),
        "node_ids": node_ids,
        "te_archived": {
            "summary_path": str(te_path.relative_to(ROOT)),
            "summary_sha256": sha256(te_path),
            "permutations_per_pair_lag": 100,
            "p_resolution": 1 / 101,
            "tests_in_family": 270,
            "lag_selection": "minimum of three per-lag permutation p-values; selected lag and TE are stored",
            "pairs_below_nominal_0_05": int(legacy_te_count),
            "bonferroni_significant_pairs": int(corrected_te_count),
            "smallest_available_p_min": float(min(row["archived_min_p_over_3_lags"] for row in lag_rows)),
            "smallest_adjusted_p": float(min(row["bonferroni_p_over_270_tests"] for row in lag_rows)),
            "asymmetry_definition": "abs(TE_ij - TE_ji) / (TE_ij + TE_ji)",
            "asymmetry_gt_0_30_pairs": int(asymmetry_count),
        },
        "pcmci_legacy": {
            "summary_path": "outputs/analysis/pcmci/pcmci_summary.json",
            "summary_sha256": sha256(ROOT / "outputs/analysis/pcmci/pcmci_summary.json"),
            "nominal_significant_lag_cells_recorded": int(old_pcmci["n_edges_pcmci"]),
            "te_pair_overlap_recorded": int(old_pcmci["n_te_confirmed_by_pcmci"]),
            "limitation": "legacy summary omits the full p-value matrix and does not record its Tigramite environment; adjusted inference cannot be reconstructed from the 80 selected edges",
        },
        "pcmci_current_environment_rerun": {
            "software": runtime_versions,
            "family": "all finite off-diagonal directed node x lag cells, lag 1..4",
            "n_tests": len(tests),
            "nominal_significant_lag_cells": int(raw_cell_count),
            "holm_significant_lag_cells": int(holm_cell_count),
            "nominal_directed_pairs": len(raw_pairs),
            "holm_directed_pairs": len(holm_pairs),
            "min_raw_p": float(min(row["p_raw"] for row in tests)),
            "min_holm_p": float(min(row["p_holm"] for row in tests)),
            "replay_matches_legacy_raw_edge_count": int(raw_cell_count) == int(old_pcmci["n_edges_pcmci"]),
            "use_in_thesis": "sensitivity audit only; do not replace the historical count because the archived package version and complete p-matrix were not saved",
        },
        "multiple_testing_method": {
            "TE": "Bonferroni over 270 directed-pair-by-lag tests, using the archived selected minimum p per directed pair; the correction is deliberately conservative and all legacy raw minima are too coarse to pass",
            "PCMCI_current_environment": "Holm step-down over the complete 360 off-diagonal directed-pair-by-lag family; exploratory post-selection PCMCI+ p-values do not establish physical causality",
        },
        "retraining_performed": False,
    }
    (out / "directionality_audit.json").write_text(
        json.dumps({"summary": summary, "pcmci_tests": tests}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
