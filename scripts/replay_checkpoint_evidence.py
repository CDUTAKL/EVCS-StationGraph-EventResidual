#!/usr/bin/env python3
"""Portable checkpoint inference audit. No training; independent source processes."""
import argparse, hashlib, importlib.metadata, json, os, platform, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
PRED_ATOL=5e-6
METRIC_ATOL=5e-6
COMPONENTS={'legacy':9,'sg019':36,'sg027':6,'sg028':12}
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def write(p,obj):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def verify(root):
    manifest=json.loads((root/'MANIFEST.json').read_text())
    for rel,digest in manifest.items():
        p=(root/rel).resolve()
        if not p.is_relative_to(root) or not p.is_file() or sha(p)!=digest:
            raise ValueError(f'Package hash mismatch: {rel}')
    return len(manifest)
def metric_values(y,p,t):
    import numpy as np
    e=np.abs(y.astype('float64')-p.astype('float64'))
    return {'mae':float(e.mean()),'rmse':float(np.sqrt((e**2).mean())),
            'event_mae':float(e[t].mean()),'stable_mae':float(e[~t].mean()),
            'by_horizon_mae':e.mean(axis=(0,2)).tolist(),'by_node_mae':e.mean(axis=(0,1)).tolist()}
def check_metrics(v,saved):
    import numpy as np
    return {k:float(np.max(np.abs(np.asarray(value)-np.asarray(saved[k])))) for k,value in v.items()}
def row_info(component,name,seed,best,pred,y,p,checks,diffs):
    import numpy as np
    return {'component':component,'model':name,'seed':int(seed),'n_test_keys':int(y.size),
            'checkpoint_sha256':sha(best),'archived_prediction_sha256':sha(pred),
            'replayed_mae':float(np.abs(y.astype('float64')-p.astype('float64')).mean()),
            'max_metric_abs_diff':max(diffs.values()),'metric_abs_differences':diffs,
            'checks':checks,'status':'PASS' if all(checks.values()) else 'FAIL'}
def modern(component,base):
    import numpy as np, torch
    from evcs_station_graph.eventtime import runner
    from evcs_station_graph.eventtime.data import FrozenData
    from evcs_station_graph.eventtime.models import build_model
    data=FrozenData(base/'data/eventtime/dataset.npz')
    code=runner.code_digest();rows=[]
    for run in sorted((base/'results/formal').glob('*/seed-*')):
        cfg=json.loads((run/'config_resolved.json').read_text());name=cfg['model'];seed=cfg['seed']
        manifest=json.loads((run/'manifest.json').read_text())
        checks={'original_manifest_exact':all(sha(run/rel)==v for rel,v in manifest.items()),
                'source_digest_exact':cfg['code_sha256']==code,'dataset_digest_exact':cfg['dataset_sha256']==data.digest,
                'formal_full_test_config':cfg['mode']=='formal' and cfg['eval_limit'] is None}
        best=torch.load(run/'best.pt',weights_only=True,map_location='cpu')
        last=torch.load(run/'last.pt',weights_only=True,map_location='cpu')
        summary=json.loads((run/'run_summary.json').read_text())
        checks['contract_chain_exact']=best['contract']==last['contract']==cfg['contract']==summary['contract']
        checks['selection_epoch_exact']=int(best['epoch'])==int(summary['best_epoch'])
        if not all(checks.values()): raise ValueError(f'Provenance failed {component}/{name}/{seed}: {checks}')
        runner.setup(seed,'cpu',cfg.get('threads',2));model=build_model(name,data.arrays['graphs']).to('cpu')
        model.load_state_dict(best['model'],strict=True)
        y,p,origins=runner.predict(model,data,'test',cfg,'cpu');target,trigger=data.masks(origins)
        saved_path=run/'predictions_test.npz'
        with np.load(saved_path,allow_pickle=False) as saved:
            for k,actual in {'y_true':y,'origins':origins,'node_ids':data.arrays['node_ids'],
              'target_event':target,'rule_trigger':trigger,
              'target_timestamps_ns':data.arrays['timestamps_ns'][origins[:,None]+np.arange(1,5)],
              'origin_cutoff_ns':data.arrays['timestamps_ns'][origins]+900_000_000_000}.items():
                checks[k+'_exact']=np.array_equal(actual,saved[k])
            pred_diff=float(np.abs(p-saved['y_pred']).max());checks['prediction_within_tolerance']=pred_diff<=PRED_ATOL
        metrics=json.loads((run/'metrics.json').read_text())['splits']['test']
        diffs=check_metrics(metric_values(y,p,target),metrics)
        checks.update({f'metric_{k}_within_tolerance':d<=METRIC_ATOL for k,d in diffs.items()})
        # Four cells: exact cell counts and independent weighted-MAE closure.
        e=np.abs(y-p);weighted=0.0;n=0
        for a in [0,1]:
            for b in [0,1]:
                mask=(target==a)&(trigger==b);cell=metrics['four_cells'][f'target_{a}_trigger_{b}']
                count=int(mask.sum());checks[f'cell_{a}{b}_count_exact']=count==cell['n']
                value=float(e[mask].mean()) if count else 0.0
                diff=abs(value-cell['mae']) if cell['mae'] is not None else 0.0
                checks[f'cell_{a}{b}_mae_within_tolerance']=diff<=METRIC_ATOL
                weighted+=float(e[mask].sum());n+=count
        checks['four_cell_closure']=n==y.size and abs(weighted/n-float(e.mean()))<=1e-12
        r=row_info(component,name,seed,run/'best.pt',saved_path,y,p,checks,diffs)
        r.update(best_epoch=int(best['epoch']),max_prediction_abs_diff=pred_diff,source_digest=code,dataset_digest=data.digest,
                 archived_mae=metrics['mae'],mae_abs_diff=diffs['mae'])
        rows.append(r);print(f"{r['status']} {component}/{name}/{seed}: max_pred_diff={pred_diff:.3g}",flush=True)
    return rows

def legacy(base):
    import copy,numpy as np,pandas as pd,torch,yaml
    from evcs_station_graph.data import NodeWindowDataset,WindowSpec,load_tensor_bundle
    from evcs_station_graph.evaluation import FrozenEventRule,apply_frozen_event_rule
    from evcs_station_graph.training.engine import _make_loader,_predict
    from evcs_station_graph.training.factory import build_model
    data=load_tensor_bundle(base/'data/dataset.npz');rows=[];torch.set_num_threads(2)
    for group in sorted((base/'results').iterdir()):
        original=yaml.safe_load((group/'config_resolved.yaml').read_text())
        with np.load(group/'relation_matrices.npz',allow_pickle=False) as f: adj=[f[k] for k in ['load','event','pattern']]
        for run in sorted(group.glob('seed-*')):
            seed=int(run.name.split('-')[1]);payload=torch.load(run/'model.pt',weights_only=True,map_location='cpu');state=payload['model_state']
            cfg=copy.deepcopy(original);prefix='network.' if group.name=='SG-EXP-002' else 'tcn.network.'
            keys=[k for k in state if k.startswith(prefix) and k.endswith('.conv.weight')]
            first=state[prefix+'0.conv.weight'];params=cfg['experiment'].setdefault('model_params',{})
            params['levels']=len(keys);params['hidden_dim']=int(first.shape[0]);cfg['project'].pop('history_steps',None)
            model=build_model(cfg,input_dim=int(first.shape[1]),horizon=4,num_nodes=len(data.node_ids),adjacencies=adj)
            model.load_state_dict(state,strict=True);model.eval()
            archived=json.loads((run/'metrics.json').read_text());r=archived['frozen_event_rule']
            rule=FrozenEventRule(thresholds=np.array(r['thresholds'],dtype='float32'),quantile=r['quantile'],
                score_definition=r['score_definition'],window_extension=r['window_extension'],score_stats=r['score_stats'])
            ds=NodeWindowDataset(data,'test',WindowSpec(96,4));triggers=np.zeros((len(data.timestamps_ns),len(data.node_ids)),dtype=bool)
            triggers[ds.origins]=apply_frozen_event_rule(data,ds.origins,rule)
            with torch.no_grad(): values=_predict(model,_make_loader(ds,256,False,seed),torch.device('cpu'),triggers,data)
            y,p=values['truth'],values['prediction'];target=values['target_event'];trigger=np.repeat(values['rule_trigger'][:,None,:],4,axis=1)
            pred_path=run/'predictions.csv.gz';frame=pd.read_csv(pred_path)
            checks={'split_exact':bool((frame['split']=='test').all()),'keys_unique':not frame.duplicated(['split','origin_index','horizon','node_id']).any(),
                    'key_count_exact':len(frame)==y.size,'seed_exact':payload['seed']==seed,
                    'parameter_count_exact':sum(x.numel() for x in model.parameters() if x.requires_grad)==archived['training']['trainable_parameters']}
            frame=frame.sort_values(['origin_index','horizon','node_index']).reset_index(drop=True)
            checks['origins_exact']=np.array_equal(frame.origin_index.to_numpy(),np.repeat(ds.origins,40))
            checks['horizons_exact']=np.array_equal(frame.horizon.to_numpy(),np.tile(np.repeat(np.arange(1,5),10),len(ds.origins)))
            checks['node_indices_exact']=np.array_equal(frame.node_index.to_numpy(),np.tile(np.arange(10),len(ds.origins)*4))
            checks['node_ids_exact']=np.array_equal(frame.node_id.to_numpy(),np.tile(data.node_ids,len(ds.origins)*4))
            indices=(ds.origins[:,None]+np.arange(1,5)).repeat(10,axis=1).ravel()
            checks['target_index_exact']=np.array_equal(frame.target_index.to_numpy(),indices)
            checks['target_time_exact']=np.array_equal(pd.to_datetime(frame.target_time).to_numpy().astype('datetime64[ns]').astype('int64'),data.timestamps_ns[indices])
            checks['origin_time_exact']=np.array_equal(pd.to_datetime(frame.forecast_origin).to_numpy().astype('datetime64[ns]').astype('int64'),np.repeat(data.timestamps_ns[ds.origins],40))
            checks['target_event_exact']=np.array_equal(target.ravel(),frame.target_event.to_numpy())
            checks['rule_trigger_exact']=np.array_equal(trigger.ravel(),frame.rule_trigger.to_numpy())
            checks['y_true_csv_rounding']=float(np.abs(y.ravel()-frame.y_true.to_numpy()).max())<=1e-7
            pred_diff=float(np.abs(p.ravel()-frame.y_pred.to_numpy()).max());checks['prediction_within_tolerance']=pred_diff<=PRED_ATOL
            saved={'mae':archived['global']['mae'],'rmse':archived['global']['rmse'],
                   'event_mae':archived['event_window']['mae'],'stable_mae':archived['stable_window']['mae'],
                   'by_horizon_mae':[archived['by_horizon'][str(h)]['mae'] for h in range(1,5)],
                   'by_node_mae':[archived['by_node'][str(n)]['mae'] for n in data.node_ids]}
            diffs=check_metrics(metric_values(y,p,target),saved);checks.update({f'metric_{k}_within_tolerance':d<=METRIC_ATOL for k,d in diffs.items()})
            row=row_info('legacy',group.name,seed,run/'model.pt',pred_path,y,p,checks,diffs)
            row.update(max_prediction_abs_diff=pred_diff,archived_mae=saved['mae'],mae_abs_diff=diffs['mae'],
              recovered_levels=len(keys),original_config_levels=original['experiment']['model_params'].get('levels'),
              source_authenticity='current reconstructed source only; historical training source unverified')
            rows.append(row);print(f"{row['status']} legacy/{group.name}/{seed}: max_pred_diff={pred_diff:.3g}",flush=True)
    return rows

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,default=ROOT/'replay-results')
    ap.add_argument('--verify-only',action='store_true');ap.add_argument('--worker',choices=COMPONENTS);args=ap.parse_args()
    out=args.out.resolve()
    if args.worker:
        base=ROOT/'components'/args.worker;sys.path.insert(0,str(base/'src'))
        if args.worker=='sg028':
            import replay_sgexp028_checkpoints as jpl
            result,rows=jpl.replay(base)
            for r in rows:r['component']='sg028';r['max_prediction_abs_diff']=r['max_prediction_abs_diff_cpu_vs_archived']
        else:rows=legacy(base) if args.worker=='legacy' else modern(args.worker,base)
        write(out/(args.worker+'.json'),{'expected_runs':COMPONENTS[args.worker],'runs':rows,'retraining_performed':False,
            'status':'PASS' if len(rows)==COMPONENTS[args.worker] and all(r['status']=='PASS' for r in rows) else 'FAIL'})
        return
    count=verify(ROOT);print(f'PASS frozen manifest: {count} files',flush=True)
    if args.verify_only:return
    if out.exists():raise ValueError('Replay output must be a new directory')
    if out.is_relative_to(ROOT/'components'):raise ValueError('Cannot write into frozen components')
    out.mkdir(parents=True)
    env=dict(os.environ);env.pop('PYTHONPATH',None);env['PYTHONDONTWRITEBYTECODE']='1';env['PYTHONUNBUFFERED']='1'
    summaries={}
    for component in COMPONENTS:
        proc=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--worker',component,'--out',str(out)],env=env)
        if proc.returncode!=0:
            summaries[component]={'status':'ERROR','exit_code':proc.returncode,'expected_runs':COMPONENTS[component]};continue
        summaries[component]=json.loads((out/(component+'.json')).read_text())
    status='PASS' if all(s.get('status')=='PASS' for s in summaries.values()) else 'FAIL'
    result={'status':status,'manifest_files_verified':count,'manifest_sha256':sha(ROOT/'MANIFEST.json'),
            'protocols':summaries,'prediction_atol':PRED_ATOL,'metric_atol':METRIC_ATOL,'retraining_performed':False,
            'environment':{'python':platform.python_version(),'platform':platform.platform(),'libraries':{k:importlib.metadata.version(k) for k in ['torch','numpy','pandas','PyYAML']}},
            'scope':'test inference only; no training reconstruction or complete raw-data rebuild'}
    write(out/'summary.json',result)
    print(f'{status}: cross-protocol replay',flush=True)
    if status!='PASS':raise SystemExit(1)
if __name__=='__main__':main()
