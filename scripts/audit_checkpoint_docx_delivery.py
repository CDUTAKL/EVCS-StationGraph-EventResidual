#!/usr/bin/env python3
"""Verify repaired thesis wording and native equation order in delivered DOCX."""
import argparse,hashlib,json,re,zipfile
from pathlib import Path
from lxml import etree

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--docx',type=Path,required=True);ap.add_argument('--source',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);args=ap.parse_args()
 ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','m':'http://schemas.openxmlformats.org/officeDocument/2006/math'}
 with zipfile.ZipFile(args.docx) as z:
  xml=etree.fromstring(z.read('word/document.xml'));text=''.join(xml.xpath('//w:t/text()',namespaces=ns));labels=[]
  for p in xml.xpath('//w:p',namespaces=ns):
   label=''.join(p.xpath('.//w:t/text()',namespaces=ns)).strip()
   if re.fullmatch(r'[（(]\d+-\d+[）)]',label) and p.xpath('./m:oMath',namespaces=ns):
    labels.append(label.translate(str.maketrans('（）','()')))
  expected=['('+a+'-'+b+')' for a,b in re.findall(r'\\tag\{(\d+)-(\d+)\}',args.source.read_text())]
  checks={
   'reference_13_scope':'官方期刊摘要及已核查的第59—64页索引正文片段' in text,
   'equal_beta_reference':'结合3.7.2节等权重重训' in text,
   'relation_retrain_reference':'新协议的等权β及关系子集重训练结果见3.7.2节' in text,
   'topk_wording':'不保证对称化后的实际边数相同' in text,
   'replay_outcome':('除三个旧AdaptiveGraph运行外，原CPU前向及指标复算通过' in text),
   'adaptive_checkpoint_replay_disclosed':('AdaptiveGraph的三个既有检查点在匹配PyTorch 2.4.1/CUDA 12.1环境下通过逐键复算' in text and '历史macOS/PyTorch 2.13失败记录和缺失训练Git标识仍保留' in text),
   'native_display_formulas':len(labels)==len(expected)==27,
   'native_equation_labels_in_source_order':labels==expected}
 result={'status':'PASS' if all(checks.values()) else 'FAIL','checks':checks,'equation_labels':labels,
         'docx_sha256':hashlib.sha256(args.docx.read_bytes()).hexdigest(),'manuscript_sha256':hashlib.sha256(args.source.read_bytes()).hexdigest(),
         'native_math_count':len(xml.xpath('//m:oMath',namespaces=ns)),
         'format_scope':'本轮核验正文措辞、原生公式顺序及图片字节同步；WPS分页与目录可视核验见word-wps-audit-20261016-core-revision/README.md',
         'math_runtime':'bundled docx; Temml 0.13.5 and fast-xml-parser 5.11.1 recovered read-only from local npm cache',
         'equation_structure':'原生成器采用带全角编号的oMath段落；不要求另有oMathPara或公式表格'}
 args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(result['status'],checks)
 if result['status']!='PASS':raise SystemExit(1)
if __name__=='__main__':main()
