"""Paired temporal-block analysis of frozen SG-EXP-027 predictions; no training."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from analyze_demand_warning import sha256_file, write_csv, write_json
from analyze_independent_calibration import bootstrap_ratio, masks, read_prediction
from evcs_station_graph.eventtime.data import FrozenData

ROOT = Path(__file__).resolve().parents[1]


def block_totals(diff, mask, blocks):
    """Keep all keys in each origin together; retain counts for ratio estimates."""
    if diff.shape != mask.shape or diff.shape[0] != len(blocks):
        raise ValueError("Misaligned error keys, mask or origin blocks")
    count = int(np.max(blocks)) + 1
    sums = np.bincount(blocks, weights=np.where(mask, diff, 0).sum(axis=(1, 2)), minlength=count)
    counts = np.bincount(blocks, weights=mask.sum(axis=(1, 2)), minlength=count).astype(np.int64)
    return sums, counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=ROOT/'configs/analysis/SG-EXP-027-time-block.json')
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    cfg = json.loads(args.config.read_text())
    out = args.out or ROOT/cfg['output']
    if out.exists():
        raise FileExistsError(f'Refusing to overwrite analysis: {out}')
    data = FrozenData(ROOT/cfg['data'])
    sources = {cfg['data']: data.digest, str(args.config.relative_to(ROOT)): sha256_file(args.config),
               str(Path(__file__).relative_to(ROOT)): sha256_file(Path(__file__))}
    errors, rows, reference = {}, [], None
    for model in cfg['models']:
        errors[model] = []
        for seed in cfg['seeds']:
            folder = ROOT/cfg['source_root']/model/f'seed-{seed}'
            for name, digest in json.loads((folder/'manifest.json').read_text()).items():
                path = folder/name
                if sha256_file(path) != digest:
                    raise ValueError(f'Archive digest mismatch: {path}')
                sources[str(path.relative_to(ROOT))] = digest
            a = read_prediction(folder, 'test', data, sources, reference)
            if reference is None:
                reference = a
            e = np.abs(a['y_true'].astype(np.float64)-a['y_pred'].astype(np.float64))
            errors[model].append(e)
            for group, mask in masks(reference).items():
                if group in cfg['groups']:
                    rows.append(dict(model=model, seed=seed, group=group, n=int(mask.sum()), mae=float(e[mask].mean())))
    full, shared = cfg['models']
    diff = np.mean(errors[shared], axis=0)-np.mean(errors[full], axis=0)
    # Separately subtract paired seed arrays, guarding against accidental ensembling.
    paired_diff = np.mean([b-a for a,b in zip(errors[full],errors[shared])],axis=0)
    np.testing.assert_allclose(diff, paired_diff, atol=1e-15, rtol=0)
    dates = pd.to_datetime(reference['origin_cutoff_ns'], utc=True).tz_convert(cfg['bootstrap']['timezone']).normalize().tz_localize(None)
    days = ((dates-dates.min())/pd.Timedelta(days=1)).to_numpy(dtype=np.int64)
    all_masks = masks(reference)
    cis, blocks_output, independent = [], [], []
    for block_days in cfg['bootstrap']['block_days']:
        blocks = days//block_days
        nblocks = int(blocks.max())+1
        draws = np.random.default_rng(cfg['bootstrap']['seed']).integers(0,nblocks,size=(cfg['bootstrap']['resamples'],nblocks))
        for group in cfg['groups']:
            mask = all_masks[group]
            sums, counts = block_totals(diff, mask, blocks)
            ci = bootstrap_ratio(sums, counts, draws)
            # Independent aggregation by direct origin slicing, without bincount.
            direct_s = np.array([paired_diff[blocks==b][mask[blocks==b]].sum() for b in range(nblocks)])
            direct_c = np.array([mask[blocks==b].sum() for b in range(nblocks)])
            np.testing.assert_allclose(sums,direct_s,atol=1e-10,rtol=0)
            np.testing.assert_array_equal(counts,direct_c)
            values = np.take(direct_s,draws).sum(axis=1)/np.take(direct_c,draws).sum(axis=1)
            low,high = np.percentile(values,[2.5,97.5])
            np.testing.assert_allclose([ci['low'],ci['high']],[low,high],atol=1e-12,rtol=0)
            np.testing.assert_allclose(ci['estimate'],paired_diff[mask].mean(),atol=1e-12,rtol=0)
            cis.append(dict(group=group,block_days=block_days,blocks=nblocks,n=int(mask.sum()),
                            primary=block_days==cfg['bootstrap']['primary_block_days'] and group=='all',**ci))
            independent.append(dict(group=group,block_days=block_days,status='PASS',max_block_sum_difference=float(np.max(np.abs(sums-direct_s)))))
            blocks_output.extend(dict(group=group,block_days=block_days,block=b,n=int(counts[b]),sum_difference=float(sums[b])) for b in range(nblocks))
    aggregates=[]
    for model in cfg['models']:
        for group in cfg['groups']:
            values=[r['mae'] for r in rows if r['model']==model and r['group']==group]
            aggregates.append(dict(model=model,group=group,mae_mean=float(np.mean(values)),mae_sd=float(np.std(values,ddof=1))))
    source_after={path:sha256_file(ROOT/path) for path in sources}
    if source_after!=sources:
        raise ValueError('Source changed during analysis')
    out.mkdir(parents=True)
    write_csv(out/'seed_metrics.csv',rows)
    write_csv(out/'aggregate_metrics.csv',aggregates)
    write_csv(out/'paired_time_blocks.csv',cis)
    write_csv(out/'block_totals.csv',blocks_output)
    write_json(out/'sources.json',sources)
    write_json(out/'independent-verification.json',dict(status='PASS',source_hashes=len(sources),checks=independent,
        method='Direct paired seed differences, direct origin slices, percentile recomputation; not an independent external reviewer'))
    write_json(out/'summary.json',dict(config=cfg,verified_runs=6,keys_per_run=int(diff.size),
        first_date=str(dates.min().date()),last_date=str(dates.max().date()),aggregates=aggregates,comparisons=cis))
    write_json(out/'manifest.json',{p.name:sha256_file(p) for p in out.iterdir() if p.is_file()})
    print(json.dumps(dict(status='PASS',output=str(out),comparisons=cis),ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
