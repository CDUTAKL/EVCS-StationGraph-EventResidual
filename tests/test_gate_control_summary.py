"""Tiny file fixtures are not experiment results."""
import hashlib
import json
import pytest
import gate_control_experiment as cli


def fixture_runs(tmp_path):
    for seed in cli.SEEDS:
        for name in cli.NAMES:
            folder = tmp_path/'formal'/name/f'seed-{seed}'
            folder.mkdir(parents=True)
            cfg = cli.config(name, seed, 'formal')
            cfg.update(dataset_sha256='f663b510c75e203c8150f57c3765645f92b9a941e0745227c6ea078008a0dc8f',
                       code_sha256='a'*64, contract='b'*64, trainable_parameters=32714)
            (folder/'config_resolved.json').write_text(json.dumps(cfg))
            (folder/'metrics.json').write_text(json.dumps({'mode': 'formal'}))
            update_manifest(folder)
    return tmp_path


def update_manifest(folder):
    manifest = {name: hashlib.sha256((folder/name).read_bytes()).hexdigest()
                for name in ('config_resolved.json', 'metrics.json')}
    (folder/'manifest.json').write_text(json.dumps(manifest))


def test_summary_accepts_runner_provenance_without_false_config_drift(tmp_path):
    cli.summary(fixture_runs(tmp_path))
    summary = json.loads((tmp_path/'summary.json').read_text())
    assert summary['verified_runs'] == 6
    assert len(summary['records']) == 6


def test_summary_still_rejects_training_budget_drift(tmp_path):
    fixture_runs(tmp_path)
    folder = tmp_path/'formal/mrg_full/seed-2024'
    cfg = json.loads((folder/'config_resolved.json').read_text())
    cfg['max_epochs'] = 61
    (folder/'config_resolved.json').write_text(json.dumps(cfg))
    update_manifest(folder)
    with pytest.raises(ValueError, match='configuration mismatch'):
        cli.summary(tmp_path)
