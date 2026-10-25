"""Publication checks for paired thesis reviews; these do not judge scientific merit."""

import hashlib
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path

PROTOCOL_ID = 'EVCS-THESIS-REVIEW-2.0'
FIXED_MAXIMA = dict(zip(
    (f'BR-{index:02d}' for index in range(1, 13)),
    (5, 5, 5, 5, 10, 5, 10, 10, 10, 10, 5, 10),
))


def file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def points(value, maximum):
    if isinstance(value, bool) or value is None:
        raise ValueError('missing or boolean score')
    try:
        number = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError('invalid score') from exc
    if not number.is_finite() or not 0 <= number <= Decimal(str(maximum)):
        raise ValueError('score out of range')
    if number % Decimal('0.5'):
        raise ValueError('score must use half-point steps')
    return number


def publication_check(card, rubric, record, card_path, root, baseline_override=None):
    """Return a separate publication decision without rewriting legacy records."""
    root, card_path = Path(root), Path(card_path).resolve()
    problems = []
    checked_files = []

    def resolve(value):
        path = Path(value)
        if path.is_absolute():
            return path
        candidates = [root / path, card_path.parent / path]
        existing = {p.resolve() for p in candidates if p.is_file()}
        if len(existing) > 1:
            raise ValueError(f'ambiguous relative path: {value}')
        return next(iter(existing)) if existing else candidates[0]

    def verified(value, sha, label):
        if not value or not sha:
            problems.append(f'{label}: 缺少文件路径或SHA-256。')
            return None
        try:
            path = resolve(value)
            if not path.is_file() or file_hash(path) != sha:
                problems.append(f'{label}: 文件不存在或SHA-256不符。')
                return None
        except (OSError, ValueError) as exc:
            problems.append(f'{label}: {exc}')
            return None
        checked_files.append(str(path))
        return path

    def verified_json(ref, label):
        ref = ref if isinstance(ref, dict) else {}
        path = verified(ref.get('path'), ref.get('sha256'), label)
        if path is None:
            return None
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
            if not isinstance(data, dict):
                problems.append(f'{label}: 必须为JSON对象。')
                return None
            return data
        except (OSError, ValueError) as exc:
            problems.append(f'{label}: JSON不可读，{exc}')
            return None

    def outcome(revision=None, calibration=None, recommendation=None):
        ready = not problems
        return {
            'protocol_id': PROTOCOL_ID,
            'status': 'publishable' if ready else 'withheld',
            'problems': problems,
            'raw_score': record.get('raw_score') if ready else None,
            'normalized_score': record.get('normalized_score') if ready else None,
            'revision_delta_raw': float(revision) if ready else None,
            'calibration_delta_raw': float(calibration) if ready else None,
            'recommendation': recommendation if ready else None,
            'checked_file_count': len(set(checked_files)),
            'note': '发布条件核验不证明证据真实、学术判断正确或评分具有测量精度。',
        }

    if record.get('status') != 'valid':
        problems.append('基础记录或算术检查未通过。')
    if card.get('schema_version') != 2 or card.get('protocol_id') != PROTOCOL_ID:
        problems.append('未采用2.0配对评阅协议；旧记录可保存，不能据此建立新发布基线。')
        return outcome()
    mode = card.get('review_mode')
    if mode not in {'calibration_pair', 'paired_revision'}:
        problems.append('必须选择配对校准或配对修订；独立快照不能替换跟踪基线。')
    if not card.get('claim_scope', '').strip():
        problems.append('缺少本论文实际接受评价的主张范围。')

    anchors_path = verified(
        'docs/thesis/scoring/criterion-anchors-v2.json',
        card.get('anchors_sha256'), '评分锚点',
    )
    if anchors_path is None:
        return outcome()
    anchors = json.loads(anchors_path.read_text(encoding='utf-8'))
    expected = {c['id']: c for c in rubric['criteria']}
    if {cid: row['maximum'] for cid, row in expected.items()} != FIXED_MAXIMA:
        problems.append('1.0固定权重发生变化；须建立新量表版本，不能静默改权重。')
    components = {c['id']: c for c in anchors['criteria']}
    if (anchors.get('rubric_id') != rubric['rubric_id']
            or set(components) != set(expected)
            or any(sum(Decimal(str(x['maximum'])) for x in c['components'])
                   != Decimal(str(expected[cid]['maximum']))
                   for cid, c in components.items())):
        problems.append('组件锚点与固定12项权重不一致。')
        return outcome()

    packet = card.get('packet', {})
    verified(packet.get('frozen_manuscript_path'),
             packet.get('manuscript_sha256'), '当前冻结稿')
    baseline_ref = card.get('baseline', {})
    baseline_path = verified(baseline_ref.get('scorecard_path'),
                             baseline_ref.get('scorecard_sha256'), '基线评分记录')
    verified(baseline_ref.get('manuscript_path'),
             baseline_ref.get('manuscript_sha256'), '旧版冻结稿')
    if baseline_path is None:
        return outcome()
    if baseline_override and Path(baseline_override).resolve() != baseline_path.resolve():
        problems.append('命令行基线与评分记录指定基线不同。')
    baseline = json.loads(baseline_path.read_text(encoding='utf-8'))
    if not isinstance(baseline, dict):
        problems.append('基线评分记录必须为JSON对象。')
        return outcome()
    if baseline.get('assessment_kind') not in {'formal', 'legacy_import'}:
        problems.append('基线不能是口头估计或探索性评分。')
    if (baseline.get('rubric_id') != rubric['rubric_id']
            or baseline.get('packet', {}).get('scope') != packet.get('scope')
            or baseline.get('packet', {}).get('manuscript_sha256')
            != baseline_ref.get('manuscript_sha256')):
        problems.append('新旧量表、审阅范围或旧稿指纹不一致。')
    if mode == 'paired_revision' and baseline.get('protocol_id') != PROTOCOL_ID:
        problems.append('2.0首次评阅必须配对校准，不能直接继承旧协议数值。')

    evidence = {e['id']: e for e in packet.get('evidence', [])
                if e.get('reviewed') is True}
    for eid, item in evidence.items():
        source = item.get('source', '')
        if not isinstance(source, str):
            problems.append(f'证据{eid}: 来源必须为路径或URL字符串。')
            continue
        path = item.get('snapshot_path') if source.startswith(('https://', 'http://')) else source
        verified(path, item.get('sha256'), f'证据{eid}')

    def refs_ok(refs):
        return isinstance(refs, list) and bool(refs) and set(refs).issubset(evidence)

    issue_doc = verified_json(card.get('issue_ledger'), '问题台账')
    issues = {}
    if issue_doc is not None:
        for issue in issue_doc.get('issues', []):
            iid = issue.get('id')
            if not iid or iid in issues:
                problems.append('问题ID为空或重复。')
                continue
            issues[iid] = issue
            if (issue.get('kind') not in {'defect', 'scope_limit', 'research_extension'}
                    or issue.get('status') not in {'supported', 'partly_supported', 'unverified', 'refuted'}
                    or issue.get('severity') not in {'blocker', 'major', 'minor', 'extension'}):
                problems.append(f'{iid}: 问题类型、核实状态或严重度无效。')
            if issue.get('primary_criterion') not in expected:
                problems.append(f'{iid}: 主要归属无效。')
            if not all(isinstance(issue.get(k), bool)
                       for k in ('present_in_baseline', 'present_in_current', 'used_for_score')):
                problems.append(f'{iid}: 必须明确旧稿/当前稿是否存在及是否参与评分。')
            if issue.get('used_for_score'):
                if (issue.get('status') not in {'supported', 'partly_supported'}
                        or not refs_ok(issue.get('evidence_ids'))):
                    problems.append(f'{iid}: 未核实或无证据的问题不能影响分数。')
            seen = {issue.get('primary_criterion')}
            for secondary in issue.get('secondary_impacts', []):
                cid = secondary.get('criterion_id')
                if (cid not in expected or cid in seen
                        or not secondary.get('distinct_reason', '').strip()
                        or not refs_ok(secondary.get('evidence_ids'))):
                    problems.append(f'{iid}: 跨指标影响缺少独立理由/证据，或重复归属。')
                seen.add(cid)

    old_rows = {r['id']: r for r in baseline.get('criteria', [])}
    current_rows = {r['id']: r for r in card.get('criteria', [])}
    revision_total = Decimal('0')
    calibration_total = Decimal('0')

    def component_total(row, key):
        cid = row['id']
        values = row.get(key, [])
        expected_parts = {x['id']: x for x in components[cid]['components']}
        if len(values) != len(expected_parts) or {v.get('id') for v in values} != set(expected_parts):
            raise ValueError(f'{key}组件缺失或重复')
        total = Decimal('0')
        for value in values:
            total += points(value.get('score'), expected_parts[value['id']]['maximum'])
            if not value.get('rationale', '').strip() or not refs_ok(value.get('evidence_ids')):
                raise ValueError(f'{value["id"]}缺少已读证据或判分理由')
        return total

    if set(old_rows) != set(expected) or set(current_rows) != set(expected):
        problems.append('新旧评分记录均须包含12项。')
        return outcome()
    for cid, row in current_rows.items():
        try:
            before = component_total(row, 'before_components')
            current = component_total(row, 'components')
            previous = points(old_rows[cid].get('score'), expected[cid]['maximum'])
            if current != points(row.get('score'), expected[cid]['maximum']):
                raise ValueError('当前组件和不等于该项得分')
            comp = row.get('comparison', {})
            revision, calibration = current - before, before - previous
            if (Decimal(str(comp.get('baseline_reassessed_score'))) != before
                    or Decimal(str(comp.get('revision_delta'))) != revision
                    or Decimal(str(comp.get('calibration_delta'))) != calibration):
                raise ValueError('旧稿重评分、修订效应或校准效应算术不符')
            if comp.get('basis') not in {'changed', 'unchanged'}:
                raise ValueError('必须说明评价依据是否实际改变')
            if comp.get('basis') == 'unchanged' and revision:
                raise ValueError('评价依据未变，修订效应必须为0')
            if mode == 'paired_revision' and calibration:
                raise ValueError('日常修订不能重新校准旧分；应切换配对校准')
            if mode == 'paired_revision':
                saved = {x['id']: x['score'] for x in old_rows[cid].get('components', [])}
                reassessed = {x['id']: x['score'] for x in row['before_components']}
                if saved != reassessed:
                    raise ValueError('日常修订的旧稿组件不得被重新定价')
            change = row.get('change', {}).get('type')
            wanted = ('improvement' if revision > 0 else 'regression' if revision < 0
                      else 'recalibration' if calibration else 'unchanged')
            if change != wanted:
                raise ValueError(f'变化类型应为{wanted}，不能重设baseline')
            if (revision or calibration) and (
                    not comp.get('rationale', '').strip() or not refs_ok(comp.get('evidence_ids'))):
                raise ValueError('变分缺少具体配对理由或已读证据')
            linked = []
            for iid in row.get('issue_ids', []):
                issue = issues.get(iid)
                if issue is None or not issue.get('used_for_score'):
                    raise ValueError('引用未核实或不存在的问题')
                allowed = {issue.get('primary_criterion')} | {
                    x.get('criterion_id') for x in issue.get('secondary_impacts', [])}
                if cid not in allowed:
                    raise ValueError('问题没有归属于此指标，可能重复扣分')
                linked.append(issue)
            if calibration and not linked:
                raise ValueError('校准旧分必须指出旧评分的具体问题')
            if revision < 0 and not any(
                    (not x.get('present_in_baseline') and x.get('present_in_current'))
                    or (x.get('impact_changed') and refs_ok(x.get('impact_change_evidence_ids')))
                    for x in linked):
                raise ValueError('下降缺少新增错误、证据失效或影响变化；旧问题不是新退步')
            revision_total += revision
            calibration_total += calibration
        except (ValueError, InvalidOperation, TypeError, KeyError) as exc:
            problems.append(f'{cid}: {exc}')

    reviewer_values = {cid: [] for cid in expected}
    reviewer_before_values = {cid: [] for cid in expected}
    contexts, reviewers, report_paths, emphases = set(), set(), set(), set()
    records = card.get('reviewer_records', [])
    if len(records) != 3:
        problems.append('正式发布须有三个隔离视角的机器可读评阅记录。')
    for ref in records:
        review = verified_json(ref, '评阅记录')
        if review is None:
            continue
        reviewer_id, context = review.get('reviewer_id'), review.get('context_id')
        if not reviewer_id or reviewer_id in reviewers or not context or context in contexts:
            problems.append('评阅者记录与上下文ID须各自唯一。')
        reviewers.add(reviewer_id)
        contexts.add(context)
        emphases.add(review.get('emphasis'))
        if (review.get('rubric_id') != rubric['rubric_id']
                or review.get('protocol_id') != PROTOCOL_ID
                or review.get('manuscript_sha256') != packet.get('manuscript_sha256')
                or review.get('before_manuscript_sha256') != baseline_ref.get('manuscript_sha256')):
            problems.append('评阅者未核对同一对稿件或采用不同量表。')
        if review.get('historical_scores_exposed') is not False:
            problems.append('初始隔离评阅暴露历史分数或未知，不能声明盲化基线。')
        raw = verified(review.get('raw_report_path'), review.get('raw_report_sha256'), '原始评阅报告')
        if raw:
            report_paths.add(raw.resolve())
        review_rows = review.get('criteria', [])
        if len(review_rows) != 12 or {x.get('id') for x in review_rows} != set(expected):
            problems.append('每位评阅者须按相同12项权重给分。')
            continue
        try:
            before_total, total = Decimal('0'), Decimal('0')
            for item in review_rows:
                cid = item['id']
                score = points(item.get('score'), expected[cid]['maximum'])
                before_score = points(item.get('before_score'), expected[cid]['maximum'])
                before_total += before_score
                total += score
                reviewer_values[cid].append(score)
                reviewer_before_values[cid].append(before_score)
            if (Decimal(str(review.get('declared_total'))) != total
                    or Decimal(str(review.get('declared_before_total'))) != before_total):
                problems.append('评阅者声明总分与分项和不一致。')
        except (ValueError, InvalidOperation) as exc:
            problems.append(f'评阅者分数无效：{exc}')
    try:
        declared_paths = {resolve(x).resolve() for x in card.get('reviewer_reports', [])}
        if declared_paths != report_paths:
            problems.append('原始报告清单与机器评阅记录不一致。')
    except (ValueError, TypeError) as exc:
        problems.append(f'原始报告路径无效：{exc}')
    if emphases != {'technical', 'originality', 'readability'}:
        problems.append('三份评阅须分别侧重技术、原创性和可读性，不能重复同一侧重。')
    for cid, values in reviewer_values.items():
        if len(values) != 3:
            continue
        before_values = reviewer_before_values[cid]
        for scores, score in (
                (values, current_rows[cid].get('score')),
                (before_values, current_rows[cid].get('comparison', {}).get('baseline_reassessed_score'))):
            spread = max(scores) - min(scores)
            if (spread > Decimal(str(expected[cid]['maximum'])) * Decimal('0.2')
                    or score is not None and not min(scores) <= Decimal(str(score)) <= max(scores)):
                if not current_rows[cid].get('adjudication', '').strip():
                    problems.append(f'{cid}: 较大分歧或超出评阅范围的裁定缺少依据。')
    forensic = card.get('forensic_report', '')
    if not forensic or not resolve(forensic).is_file():
        problems.append('独立证据核验报告不存在。')

    active = [x for x in issues.values() if x.get('present_in_current')
              and x.get('status') in {'supported', 'partly_supported'}
              and x.get('kind') == 'defect']
    severity = {x.get('severity') for x in active}
    recommendation = ('repair_critical_issue' if 'blocker' in severity else
                      'targeted_substantive_revision' if 'major' in severity else
                      'minor_revision' if 'minor' in severity else 'advisor_review')
    return outcome(revision_total, calibration_total, recommendation)
