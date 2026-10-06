#!/usr/bin/env python3
"""Stage the canonical Markdown figure assets into an existing formal DOCX.

The script writes only to the requested candidate path. It preserves the DOCX
template, paragraph/style XML, captions, relationships, and image placement
widths; only the manuscript figure media payloads and their proportional drawing heights
are updated. A leading cover/logo drawing is retained untouched.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import posixpath
import re
import struct
import zipfile
from pathlib import Path

from lxml import etree


NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "pic": "http://schemas.openxmlformats.org/drawingml/2006/picture",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}
EMU_PER_CM = 360_000
DOC_XML = "word/document.xml"
RELS_XML = "word/_rels/document.xml.rels"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def png_dimensions(data: bytes) -> tuple[int, int]:
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("Expected a valid PNG image")
    width, height = struct.unpack(">II", data[16:24])
    if not width or not height:
        raise ValueError("PNG has an empty dimension")
    return width, height


def part_name(target: str) -> str:
    if target.startswith("/"):
        return posixpath.normpath(target.lstrip("/"))
    return posixpath.normpath(posixpath.join("word", target))


def source_figures(source: Path) -> tuple[list[Path], list[tuple[int, int]]]:
    text = source.read_text(encoding="utf-8")
    links = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", text)
    captions = [(int(ch), int(num)) for ch, num in re.findall(r"\*\*图(\d+)-(\d+)\b", text)]
    expected = [(ch, num) for ch, count in ((1, 2), (2, 13), (3, 16), (4, 6), (5, 9))
                for num in range(1, count + 1)]
    if len(links) != len(expected) or captions != expected:
        raise ValueError(f"Expected {len(expected)} ordered figures/captions; got {len(links)} links and {len(captions)} captions")
    paths = []
    for (chapter, number), link in zip(captions, links):
        path = (source.parent / link).resolve()
        if path.suffix.lower() == ".svg":
            path = path.with_suffix(".png")
        if f"fig{chapter}_{number}_" not in path.name:
            raise ValueError(f"Figure link does not match caption 图{chapter}-{number}: {path}")
        if not path.is_file():
            raise FileNotFoundError(path)
        paths.append(path)
    return paths, captions


def read_image_refs(zf: zipfile.ZipFile):
    relroot = etree.fromstring(zf.read(RELS_XML))
    rels = {rel.get("Id"): rel.get("Target") for rel in relroot}
    doc = etree.fromstring(zf.read(DOC_XML))
    paras = doc.xpath("//w:body/w:p", namespaces=NS)
    refs = []
    for pindex, para in enumerate(paras):
        for blip in para.xpath(".//a:blip", namespaces=NS):
            rid = blip.get(f"{{{NS['r']}}}embed")
            if rid not in rels or not rels[rid]:
                raise ValueError(f"Missing image relationship for {rid}")
            target = part_name(rels[rid])
            drawing = blip.xpath("ancestor::wp:inline[1] | ancestor::wp:anchor[1]", namespaces=NS)
            if len(drawing) != 1:
                raise ValueError(f"Expected one picture drawing for {rid}")
            refs.append({"rid": rid, "target": target, "para": pindex, "blip": blip,
                         "drawing": drawing[0], "paras": paras})
    return doc, refs


def caption_after(ref: dict) -> str:
    for para in ref["paras"][ref["para"] + 1:]:
        text = "".join(para.xpath(".//w:t/text()", namespaces=NS)).strip()
        if text:
            return text
    return ""


def visible_aspect(drawing, width: int, height: int) -> float:
    source_rect = drawing.xpath(".//a:srcRect[1]", namespaces=NS)
    crop_w = crop_h = 100_000
    if source_rect:
        rect = source_rect[0]
        crop_w -= int(rect.get("l", "0")) + int(rect.get("r", "0"))
        crop_h -= int(rect.get("t", "0")) + int(rect.get("b", "0"))
    if crop_w <= 0 or crop_h <= 0:
        raise ValueError("Invalid source crop on image")
    return width / height * crop_w / crop_h


def set_image_height(ref: dict, png_data: bytes) -> tuple[int, int]:
    width, height = png_dimensions(png_data)
    extents = ref["drawing"].xpath("./wp:extent", namespaces=NS)
    inner = ref["drawing"].xpath(".//pic:spPr/a:xfrm/a:ext", namespaces=NS)
    if len(extents) != 1 or len(inner) != 1:
        raise ValueError(f"Drawing {ref['rid']} does not have a single editable extent")
    cx = int(extents[0].get("cx"))
    cy = round(cx / visible_aspect(ref["drawing"], width, height))
    for extent in (extents[0], inner[0]):
        extent.set("cx", str(cx))
        extent.set("cy", str(cy))
    return cx, cy


def check_caption(ref: dict, number: tuple[int, int]) -> None:
    ch, fig = number
    text = caption_after(ref)
    if not re.match(rf"^图\s*{ch}\s*[-－]\s*{fig}(?:\D|$)", text):
        raise ValueError(f"DOCX image order/caption mismatch: expected 图{ch}-{fig}, found {text[:100]!r}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--source", type=Path, default=Path("docs/thesis/thesis-manuscript.md"))
    parser.add_argument("--output", type=Path, required=True,
                        help="Candidate DOCX path; must differ from --input")
    args = parser.parse_args()
    input_path = args.input.resolve()
    output_path = args.output.resolve()
    source_path = args.source.resolve()
    if input_path == output_path:
        raise ValueError("Candidate output must not overwrite the source DOCX")
    if output_path.exists():
        raise FileExistsError(f"Refusing to overwrite existing candidate: {output_path}")

    figures, captions = source_figures(source_path)
    payloads = [p.read_bytes() for p in figures]
    for payload in payloads:
        png_dimensions(payload)

    with zipfile.ZipFile(input_path, "r") as zin:
        doc, refs = read_image_refs(zin)
        if len(refs) != len(figures) + 1:
            raise ValueError(f"Expected one cover mark plus {len(figures)} figure embeds; found {len(refs)}")
        if refs[0]["target"].lower().endswith(".png"):
            raise ValueError("Expected the first document image to be the untouched non-figure cover mark")
        figure_refs = refs[1:]
        if any(not ref["target"].lower().endswith(".png") for ref in figure_refs):
            raise ValueError("Expected all manuscript figures to use PNG media parts")
        targets = [ref["target"] for ref in figure_refs]
        if len(set(targets)) != len(targets):
            raise ValueError("A figure media part is reused; refusing ambiguous ordered replacement")
        for ref, caption in zip(figure_refs, captions):
            check_caption(ref, caption)

        replacements = {}
        extent_report = []
        for ref, path, payload, caption in zip(figure_refs, figures, payloads, captions):
            replacements[ref["target"]] = payload
            cx, cy = set_image_height(ref, payload)
            extent_report.append({
                "figure": f"图{caption[0]}-{caption[1]}",
                "source": str(path),
                "sha256": digest(payload),
                "display_cm": [round(cx / EMU_PER_CM, 3), round(cy / EMU_PER_CM, 3)],
            })

        updated_document = etree.tostring(doc, xml_declaration=True, encoding="UTF-8", standalone=True)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output_path, "w") as zout:
            zout.comment = zin.comment
            for info in zin.infolist():
                data = updated_document if info.filename == DOC_XML else replacements.get(info.filename)
                if data is None:
                    data = zin.read(info.filename)
                zout.writestr(info, data)

    # Re-open the candidate and verify package integrity and exact ordered hashes.
    with zipfile.ZipFile(output_path, "r") as zout:
        bad = zout.testzip()
        if bad:
            raise ValueError(f"Candidate ZIP integrity failed at {bad}")
        checkdoc, checkrefs = read_image_refs(zout)
        checkrefs = checkrefs[1:]
        actual_hashes = [digest(zout.read(ref["target"])) for ref in checkrefs]
        if actual_hashes != [digest(payload) for payload in payloads]:
            raise ValueError("Candidate figure payloads differ from the canonical PNG sequence")
        for ref, caption in zip(checkrefs, captions):
            check_caption(ref, caption)

    print(json.dumps({"candidate": str(output_path), "figures_synced": len(figures),
                      "cover_mark_preserved": True, "captions_in_order": True,
                      "all_payload_hashes_match": True, "figures": extent_report},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
