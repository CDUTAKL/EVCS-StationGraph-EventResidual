#!/usr/bin/env python3
"""Focused structural audit for the isolated thesis DOCX candidate."""
from __future__ import annotations

import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path

from lxml import etree
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from rebuild_docx_formulas import extract_tagged_formulas  # noqa: E402

REV = Path(__file__).resolve().parent
SOURCE = ROOT / "docs/thesis/thesis-manuscript.md"
DOCX = REV / "thesis-candidate.docx"
NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "m": "http://schemas.openxmlformats.org/officeDocument/2006/math",
}
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
EMU_PER_INCH = 914400


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    source_text = SOURCE.read_text(encoding="utf-8")
    figure_paths = [
        (SOURCE.parent / p).resolve().with_suffix(".png")
        for p in re.findall(r"!\[[^]]*\]\(([^)]+)\)", source_text)
    ]
    expected_tags = set(extract_tagged_formulas(source_text))
    image_hash_to_path = {sha(p.read_bytes()): p for p in figure_paths}

    with zipfile.ZipFile(DOCX) as package:
        bad_zip_member = package.testzip()
        document = etree.fromstring(package.read("word/document.xml"))
        rel_root = etree.fromstring(package.read("word/_rels/document.xml.rels"))
        relationships = {node.get("Id"): node.get("Target") for node in rel_root}
        formula_paragraphs = []
        for paragraph in document.xpath("//w:p", namespaces=NS):
            text = "".join(paragraph.xpath(".//w:t/text()", namespaces=NS))
            if paragraph.xpath(".//m:oMath", namespaces=NS) and re.fullmatch(
                r"（[2-5]-\d+）", text
            ):
                formula_paragraphs.append((text[1:-1], paragraph))

        actual_tags = [tag for tag, _ in formula_paragraphs]
        figure_ppi = []
        figure_hashes = []
        for blip in document.xpath('//*[local-name()="blip"]'):
            rid = blip.get(f"{{{REL}}}embed")
            target = "word/" + relationships[rid]
            data = package.read(target)
            digest = sha(data)
            if digest not in image_hash_to_path:
                continue  # template marks are outside the manuscript figure list
            figure_hashes.append(digest)
            drawing = blip
            while drawing is not None and etree.QName(drawing).localname not in {
                "inline",
                "anchor",
            }:
                drawing = drawing.getparent()
            extent = (
                drawing.find(
                    "{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}extent"
                )
                if drawing is not None
                else None
            )
            if extent is None:
                continue
            with Image.open(image_hash_to_path[digest]) as image:
                px_w, px_h = image.size
            figure_ppi.append(
                min(
                    px_w * EMU_PER_INCH / int(extent.get("cx")),
                    px_h * EMU_PER_INCH / int(extent.get("cy")),
                )
            )

    expected_order = sorted(expected_tags, key=lambda tag: tuple(map(int, tag.split("-"))))
    checks = {
        "zip_integrity": bad_zip_member is None,
        "all_tagged_display_equations_native": len(actual_tags) == len(expected_tags)
        and set(actual_tags) == expected_tags
        and len(actual_tags) == len(set(actual_tags)),
        "equation_labels_in_chapter_order": actual_tags == expected_order,
        "all_manuscript_figures_embedded": len(figure_hashes) == len(figure_paths),
        "figure_order_and_hashes_match_source": figure_hashes
        == [sha(path.read_bytes()) for path in figure_paths],
        "all_figures_effective_1200_ppi_or_higher": len(figure_ppi)
        == len(figure_paths)
        and min(figure_ppi, default=0) >= 1200,
    }
    result = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "source": str(SOURCE),
        "source_sha256": sha(source_text.encode("utf-8")),
        "docx": str(DOCX),
        "docx_sha256": sha(DOCX.read_bytes()),
        "docx_bytes": DOCX.stat().st_size,
        "checks": checks,
        "display_equations": {
            "expected": len(expected_tags),
            "native_numbered": len(actual_tags),
            "labels": actual_tags,
        },
        "figures": {
            "expected": len(figure_paths),
            "embedded_source_matches": len(figure_hashes),
            "min_effective_ppi": round(min(figure_ppi), 1) if figure_ppi else None,
            "max_effective_ppi": round(max(figure_ppi), 1) if figure_ppi else None,
        },
        "visual_page_acceptance": "NOT_PERFORMED",
    }
    (REV / "docx-candidate-audit.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
