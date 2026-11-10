"""Read-only feasibility probe for the ACN /ts endpoint (A-tier prerequisite).

Never prints or persists the API token / Authorization header.
Run:  python3 -B .cache/acn-a-tier/probe.py <experiment>
"""
import json
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://ev.caltech.edu/api/v1/sessions/caltech"
BUDGET_FILE = ".cache/acn-a-tier/_probe_count.txt"


def token():
    r = subprocess.run(
        ["security", "find-generic-password", "-s", "acn-api", "-w"],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        raise SystemExit("keychain lookup failed (rc=%d)" % r.returncode)
    return r.stdout.strip()


def opener():
    # local git proxy 127.0.0.1:7897 is dead -> force direct connection
    return urllib.request.build_opener(urllib.request.ProxyHandler({}))


def bump_budget():
    try:
        n = int(open(BUDGET_FILE).read().strip())
    except Exception:
        n = 0
    n += 1
    with open(BUDGET_FILE, "w") as f:
        f.write(str(n))
    return n


def probe(url, label, headers):
    """Issue one GET, return a measurement record."""
    n = bump_budget()
    op = opener()
    req = urllib.request.Request(url, headers=headers)
    t0 = time.time()
    rec = {"label": label, "url_no_token": url, "probe_index": n}
    try:
        with op.open(req, timeout=240) as resp:
            raw = resp.read()
            rec["status"] = resp.status
            rec["content_length_header"] = resp.headers.get("Content-Length")
    except urllib.error.HTTPError as e:
        raw = e.read()
        rec["status"] = e.code
    except Exception as e:  # timeout / connection reset
        rec["status"] = None
        rec["error"] = "%s: %s" % (type(e).__name__, e)
        raw = b""
    rec["elapsed_s"] = round(time.time() - t0, 2)
    rec["bytes"] = len(raw)
    rec["content_type"] = None
    body = None
    if raw:
        try:
            body = json.loads(raw.decode("utf-8", "replace"))
        except Exception:
            rec["body_head"] = raw[:400].decode("utf-8", "replace")
    if isinstance(body, dict):
        meta = body.get("_meta")
        if isinstance(meta, dict):
            rec["meta"] = {k: meta.get(k) for k in ("total", "max_results", "page")}
        items = body.get("_items")
        if isinstance(items, list):
            rec["n_items"] = len(items)
            rec["item_keys"] = sorted(items[0].keys()) if items else []
            rec["first_ids"] = [
                {k: it.get(k) for k in ("_id", "sessionID", "spaceID", "connectionTime") if k in it}
                for it in items[:3]
            ]
        elif "_items" in body:
            rec["n_items"] = 0
        if "issues" in body or "_issues" in body:
            rec["issues"] = body.get("issues") or body.get("_issues")
        if "_error" in body:
            rec["_error"] = body["_error"]
        # compact per-item metadata for the join/alignment check
        if isinstance(items, list) and items:
            rows = []
            for it in items:
                cc = it.get("chargingCurrent") or {}
                ps = it.get("pilotSignal") or {}
                ts = cc.get("timestamps") or []
                rows.append({
                    "sessionID": it.get("sessionID"),
                    "spaceID": it.get("spaceID"),
                    "connectionTime": it.get("connectionTime"),
                    "disconnectTime": it.get("disconnectTime"),
                    "stationID": it.get("stationID"),
                    "kWhDelivered": it.get("kWhDelivered"),
                    "n_current": len(cc.get("current") or []),
                    "n_timestamps": len(ts),
                    "n_pilot": len(ps.get("pilot") or ps.get("pilotSignal") or ps.get("current") or []),
                    "ts_first": ts[0] if ts else None,
                    "ts_last": ts[-1] if ts else None,
                })
            with open(".cache/acn-a-tier/items_probe.jsonl", "a") as f:
                for row in rows:
                    row["_probe_label"] = label
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return rec, body


def persist(records):
    with open(".cache/acn-a-tier/probe_results.jsonl", "a") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def main():
    which = sys.argv[1]
    tok = token()
    headers = {"Authorization": "Bearer " + tok, "Accept": "application/json"}
    out = []

    def base(params):
        # default percent-encoding of the JSON `where` payload (standard form)
        return BASE + "/ts?" + urllib.parse.urlencode(params)

    if which == "spec":
        # generic: argv[2] = JSON {"label":..., "params": {..}, "add_where": {...}}
        spec = json.loads(sys.argv[2])
        params = dict(spec.get("params", {}))
        if spec.get("add_where") is not None:
            params["where"] = json.dumps(spec["add_where"])
        rec, body = probe(base(params), spec["label"], headers)
        out.append(rec)
        if spec.get("dump_raw") and isinstance(body, dict):
            items = body.get("_items") or []
            if items:
                def sketch(v):
                    if isinstance(v, dict):
                        return {k: sketch(x) for k, x in v.items()}
                    if isinstance(v, list):
                        return {"__list_len__": len(v),
                                "__head__": [sketch(x) for x in v[:2]]}
                    return v
                with open(".cache/acn-a-tier/raw_item_sketch.json", "w") as f:
                    json.dump({"label": spec["label"], "n_items": len(items),
                               "item": sketch(items[0])}, f, ensure_ascii=False, indent=1)
        persist(out); print(json.dumps(out, indent=1))

    elif which == "control":
        # 1) whole-collection control page, default page size
        rec, body = probe(BASE + "/ts?page=1", "control_page1_default", headers)
        out.append(rec)
        persist(out); print(json.dumps(out, indent=1))

    elif which == "where_iso":
        lo, hi = "2021-03-01T00:00:00", "2021-04-01T00:00:00"
        w = json.dumps({"connectionTime": {"$gte": lo, "$lt": hi}})
        url = base({"page": 1, "max_results": 1000, "where": w})
        rec, body = probe(url, "where_connectionTime_ISO_2021-03", headers)
        out.append(rec)
        persist(out); print(json.dumps(out, indent=1))

    elif which == "where_rfc1123":
        lo, hi = "Mon, 01 Mar 2021 00:00:00 GMT", "Thu, 01 Apr 2021 00:00:00 GMT"
        w = json.dumps({"connectionTime": {"$gte": lo, "$lt": hi}})
        url = base({"page": 1, "max_results": 1000, "where": w})
        rec, body = probe(url, "where_connectionTime_RFC1123_2021-03", headers)
        out.append(rec)
        persist(out); print(json.dumps(out, indent=1))

    elif which == "where_space":
        w = json.dumps({"spaceID": "CA-496"})
        url = base({"page": 1, "where": w})
        rec, body = probe(url, "where_spaceID_CA-496", headers)
        out.append(rec)
        persist(out); print(json.dumps(out, indent=1))

    elif which == "follow":
        # run both a filtered month and its neighbour to prove the window really filters
        for label, lo, hi in [
            ("where_ISO_2021-04", "2021-04-01T00:00:00", "2021-05-01T00:00:00"),
            ("where_ISO_2021-02", "2021-02-01T00:00:00", "2021-03-01T00:00:00"),
        ]:
            w = json.dumps({"connectionTime": {"$gte": lo, "$lt": hi}})
            url = base({"page": 1, "max_results": 1000, "where": w})
            rec, body = probe(url, label, headers)
            out.append(rec)
        persist(out); print(json.dumps(out, indent=1))

    else:
        raise SystemExit("unknown experiment %r" % which)


if __name__ == "__main__":
    main()
