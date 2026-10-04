#!/usr/bin/env python3
"""Reproduce the fixed-origin forecast-to-operation interface example.

The script derives interval-average *proxy* rates from the already reviewed
SG-EXP-021 display-only three-seed mean. It does not create a dispatch result,
fit a capacity threshold, or modify any source predictions.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "outputs/analysis/SG-EXP-021-demand-warning/final/first_example_seed_mean_display_only.csv"
DEFAULT_OUT = ROOT / "outputs/analysis/SG-EXP-022-forecast-operation-interface"
INTERVAL_HOURS = 0.25
EXPECTED_LOCAL_ORIGIN = "2021-03-16T13:00:00-07:00"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    if not args.source.is_file():
        raise FileNotFoundError(args.source)
    if args.out.exists():
        raise FileExistsError(f"Refusing to overwrite existing evidence: {args.out}")

    with args.source.open(newline="", encoding="utf-8") as stream:
        rows = [row for row in csv.DictReader(stream) if row["model"] == "mrg_full"]
    rows.sort(key=lambda row: int(row["horizon_step"]))
    if len(rows) != 4 or [int(row["horizon_step"]) for row in rows] != [1, 2, 3, 4]:
        raise ValueError("Expected exactly the four MRG-GCN horizon rows")
    if {row["origin_cutoff_local"] for row in rows} != {EXPECTED_LOCAL_ORIGIN}:
        raise ValueError("Unexpected issue time for the frozen example")
    if {row["origin_index"] for row in rows} != {"101411"}:
        raise ValueError("Unexpected source prediction origin")
    if {row["seeds"] for row in rows} != {"3"}:
        raise ValueError("The display values must summarize exactly three seeds")
    if [float(row["actual_target_start_lead_minutes"]) for row in rows] != [0, 15, 30, 45]:
        raise ValueError("Unexpected target-start lead-time mapping")

    args.out.mkdir(parents=True)
    derived: list[dict[str, str]] = []
    for row in rows:
        pred = float(row["y_pred_sum_mean_display_only"])
        pred_sd = float(row["y_pred_sum_sample_sd_display_only"])
        actual = float(row["y_true_sum"])
        derived.append(
            {
                "target_interval_start_local": row["target_local"],
                "target_start_lead_minutes": row["actual_target_start_lead_minutes"],
                "horizon_step": row["horizon_step"],
                "predicted_proxy_kwh_per_15min_mean_display_only": f"{pred:.12f}",
                "predicted_proxy_kwh_per_15min_seed_sd_display_only": f"{pred_sd:.12f}",
                "retrospective_proxy_kwh_per_15min": f"{actual:.12f}",
                "predicted_proxy_average_kw_mean_display_only": f"{pred / INTERVAL_HOURS:.12f}",
                "predicted_proxy_average_kw_seed_sd_display_only": f"{pred_sd / INTERVAL_HOURS:.12f}",
                "retrospective_proxy_average_kw": f"{actual / INTERVAL_HOURS:.12f}",
                "underprediction_kwh_per_15min": f"{max(0.0, actual - pred):.12f}",
                "underprediction_proxy_kw": f"{max(0.0, actual - pred) / INTERVAL_HOURS:.12f}",
                "selected_process_onset_local": "2021-03-16T13:45:00-07:00",
                "origin_cutoff_local": row["origin_cutoff_local"],
                "note": "Three-seed mean/SD are display summaries, not a deployed ensemble or prediction interval; all power values are proxy-equivalent interval averages, not metered kW.",
            }
        )

    csv_path = args.out / "forecast_operation_case.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(derived[0]))
        writer.writeheader()
        writer.writerows(derived)

    onset = derived[-1]
    audit = {
        "analysis_id": "SG-EXP-022",
        "status": "PASS_FIXED_ORIGIN_ARITHMETIC_AND_TIME_MAPPING",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source": str(args.source.resolve()),
        "source_sha256": sha256(args.source),
        "source_model": "mrg_full",
        "source_seeds": [2024, 2025, 2026],
        "source_origin_index": 101411,
        "issue_time_local": EXPECTED_LOCAL_ORIGIN,
        "selected_process_onset_local": "2021-03-16T13:45:00-07:00",
        "rows": len(derived),
        "target_start_leads_minutes": [int(float(row["target_start_lead_minutes"])) for row in derived],
        "interval_hours": INTERVAL_HOURS,
        "conversion": "proxy kWh per 15-minute interval / 0.25 h = proxy-equivalent interval-average kW",
        "onset_step_predicted_proxy_kwh_mean": float(onset["predicted_proxy_kwh_per_15min_mean_display_only"]),
        "onset_step_predicted_proxy_kw_mean": float(onset["predicted_proxy_average_kw_mean_display_only"]),
        "onset_step_retrospective_proxy_kwh": float(onset["retrospective_proxy_kwh_per_15min"]),
        "onset_step_retrospective_proxy_kw_equivalent": float(onset["retrospective_proxy_average_kw"]),
        "onset_step_underprediction_kwh": float(onset["underprediction_kwh_per_15min"]),
        "onset_step_underprediction_kw_equivalent": float(onset["underprediction_proxy_kw"]),
        "onset_step_relative_underprediction": float(onset["underprediction_kwh_per_15min"]) / float(onset["retrospective_proxy_kwh_per_15min"]),
        "evidence_boundary": [
            "The target is retrospective session-energy allocation, not measured power.",
            "The ten-node set is not the complete station load.",
            "The three-seed mean is for display only, not a deployed ensemble.",
            "No capacity limit, background site load, controllable-session constraints, or dispatch objective is available; no dispatch schedule or benefit is calculated.",
        ],
    }
    audit_path = args.out / "audit.json"
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    manifest = {
        "analysis_id": "SG-EXP-022",
        "source_sha256": sha256(args.source),
        "script_sha256": sha256(Path(__file__).resolve()),
        "files": {
            "forecast_operation_case.csv": sha256(csv_path),
            "audit.json": sha256(audit_path),
        },
        "scope": "Fixed-origin arithmetic and time-mapping check only; no dispatch experiment.",
    }
    (args.out / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
