"""SG-EXP-024: support-range sensitivity, not measured-power validation."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from analyze_demand_warning import sha256_file, write_json, write_csv
from evcs_station_graph.eventtime.data import FrozenData
from evcs_station_graph.data.visibility_v2 import proxy_targets, STEP

ROOT = Path(__file__).resolve().parents[1]


def completion_audit(frame, grid, nodes):
    selected = frame.loc[frame.spaceID.astype(str).isin(nodes)].copy()
    for field in ('connectionTime', 'disconnectTime', 'doneChargingTime'):
        selected[field] = pd.to_datetime(selected[field], utc=True, errors='coerce')
    c, d, done = (selected[k] for k in ('connectionTime', 'disconnectTime', 'doneChargingTime'))
    valid = done.notna() & (done > c) & (done <= d)
    rows = []
    for r, ok in zip(selected.itertuples(index=False), valid):
        lo = (r.connectionTime.value - int(grid[0])) // STEP
        hi = (r.disconnectTime.value - int(grid[0]) + STEP - 1) // STEP
        # Strictly after the last nonzero-current timestamp: equality is excluded.
        post_start = ((r.doneChargingTime.value - int(grid[0])) // STEP + 1) if ok else hi
        bins = max(0, hi - max(lo, post_start)) if ok else 0
        energy = float(r.kWhDelivered)
        rows.append(dict(sessionID=r.sessionID, node=r.spaceID, valid_completion=bool(ok),
                         original_bins=int(hi-lo), entirely_post_completion_bins=int(bins),
                         assigned_post_completion_kwh=energy*bins/(hi-lo) if hi > lo else 0.,
                         completed_to_disconnect_minutes=(r.disconnectTime-r.doneChargingTime).total_seconds()/60 if ok else None))
    original, _ = proxy_targets(selected, grid, nodes)
    alternative = selected.copy()
    alternative.loc[valid, 'disconnectTime'] = done[valid]
    revised, _ = proxy_targets(alternative, grid, nodes)
    result = dict(selected_sessions=len(selected), valid_completion=int(valid.sum()),
                  missing_completion=int(done.isna().sum()), invalid_nonmissing_completion=int((done.notna() & ~valid).sum()),
                  valid_with_post_completion_bins=sum(r['entirely_post_completion_bins'] > 0 for r in rows),
                  total_energy_kwh=float(selected.kWhDelivered.sum()),
                  valid_completion_energy_kwh=float(selected.loc[valid, 'kWhDelivered'].sum()),
                  energy_assigned_strictly_after_completion_kwh=sum(r['assigned_post_completion_kwh'] for r in rows),
                  median_completed_to_disconnect_minutes=float(np.median([r['completed_to_disconnect_minutes'] for r in rows if r['valid_completion']])),
                  original_sum_kwh=float(original.sum()), alternative_sum_kwh=float(revised.sum()),
                  reconstruction_mean_absolute_difference_kwh_per_bin=float(np.abs(revised-original).mean()),
                  max_node_energy_difference_kwh=float(np.abs(revised.sum(axis=0)-original.sum(axis=0)).max()),
                  interpretation='Session support-range artifact and alternative reconstruction sensitivity, NOT measured power error or model MAE bias.')
    return result, rows, original, revised


def main():
    cfg = json.loads((ROOT/'configs/analysis/SG-EXP-023-independent-calibration.json').read_text())
    raw = Path(cfg['raw_sessions'])
    out = ROOT/'outputs/analysis/SG-EXP-024-proxy-engineering'
    if out.exists():
        raise FileExistsError(out)
    data = FrozenData(ROOT/cfg['data'])
    frame = pd.read_csv(raw)
    sources = {str(raw): sha256_file(raw), cfg['data']: data.digest,
               'scripts/audit_proxy_engineering.py': sha256_file(Path(__file__))}
    stats, sessions, original, alternative = completion_audit(frame, data.arrays['timestamps_ns'], data.arrays['node_ids'].tolist())
    if not np.allclose(original, data.arrays['targets'], atol=1e-12, rtol=0):
        raise ValueError('Original reconstruction no longer matches frozen target')
    if stats['max_node_energy_difference_kwh'] > 1e-7:
        raise ValueError('Alternative reconstruction violates energy conservation')
    inventory = []
    for p in sorted(raw.parent.glob('acn_caltech_*.csv')):
        f = pd.read_csv(p)
        inventory.append(dict(file=p.name, rows=len(f), connection_min=f.connectionTime.min() if len(f) else None,
                              connection_max=f.connectionTime.max() if len(f) else None, sha256=sha256_file(p)))
        sources[str(p)] = sha256_file(p)
    stats.update(time_series_true_rows=int(frame.has_time_series.astype(str).str.lower().eq('true').sum()),
                 actual_reporting_delay_available=False,
                 real_measurement_validation_completed=False, genuine_new_period_available=False)
    out.mkdir(parents=True)
    write_json(out/'summary.json', stats)
    write_csv(out/'session_support_audit.csv', sessions)
    write_csv(out/'yearly_inventory.csv', inventory)
    np.savez_compressed(out/'alternative_reconstruction.npz', timestamps_ns=data.arrays['timestamps_ns'],
                        node_ids=data.arrays['node_ids'], original=original, completion_support=alternative)
    write_json(out/'sources.json', sources)
    write_json(out/'manifest.json', {p.name: sha256_file(p) for p in out.iterdir() if p.is_file()})
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
