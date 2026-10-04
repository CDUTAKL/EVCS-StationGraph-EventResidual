"""Bounded public-file field probe; no private credentials or redistribution.

This office-site file is an acquisition demonstration, NOT a matched validation
sample for the thesis' Caltech nodes. Re-download is pinned by content hash.
"""
from pathlib import Path
import gzip
import hashlib
import io
import urllib.parse
import urllib.request
import pandas as pd
from analyze_demand_warning import write_json, sha256_file

ROOT = Path(__file__).resolve().parents[1]
FILE = 'time series data/office_01/Parking_Lot_01/19-102-260-1635-2019-10-31T14-21-10-330888.csv.gz'
EXPECTED = '374cc7aec1540354e1a020c23559b4fdc009ebd40e44f0064adee2196ede35fb'


def main():
    out = ROOT/'outputs/analysis/SG-EXP-024-public-measurement-probe.json'
    if out.exists():
        raise FileExistsError(out)
    url = 'https://raw.githubusercontent.com/tongxin-li/ACN-Data-Static/main/'+urllib.parse.quote(FILE)
    with urllib.request.urlopen(url, timeout=30) as response:
        blob = response.read(2_000_001)
    if len(blob) > 2_000_000 or hashlib.sha256(blob).hexdigest() != EXPECTED:
        raise ValueError('Public sample changed or exceeds bounded acquisition size')
    frame = pd.read_csv(io.BytesIO(gzip.decompress(blob)))
    times = pd.to_datetime(frame.iloc[:, 0], utc=True, errors='raise')
    required = ['Charging Current (A)', 'Voltage (V)', 'Power (kW)', 'Energy Delivered (kWh)']
    if not set(required).issubset(frame.columns):
        raise ValueError('Missing promised measurement columns')
    result = dict(status='PASS_ACQUISITION_ONLY', site='office_01', file=FILE, url=url,
                  bytes=len(blob), sha256=EXPECTED, rows=len(frame), columns=frame.columns.tolist(),
                  first_time=times.min().isoformat(), last_time=times.max().isoformat(),
                  timestamp_order_strict=bool((times.diff().dropna().dt.total_seconds() > 0).all()),
                  missing_measurements={k: int(frame[k].isna().sum()) for k in required},
                  matches_thesis_nodes=False, thesis_measured_power_validation=False,
                  new_period_validation=False, raw_sample_saved=False,
                  access='Public HTTP file; no token used',
                  redistribution_permission='No standalone repository license; official terms must be checked before redistribution',
                  script_sha256=sha256_file(Path(__file__)))
    write_json(out, result)
    print(result)


if __name__ == '__main__':
    main()
