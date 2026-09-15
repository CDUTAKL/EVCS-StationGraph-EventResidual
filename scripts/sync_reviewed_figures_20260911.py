"""Promote the nine conversation-reviewed originals, preserving replaced assets."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / 'outputs/figures'
WORK = Path('/Users/xushuyuan/Documents/Codex/2026-08-01/019f6b74-a345-7470-8376-6c8a037940f3/imagegen-redraw-20260906')
SOURCES = {
    'fig1_2_roadmap': WORK / 'fig1_2_roadmap_v2.png',
    'fig2_1_data_reconstruction': WORK / 'fig2_1_data_reconstruction.png',
    'fig3_8_train_predict_pipeline': WORK / 'fig3_6_train_predict_pipeline.png',
    'fig3_6_gate_residual_detail': WORK / 'fig3_13_gate_residual_detail_v3.png',
    'fig3_7_cross_layer_detail': WORK / 'fig3_14_cross_layer_detail_v5.png',
    'fig4_1_three_layer_framework': WORK / 'fig4_1_three_layer_framework.png',
    **{stem: FIG / 'priority-review-20260907' / f'fig3_{n}_thesis_style_20260909.png'
       for n, stem in [(1, 'fig3_1_mrggcn_architecture'), (2, 'fig3_2_relation_propagation_unit'), (3, 'fig3_3_temporal_skip_fusion')]},
}

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    assert all(p.is_file() for p in SOURCES.values())
    archive = FIG / 'archive-before-reviewed-sync-20260911'
    archive.mkdir(exist_ok=True)
    registry_path = FIG / 'priority-review-20260907/imagegen_provenance.json'
    registry = json.loads(registry_path.read_text())
    entries = {e['stem']: e for e in registry['entries']}
    changes = []
    for stem, source in SOURCES.items():
        target = FIG / (stem + '.png')
        old_hash = sha(target)
        for suffix in ('.png', '.svg'):
            old = FIG / (stem + suffix)
            if old.exists() and not (archive / old.name).exists():
                shutil.copy2(old, archive / old.name)
        shutil.copy2(source, target)
        # Do not advertise the obsolete vector drawing as the approved raster.
        stale_svg = FIG / (stem + '.svg')
        if stale_svg.exists():
            stale_svg.unlink()
        e = entries.setdefault(stem, {'stem': stem})
        e.update(status='accepted', selected_path=str(source), sha256=sha(target),
                 reviewed_at='2026-09-11', review_scope='Restore conversation-reviewed ImageGen original; topology and labels visually checked',
                 workspace_output=str(source))
        changes.append({'stem': stem, 'source': str(source), 'before_sha256': old_hash, 'sha256': sha(target)})
    registry['entries'] = list(entries.values())
    registry_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + '\n')
    # Mechanical path/source remapping only; leave thesis prose and results untouched.
    manifest = ROOT / 'scripts/figures/figure_manifest.py'
    text = manifest.read_text()
    import re
    for stem in SOURCES:
        text = re.sub(r'("' + stem + r'": )[^,\n]+,', r'\1"imagegen_priority_registry.py",', text, count=1)
    pos = text.index('PNG_ONLY = {') + len('PNG_ONLY = {')
    already = text[pos:text.index('}', pos)]
    text = text[:pos] + ''.join('\n    "' + s + '",' for s in SOURCES if '"'+s+'"' not in already) + text[pos:]
    manifest.write_text(text)
    for path in [ROOT / 'docs/thesis/thesis-manuscript.md', ROOT / 'docs/thesis/figure-captions-and-index-2026-08-01.md']:
        text = path.read_text()
        for stem in SOURCES:
            text = text.replace(stem + '.svg', stem + '.png')
        path.write_text(text)
    (ROOT / 'docs/thesis/reviewed-figure-sync-20260911.json').write_text(json.dumps(changes, ensure_ascii=False, indent=2) + '\n')
    print(f'Promoted {len(changes)} reviewed originals; previous files preserved in {archive}')

if __name__ == '__main__':
    main()
