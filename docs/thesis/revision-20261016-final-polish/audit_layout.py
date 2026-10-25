from pathlib import Path
from lxml import etree
import json,re,subprocess,zipfile,hashlib,posixpath,unicodedata
root=Path(__file__).resolve().parents[3]
out=root/'docs/thesis/revision-20261016-final-polish'
docx=root/'outputs/thesis/基于站内多关系图与机制诊断的充电节点短期负荷预测研究_终轮精修稿_20261016.docx'
pdf=root/'outputs/thesis/audits/final-polish-20261016/wps-layout-check.pdf'
raw=subprocess.run(['pdftotext','-layout',str(pdf),'-'],check=True,stdout=subprocess.PIPE).stdout.decode()
Path('/private/tmp/evcs-final-polish.txt').write_text(raw)
pages=raw.split('\f'); pages=pages[:-1] if not pages[-1].strip() else pages
norm=lambda s:re.sub(r'\s+','',unicodedata.normalize('NFKC',s)).replace('\u00ad','')
npages=[norm(p) for p in pages]
rawtext=subprocess.run(['pdftotext','-raw',str(pdf),'-'],check=True,stdout=subprocess.PIPE).stdout.decode()
rawpages=rawtext.split('\f')
nrawpages=[norm(p) for p in rawpages]
ns={'m':'http://schemas.openxmlformats.org/officeDocument/2006/math','w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
with zipfile.ZipFile(docx) as z:
 xml=etree.fromstring(z.read('word/document.xml'))
 relxml=etree.fromstring(z.read('word/_rels/document.xml.rels'))
 rel={x.get('Id'):x.get('Target') for x in relxml}
 expected=json.loads((root/'docs/thesis/word-wps-audit-20261016-concision-rev9/figure-sync-audit.json').read_text())['figures']
 actual=[]
 for blip in xml.xpath('//a:blip[@r:embed]',namespaces=ns):
  target=rel[blip.get('{'+ns['r']+'}embed')]
  member=posixpath.normpath('word/'+target)
  digest=hashlib.sha256(z.read(member)).hexdigest()
  if digest in {x['sha256'] for x in expected}:actual.append(digest)
 toc_keys=json.loads((root/'docs/thesis/word-wps-audit-20261016-concision-rev9/final-toc-map-20261016-rev9.json').read_text())
 keymap={norm(k):k for k in toc_keys}
 toc={}
 for el in xml.xpath('//w:body/w:p',namespaces=ns):
  text=''.join(el.xpath('.//w:t/text()',namespaces=ns))
  m=re.match(r'^(.*?)(\d+)$',text)
  if m and norm(m[1]) in keymap:toc[keymap[norm(m[1])]]=int(m[2])
 printed={}
 for i,page in enumerate(pages):
  last=[l.strip() for l in page.splitlines() if l.strip()][-1:]
  if last and re.fullmatch(r'\d+',last[0]):printed[int(last[0])]=i
 toc_records=[{'heading':key,'printed_page':num,'physical_page':printed.get(num,-2)+1,'found':num in printed and norm(key) in npages[printed[num]]} for key,num in toc.items()]
 table_records=[];prev=''
 for el in xml.find('w:body',ns):
  if etree.QName(el).localname=='p':
   tx=''.join(el.xpath('.//w:t/text() | .//m:t/text()',namespaces=ns)).strip()
   if tx:prev=tx
  elif etree.QName(el).localname=='tbl':
   cap=prev
   idx=next((i for i,page in enumerate(npages) if norm(cap) in page),None)
   if idx is None:
    plaincap=norm(cap).replace('β','')
    idx=next((i for i,page in enumerate(npages) if plaincap in page.replace('β','').replace('�','')),None)
   pool=''.join(npages[idx:idx+4]) if idx is not None else ''
   rawpool=''.join(nrawpages[idx:idx+4]) if idx is not None else ''
   cells=[]
   for cell in el.xpath('.//w:tc',namespaces=ns):
    segment=''
    for run in cell.iter():
     if run.tag=='{'+ns['m']+'}t':
      if segment.strip():cells.append(segment.strip())
      segment=''
     elif run.tag=='{'+ns['w']+'}t':segment+=run.text or ''
    if segment.strip():cells.append(segment.strip())
   missing=[c for c in cells if c and norm(c) not in pool and norm(c) not in rawpool]
   table_records.append({'caption':cap,'physical_page':idx+1 if idx is not None else None,'cells':len(cells),'missing_cells':missing})
report={'status':'PASS','pdf_pages':len(pages),'printed_body_pages':len(printed),'printed_body_page_range':[min(printed),max(printed)],'toc_entries':len(toc),'all_toc_entries_match_source_and_pdf_page':len(toc)==len(toc_keys) and all(x['found'] for x in toc_records),'english_abstract_with_keywords_one_page':'Abstract' in pages[5] and 'Keywords:' in pages[5],'figure_count':len(actual),'ordered_figure_hash_match':actual==[x['sha256'] for x in expected],'table_count':len(table_records),'all_table_cell_text_recovered':all(not x['missing_cells'] for x in table_records),'docx_sha256':hashlib.sha256(docx.read_bytes()).hexdigest(),'pdf_sha256':hashlib.sha256(pdf.read_bytes()).hexdigest()}
checks=[report['all_toc_entries_match_source_and_pdf_page'],report['english_abstract_with_keywords_one_page'],report['ordered_figure_hash_match'],report['all_table_cell_text_recovered'],sorted(printed)==list(range(1,max(printed)+1))]
report['status']='PASS' if all(checks) else 'REVIEW_REQUIRED'
(out/'layout-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
(out/'toc-page-audit.json').write_text(json.dumps(toc_records,ensure_ascii=False,indent=2)+'\n')
(out/'final-toc-map.json').write_text(json.dumps({k:str(v) for k,v in toc.items()},ensure_ascii=False,indent=2)+'\n')
(out/'table-text-audit.json').write_text(json.dumps(table_records,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
print('TOC failures:',[x for x in toc_records if not x['found']])
print('TABLE failures:',[(x['caption'],x['missing_cells'][:3]) for x in table_records if x['missing_cells']])
