"""限速获取官方JPL元数据；仅保留研究必要字段，不保存令牌或用户字段。"""
import argparse
import base64
from datetime import datetime, timezone
import getpass
import hashlib
import json
import os
from pathlib import Path
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = 'https://ev.caltech.edu/api/v1/sessions/jpl'
FIELDS = ('siteID', 'clusterID', 'stationID', 'spaceID', 'connectionTime',
          'disconnectTime', 'doneChargingTime', 'kWhDelivered', 'timezone')


def minimize(row):
    """输出必要会话字段和不可逆会话键；缺失稳定键时拒绝静默去重。"""
    key = row.get('sessionID') or row.get('_id')
    if not key:
        raise ValueError('Missing stable session key')
    return dict(session_key=hashlib.sha256(str(key).encode()).hexdigest(),
                **{k: row.get(k) for k in FIELDS})


def run(destination, audit_dir, page_size=1000, delay=0.6, max_pages=1500):
    """串行分页并检查总量、重复与来源；未完成快照不允许被标记为完整。"""
    if destination.exists() or audit_dir.exists():
        raise FileExistsError('Use a new snapshot directory; overwriting is forbidden')
    token = getpass.getpass('ACN API token (hidden): ').strip()
    if not token:
        raise ValueError('Missing token')
    authorization = 'Basic ' + base64.b64encode((token + ':').encode()).decode()
    token = None
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    destination.mkdir(parents=True, mode=0o700)
    audit_dir.mkdir(parents=True)
    output = destination / 'sessions.jsonl'
    pages, seen, expected = [], set(), None
    next_url = BASE + '?' + urllib.parse.urlencode({'sort': 'connectionTime', 'max_results': page_size})
    status = 'incomplete'
    error = None
    try:
        with output.open('x', encoding='utf-8') as stream:
            os.chmod(output, 0o600)
            while next_url:
                if len(pages) >= max_pages:
                    raise RuntimeError('Maximum-page guard reached')
                parsed = urllib.parse.urlsplit(next_url)
                if parsed.scheme != 'https' or parsed.netloc != 'ev.caltech.edu' or parsed.path != '/api/v1/sessions/jpl':
                    raise ValueError('Unexpected pagination URL')
                raw = None
                for attempt in range(3):
                    try:
                        request = urllib.request.Request(next_url, headers={'Authorization': authorization, 'User-Agent': 'EVCS-JPL-metadata-census/1.0'})
                        with opener.open(request, timeout=40) as response:
                            raw = response.read(12_000_001)
                        break
                    except (urllib.error.URLError, TimeoutError) as exc:
                        if attempt == 2:
                            raise RuntimeError('API request failed: ' + type(exc).__name__) from None
                        time.sleep(2 ** (attempt + 1))
                if len(raw) > 12_000_000:
                    raise ValueError('Response size guard reached')
                payload = json.loads(raw)
                meta = payload['_meta']
                total = int(meta['total'])
                if expected is not None and total != expected:
                    raise ValueError('Dynamic API total changed during acquisition')
                expected = total
                rows = payload['_items']
                for row in rows:
                    clean = minimize(row)
                    if clean['session_key'] in seen:
                        raise ValueError('Repeated session across pages; snapshot not stable')
                    seen.add(clean['session_key'])
                    stream.write(json.dumps(clean, sort_keys=True, ensure_ascii=False) + '\n')
                pages.append(dict(page=int(meta['page']), records=len(rows), max_results=int(meta['max_results']), response_sha256=hashlib.sha256(raw).hexdigest()))
                link = payload.get('_links', {}).get('next', {}).get('href')
                next_url = urllib.parse.urljoin('https://ev.caltech.edu/api/v1/', link) if link else None
                if len(pages) == 1 or len(pages) % 25 == 0 or not next_url:
                    print(json.dumps(dict(pages=len(pages), records=len(seen), total=expected, page_size=int(meta['max_results']))), flush=True)
                if next_url:
                    time.sleep(delay)
        if len(seen) != expected:
            raise ValueError('Fetched count differs from API total')
        status = 'complete'
    except Exception as exc:
        error = type(exc).__name__ + ': ' + str(exc)[:160]
        raise
    finally:
        summary = dict(dataset_id='DATA-JPL-METADATA-20261005', source=BASE,
                       retrieved_at_utc=datetime.now(timezone.utc).isoformat(), status=status,
                       total_reported=expected, records_saved=len(seen), pages=pages, error=error,
                       snapshot_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
                       script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                       fields_saved=list(FIELDS) + ['session_key'], personal_fields_saved=False,
                       credential_saved=False, access='local research only; redistribution unconfirmed',
                       measurement_time_series_acquired=False)
        (audit_dir / 'acquisition.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--audit-dir', type=Path, required=True)
    parser.add_argument('--page-size', type=int, default=1000)
    parser.add_argument('--delay', type=float, default=0.6)
    args = parser.parse_args()
    if not 1 <= args.page_size <= 1000 or args.delay < 0.5:
        parser.error('Use page size <=1000 and serial request spacing >=0.5 seconds')
    run(args.destination, args.audit_dir, args.page_size, args.delay)
