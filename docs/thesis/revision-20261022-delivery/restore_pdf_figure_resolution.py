#!/usr/bin/env python3
"""Restore original DOCX raster figures into a WPS-rendered PDF without reflow.

WPS exports the thesis layout correctly but may downsample figures. This script
matches each PDF image XObject to the DOCX's ordered PNG figures, verifies the
mapping with normalized thumbnails, and replaces only image streams. Page text,
coordinates, and pagination remain those of the WPS-exported PDF.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import subprocess
import zipfile
from pathlib import Path

import fitz
import numpy as np
from lxml import etree
from PIL import Image

THUMB = 96


def thumbnail(image: Image.Image) -> np.ndarray:
    image = image.convert("RGB")
    image.thumbnail((THUMB, THUMB), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (THUMB, THUMB), "white")
    canvas.paste(image, ((THUMB - image.width) // 2, (THUMB - image.height) // 2))
    return np.asarray(canvas, dtype=np.int16)


def docx_figures(docx: Path) -> list[tuple[str, bytes, tuple[int, int]]]:
    ns_rel = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    with zipfile.ZipFile(docx) as package:
        if package.testzip() is not None:
            raise ValueError("DOCX package integrity check failed")
        document = etree.fromstring(package.read("word/document.xml"))
        rels_xml = etree.fromstring(package.read("word/_rels/document.xml.rels"))
        rels = {node.get("Id"): node.get("Target") for node in rels_xml}
        figures = []
        for blip in document.xpath('//*[local-name()="blip"]'):
            rid = blip.get(f"{{{ns_rel}}}embed")
            target = "word/" + rels[rid]
            if not target.lower().endswith(".png"):
                continue
            data = package.read(target)
            with Image.open(io.BytesIO(data)) as image:
                size = image.size
            figures.append((target, data, size))
    return figures


def pdf_xrefs(pdf: fitz.Document) -> list[tuple[int, int, int, int]]:
    found: list[tuple[int, int, int, int]] = []
    seen: set[int] = set()
    for page_index, page in enumerate(pdf):
        for item in page.get_images(full=True):
            xref, width, height = item[0], item[2], item[3]
            if xref not in seen:
                found.append((xref, page_index + 1, width, height))
                seen.add(xref)
    return found


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--docx", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--verify-only", action="store_true", help="verify an already-restored PDF without rewriting it")
    args = parser.parse_args()

    figures = docx_figures(args.docx)
    pdf = fitz.open(args.pdf)
    objects = pdf_xrefs(pdf)
    if len(figures) != 46 or len(objects) != len(figures):
        raise ValueError(f"Expected 46 source figures and matching PDF objects; got {len(figures)} and {len(objects)}")

    source_thumbs = [thumbnail(Image.open(io.BytesIO(data))) for _, data, _ in figures]
    mapping_rows = []
    for index, (xref, page, width, height) in enumerate(objects):
        embedded = pdf.extract_image(xref)
        pdf_thumb = thumbnail(Image.open(io.BytesIO(embedded["image"])))
        errors = [float(np.abs(pdf_thumb - source).mean()) for source in source_thumbs]
        best = int(np.argmin(errors))
        ordered_error = errors[index]
        margin = min(errors[j] for j in range(len(errors)) if j != index) - ordered_error
        if best != index or ordered_error > 3.0 or margin < 1.0:
            raise ValueError(
                f"Image mapping is ambiguous at object {index + 1}: best={best + 1}, "
                f"ordered MAE={ordered_error:.3f}, margin={margin:.3f}"
            )
        mapping_rows.append({
            "figure_index": index + 1,
            "pdf_page": page,
            "pdf_xref": xref,
            "pdf_before_pixels": [width, height],
            "source_docx_media": figures[index][0],
            "source_pixels": list(figures[index][2]),
            "thumbnail_mae": round(ordered_error, 4),
            "mapping_margin": round(margin, 4),
            "source_sha256": hashlib.sha256(figures[index][1]).hexdigest(),
        })

    # Replace only the image streams; keep WPS page geometry and pagination.
    if not args.verify_only:
        for (xref, page_number, _, _), (_, source_bytes, _) in zip(objects, figures, strict=True):
            pdf[page_number - 1].replace_image(xref, stream=source_bytes)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        pdf.save(args.output, garbage=4, deflate=True, clean=True)
    expected_pages = len(pdf)
    pdf.close()

    checked = fitz.open(args.output)
    final_objects = pdf_xrefs(checked)
    if len(checked) != expected_pages or len(final_objects) != 46:
        raise ValueError(f"Post-replacement structure mismatch: pages={len(checked)}, images={len(final_objects)}")
    image_list = subprocess.run(["pdfimages", "-list", str(args.output)], check=True, capture_output=True, text=True).stdout
    image_rows = []
    for line in image_list.splitlines():
        parts = line.split()
        if len(parts) >= 13 and parts[0].isdigit() and parts[1].isdigit() and parts[2] == "image":
            image_rows.append((int(parts[0]), int(parts[3]), int(parts[4]), float(parts[-4]), float(parts[-3])))
    if len(image_rows) != 46:
        raise ValueError(f"pdfimages reported {len(image_rows)} images, expected 46")
    final_ppi = [min(row[3], row[4]) for row in image_rows]
    if min(final_ppi) < 1200:
        raise ValueError(f"Resolution requirement failed: minimum effective ppi={min(final_ppi):.2f}")

    report = {
        "status": "PASS",
        "method": "WPS PDF page layout retained; matched original DOCX figure streams restored by XObject replacement",
        "input_pdf": str(args.pdf),
        "input_pdf_sha256": hashlib.sha256(args.pdf.read_bytes()).hexdigest(),
        "input_docx": str(args.docx),
        "input_docx_sha256": hashlib.sha256(args.docx.read_bytes()).hexdigest(),
        "output_pdf": str(args.output),
        "output_pdf_sha256": hashlib.sha256(args.output.read_bytes()).hexdigest(),
        "page_count": len(checked),
        "figure_count": len(final_ppi),
        "minimum_effective_ppi": round(min(final_ppi), 1),
        "maximum_effective_ppi": round(max(final_ppi), 1),
        "figure_mapping": mapping_rows,
    }
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "figure_mapping"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
