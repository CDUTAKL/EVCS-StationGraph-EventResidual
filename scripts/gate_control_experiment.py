#!/usr/bin/env python3
"""Six paired SG-EXP-027 runs; never invokes the old 36-run suite."""
import argparse
import json
import os
from pathlib import Path
import sys
import time

os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from evcs_station_graph.eventtime.data import DATA_SHA256, FrozenData, sha256
from evcs_station_graph.eventtime.models import build_model, count_parameters
from evcs_station_graph.eventtime.runner import default_config, train, export, write_json

NAMES = ('mrg_full', 'mrg_shared_gate')
SEEDS = (2024, 2025, 2026)


def config(name, seed, stage):
    cfg = default_config(name, seed, smoke=stage == 'smoke')
    cfg['experiment'] = 'SG-EXP-027'
    if stage == 'benchmark':
        cfg.update(mode='BENCHMARK_NOT_SCIENTIFIC_EVIDENCE', max_epochs=2,
                   train_limit=2560, eval_limit=512)
    return cfg


def verify_bundle():
    path = ROOT/'BUNDLE_MANIFEST.json'
    if path.exists():
        for name, digest in json.loads(path.read_text()).items():
            if sha256(ROOT/name) != digest:
                raise ValueError(f'Frozen bundle drift: {name}')
        frozen = json.loads((ROOT/'configs/gate_control.json').read_text())
        expected = [config(n, s, 'formal') for s in SEEDS for n in NAMES]
        if frozen != expected:
            raise ValueError('Frozen gate configuration drift')


def summary(out):
    records = []
    for seed in SEEDS:
        for name in NAMES:
            folder = out/'formal'/name/f'seed-{seed}'
            manifest = json.loads((folder/'manifest.json').read_text())
            for f, digest in manifest.items():
                if sha256(folder/f) != digest:
                    raise ValueError(f'Result hash mismatch: {folder/f}')
            cfg = json.loads((folder/'config_resolved.json').read_text())
            expected = config(name, seed, 'formal')
            metadata = {'dataset_sha256', 'code_sha256', 'contract', 'trainable_parameters'}
            if (set(cfg) != set(expected) | metadata or
                    any(cfg.get(k) != v for k, v in expected.items()) or
                    cfg.get('dataset_sha256') != DATA_SHA256 or
                    cfg.get('trainable_parameters') != 32714):
                raise ValueError(f'Result configuration mismatch: {folder}')
            records.append(dict(model=name, seed=seed,
                                metrics=json.loads((folder/'metrics.json').read_text())))
    write_json(out/'summary.json', dict(experiment='SG-EXP-027', verified_runs=6,
                                      expected_runs=6, records=records))
    print('6/6 verified paired formal runs', flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage', choices=('check', 'smoke', 'benchmark', 'formal', 'summary'))
    p.add_argument('--device', choices=('cpu', 'cuda'), default='cuda')
    p.add_argument('--out', type=Path, default=ROOT/'results')
    args = p.parse_args()
    verify_bundle()
    if args.stage == 'summary':
        summary(args.out)
        return
    path = ROOT/'data/eventtime/dataset.npz'
    if not path.exists():
        path = ROOT/'outputs/visibility/SG-DATA-006-eventtime-v1/dataset.npz'
    data = FrozenData(path)
    params = {n: count_parameters(build_model(n, data.arrays['graphs'])) for n in NAMES}
    if len(set(params.values())) != 1:
        raise ValueError('Unequal trainable capacity')
    if args.stage == 'check':
        print(json.dumps(dict(data_sha256=data.digest, parameters=params, formal_runs=6,
                             configuration=[config(n, s, 'formal') for s in SEEDS for n in NAMES]), indent=2))
        return
    seeds = SEEDS if args.stage == 'formal' else (2024,)
    for seed in seeds:
        for name in NAMES:
            cfg = config(name, seed, args.stage)
            folder = args.out/args.stage/name/f'seed-{seed}'
            start = time.monotonic()
            print(f'START {args.stage} {name} seed={seed}', flush=True)
            train(data, cfg, folder, device=args.device)
            export(data, cfg, folder, device=args.device)
            elapsed = time.monotonic()-start
            print(f'COMPLETE {args.stage} {name} seed={seed} seconds={elapsed:.2f}', flush=True)
    if args.stage == 'formal':
        summary(args.out)


if __name__ == '__main__':
    main()
