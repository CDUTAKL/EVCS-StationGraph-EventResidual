#!/usr/bin/env python3
"""SG-EXP-020: immutable legacy-source lock, four cells, paired temporal blocks.

No training. Build refuses existing output; --verify checks source/product SHA256
and independently recomputes block intervals from the exported sufficient statistics.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import platform
import subprocess
from pathlib import Path
import numpy as np
import pandas as pd
import torch
import yaml

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/analysis/SG-EXP-020-legacy-evidence-v1'
SEEDS = (2024, 2025, 2026)
KEYS = ['split', 'origin_index', 'horizon', 'node_id']
MODELS = {'MRG-GCN':'SG-EXP-003', 'TCN':'SG-EXP-002', 'AdaptiveGraph':'SG-EXP-004'}
CELLS = [(1,1,'target_event_triggered'), (1,0,'target_event_not_triggered'),
         (0,1,'stable_triggered'), (0,0,'stable_not_triggered')]
RESAMPLES = 10000
RNG_SEED = 20260906
METRIC_TOLERANCE = 1e-8

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for b in iter(lambda:stream.read(1<<20),b''): h.update(b)
    return h.hexdigest()

def dump(path, obj):
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False)+'\n')

def cell_stats(y, pred, event, trigger):
    error=np.abs(pred-y)
    total=float(error.sum())
    if not np.isfinite(error).all() or total<=0: raise ValueError('invalid errors')
    rows=[]
    for a,b,name in CELLS:
        mask=(event==a)&(trigger==b)
        n=int(mask.sum())
        if n==0: raise ValueError(f'empty cell: {name}')
        s=float(error[mask].sum())
        rows.append(dict(cell=name,target_event=a,rule_trigger=b,n=n,
            sample_percent=100*n/len(y),mae=s/n,sum_absolute_error=s,
            contribution_percent=100*s/total))
    if sum(r['n'] for r in rows)!=len(y): raise ValueError('cell partition failed')
    if abs(sum(r['sum_absolute_error'] for r in rows)/len(y)-error.mean())>1e-12:
        raise ValueError('four-cell reconstruction failed')
    return rows

def block_ci(sums, counts):
    sums=np.asarray(sums,dtype=float); counts=np.asarray(counts,dtype=int)
    if len(sums)!=len(counts) or np.any(counts<0) or counts.sum()==0:
        raise ValueError('invalid block statistics')
    rng=np.random.default_rng(RNG_SEED)
    idx=rng.integers(0,len(counts),size=(RESAMPLES,len(counts)))
    denom=counts[idx].sum(axis=1)
    if np.any(denom==0): raise ValueError('empty bootstrap replicate')
    draws=sums[idx].sum(axis=1)/denom
    lo,hi=np.quantile(draws,[.025,.975])
    return dict(mean_difference=float(sums.sum()/counts.sum()),lower=float(lo),upper=float(hi),
                blocks=len(counts),keys=int(counts.sum()),positive_blocks=int((sums[counts>0]>0).sum()),
                nonempty_blocks=int((counts>0).sum()))

def build(out):
    if out.exists(): raise FileExistsError(f'Frozen output exists: {out}; use --verify')
    sources={}; runs=[]; per_cells=[]; arrays={}; reference=None; times=None
    adj_reference=None
    def source(p):
        rel=str(p.relative_to(ROOT)); sources[rel]={'sha256':sha(p),'bytes':p.stat().st_size}
    for rel in ('data/processed/SG-DATA-005-primary-tensor.npz',
                'data/manifests/SG-DATA-005-primary-tensor.json',
                'src/evcs_station_graph/models/graph.py',
                'src/evcs_station_graph/graphs/relations.py',
                'scripts/lock_legacy_evidence.py'):
        source(ROOT/rel)
    for model,exp in MODELS.items():
        run=ROOT/f'outputs/night_run/20260730-171821/{exp}/20260730-171821'
        config=yaml.safe_load((run/'config_resolved.yaml').read_text())
        for name in ('config_resolved.yaml','manifest.json','environment.json'):
            source(run/name)
        params=config['experiment']; k=params.get('graph',{}).get('top_k')
        if model=='MRG-GCN' and k!=3: raise ValueError('MRG legacy k must be 3')
        arrays[model]=[]
        for seed in SEEDS:
            d=run/f'seed-{seed}'
            for name in ('metrics.json','manifest.json','model.pt','predictions.csv.gz','training_log.csv'):
                source(d/name)
            df=pd.read_csv(d/'predictions.csv.gz').sort_values(KEYS).reset_index(drop=True)
            if df.duplicated(KEYS).any() or set(df.split)!={'test'}: raise ValueError('bad keys')
            if len(df)!=712360 or not df.groupby('origin_index').size().eq(40).all():
                raise ValueError('incomplete origin/node/horizon coverage')
            for c in ('target_event','rule_trigger'):
                if df[c].isna().any() or not set(df[c].unique()) <= {0,1,True,False}:
                    raise ValueError('invalid boolean labels')
            same=KEYS+['target_index','forecast_origin','target_time','y_true','target_event','rule_trigger']
            if reference is None:
                reference=df[same].copy(); times=pd.to_datetime(df.forecast_origin,utc=True)
            elif not reference.equals(df[same]): raise ValueError('keys/truth/masks/time differ')
            y=df.y_true.to_numpy(float); pred=df.y_pred.to_numpy(float)
            if not np.isfinite(np.column_stack([y,pred])).all(): raise ValueError('nonfinite')
            err=np.abs(y-pred); arrays[model].append(err)
            m=json.loads((d/'metrics.json').read_text())
            difference=abs(float(err.mean())-m['global']['mae'])
            if difference>1e-9: raise ValueError('MAE disagrees with original record')
            rows=cell_stats(y,pred,df.target_event.to_numpy(bool),df.rule_trigger.to_numpy(bool))
            if model=='MRG-GCN':
                for r in rows:
                    old=m['four_cell']['cells'][r['cell']]
                    # The CSV stores decimal text while metrics.json was written
                    # from the in-memory tensors.  Counts must match exactly;
                    # MAE is cross-checked within a small serialization tolerance.
                    if old['count']!=r['n'] or abs(old['mae']-r['mae'])>METRIC_TOLERANCE:
                        raise ValueError('cell differs from original metrics')
                    per_cells.append(dict(seed=seed,**r))
                payload=torch.load(d/'model.pt',map_location='cpu',weights_only=True)
                state=payload.get('model_state',payload)
                adj={f'adj_{i}':state[f'adj_{i}'].numpy() for i in range(3)}
                if adj_reference is None: adj_reference=adj
                elif any(not np.array_equal(adj[x],adj_reference[x]) for x in adj):
                    raise ValueError('MRG seed adjacencies differ')
            runs.append(dict(model=model,experiment=exp,seed=seed,run=str(d.relative_to(ROOT)),
                top_k=k,model_params=params.get('model_params'),training_config=params.get('training'),
                global_mae=float(err.mean()),stored_global_mae=m['global']['mae'],
                metric_recompute_difference=difference,keys=len(df),
                parameters=m['training']['trainable_parameters'],
                keys_truth_masks_identical=True,nonfinite=0,duplicate_keys=0))
        arrays[model]=np.asarray(arrays[model])
    summary=[]
    for model in MODELS:
        vals=arrays[model].mean(axis=1)
        summary.append(dict(model=model,mean=float(vals.mean()),sample_std=float(vals.std(ddof=1))))
    cells=pd.DataFrame(per_cells)
    cell_summary=[]
    for _,_,name in CELLS:
        s=cells[cells.cell==name]
        cell_summary.append(dict(cell=name,n=int(s.n.iloc[0]),sample_percent=float(s.sample_percent.iloc[0]),
            mae_mean=float(s.mae.mean()),mae_sd=float(s.mae.std(ddof=1)),
            contribution_percent_mean=float(s.contribution_percent.mean()),
            contribution_percent_sd=float(s.contribution_percent.std(ddof=1))))
    block_rows=[]; intervals=[]
    for days in (1,7):
        bins=((times-times.min().floor('D')).dt.total_seconds()//(86400*days)).astype(int).to_numpy()
        nblocks=int(bins.max())+1
        counts=np.bincount(bins,minlength=nblocks)
        for baseline in ('TCN','AdaptiveGraph'):
            paired=arrays[baseline]-arrays['MRG-GCN']
            for seed_index,seed in enumerate((*SEEDS,'seed_mean')):
                delta=paired[seed_index] if seed!='seed_mean' else paired.mean(axis=0)
                sums=np.bincount(bins,weights=delta,minlength=nblocks)
                for i,(s,n) in enumerate(zip(sums,counts)):
                    block_rows.append(dict(baseline=baseline,seed=str(seed),block_days=days,block_id=i,
                        start_utc=(times.min().floor('D')+pd.Timedelta(days=i*days)).isoformat(),
                        end_utc_exclusive=(times.min().floor('D')+pd.Timedelta(days=(i+1)*days)).isoformat(),
                        sum_paired_error_difference=float(s),n=int(n)))
                intervals.append(dict(baseline=baseline,seed=str(seed),block_days=days,**block_ci(sums,counts)))
    out.mkdir(parents=True)
    pd.DataFrame(runs).to_csv(out/'run_inventory.csv',index=False)
    cells.to_csv(out/'four_cell_per_seed.csv',index=False)
    pd.DataFrame(cell_summary).to_csv(out/'four_cell_summary.csv',index=False)
    pd.DataFrame(block_rows).to_csv(out/'block_statistics.csv',index=False)
    pd.DataFrame(intervals).to_csv(out/'block_intervals.csv',index=False)
    np.savez(out/'locked_adjacencies.npz',**adj_reference)
    dump(out/'source_lock.json',dict(experiment='SG-EXP-020',protocol='SG-DATA-005-legacy-recorded',
        git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        source_code_note='Current source hashes are audit-time snapshots, not proof of original training revision.',
        source_files=sources,runs=runs,
        scope='Original offline reconstructed protocol; known visibility/full-period fitting risks remain.'))
    dump(out/'analysis_contract.json',dict(experiment='SG-EXP-020',seeds=SEEDS,bootstrap_resamples=RESAMPLES,
        bootstrap_seed=RNG_SEED,block_days=[1,7],timezone='UTC',
        anchor=str(times.min().floor('D')),first_origin=str(times.min()),last_origin=str(times.max()),
        comparisons=['TCN - MRG-GCN','AdaptiveGraph - MRG-GCN'],
        seed_aggregation='mean absolute error across three seeds on each common key; not ensemble prediction',
        uncertainty='conditional temporal-block percentile intervals; per-seed intervals separate; no p-value',
        limitations=['old visibility and full-period fitting','already-seen test period','single site',
          'possible cross-block dependence','no full training randomness inference','different graph k for AdaptiveGraph'],
        python=platform.python_version(),numpy=np.__version__,pandas=pd.__version__,torch=torch.__version__))
    dump(out/'results.json',dict(global_summary=summary,four_cell_summary=cell_summary,block_intervals=intervals))
    dump(out/'manifest.json',dict(sources=sources,products={p.name:sha(p) for p in sorted(out.iterdir()) if p.is_file()}))
    verify(out)

def verify(out):
    m=json.loads((out/'manifest.json').read_text())
    for rel,item in m['sources'].items():
        if sha(ROOT/rel)!=item['sha256']: raise ValueError(f'source changed: {rel}')
    for name,digest in m['products'].items():
        if sha(out/name)!=digest: raise ValueError(f'product changed: {name}')
    blocks=pd.read_csv(out/'block_statistics.csv',dtype={'seed':str},float_precision='round_trip')
    intervals=pd.read_csv(out/'block_intervals.csv',dtype={'seed':str},float_precision='round_trip')
    for _,r in intervals.iterrows():
        b=blocks[(blocks.baseline==r.baseline)&(blocks.seed==r.seed)&(blocks.block_days==r.block_days)]
        result=block_ci(b.sum_paired_error_difference,b.n)
        for k in ('mean_difference','lower','upper'):
            if not np.isclose(result[k],r[k],atol=1e-12,rtol=0): raise ValueError(f'interval mismatch: {k}')
    cells=pd.read_csv(out/'four_cell_per_seed.csv',float_precision='round_trip')
    for _,c in cells.groupby('seed'):
        if c.n.sum()!=712360 or abs(c.contribution_percent.sum()-100)>1e-10:
            raise ValueError('four-cell totals failed')
    print(json.dumps({'status':'passed','sources':len(m['sources']),'products':len(m['products']),
                      'recomputed_intervals':len(intervals),'four_cell_seeds':3},ensure_ascii=False))

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--verify',action='store_true')
    parser.add_argument('--out',type=Path,default=OUT); args=parser.parse_args()
    verify(args.out) if args.verify else build(args.out)
