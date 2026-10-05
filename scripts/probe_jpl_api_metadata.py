"""Read-only, privacy-minimizing probe of ACN-Data JPL session metadata.

The token is requested interactively and is never written to disk. Raw API
records are held in memory only; the output contains aggregate coverage,
sampled time bounds, and response hashes, never session/user identifiers.
"""
import argparse
import base64
import getpass
import hashlib
import json
import math
from pathlib import Path
import urllib.parse
import urllib.request

BASE = "https://ev.caltech.edu/api/v1/sessions/jpl"
FIELDS = ("stationID", "sessionID", "connectionTime", "disconnectTime",
          "doneChargingTime", "kWhDelivered", "chargingCurrent", "pilotSignal", "timezone")


def rows_from(payload):
    if isinstance(payload, dict):
        for key in ("_items", "items", "sessions", "data"):
            if isinstance(payload.get(key), list):
                return payload[key]
    return payload if isinstance(payload, list) else []


def summarize_page(rows):
    dates = [str(row["connectionTime"]) for row in rows
             if isinstance(row, dict) and row.get("connectionTime") is not None]
    stations = {str(row["stationID"]) for row in rows
                if isinstance(row, dict) and row.get("stationID") is not None}
    return {
        "record_count": len(rows),
        "connection_time_min": min(dates, default=None),
        "connection_time_max": max(dates, default=None),
        "distinct_station_ids_in_page": len(stations),
        "nonnull_field_counts": {
            field: sum(isinstance(row, dict) and row.get(field) is not None for row in rows)
            for field in FIELDS
        },
        "station_ids_internal": stations,
    }


def fetch(url, headers):
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=35) as response:
        raw = response.read(12_000_001)
        if len(raw) > 12_000_000:
            raise ValueError("API page exceeded the 12 MB bounded-read limit")
        return json.loads(raw), response.status, hashlib.sha256(raw).hexdigest()


def trace_shape(value, depth=0):
    shape = {"type": type(value).__name__}
    if isinstance(value, (list, tuple)):
        shape["length"] = len(value)
        if value and depth < 2 and isinstance(value[0], (list, tuple, dict)):
            shape["item_shape"] = trace_shape(value[0], depth + 1)
    elif isinstance(value, dict) and depth < 2:
        shape["keys"] = sorted(value.keys())
        shape["members"] = {key: trace_shape(item, depth + 1) for key, item in value.items()
                            if isinstance(item, (list, tuple, dict))}
    return shape


def summarize_trace_page(payload):
    rows = rows_from(payload)
    current = [row for row in rows if isinstance(row, dict) and row.get("chargingCurrent") is not None]
    pilot = [row for row in rows if isinstance(row, dict) and row.get("pilotSignal") is not None]
    sample = current[0] if current else (pilot[0] if pilot else None)
    return {
        "record_count": len(rows),
        "records_with_chargingCurrent": len(current),
        "records_with_pilotSignal": len(pilot),
        "sample_time_bounds": ({key: sample.get(key) for key in
                                 ("connectionTime", "doneChargingTime", "disconnectTime")}
                                if sample else None),
        "sample_trace_shapes": ({key: trace_shape(sample[key]) for key in
                                 ("chargingCurrent", "pilotSignal", "timestamps")
                                 if sample.get(key) is not None}
                                if sample else None),
    }


def candidate_crosswalk(candidate_ids, sampled_station_ids):
    candidate_ids = set(candidate_ids)
    sampled_station_ids = set(sampled_station_ids)
    return {
        "static_candidate_count": len(candidate_ids),
        "sampled_api_station_id_count": len(sampled_station_ids),
        "matching_identifier_count": len(candidate_ids & sampled_station_ids),
        "static_candidates_not_seen_in_api_sample": len(candidate_ids - sampled_station_ids),
        "api_sample_ids_not_in_static_candidates": len(sampled_station_ids - candidate_ids),
        "interpretation": "string-ID overlap in sampled rows only; not a physical EVSE or full-coverage proof",
    }


def run(out_path, timeseries_pages=None, candidate_inventory=None):
    if out_path.exists():
        raise FileExistsError(out_path)
    token = getpass.getpass("ACN API token (input hidden): ").strip()
    if not token:
        raise ValueError("No token supplied")
    headers = {
        "Authorization": "Basic " + base64.b64encode((token + ":").encode()).decode(),
        "User-Agent": "JPL-readonly-feasibility-probe/1.0",
    }
    token = None
    first_url = BASE + "?" + urllib.parse.urlencode({"sort": "connectionTime", "pretty": "1"})
    first, status, first_hash = fetch(first_url, headers)
    meta = first.get("_meta", {}) if isinstance(first, dict) else {}
    page_size = int(meta.get("max_results") or 25)
    total = int(meta.get("total") or len(rows_from(first)))
    page_count = max(1, math.ceil(total / page_size))
    pages = sorted({1, max(1, round(page_count * .25)), max(1, round(page_count * .5)),
                    max(1, round(page_count * .75)), page_count})
    page_data = {1: (first, status, first_hash)}
    for page in pages:
        if page == 1:
            continue
        url = BASE + "?" + urllib.parse.urlencode(
            {"sort": "connectionTime", "page": str(page), "pretty": "1"})
        page_data[page] = fetch(url, headers)

    page_summaries = []
    station_ids = set()
    for page in pages:
        payload, http_status, digest = page_data[page]
        summary = summarize_page(rows_from(payload))
        station_ids.update(summary.pop("station_ids_internal"))
        page_summaries.append({"page": page, "http_status": http_status,
                               "response_sha256": digest, **summary})

    output = {
        "dataset_id": "DATA-JPL-FEASIBILITY-20261004",
        "source": BASE,
        "query": {"sort": "connectionTime", "pages": pages,
                  "sampling": "first, quarter, midpoint, three-quarter, last API metadata pages"},
        "raw_records_saved": False,
        "credential_saved": False,
        "api_metadata": {"total_sessions_reported": total, "page_size": page_size,
                         "page_count": page_count},
        "sampled_page_summaries": page_summaries,
        "distinct_station_ids_across_sampled_pages_only": len(station_ids),
        "limitations": [
            "Page sampling is not an exhaustive station inventory or field-completeness census.",
            "Metadata endpoint omits time-series payloads; no kW reconstruction is implied.",
            "API is dynamic; response hashes identify these fetched pages, not a frozen dataset release.",
        ],
    }
    if candidate_inventory is not None:
        inventory = json.loads(candidate_inventory.read_text())
        candidate_ids = [row["candidate_id"] for row in inventory
                         if isinstance(row, dict) and row.get("candidate_id")]
        output["sampled_station_id_crosswalk"] = candidate_crosswalk(candidate_ids, station_ids)
    if timeseries_pages:
        output["timeseries_endpoint_probes"] = []
        for timeseries_page in timeseries_pages:
            ts_url = BASE + "/ts?" + urllib.parse.urlencode(
                {"page": str(timeseries_page), "pretty": "1"})
            try:
                payload, http_status, digest = fetch(ts_url, headers)
                output["timeseries_endpoint_probes"].append({
                    "page": timeseries_page, "http_status": http_status,
                    "response_sha256": digest, **summarize_trace_page(payload),
                })
            except Exception as exc:
                output["timeseries_endpoint_probes"].append({
                    "page": timeseries_page, "error": type(exc).__name__ + ": " + str(exc)[:160],
                })
    out_path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(output, ensure_ascii=False, indent=2) + "\n").encode()
    out_path.write_bytes(encoded)
    print(json.dumps({"output": str(out_path), "summary_sha256": hashlib.sha256(encoded).hexdigest(),
                      "total_sessions": total, "sampled_pages": pages,
                      "distinct_station_ids_in_sample": len(station_ids),
                      "raw_records_saved": False, "credential_saved": False}, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--timeseries-page", type=int, action="append")
    parser.add_argument("--candidate-inventory", type=Path)
    args = parser.parse_args()
    run(args.out, args.timeseries_page, args.candidate_inventory)
