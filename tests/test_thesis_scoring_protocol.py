"""Synthetic contract tests: these fixtures do not score the actual thesis."""

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / 'scripts'))

from audit_thesis_content_score import validate  # noqa: E402
from thesis_scoring_protocol import PROTOCOL_ID, file_hash, publication_check  # noqa: E402


class ScoringPublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        scoring = self.root / 'docs/thesis/scoring'
        scoring.mkdir(parents=True)
        for name in ('rubric.json', 'criterion-anchors-v2.json'):
            (scoring / name).write_bytes((PROJECT / 'docs/thesis/scoring' / name).read_bytes())
        self.rubric = json.loads((scoring / 'rubric.json').read_text())
        anchors = json.loads((scoring / 'criterion-anchors-v2.json').read_text())
        for name in ('before.md', 'after.md', 'evidence.md', 'forensic.md'):
            (self.root / name).write_text('Synthetic fixture: ' + name)
        self.card_path = self.root / 'card.json'
        self.card = {
            'schema_version': 2, 'protocol_id': PROTOCOL_ID,
            'rubric_id': self.rubric['rubric_id'], 'assessment_id': 'SYNTHETIC-ONLY',
            'assessment_kind': 'formal', 'review_date': '2026-10-17',
            'confidence': 'medium', 'review_mode': 'calibration_pair',
            'claim_scope': 'Synthetic validation fixture; not an academic assessment.',
            'anchors_sha256': file_hash(scoring / 'criterion-anchors-v2.json'),
            'packet': {
                'packet_id': 'SYNTHETIC', 'manuscript_path': 'after.md',
                'frozen_manuscript_path': 'after.md',
                'manuscript_sha256': file_hash(self.root / 'after.md'), 'scope': 'S',
                'evidence': [{'id': 'E', 'source': 'evidence.md', 'locator': 'fixture',
                              'reviewed': True, 'sha256': file_hash(self.root / 'evidence.md')}],
            },
            'reviewer_reports': [], 'reviewer_records': [],
            'forensic_report': 'forensic.md', 'criteria': [],
        }
        baseline = copy.deepcopy(self.card)
        baseline.pop('protocol_id')
        baseline['packet']['manuscript_sha256'] = file_hash(self.root / 'before.md')
        baseline['criteria'] = []
        for spec in anchors['criteria']:
            parts = [{'id': x['id'], 'score': x['maximum'],
                      'evidence_ids': ['E'], 'rationale': 'fixture'} for x in spec['components']]
            row = {
                'id': spec['id'], 'score': spec['maximum'],
                'manuscript_location': 'fixture', 'evidence_ids': ['E'],
                'rationale': 'fixture', 'components': parts,
                'before_components': copy.deepcopy(parts), 'issue_ids': [],
                'comparison': {'basis': 'unchanged',
                               'baseline_reassessed_score': spec['maximum'],
                               'revision_delta': 0, 'calibration_delta': 0,
                               'evidence_ids': ['E'], 'rationale': 'fixture'},
                'change': {'type': 'unchanged', 'reason': 'fixture', 'evidence_ids': ['E']},
                'adjudication': '',
            }
            self.card['criteria'].append(row)
            baseline['criteria'].append(copy.deepcopy(row))
        self.baseline = baseline
        self.write('baseline.json', baseline)
        self.card['baseline'] = {
            'scorecard_path': 'baseline.json',
            'scorecard_sha256': file_hash(self.root / 'baseline.json'),
            'manuscript_path': 'before.md',
            'manuscript_sha256': file_hash(self.root / 'before.md'),
        }
        self.set_issues([])
        for index in range(3):
            name = f'reviewer-{index}.md'
            (self.root / name).write_text('Synthetic raw report')
            record = {
                'protocol_id': PROTOCOL_ID, 'rubric_id': self.rubric['rubric_id'],
                'reviewer_id': f'R{index}', 'context_id': f'C{index}',
                'emphasis': ('technical', 'originality', 'readability')[index],
                'historical_scores_exposed': False,
                'manuscript_sha256': self.card['packet']['manuscript_sha256'],
                'before_manuscript_sha256': self.card['baseline']['manuscript_sha256'],
                'raw_report_path': name, 'raw_report_sha256': file_hash(self.root / name),
                'declared_total': 90, 'declared_before_total': 90,
                'criteria': [{'id': x['id'], 'score': x['maximum'],
                              'before_score': x['maximum']} for x in self.rubric['criteria']],
            }
            path = f'reviewer-{index}.json'
            self.write(path, record)
            self.card['reviewer_reports'].append(name)
            self.card['reviewer_records'].append({'path': path, 'sha256': file_hash(self.root / path)})

    def write(self, name, data):
        (self.root / name).write_text(json.dumps(data, ensure_ascii=False, indent=2))

    def set_issues(self, issues):
        self.write('issues.json', {'issues': issues})
        self.card['issue_ledger'] = {'path': 'issues.json',
                                     'sha256': file_hash(self.root / 'issues.json')}

    def check(self):
        self.write('card.json', self.card)
        record = validate(self.card, self.rubric)
        return publication_check(self.card, self.rubric, record, self.card_path, self.root)

    def assert_withheld(self, phrase):
        result = self.check()
        self.assertEqual(result['status'], 'withheld')
        self.assertIsNone(result['raw_score'])
        self.assertTrue(any(phrase in x for x in result['problems']), result)

    def test_complete_pair_passes_and_effects_are_separate(self):
        result = self.check()
        self.assertEqual(result['status'], 'publishable', result)
        self.assertEqual(result['revision_delta_raw'], 0)
        self.assertEqual(result['calibration_delta_raw'], 0)

    def test_legacy_record_cannot_create_new_publication_baseline(self):
        self.card['schema_version'] = 1
        self.card.pop('protocol_id')
        self.assert_withheld('未采用2.0')

    def test_resetting_all_rows_to_baseline_is_rejected(self):
        for row in self.card['criteria']:
            row['change']['type'] = 'baseline'
        self.assert_withheld('不能重设baseline')

    def test_unchanged_basis_cannot_be_reported_as_regression(self):
        row = self.card['criteria'][0]
        row['components'][0]['score'] -= 0.5
        row['score'] -= 0.5
        row['comparison']['revision_delta'] = -0.5
        row['change']['type'] = 'regression'
        self.assert_withheld('评价依据未变')

    def test_inherited_issue_can_calibrate_both_but_is_not_regression(self):
        row = self.card['criteria'][0]
        for key in ('components', 'before_components'):
            row[key][0]['score'] -= 0.5
        row['score'] -= 0.5
        row['comparison'].update(baseline_reassessed_score=4.5, calibration_delta=-0.5)
        row['change']['type'] = 'recalibration'
        row['issue_ids'] = ['ISSUE-1']
        row['adjudication'] = 'The same inherited issue affects both versions, as documented.'
        self.set_issues([{'id': 'ISSUE-1', 'primary_criterion': 'BR-01',
                          'secondary_impacts': [], 'present_in_baseline': True,
                          'present_in_current': True, 'used_for_score': True,
                          'status': 'supported', 'evidence_ids': ['E'],
                          'kind': 'defect', 'severity': 'minor'}])
        result = self.check()
        self.assertEqual(result['status'], 'publishable', result)
        self.assertEqual(result['revision_delta_raw'], 0)
        self.assertEqual(result['calibration_delta_raw'], -0.5)

    def test_unverified_concern_cannot_change_score(self):
        self.set_issues([{'id': 'I', 'primary_criterion': 'BR-04',
                          'present_in_baseline': True, 'present_in_current': True,
                          'used_for_score': True, 'status': 'unverified', 'evidence_ids': ['E']}])
        self.assert_withheld('未核实或无证据')

    def test_cross_criterion_deduction_requires_distinct_basis(self):
        self.set_issues([{'id': 'I', 'primary_criterion': 'BR-11',
                          'present_in_baseline': True, 'present_in_current': True,
                          'used_for_score': True, 'status': 'supported', 'evidence_ids': ['E'],
                          'secondary_impacts': [{'criterion_id': 'BR-07',
                                                 'distinct_reason': '', 'evidence_ids': ['E']}]}])
        self.assert_withheld('跨指标影响')

    def test_report_total_error_is_detected_before_publication(self):
        ref = self.card['reviewer_records'][0]
        report = json.loads((self.root / ref['path']).read_text())
        report['declared_total'] = 89.5
        self.write(ref['path'], report)
        ref['sha256'] = file_hash(self.root / ref['path'])
        self.assert_withheld('声明总分与分项和不一致')

    def test_changed_evidence_hash_is_detected(self):
        (self.root / 'evidence.md').write_text('Changed evidence')
        self.assert_withheld('证据E')

    def test_changed_snapshot_hash_is_detected(self):
        (self.root / 'after.md').write_text('Changed manuscript')
        self.assert_withheld('当前冻结稿')

    def test_changed_component_sum_is_detected(self):
        self.card['criteria'][0]['components'][0]['score'] -= 0.5
        self.assert_withheld('组件和不等于')

    def test_fixed_weights_cannot_silently_change(self):
        self.rubric['criteria'][0]['maximum'] = 4.5
        self.rubric['criteria'][1]['maximum'] = 5.5
        self.assert_withheld('固定权重发生变化')

    def test_daily_update_cannot_inherit_legacy_baseline_directly(self):
        self.card['review_mode'] = 'paired_revision'
        self.assert_withheld('首次评阅必须配对校准')

    def test_documented_new_error_can_reduce_current_score(self):
        row = self.card['criteria'][0]
        row['components'][0]['score'] -= 0.5
        row['score'] -= 0.5
        row['comparison'].update(basis='changed', revision_delta=-0.5)
        row['change']['type'] = 'regression'
        row['issue_ids'] = ['NEW-ERROR']
        row['adjudication'] = 'Verified new error in the current version only.'
        self.set_issues([{'id': 'NEW-ERROR', 'primary_criterion': 'BR-01',
                          'present_in_baseline': False, 'present_in_current': True,
                          'used_for_score': True, 'status': 'supported',
                          'evidence_ids': ['E'], 'kind': 'defect', 'severity': 'minor'}])
        result = self.check()
        self.assertEqual(result['status'], 'publishable', result)
        self.assertEqual(result['revision_delta_raw'], -0.5)
        self.assertEqual(result['calibration_delta_raw'], 0)

    def test_supported_writing_improvement_can_gain_without_new_training(self):
        self.baseline['criteria'][0]['score'] -= 0.5
        self.write('baseline.json', self.baseline)
        self.card['baseline']['scorecard_sha256'] = file_hash(self.root / 'baseline.json')
        row = self.card['criteria'][0]
        row['before_components'][0]['score'] -= 0.5
        row['comparison'].update(basis='changed', baseline_reassessed_score=4.5,
                                 revision_delta=0.5)
        row['change']['type'] = 'improvement'
        row['adjudication'] = 'The paired text shows a concrete improvement.'
        result = self.check()
        self.assertEqual(result['status'], 'publishable', result)
        self.assertEqual(result['revision_delta_raw'], 0.5)
        self.assertEqual(result['calibration_delta_raw'], 0)

    def test_daily_update_accepts_fixed_protocol_v2_baseline(self):
        self.baseline['protocol_id'] = PROTOCOL_ID
        self.write('baseline.json', self.baseline)
        self.card['baseline']['scorecard_sha256'] = file_hash(self.root / 'baseline.json')
        self.card['review_mode'] = 'paired_revision'
        self.assertEqual(self.check()['status'], 'publishable')

    def test_historical_score_exposure_is_not_blind_baseline(self):
        ref = self.card['reviewer_records'][0]
        report = json.loads((self.root / ref['path']).read_text())
        report['historical_scores_exposed'] = True
        self.write(ref['path'], report)
        ref['sha256'] = file_hash(self.root / ref['path'])
        self.assert_withheld('暴露历史分数')

    def test_scope_limit_does_not_automatically_recommend_major_repair(self):
        self.set_issues([{'id': 'I', 'primary_criterion': 'BR-11',
                          'present_in_baseline': True, 'present_in_current': True,
                          'used_for_score': False, 'status': 'supported',
                          'kind': 'scope_limit', 'severity': 'major', 'evidence_ids': ['E']}])
        result = self.check()
        self.assertEqual(result['status'], 'publishable', result)
        self.assertEqual(result['recommendation'], 'advisor_review')


if __name__ == '__main__':
    unittest.main()
