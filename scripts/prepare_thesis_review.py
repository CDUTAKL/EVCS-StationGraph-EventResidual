#!/usr/bin/env python3
"""Offline review preparation. Cache deterministic checks, never academic judgments."""
from __future__ import annotations

import argparse
import difflib
import hashlib
import hmac
import json
import os
import platform
import re
import secrets
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path

VERSION = '1.0'
FIGURE_SCOPE = 'captions_only; image content and full-page visual acceptance remain unchecked'


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def signature(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def cache_auth_key():
    """Load a per-user key outside the project so repository cache files cannot forge hits."""
    state_value = os.environ.get('XDG_STATE_HOME')
    state_root = Path(state_value) if state_value else Path.home() / '.local' / 'state'
    if not state_root.is_absolute():
        return None
    directory = state_root / 'thesis-review'
    path = directory / 'cache-auth.key'
    try:
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        if directory.is_symlink() or path.is_symlink():
            return None
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            pass
        else:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(secrets.token_bytes(32))
                stream.flush()
                os.fsync(stream.fileno())
        if os.name != 'posix':
            return None  # Do not trust cache hits where private ACLs cannot be verified here.
        directory_info = directory.stat()
        if directory_info.st_uid != os.getuid() or directory_info.st_mode & 0o077:
            return None
        info = path.stat()
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or info.st_mode & 0o077 or info.st_nlink != 1):
            return None
        key = path.read_bytes()
        return key if len(key) == 32 else None
    except OSError:
        return None


def local(root, value):
    path = (root / value).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError(f'Path outside project: {value}') from exc
    return path


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent, delete=False) as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
        temporary = stream.name
    os.replace(temporary, path)


def sections(text):
    """Hash each heading's own text; ancestors do not mask changed children."""
    records, stack, counts = {}, [], {}
    key, lines, fence = '__preamble__', [], None
    for number, line in enumerate(text.splitlines(), 1):
        mark = re.match(r'^\s*(`{3,}|~{3,})', line)
        if mark:
            token = mark.group(1)[0]
            if fence is None:
                fence = token
            elif fence == token:
                fence = None
        heading = re.match(r'^(#{1,6})\s+(.+?)\s*#*\s*$', line) if fence is None else None
        if heading:
            if lines:
                records[key]['text'] = '\n'.join(lines)
            level, title = len(heading.group(1)), heading.group(2)
            stack = [(n, t) for n, t in stack if n < level] + [(level, title)]
            full = ' / '.join(t for _, t in stack)
            counts[full] = counts.get(full, 0) + 1
            key = f'{full} [{counts[full]}]'
            records[key] = {'title': title, 'line': number, 'text': ''}
            lines = [line]
        else:
            if key not in records:
                records[key] = {'title': '__preamble__', 'line': 1, 'text': ''}
            lines.append(line)
    if lines:
        records[key]['text'] = '\n'.join(lines)
    return records


def matches(title, prefix):
    for part in title.split(' / '):
        if part == prefix or (part.startswith(prefix) and part[len(prefix):len(prefix)+1] in {' ', '\t', '.', '　'}):
            return True
    return False


class Preparer:
    def __init__(self, root, config, cache, run_checks=False, rerun=False, cache_secret=None):
        self.root, self.config, self.cache = Path(root).resolve(), config, Path(cache).resolve()
        self.run_checks, self.rerun = run_checks, rerun
        self.cache_secret = cache_auth_key() if cache_secret is None else cache_secret
        self.tool_hash = digest(Path(__file__))
        self.blockers, self.warnings, self.timings = [], [], {}
        self.guard = {}
        self.stats = {'structure_hits': 0, 'structure_misses': 0, 'check_hits': 0, 'check_executions': 0}

    def input(self, value):
        path = local(self.root, value)
        if not path.is_file():
            raise ValueError(f'Missing input: {value}')
        self.guard[str(path.relative_to(self.root))] = digest(path)
        return path

    def memo(self, namespace, key):
        if self.cache_secret is None:
            return None
        path = self.cache_file(namespace, key)
        try:
            if path.is_symlink():
                return None
            item = load(path)
            mac = item.pop('cache_hmac_sha256', None)
            expected = hmac.new(self.cache_secret, signature(item).encode(), hashlib.sha256).hexdigest()
            return item if item.get('key') == key and isinstance(mac, str) and hmac.compare_digest(mac, expected) else None
        except (OSError, ValueError, TypeError):
            return None

    def save_memo(self, namespace, key, item):
        if self.cache_secret is None:
            return
        record = dict(item)
        record['cache_hmac_sha256'] = hmac.new(
            self.cache_secret, signature(item).encode(), hashlib.sha256
        ).hexdigest()
        save(self.cache_file(namespace, key), record)

    def cache_file(self, namespace, key):
        directory = self.cache / namespace
        if directory.is_symlink():
            raise ValueError(f'Cache namespace cannot be a symlink: {namespace}')
        path = directory / f'{key}.json'
        try:
            path.resolve().relative_to(self.root)
        except ValueError as exc:
            raise ValueError('Cache path resolves outside project') from exc
        return path

    def inspect(self, path):
        file_sha = digest(path)  # Always hash bytes, even if size/mtime are unchanged.
        key = signature([self.tool_hash, VERSION, 'structure', path.suffix.lower(), file_sha])
        cached = self.memo('structure', key)
        if cached:
            self.stats['structure_hits'] += 1
            return file_sha, cached['result']
        self.stats['structure_misses'] += 1
        result = {'scope': 'file readability / syntax only', 'valid': True}
        try:
            if path.suffix.lower() == '.json':
                value = load(path)
                result['json_type'] = type(value).__name__
            elif path.suffix.lower() in {'.md', '.txt', '.csv', '.tsv'}:
                path.read_text(encoding='utf-8')
        except (OSError, ValueError, UnicodeError) as exc:
            result.update(valid=False, error=str(exc))
        self.save_memo('structure', key, {'key': key, 'result': result})
        return file_sha, result

    def check(self, spec, policy):
        started = time.perf_counter()
        cid = spec['id']
        if spec.get('dependency_scope_confirmed') is not True or not spec.get('scope'):
            return {'id': cid, 'status': 'unbound', 'reason': 'dependency closure/scope not confirmed'}
        script = self.input(spec['script'])
        if script.suffix != '.py' or not isinstance(spec.get('args', []), list) or not all(isinstance(x, str) for x in spec.get('args', [])):
            raise ValueError(f'{cid}: requires a local Python script and string arguments')
        paths = sorted(set(spec.get('inputs', []) + [spec['script']]))
        before = {p: digest(self.input(p)) for p in paths}
        env_keys = sorted(set(spec.get('environment_keys', [])))
        env_hashes = {k: signature(os.environ.get(k)) for k in env_keys}
        payload = {'version': VERSION, 'tool_sha256': self.tool_hash, 'policy': policy, 'spec': spec,
                   'inputs': before, 'environment': env_hashes,
                   'runtime': [sys.executable, sys.version, platform.platform()]}
        key = signature(payload)
        cached = self.memo('checks', key)
        if cached and not self.rerun and cached.get('payload') == payload and cached.get('successful') is True:
            outputs = cached.get('outputs', {})
            declared_outputs = spec.get('outputs', [])
            if set(outputs) == set(declared_outputs) and all(local(self.root, p).is_file() and digest(local(self.root, p)) == h for p, h in outputs.items()):
                self.stats['check_hits'] += 1
                return {'id': cid, 'status': 'reused_success', 'cache_key': key, 'scope': spec['scope'],
                        'duration_seconds': time.perf_counter()-started, 'original_execution': cached['execution']}
        if not self.run_checks:
            return {'id': cid, 'status': 'pending', 'cache_key': key, 'scope': spec['scope']}
        self.stats['check_executions'] += 1
        try:
            result = subprocess.run([sys.executable, str(script), *spec.get('args', [])], cwd=self.root,
                                    capture_output=True, timeout=spec.get('timeout_seconds', 120), check=False)
        except subprocess.TimeoutExpired:
            return {'id': cid, 'status': 'failed', 'reason': 'timeout; no successful cache recorded'}
        after = {p: digest(local(self.root, p)) if local(self.root, p).is_file() else None for p in paths}
        changed_env = {k: signature(os.environ.get(k)) for k in env_keys} != env_hashes
        if before != after or changed_env:
            return {'id': cid, 'status': 'failed', 'reason': 'inputs changed during execution; no successful cache recorded'}
        outputs = {p: digest(local(self.root, p)) for p in spec.get('outputs', []) if local(self.root, p).is_file()}
        execution = {'returncode': result.returncode, 'stdout_sha256': hashlib.sha256(result.stdout).hexdigest(),
                     'stderr_sha256': hashlib.sha256(result.stderr).hexdigest(),
                     'stdout_bytes': len(result.stdout), 'stderr_bytes': len(result.stderr),
                     'duration_seconds': time.perf_counter()-started}
        success = result.returncode == 0 and set(outputs) == set(spec.get('outputs', []))
        if success:
            self.save_memo('checks', key, {'key': key, 'payload': payload, 'successful': True,
                 'outputs': outputs, 'execution': execution})
        return {'id': cid, 'status': 'executed_success' if success else 'failed', 'cache_key': key,
                'scope': spec['scope'], 'execution': execution}

    def prepare(self):
        started = time.perf_counter()
        c = self.config
        if c.get('schema_version') != 1:
            raise ValueError('Unsupported configuration schema')
        baseline_path = self.input(c['baseline_scorecard'])
        baseline = load(baseline_path)
        baseline_sha = digest(baseline_path)
        if baseline_sha != c['baseline_scorecard_sha256']:
            self.blockers.append('Baseline scorecard fingerprint changed; choose and confirm baseline explicitly.')
        if baseline.get('rubric_id') != load(self.input(c['rubric']))['rubric_id']:
            if c.get('review_mode') == 'calibration_pair':
                self.warnings.append('Calibration pair uses a changed rubric; all criteria require explicit recalibration.')
            else:
                self.blockers.append('Rubric differs from baseline; explicit recalibration is required.')
        mode = c.get('review_mode')
        if mode not in {'paired_revision', 'calibration_pair'}:
            raise ValueError('review_mode must be paired_revision or calibration_pair')
        if mode == 'paired_revision' and baseline.get('protocol_id') != c['protocol_id']:
            self.blockers.append('Baseline protocol differs; paired_revision cannot inherit this baseline.')
        policy = {p: digest(self.input(c[p])) for p in ('rubric', 'anchors', 'protocol', 'reviewer_instructions')}
        for role in ('rubric', 'anchors', 'reviewer_instructions'):
            attached = self.input(c[role])
            if attached == baseline_path or digest(attached) == baseline_sha:
                self.blockers.append(f'{role}: baseline scorecard cannot be included in reviewer materials')
            if role == 'reviewer_instructions' and self._looks_like_scorecard(attached):
                self.blockers.append(f'{role}: scorecard-shaped file cannot be included in reviewer materials')
        if digest(local(self.root, c['anchors'])) != baseline.get('anchors_sha256'):
            if mode == 'paired_revision':
                self.blockers.append('Anchors differ from baseline; complete calibration before paired_revision.')
            else:
                self.warnings.append('Calibration pair uses changed anchors; all criteria require explicit recalibration.')
        policy_recalibration = mode == 'calibration_pair' and (
            baseline.get('rubric_id') != load(local(self.root, c['rubric'])).get('rubric_id')
            or digest(local(self.root, c['anchors'])) != baseline.get('anchors_sha256')
        )
        current_path = self.input(c['manuscript'])
        previous_path = self.input(baseline['packet']['frozen_manuscript_path'])
        if digest(previous_path) != baseline['packet']['manuscript_sha256']:
            self.blockers.append('Frozen baseline manuscript hash mismatch.')
        before_text, text = previous_path.read_text(encoding='utf-8'), current_path.read_text(encoding='utf-8')
        before, current = sections(before_text), sections(text)
        changed_sections = [{'key': k, 'title': (current.get(k) or before[k])['title'],
                             'before_line': before.get(k, {}).get('line'), 'current_line': current.get(k, {}).get('line')}
                            for k in sorted(set(before) | set(current))
                            if before.get(k, {}).get('text') != current.get(k, {}).get('text')]
        old_evidence = {e['id']: e for e in baseline['packet']['evidence']}
        evidence, ids = [], set()
        for item in c['evidence']:
            eid = item['id']
            if eid in ids:
                raise ValueError(f'Duplicate evidence ID: {eid}')
            ids.add(eid)
            path = self.input(item['path'])
            file_sha, syntax = self.inspect(path)
            if not syntax['valid']:
                self.blockers.append(f'{eid}: unreadable/invalid file')
            looks_like_scorecard = self._looks_like_scorecard(path)
            if item.get('reviewer_safe') is not True or path == baseline_path or looks_like_scorecard:
                self.blockers.append(f'{eid}: not confirmed safe for isolated reviewers')
            prior = old_evidence.get(item.get('baseline_evidence_id', eid))
            dependencies = {p: digest(self.input(p)) for p in item.get('dependencies', [])}
            bound = item.get('baseline_dependencies', {})
            dep_change = bool(dependencies) and dependencies != bound
            status = 'added' if prior is None else 'unchanged' if file_sha == prior['sha256'] and not dep_change else 'changed'
            evidence.append({'id': eid, 'path': item['path'], 'sha256': file_sha, 'syntax': syntax, 'status': status,
                             'dependency_change_or_unbound': dep_change, 'dependencies': dependencies,
                             'prior_reviewed': prior.get('reviewed', False) if prior else False,
                             'reuse_scope': 'prior recorded reading only; not new scientific verification'})
        exclusions = c.get('baseline_evidence_exclusions', {})
        if not isinstance(exclusions, dict) or any(
                not isinstance(k, str) or not isinstance(v, str) or not v.strip()
                for k, v in exclusions.items()):
            raise ValueError('baseline_evidence_exclusions must map each excluded ID to a reason')
        excluded = set(exclusions)
        covered = {e.get('baseline_evidence_id', e['id']) for e in c['evidence']}
        removed = sorted(set(old_evidence) - covered - excluded)
        if removed:
            self.warnings.append('Unmapped/removed baseline evidence: ' + ', '.join(removed))
        source_ids, sources = set(), []
        for source in c.get('sources', []):
            sid = source['id']
            if sid in source_ids or source['evidence_id'] not in ids:
                raise ValueError(f'Invalid/duplicate source: {sid}')
            source_ids.add(sid)
            if source.get('reading_status') not in {'verified_fulltext', 'verified_excerpt', 'verified_abstract', 'unavailable_declared'} or not source.get('locator'):
                self.blockers.append(f'{sid}: source reading scope/disposition is missing')
            if source.get('comparison_status') not in {'compared', 'not_required', 'known_gap'}:
                self.blockers.append(f'{sid}: comparison disposition is missing')
            if source.get('comparison_status') == 'known_gap':
                self.warnings.append(f'{sid}: known near-neighbor comparison gap; include in review planning')
            evidence_sha = next(e['sha256'] for e in evidence if e['id'] == source['evidence_id'])
            attestation_current = source.get('reviewed_sha256') == evidence_sha
            if not attestation_current:
                self.blockers.append(f'{sid}: reading attestation is not bound to the current evidence hash')
            sources.append({**source, 'current_evidence_sha256': evidence_sha,
                            'attestation_current': attestation_current})
        registered_citations = {str(n) for s in sources for n in s.get('citations', [])}
        for number in c.get('required_citations', []):
            if str(number) not in registered_citations:
                self.blockers.append(f'Critical citation [{number}] has no source-grounded reading record')
        self.timings['preflight_seconds'] = time.perf_counter()-started
        stage = time.perf_counter()
        checks = []
        check_ids = set()
        for spec in c.get('checks', []):
            if spec['id'] in check_ids or not set(spec.get('evidence_ids', [])).issubset(ids):
                raise ValueError(f'Invalid/duplicate check ID or evidence binding: {spec["id"]}')
            check_ids.add(spec['id'])
            result = self.check(spec, policy)
            checks.append(result)
            if result['status'] not in {'reused_success', 'executed_success'}:
                self.blockers.append(f'{spec["id"]}: deterministic check {result["status"]}; no automatic pass')
        if not checks:
            self.warnings.append('No computation checks registered; syntax cache does not verify scientific numbers.')
        self.timings['checks_seconds'] = time.perf_counter()-stage
        stage = time.perf_counter()
        rubric_doc = load(local(self.root, c['rubric']))
        criterion_ids = {r['id'] for r in rubric_doc['criteria']}
        claims = {x['id']: x for x in c['claims']}
        if not claims:
            raise ValueError('At least one claim is required for impact routing')
        if len(claims) != len(c['claims']):
            raise ValueError('Duplicate claim ID')
        affected, direct, mapped = {}, set(), set()
        changed_evidence = {e['id'] for e in evidence if e['status'] != 'unchanged'}
        changed_evidence_ids = {e['id'] for e in evidence if e['status'] != 'unchanged'}
        attention_sources = {s['id'] for s in sources
                             if s['comparison_status'] == 'known_gap' or not s['attestation_current']
                             or s['evidence_id'] in changed_evidence_ids}
        check_by_id = {r['id']: r for r in checks}
        for spec in c.get('checks', []):
            if check_by_id[spec['id']]['status'] not in {'reused_success', 'executed_success'}:
                changed_evidence.update(spec.get('evidence_ids', []))
        for cid, claim in claims.items():
            if not set(claim.get('evidence_ids', [])).issubset(ids) or not set(claim.get('source_ids', [])).issubset(source_ids) or not set(claim.get('depends_on', [])).issubset(claims):
                raise ValueError(f'{cid}: dangling dependency in impact index')
            if not claim.get('criteria') or not set(claim['criteria']).issubset(criterion_ids):
                raise ValueError(f'{cid}: empty or invalid scoring criterion mapping')
            selectors = claim.get('sections', [])
            if not selectors or not all(isinstance(s, str) and s.strip() for s in selectors):
                raise ValueError(f'{cid}: section selectors must be a non-empty list')
            if not all(any(matches(key, prefix) for key in current) for prefix in selectors):
                self.blockers.append(f'{cid}: a section locator no longer resolves; refresh index')
            related = [s for s in changed_sections if any(matches(s['key'], p) for p in selectors)]
            mapped.update(s['key'] for s in related)
            reasons = []
            if related:
                reasons.append('manuscript_section_changed')
            if set(claim.get('evidence_ids', [])) & changed_evidence:
                reasons.append('evidence_or_dependency_changed')
            if set(claim.get('source_ids', [])) & attention_sources:
                reasons.append('source_scope_or_comparison_attention')
            if reasons:
                affected[cid] = reasons
                direct.add(cid)
        # Fixed-point propagation is conservative even when claims cross-reference each other.
        while True:
            added = {cid: ['dependent_claim_affected'] for cid, cl in claims.items() if cid not in affected and set(cl.get('depends_on', [])) & set(affected)}
            if not added:
                break
            affected.update(added)
        unknown = [s for s in changed_sections if s['key'] not in mapped]
        coverage_unknown = c.get('evidence_inventory_confirmed') is not True
        if coverage_unknown:
            self.blockers.append('Evidence inventory completeness has not been explicitly confirmed.')
        fallback = bool(unknown or removed or coverage_unknown or policy_recalibration)
        criteria = sorted({r for cid in affected for r in claims[cid]['criteria']})
        if fallback:
            criteria = [r['id'] for r in load(local(self.root, c['rubric']))['criteria']]
            self.warnings.append('Unmapped changes/material: full review fallback; no unaffected claim is certified.')
        self.timings['impact_seconds'] = time.perf_counter()-stage
        self.current_path, self.previous_path = current_path, previous_path
        self.diff = ''.join(difflib.unified_diff(before_text.splitlines(True), text.splitlines(True), fromfile='baseline', tofile='current'))
        self.timings['total_seconds'] = time.perf_counter()-started
        self.report = {'schema_version': 1, 'tool_version': VERSION, 'tool_sha256': self.tool_hash,
                       'ready_for_dispatch': not self.blockers, 'blockers': self.blockers, 'warnings': self.warnings,
                       'config_sha256': digest(local(self.root, c['_config_path'])), 'review_mode': c['review_mode'],
                       'baseline_manuscript_sha256': digest(previous_path), 'current_manuscript_sha256': digest(current_path),
                       'policy_fingerprints': policy, 'evidence': evidence, 'removed_or_unmapped_evidence_ids': removed,
                       'excluded_baseline_evidence': exclusions,
                       'evidence_inventory_scope': c.get('evidence_inventory_scope', 'not specified'),
                       'checks': checks, 'cache_authenticated': self.cache_secret is not None,
                       'cache_statistics': self.stats, 'timings': self.timings,
                       'figure_scope': FIGURE_SCOPE, 'not_a_score_or_publication_approval': True}
        self.impact = {'changed_sections': changed_sections, 'unmapped_changed_sections': unknown,
                       'affected_criteria': criteria, 'full_review_fallback': fallback,
                       'claims': [{**cl, 'review_reasons': affected.get(cid, []),
                                  'status': 'reread_required' if cid in affected or fallback else 'no_change_detected_in_declared_scope'} for cid, cl in claims.items()],
                       'note': 'Routing only; formal independent reading, forensic adjudication and publication checks remain required.'}
        return self.report, self.impact

    @staticmethod
    def _looks_like_scorecard(path):
        if path.suffix.lower() != '.json':
            return False
        try:
            candidate = load(path)
            return (isinstance(candidate, dict) and isinstance(candidate.get('criteria'), list)
                    and bool(candidate.get('assessment_id') or candidate.get('raw_maximum')))
        except (OSError, ValueError, UnicodeError):
            return False

    def stable(self):
        return all(local(self.root, p).is_file() and digest(local(self.root, p)) == h for p, h in self.guard.items())

    def freeze(self, out):
        if self.blockers or not self.stable():
            raise ValueError('Preparation blocked or inputs drifted; cannot freeze reviewer packet')
        target = out / 'reviewer-packet'
        # Construct privately and promote atomically; never reuse or overwrite an old packet.
        with tempfile.TemporaryDirectory(prefix='.packet-', dir=out) as name:
            staging = Path(name)
            copies = [(self.previous_path, 'manuscripts/baseline.md'), (self.current_path, 'manuscripts/current.md')]
            copies += [(local(self.root, e['path']), f'evidence/{e["id"]}{Path(e["path"]).suffix}') for e in self.config['evidence']]
            copies += [(local(self.root, self.config[k]), f'{k}{Path(self.config[k]).suffix}') for k in ('rubric', 'anchors', 'reviewer_instructions')]
            names = [n for _, n in copies]
            if len(names) != len(set(names)) or any(not re.fullmatch(r'[A-Za-z0-9_.\-/]+', n) or '..' in Path(n).parts for n in names):
                raise ValueError('Unsafe or duplicate packet file name')
            for source, destination in copies:
                dest = staging / destination
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, dest)
                if digest(dest) != digest(source):
                    raise ValueError('Input changed during packet copy')
            if not self.stable():
                raise ValueError('Input drift during freezing; rerun preparation')
            inventory = [{'path': str(p.relative_to(staging)), 'sha256': digest(p), 'bytes': p.stat().st_size}
                         for p in sorted(staging.rglob('*')) if p.is_file()]
            save(staging / 'manifest.json', {'schema_version': 1, 'files': inventory,
                 'packet_fingerprint': signature(inventory), 'figure_scope': FIGURE_SCOPE,
                 'historical_scorecards_and_reviewer_reports_excluded': True})
            if target.exists():
                raise ValueError('Frozen packet already exists; choose a new output directory')
            os.rename(staging, target)
        return str(target)


def run(args):
    root = args.project.resolve()
    config_path = local(root, str(args.config))
    config = load(config_path)
    out, cache = local(root, str(args.out)), local(root, str(args.cache_dir))
    if out == root or out.exists() or cache == root or out == cache or out in cache.parents or cache in out.parents:
        raise ValueError('Output must be a new project-local directory')
    if config.get('review_mode') not in {'paired_revision', 'calibration_pair'}:
        raise ValueError('review_mode must be paired_revision or calibration_pair')
    config['_config_path'] = str(config_path.relative_to(root))
    for claim in config.get('claims', []):
        if not re.fullmatch(r'[A-Za-z0-9_-]+', claim['id']):
            raise ValueError('Claim IDs require safe alphanumeric names')
    for evidence in config.get('evidence', []):
        if not re.fullmatch(r'[A-Za-z0-9_-]+', evidence['id']):
            raise ValueError('Evidence IDs require safe alphanumeric names')
    prep = Preparer(root, config, cache, args.run_checks, args.rerun_checks)
    prep.input(str(config_path))
    report, impact = prep.prepare()
    if not prep.stable():
        report['blockers'].append('Input changed during preparation; rerun')
        report['ready_for_dispatch'] = False
    out.mkdir(parents=True, exist_ok=False)
    save(out / 'preflight.json', report)
    save(out / 'impact-index.json', impact)
    (out / 'manuscript.diff').write_text(prep.diff, encoding='utf-8')
    plan = ['# 论文评分准备与重读清单', '', f'准备状态：{report["ready_for_dispatch"]}；这不是评分或发布许可。', '',
            f'缓存：{json.dumps(report["cache_statistics"], ensure_ascii=False)}',
            f'耗时：{json.dumps(report["timings"], ensure_ascii=False)}', '', '## 阻断项', '']
    plan += report['blockers'] or ['无']
    plan += ['', '## 提醒', ''] + report['warnings'] + ['', '## 主张重读', '']
    plan += [f'- {cl["id"]}：{cl["status"]}；原因={", ".join(cl["review_reasons"]) or "未检测到登记范围内变化"}；位置={", ".join(cl["sections"])}；证据={", ".join(cl.get("evidence_ids", []))}' for cl in impact['claims']]
    plan += ['', '正式评分仍按现有协议完成独立评阅、证据裁定和发布核验。未登记的新材料需补入配置；图像及全页视觉验收另审。']
    (out / 'review-plan.md').write_text('\n'.join(plan)+'\n', encoding='utf-8')
    frozen = prep.freeze(out) if args.freeze and report['ready_for_dispatch'] else None
    print(json.dumps({'ready_for_dispatch': report['ready_for_dispatch'], 'out': str(out), 'frozen_packet': frozen,
                      'cache': report['cache_statistics'], 'timings': report['timings'], 'blockers': report['blockers']}, ensure_ascii=False, indent=2))
    return 0 if report['ready_for_dispatch'] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path.cwd())
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--cache-dir', type=Path, default=Path('.cache/thesis-review'))
    parser.add_argument('--run-checks', action='store_true', help='Execute registered local Python checks on cache misses')
    parser.add_argument('--rerun-checks', action='store_true', help='Ignore successful computation cache; requires --run-checks')
    parser.add_argument('--freeze', action='store_true', help='Freeze a new reviewer packet only if preparation has no blockers')
    args = parser.parse_args()
    if args.rerun_checks and not args.run_checks:
        parser.error('--rerun-checks requires --run-checks')
    try:
        return run(args)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({'ready_for_dispatch': False, 'error': str(exc)}, ensure_ascii=False))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
