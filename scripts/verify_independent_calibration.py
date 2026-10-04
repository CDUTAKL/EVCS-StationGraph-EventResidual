"""Independent sorted-residual/interval reconstruction of SG-EXP-023 evidence."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from analyze_demand_warning import sha256_file, write_json

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/analysis/SG-EXP-023-independent-calibration'


def main():
    s = json.loads((OUT / 'summary.json').read_text())
    manifest = json.loads((OUT / 'manifest.json').read_text())
    for name, digest in manifest['files'].items():
        assert sha256_file(OUT / name) == digest, name
    for name, digest in s['source_hashes'].items():
        assert sha256_file(Path(name) if Path(name).is_absolute() else ROOT / name) == digest, name
    cfg = json.loads((OUT / 'config_resolved.json').read_text())
    root = ROOT / cfg['source_root'] / 'mrg_full'
    rows = pd.read_csv(OUT / 'coverage_per_seed.csv')
    max_gap = 0.
    distributions = {}
    for seed in cfg['seeds']:
        folder = root / f'seed-{seed}'
        config = json.loads((folder / 'config_resolved.json').read_text())
        assert config['selection'] == 'tuning_original_unit_MAE' and config['mode'] == 'formal'
        assert config['dataset_sha256'] == s['source_hashes'][cfg['data']]
        with np.load(folder / 'predictions_calibration.npz') as f:
            c = {k:f[k] for k in f.files}
        with np.load(folder / 'predictions_test.npz') as f:
            t = {k:f[k] for k in f.files}
        with np.load(OUT / f'intervals_seed-{seed}.npz') as f:
            intervals = {k:f[k] for k in f.files}
        ce, te = abs(c['y_true']-c['y_pred']), abs(t['y_true']-t['y_pred'])
        def sorted_rank(scores):
            ordered = np.sort(scores.ravel())
            # Exact integer form of ceil(0.9*(n+1)), separate from partition implementation.
            rank = (9 * (len(ordered)+1) + 9) // 10
            return ordered[rank-1]
        q_node = np.array([sorted_rank(ce[:,:,n]) for n in range(10)])
        q_stable = np.array([sorted_rank(ce[:,:,n][~c['rule_trigger'][:,:,n]]) for n in range(10)])
        q_trigger = sorted_rank(ce[c['rule_trigger']])
        for method in cfg['calibration_methods']:
            q = np.broadcast_to(q_node[None,None,:],te.shape) if method=='node_standard' else np.where(t['rule_trigger'], q_trigger, q_stable[None,None,:])
            np.testing.assert_array_equal(q, intervals[method+'_halfwidth'])
            np.testing.assert_array_equal(t['y_pred']-q, intervals[method+'_lower'])
            np.testing.assert_array_equal(t['y_pred']+q, intervals[method+'_upper'])
            for group, mask in [('all',np.ones(te.shape,bool)),('event',t['target_event']),('stable',~t['target_event'])]:
                r = rows[(rows.seed==seed)&(rows.method==method)&(rows.group==group)].iloc[0]
                assert r['n']==mask.sum()
                actual = [(te[mask]<=q[mask]).mean(),(2*q[mask]).mean(),(2*q[mask]+20*np.maximum(te[mask]-q[mask],0)).mean()]
                gap = max(abs(float(r[k])-v) for k,v in zip(['coverage','width','interval_score'],actual))
                max_gap = max(max_gap,gap)
                assert gap<1e-12
        distributions = {split:dict(zero_rate=float((v['y_true']==0).mean()),target_event_rate=float(v['target_event'].mean()),trigger_rate=float(v['rule_trigger'].mean()),triggered_event_keys=int((v['rule_trigger']&v['target_event']).sum())) for split,v in [('calibration',c),('test',t)]}
    # Recompute group MAEs independently from source predictions.
    group_table = pd.read_csv(OUT/'innovation_by_group.csv')
    for model in cfg['innovation_models']:
        for seed in cfg['seeds']:
            with np.load(ROOT/cfg['source_root']/model/f'seed-{seed}/predictions_test.npz') as f:
                e=abs(f['y_true']-f['y_pred'])
                group_masks={'all':np.ones(e.shape,bool),'event':f['target_event'],'stable':~f['target_event'],'zero':f['y_true']==0,'nonzero':f['y_true']!=0}
            for group,m in group_masks.items():
                r=group_table[(group_table.model==model)&(group_table.seed==seed)&(group_table.group==group)].iloc[0]
                assert r['n']==m.sum() and abs(r.mae-e[m].mean())<1e-12
    report=dict(status='passed',original_source_files_verified=len(s['source_hashes']),
                independent_sorted_quantiles_exact=True,interval_endpoints_exact=True,
                max_coverage_width_score_reconstruction_gap=max_gap,innovation_groups_verified=135,
                distributions=distributions,summary_sha256=sha256_file(OUT/'summary.json'),
                script_sha256=sha256_file(Path(__file__)))
    write_json(OUT.parent/'SG-EXP-023-independent-verification.json',report)
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
