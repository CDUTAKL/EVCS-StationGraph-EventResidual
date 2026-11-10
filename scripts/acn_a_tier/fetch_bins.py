#!/usr/bin/env python3
"""A-tier: fetch /ts for the 2021 test window on the 10 thesis nodes and build
15-min semi-metered labels. Raw arrays are never persisted; only binned energy."""
import base64, csv, json, subprocess, sys, time, urllib.parse, urllib.request, urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path
from collections import defaultdict

ROOT = Path("/Users/xushuyuan/Documents/Codex/EVCS-StationGraph-EventResidual")
OUT = ROOT/".cache/acn-a-tier"
NODES = {"CA-303","CA-304","CA-305","CA-307","CA-311","CA-315","CA-317","CA-321","CA-327","CA-489"}
API = "https://ev.caltech.edu/api/v1/sessions/caltech/ts"
OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
FMT = "%a, %d %b %Y %H:%M:%S GMT"

def token():
    r = subprocess.run(["security","find-generic-password","-s","acn-api","-w"], capture_output=True, text=True)
    if r.returncode != 0: raise SystemExit("keychain item acn-api not found")
    return r.stdout.strip()

def fetch(url, auth):
    req = urllib.request.Request(url, headers={"Authorization": auth, "User-Agent":"acn-a-tier/1.0"})
    for attempt in range(4):
        try:
            with OP.open(req, timeout=120) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code in (429,500,502,503,504) and attempt < 3:
                time.sleep(2*(attempt+1)); continue
            raise
        except Exception:
            if attempt < 3: time.sleep(2*(attempt+1)); continue
            raise
    raise RuntimeError("unreachable")

def month_windows():
    y,m = 2021,3
    while (y,m) <= (2021,9):
        ny,nm = (y+1,1) if m==12 else (y,m+1)
        fmt = lambda Y,M,D: datetime(Y,M,D,tzinfo=timezone.utc).strftime(FMT)
        yield f"{y}-{m:02d}", fmt(y,m,1), fmt(ny,nm,1)
        y,m = ny,nm

def bins_for(rec, v_fixed=208.0, crop=None):
    cc = rec.get("chargingCurrent") or {}
    ts, cur = cc.get("timestamps"), cc.get("current")
    if not ts or not cur or len(ts) < 2: return None
    pairs = []
    for t, c in zip(ts, cur):
        if c is None: continue
        try: pairs.append((datetime.strptime(t, FMT).replace(tzinfo=timezone.utc), float(c)))
        except ValueError: continue
    if len(pairs) < 2: return None
    pairs.sort(key=lambda x: x[0])
    amp_s = 0.0; per_bin = defaultdict(float)
    for (t0,c0),(t1,_) in zip(pairs, pairs[1:]):
        dt = (t1-t0).total_seconds()
        if dt <= 0 or dt > 300: continue
        amp_s += c0*dt
        b = t0.replace(minute=(t0.minute//15)*15, second=0, microsecond=0)
        per_bin[b] += c0*dt
    if amp_s <= 0: return None
    kwh = float(rec.get("kWhDelivered") or 0.0)
    v_eff = (kwh*3.6e6/amp_s) if kwh > 0 else None
    out = {}
    lo, hi = (crop or (None, None))
    for b, a in per_bin.items():
        if lo is not None and b < lo: continue
        if hi is not None and b > hi: continue
        out[b] = {"e208": a*v_fixed/3.6e6,
                  "eeff": (a*v_eff/3.6e6) if v_eff else None}
    return {"bins": out, "amp_s": amp_s, "implied_v": v_eff, "n_samples": len(pairs)}

def main():
    manifest = {}
    with (OUT/"test_window_manifest.csv").open() as f:
        for row in csv.DictReader(f):
            if row["spaceID"] in NODES:
                manifest[row["sessionID"]] = row
    print("target sessions on 10 nodes:", len(manifest), flush=True)
    auth = "Basic " + base64.b64encode((token()+":").encode()).decode()
    done = set()
    bins_path = OUT/"bins.csv"
    stats_path = OUT/"session_stats.csv"
    if bins_path.exists():
        with bins_path.open() as f:
            for row in csv.DictReader(f): done.add(row["sessionID"])
        print("already done:", len(done), flush=True)
    new_bins = not bins_path.exists()
    fb = bins_path.open("a", newline=""); wb = csv.writer(fb)
    if new_bins: wb.writerow(["sessionID","spaceID","bin_start_utc","e208_kwh","eeff_kwh","uniform_kwh"])
    fs = stats_path.open("a", newline=""); ws = csv.writer(fs)
    if stats_path.exists() and stats_path.stat().st_size == 0 or not stats_path.exists():
        ws.writerow(["sessionID","spaceID","kWhDelivered","n_bins","n_samples","implied_v","int_kwh_208","int_kwh_eff","rel_err_208","rel_err_eff"])
    found = 0
    for label, start, end in month_windows():
        page = 1
        while True:
            where = {"connectionTime": {"$gte": start, "$lt": end}}
            url = API + "?" + urllib.parse.urlencode({"page": page, "max_results": 100, "where": json.dumps(where)})
            try:
                obj = fetch(url, auth)
            except Exception as exc:
                print(f"{label} page {page} FAILED {type(exc).__name__}", flush=True); break
            if page == 1:
                total = int((obj.get("_meta") or {}).get("total", 0))
                if total <= 0:
                    raise SystemExit(f"{label}: where returned total=0 (RFC1123 literal required)")
                print(f"{label}: total={total}", flush=True)
            items = obj.get("_items", [])
            if not items: break
            for rec in items:
                sid = str(rec.get("sessionID") or "")
                if sid not in manifest or sid in done: continue
                try:
                    _c = datetime.strptime(manifest[sid]["connectionTime"], FMT).replace(tzinfo=timezone.utc)
                    _d = datetime.strptime(rec["disconnectTime"], FMT).replace(tzinfo=timezone.utc)
                    _lo = _c.replace(minute=(_c.minute//15)*15, second=0, microsecond=0)
                    _hi = _d.replace(minute=(_d.minute//15)*15, second=0, microsecond=0)
                except Exception:
                    _lo, _hi = None, None
                res = bins_for(rec, crop=(_lo, _hi))
                if not res:
                    with open(OUT/"no_current.csv","a",newline="") as fn:
                        csv.writer(fn).writerow([sid, manifest[sid]["spaceID"], rec.get("connectionTime")])
                    done.add(sid); continue
                row = manifest[sid]
                n_bins = None
                kwh = float(rec.get("kWhDelivered") or 0.0)
                # uniform allocation over connect..disconnect touched bins
                try:
                    c = datetime.strptime(row["connectionTime"], FMT).replace(tzinfo=timezone.utc)
                    d = datetime.strptime(rec["disconnectTime"], FMT).replace(tzinfo=timezone.utc)
                    nb = int((d - c).total_seconds()//900) + 1
                    nb = max(nb, 1); n_bins = nb
                    u = kwh/nb
                except Exception:
                    u = None
                for b, vals in res["bins"].items():
                    wb.writerow([sid, row["spaceID"], b.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                 f"{vals['e208']:.8f}",
                                 "" if vals["eeff"] is None else f"{vals['eeff']:.8f}",
                                 "" if u is None else f"{u:.8f}"])
                i208 = sum(v["e208"] for v in res["bins"].values())
                ieff = sum(v["eeff"] for v in res["bins"].values()) if res["implied_v"] else None
                ws.writerow([sid, row["spaceID"], kwh, n_bins, res["n_samples"],
                             "" if res["implied_v"] is None else f"{res['implied_v']:.2f}",
                             f"{i208:.6f}", "" if ieff is None else f"{ieff:.6f}",
                             "" if not kwh else f"{(i208-kwh)/kwh:.6f}",
                             "" if (ieff is None or not kwh) else f"{(ieff-kwh)/kwh:.6f}"])
                done.add(sid); found += 1
                if found % 25 == 0:
                    fb.flush(); fs.flush(); print(f"{label}: {found} sessions written (total {len(done)})", flush=True)
            page += 1
            if len(items) < 100: break
        fb.flush(); fs.flush()
        print(f"{label}: done, total {len(done)}/{len(manifest)}", flush=True)
    fb.close(); fs.close()
    print("FINISHED", len(done), "of", len(manifest), flush=True)

if __name__ == "__main__":
    main()
