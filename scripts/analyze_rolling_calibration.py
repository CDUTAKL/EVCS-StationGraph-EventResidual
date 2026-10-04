"""SG-EXP-025 daily rolling residuals with strict node-label maturity gates."""
from pathlib import Path
import json
import hashlib
import numpy as np
import pandas as pd
from analyze_demand_warning import sha256_file, write_json, write_csv
from analyze_independent_calibration import read_prediction, fit_halfwidths, order_quantile, masks, mean_sd
from evcs_station_graph.eventtime.data import FrozenData

ROOT = Path(__file__).resolve().parents[1]
STEP = 900_000_000_000
DAY = 86400_000_000_000


def eligible_mask(target_start, maturity, issue, cutoff, days):
    return ((target_start[:, :, None] >= cutoff-days*DAY) &
            (target_start[:, :, None]+STEP <= cutoff) &
            (maturity < cutoff) & (issue[:, None, None] < cutoff))


def fit_rolling(error, trigger, eligible, fallback, alpha):
    result, rows = dict(node_standard=[], stable=[]), []
    for name, restricted in [('node_standard', eligible), ('stable', eligible & ~trigger)]:
        for node in range(error.shape[2]):
            values = error[:, :, node][restricted[:, :, node]]
            if len(values):
                q, n, rank = order_quantile(values, alpha)
            else:
                q, n, rank = float(fallback[name][node]), 0, 0
            result[name].append(q)
            rows.append(dict(group=name, node=node, n=n, rank=rank, q=q, frozen_fallback=n == 0))
    values = error[eligible & trigger]
    if len(values):
        q, n, rank = order_quantile(values, alpha)
    else:
        q, n, rank = float(fallback['triggered']), 0, 0
    result['triggered'] = q
    rows.append(dict(group='triggered', node=-1, n=n, rank=rank, q=q, frozen_fallback=n == 0))
    return result, rows


def interval_stats(error, q, alpha):
    if not np.isfinite(error).all() or np.isnan(q).any() or np.any(q < 0):
        raise ValueError('Invalid interval arrays')
    return dict(coverage=float(np.mean(error <= q)), width=float(np.mean(2*q)),
                interval_score=float(np.mean(2*q+(2/alpha)*np.maximum(error-q, 0))),
                unbounded_fraction=float(np.mean(np.isinf(q))))


def main():
    config = ROOT/'configs/analysis/SG-EXP-025-rolling-calibration.json'
    cfg = json.loads(config.read_text())
    out = ROOT/cfg['output']
    if out.exists():
        raise FileExistsError(out)
    data = FrozenData(ROOT/cfg['data'])
    sources = {str(config.relative_to(ROOT)): sha256_file(config), cfg['data']: data.digest,
               'scripts/analyze_rolling_calibration.py': sha256_file(Path(__file__)),
               'scripts/analyze_independent_calibration.py': sha256_file(ROOT/'scripts/analyze_independent_calibration.py')}
    metric_rows, daily_rows = [], []
    out.mkdir(parents=True)
    for seed in cfg['seeds']:
        folder = ROOT/cfg['source_root']/f'seed-{seed}'
        cal = read_prediction(folder, 'calibration', data, sources)
        test = read_prediction(folder, 'test', data, sources)
        origins = np.r_[cal['origins'], test['origins']]
        times = np.concatenate([cal['target_timestamps_ns'], test['target_timestamps_ns']])
        issued = np.r_[cal['origin_cutoff_ns'], test['origin_cutoff_ns']]
        error = np.concatenate([np.abs(cal['y_true']-cal['y_pred']), np.abs(test['y_true']-test['y_pred'])])
        trigger = np.concatenate([cal['rule_trigger'], test['rule_trigger']])
        maturity = data.arrays['label_available_at_ns'][origins[:, None]+np.arange(1, 5)]
        dates = pd.to_datetime(test['origin_cutoff_ns'], utc=True).tz_convert(cfg['timezone']).normalize()
        cutoffs = dates.tz_convert('UTC').asi8
        months = dates.strftime('%Y-%m').to_numpy()
        fallback, _ = fit_halfwidths(error[:len(cal['origins'])], cal['rule_trigger'], cfg['alpha'])
        if np.max(maturity[:len(cal['origins'])]) >= cutoffs.min():
            raise ValueError('Frozen fallback not fully mature at first update')
        te = error[len(cal['origins']):]
        output_arrays = {}
        for days in [0]+cfg['lookback_days']:
            nodeq = np.broadcast_to(np.array(fallback['node_standard']), te.shape).copy()
            ruleq = np.where(test['rule_trigger'], fallback['triggered'], np.array(fallback['stable']))
            if days:
                for cutoff in np.unique(cutoffs):
                    eligible = eligible_mask(times, maturity, issued, int(cutoff), days)
                    fitted, ranks = fit_rolling(error, trigger, eligible, fallback, cfg['alpha'])
                    selected = cutoffs == cutoff
                    nodeq[selected] = np.array(fitted['node_standard'])
                    ruleq[selected] = np.where(test['rule_trigger'][selected], fitted['triggered'], np.array(fitted['stable']))
                    latest = int(maturity[eligible].max()) if eligible.any() else None
                    if latest is not None and latest >= cutoff:
                        raise ValueError('Immature label entered update')
                    fingerprint = hashlib.sha256(np.packbits(eligible).tobytes()).hexdigest()
                    daily_rows.extend(dict(seed=seed, days=days, cutoff_ns=int(cutoff),
                                           max_label_available_ns=latest, eligibility_sha256=fingerprint, **r) for r in ranks)
            for name, q in [('node_standard', nodeq), ('behavior_rule', ruleq)]:
                output_arrays[f'{name}_{days}d'] = q
                for group in ['all', 'event', 'stable', 'cell11', 'cell10']:
                    m = masks(test)[group]
                    metric_rows.append(dict(seed=seed, days=days, method=name, group=group, n=int(m.sum()),
                                            **interval_stats(te[m], q[m], cfg['alpha'])))
                for month in np.unique(months):
                    selected = months == month
                    metric_rows.append(dict(seed=seed, days=days, method=name, group='month:'+str(month), n=int(selected.sum()*40),
                                            **interval_stats(te[selected], q[selected], cfg['alpha'])))
        np.savez_compressed(out/f'interval_halfwidths_seed-{seed}.npz', origins=test['origins'],
                            daily_cutoff_ns=cutoffs, **output_arrays)
        print('Completed seed', seed, flush=True)
    write_csv(out/'daily_quantiles.csv', daily_rows)
    write_csv(out/'metrics_by_seed.csv', metric_rows)
    summary = mean_sd(metric_rows, ['days', 'method', 'group'], ['coverage', 'width', 'interval_score', 'unbounded_fraction'])
    write_csv(out/'summary.csv', summary)
    write_json(out/'audit.json', dict(analysis_id=cfg['analysis_id'], training=False,
                                    label_maturity_enforced=True, unseen_period=False,
                                    test_label_used_only_after_completion=True,
                                    daily_rank_records=len(daily_rows), finite_sample_coverage_guarantee=False))
    for path, digest in sources.items():
        if sha256_file(ROOT/path) != digest:
            raise ValueError('Source changed during run: '+path)
    write_json(out/'sources.json', sources)
    write_json(out/'manifest.json', {p.name: sha256_file(p) for p in out.iterdir() if p.is_file()})
    for r in summary:
        if r['group'] == 'all':
            print(r)


if __name__ == '__main__':
    main()
