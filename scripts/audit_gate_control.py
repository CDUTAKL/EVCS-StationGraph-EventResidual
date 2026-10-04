#!/usr/bin/env python3
"""Read-only independent SG-EXP-027 artifact audit; never changes remote runs."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from evcs_station_graph.eventtime.data import FrozenData, sha256
from evcs_station_graph.eventtime.runner import write_json
from gate_control_experiment import config, NAMES, SEEDS

FROZEN_CODE = 'd40d609177089702c0799f106dbce19ce07e906f28410554506d74e1c39d0018'


def audit_predictions(a, split, p, reported):
    origins = p['origins']
    np.testing.assert_array_equal(origins, a[split+'_origins'])
    np.testing.assert_array_equal(p['node_ids'], a['node_ids'])
    indices = origins[:, None] + np.arange(1, 5)
    np.testing.assert_array_equal(p['y_true'], a['targets'][indices])
    np.testing.assert_array_equal(p['target_event'], a['target_event'][indices])
    trigger = np.repeat(a['rule_trigger'][origins, None, :], 4, axis=1)
    np.testing.assert_array_equal(p['rule_trigger'], trigger)
    np.testing.assert_array_equal(p['target_timestamps_ns'], a['timestamps_ns'][indices])
    np.testing.assert_array_equal(p['origin_cutoff_ns'], a['timestamps_ns'][origins]+900000000000)
    actual = p['y_true'].astype('float64')
    prediction = p['y_pred'].astype('float64')
    assert prediction.shape == actual.shape and np.isfinite(prediction).all()
    error = np.abs(actual-prediction)
    assert error.size == reported['n']
    computed = dict(n=int(error.size), mae=float(error.mean()),
                    rmse=float(np.sqrt(np.mean((actual-prediction)**2))))
    for key in ('mae', 'rmse'):
        np.testing.assert_allclose(computed[key], reported[key], atol=1e-12, rtol=0)
    event = p['target_event']
    for key, mask in (('event_mae', event), ('stable_mae', ~event)):
        computed[key] = float(error[mask].mean()) if mask.any() else None
        if computed[key] is None:
            assert reported[key] is None
        else:
            np.testing.assert_allclose(computed[key], reported[key], atol=1e-12, rtol=0)
    np.testing.assert_allclose(error.mean((0,2)), reported['by_horizon_mae'], atol=1e-12, rtol=0)
    np.testing.assert_allclose(error.mean((0,1)), reported['by_node_mae'], atol=1e-12, rtol=0)
    total, count = 0., 0
    for t, r in ((1,1), (1,0), (0,1), (0,0)):
        mask = (event == t) & (trigger == r)
        cell = reported['four_cells'][f'target_{t}_trigger_{r}']
        n, s = int(mask.sum()), float(error[mask].sum())
        assert cell['n'] == n
        np.testing.assert_allclose(cell['sum_absolute_error'], s, atol=1e-9, rtol=0)
        np.testing.assert_allclose(cell['error_contribution'], s/error.sum() if error.sum() else 0., atol=1e-12, rtol=0)
        if n:
            np.testing.assert_allclose(cell['mae'], s/n, atol=1e-12, rtol=0)
        else:
            assert cell['mae'] is None
        total += s
        count += n
    assert count == error.size
    np.testing.assert_allclose(total/count, computed['mae'], atol=1e-12, rtol=0)
    assert reported['four_cell_reconstruction_error'] <= 1e-9
    computed.update(origins=len(origins), verification='PASS')
    return computed


def audit_run(folder, data, name, seed):
    manifest = json.loads((folder/'manifest.json').read_text())
    required = {'best.pt','last.pt','config_resolved.json','environment.json','metrics.json',
                'train_log.json','exit_code.txt','run_summary.json',
                'predictions_tuning.npz','predictions_calibration.npz','predictions_test.npz'}
    assert required <= set(manifest)
    for file, digest in manifest.items():
        assert Path(file).name == file and sha256(folder/file) == digest, file
    cfg = json.loads((folder/'config_resolved.json').read_text())
    expected = config(name, seed, 'formal')
    metadata = {'dataset_sha256','code_sha256','contract','trainable_parameters'}
    assert set(cfg) == set(expected) | metadata
    assert all(cfg[k] == v for k,v in expected.items())
    assert cfg['dataset_sha256'] == data.digest and cfg['code_sha256'] == FROZEN_CODE
    assert cfg['trainable_parameters'] == 32714
    env = json.loads((folder/'environment.json').read_text())
    assert env['gpu'] == 'NVIDIA GeForce RTX 5090' and env['torch'] == '2.8.0+cu128'
    assert env['cuda'] == '12.8' and env['device'] == 'cuda'
    fingerprint = dict(config=expected, dataset_sha256=data.digest, code_sha256=FROZEN_CODE,
                       torch=env['torch'], device='cuda', gpu=env['gpu'])
    contract = hashlib.sha256(json.dumps(fingerprint,sort_keys=True).encode()).hexdigest()
    assert contract == cfg['contract']
    log = json.loads((folder/'train_log.json').read_text())
    assert [r['epoch'] for r in log] == list(range(1,len(log)+1))
    assert all(np.isfinite([r['train_standardized_mae'],r['tuning_mae'],r['seconds']]).all() for r in log)
    selected = min(log,key=lambda r:r['tuning_mae'])['epoch']
    best = torch.load(folder/'best.pt',map_location='cpu',weights_only=True)
    last = torch.load(folder/'last.pt',map_location='cpu',weights_only=True)
    assert best['contract'] == last['contract'] == contract
    assert best['epoch'] == selected and last['complete']
    assert last['history'] == log and last['epoch'] == len(log)
    assert len(log) <= 60 and (last['stale'] >= 8 or len(log) == 60)
    run = json.loads((folder/'run_summary.json').read_text())
    assert run['status'] == 'complete' and run['mode'] == 'formal' and run['contract'] == contract
    assert (folder/'exit_code.txt').read_text().strip() == '0'
    m = json.loads((folder/'metrics.json').read_text())
    assert m['selected_epoch'] == selected and m['mode'] == 'formal'
    assert m['unit'] == 'retrospective proxy kWh/15min'
    splits = {}
    for split in ('tuning','calibration','test'):
        with np.load(folder/f'predictions_{split}.npz',allow_pickle=False) as p:
            splits[split] = audit_predictions(data.arrays, split, p, m['splits'][split])
    return dict(model=name,seed=seed,status='PASS',trained_epochs=len(log),selected_epoch=selected,
                manifest_sha256=sha256(folder/'manifest.json'),manifest_files=len(manifest),
                contract_sha256=contract,code_sha256=FROZEN_CODE,dataset_sha256=data.digest,
                local_artifact=str(folder.resolve()),splits=splits)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=ROOT/'outputs/experiments/SG-EXP-027/recovered')
    args = p.parse_args()
    data = FrozenData(ROOT/'outputs/visibility/SG-DATA-006-eventtime-v1/dataset.npz')
    records = []
    for seed in SEEDS:
        for name in NAMES:
            folder = args.root/'formal'/name/f'seed-{seed}'
            if (folder/'manifest.json').exists():
                report = audit_run(folder,data,name,seed)
                records.append(report)
                write_json(args.root/f'audit_{name}_seed-{seed}.json',report)
    complete = len(records) == 6
    output = dict(experiment='SG-EXP-027',verified_runs=len(records),expected_runs=6,
                  status='PASS_COMPLETE' if complete else 'PASS_PARTIAL_NOT_FINAL',records=records,
                  verification_script_sha256=sha256(Path(__file__)),
                  limitations=['same historical test period, not unseen-period confirmation',
                               'proxy energy, not metered instantaneous power',
                               'three seeds do not replace temporal-block uncertainty'])
    if complete:
        output['test_summary'] = {name:{key:dict(mean=float(np.mean(values)),std_ddof1=float(np.std(values,ddof=1)))
            for key in ('mae','event_mae','stable_mae')
            for values in [[r['splits']['test'][key] for r in records if r['model']==name]]} for name in NAMES}
        output['paired_test_mae_shared_minus_full'] = [dict(seed=s,
            difference=next(r['splits']['test']['mae'] for r in records if r['model']=='mrg_shared_gate' and r['seed']==s)
                      -next(r['splits']['test']['mae'] for r in records if r['model']=='mrg_full' and r['seed']==s)) for s in SEEDS]
    write_json(args.root/'independent_audit_summary.json',output)
    print(json.dumps(dict(status=output['status'],verified_runs=len(records),expected_runs=6),indent=2))


if __name__ == '__main__':
    main()
