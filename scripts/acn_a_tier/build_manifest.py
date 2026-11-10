"""Build the test-window manifest from the ACN sessions checkpoint (local only)."""
import csv
import json
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

CK = ".cache/acn-audit-20261102/checkpoint_caltech_windowed.json"
OUT = ".cache/acn-a-tier/test_window_manifest.csv"
LO = datetime(2021, 3, 12, 0, 0, 0, tzinfo=timezone.utc)
HI = datetime(2021, 9, 14, 23, 59, 59, tzinfo=timezone.utc)


def norm_sid(sid):
    """Static ACN CSVs use '<cluster>_<...>_<station>_<timestamp>' style slugs."""
    s = sid.strip().replace(" ", "T").replace(":", "-").replace(".", "-")
    s = re.sub(r"[^0-9A-Za-z_\-]+", "_", s)
    return s.lower()


def main():
    d = json.load(open(CK))
    rows = d["rows"]
    sel = []
    for sid, v in rows.items():
        raw = v.get("connectionTime")
        try:
            dt = parsedate_to_datetime(raw).astimezone(timezone.utc)
        except Exception:
            continue
        if LO <= dt <= HI:
            sel.append((sid, v.get("spaceID"), raw, dt))
    sel.sort(key=lambda x: x[3])
    with open(OUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["sessionID", "slug", "spaceID", "connectionTime", "month"])
        for sid, space, raw, dt in sel:
            w.writerow([sid, norm_sid(sid), space, raw, dt.strftime("%Y-%m")])
    print("wrote", OUT, len(sel), "rows")
    print("first", sel[0][3].isoformat(), "last", sel[-1][3].isoformat())
    # 20-session sample spread over months for the alignment probe
    by_month = {}
    for sid, space, raw, dt in sel:
        by_month.setdefault(dt.strftime("%Y-%m"), []).append(sid)
    sample = []
    months = sorted(by_month)
    i = 0
    while len(sample) < 20:
        m = months[i % len(months)]
        bucket = by_month[m]
        if bucket:
            sample.append(bucket[(i * 7) % len(bucket)])
        i += 1
        if i > 500:
            break
    sample = list(dict.fromkeys(sample))[:20]
    json.dump(sample, open(".cache/acn-a-tier/_sample_sids.json", "w"), indent=0)
    print("sample", len(sample))


if __name__ == "__main__":
    main()
