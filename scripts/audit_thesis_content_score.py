#!/usr/bin/env python3
"""Validate project content score records; never infer missing evidence or scores."""
import argparse
import json
import re
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUBRIC = ROOT / 'docs/thesis/scoring/rubric.json'


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def validate(card, rubric):
    errors, missing = [], []
    expected = {c['id']: c for c in rubric['criteria']}
    maximum = sum(Decimal(str(c['maximum'])) for c in expected.values())
    if len(expected) != 12 or maximum != Decimal(str(rubric['raw_maximum'])):
        errors.append('量表必须包含12个唯一指标，权重合计必须等于原始满分。')
    if rubric['raw_maximum'] != 90 or rubric['display_maximum'] != 100:
        errors.append('1.0量表满分必须固定为原始90、显示100。')
    if card.get('rubric_id') != rubric['rubric_id']:
        errors.append('量表版本不一致。')
    kind = card.get('assessment_kind')
    if kind not in {'formal', 'legacy_import', 'exploratory', 'calibration'}:
        errors.append('未知评分记录类型。')
    for field in ('assessment_id', 'review_date'):
        if not nonempty(card.get(field)) or card[field] in {'REPLACE', 'YYYY-MM-DD'}:
            missing.append(f'缺少有效{field}。')
    if card.get('confidence') not in {'low', 'medium', 'high'}:
        missing.append('缺少置信度。')
    packet = card.get('packet', {})
    for field in ('packet_id', 'manuscript_path', 'scope'):
        if not nonempty(packet.get(field)) or packet[field] == 'REPLACE':
            missing.append(f'缺少证据包字段{field}。')
    if not re.fullmatch(r'[0-9a-fA-F]{64}', str(packet.get('manuscript_sha256', ''))):
        missing.append('缺少有效稿件SHA-256。')
    evidence = packet.get('evidence', [])
    evidence_by_id = {e.get('id'): e for e in evidence}
    if len(evidence_by_id) != len(evidence) or None in evidence_by_id:
        errors.append('证据ID必须存在且唯一。')
    reviewed = {key for key, e in evidence_by_id.items()
                if e.get('reviewed') is True and nonempty(e.get('source'))
                and nonempty(e.get('locator'))}
    rows = card.get('criteria', [])
    ids = [r.get('id') for r in rows]
    if len(ids) != len(set(ids)) or set(ids) != set(expected):
        errors.append('评分表必须包含全部12项，不能重复、增加或遗漏指标。')
    total = Decimal('0')
    for row in rows:
        cid = row.get('id')
        if cid not in expected:
            continue
        value = row.get('score')
        if value is None:
            missing.append(f'{cid}: N/A，{row.get("na_reason") or "未说明缺失材料"}。')
            continue
        try:
            if isinstance(value, bool):
                raise ValueError
            score = Decimal(str(value))
            step = Decimal(str(rubric['score_step']))
            if not score.is_finite() or not (0 <= score <= expected[cid]['maximum']):
                raise ValueError
            if score % step:
                raise ValueError
        except (ValueError, ArithmeticError):
            errors.append(f'{cid}: 得分必须在0到该项满分之间，并按0.5分递进。')
            continue
        total += score
        for field in ('manuscript_location', 'rationale'):
            if not nonempty(row.get(field)):
                missing.append(f'{cid}: 缺少{field}。')
        refs = row.get('evidence_ids', [])
        if not isinstance(refs, list) or not refs or not set(refs).issubset(reviewed):
            missing.append(f'{cid}: 缺少已检查的有效证据。')
        change = row.get('change', {})
        if change.get('type') not in {'baseline', 'unchanged', 'improvement', 'regression', 'recalibration'}:
            missing.append(f'{cid}: 缺少有效变化类型。')
        if not nonempty(change.get('reason')):
            missing.append(f'{cid}: 缺少变化理由。')
    if kind == 'formal':
        reports = card.get('reviewer_reports', [])
        if len(set(reports)) < 3:
            missing.append('正式评分需保存至少三个不同视角的原始报告。')
        if not nonempty(card.get('forensic_report')):
            missing.append('正式评分缺少独立证据核验报告。')
    if kind in {'exploratory', 'calibration'}:
        missing.append('本记录为探索性评阅或校准估计，不发布正式总分。')
    status = 'invalid' if errors else ('withheld' if missing else 'valid')
    normalized = (total / maximum * Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    return {'assessment_id': card.get('assessment_id'), 'rubric_id': rubric['rubric_id'],
            'status': status, 'errors': errors, 'missing': missing,
            'raw_score': float(total) if status == 'valid' else None,
            'raw_maximum': float(maximum),
            'normalized_score': float(normalized) if status == 'valid' else None,
            'blockers': card.get('blockers', []),
            'note': '记录和算术校验不代表重新阅读、核验文件真实性或完成学术评审。'}


def compare(card, old, rubric, result):
    baseline = validate(old, rubric)
    comparison_errors = []
    if result['status'] != 'valid' or baseline['status'] != 'valid':
        comparison_errors.append('新旧记录必须均有效，缺项时暂缓比较。')
    if card.get('assessment_kind') not in {'formal', 'legacy_import'} or old.get('assessment_kind') not in {'formal', 'legacy_import'}:
        comparison_errors.append('估计或探索性评阅不能用于正式增减分。')
    if card.get('packet', {}).get('scope') != old.get('packet', {}).get('scope'):
        comparison_errors.append('新旧审阅范围不一致。')
    old_rows = {r['id']: r for r in old.get('criteria', [])}
    delta_rows = []
    reviewed = {e.get('id') for e in card.get('packet', {}).get('evidence', []) if e.get('reviewed') is True}
    for row in card.get('criteria', []):
        prior = old_rows.get(row.get('id'), {})
        if row.get('score') is None or prior.get('score') is None:
            continue
        delta = Decimal(str(row['score'])) - Decimal(str(prior['score']))
        change = row.get('change', {})
        ct = change.get('type')
        if delta and ct not in {'improvement', 'regression', 'recalibration'}:
            comparison_errors.append(f'{row["id"]}: 分数变化必须解释改善、退步或校准。')
        if delta > 0 and ct == 'regression' or delta < 0 and ct == 'improvement':
            comparison_errors.append(f'{row["id"]}: 差值方向与变化类型冲突。')
        refs = change.get('evidence_ids', [])
        if delta and (not refs or not set(refs).issubset(reviewed)):
            comparison_errors.append(f'{row["id"]}: 缺少支持分数变化的已检查证据。')
        delta_rows.append({'id': row['id'], 'old': prior['score'], 'new': row['score'],
                           'raw_delta': float(delta), 'type': ct, 'reason': change.get('reason')})
    result['comparison'] = {'baseline_id': old.get('assessment_id'),
                            'status': 'withheld' if comparison_errors else 'valid',
                            'errors': comparison_errors,
                            'normalized_delta': float(((Decimal(str(result['raw_score'])) - Decimal(str(baseline['raw_score'])))
                                / Decimal(str(rubric['raw_maximum'])) * Decimal('100')).quantize(
                                    Decimal('0.01'), rounding=ROUND_HALF_UP))
                            if not comparison_errors else None,
                            'criteria': delta_rows}
    return bool(comparison_errors)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('scorecard', type=Path)
    parser.add_argument('--baseline', type=Path)
    parser.add_argument('--publish', action='store_true',
                        help='核验2.0配对发布条件；未通过则不输出可发布总分')
    args = parser.parse_args()
    try:
        rubric, card = read_json(RUBRIC), read_json(args.scorecard)
        result = validate(card, rubric)
        bad_compare = compare(card, read_json(args.baseline), rubric, result) if args.baseline else False
        result['publication_status'] = 'record_only_not_publication_checked'
        status_path = ROOT / 'docs/thesis/scoring/publication-status.json'
        decisions = read_json(status_path) if status_path.exists() else {}
        decision = decisions.get('assessments', {}).get(card.get('assessment_id'), {})
        if decision:
            result['publication_status'] = decision.get('status', 'record_only')
            result['publication_decision'] = decision
        publish_failed = False
        if args.publish:
            from thesis_scoring_protocol import publication_check

            publication = publication_check(
                card, rubric, result, args.scorecard, ROOT, args.baseline,
            )
            if decision.get('status') == 'suspended_pending_paired_calibration':
                publication['status'] = 'withheld'
                publication['problems'].append('该历史评分已暂缓发布，须使用新评审ID完成配对校准。')
                publication['raw_score'] = publication['normalized_score'] = None
            result['publication'] = publication
            result['publication_status'] = publication['status']
            publish_failed = publication['status'] != 'publishable'
            result['record_validation_status'] = result['status']
            if publish_failed:
                result['record_raw_sum'] = result['raw_score']
                result['raw_score'] = result['normalized_score'] = None
                if not result['errors']:
                    result['status'] = 'withheld'
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({'status': 'invalid', 'error': str(exc)}, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 2 if result['errors'] else (1 if result['status'] != 'valid' or bad_compare or publish_failed else 0)


if __name__ == '__main__':
    raise SystemExit(main())
