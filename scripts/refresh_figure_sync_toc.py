"""Refresh cached TOC pages from the image-synchronized PDF's body headings."""
import json
from pathlib import Path
import re
import subprocess

pdf = 'outputs/thesis/figure-sync-20260911/正式论文_已同步审定图片_20260911.pdf'
pages = subprocess.check_output(['pdftotext', '-layout', pdf, '-']).decode().split('\f')
original = json.loads(Path('docs/thesis/final-toc-map-20260909.json').read_text())
norm = lambda s: re.sub(r'\s+', '', s)
found = {}
for i, page in enumerate(pages):
    if i < 15:
        continue
    lines = {norm(line) for line in page.splitlines()}
    for heading in original:
        if norm(heading) in lines and heading not in found:
            found[heading] = i - 14
assert len(found) == len(original) == 109
Path('docs/thesis/final-toc-map-20260911.json').write_text(json.dumps(found, ensure_ascii=False, indent=2) + '\n')
print('109 heading pages mapped; body starts at PDF page 16')
