#!/usr/bin/env python3
"""Render every page of the current thesis PDF and make review contact sheets."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import fitz
import numpy as np
from PIL import Image, ImageDraw, ImageFont

RENDER_DPI = 120
TILE_WIDTH = 500
TILE_LABEL_HEIGHT = 30
PAGES_PER_SHEET = 4


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    sheets_dir = args.output_dir / "contact-sheets"
    sheets_dir.mkdir(exist_ok=True)

    doc = fitz.open(args.pdf)
    if len(doc) != 104:
        raise ValueError(f"Expected 104 pages, found {len(doc)}")
    scale = RENDER_DPI / 72
    pages: list[Image.Image] = []
    page_records = []
    for index, page in enumerate(doc):
        pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
        image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        page_hash = hashlib.sha256(pix.tobytes("png")).hexdigest()
        gray = np.asarray(image.convert("L"))
        occupancy = float(np.count_nonzero(gray < 248) / gray.size)
        words = page.get_text("words")
        text = page.get_text("text")
        preview = image.copy()
        draw = ImageDraw.Draw(preview)
        redacted = 0
        # Cover long digit strings on the preview only. The source PDF is untouched.
        for word in words:
            if re.search(r"\d{6,}", str(word[4])):
                x0, y0, x1, y1 = word[:4]
                pad = 3
                draw.rectangle(
                    (max(0, int((x0 - pad) * scale)), max(0, int((y0 - pad) * scale)),
                     min(pix.width, int((x1 + pad) * scale)), min(pix.height, int((y1 + pad) * scale))),
                    fill="white",
                )
                redacted += 1
        thumb_h = round(preview.height * TILE_WIDTH / preview.width)
        preview = preview.resize((TILE_WIDTH, thumb_h), Image.Resampling.LANCZOS)
        pages.append(preview)
        page_records.append({
            "pdf_page": index + 1,
            "render_dpi": RENDER_DPI,
            "rendered_pixels": [pix.width, pix.height],
            "page_image_sha256": page_hash,
            "extracted_text_characters": len(text.strip()),
            "nonwhite_pixel_fraction": round(occupancy, 6),
            "blank_page_candidate": len(text.strip()) == 0 and occupancy < 0.005,
            "preview_redacted_long_digit_tokens": redacted,
            "manual_visual_status": "pending",
            "notes": "",
        })

    tile_h = pages[0].height + TILE_LABEL_HEIGHT
    for start in range(0, len(pages), PAGES_PER_SHEET):
        group = pages[start : start + PAGES_PER_SHEET]
        sheet = Image.new("RGB", (TILE_WIDTH * 2, tile_h * 2), "#e9edf2")
        draw = ImageDraw.Draw(sheet)
        for offset, tile in enumerate(group):
            x = (offset % 2) * TILE_WIDTH
            y = (offset // 2) * tile_h
            draw.rectangle((x, y, x + TILE_WIDTH - 1, y + TILE_LABEL_HEIGHT - 1), fill="#dbe3ec")
            draw.text((x + 12, y + 7), f"PDF page {start + offset + 1}", fill="#243447")
            sheet.paste(tile, (x, y + TILE_LABEL_HEIGHT))
        first, last = start + 1, start + len(group)
        sheet.save(sheets_dir / f"pages-{first:03d}-{last:03d}.jpg", quality=92, optimize=True)

    report = {
        "pdf": str(args.pdf),
        "pdf_sha256": hashlib.sha256(args.pdf.read_bytes()).hexdigest(),
        "page_count": len(doc),
        "render_dpi": RENDER_DPI,
        "generated_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds"),
        "blank_page_candidates": [r["pdf_page"] for r in page_records if r["blank_page_candidate"]],
        "pages": page_records,
        "contact_sheets": [str(p.relative_to(args.output_dir)) for p in sorted(sheets_dir.glob("*.jpg"))],
        "manual_review_complete": False,
    }
    (args.output_dir / "visual-qa.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "manual-review.json").write_text(json.dumps({
        "pdf_sha256": report["pdf_sha256"],
        "reviewer": "Codex",
        "review_started_at": report["generated_at"],
        "render_dpi": RENDER_DPI,
        "all_pages": page_records,
        "review_complete": False,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "pdf_sha256": report["pdf_sha256"],
        "pages": len(doc),
        "render_dpi": RENDER_DPI,
        "contact_sheets": len(report["contact_sheets"]),
        "blank_page_candidates": report["blank_page_candidates"],
        "min_nonwhite_fraction": min(r["nonwhite_pixel_fraction"] for r in page_records),
        "max_nonwhite_fraction": max(r["nonwhite_pixel_fraction"] for r in page_records),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
