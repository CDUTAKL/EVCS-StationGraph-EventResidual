#!/usr/bin/env python3
"""Independently recalculate six metric groups from archived test predictions."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
import pandas as pd

def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def measures(y,p,t):
 e=np.abs(y.astype('float64')-p.astype('float64'))
 return {'mae':float(e.mean()),'rmse':float(np.sqrt((e**2).mean())), 'event_mae':float(e[t].mean()),'stable_mae':float(e[~t].mean()),'by_horizon_mae':e.mean(axis=(0,2)).tolist(),'by_node_mae':e.mean(axis=(0,1)).tolist()}
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--bundle',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);args=ap.parse_args();rows=[]
 for component in ['legacy','sg019','sg027','sg028']:
  base=args.bundle/'components'/component
  dirs=sorted((base/'results').glob('SG-EXP-*/seed-*')) if component=='legacy' else sorted((base/'results/formal').glob('*/seed-*'))
  for run in dirs:
   saved=json.loads((run/'metrics.json').read_text())
   if component=='legacy':
    path=run/'predictions.csv.gz';df=pd.read_csv(path).sort_values(['origin_index','horizon','node_index'])
    y=df.y_true.to_numpy().reshape(-1,4,10);p=df.y_pred.to_numpy().reshape(-1,4,10);t=df.target_event.to_numpy().reshape(-1,4,10)
    node_ids=df.node_id.iloc[:10].tolist()
    target={'mae':saved['global']['mae'],'rmse':saved['global']['rmse'],'event_mae':saved['event_window']['mae'],'stable_mae':saved['stable_window']['mae'],'by_horizon_mae':[saved['by_horizon'][str(i)]['mae'] for i in range(1,5)],'by_node_mae':[saved['by_node'][n]['mae'] for n in node_ids]}
   else:
    path=run/'predictions_test.npz'
    with np.load(path,allow_pickle=False) as f:y=f['y_true'];p=f['y_pred'];t=f['target_event']
    target=saved['splits']['test']
   v=measures(y,p,t);diff={k:float(np.abs(np.asarray(a)-np.asarray(target[k])).max()) for k,a in v.items()}
   row={'component':component,'model':run.parent.name,'seed':int(run.name.split('-')[1]),'keys':int(y.size),'prediction_sha256':sha(path),'metric_sha256':sha(run/'metrics.json'),'recomputed_metrics':v,'max_metric_abs_diff':max(diff.values()),'metric_abs_differences':diff,'status':'PASS' if max(diff.values())<=1e-7 else 'FAIL'}
   rows.append(row)
 result={'status':'PASS' if len(rows)==63 and all(r['status']=='PASS' for r in rows) else 'FAIL','runs':rows,'expected_runs':63,'metric_atol':1e-7,'scope':'archived prediction to six metric groups; no checkpoint inference performed by this script','retraining_performed':False}
 args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'status':result['status'],'runs':len(rows),'max_metric_abs_diff':max(r['max_metric_abs_diff'] for r in rows)}))
 if result['status']!='PASS':raise SystemExit(1)
if __name__=='__main__':main()
