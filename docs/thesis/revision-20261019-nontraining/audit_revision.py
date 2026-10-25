#!/usr/bin/env python3
"""Audit bounded thesis revisions against the preserved pre-task manuscript."""
from pathlib import Path
from collections import Counter
import hashlib,json,re

ROOT=Path(__file__).resolve().parents[3]
REV=Path(__file__).resolve().parent
BEFORE=REV/'before.md'
CURRENT=ROOT/'docs/thesis/thesis-manuscript.md'
a,b=BEFORE.read_text(),CURRENT.read_text()
scope=json.loads((REV/'scope.json').read_text())
state=json.loads((REV/'before-state.json').read_text())

def sections(text):
    result={}; head='__preamble__';body=[]
    for line in text.splitlines(keepends=True):
        if re.match(r'^#{1,6} ',line):
            result[head]=''.join(body);head=line.lstrip('# ').strip();body=[]
        else:body.append(line)
    result[head]=''.join(body)
    return result

sa,sb=sections(a),sections(b)
changed=[h for h in set(sa)|set(sb) if sa.get(h)!=sb.get(h)]
expected={
'摘  要':({'0.03890':1,'15':1,'1.82':1,'1.52':1},{}),
'1.2.2 多节点负荷与时空图预测':({'73':1},{}),
'1.5 技术路线':({},{}),
'1.6 论文组织结构':({},{}),
'3.5.4 节点级门控':({'3.7.2':1,'1':1},{'3.6.2':1}),
'5.4.1 预测量与运行量的对应':({'1':1,'4':1},{}),
'研究局限与后续工作':({'1':1},{}),
}
num_deltas=[]
for h in changed:
    aa=Counter(re.findall(r'\d+(?:\.\d+)*',sa.get(h,'')))
    bb=Counter(re.findall(r'\d+(?:\.\d+)*',sb.get(h,'')))
    added,removed=dict(bb-aa),dict(aa-bb)
    exadd,exrem=expected.get(h,({},{}))
    num_deltas.append({'heading':h,'added':added,'removed':removed,'matches_reviewed_allowance':added==exadd and removed==exrem})
protected={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==sha for p,sha in state['protected'].items()}
checks={
'heading_sequence_unchanged':re.findall(r'^#{1,6} .+$',a,re.M)==re.findall(r'^#{1,6} .+$',b,re.M),
'changes_within_allowed_headings':all(h in scope['allowed_headings'] for h in changed),
'all_markdown_table_rows_unchanged':[x for x in a.splitlines() if x.startswith('|')]==[x for x in b.splitlines() if x.startswith('|')],
'display_equations_unchanged':re.findall(r'\$\$.*?\$\$',a,re.S)==re.findall(r'\$\$.*?\$\$',b,re.S),
'figure_links_unchanged':re.findall(r'!\[[^]]*\]\([^)]+\)',a)==re.findall(r'!\[[^]]*\]\([^)]+\)',b),
'reference_entries_unchanged':sa.get('参考文献')==sb.get('参考文献'),
'numeric_changes_match_reviewed_allowances':all(x['matches_reviewed_allowance'] for x in num_deltas),
'protected_scoring_and_scientific_records_unchanged':all(protected.values()),
'correct_fixed_gate_reference':'详见3.7.2节及附表A-1' in sb['3.5.4 节点级门控'],
'correct_tau_definition':'以目标片左端时刻$\\tau$标记时间片' in sb['5.4.1 预测量与运行量的对应'],
'gate_budget_followup_is_paired':'共同延长的预算比较节点级与共享门控' in sb['研究局限与后续工作'],
}
result={'status':'PASS' if all(checks.values()) else 'FAIL','checks':checks,'changed_headings':sorted(changed),'numeric_deltas':num_deltas,'protected_records':protected,'before_sha256':hashlib.sha256(BEFORE.read_bytes()).hexdigest(),'current_sha256':hashlib.sha256(CURRENT.read_bytes()).hexdigest(),'scope':'Bounded Markdown and protected-record consistency; not scientific rerun, formal scoring or Word/PDF visual acceptance.'}
(REV/'revision-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':result['status'],'checks':checks,'numeric_deltas':num_deltas},ensure_ascii=False,indent=2))
raise SystemExit(0 if result['status']=='PASS' else 1)
