"""Read frozen prediction arrays independently; write only this review's outputs.

No training, model fitting, checkpoint forward pass or original artifact edits.
"""
import csv
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sources = {}


def read_npz(path):
    path = Path(path)
    sources[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    with np.load(path, allow_pickle=False) as a:
        return {k: a[k] for k in a.files}


def metrics(y, p, event):
    e = np.abs(y.astype('float64') - p.astype('float64'))
    return {'mae': float(e.mean()), 'rmse': float(np.sqrt(np.square(e).mean())),
            'zero_mae': float(e[y == 0].mean()),
            'nonzero_mae': float(e[y != 0].mean()),
            'event_mae': float(e[event].mean()), 'n': int(e.size),
            'zero_fraction': float((y == 0).mean())}


def main():
    evidence = ROOT / 'outputs/evidence/checkpoint-replay-20261012/components'
    result = {'scope': 'new independent arithmetic on archived arrays, not a new model forward run'}
    caltech = {}
    reported = json.loads((ROOT / 'docs/thesis/revision-20261015-final/caltech-main-strata.json').read_text())
    for item in reported['sources']:
        assert hashlib.sha256((ROOT/item['path']).read_bytes()).hexdigest() == item['sha256']
    for model in ('agcrn_full', 'mrg_full', 'tcn_wide', 'tcn'):
        rows = []
        for seed in (2024, 2025, 2026):
            a = read_npz(evidence / f'sg019/results/formal/{model}/seed-{seed}/predictions_test.npz')
            rows.append(metrics(a['y_true'], a['y_pred'], a['target_event']))
        summary = {k: float(np.mean([r[k] for r in rows])) for k in rows[0]}
        for k, v in zip(reported['metrics'], reported['rows'][model]['mean']):
            assert abs(summary[k] - v) < 1e-12
        caltech[model] = {'seeds': rows, 'mean': summary}
    m, t = caltech['mrg_full']['mean'], caltech['tcn_wide']['mean']
    net = t['mae'] - m['mae']
    result['caltech_primary'] = {'models': caltech,
        'global_relative_reduction': net / t['mae'],
        'zero_group_share_of_net_reduction': m['zero_fraction'] * (t['zero_mae']-m['zero_mae']) / net}

    mdp_dir = ROOT / 'outputs/analysis/JPL-MDP-20261014'
    mdp_report = json.loads((mdp_dir/'audit.json').read_text())
    mdp_manifest=json.loads((mdp_dir/'output-manifest.json').read_text())
    assert all(hashlib.sha256((mdp_dir/rel).read_bytes()).hexdigest()==sha for rel,sha in mdp_manifest.items())
    for source in mdp_report['source_provenance']:
        for relative,sha in source['source_hashes'].items():
            assert hashlib.sha256((evidence/'sg028'/relative).read_bytes()).hexdigest()==sha
    mdp_rows = []
    for sr in mdp_report['seeds']:
        seed = sr['seed']
        original = read_npz(evidence / f'sg028/results/formal/mrg_full/seed-{seed}/predictions_test.npz')
        y, event, trigger = [original[k] for k in ('y_true', 'target_event', 'rule_trigger')]
        learned = read_npz(mdp_dir/f'seed-{seed}-learned.npz')['y_pred']
        assert np.max(np.abs(learned-original['y_pred'])) <= 5e-6
        runs = {}
        for name, report in sr['runs'].items():
            p = read_npz(mdp_dir/f'seed-{seed}-{name}.npz')['y_pred']
            err = np.abs(p.astype('float64')-y.astype('float64'))
            assert abs(err.mean()-report['mae']) < 1e-12
            cells = {}
            for label in (0, 1):
                for rule in (0, 1):
                    mask = (event == label) & (trigger == rule)
                    cells[f'{label}_{rule}'] = {'n': int(mask.sum()), 'mae': float(err[mask].mean()),
                        'error_share': float(err[mask].sum()/err.sum())}
            closed = sum(c['mae']*c['n'] for c in cells.values()) / err.size
            assert abs(closed-err.mean()) < 1e-12
            runs[name] = {'mae': float(err.mean()), 'event_mae': float(err[event].mean()), 'cells': cells}
        rep = read_npz(mdp_dir/f'seed-{seed}-equal-reparameterized.npz')['y_pred']
        gap = float(np.max(np.abs(rep-learned)))
        assert gap <= 5e-6
        mdp_rows.append({'seed': seed, 'runs': runs, 'reparameterized_max_difference': gap})
    result['jpl_mdp'] = mdp_rows

    ca = json.loads((ROOT/'outputs/analysis/JPL-calibration-20261015/audit.json').read_text())
    assert all(hashlib.sha256(Path(x['path']).read_bytes()).hexdigest()==x['sha256'] for x in ca['inputs'])
    calibration = []
    for sr in ca['runs']:
        seed = sr['seed']
        base = Path(ca['source']) / f'seed-{seed}'
        c, t = [read_npz(base/f'predictions_{part}.npz') for part in ('calibration', 'test')]
        assert not np.intersect1d(c['target_timestamps_ns'],t['target_timestamps_ns']).size
        residual = np.abs(c['y_true']-c['y_pred'])
        def q(v):
            z = np.sort(v.ravel())
            return z[int(np.ceil((len(z)+1)*.9))-1]
        nodeq = np.array([q(residual[:,:,j]) for j in range(10)])[None,None,:]
        stableq = np.array([q(residual[:,:,j][~c['rule_trigger'][:,:,j]]) for j in range(10)])[None,None,:]
        triggerq = q(residual[c['rule_trigger']])
        y,p=t['y_true'],t['y_pred']
        paths={}
        for name,half in [('node',np.broadcast_to(nodeq,y.shape)),('behavior',np.where(t['rule_trigger'],triggerq,stableq))]:
            lower,upper=p-half,p+half
            covered=(y>=lower)&(y<=upper)
            score=upper-lower+20*np.maximum(lower-y,0)+20*np.maximum(y-upper,0)
            groups={}
            for g,mask in [('overall',np.ones(y.shape,bool)),('event',t['target_event']),('nonzero',y!=0),('zero',y==0)]:
                groups[g]={'n':int(mask.sum()),'coverage':float(covered[mask].mean()),
                    'width':float((upper-lower)[mask].mean()),'interval_score':float(score[mask].mean())}
                assert abs(groups[g]['coverage']-sr['paths'][name][g]['coverage']) < 1e-12
                assert abs(groups[g]['interval_score']-sr['paths'][name][g]['interval_score']) < 1e-12
            paths[name]=groups
        calibration.append({'seed':seed,'paths':paths})
    result['jpl_calibration']=calibration

    ad = ROOT/'outputs/analysis/AdaptiveGraph-CUDA-20261015'
    status=json.loads((ad/'status.json').read_text())
    ad_manifest=json.loads((ad/'output-manifest.json').read_text())
    assert all(hashlib.sha256((ad/rel).read_bytes()).hexdigest()==sha for rel,sha in ad_manifest.items())
    package=ROOT/'outputs/evidence/AdaptiveGraph-CUDA-replay-20261014'
    package_manifest=json.loads((package/'MANIFEST.json').read_text())
    assert all(hashlib.sha256((package/rel).read_bytes()).hexdigest()==sha for rel,sha in package_manifest.items())
    adaptive=[]
    for run in status['runs']:
        seed=run['seed']
        path=ROOT/f'outputs/evidence/AdaptiveGraph-CUDA-replay-20261014/legacy/results/SG-EXP-004/seed-{seed}/predictions.csv.gz'
        sources[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
        with gzip.open(path,'rt') as f:
            rows=list(csv.DictReader(f))
        rows.sort(key=lambda r:(int(r['origin_index']),int(r['horizon']),int(r['node_index'])))
        keys=[(r['origin_index'],r['horizon'],r['node_index']) for r in rows]
        assert len(set(keys))==len(keys)==712360
        truth=np.array([float(r['y_true']) for r in rows])
        archived=np.array([float(r['y_pred']) for r in rows])
        del rows,keys
        values=read_npz(ad/f'seed-{seed}-predictions.npz')
        gaps={name:float(np.max(np.abs(values[name].ravel()-archived))) for name in ('native_cpu','native_cuda','cpu_with_cuda_adjacency')}
        assert gaps['native_cuda']<=5e-6 and gaps['cpu_with_cuda_adjacency']<=5e-6 and gaps['native_cpu']>5e-6
        cpu=read_npz(ad/f'seed-{seed}-cpu-adjacency.npz'); cuda=read_npz(ad/f'seed-{seed}-cuda-adjacency.npz')
        changed=np.flatnonzero(np.any(np.sort(cpu['topk_indices'],axis=1)!=np.sort(cuda['topk_indices'],axis=1),axis=1)).tolist()
        assert set(changed)<=set(cpu['ambiguous_rows'].tolist())
        assert changed==run['changed_neighbor_rows']
        adaptive.append({'seed':seed,'n_keys':len(truth),'gaps':gaps,
            'cuda_mae':float(np.abs(values['native_cuda'].ravel()-truth).mean()),
            'archived_mae':float(np.abs(archived-truth).mean()),'changed_tied_rows':changed})
    result['adaptivegraph']=adaptive
    result['sources']=sources
    result['hash_manifests_verified']={'caltech_predictions':len(reported['sources']),
        'jpl_mdp_outputs':len(mdp_manifest),'jpl_calibration_inputs':len(ca['inputs']),
        'adaptivegraph_outputs':len(ad_manifest),'adaptivegraph_input_package':len(package_manifest)}
    result['status']='PASS'
    (OUT/'primary-evidence-recomputation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':result['status'],'source_files':len(sources),
        'caltech_reduction':result['caltech_primary']['global_relative_reduction'],
        'zero_share':result['caltech_primary']['zero_group_share_of_net_reduction'],
        'mdp_variants':sum(len(x['runs']) for x in mdp_rows),'adaptive_cuda_gaps':[x['gaps']['native_cuda'] for x in adaptive]},ensure_ascii=False))


if __name__=='__main__':
    main()
