#!/usr/bin/env python3
"""Portable CLI: python scripts/eventtime_experiment.py --help."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))

from evcs_station_graph.eventtime.data import FrozenData, sha256
from evcs_station_graph.eventtime.models import MODELS, PHASE1, PHASE2, build_model, count_parameters, matched_width
from evcs_station_graph.eventtime.runner import default_config, train, export, write_json, setup


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['check', 'smoke', 'benchmark', 'phase1', 'phase2', 'all', 'train', 'evaluate', 'summary'])
    parser.add_argument('--data', type=Path)
    parser.add_argument('--out', type=Path, default=ROOT/'results')
    parser.add_argument('--device', choices=['cpu','cuda'], default='cuda')
    parser.add_argument('--model', choices=MODELS, default='mrg_full')
    parser.add_argument('--seed', choices=[2024,2025,2026], type=int, default=2024)
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--run-stage', choices=['smoke', 'benchmark', 'formal'])
    args = parser.parse_args()
    bundle_manifest = ROOT/'BUNDLE_MANIFEST.json'
    if bundle_manifest.exists():
        hashes = json.loads(bundle_manifest.read_text())
        for name, digest in hashes.items():
            if sha256(ROOT/name) != digest:
                raise ValueError(f'Bundle hash mismatch: {name}; rebuild/version rather than patch a frozen upload')
        snapshot = json.loads((ROOT/'configs/suite.json').read_text())
        if snapshot != {name: default_config(name, 2024) for name in MODELS}:
            raise ValueError('Frozen suite configuration drift')
    path = args.data or ROOT/'data/eventtime/dataset.npz'
    if args.data is None and not path.exists():
        path = ROOT/'outputs/visibility/SG-DATA-006-eventtime-v1/dataset.npz'
    if args.command == 'summary':
        records = []
        for p in sorted(args.out.glob('formal/*/seed-*/metrics.json')):
            folder = p.parent
            manifest = json.loads((folder/'manifest.json').read_text())
            if not all(sha256(folder/k) == v for k,v in manifest.items()):
                raise ValueError(f'Result digest mismatch: {folder}')
            record = json.loads(p.read_text())
            cfg = json.loads((folder/'config_resolved.json').read_text())
            records.append(dict(model=cfg['model'], seed=cfg['seed'], metrics=record))
        write_json(args.out/'summary.json', dict(completed=len(records), expected=36, records=records))
        print(f'{len(records)}/36 verified formal runs. No significance claim from this summary.')
        return
    data = FrozenData(path)
    if args.command == 'check':
        import torch
        with torch.random.fork_rng(devices=[]):
            params = {name: count_parameters(build_model(name, data.arrays['graphs'])) for name in MODELS}
        print(json.dumps(dict(status='contracts_passed', data_sha256=data.digest,
             formal_runs=36, matched_tcn_width=matched_width(), trainable_parameters=params,
             split_origins={s:len(data.arrays[s+'_origins']) for s in ('train','tuning','calibration','test')},
             cuda_available=torch.cuda.is_available(), training_not_started=True), indent=2))
        return
    run_stage = args.run_stage or ('smoke' if args.command == 'smoke' else 'benchmark' if args.command == 'benchmark' else 'formal')
    setup(args.seed, args.device)
    names = MODELS if args.command in ('all','smoke') else PHASE1 if args.command=='phase1' else PHASE2 if args.command=='phase2' else (args.model,)
    seeds = (2024,2025,2026) if args.command in ('all','phase1','phase2') else (args.seed,)
    for name in names:
        for seed in seeds:
            cfg = default_config(name, seed, smoke=run_stage == 'smoke')
            namespace = run_stage
            if run_stage == 'benchmark':
                cfg.update(mode='BENCHMARK_NOT_SCIENTIFIC_EVIDENCE', max_epochs=2, train_limit=2560, eval_limit=512)
            folder = args.out/namespace/name/f'seed-{seed}'
            if args.command != 'evaluate':
                train(data, cfg, folder, device=args.device, resume=args.resume)
            export(data, cfg, folder, device=args.device)
            print(f'Verified artifacts: {folder}', flush=True)


if __name__ == '__main__':
    main()
