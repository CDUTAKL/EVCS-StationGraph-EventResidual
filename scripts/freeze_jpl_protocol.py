"""在无JPL预测结果的状态下封存数据、方案和源代码摘要；不训练。"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.verify_jpl_validation import check_manifest
OUTPUT = ROOT / 'docs/thesis/JPL-validation-freeze-20261005.json'


def sha256(path):
    """计算来源/产物SHA256，哈希清单可供后续GPU包校验。"""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def freeze():
    """只有数据与独立核验通过、正式输出为空时才允许生成冻结记录。"""
    if OUTPUT.exists():
        raise FileExistsError('Freeze record exists; do not silently overwrite')
    formal = ROOT / 'outputs/experiments/SG-EXP-028'
    if formal.exists() and any(formal.rglob('*')):
        raise ValueError('Experiment output already exists; cannot claim pre-result lock')
    frozen = ROOT / 'outputs/visibility/SG-DATA-007-jpl-eventtime-v1'
    verified = ROOT / 'outputs/visibility/SG-DATA-007-jpl-eventtime-v1-verification'
    verification_manifest = json.loads((verified / 'manifest.json').read_text())
    if verification_manifest != {'verification.json': sha256(verified / 'verification.json')}:
        raise ValueError('Independent verification manifest is missing or stale')
    verification = json.loads((verified / 'verification.json').read_text())
    if verification['status'] != 'passed' or verification['training_performed'] or verification['model_predictions_created']:
        raise ValueError('Independent verification has not passed without predictions')
    manifest = json.loads((frozen / 'manifest.json').read_text())
    check_manifest(frozen, manifest)
    expected_bindings = dict(script_sha256=sha256(ROOT / 'scripts/verify_jpl_validation.py'),
                             data_manifest_sha256=sha256(frozen / 'manifest.json'),
                             source_snapshot_sha256=sha256(ROOT / 'data/external/JPL-20261005/sessions.jsonl'),
                             protocol_sha256=sha256(frozen / 'protocol.json'))
    if any(verification.get(key) != value for key, value in expected_bindings.items()):
        raise ValueError('Independent verification is not bound to the current code/data/protocol')
    if sha256(frozen / 'dataset.npz') != verification['dataset_sha256']:
        raise ValueError('Independent verification points at another dataset')
    suite = json.loads((ROOT / 'configs/experiments/SG-EXP-028-jpl-independent-site.json').read_text())
    paths = [ROOT / name for name in (
        'configs/data/SG-DATA-007-jpl-eventtime-v1.json',
        'configs/experiments/SG-EXP-028-jpl-independent-site.json',
        'docs/thesis/SG-EXP-028-jpl-independent-site-validation.md',
        'scripts/fetch_jpl_sessions.py', 'scripts/prepare_jpl_validation.py',
        'scripts/verify_jpl_validation.py', 'scripts/freeze_jpl_protocol.py',
        'tests/test_jpl_validation.py',
        'src/evcs_station_graph/data/visibility_v2.py',
        'src/evcs_station_graph/graphs/relations.py',
        'src/evcs_station_graph/eventtime/models.py',
        'src/evcs_station_graph/eventtime/gate_control.py',
        'src/evcs_station_graph/eventtime/runner.py',
        'src/evcs_station_graph/models/graph.py',
        'src/evcs_station_graph/models/tcn.py',
        'src/evcs_station_graph/models/common.py')]
    record = dict(experiment='SG-EXP-028', protocol='SG-DATA-007-jpl-eventtime-v1',
                  locked_at_utc=datetime.now(timezone.utc).isoformat(),
                  base_git_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  status='data_and_design_frozen_no_training', planned_runs=suite['planned_runs'],
                  primary_metric=suite['primary_metric'], models=suite['primary_models'] + suite['secondary_models'],
                  seeds=suite['seeds'], data_manifest_sha256=sha256(frozen / 'manifest.json'),
                  dataset_sha256=sha256(frozen / 'dataset.npz'), source_snapshot_sha256=manifest['sources']['data/external/JPL-20261005/sessions.jsonl'],
                  independent_verification_sha256=sha256(verified / 'verification.json'),
                  frozen_files={str(p.relative_to(ROOT)): sha256(p) for p in paths},
                  no_model_test_results=True, no_training=True,
                  permissions='later explicit training authorization and GPU smoke required',
                  remaining_execution_gates=['JPL-specific strict loader', 'portable upload bundle', 'remote GPU smoke', 'explicit formal-training approval'],
                  change_policy='before-test amendments require reason and new dated lock; after-test changes exploratory only, no overwriting original evidence')
    OUTPUT.write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(dict(status=record['status'], record=str(OUTPUT), record_sha256=sha256(OUTPUT), dataset_sha256=record['dataset_sha256']), indent=2))


if __name__ == '__main__':
    freeze()
