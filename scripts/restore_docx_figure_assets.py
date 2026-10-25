#!/usr/bin/env python3
"""Restore canonical PNG assets in a Word package without changing pagination.

WPS may downsample embedded figures when saving a DOCX. The document drawing
extents remain in document.xml, so replacing the ordered figure media with the
canonical manuscript PNG bytes restores source resolution without changing the
refreshed TOC fields or layout.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import zipfile
from pathlib import Path

from lxml import etree


ROOT = Path(__file__).resolve().parents[1]
NS = {"r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}


def png_metadata(data: bytes) -> dict:
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("Expected a PNG figure asset")
    width, height = struct.unpack(">II", data[16:24])
    dpi_x = dpi_y = None
    cursor = 8
    while cursor + 12 <= len(data):
        size = struct.unpack(">I", data[cursor:cursor + 4])[0]
        kind = data[cursor + 4:cursor + 8]
        body = data[cursor + 8:cursor + 8 + size]
        if kind == b"pHYs" and len(body) == 9 and body[8] == 1:
            xppm, yppm = struct.unpack(">II", body[:8])
            dpi_x, dpi_y = xppm * 0.0254, yppm * 0.0254
        cursor += size + 12
        if kind == b"IEND":
            break
    return {"width_px": width, "height_px": height, "dpi_x": dpi_x, "dpi_y": dpi_y}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_docx", type=Path)
    parser.add_argument("output_docx", type=Path)
    parser.add_argument("--source", type=Path, default=ROOT / "docs/thesis/thesis-manuscript.md")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    source_text = args.source.read_text(encoding="utf-8")
    source_images = [
        (args.source.parent / p).resolve().with_suffix(".png")
        for p in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", source_text)
    ]
    if not source_images:
        raise SystemExit("No manuscript figure images found")

    with zipfile.ZipFile(args.input_docx, "r") as zin:
        relationships = etree.fromstring(zin.read("word/_rels/document.xml.rels"))
        rel_targets = {r.get("Id"): "word/" + r.get("Target") for r in relationships}
        document = etree.fromstring(zin.read("word/document.xml"))
        embeds = document.xpath("//*[local-name()='blip']/@*[local-name()='embed']")
        figure_targets = [rel_targets[e] for e in embeds if rel_targets[e].lower().endswith(".png")]
        if len(figure_targets) != len(source_images):
            raise SystemExit(
                f"Expected {len(source_images)} PNG figure embeds, found {len(figure_targets)}"
            )
        payloads = [(target, path.read_bytes()) for target, path in zip(figure_targets, source_images)]
        entries = [(item, zin.read(item.filename)) for item in zin.infolist()]

    replacement = {target: data for target, data in payloads}
    args.output_docx.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.output_docx, "w", compression=zipfile.ZIP_DEFLATED) as zout:
        for info, content in entries:
            zout.writestr(info, replacement.get(info.filename, content))

    figures = []
    for target, path, data in [(t, p, d) for (t, d), p in zip(payloads, source_images)]:
        meta = png_metadata(data)
        if meta["dpi_x"] is None or meta["dpi_y"] is None:
            raise SystemExit(f"Missing physical resolution metadata: {path}")
        figures.append({
            "package_media": target,
            "source": str(path),
            "sha256": hashlib.sha256(data).hexdigest(),
            **meta,
        })
    if any(min(f["dpi_x"], f["dpi_y"]) < 1199 for f in figures):
        raise SystemExit("At least one source figure is below 1200-DPI metadata")
    report = {
        "input_docx": str(args.input_docx),
        "output_docx": str(args.output_docx),
        "figure_count": len(figures),
        "restored_source_assets": True,
        "minimum_source_dpi": min(min(f["dpi_x"], f["dpi_y"]) for f in figures),
        "figures": figures,
    }
    encoded = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(encoded, encoding="utf-8")
    print(encoded, end="")


if __name__ == "__main__":
    main()
