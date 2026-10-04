"""Frozen-checkpoint, legacy-protocol coverage audit; no training or test tuning.

Reproduces archived quantiles/coverage before promoting descriptive drift results.
Run from repository root with PYTHONPATH=src .venv/bin/python this_script.py.
"""
from pathlib import Path
import csv
import hashlib
import json
import numpy as np
import pandas as pd
import torch
import yaml
from analyze_conformal_prediction import (
    _load_model, _per_node_quantiles, _global_quantile, _masked_per_node_quantiles,
)
from evcs_station_graph.data import load_tensor_bundle, NodeWindowDataset, WindowSpec
from evcs_station_graph.evaluation import fit_frozen_event_rule, apply_frozen_event_rule
from evcs_station_graph.training.engine import _make_loader, _predict

ROOT = Path('outputs/night_run/20260730-171821/SG-EXP-003/20260730-171821')
DATA = Path('data/processed/SG-DATA-005-primary-tensor.npz')
OLD = Path('outputs/analysis/conformal_prediction/conformal_summary.json')
OUT = Path('outputs/analysis/conformal_failure_audit')

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    torch.set_num_threads(4)
    bundle = load_tensor_bundle(DATA)
    config = yaml.safe_load((ROOT/'config_resolved.yaml').read_text())
    ds = NodeWindowDataset(bundle, 'validation', WindowSpec(history_steps=96, forecast_steps=4))
    loader = _make_loader(ds, 256, False, 2024)
    rule = fit_frozen_event_rule(bundle, quantile=.95, window_extension=2)
    triggers = np.zeros((len(bundle.timestamps_ns), len(bundle.node_ids)), dtype=bool)
    triggers[ds.origins] = apply_frozen_event_rule(bundle, ds.origins, rule)
    old = json.loads(OLD.read_text())
    sources = {str(p):sha(p) for p in [DATA, OLD, ROOT/'config_resolved.yaml']}
    rows, cells, months, all_seed = [], [], [], []
    for seed in (2024, 2025, 2026):
        ckpt = ROOT/f'seed-{seed}/model.pt'
        predfile = ROOT/f'seed-{seed}/predictions.csv.gz'
        sources.update({str(p):sha(p) for p in (ckpt,predfile)})
        model = _load_model(ckpt, config, bundle, torch.device('cpu'))
        val = _predict(model, loader, torch.device('cpu'), triggers, bundle)
        vr = np.abs(val['truth']-val['prediction'])
        vmask = np.broadcast_to(val['rule_trigger'][:,None,:],vr.shape)
        qg = _per_node_quantiles(vr,.1)
        qt = np.full(len(bundle.node_ids),_global_quantile(vr[vmask],.1),dtype=np.float32)
        qs = _masked_per_node_quantiles(vr,~vmask,.1)
        qe = np.full(len(bundle.node_ids),_global_quantile(vr[val['target_event']],.1),dtype=np.float32)
        qne = _masked_per_node_quantiles(vr,~val['target_event'],.1)
        ref = next(x for x in old['per_seed'] if x['seed']==seed)
        for key,q in [('q_global_per_node',qg),('q_event_per_node',qt),('q_stable_per_node',qs),('q_event_oracle_per_node',qe),('q_stable_oracle_per_node',qne)]:
            if not np.allclose(q,ref[key],atol=2e-7,rtol=2e-4):
                raise AssertionError(f'Quantile mismatch: {seed} {key}')
        df = pd.read_csv(predfile)
        assert len(df)==712360 and not df.duplicated(['origin_index','horizon','node_index']).any()
        assert set(df['split'])=={'test'}
        df = df.sort_values(['origin_index','horizon','node_index'])
        shape=(len(bundle.split_origins['test']),4,len(bundle.node_ids))
        assert np.array_equal(df.origin_index.unique(),bundle.split_origins['test'])
        assert np.array_equal(df.node_index.to_numpy().reshape(shape),np.broadcast_to(np.arange(shape[2]),shape))
        assert np.array_equal(df.horizon.to_numpy().reshape(shape),np.broadcast_to(np.arange(1,5)[None,:,None],shape))
        # Archived reports subtract float32 model outputs, not CSV float64 values.
        tr = np.abs(df.y_true.to_numpy(dtype=np.float32)-df.y_pred.to_numpy(dtype=np.float32)).reshape(shape)
        assert np.isfinite(tr).all()
        ev = df.target_event.to_numpy(dtype=bool).reshape(shape)
        rt = df.rule_trigger.to_numpy(dtype=bool).reshape(shape)
        assert ev.sum()==10160 and rt.sum()==3060
        covers = {'standard':tr<=qg[None,None,:], 'rule':tr<=np.where(rt,qt[None,None,:],qs[None,None,:]), 'oracle':tr<=np.where(ev,qe[None,None,:],qne[None,None,:])}
        differences = {}
        for method, refkey in [('standard','standard_conformal'),('rule','stratified_conformal'),('oracle','stratified_oracle_upper')]:
            for mask,key in [(np.ones(shape,bool),'coverage_overall'),(ev,'coverage_event_window'),(~ev,'coverage_stable_window')]:
                delta=float(covers[method][mask].mean()-ref[refkey][key])
                differences[f'{method}:{key}']=delta
                # Floating-point forward reconstruction can change boundary ties.
                # 0.01 percentage point is below the thesis's 0.1-point display.
                assert abs(delta)<1e-4,(seed,method,key,delta)
        for split,res,event,rtrigger in [('validation',vr,val['target_event'],vmask),('test',tr,ev,rt)]:
            for group,mask in [('all',np.ones(res.shape,bool)),('event',event),('non_event',~event),('rule_trigger',rtrigger),('rule_not_trigger',~rtrigger)]:
                p=np.quantile(res[mask],[.5,.9,.95])
                rows.append(dict(seed=seed,split=split,node='all',horizon='all',group=group,n=int(mask.sum()),p50=p[0],p90=p[1],p95=p[2]))
            for n,node in enumerate(bundle.node_ids):
                for h in range(4):
                    p=np.quantile(res[:,h,n],[.5,.9,.95])
                    rows.append(dict(seed=seed,split=split,node=str(node),horizon=h+1,group='all',n=res.shape[0],p50=p[0],p90=p[1],p95=p[2]))
        for a in (0,1):
            for b in (0,1):
                mask=(ev==a)&(rt==b)
                cells.append(dict(seed=seed,cell=f'{a}{b}',n=int(mask.sum()),mae=float(tr[mask].mean()),**{k:float(c[mask].mean()) for k,c in covers.items()}))
        # By target month (overlapping forecast keys are not independent observations).
        month=df.target_time.astype(str).str[:7].to_numpy().reshape(shape)
        for m in np.unique(month):
            mask=month==m
            months.append(dict(seed=seed,month=m,n=int(mask.sum()),event_rate=float(ev[mask].mean()),**{k:float(c[mask].mean()) for k,c in covers.items()}))
        all_seed.append(dict(seed=seed,quantiles_within_tolerance=True,coverage_tolerance=1e-4,coverage_differences=differences))
        print(f'seed {seed}: archived coverage reproduced within 0.01 percentage point; max difference={max(abs(d) for d in differences.values()):.8f}',flush=True)
    OUT.mkdir(parents=True,exist_ok=True)
    for name,items in [('residual_quantiles.csv',rows),('four_cell_coverage.csv',cells),('monthly_coverage.csv',months)]:
        with (OUT/name).open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(items[0]));writer.writeheader();writer.writerows(items)
    aggregate={}
    for split in ('validation','test'):
        sel=[r for r in rows if r['split']==split and r['node']=='all' and r['group']=='all']
        aggregate[split]={k:dict(mean=float(np.mean([x[k] for x in sel])),std=float(np.std([x[k] for x in sel],ddof=1))) for k in ('p50','p90','p95')}
    cell_summary={g:{k:float(np.mean([x[k] for x in cells if x['cell']==g])) for k in ('n','standard','rule','oracle','mae')} for g in ('11','10','01','00')}
    summary=dict(protocol='SG-DATA-005 legacy retrospective',seeds=all_seed,aggregate_quantiles=aggregate,four_cell_coverage=cell_summary,sources=sources,limitations=['No training; frozen validation quantiles; no test tuning','Validation reused for early stopping and rule fitting','No independent-observation CI or 90% guarantee','Old proxy-load rule is retrospective, not online-visible'])
    (OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'aggregate_quantiles':aggregate,'four_cell_coverage':cell_summary},ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
