#!/usr/bin/env python3
"""Build an allowlisted portable upload archive, never a whole-repository zip."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import tarfile
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from evcs_station_graph.eventtime.data import FrozenData
from evcs_station_graph.eventtime.models import MODELS
from evcs_station_graph.eventtime.runner import default_config


def build(out, gate_control=False):
    if out.exists():
        raise FileExistsError(f'Refusing overwrite: {out}')
    data = ROOT/'data/eventtime/dataset.npz'
    if not data.exists():
        data = ROOT/'outputs/visibility/SG-DATA-006-eventtime-v1/dataset.npz'
    frozen = FrozenData(data)
    files = {str(p.relative_to(ROOT)): p.read_bytes() for p in (ROOT/'src').rglob('*.py')}
    paths = ['scripts/eventtime_experiment.py', 'scripts/parallel_eventtime.py', 'scripts/package_eventtime.py', 'scripts/finalize_eventtime.py',
             'tests/test_eventtime_experiment.py', 'cloud/eventtime/requirements.txt',
             'cloud/eventtime/run_autodl.sh', 'cloud/eventtime/README.md']
    for name in paths:
        files[name] = (ROOT/name).read_bytes()
    if gate_control:
        from gate_control_experiment import config, NAMES, SEEDS
        for name in ('scripts/gate_control_experiment.py', 'tests/test_gate_control.py',
                     'cloud/eventtime/run_gate_control.sh', 'docs/thesis/SG-EXP-027-paired-gate-control.md'):
            files[name] = (ROOT/name).read_bytes()
        files['configs/gate_control.json'] = json.dumps(
            [config(n, s, 'formal') for s in SEEDS for n in NAMES], indent=2).encode()
        files['GATE_CONTROL_PROVENANCE.json'] = json.dumps(dict(experiment='SG-EXP-027',
            source_base='2eb44c2', formal_runs=6, data_sha256=frozen.digest,
            definition='sigmoid(mean_node(W_gate([H,M]))); same active parameters',
            configuration_frozen_before_training=True), indent=2).encode()
    files['README.md'] = (ROOT/'cloud/eventtime/README.md').read_bytes()
    files['data/eventtime/dataset.npz'] = data.read_bytes()
    files['pytest.ini'] = b'[pytest]\npythonpath = src .\ntestpaths = tests\naddopts = -q\n'
    files['configs/suite.json'] = json.dumps({name: default_config(name, 2024) for name in MODELS}, indent=2).encode()
    files['configs/smoke.json'] = json.dumps(default_config('mrg_full', 2024, True), indent=2).encode()
    files['PROVENANCE.json'] = json.dumps(dict(protocol='SG-DATA-006-eventtime-v1', experiment='SG-EXP-019',
        data_sha256=frozen.digest, original_protocol_sha256='c940399c728b5bc1a5cbc1055243fed516817c89a79e75c76519de499c284c0e',
        raw_records_included=False, legacy_checkpoints_compatible=False, original_test_previously_seen=True,
        task='event-time behavior to retrospective session-energy proxy; zero ingestion delay assumed',
        official_agcrn_reference='https://github.com/LeiBAI/AGCRN/tree/master/model'), indent=2).encode()
    manifest = {k: hashlib.sha256(v).hexdigest() for k,v in sorted(files.items())}
    files['BUNDLE_MANIFEST.json'] = json.dumps(manifest, indent=2).encode()
    out.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(out, 'w:gz') as tar:
        for name, value in sorted(files.items()):
            info = tarfile.TarInfo('evcs-eventtime/'+name)
            info.size = len(value)
            info.mode = 0o644
            info.mtime = 0
            tar.addfile(info, io.BytesIO(value))
    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    out.with_suffix(out.suffix+'.sha256').write_text(f'{digest}  {out.name}\n')
    print(json.dumps(dict(archive=str(out.resolve()), bytes=out.stat().st_size, sha256=digest, files=len(files)), indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--gate-control', action='store_true')
    args = p.parse_args()
    build(args.out, gate_control=args.gate_control)
