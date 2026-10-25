from pathlib import Path
import numpy as np, json, hashlib, datetime as dt
from zoneinfo import ZoneInfo
R=Path('/Users/xushuyuan/Documents/Codex/EVCS-StationGraph-EventResidual')
O=R/'docs/thesis/content-review-20261016-paired-reaudit'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads(p.read_text())
def npz(p):
 with np.load(p,allow_pickle=False) as z:return dict(z)
def calc(a):
 y=a['y_true'].astype(float); e=np.abs(y-a['y_pred'].astype(float)); ev=a['target_event'].astype(bool)
 return dict(mae=float(e.mean()),rmse=float(np.sqrt(np.square(e).mean())),event=float(e[ev].mean()),stable=float(e[~ev].mean()),zero=float(e[y==0].mean()),nonzero=float(e[y!=0].mean()),zero_fraction=float((y==0).mean()),by_node=e.mean((0,1)).tolist(),by_horizon=e.mean((0,2)).tolist())
def run_suite(exp,root,vs,contrasts):
 data={}; rows=[]; reference=None; files=[]
 for v in vs:
  for s in [2024,2025,2026]:
   p=root/v/f'seed-{s}'; cfg=read(p/'config_resolved.json'); log=read(p/'train_log.json'); summary=read(p/'run_summary.json')
   manifest=read(p/'manifest.json')
   for name,h in manifest.items():
    assert sha(p/name)==h; files.append(str(p/name))
   a=npz(p/'predictions_test.npz'); e=np.abs(a['y_true'].astype(float)-a['y_pred'].astype(float))
   assert np.isfinite(e).all(); assert len(set(a['origins'].tolist()))==len(a['origins'])
   if reference is None: reference=a
   for k in ['origins','node_ids','target_event','rule_trigger','target_timestamps_ns','origin_cutoff_ns','y_true']: assert np.array_equal(a[k],reference[k]),k
   best=min(log,key=lambda row:row['tuning_mae'])['epoch']; assert best==summary['best_epoch']
   assert [x['epoch'] for x in log]==list(range(1,len(log)+1))
   assert len(log)==best+8 and len(log)<60
   assert cfg['max_epochs']==60 and cfg['patience']==8 and cfg['batch_size']==256 and cfg['lr']==.001 and cfg['weight_decay']==.0001
   assert cfg['train_limit'] is None and cfg['eval_limit'] is None
   m=calc(a); rows.append(dict(variant=v,seed=s,best=best,stop=len(log),parameters=cfg['trainable_parameters'],metrics=m,prediction_sha=sha(p/'predictions_test.npz')))
   data[v,s]=(e,cfg,a)
 aggregate={v:{k:dict(mean=np.mean([x['metrics'][k] for x in rows if x['variant']==v],axis=0).tolist(),sd=np.std([x['metrics'][k] for x in rows if x['variant']==v],axis=0,ddof=1).tolist()) for k in rows[0]['metrics']} for v in vs}
 tz=ZoneInfo('America/Los_Angeles'); dates=[dt.datetime.fromtimestamp(int(t)/1e9,dt.timezone.utc).astimezone(tz).date() for t in reference['origin_cutoff_ns']]; anchor=min(dates)
 ids=np.array([(d-anchor).days//7 for d in dates]); n=int(ids.max())+1; keys=np.bincount(ids)*40
 draws=np.random.default_rng(20261015).integers(n,size=(10000,n)); comps=[]
 for v,b in contrasts:
  ds=[data[v,s][0]-data[b,s][0] for s in [2024,2025,2026]]; delta=np.mean(ds,axis=0)
  sums=np.bincount(ids,weights=delta.sum((1,2))); samples=sums[draws].sum(1)/keys[draws].sum(1)
  masks={'all':np.ones(delta.shape,bool),'event':reference['target_event'].astype(bool),'zero':reference['y_true']==0,'nonzero':reference['y_true']!=0}
  comps.append(dict(contrast=f'{v} minus {b}',seed_delta=[float(d.mean()) for d in ds],mean=float(delta.mean()),ci95=np.quantile(samples,[.025,.975]).tolist(),bonferroni98=np.quantile(samples,[1/120,119/120]).tolist(),positive_blocks=int((sums>0).sum()),blocks=n,block_anchor=str(anchor),strata={k:float(delta[m].mean()) for k,m in masks.items()},zero_net_contribution=float(delta[masks['zero']].sum()/delta.sum()),block_key_counts=keys.tolist()))
 for c,(v,b) in zip(comps,contrasts):
  mask=reference['y_true']!=0;ds=[data[v,s][0]-data[b,s][0] for s in [2024,2025,2026]]; delta=np.mean(ds,axis=0)
  subset_sums=np.bincount(ids,weights=np.where(mask,delta,0).sum((1,2)),minlength=n)
  subset_counts=np.bincount(ids,weights=mask.sum((1,2)),minlength=n)
  sample=subset_sums[draws].sum(1)/subset_counts[draws].sum(1)
  c['reviewer_added_nonzero_ci95']=np.quantile(sample,[.025,.975]).tolist()
  c['nonzero_seed_differences']=[float(d[mask].mean()) for d in ds]
  c['reviewer_added_analysis_scope']='Review-time post hoc descriptive nonzero endpoint; no multiplicity correction; not a manuscript result or confirmatory endpoint.'
 return dict(experiment=exp,verified_manifest_entries=len(files),runs=rows,aggregate=aggregate,comparisons=comps),data
r31,d31=run_suite('031',R/'outputs/experiments/SG-EXP-031/recovered/results/SG-EXP-031/jpl',['full','load_to_self','event_to_self','pattern_to_self'],[(v,'full') for v in ['load_to_self','event_to_self','pattern_to_self']])
for s in [2024,2025,2026]:assert len({d31[v,s][1]['initial_parameters_sha256'] for v in ['full','load_to_self','event_to_self','pattern_to_self']})==1
r32,d32=run_suite('032',R/'outputs/experiments/SG-EXP-032/recovered/closeout/closeout/results/formal',['mrg_full','tcn_wide'],[('tcn_wide','mrg_full')])
a=npz(R/'outputs/visibility/SG-DATA-006-eventtime-v1/dataset.npz'); b=npz(R/'outputs/experiments/SG-EXP-032/frozen-contract/dataset.npz')
fixed=['features','feature_mean','feature_std','graphs','timestamps_ns','node_ids','target_event','rule_trigger','train_origins','tuning_origins','calibration_origins','test_origins']
for k in fixed: assert np.array_equal(a[k],b[k]),k
assert np.allclose(b['target_mean'],b['targets'][:83198].mean(0),rtol=0,atol=1e-14)
assert np.allclose(b['target_std'],b['targets'][:83198].std(0),rtol=0,atol=1e-14)
for (_,s),(_,cfg,p) in d32.items():
 idx=b['test_origins'][:,None]+np.arange(1,5);assert np.array_equal(p['y_true'],b['targets'][idx]);assert np.array_equal(p['target_event'],b['target_event'][idx])
report=dict(manuscripts={n:sha(O/'packet'/f'{n}-training.md') for n in ['before','after']},sg031=r31,sg032=r32,sg032_fixed_arrays=fixed,scope='Independent NumPy arithmetic; no training, no checkpoint forward; source array and manifest verification; fixed original graph comparison. Bootstrap seed reproduces protocol; not an untouched test.')
(O/'methods-numeric-recompute.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
for result in [r31,r32]:
 print(result['experiment'],result['verified_manifest_entries'])
 for v,met in result['aggregate'].items(): print(v,{k:round(x['mean'],9) for k,x in met.items() if k not in ['by_node','by_horizon']})
 for c in result['comparisons']: print(c)
# Independently rebuild completion-support energy with Python csv and integer bins.
import csv
raw=Path(read(R/'configs/data/SG-DATA-006-eventtime-v1.json')['source'])
grid=b['timestamps_ns']; start=int(grid[0]); step=900000000000
nodes={str(n):i for i,n in enumerate(b['node_ids'])}; rebuilt=np.zeros_like(b['targets']); original=np.zeros_like(rebuilt)
stats={'selected':0,'missing':0,'invalid':0,'valid':0,'done_equals_connection':0,'done_equals_disconnect':0}
def ns(t):return int(np.datetime64(t.replace(' ','T'),'ns').astype('int64'))
with raw.open() as f:
 for row in csv.DictReader(f):
  if row['spaceID'] not in nodes: continue
  stats['selected']+=1; c=ns(row['connectionTime']); d=ns(row['disconnectTime']); text=row['doneChargingTime']; done=ns(text) if text and text.lower()!='nan' else None
  valid=done is not None and c<=done<=d
  stats['missing' if done is None else ('valid' if valid else 'invalid')]+=1
  stats['done_equals_connection']+=int(done==c);stats['done_equals_disconnect']+=int(done==d)
  endpoint=done if valid else d; energy=float(row['kWhDelivered']); n=nodes[row['spaceID']]
  for matrix,finish in [(rebuilt,endpoint),(original,d)]:
   lo=(c-start)//step; hi=(finish-start+step-1)//step
   if hi>lo:matrix[max(0,lo):min(len(grid),hi),n]+=energy/(hi-lo)
assert np.max(np.abs(rebuilt-b['targets']))<1e-12
assert np.max(np.abs(original-a['targets']))<1e-12
stats.update(max_rebuild_error=float(np.max(np.abs(rebuilt-b['targets']))),original_energy=float(original.sum()),alternative_energy=float(rebuilt.sum()),max_node_energy_difference=float(np.max(np.abs(original.sum(0)-rebuilt.sum(0)))),mean_label_difference=float(np.abs(original-rebuilt).mean()),raw_sha256=sha(raw))
report['raw_reconstruction']=stats
# Tie JPL predictions and substituted graphs to frozen original dataset.
jpl=npz(R/'outputs/experiments/SG-EXP-031/bundle/data/jpl/dataset.npz'); graph=jpl['graphs']; confirms=[]
for (v,s),(_,cfg,p) in d31.items():
 idx=p['origins'][:,None]+np.arange(1,5)
 assert np.array_equal(p['y_true'],jpl['targets'][idx]);assert np.array_equal(p['origins'],jpl['test_origins'])
 used=graph.copy()
 if v!='full':used[['load_to_self','event_to_self','pattern_to_self'].index(v)]=np.eye(10)
 assert hashlib.sha256(used.tobytes()).hexdigest()==cfg['used_graph_sha256']
 confirms.append(f'{v}/{s}')
report['jpl_graph_and_source_array_checks']=confirms
(O/'methods-numeric-recompute.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(stats)
