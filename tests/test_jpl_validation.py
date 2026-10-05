"""JPL预登记与元数据门禁回归测试；只使用合成记录，不训练模型。"""
import json
from pathlib import Path

import pandas as pd
import pytest

from scripts.fetch_jpl_sessions import minimize
from scripts.prepare_jpl_validation import select_nodes, split_bounds, validate_frame
from scripts.verify_jpl_validation import check_manifest, independent_labels, independent_origins
import numpy as np
import hashlib
from scripts import freeze_jpl_protocol, verify_jpl_validation

ROOT = Path(__file__).resolve().parents[1]


def frame():
    """构造四个合法会话，供身份与时间边界检查使用。"""
    return pd.DataFrame(dict(session_key=['a', 'b', 'c', 'd'], siteID=['1'] * 4,
                            stationID=['s1', 's1', 's2', 's2'], spaceID=['n1', 'n1', 'n2', 'n2'],
                            timezone=['America/Los_Angeles'] * 4, kWhDelivered=[1.] * 4,
                            connectionTime=pd.to_datetime(['2019-01-01', '2019-02-01'] * 2, utc=True),
                            disconnectTime=pd.to_datetime(['2019-01-02', '2019-02-02'] * 2, utc=True)))


def test_minimize_removes_personal_fields_and_raw_session_id():
    row = dict(sessionID='private-session', userID='private-user', userInputs=[{'name': 'private'}],
               spaceID='A', kWhDelivered=2)
    output = minimize(row)
    assert len(output['session_key']) == 64
    assert 'private' not in json.dumps(output)
    assert 'userID' not in output and 'userInputs' not in output
    with pytest.raises(ValueError, match='stable session'):
        minimize({'spaceID': 'A'})


def test_split_is_fixed_chronological_and_covers_grid():
    assert split_bounds(1000) == {'train': (0, 700), 'tuning': (700, 775), 'calibration': (775, 850), 'test': (850, 1000)}
    assert split_bounds(1001)['test'][1] == 1001


def test_node_selection_does_not_use_future_counts_or_immature_sessions():
    f = frame()
    policy = dict(minimum_mature_sessions=2, minimum_active_months=2, count=2)
    cutoff = pd.Timestamp('2019-03-01', tz='UTC')
    assert select_nodes(f, cutoff, policy)[0] == ['n1', 'n2']
    extra = f.iloc[[0]].copy()
    extra['spaceID'] = 'future'
    extra['connectionTime'] = pd.Timestamp('2019-04-01', tz='UTC')
    extra['disconnectTime'] = pd.Timestamp('2019-04-02', tz='UTC')
    altered = pd.concat([f] + [extra] * 20, ignore_index=True)
    assert select_nodes(altered, cutoff, policy)[0] == ['n1', 'n2']
    f.loc[0, 'disconnectTime'] = cutoff
    with pytest.raises(ValueError, match='eligible'):
        select_nodes(f, cutoff, policy)


def test_identity_allows_coalesced_hardware_alias_but_rejects_split_alias():
    f = frame()
    f.loc[1, 'stationID'] = 'replacement'
    validate_frame(f)
    f.loc[2, 'stationID'] = 's1'
    with pytest.raises(ValueError, match='multiple parking spaces'):
        validate_frame(f)


def test_qc_rejects_invalid_energy_duplicate_and_missing_metadata():
    f = frame()
    validate_frame(f)
    for column, value, message in [('kWhDelivered', -1, 'energy'), ('session_key', 'b', 'Duplicate'), ('spaceID', None, 'missing')]:
        changed = f.copy()
        changed.loc[0, column] = value
        with pytest.raises(ValueError, match=message):
            validate_frame(changed)
    f.loc[0, 'disconnectTime'] = pd.Timestamp('2018-01-01', tz='UTC')
    with pytest.raises(ValueError, match='precedes'):
        validate_frame(f)


def test_protocol_and_suite_freeze_no_legacy_input_or_test_selection():
    data = json.loads((ROOT / 'configs/data/SG-DATA-007-jpl-eventtime-v1.json').read_text())
    suite = json.loads((ROOT / 'configs/experiments/SG-EXP-028-jpl-independent-site.json').read_text())
    assert data['split_fractions'] == {'train': .70, 'tuning': .075, 'calibration': .075, 'test': .15}
    assert data['node_selection']['fit_split'] == 'train'
    assert len(data['feature_names']) == 7 and not any('load' in n or 'energy' in n for n in data['feature_names'])
    assert suite['planned_runs'] == len(suite['primary_models'] + suite['secondary_models']) * len(suite['seeds']) == 12
    assert suite['training']['selection'] == 'tuning MAE in original proxy units'
    assert suite['training']['max_epochs'] == 60
    assert 'agcrn_full' in suite['primary_models']
    assert suite['statistics']['minimum_week_blocks'] == 12


def test_verifier_rejects_empty_or_partial_manifest(tmp_path):
    for manifest in ({}, {'files': {}, 'sources': {}}, {'files': {'dataset.npz': 'x'}, 'sources': {}}):
        with pytest.raises(ValueError, match='Required manifest'):
            check_manifest(tmp_path, manifest)


def test_independent_labels_reconstruct_time_bins_not_only_total_energy():
    grid = pd.date_range('2019-01-01', periods=5, freq='15min', tz='UTC').astype('int64').to_numpy()
    rows = pd.DataFrame(dict(spaceID=['A', 'A'], kWhDelivered=[6., 999.],
                             connectionTime=pd.to_datetime(['2019-01-01T00:07Z', '2019-01-01T00:45Z'], utc=True),
                             disconnectTime=pd.to_datetime(['2019-01-01T00:30Z', '2019-01-01T00:45Z'], utc=True),
                             doneChargingTime=pd.to_datetime(['2019-01-01T00:35Z', None], utc=True)))
    y, maturity = independent_labels(rows, grid, ['A'])
    np.testing.assert_array_equal(y[:, 0], [3., 3., 0., 0., 0.])
    assert maturity[0, 0] == rows.doneChargingTime.iloc[0].value
    assert maturity[1, 0] == rows.doneChargingTime.iloc[0].value
    # 总量相同但挪到错误时间格，逐格比较必须失败。
    wrong = np.array([[0.], [0.], [6.], [0.], [0.]])
    assert wrong.sum() == y.sum()
    with pytest.raises(AssertionError):
        np.testing.assert_allclose(wrong, y)


def test_independent_origins_remove_immature_labels_and_fit_tail():
    grid = np.arange(500, dtype=np.int64) * 900_000_000_000
    maturity = grid[:, None] + 900_000_000_000 - 1
    bounds = {'train': (0, 250), 'test': (250, 500)}
    expected = independent_origins(grid, maturity, bounds, fit=230)
    assert expected['train'][-1] == 225 and expected['test'][0] == 345
    changed = maturity.copy()
    changed[350] = grid[-1] + 900_000_000_000
    result = independent_origins(grid, changed, bounds, fit=230)
    assert all(k not in result['test'] for k in (346, 347, 348, 349))
    assert len(result['test']) == len(expected['test']) - 4


def test_selection_uses_late_completion_maturity_conservatively():
    f = frame()
    f['doneChargingTime'] = f.disconnectTime
    f.loc[0, 'doneChargingTime'] = pd.Timestamp('2019-04-01', tz='UTC')
    with pytest.raises(ValueError, match='eligible'):
        select_nodes(f, pd.Timestamp('2019-03-01', tz='UTC'), dict(minimum_mature_sessions=2, minimum_active_months=2, count=2))


def test_null_identity_is_not_normalized_to_a_fake_valid_node():
    for value in (None, 'None', ' ', 1, True):
        f = frame()
        f.loc[0, 'spaceID'] = value
        with pytest.raises(ValueError, match='missing|identity'):
            validate_frame(f)


def freeze_fixture(tmp_path, monkeypatch):
    """构造封存门禁的合成文件树，不访问真实会话或生成模型预测。"""
    monkeypatch.setattr(freeze_jpl_protocol, 'ROOT', tmp_path)
    monkeypatch.setattr(freeze_jpl_protocol, 'OUTPUT', tmp_path / 'lock.json')
    monkeypatch.setattr(verify_jpl_validation, 'ROOT', tmp_path)
    frozen = tmp_path / 'outputs/visibility/SG-DATA-007-jpl-eventtime-v1'
    verified = tmp_path / 'outputs/visibility/SG-DATA-007-jpl-eventtime-v1-verification'
    frozen.mkdir(parents=True)
    verified.mkdir(parents=True)
    for name in verify_jpl_validation.REQUIRED_ASSETS:
        (frozen / name).write_text('synthetic artifact')
    for name in verify_jpl_validation.REQUIRED_SOURCES | {'scripts/verify_jpl_validation.py'}:
        p = tmp_path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text('synthetic source')
    def hashed(p):
        return hashlib.sha256(p.read_bytes()).hexdigest()
    manifest = dict(files={n: hashed(frozen / n) for n in verify_jpl_validation.REQUIRED_ASSETS},
                    sources={n: hashed(tmp_path / n) for n in verify_jpl_validation.REQUIRED_SOURCES})
    (frozen / 'manifest.json').write_text(json.dumps(manifest))
    record = dict(status='passed', training_performed=False, model_predictions_created=False,
                  dataset_sha256=hashed(frozen / 'dataset.npz'),
                  script_sha256=hashed(tmp_path / 'scripts/verify_jpl_validation.py'),
                  data_manifest_sha256=hashed(frozen / 'manifest.json'),
                  source_snapshot_sha256=hashed(tmp_path / 'data/external/JPL-20261005/sessions.jsonl'),
                  protocol_sha256=hashed(frozen / 'protocol.json'))
    (verified / 'verification.json').write_text(json.dumps(record))
    (verified / 'manifest.json').write_text(json.dumps({'verification.json': hashed(verified / 'verification.json')}))
    return frozen, verified, record


def test_freeze_rejects_missing_asset_entries(tmp_path, monkeypatch):
    frozen, _, _ = freeze_fixture(tmp_path, monkeypatch)
    manifest = json.loads((frozen / 'manifest.json').read_text())
    manifest['files'] = {}
    (frozen / 'manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match='Required manifest'):
        freeze_jpl_protocol.freeze()
    assert not (tmp_path / 'lock.json').exists()


def test_freeze_rejects_stale_verifier_even_if_its_output_hash_matches(tmp_path, monkeypatch):
    _, verified, record = freeze_fixture(tmp_path, monkeypatch)
    record['script_sha256'] = 'outdated-script'
    p = verified / 'verification.json'
    p.write_text(json.dumps(record))
    (verified / 'manifest.json').write_text(json.dumps({'verification.json': hashlib.sha256(p.read_bytes()).hexdigest()}))
    with pytest.raises(ValueError, match='not bound'):
        freeze_jpl_protocol.freeze()
    assert not (tmp_path / 'lock.json').exists()


def test_freeze_rejects_unverified_record_mutation(tmp_path, monkeypatch):
    _, verified, record = freeze_fixture(tmp_path, monkeypatch)
    record['protocol_sha256'] = 'changed-protocol'
    (verified / 'verification.json').write_text(json.dumps(record))
    with pytest.raises(ValueError, match='manifest'):
        freeze_jpl_protocol.freeze()
