#!/usr/bin/env python3
"""Prepare the 46 manuscript PNG assets for 1200 dpi at their Word size.

Vector-backed plots below the target width are rasterized from the SVG.
ImageGen-only rasters are interpolated without changing labels or geometry;
the report distinguishes interpolated pixels from native source resolution.
The Word display width is read from its image extents, never guessed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import struct
import subprocess
import sys
import zlib
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import sync_formal_docx_figure_assets as docx_sync  # noqa: E402

FIG = ROOT / "outputs/figures"
STAGE = Path("/private/tmp/evcs-1200dpi-stage")
REPORT = ROOT / "docs/thesis/figure-1200dpi-20261007.json"
DPI = 1200
PNG_SIG = b"\x89PNG\r\n\x1a\n"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def dimensions(raw: bytes) -> tuple[int, int]:
    if raw[:8] != PNG_SIG or len(raw) < 24:
        raise ValueError("Not a PNG")
    return struct.unpack(">II", raw[16:24])


def add_dpi(raw: bytes, dpi: int = DPI) -> bytes:
    """Set PNG physical resolution metadata while retaining all image data."""
    ppm = round(dpi / 0.0254)
    chunk_data = struct.pack(">IIB", ppm, ppm, 1)
    chunk = struct.pack(">I", len(chunk_data)) + b"pHYs" + chunk_data
    chunk += struct.pack(">I", zlib.crc32(b"pHYs" + chunk_data) & 0xffffffff)
    chunks = []
    pos = 8
    while pos < len(raw):
        n = struct.unpack(">I", raw[pos:pos+4])[0]
        typ = raw[pos+4:pos+8]
        end = pos+12+n
        if typ != b"pHYs":
            chunks.append(raw[pos:end])
        pos = end
        if typ == b"IHDR":
            chunks.append(chunk)
    return PNG_SIG + b"".join(chunks)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--docx", type=Path, required=True)
    ap.add_argument("--apply", action="store_true", help="replace canonical PNG assets after staging checks")
    args = ap.parse_args()
    _, refs = docx_sync.read_image_refs(__import__("zipfile").ZipFile(args.docx))
    refs = refs[1:]  # first drawing is the cover mark
    manuscript, labels = docx_sync.source_figures(ROOT / "docs/thesis/thesis-manuscript.md")
    if len(refs) != len(manuscript) or len(refs) != 46:
        raise ValueError(f"Expected 46 manuscript figures; found {len(refs)} Word images and {len(manuscript)} Markdown images")
    STAGE.mkdir(parents=True, exist_ok=True)
    rows = []
    for index, (path, label, ref) in enumerate(zip(manuscript, labels, refs), start=1):
        original = path.read_bytes()
        w, h = dimensions(original)
        extent = ref["drawing"].xpath("./wp:extent", namespaces=docx_sync.NS)[0]
        width_cm = int(extent.get("cx")) / docx_sync.EMU_PER_CM
        target_w = math.ceil(width_cm / 2.54 * DPI)
        target_h = round(target_w * h / w)
        svg = path.with_suffix(".svg")
        method = "native pixels; added 1200 dpi metadata"
        native = [w, h]
        if w < target_w and svg.is_file():
            tmp = STAGE / f"{index:02d}-{path.stem}.render.png"
            subprocess.run(["rsvg-convert", "--width", str(target_w), "--height", str(target_h),
                            str(svg), "--output", str(tmp)], check=True)
            with Image.open(tmp) as im:
                if im.size != (target_w, target_h):
                    raise ValueError(f"Vector export size mismatch for {path.name}: {im.size} != {(target_w,target_h)}")
                im.load()
                output = im.convert("RGBA" if "A" in im.getbands() else "RGB")
                tmp.unlink()
            method = "rasterized from companion SVG at target dimensions"
        elif w < target_w:
            with Image.open(path) as im:
                im.load()
                output = im.resize((target_w, target_h), Image.Resampling.LANCZOS)
            method = "Lanczos interpolation from raster-only source; no new source detail"
        else:
            output = None

        staged = STAGE / f"{index:02d}-{path.name}"
        if output is not None:
            output.save(staged, format="PNG", dpi=(DPI, DPI), optimize=True)
            output.close()
            raw = staged.read_bytes()
        else:
            raw = add_dpi(original)
            staged.write_bytes(raw)
        outw, outh = dimensions(raw)
        actual_dpi = outw / width_cm * 2.54
        metadata = Image.open(staged).info.get("dpi")
        if outw < target_w or actual_dpi < DPI or not metadata or min(metadata) < DPI-0.1:
            raise ValueError(f"1200 dpi check failed for {path.name}: size={outw}x{outh}, effective={actual_dpi}, metadata={metadata}")
        rows.append({
            "figure": f"图{label[0]}-{label[1]}", "path": str(path.relative_to(ROOT)),
            "width_cm": width_cm, "source_size_px": native, "delivery_size_px": [outw, outh],
            "effective_dpi": actual_dpi, "metadata_dpi": list(metadata), "method": method,
            "source_sha256": sha(original), "delivery_sha256": sha(raw),
            "companion_svg": str(svg.relative_to(ROOT)) if svg.is_file() else None,
        })
        print(f"{index:02d}/46 {label[0]}-{label[1]}: {w}x{h} -> {outw}x{outh}, {actual_dpi:.1f} dpi ({method})")

    report = {
        "requested_dpi": DPI, "figure_count": len(rows), "all_minimum_effective_dpi_pass": min(x["effective_dpi"] for x in rows) >= DPI,
        "dpi_definition": "embedded pixel width / actual Word image width; PNG pHYs is set to 1200 dpi",
        "resampling_disclosure": "SVG sources are rerasterized; raster-only sources below target use Lanczos interpolation and do not gain native detail.",
        "figures": rows,
    }
    if not report["all_minimum_effective_dpi_pass"]:
        raise ValueError("At least one manuscript raster is below the required effective 1200 dpi")
    if args.apply:
        archive = FIG / "archive/2026-10-06-pre-1200dpi-originals"
        archive.mkdir(parents=True, exist_ok=True)
        for row in rows:
            p = ROOT / row["path"]
            previous = archive / p.name
            if not previous.exists():
                shutil.copy2(p, previous)
            shutil.copy2(STAGE / f"{rows.index(row)+1:02d}-{p.name}", p)
            sidecar = p.with_name(p.stem + "_source.json")
            if sidecar.is_file():
                try:
                    src = json.loads(sidecar.read_text())
                    src["pre_1200dpi_sha256"] = row["source_sha256"]
                    src["outputs"] = src.get("outputs", {})
                    if "png" in src["outputs"]:
                        src["outputs"]["png"] = row["delivery_sha256"]
                    src["delivery"] = {"size_px": row["delivery_size_px"], "metadata_dpi": row["metadata_dpi"],
                                        "effective_dpi_at_word_size": row["effective_dpi"], "method": row["method"]}
                    sidecar.write_text(json.dumps(src, ensure_ascii=False, indent=2) + "\n")
                except (json.JSONDecodeError, OSError):
                    pass
        report["applied"] = True
        report["archive"] = str(archive.relative_to(ROOT))
    else:
        report["applied"] = False
        print("Preview only. Re-run with --apply to replace canonical PNGs.")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k:v for k,v in report.items() if k != "figures"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
