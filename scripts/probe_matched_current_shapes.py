"""Ten predetermined matched-session current probes; no measured kWh claims.

One first positive-energy May-2018 session per frozen thesis node. Files are
read in memory only. Charge/current shape is normalized; unavailable voltage
and power fields are not manufactured from current. No population inference.
"""
from pathlib import Path
import gzip
import hashlib
import io
import json
import urllib.parse
import urllib.request
import numpy as np
import pandas as pd
from analyze_demand_warning import sha256_file, write_json, write_csv

ROOT = Path(__file__).resolve().parents[1]


def current_shape(frame, connection, disconnect):
    time = pd.to_datetime(frame.iloc[:, 0], utc=True).astype('int64').to_numpy()
    current = pd.to_numeric(frame['Charging Current (A)'], errors='raise').to_numpy(float)
    if len(time) < 2 or np.any(np.diff(time) <= 0) or not np.isfinite(current).all() or np.any(current < 0):
        raise ValueError('Invalid current/time trace')
    c, d = pd.Timestamp(connection).value, pd.Timestamp(disconnect).value
    if abs(time[0]-c) > 60e9 or abs(time[-1]-d) > 60e9:
        raise ValueError('Trace does not cover the matched session within 60 seconds')
    seconds = (time-time[0])/1e9
    integral = np.r_[0., np.cumsum(current[:-1]*np.diff(seconds))]
    if integral[-1] <= 0 or np.max(np.diff(seconds)) > 60:
        raise ValueError('No current integral or long sampling gap')
    step = 900_000_000_000
    start, end = (c//step)*step, ((d+step-1)//step)*step
    edges = np.arange(start, end+step, step, dtype=np.int64)
    # Piecewise-constant left-sample current; area is linear inside each gap.
    area = np.interp((edges-time[0])/1e9, seconds, integral, left=0., right=integral[-1])
    fraction = np.diff(area)/integral[-1]
    uniform = np.full(len(fraction), 1/len(fraction))
    return dict(bins=len(fraction), current_amp_seconds=float(integral[-1]),
                maximum_sampling_gap_seconds=float(np.max(np.diff(seconds))),
                missing_voltage_rows=int(frame['Voltage (V)'].isna().sum()),
                missing_power_rows=int(frame['Power (kW)'].isna().sum()),
                normalized_shape_total_variation=float(.5*np.abs(fraction-uniform).sum()),
                peak_bin_fraction_ratio_to_uniform=float(fraction.max()*len(fraction))), fraction, edges[:-1]


def main():
    out = ROOT/'outputs/analysis/SG-EXP-024-matched-current-probe'
    if out.exists():
        raise FileExistsError(out)
    cfg = json.loads((ROOT/'configs/analysis/SG-EXP-023-independent-calibration.json').read_text())
    raw = Path(cfg['raw_sessions'])
    f = pd.read_csv(raw)
    with np.load(ROOT/cfg['data'], allow_pickle=False) as frozen:
        nodes = frozen['node_ids'].tolist()
    selected = []
    for node in nodes:
        candidates = f[(f.spaceID == node) & (f.connectionTime >= '2018-05-01') &
                       (f.connectionTime < '2018-06-01') & (f.kWhDelivered > 0)].sort_values(['connectionTime', 'sessionID'])
        if not len(candidates):
            raise ValueError('No predetermined eligible May session: '+node)
        selected.append(candidates.iloc[0])
    out.mkdir(parents=True)
    selection = [dict(node=r.spaceID, sessionID=r.sessionID, connectionTime=r.connectionTime,
                      disconnectTime=r.disconnectTime, kWhDelivered=float(r.kWhDelivered)) for r in selected]
    # Freeze sample list before contacting any file server.
    write_json(out/'selection.json', dict(rule='first chronological positive-energy May-2018 session per frozen node', sessions=selection))
    rows, profiles = [], []
    for r in selected:
        filename = r.sessionID.replace('_', '-').replace(' ', 'T').replace(':', '-').replace('.', '-')+'.csv.gz'
        row = dict(node=r.spaceID, sessionID=r.sessionID, status='UNAVAILABLE', errors=[])
        for site in ('California_Garage_01', 'California_Garage_02', 'N_Wilson_Garage_01', 'S_Wilson_Garage_01', 'LIGO_01'):
            path = 'time series data/caltech/'+site+'/'+filename
            url = 'https://raw.githubusercontent.com/tongxin-li/ACN-Data-Static/main/'+urllib.parse.quote(path)
            try:
                with urllib.request.urlopen(url, timeout=15) as response:
                    blob = response.read(2_000_001)
                if len(blob) > 2_000_000:
                    raise ValueError('Sample exceeds 2MB guard')
                frame = pd.read_csv(io.BytesIO(gzip.decompress(blob)))
                stats, fractions, times = current_shape(frame, r.connectionTime, r.disconnectTime)
                row.update(status='MATCHED_CURRENT_SHAPE_ONLY', url=url, sha256=hashlib.sha256(blob).hexdigest(), rows=len(frame), **stats)
                profiles.extend(dict(node=r.spaceID, target_bin_start_ns=int(t),
                                     normalized_current_fraction=float(p), uniform_proxy_fraction=1/len(fractions)) for t, p in zip(times, fractions))
                break
            except Exception as e:
                row['errors'].append(dict(location=site, error=type(e).__name__, detail=str(e)[:100]))
        rows.append(row)
        print(r.spaceID, row['status'], flush=True)
    sources = {str(raw): sha256_file(raw), cfg['data']: sha256_file(ROOT/cfg['data']),
               'scripts/probe_matched_current_shapes.py': sha256_file(Path(__file__))}
    write_json(out/'sample_metadata.json', rows)
    write_csv(out/'normalized_bin_shapes.csv', profiles)
    write_json(out/'summary.json', dict(selected_sessions=10, matched_sessions=sum(r['status'] == 'MATCHED_CURRENT_SHAPE_ONLY' for r in rows),
                                      selection='predetermined convenience sample, not representative',
                                      actual_metered_kwh_validation=False, unseen_period_validation=False,
                                      measured_quantity='charging current in A; normalized integrated current, not energy',
                                      raw_files_saved=False))
    write_json(out/'sources.json', sources)
    write_json(out/'manifest.json', {p.name: sha256_file(p) for p in out.iterdir()})


if __name__ == '__main__':
    main()
