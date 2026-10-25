#!/usr/bin/env python3
"""Audit within-session measured charging-profile shape in the KIT LF dataset.

The script reads only charging_uuid, timestamp_ns, and the three phase active
power columns from the public Parquet source. Active power in the source is
calculated from measured voltage/current; the comparison is a curve-shape
diagnostic, not ACN label calibration or station-level forecast validation.

Requires DuckDB 1.5+ with httpfs for the remote URL, or accepts a local Parquet
path via --source. HTTP proxy settings can be supplied in http_proxy/https_proxy.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
from datetime import date, datetime
from pathlib import Path
from statistics import median

import duckdb


DEFAULT_URL = (
    "https://zenodo.org/api/records/17866847/files/"
    "ev-charging_lf.parquet/content"
)
PUBLISHED_SIZE = 422_470_722
PUBLISHED_MD5 = "0327dae2664c79ecde0bd07166bf6b1d"
PUBLISHED_DOI = "10.5281/zenodo.17866847"
INTERVAL_SECONDS = 900.0
ACTIVE_POWER_THRESHOLD_W = 100.0
MAX_GAP_MULTIPLE = 5.0
MIN_WINDOW_SECONDS = INTERVAL_SECONDS
MIN_TIME_COVERAGE = 0.95


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, obj: object) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=DEFAULT_URL, help="LF Parquet URL or local file")
    ap.add_argument("--charging-metadata", type=Path, help="Optional small charging.parquet metadata table")
    ap.add_argument("--output-dir", required=True, type=Path)
    args = ap.parse_args()

    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute("SET threads=4")
    proxy = os.environ.get("https_proxy") or os.environ.get("HTTPS_PROXY") or os.environ.get("http_proxy") or os.environ.get("HTTP_PROXY")
    if args.source.startswith(("http://", "https://")):
        con.execute("LOAD httpfs")
        if proxy:
            escaped = proxy.replace("'", "''")
            con.execute(f"SET http_proxy='{escaped}'")

    source_sql = "'" + args.source.replace("'", "''") + "'"
    con.execute(f"""
        CREATE TEMP TABLE lf AS
        SELECT CAST(charging_uuid AS VARCHAR) AS sid,
               timestamp_ns AS ts,
               CAST(p_l1_w AS DOUBLE) + CAST(p_l2_w AS DOUBLE) + CAST(p_l3_w AS DOUBLE) AS p_w
        FROM read_parquet({source_sql})
    """)
    con.execute("""
        CREATE TEMP TABLE lagged AS
        SELECT sid, ts, p_w,
               LAG(ts) OVER (PARTITION BY sid ORDER BY ts) AS prev_ts,
               LAG(p_w) OVER (PARTITION BY sid ORDER BY ts) AS prev_p_w
        FROM lf
    """)
    con.execute("""
        CREATE TEMP TABLE segments AS
        SELECT sid, ts, prev_ts, p_w, prev_p_w,
               EPOCH_NS(ts) - EPOCH_NS(prev_ts) AS dt_ns,
               (EPOCH_NS(ts) - EPOCH_NS(prev_ts)) / 1000000000.0 AS dt_s
        FROM lagged
        WHERE prev_ts IS NOT NULL
    """)
    con.execute("""
        CREATE TEMP TABLE quality AS
        WITH base AS (
            SELECT sid,
                   COUNT(*) + 1 AS sample_count,
                   MIN(ts) AS first_ts,
                   MAX(ts) AS last_ts,
                   MIN(ts) FILTER (WHERE p_w > ?) AS active_start,
                   MAX(ts) FILTER (WHERE p_w > ?) AS active_end,
                   COUNT(*) FILTER (WHERE dt_s <= 0) AS nonpositive_intervals,
                   QUANTILE_CONT(dt_s, 0.5) FILTER (WHERE dt_s > 0) AS median_dt_s,
                   QUANTILE_CONT(dt_s, 0.99) FILTER (WHERE dt_s > 0) AS p99_dt_s,
                   MAX(dt_s) FILTER (WHERE dt_s > 0) AS max_dt_s
            FROM segments
            GROUP BY sid
        ),
        span AS (
            SELECT s.sid,
                   SUM(s.dt_ns) FILTER (
                       WHERE s.dt_s > 0 AND s.dt_s <= ? * b.median_dt_s
                   ) / 1000000000.0 AS covered_seconds,
                   COUNT(*) FILTER (
                       WHERE s.dt_s > ? * b.median_dt_s
                   ) AS long_gap_count
            FROM segments s JOIN base b USING (sid)
            GROUP BY s.sid
        )
        SELECT b.*, sp.covered_seconds, sp.long_gap_count,
               (EPOCH_NS(b.last_ts) - EPOCH_NS(b.first_ts)) / 1000000000.0 AS observed_seconds,
               (EPOCH_NS(b.active_end) - EPOCH_NS(b.active_start)) / 1000000000.0 AS active_window_seconds,
               sp.covered_seconds / NULLIF((EPOCH_NS(b.last_ts) - EPOCH_NS(b.first_ts)) / 1000000000.0, 0) AS time_coverage
        FROM base b JOIN span sp USING (sid)
    """, [ACTIVE_POWER_THRESHOLD_W, ACTIVE_POWER_THRESHOLD_W, MAX_GAP_MULTIPLE, MAX_GAP_MULTIPLE])
    con.execute("""
        CREATE TEMP TABLE segment_bins AS
        SELECT s.sid,
               CAST(FLOOR((((EPOCH_NS(s.prev_ts) - EPOCH_NS(q.active_start)) + (EPOCH_NS(s.ts) - EPOCH_NS(q.active_start))) / 2.0 / 1000000000.0) / ?) AS BIGINT) AS bin_id,
               ((s.prev_p_w + s.p_w) / 2.0) * s.dt_s / 3600000.0 AS energy_kwh
        FROM segments s JOIN quality q USING (sid)
        WHERE s.dt_s > 0
          AND s.dt_s <= ? * q.median_dt_s
          AND s.prev_ts >= q.active_start
          AND s.ts <= q.active_end
          AND q.active_start IS NOT NULL
          AND q.active_end IS NOT NULL
    """, [INTERVAL_SECONDS, MAX_GAP_MULTIPLE])
    bin_rows = con.execute("""
        SELECT sid, bin_id, SUM(energy_kwh) AS energy_kwh
        FROM segment_bins
        GROUP BY sid, bin_id
        ORDER BY sid, bin_id
    """).fetchall()
    bins_by_id: dict[str, dict[int, float]] = {}
    for sid, bin_id, energy in bin_rows:
        bins_by_id.setdefault(str(sid), {})[int(bin_id)] = float(energy)

    quality_rows = con.execute("""
        SELECT CAST(sid AS VARCHAR), sample_count, first_ts, last_ts,
               active_start, active_end, nonpositive_intervals, median_dt_s,
               p99_dt_s, max_dt_s, covered_seconds, long_gap_count,
               observed_seconds, active_window_seconds, time_coverage
        FROM quality ORDER BY active_start, sid
    """).fetchall()

    metadata_by_id: dict[str, tuple[str, str, str]] = {}
    if args.charging_metadata:
        meta_sql = "'" + str(args.charging_metadata).replace("'", "''") + "'"
        for sid, day, brand, model in con.execute(
            f"SELECT CAST(charging_uuid AS VARCHAR), CAST(date AS VARCHAR), "
            f"CAST(car_brand AS VARCHAR), CAST(car_model AS VARCHAR) "
            f"FROM read_parquet({meta_sql})"
        ).fetchall():
            metadata_by_id[str(sid)] = (str(day), str(brand or ""), str(model or ""))

    rows: list[dict[str, object]] = []
    for idx, q in enumerate(quality_rows, start=1):
        (sid, sample_count, first_ts, last_ts, active_start, active_end,
         nonpositive, median_dt, p99_dt, max_dt, covered_s, long_gaps,
         observed_s, active_window_s, coverage) = q
        bins = bins_by_id.get(str(sid), {})
        duration = float(active_window_s or 0.0)
        energy = float(sum(bins.values()))
        bin_count = int(math.ceil(duration / INTERVAL_SECONDS)) if duration > 0 else 0
        uniform: list[float] = []
        actual: list[float] = []
        for b in range(bin_count):
            left = b * INTERVAL_SECONDS
            right = min(duration, (b + 1) * INTERVAL_SECONDS)
            overlap = max(0.0, right - left)
            uniform.append(energy * overlap / duration if duration > 0 else 0.0)
            actual.append(float(bins.get(b, 0.0)))
        abs_diffs = [abs(a - u) for a, u in zip(actual, uniform)]
        included = (
            duration >= MIN_WINDOW_SECONDS
            and float(coverage or 0.0) >= MIN_TIME_COVERAGE
            and energy > 0
            and bin_count >= 2
        )
        reasons = []
        if duration < MIN_WINDOW_SECONDS: reasons.append("active_window_under_15min")
        if float(coverage or 0.0) < MIN_TIME_COVERAGE: reasons.append("timestamp_coverage_below_95pct")
        if energy <= 0: reasons.append("nonpositive_integrated_energy")
        if bin_count < 2: reasons.append("fewer_than_two_relative_bins")
        day, brand, model = metadata_by_id.get(str(sid), ("", "", ""))
        rows.append({
            "session_index": idx,
            "record_date": day,
            "sample_count": int(sample_count),
            "measurement_start": first_ts.isoformat() if first_ts else "",
            "measurement_end": last_ts.isoformat() if last_ts else "",
            "observed_duration_min": float(observed_s or 0.0) / 60.0,
            "active_window_min": duration / 60.0,
            "median_interval_s": float(median_dt or 0.0),
            "p99_interval_s": float(p99_dt or 0.0),
            "max_interval_s": float(max_dt or 0.0),
            "long_gap_count_gt_5x_median": int(long_gaps or 0),
            "nonpositive_interval_count": int(nonpositive or 0),
            "time_coverage_fraction": float(coverage or 0.0),
            "integrated_energy_kwh_from_phase_power": energy,
            "relative_15min_bin_count": bin_count,
            "mae_kwh_per_relative_bin_vs_uniform": (sum(abs_diffs) / bin_count if bin_count else None),
            "total_variation_distance_vs_uniform": (sum(abs_diffs) / (2.0 * energy) if energy > 0 else None),
            "peak_bin_energy_ratio_vs_uniform": (max(actual) / max(uniform) if uniform and max(uniform) > 0 else None),
            "included_in_shape_summary": bool(included),
            "exclusion_reason": ";".join(reasons),
        })

    included_rows = [r for r in rows if r["included_in_shape_summary"]]
    tvs = [float(r["total_variation_distance_vs_uniform"]) for r in included_rows]
    maes = [float(r["mae_kwh_per_relative_bin_vs_uniform"]) for r in included_rows]
    peak_ratios = [float(r["peak_bin_energy_ratio_vs_uniform"]) for r in included_rows]
    source = Path(args.source)
    source_hash = sha256(source) if source.is_file() else None
    session_dates = [m[0] for m in metadata_by_id.values() if m[0]]
    summary = {
        "audit_id": "KIT-LF-MEASURED-PROFILE-20261021",
        "status": "COMPUTED",
        "retrieved_or_queried_utc_date": date.today().isoformat(),
        "source": {
            "doi": PUBLISHED_DOI,
            "url": args.source,
            "published_size_bytes": PUBLISHED_SIZE,
            "published_md5": PUBLISHED_MD5,
            "local_source_sha256": source_hash,
            "dataset_license": "CC BY 4.0 (KITopen record; Zenodo rendered license field was blank, API reports cc-by-4.0)",
            "source_dates": [min(session_dates), max(session_dates)] if session_dates else None,
            "metering_semantics": "phase active power calculated from recorded phase voltage/current; voltage/current are measured",
        },
        "runtime": {"duckdb": duckdb.__version__},
        "method": {
                       "integration": "trapezoidal integration between adjacent samples; nanosecond timestamp differences are retained; intervals >5x per-session median spacing are excluded",
            "active_window": f"first through last sample with summed phase active power >{ACTIVE_POWER_THRESHOLD_W:g} W",
            "binning": "15-minute bins relative to first active sample; segment energy assigned by segment midpoint",
            "uniform_counterfactual": "same integrated energy distributed in proportion to each 15-minute bin's overlap with the observed active window",
            "inclusion": f"active window >= {MIN_WINDOW_SECONDS:g} s, valid-time coverage >= {MIN_TIME_COVERAGE:.0%}, positive energy, and >=2 relative bins",
            "shape_metric": "total variation distance = sum absolute per-bin energy differences / (2 * integrated session energy); 0 means identical binned shape",
            "limitations": [
                "not ACN or a station-level multi-node dataset",
                "no connection/done/disconnect timestamps to reproduce the thesis target construction",
                "no same-node mapping, ACN graph or compatible input tensor for frozen-checkpoint inference",
                "does not validate forecast accuracy, meter calibration or dispatch/application benefit",
                "controlled measurement sessions do not represent ordinary station operation",
            ],
        },
        "quality": {
            "sessions_in_source_metadata": len(metadata_by_id) or None,
            "lf_session_count": len(rows),
            "sessions_in_shape_summary": len(included_rows),
            "sessions_excluded": len(rows) - len(included_rows),
            "session_date_min_max": [min(session_dates), max(session_dates)] if session_dates else None,
            "valid_time_coverage_min": min(float(r["time_coverage_fraction"]) for r in rows) if rows else None,
            "valid_time_coverage_median": median(float(r["time_coverage_fraction"]) for r in rows) if rows else None,
            "total_variation_median": median(tvs) if tvs else None,
            "total_variation_iqr": [
                sorted(tvs)[len(tvs)//4], sorted(tvs)[(3*len(tvs))//4]
            ] if len(tvs) >= 4 else None,
            "mae_kwh_per_bin_median": median(maes) if maes else None,
            "peak_bin_energy_ratio_median": median(peak_ratios) if peak_ratios else None,
        },
    }

    csv_path = out / "session_profile_audit.csv"
    if rows:
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    summary_path = out / "summary.json"
    write_json(summary_path, summary)
    method_path = out / "query_method.txt"
    method_path.write_text(
        "Source fields: charging_uuid, timestamp_ns, p_l1_w, p_l2_w, p_l3_w.\n"
        f"Computed power: p_l1_w + p_l2_w + p_l3_w; source power columns are calculated from measured voltage/current.\n"
        f"Sampling intervals above {MAX_GAP_MULTIPLE:g}x each session median were excluded from integration.\n"
        f"Active-window threshold: total phase power > {ACTIVE_POWER_THRESHOLD_W:g} W.\n"
        "Per-session energy integrated trapezoidally using nanosecond timestamp differences; binned relative to the first active sample in 900 s bins.\n"
        "Uniform reference preserves the integrated energy and spreads it over the observed active window.\n"
        "Comparison is a curve-shape diagnostic only. It does not recreate ACN connection-to-disconnect target labels.\n"
    )
    manifest = {
        "script_sha256": sha256(Path(__file__).resolve()),
        "summary_json_sha256": sha256(summary_path),
        "session_profile_csv_sha256": sha256(csv_path),
        "query_method_sha256": sha256(method_path),
        "source_local_sha256": source_hash,
        "published_source_md5": PUBLISHED_MD5,
        "metadata_local_sha256": sha256(args.charging_metadata) if args.charging_metadata else None,
    }
    write_json(out / "manifest.json", manifest)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("\nDerived file hashes:")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
