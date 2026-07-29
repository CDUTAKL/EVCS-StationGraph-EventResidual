#!/usr/bin/env python3
"""Read-only audit for station-internal node identifiers in session CSV data."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median


ID_FIELDS = ("siteID", "stationID", "EVSEID", "spaceID")
TIME_FIELDS = ("connectionTime", "disconnectTime", "doneChargingTime")


def parse_time(value: str) -> dt.datetime | None:
    value = value.strip()
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        return dt.datetime.fromisoformat(normalized)
    except ValueError:
        return None


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--max-rows", type=int, default=0)
    args = parser.parse_args()

    unique = {field: set() for field in ID_FIELDS}
    missing = Counter()
    pair_counts: dict[tuple[str, str], Counter] = defaultdict(Counter)
    equality = Counter()
    comparable = Counter()
    sessions_by_node = Counter()
    nodes_by_site: dict[str, set[str]] = defaultdict(set)
    parsed_times = {field: [] for field in TIME_FIELDS}
    rows = 0

    with args.input.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        for row in reader:
            rows += 1
            if args.max_rows and rows > args.max_rows:
                break
            values = {field: (row.get(field) or "").strip() for field in ID_FIELDS}
            for field, value in values.items():
                if value:
                    unique[field].add(value)
                else:
                    missing[field] += 1
            site = values["siteID"]
            node = values["stationID"]
            if site and node:
                nodes_by_site[site].add(node)
                sessions_by_node[node] += 1
            for left, right in (
                ("stationID", "EVSEID"),
                ("stationID", "spaceID"),
                ("EVSEID", "spaceID"),
            ):
                if values[left] and values[right]:
                    comparable[(left, right)] += 1
                    if values[left] == values[right]:
                        equality[(left, right)] += 1
                    pair_counts[(left, right)][(values[left], values[right])] += 1
            for field in TIME_FIELDS:
                parsed = parse_time(row.get(field) or "")
                if parsed is not None:
                    parsed_times[field].append(parsed)

    mapping_summary = {}
    for (left, right), counts in pair_counts.items():
        left_to_right: dict[str, set[str]] = defaultdict(set)
        right_to_left: dict[str, set[str]] = defaultdict(set)
        for (left_value, right_value), _ in counts.items():
            left_to_right[left_value].add(right_value)
            right_to_left[right_value].add(left_value)
        mapping_summary[f"{left}->{right}"] = {
            "one_to_one": all(len(v) == 1 for v in left_to_right.values())
            and all(len(v) == 1 for v in right_to_left.values()),
            "left_values_with_multiple_right_values": sum(
                len(v) > 1 for v in left_to_right.values()
            ),
            "right_values_with_multiple_left_values": sum(
                len(v) > 1 for v in right_to_left.values()
            ),
        }

    session_counts = sorted(sessions_by_node.values())
    report = {
        "audit_id": "SG-DATA-001",
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "input": {
            "path": str(args.input.resolve()),
            "sha256": sha256(args.input),
            "rows_scanned": rows,
            "columns": fields,
        },
        "identifier_summary": {
            "unique_counts": {field: len(values) for field, values in unique.items()},
            "missing_counts": dict(missing),
            "equality_rates": {
                f"{left}=={right}": (
                    equality[(left, right)] / comparable[(left, right)]
                    if comparable[(left, right)]
                    else None
                )
                for left, right in (
                    ("stationID", "EVSEID"),
                    ("stationID", "spaceID"),
                    ("EVSEID", "spaceID"),
                )
            },
            "mapping_summary": mapping_summary,
            "nodes_per_site": {
                site: len(nodes) for site, nodes in sorted(nodes_by_site.items())
            },
        },
        "coverage_summary": {
            "node_count": len(session_counts),
            "sessions_per_node_min": min(session_counts) if session_counts else None,
            "sessions_per_node_median": median(session_counts) if session_counts else None,
            "sessions_per_node_max": max(session_counts) if session_counts else None,
        },
        "time_summary": {
            field: {
                "parsed_count": len(values),
                "min": min(values).isoformat() if values else None,
                "max": max(values).isoformat() if values else None,
            }
            for field, values in parsed_times.items()
        },
        "preliminary_findings": [
            "stationID and EVSEID must be treated as aliases if equality rate is 1.0",
            "spaceID may be used only after one-to-one and temporal stability checks",
            "the target remains reconstructed proxy load rather than meter power",
        ],
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report["identifier_summary"], ensure_ascii=False))


if __name__ == "__main__":
    main()
