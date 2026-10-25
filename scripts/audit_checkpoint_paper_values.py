#!/usr/bin/env python3
"""Check selected paper MAE mean/SD cells against cross-protocol replay."""
import argparse,json
from pathlib import Path
import numpy as np

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--results',type=Path);ap.add_argument('--archived',type=Path);ap.add_argument('--out',type=Path,required=True);args=ap.parse_args()
 if bool(args.results)==bool(args.archived):ap.error('Use exactly one of --results or --archived')
 if args.archived:
  original=json.loads(args.archived.read_text());groups={}
  for row in original['runs']:
   groups.setdefault(row['component'],{'runs':[]})['runs'].append({**row,'replayed_mae':row['recomputed_metrics']['mae']})
 else:
  s=json.loads((args.results/'summary.json').read_text());groups=s['protocols']
 targets={
 'sg019':{'agcrn_full':(.03743,.00022,5),'mrg_equal_beta':(.03862,.00028,5),'mrg_full':(.03890,.00010,5),'mrg_no_skip':(.03900,.00051,5),'mrg_no_refine':(.03931,.00031,5),'mrg_pattern':(.03948,.00031,5),'mrg_fixed_gate':(.04111,.00147,5),'mrg_load':(.04315,.00073,5),'mrg_event':(.04559,.00027,5),'mrg_self_loop':(.04610,.00057,5),'tcn':(.04629,.00019,5),'tcn_wide':(.04634,.00029,5)},
 'sg027':{'mrg_full':(.038677,.000289,6),'mrg_shared_gate':(.039744,.000142,6)},
 'sg028':{'mrg_full':(.081067,.000304,6),'tcn_wide':(.083888,.000180,6),'agcrn_full':(.083268,.000552,6),'mrg_shared_gate':(.083325,.000713,6)},
 'legacy':{'SG-EXP-003':(.01376,.00023,5),'SG-EXP-002':(.02952,.00014,5),'SG-EXP-004':(.01396,.00017,5)}}
 locations={'sg019':'表3-2 全局MAE','sg027':'表3-9 整体MAE','sg028':'表3-3 MAE','legacy':'表3-4 MAE（仅三模型行）'}
 rows=[]
 for component,models in targets.items():
  for model,(mean,sd,places) in models.items():
   runs=[r for r in groups[component]['runs'] if r['model']==model]
   values=np.array([r['replayed_mae'] for r in runs]);a=float(values.mean());b=float(values.std(ddof=1))
   tol=.5*10**(-places)
   status='PASS' if len(runs)==3 and all(r['status']=='PASS' for r in runs) and abs(a-mean)<tol and abs(b-sd)<tol else 'FAIL'
   rows.append({'component':component,'model':model,'paper_location':locations[component],'paper_mean':mean,'paper_sample_sd':sd,'decimal_places':places,'replay_mean':a,'replay_sample_sd':b,'status':status})
 result={'status':'PASS' if all(r['status']=='PASS' for r in rows) else 'PARTIAL','scope':'MAE mean and sample SD only; other metrics are checked per run separately','input_kind':'archived-prediction metrics' if args.archived else 'checkpoint-forward metrics','cells':rows,'passed_model_rows':sum(r['status']=='PASS' for r in rows),'total_model_rows':len(rows),'retraining_performed':False}
 args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'status':result['status'],'passed_model_rows':result['passed_model_rows'],'total_model_rows':len(rows)},ensure_ascii=False))
if __name__=='__main__':main()
