"""Recompute the mappings corrected by the 2026-09-07 figure audit."""
from pathlib import Path
import json
import sys
import numpy as np
import pandas as pd
sys.path.insert(0,'src')
from evcs_station_graph.data import load_tensor_bundle

b=load_tensor_bundle('data/processed/SG-DATA-005-primary-tensor.npz')
t=pd.to_datetime(b.timestamps_ns,utc=True).tz_convert('America/Los_Angeles')
event=b.event_labels.any(axis=1)
hour_counts=np.bincount(t.hour[event],minlength=24)
assert int(hour_counts.sum())==int(event.sum())
order4=np.argsort(-b.targets[:2688].sum(axis=0))
ordertest=np.argsort(-b.targets[b.split_origins['test']].sum(axis=0))
report={'timezone':'America/Los_Angeles','first_sample':str(t[0]),
        'first_weekend_offset_days':next(float((d-t[0]).total_seconds()/86400)
            for d in pd.date_range(t[0].normalize(),periods=7,freq='D') if d.weekday()==5),
        'typical_week_first_sample':str(t[2880]),'typical_week_nodes':['CA-303','CA-489','CA-311'],
        'four_week_nodes_top_to_bottom':[str(b.node_ids[i]) for i in order4],
        'test_origin_load_order':[str(b.node_ids[i]) for i in ordertest],
        'event_hour_counts':hour_counts.tolist(),'event_hour_peak':int(hour_counts.argmax()),
        'event_hour_peak_percent':float(hour_counts.max()/hour_counts.sum()*100),
        'shared_prediction_key_denominator':712360,
        'target_event_percent':10160/712360*100,'rule_trigger_percent':3060/712360*100}
p=Path('outputs/analysis/pcmci/pcmci_summary.json')
d=json.loads(p.read_text())
groups=[{tuple(e) for e in d[k] if e[0]!=e[1]}
        for k in ['confirmed_edges','te_only_edges','pcmci_only_edges']]
assert [len(g) for g in groups]==[44,32,6]
assert sum(len(g) for g in groups)==len(set.union(*groups))==82
assert len([e for e in d['pcmci_only_edges'] if e[0]==e[1]])==10
report['pcmci_inter_node_counts']=[44,32,6]
report['pcmci_excluded_self_pairs']=10
from evcs_station_graph.evaluation.rules import fit_frozen_event_rule, visible_event_scores
rule=fit_frozen_event_rule(b)
scores=visible_event_scores(b,b.split_origins['test'],score_stats={
    k:np.asarray(v,dtype=np.float32) for k,v in rule.score_stats.items()})
pred=pd.read_csv('outputs/experiments/SG-EXP-004/20260731-102456/seed-2024/predictions.csv.gz')
pred=pred[pred['split']=='test'].copy()
assert len(pred)==712360
assert int(pred.target_event.sum())==10160
assert int(pred.rule_trigger.sum())==3060
report['dual_definition_counts_verified_from_predictions']={
    'prediction_keys':len(pred),'target_event':int(pred.target_event.sum()),
    'rule_trigger':int(pred.rule_trigger.sum())}
origin_rows={int(o):i for i,o in enumerate(b.split_origins['test'])}
pred['score']=[scores[origin_rows[int(o)],int(n)] for o,n in zip(pred.origin_index,pred.node_index)]
q50,q95=np.percentile(scores[scores>0],[50,95])
pred['group']=pd.cut(pred.score,[0,1e-6,q50,q95,np.inf],labels=['zero','low','mid','high'],include_lowest=True)
pred['absolute_error']=(pred.y_pred-pred.y_true).abs()
groups_table=pred.groupby('group',observed=True).absolute_error.agg(['count','mean'])
assert int(groups_table['count'].sum())==712360
assert abs(np.average(groups_table['mean'],weights=groups_table['count'])-pred.absolute_error.mean())<1e-12
report['intensity_bins']={'model':'AdaptiveGraph','seed':2024,'q50':float(q50),'q95':float(q95),
                         'groups':json.loads(groups_table.to_json(orient='index'))}
out=Path('outputs/figures/priority-review-20260907/data_checks.json')
out.write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False,indent=2))
