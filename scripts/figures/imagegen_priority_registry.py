"""Verify native ImageGen raster assets against the reviewed provenance registry.

This is an asset verifier, NOT a deterministic image-generation implementation.
The prompt, source image and native generation output are recorded separately.
"""
from pathlib import Path
import hashlib
import json

REGISTRY=Path('outputs/figures/priority-review-20260907/imagegen_provenance.json')

def main():
    entries=json.loads(REGISTRY.read_text())['entries']
    for item in entries:
        if item.get('status')!='accepted':
            raise ValueError('ImageGen review unfinished: '+item['stem'])
        p=Path('outputs/figures')/(item['stem']+'.png')
        assert hashlib.sha256(p.read_bytes()).hexdigest()==item['sha256'],p
    print(f'{len(entries)} ImageGen PNG assets verified; no vector SVG claimed')

if __name__=='__main__': main()
