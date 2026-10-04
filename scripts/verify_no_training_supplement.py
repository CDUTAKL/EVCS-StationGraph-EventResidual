"""Independent full-sort and scalar arithmetic audit of SG-EXP-024/025."""
import json
import math
from fractions import Fraction
from pathlib import Path
import numpy as np
import pandas as pd
from analyze_demand_warning import sha256_file, write_json

ROOT = Path(__file__).resolve().parents[1]


def main():
    cfg = json.loads((ROOT/'configs/analysis/SG-EXP-025-rolling-calibration.json').read_text())
    roll = ROOT/cfg['output']
    eng = ROOT/'outputs/analysis/SG-EXP-024-proxy-engineering'
    source_checks = 0
    for directory in (eng, roll):
        for name, digest in json.loads((directory/'manifest.json').read_text()).items():
            assert sha256_file(directory/name) == digest, name
        for name, digest in json.loads((directory/'sources.json').read_text()).items():
            assert sha256_file(ROOT/name) == digest, name
            source_checks += 1
    # Recheck every original formal run artifact, not just this analysis' six NPZs.
    original_checks = 0
    for folder in (ROOT/'outputs/recovered/SG-EXP-019/unpacked/results/formal').glob('*/seed-*'):
        for name, digest in json.loads((folder/'manifest.json').read_text()).items():
            assert sha256_file(folder/name) == digest, str(folder/name)
            original_checks += 1
    raw_cfg = json.loads((ROOT/'configs/analysis/SG-EXP-023-independent-calibration.json').read_text())
    raw = pd.read_csv(raw_cfg['raw_sessions'])
    with np.load(ROOT/cfg['data'], allow_pickle=False) as f:
        times, maturity_all, nodes = f['timestamps_ns'], f['label_available_at_ns'], f['node_ids']
    total = 0.
    for r in raw.loc[raw.spaceID.isin(nodes)].itertuples(index=False):
        c, d, done = (pd.to_datetime(x, utc=True) for x in (r.connectionTime, r.disconnectTime, r.doneChargingTime))
        if pd.notna(done) and c < done <= d:
            lo = math.floor((c.value-int(times[0]))/900_000_000_000)
            hi = math.ceil((d.value-int(times[0]))/900_000_000_000)
            # Count bins independently, rather than reuse the analytical formula.
            count = sum(int(times[0])+i*900_000_000_000 > done.value for i in range(lo, hi))
            total += float(r.kWhDelivered)*count/(hi-lo)
    assert abs(total-json.loads((eng/'summary.json').read_text())['energy_assigned_strictly_after_completion_kwh']) < 1e-8
    trace = pd.read_csv(roll/'daily_quantiles.csv')
    metric = pd.read_csv(roll/'metrics_by_seed.csv')
    records, max_gap, metric_gap = 0, 0., 0.
    for seed in cfg['seeds']:
        folder = ROOT/cfg['source_root']/f'seed-{seed}'
        arrays = []
        for split in ('calibration', 'test'):
            with np.load(folder/f'predictions_{split}.npz', allow_pickle=False) as f:
                arrays.append({k: f[k] for k in f.files})
        cal, test = arrays
        starts = np.concatenate([a['target_timestamps_ns'] for a in arrays])
        issues = np.concatenate([a['origin_cutoff_ns'] for a in arrays])
        origins = np.concatenate([a['origins'] for a in arrays])
        errors = np.concatenate([np.abs(a['y_true']-a['y_pred']) for a in arrays])
        trigger = np.concatenate([a['rule_trigger'] for a in arrays])
        available = maturity_all[origins[:, None]+np.arange(1, 5)]
        with np.load(roll/f'interval_halfwidths_seed-{seed}.npz', allow_pickle=False) as f:
            saved = {k: f[k] for k in f.files}
        for (days, cutoff), group in trace[trace.seed == seed].groupby(['days', 'cutoff_ns']):
            eligible = np.zeros_like(errors, bool)
            # Independent explicit horizon/node predicates.
            for h in range(4):
                for n in range(10):
                    eligible[:, h, n] = ((starts[:, h] >= cutoff-int(days)*86400_000_000_000) &
                                         (starts[:, h]+900_000_000_000 <= cutoff) &
                                         (issues < cutoff) & (available[:, h, n] < cutoff))
            for r in group.itertuples(index=False):
                selection = eligible & trigger if r.group == 'triggered' else eligible[:, :, r.node]
                if r.group == 'stable':
                    selection = selection & ~trigger[:, :, r.node]
                values = errors[selection] if r.node == -1 else errors[:, :, r.node][selection]
                n = len(values)
                assert n == r.n
                if n:
                    rank = math.ceil(Fraction(n+1)*Fraction(9, 10))
                    expected = np.sort(values)[rank-1] if rank <= n else math.inf
                    assert rank == r.rank
                    max_gap = max(max_gap, abs(expected-r.q))
                    assert np.isclose(expected, r.q, atol=1e-12, rtol=0)
                else:
                    # The fallback must itself be mature and independent of test.
                    assert np.max(available[:len(cal['origins'])]) < cutoff
                    ce = errors[:len(cal['origins'])]
                    ct = cal['rule_trigger']
                    values = ce[ct] if r.node == -1 else ce[:, :, r.node][~ct[:, :, r.node]] if r.group == 'stable' else ce[:, :, r.node].ravel()
                    rank = math.ceil(Fraction(len(values)+1)*Fraction(9, 10))
                    expected = np.sort(values)[rank-1] if rank <= len(values) else math.inf
                    assert np.isclose(expected, r.q, atol=1e-12, rtol=0)
                selected = saved['daily_cutoff_ns'] == cutoff
                key = ('node_standard' if r.group == 'node_standard' else 'behavior_rule')+f'_{int(days)}d'
                if r.node == -1:
                    emitted = saved[key][selected][test['rule_trigger'][selected]]
                elif r.group == 'stable':
                    emitted = saved[key][selected, :, r.node][~test['rule_trigger'][selected, :, r.node]]
                else:
                    emitted = saved[key][selected, :, r.node].ravel()
                assert np.allclose(emitted, expected, atol=1e-12, rtol=0)
                records += 1
        err = np.abs(test['y_true']-test['y_pred'])
        for r in metric[(metric.seed == seed) & metric.group.isin(['all', 'event', 'stable', 'cell11', 'cell10'])].itertuples(index=False):
            event, tr = test['target_event'], test['rule_trigger']
            m = {'all': np.ones_like(event), 'event': event, 'stable': ~event,
                 'cell11': event & tr, 'cell10': event & ~tr}[r.group]
            q = saved[('node_standard' if r.method == 'node_standard' else 'behavior_rule')+f'_{r.days}d'][m]
            e = err[m]
            covered = ((test['y_true'] >= test['y_pred']-saved[('node_standard' if r.method == 'node_standard' else 'behavior_rule')+f'_{r.days}d']) &
                       (test['y_true'] <= test['y_pred']+saved[('node_standard' if r.method == 'node_standard' else 'behavior_rule')+f'_{r.days}d']))[m]
            for actual, expected in [(covered.mean(), r.coverage), ((2*q).mean(), r.width),
                                     ((2*q+20*np.maximum(e-q, 0)).mean(), r.interval_score)]:
                metric_gap = max(metric_gap, abs(actual-expected))
                assert np.isclose(actual, expected, atol=1e-12, rtol=0)
    result = dict(status='PASS', original_formal_artifact_hashes=original_checks, source_hashes=source_checks,
                  independently_sorted_daily_quantiles=records, max_quantile_difference=max_gap,
                  max_interval_metric_difference=metric_gap, independently_counted_post_completion_kwh=total,
                  scientific_scope='Arithmetic and temporal eligibility verified; not measured-power or unseen-period validation')
    write_json(ROOT/'outputs/analysis/SG-EXP-024-025-independent-verification.json', result)
    print(result)


if __name__ == '__main__':
    main()
