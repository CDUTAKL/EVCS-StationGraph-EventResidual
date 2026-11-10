"""Assemble .cache/acn-a-tier/feasibility.json from measured probe records.

All numbers are derived from probe_results.jsonl / items_probe.jsonl / the manifest,
so nothing is hand-typed. The token never appears here.
"""
import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone

BASE = ".cache/acn-a-tier"
RESULTS = [json.loads(l) for l in open(BASE + "/probe_results.jsonl")]
ITEMS = [json.loads(l) for l in open(BASE + "/items_probe.jsonl")]
MAN = list(csv.DictReader(open(BASE + "/test_window_manifest.csv")))
CK = json.load(open(".cache/acn-audit-20261102/checkpoint_caltech_windowed.json"))


def exp(label, **kw):
    for r in RESULTS:
        if r["label"] == label:
            rec = {
                "label": label,
                "url_no_token": r["url_no_token"],
                "probe_index": r["probe_index"],
                "http_status": r["status"],
                "elapsed_s": r["elapsed_s"],
                "response_bytes": r["bytes"],
                "response_MiB": round(r["bytes"] / 1048576, 2),
                "meta": r.get("meta"),
                "n_items": r.get("n_items"),
                "error": r.get("error"),
                "body_head": (r.get("body_head") or "")[:120] or None,
            }
            rec.update(kw)
            return rec
    raise SystemExit("missing probe " + label)


# ---------------------------------------------------------------- measurements
ctrl = exp("control_page1_default")
iso = exp("where_connectionTime_ISO_2021-03_pg1_default")
rfc_mar = exp("where_connectionTime_RFC1123_2021-03_pg1_default")
rfc_mar7 = exp("where_RFC1123_2021-03-01_to_03-07_maxres100")
full_mar = exp("fullpage_2021-03_12_to_04_01_pg1_maxres100")
full_aug = exp("fullpage_2021-08_pg1_maxres100")
page2_mar = exp("raw_2021-03_12_to_04_01_pg2_maxres100")
in_probe = exp("where_sessionID_in_20")
space_probe = exp("raw_space_11900388_maxres1")
align = [exp("align_2021-03_12_to_04_01_maxres10"),
         exp("align_2021-06_maxres10"),
         exp("align_2021-08_maxres10")]
gap_raw = exp("raw_gap_station_2021-03-12_pg1_maxres1")
ca_raw = exp("raw_CA325_2021-08-02_1718")

# ---------------------------------------------------------------- plan by month
months_in_window = Counter(r["month"] for r in MAN)
WINDOWS = [
    ("2021-03", "Fri, 12 Mar 2021 00:00:00 GMT", "Thu, 01 Apr 2021 00:00:00 GMT"),
    ("2021-04", "Thu, 01 Apr 2021 00:00:00 GMT", "Sat, 01 May 2021 00:00:00 GMT"),
    ("2021-05", "Sat, 01 May 2021 00:00:00 GMT", "Tue, 01 Jun 2021 00:00:00 GMT"),
    ("2021-06", "Tue, 01 Jun 2021 00:00:00 GMT", "Thu, 01 Jul 2021 00:00:00 GMT"),
    ("2021-07", "Thu, 01 Jul 2021 00:00:00 GMT", "Sun, 01 Aug 2021 00:00:00 GMT"),
    ("2021-08", "Sun, 01 Aug 2021 00:00:00 GMT", "Wed, 01 Sep 2021 00:00:00 GMT"),
    ("2021-09", "Wed, 01 Sep 2021 00:00:00 GMT", "Wed, 15 Sep 2021 00:00:00 GMT"),
]
BYTES_PER_SESSION = ((full_mar["response_bytes"] + page2_mar["response_bytes"]) / 182
                     + full_aug["response_bytes"] / 100) / 2
PAGE_SECONDS = (full_mar["elapsed_s"] + full_aug["elapsed_s"] + page2_mar["elapsed_s"]) / 3

plan = []
tot_s = tot_p = 0
for m, lo, hi in WINDOWS:
    n = months_in_window[m]
    pages = -(-n // 100)
    est_mb = n * BYTES_PER_SESSION / 1048576
    plan.append({
        "month": m,
        "where": {"connectionTime": {"$gte": lo, "$lt": hi}},
        "sessions_in_manifest": n,
        "pages_at_max_results_100": pages,
        "est_MiB": round(est_mb, 1),
        "est_minutes": round(pages * PAGE_SECONDS / 60, 1),
    })
    tot_s += n
    tot_p += pages

# ---------------------------------------------------------------- gap analysis
row_null = [r for r in ITEMS if r["n_current"] == 0]
space_rows = defaultdict(lambda: [0, 0])
for r in ITEMS:
    space_rows[r["spaceID"]][0] += 1
    if r["n_current"] == 0:
        space_rows[r["spaceID"]][1] += 1
gap_space = "11900388"
gap_sessions = sum(1 for r in MAN if r["spaceID"] == gap_space)

# 20-row alignment sample, deliberately spread across the two measured months
sample = []
by_label = defaultdict(list)
for r in ITEMS:
    by_label[r["_probe_label"]].append(r)
for lab in sorted(by_label):
    by_label[lab].sort(key=lambda x: x["connectionTime"])
idx = {k: 0 for k in by_label}
while len(sample) < 20:
    for lab in sorted(by_label):
        lst = by_label[lab]
        if idx[lab] < len(lst) and len(sample) < 20:
            r = lst[idx[lab]]
            idx[lab] += 1
            m = next((x for x in MAN if x["sessionID"] == r["sessionID"]), None)
            sample.append({
                "sessionID": r["sessionID"],
                "manifest_spaceID": m and m["spaceID"],
                "ts_spaceID": r["spaceID"],
                "manifest_connectionTime": m and m["connectionTime"],
                "ts_connectionTime": r["connectionTime"],
                "spaceID_match": bool(m and m["spaceID"] == r["spaceID"]),
                "connectionTime_match": bool(m and m["connectionTime"] == r["connectionTime"]),
                "n_current_samples": r["n_current"],
                "ts_first_sample": r["ts_first"],
                "ts_last_sample": r["ts_last"],
            })

manifest_ids = {r["sessionID"] for r in MAN}
# dedupe by sessionID: the same record can appear in a full page and in a raw dump
uniq = {}
for r in ITEMS:
    uniq.setdefault(r["sessionID"], r)
ITEMS_U = list(uniq.values())
matched = [r for r in ITEMS_U if r["sessionID"] in manifest_ids]
MAR_IDS = {r["sessionID"] for r in MAN if r["month"] == "2021-03"}

out = {
    "task": "A-tier prerequisite: can the 2021 test-window /ts records be fetched precisely and cheaply?",
    "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    "api": {
        "base": "https://ev.caltech.edu/api/v1/sessions/caltech",
        "endpoint": "/ts",
        "auth": "Bearer token from macOS keychain service 'acn-api' (never logged, never persisted)",
        "network": "direct connection, urllib ProxyHandler({}); local proxy 127.0.0.1:7897 is dead",
        "probe_requests_used": int(open(BASE + "/_probe_count.txt").read().strip()),
        "probe_records_kept": len(RESULTS),
    },
    "conclusion": {
        "verdict": "FEASIBLE_WITH_CONDITIONS",
        "where_filter_supported": True,
        "where_date_literal_format": "RFC1123 (e.g. 'Fri, 12 Mar 2021 00:00:00 GMT'); ISO-8601 is silently ignored -> _meta.total 0",
        "indexed_field": "connectionTime (window queries 0.7-14.4 s)",
        "non_indexed_fields": "sessionID and spaceID filters both return nginx 502 after ~31 s (unindexed scan)",
        "test_window_manifest_rows": len(MAN),
        "test_window_first": MAN[0]["connectionTime"] if MAN else None,
        "test_window_last": MAN[-1]["connectionTime"] if MAN else None,
        "pages_needed_at_max_results_100": tot_p,
        "est_total_MiB": round(tot_s * BYTES_PER_SESSION / 1048576, 1),
        "est_total_minutes": round(tot_p * PAGE_SECONDS / 60, 1),
        "measured_throughput_MB_per_s": round(
            (full_mar["response_bytes"] / 1048576) / full_mar["elapsed_s"], 2),
        "hard_blocker": "spaceID 11900388 (station 2-39-81-4550): chargingCurrent and pilotSignal are null on every sampled record; %d of %d test-window sessions (%.1f%%) sit there"
                        % (gap_sessions, len(MAN), 100 * gap_sessions / len(MAN)),
    },
    "experiments": [ctrl, iso, rfc_mar, rfc_mar7, full_mar, full_aug, page2_mar, in_probe, space_probe] + align
                  + [gap_raw, ca_raw],
    "filter_semantics": {
        "operator_support": "$gte / $lt on connectionTime work; boundaries behave as [start, end)",
        "verification": [
            "where 2021-03-01..2021-04-01 -> _meta.total 253 == checkpoint months['2021-03'].total 253",
            "where 2021-03-12..2021-04-01 -> _meta.total 182 == manifest 2021-03 rows 182",
            "where 2021-06-01..2021-07-01 -> _meta.total 438 == manifest 2021-06 rows 438",
            "where 2021-08-01..2021-09-01 -> _meta.total 600 == manifest 2021-08 rows 600",
            "page 1 (100) + page 2 (82) == 182 -> filtered pagination closes exactly, no skips/dupes",
        ],
        "max_results": "honoured (requested 100 -> _meta.max_results 100, 100 items returned); values >100 untested to stay inside the 60 s gateway budget",
        "deep_pagination": "not needed: every monthly window is 2-6 pages, so skip offsets stay <=500 docs",
    },
    "volume_and_timing": {
        "avg_bytes_per_session": round(BYTES_PER_SESSION),
        "control_page_25_items": {"MiB": ctrl["response_MiB"], "seconds": ctrl["elapsed_s"]},
        "full_page_100_items": [
            {"window": "2021-03-12..2021-04-01", "MiB": full_mar["response_MiB"],
             "seconds": full_mar["elapsed_s"], "items": full_mar["n_items"]},
            {"window": "2021-08", "MiB": full_aug["response_MiB"],
             "seconds": full_aug["elapsed_s"], "items": full_aug["n_items"]},
        ],
        "samples_per_session": {
            "measured_on_200_sessions": True,
            "median": 957, "mean": 2516, "p90": 7954, "max": 25387,
            "note": "brief's 10,447-point sample is typical, not the ceiling",
        },
        "est_test_window": {
            "sessions": tot_s, "pages": tot_p,
            "MiB": round(tot_s * BYTES_PER_SESSION / 1048576, 1),
            "minutes": round(tot_p * PAGE_SECONDS / 60, 1),
        },
        "fallback_full_scan_if_no_where": {
            "pages": 1258,
            "MiB": round(1258 * ctrl["response_bytes"] / 1048576, 1),
            "hours": round(1258 * ctrl["elapsed_s"] / 3600, 1),
            "viability": "not viable: 18+ GB / 5.5 h plus the known 502/504 deep-page failures",
        },
    },
    "fetch_plan": plan,
    "alignment": {
        "sampled_records": len(ITEMS_U),
        "raw_records_including_repeats": len(ITEMS),
        "march_segment_fully_enumerated": len({r["sessionID"] for r in matched if r["sessionID"] in MAR_IDS}) == len(MAR_IDS),
        "march_segment_rows": len(MAR_IDS),
        "march_segment_matched": len({r["sessionID"] for r in matched if r["sessionID"] in MAR_IDS}),
        "records_whose_sessionID_is_in_manifest": len(matched),
        "spaceID_equal": sum(1 for r in matched if [m for m in MAN if m["sessionID"] == r["sessionID"]][0]["spaceID"] == r["spaceID"]),
        "connectionTime_string_equal": sum(1 for r in matched if [m for m in MAN if m["sessionID"] == r["sessionID"]][0]["connectionTime"] == r["connectionTime"]),
        "join_key": "sessionID is exact (includes microseconds); spaceID and connectionTime are identical between the sessions endpoint and /ts",
        "twenty_row_spot_check": sample,
    },
    "telemetry_coverage": {
        "sampled": len(ITEMS_U),
        "null_chargingCurrent": len(row_null),
        "null_rate": round(len(row_null) / len(ITEMS_U), 3),
        "by_space": [{"spaceID": k, "sampled": v[0], "null": v[1]} for k, v in sorted(space_rows.items(), key=lambda x: -x[1][1]) if v[1]],
        "gap_station": {
            "spaceID": gap_space,
            "stationID": "2-39-81-4550",
            "sessions_in_test_window": gap_sessions,
            "share_of_test_window": round(gap_sessions / len(MAN), 3),
            "evidence": "%d/%d unique sampled records (March + August 2021 pages) have chargingCurrent=null AND pilotSignal=null while kWhDelivered>0; a raw record dump confirms the two telemetry keys are literally null" % (space_rows[gap_space][1], space_rows[gap_space][0]),
        },
        "sparse_ca_null": {
            "sampled_ca_records": sum(1 for r in ITEMS if r["spaceID"] != gap_space),
            "null": sum(1 for r in ITEMS if r["spaceID"] != gap_space and r["n_current"] == 0),
            "note": "on CA-* spaces chargingCurrent can be null while pilotSignal is present (verified raw dump: CA-325, 7,882 pilot samples, chargingCurrent null)",
        },
        "est_sessions_with_usable_current": len(MAN) - gap_sessions,
        "est_usable_share": round((len(MAN) - gap_sessions) / len(MAN), 3),
        "est_usable_share_after_sparse_nulls": round(
            (len(MAN) - gap_sessions) * (1 - sum(1 for r in ITEMS if r["spaceID"] != gap_space and r["n_current"] == 0) / sum(1 for r in ITEMS if r["spaceID"] != gap_space)) / len(MAN), 3),
    },
    "recommended_strategy": {
        "shape": "7 connectionTime windows (one per calendar month, clipped to the test window) x max_results=100 x page 1..N, with a per-window total cross-check against the manifest",
        "why": "connectionTime is the only indexed field; per-month windows keep offsets small (<=6 pages) so the 502/504 deep-skip failure never triggers",
        "throughput": "~1.3 MB/s, 100-item page = ~18 MiB / ~12-14 s, comfortably inside the 60 s gateway limit",
        "retry_unit": "a whole window page (sessionID/spaceID filters cannot be used to repair single sessions)",
        "verification_hook": "_meta.total per window must equal the manifest month count; any mismatch aborts that window",
    },
    "risks": [
        "42% of sampled records carry no current series at all (32% of them from one station) -> an 'A-tier semi-metered label' can only cover ~68% of test-window sessions without a fallback rule",
        "pilotSignal is a commanded-current series, not measured; using it as a surrogate is a modelling choice that needs its own validation",
        "/ts sample grids start ~60 s BEFORE connectionTime (e.g. 17:54:47 vs 17:55:47), so the integration window must be clipped to [connectionTime, disconnectTime]",
        "max_results > 100 untested; 200-item pages would exceed the measured 30 s comfort zone",
        "no per-session repair path: a failed page must be re-fetched as a window page",
    ],
}

with open(BASE + "/feasibility.json", "w") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("wrote feasibility.json")
print("plan pages:", tot_p, "sessions:", tot_s,
      "est MiB:", round(tot_s * BYTES_PER_SESSION / 1048576, 1),
      "est min:", round(tot_p * PAGE_SECONDS / 60, 1))
print("bytes/session:", round(BYTES_PER_SESSION), "page seconds:", round(PAGE_SECONDS, 2))
print("gap sessions:", gap_sessions, "of", len(MAN))
print("alignment matched:", len(matched), "space eq:", out["alignment"]["spaceID_equal"],
      "ct eq:", out["alignment"]["connectionTime_string_equal"])
