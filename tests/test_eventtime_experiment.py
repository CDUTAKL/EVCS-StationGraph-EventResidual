"""Portable event-time experiment contracts; no legacy training entrypoint."""
import importlib.util
from pathlib import Path

import numpy as np
import pytest
import torch

ROOT = Path(__file__).resolve().parents[1]


def api():
    assert importlib.util.find_spec('evcs_station_graph.eventtime') is not None, 'new isolated experiment API missing'
    from evcs_station_graph.eventtime import models, runner, data
    return models, runner, data


def test_full_model_matches_frozen_architecture():
    models, _, _ = api()
    from evcs_station_graph.models.graph import StaticGraphForecast
    a = np.stack([np.eye(10)] * 3)
    old = StaticGraphForecast(7, 4, 10, list(a), hidden_dim=32, levels=6, history_steps=96)
    new = models.build_model('mrg_full', a)
    new.load_state_dict(old.state_dict(), strict=True)
    old.eval(); new.eval()
    x = torch.randn(2, 96, 10, 7)
    torch.testing.assert_close(new(x).prediction, old(x).prediction, rtol=0, atol=0)


def test_all_models_backward_and_ablation_parameters():
    models, _, _ = api()
    torch.set_num_threads(1)
    a = np.stack([np.eye(10)] * 3)
    for name in models.MODELS:
        m = models.build_model(name, a)
        y = m(torch.randn(2, 96, 10, 7)).prediction
        assert y.shape == (2, 4, 10)
        y.square().mean().backward()
        assert all(p.grad is not None for p in m.parameters() if p.requires_grad), name
        assert all(torch.isfinite(p.grad).all() for p in m.parameters() if p.requires_grad), name
    fixed = models.build_model('mrg_equal_beta', a)
    assert not fixed.relation_weights_gcn1.requires_grad
    assert not any('W_gate' in n for n, p in models.build_model('mrg_fixed_gate', a).named_parameters())
    assert not hasattr(models.build_model('mrg_no_refine', a), 'graph_mlp_refine')
    assert models.build_model('mrg_no_skip', a).skip_fusion.in_features == 32
    full = models.count_parameters(models.build_model('mrg_full', a))
    wide = models.count_parameters(models.build_model('tcn_wide', a))
    assert abs(wide / full - 1) < .05


def test_node_adaptive_convolution_matches_literal_loops():
    models, _, _ = api()
    torch.manual_seed(3)
    conv = models.NodeAdaptiveConv(2, 3, 2, 2)
    e = torch.randn(3, 2)
    x = torch.randn(1, 3, 2)
    a = torch.softmax(torch.relu(e @ e.T), dim=1)
    expected = torch.zeros(1, 3, 3)
    for n in range(3):
        for o in range(3):
            expected[0, n, o] = sum(e[n, d] * conv.bias_pool[d, o] for d in range(2))
            for k, support in enumerate([torch.eye(3), a]):
                for j in range(3):
                    for i in range(2):
                        for d in range(2):
                            expected[0, n, o] += support[n, j] * x[0, j, i] * e[n, d] * conv.weights_pool[d, k, i, o]
    torch.testing.assert_close(conv(x, e), expected)


def test_frozen_dataset_slicing_and_trigger():
    _, _, data = api()
    path = ROOT / 'data/eventtime/dataset.npz'
    if not path.exists():
        path = ROOT / 'outputs/visibility/SG-DATA-006-eventtime-v1/dataset.npz'
    d = data.FrozenData(path)
    ds = d.windows('train', limit=2)
    x, y, k = ds[0]
    raw = d.arrays
    np.testing.assert_allclose(x, (raw['features'][k-95:k+1] - raw['feature_mean']) / raw['feature_std'], atol=1e-6)
    np.testing.assert_allclose(y, (raw['targets'][k+1:k+5] - raw['target_mean']) / raw['target_std'], atol=1e-6)
    labels, triggers = d.masks(np.array([k]))
    assert labels.shape == triggers.shape == (1, 4, 10)
    assert np.array_equal(triggers[0, 0], raw['rule_trigger'][k])
    assert np.array_equal(triggers[0, 0], triggers[0, 3])


def test_four_cells_restore_total_error():
    _, runner, _ = api()
    y = np.array([1., 2., 3., 4.]).reshape(1, 2, 2)
    t = np.array([1, 1, 0, 0], dtype=bool).reshape(y.shape)
    r = np.array([1, 0, 1, 0], dtype=bool).reshape(y.shape)
    m = runner.metric_report(y, np.zeros_like(y), t, r)
    assert m['mae'] == 2.5
    assert sum(c['error_contribution'] for c in m['four_cells'].values()) == 1
    assert m['four_cell_reconstruction_error'] < 1e-9


def test_resume_exact_and_refuse_drift(tmp_path):
    _, runner, data = api()
    path = ROOT / 'data/eventtime/dataset.npz'
    if not path.exists():
        path = ROOT / 'outputs/visibility/SG-DATA-006-eventtime-v1/dataset.npz'
    d = data.FrozenData(path)
    cfg = runner.default_config('tcn', 2024, smoke=True)
    cfg['max_epochs'] = 2
    a = runner.train(d, cfg, tmp_path/'continuous', device='cpu')
    runner.train(d, cfg, tmp_path/'resumed', device='cpu', stop_after=1)
    b = runner.train(d, cfg, tmp_path/'resumed', device='cpu', resume=True)
    for key in a['model']:
        torch.testing.assert_close(a['model'][key], b['model'][key], rtol=0, atol=0)
    changed = dict(cfg, seed=2025)
    with pytest.raises(ValueError, match='contract'):
        runner.train(d, changed, tmp_path/'resumed', device='cpu', resume=True)


def test_portable_cli_check():
    import subprocess
    import sys
    import json
    script = ROOT/'scripts/eventtime_experiment.py'
    assert script.exists(), 'portable entrypoint missing'
    result = subprocess.run([sys.executable, str(script), 'check'], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    info = json.loads(result.stdout)
    assert info['formal_runs'] == 36
    assert info['data_sha256'] == 'f663b510c75e203c8150f57c3765645f92b9a941e0745227c6ea078008a0dc8f'


def test_export_and_selection_separation(tmp_path):
    import json
    _, runner, data = api()
    path = ROOT/'data/eventtime/dataset.npz'
    if not path.exists():
        path = ROOT/'outputs/visibility/SG-DATA-006-eventtime-v1/dataset.npz'
    class TrackedData(data.FrozenData):
        def windows(self, split, limit=None):
            touched.append(split)
            return super().windows(split, limit)
    touched = []
    d = TrackedData(path)
    cfg = runner.default_config('mrg_full', 2024, smoke=True)
    cfg['max_epochs'] = 1
    runner.train(d, cfg, tmp_path/'run', device='cpu')
    assert set(touched) == {'train', 'tuning'}
    report = runner.export(d, cfg, tmp_path/'run', device='cpu')
    assert set(report) == {'tuning', 'calibration', 'test'}
    with np.load(tmp_path/'run/predictions_test.npz', allow_pickle=False) as p:
        np.testing.assert_array_equal(p['rule_trigger'][:, 0], d.arrays['rule_trigger'][p['origins']])
        assert p['y_true'].shape == (8, 4, 10)
    manifest = json.loads((tmp_path/'run/manifest.json').read_text())
    assert all(data.sha256(tmp_path/'run'/name) == digest for name, digest in manifest.items())


def test_selfloop_has_no_cross_node_path():
    models, _, _ = api()
    a = np.ones((3, 10, 10), dtype='float32') / 10
    m = models.build_model('mrg_self_loop', a).eval()
    x = torch.randn(1, 96, 10, 7)
    y = m(x).prediction
    x[:, :, 1:] += 10
    torch.testing.assert_close(y[:, :, 0], m(x).prediction[:, :, 0], rtol=0, atol=0)


def test_parallel_plan_covers_36_runs_and_uses_four_gpu_workers():
    models, _, _ = api()
    from evcs_station_graph.eventtime.parallel import build_tasks, parse_gpu_ids, assign_gpu
    tasks = build_tasks('all')
    assert len(tasks) == 36
    assert len({(t.model, t.seed) for t in tasks}) == 36
    gpu_ids = parse_gpu_ids('0,1,2,3')
    assert gpu_ids == (0, 1, 2, 3)
    assert [assign_gpu(i, gpu_ids) for i in range(8)] == [0, 1, 2, 3, 0, 1, 2, 3]
    assert {t.model for t in tasks} == set(models.MODELS)
    assert [sum(assign_gpu(i, gpu_ids) == g for i in range(len(tasks))) for g in gpu_ids] == [9, 9, 9, 9]


def test_parallel_plan_rejects_bad_gpu_lists_and_has_unique_outputs():
    _, _, _ = api()
    from evcs_station_graph.eventtime.parallel import build_tasks, parse_gpu_ids, output_dir
    with pytest.raises(ValueError):
        parse_gpu_ids('0,1,1,3')
    with pytest.raises(ValueError):
        parse_gpu_ids('0,1,2')
    tasks = build_tasks('phase1')
    assert len({output_dir(t) for t in tasks}) == 15


def test_parallel_cli_dry_run_has_one_process_slot_per_gpu(tmp_path):
    import json
    import subprocess
    import sys
    result = subprocess.run([sys.executable, str(ROOT/'scripts/parallel_eventtime.py'), 'phase2',
                             '--gpus', '0,1,2,3', '--dry-run'], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    plan = json.loads(result.stdout)
    assert plan['task_count'] == 21
    assert plan['worker_count'] == 4
    assert plan['assignment_counts'] == {'0': 6, '1': 5, '2': 5, '3': 5}
    assert all('CUDA_VISIBLE_DEVICES' in task for task in plan['tasks'])
    assert all('--run-stage' in task['command'] and 'formal' in task['command'] for task in plan['tasks'])


def test_parallel_stage_preserves_smoke_output_namespace():
    import json
    import subprocess
    import sys
    result = subprocess.run([sys.executable, str(ROOT/'scripts/parallel_eventtime.py'), 'smoke',
                             '--gpus', '0,1,2,3', '--dry-run'], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    plan = json.loads(result.stdout)
    assert all('/smoke/' in task['output'] for task in plan['tasks'])
    assert all('--run-stage' in task['command'] and 'smoke' in task['command'] for task in plan['tasks'])


def test_parallel_benchmark_accepts_the_requested_model():
    import json
    import subprocess
    import sys
    result = subprocess.run([sys.executable, str(ROOT/'scripts/parallel_eventtime.py'), 'benchmark',
                             '--model', 'agcrn_full', '--gpus', '0,1,2,3', '--dry-run'],
                            cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    plan = json.loads(result.stdout)
    assert plan['task_count'] == 1
    assert plan['tasks'][0]['model'] == 'agcrn_full'


def test_upload_package_is_portable_and_has_no_old_artifacts(tmp_path):
    import subprocess
    import sys
    import tarfile
    import json
    script = ROOT/'scripts/package_eventtime.py'
    assert script.exists(), 'upload packager missing'
    result = subprocess.run([sys.executable, str(script), '--out', str(tmp_path/'bundle.tar.gz')],
                            cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    with tarfile.open(tmp_path/'bundle.tar.gz') as tar:
        names = tar.getnames()
        assert not any('/.git/' in n or '/.venv/' in n or n.endswith(('.docx','.pt')) for n in names)
        assert 'evcs-eventtime/scripts/parallel_eventtime.py' in names
        tar.extractall(tmp_path/'unpacked', filter='data')
    bundle = tmp_path/'unpacked/evcs-eventtime'
    result = subprocess.run([sys.executable, '-I', str(bundle/'scripts/eventtime_experiment.py'), 'check'],
                            cwd=tmp_path, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['formal_runs'] == 36
    (bundle/'configs/suite.json').write_text('{}')
    changed = subprocess.run([sys.executable, '-I', str(bundle/'scripts/eventtime_experiment.py'), 'check'],
                             cwd=tmp_path, capture_output=True, text=True)
    assert changed.returncode != 0, 'tampered bundle must be refused'


def test_finalize_saves_failure_and_archive(tmp_path):
    import subprocess
    import sys
    import json
    script = ROOT/'scripts/finalize_eventtime.py'
    assert script.exists(), 'finalizer missing'
    log = tmp_path/'results/cloud_logs/launch-test'
    log.mkdir(parents=True)
    (log/'train.log').write_text('synthetic failure log')
    result = subprocess.run([sys.executable, str(script), '--root', str(tmp_path), '--log-dir', str(log),
                             '--exit-code', '7', '--auto-shutdown', '0'], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    summary = json.loads((log/'autodl_run_summary.json').read_text())
    assert summary['exit_code'] == 7
    assert Path(summary['archive_path']).exists()
    assert (log/'exit_code.txt').read_text().strip() == '7'
