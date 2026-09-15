"""Check every manuscript figure against the actual ordered DOCX image embeds."""
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile
from lxml import etree

root = Path(__file__).resolve().parents[1]
source = root / 'docs/thesis/thesis-manuscript.md'
paths = [(source.parent / p).resolve().with_suffix('.png') for p in re.findall(r'!\[[^\]]*\]\(([^)]+)\)', source.read_text())]
sha = lambda b: hashlib.sha256(b).hexdigest()
with zipfile.ZipFile(sys.argv[1]) as z:
    rels = {r.get('Id'): r.get('Target') for r in etree.fromstring(z.read('word/_rels/document.xml.rels'))}
    doc = etree.fromstring(z.read('word/document.xml'))
    embeds = doc.xpath('//*[local-name()="blip"]/@*[local-name()="embed"]')
    actual = [sha(z.read('word/' + rels[e])) for e in embeds]
    expected = [sha(p.read_bytes()) for p in paths]
    # Template logos may precede the first manuscript figure.
    start = actual.index(expected[0])
    assert actual[start:] == expected, 'DOCX image order/hash differs from manuscript'
report = {'docx': sys.argv[1], 'figure_count': len(paths), 'ordered_hash_match': True,
          'figures': [{'path': str(p), 'sha256': h} for p,h in zip(paths, expected)]}
print(json.dumps(report, ensure_ascii=False, indent=2))
