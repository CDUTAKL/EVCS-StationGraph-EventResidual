"""Bounded public JPL feasibility probe; metadata census plus fixed trace samples.

No training, API token, raw trace storage, test performance or target building.
Filename prefixes are candidate measurement identifiers, not certified EVSEs.
"""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import urllib.parse
import urllib.request

import numpy as np
import pandas as pd

REPO = 'tongxin-li/ACN-Data-Static'
EXPECTED_COMMIT = 'abb7cf15cc7108913e965d4375cc7270d532b65f'
PATTERN = re.compile(r'(?P<prefix>.+)-(?P<date>\d{4}-\d{2}-\d{2})T(?P<h>\d{2})-(?P<m>\d{2})-(?P<s>\d{2})-(?P<us>\d+)\.csv\.gz')


def describe_path(path):
    match = PATTERN.fullmatch(Path(path).name)
    if not match:
        raise ValueError('Unrecognized filename: ' + path)
    d = match.groupdict()
    return dict(path=path, candidate_id=d['prefix'], filename_timestamp=d['date']+'T'+d['h']+':'+d['m']+':'+d['s']+'.'+d['us'])


def sample_indices(n):
    return sorted({0, n//2, n-1})


def trace_stats(frame):
    t = pd.to_datetime(frame.iloc[:, 0], utc=True, errors='coerce')
    good = t.dropna()
    dt = np.diff(good.astype('int64').to_numpy()) / 1e9
    result = dict(rows=len(frame), columns=frame.columns.tolist(), timestamp_missing=int(t.isna().sum()),
                  timestamp_duplicates=int(good.duplicated().sum()), strictly_increasing=bool(len(dt) and (dt > 0).all()),
                  first_timestamp=str(good.iloc[0]) if len(good) else None,
                  last_timestamp=str(good.iloc[-1]) if len(good) else None,
                  duration_hours=float((good.iloc[-1]-good.iloc[0]).total_seconds()/3600) if len(good) else None,
                  max_gap_seconds=float(dt.max()) if len(dt) else None,
                  gap_over_60_seconds=int((dt > 60).sum()), fields={})
    for col in frame.columns[1:]:
        a = pd.to_numeric(frame[col], errors='coerce')
        valid = a.dropna()
        result['fields'][col] = dict(nonmissing=int(frame[col].notna().sum()), numeric_valid=int(np.isfinite(a).sum()),
                                    negative=int((a < 0).sum()), min=float(valid.min()) if len(valid) else None,
                                    max=float(valid.max()) if len(valid) else None)
    energy = pd.to_numeric(frame.get('Energy Delivered (kWh)', pd.Series(dtype=float)), errors='coerce').dropna()
    result['cumulative_energy_monotonic'] = bool(len(energy)>1 and (np.diff(energy.to_numpy()) >= -1e-8).all())
    result['cumulative_energy_span_kwh'] = float(energy.iloc[-1]-energy.iloc[0]) if len(energy)>1 else None
    return result


def probe(item):
    path = item['path']
    url = 'https://raw.githubusercontent.com/'+REPO+'/'+EXPECTED_COMMIT+'/'+urllib.parse.quote(path)
    row = dict(**item, url=url)
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent':'EVCS-JPL-feasibility-audit'}), timeout=25) as response:
            blob = response.read(2_000_001)
        if len(blob)>2_000_000:
            raise ValueError('Compressed sample exceeds 2MB guard')
        git_sha = hashlib.sha1(b'blob '+str(len(blob)).encode()+b'\0'+blob).hexdigest()
        if git_sha != item['git_blob_sha1']:
            raise ValueError('Git object digest mismatch')
        with gzip.GzipFile(fileobj=io.BytesIO(blob)) as g:
            payload = g.read(30_000_001)
        if len(payload)>30_000_000:
            raise ValueError('Expanded sample exceeds 30MB guard')
        frame = pd.read_csv(io.BytesIO(payload))
        row.update(status='READ', compressed_bytes=len(blob), sha256=hashlib.sha256(blob).hexdigest(), **trace_stats(frame))
    except Exception as error:
        row.update(status='FAILED', error=type(error).__name__+': '+str(error)[:180])
    return row


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--metadata-repo', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    head = subprocess.check_output(['git','-C',str(args.metadata_repo),'rev-parse','HEAD']).decode().strip()
    if head != EXPECTED_COMMIT:
        raise ValueError('Repository revision changed')
    tree = subprocess.check_output(['git','-C',str(args.metadata_repo),'ls-tree','-r','HEAD','time series data/jpl'])
    inventory = []
    for line in tree.decode().splitlines():
        spec, path = line.split('\t', 1)
        if path.endswith('.csv.gz'):
            inventory.append(dict(**describe_path(path), git_blob_sha1=spec.split()[2]))
    groups = defaultdict(list)
    for item in inventory:
        groups[item['candidate_id']].append(item)
    candidates, selected = [], []
    for node in sorted(groups):
        files = sorted(groups[node], key=lambda x:x['filename_timestamp'])
        months = Counter(x['filename_timestamp'][:7] for x in files)
        candidates.append(dict(candidate_id=node, files=len(files), first=files[0]['filename_timestamp'],
                               last=files[-1]['filename_timestamp'], months_with_files=len(months), monthly_files=dict(sorted(months.items()))))
        selected.extend(files[i] for i in sample_indices(len(files)))
    args.out.mkdir(parents=True)
    def save(name, data):
        (args.out/name).write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    save('inventory.json', inventory)
    save('candidate_coverage.json', candidates)
    save('selection.json',dict(rule='Earliest, chronological median and latest file per filename prefix; fixed before reading measurements', commit=head, samples=selected))
    print('Frozen census:',len(inventory),'files,',len(candidates),'candidate prefixes;',len(selected),'samples',flush=True)
    rows = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        for i, row in enumerate(pool.map(probe,selected),1):
            rows.append(row)
            if i%20==0 or i==len(selected):
                print('Sample progress',i,'/',len(selected),'read',sum(x['status']=='READ' for x in rows),flush=True)
    save('sample_audit.json', rows)
    good = [x for x in rows if x['status']=='READ']
    columns = sorted(set(c for x in good for c in x['fields']))
    save('summary.json', dict(dataset_id='DATA-JPL-FEASIBILITY-20261004', repository=REPO, commit=head,
          metadata_tree_sha256=hashlib.sha256(tree).hexdigest(), inventory_files=len(inventory), candidate_prefixes=len(candidates),
          first_filename_timestamp=min(x['filename_timestamp'] for x in inventory),last_filename_timestamp=max(x['filename_timestamp'] for x in inventory),
          selected=len(selected),read=len(good), failed=len(rows)-len(good),
          timestamp_order_pass=sum(x['strictly_increasing'] and not x['timestamp_missing'] and not x['timestamp_duplicates'] for x in good),
          max_gap_seconds_max=max((x['max_gap_seconds'] or 0) for x in good) if good else None,
          fields={c:dict(samples_with_any_value=sum(x['fields'].get(c,{}).get('nonmissing',0)>0 for x in good),
                         numeric_rows=sum(x['fields'].get(c,{}).get('numeric_valid',0) for x in good)) for c in columns},
          cumulative_energy_monotonic_pass=sum(x['cumulative_energy_monotonic'] for x in good),
          raw_traces_saved=False, training_performed=False, physical_node_mapping_confirmed=False,
          full_trace_coverage_confirmed=False, original_session_contract_available=False,
          license_status='research/education wording on official registration; standalone static-repo license absent; redistribution unconfirmed',
          interpretation='Metadata census and non-random boundary probes only; no performance results or certified reconstructed target.'))
    save('sources.json',dict(script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),commit=head,
                             metadata_repository=str(args.metadata_repo),raw_trace_storage='none; read in memory'))
    save('manifest.json',{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(args.out.iterdir())})
    print('Done; no raw traces saved',flush=True)


if __name__=='__main__':
    main()
