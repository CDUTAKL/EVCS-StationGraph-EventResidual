#!/usr/bin/env python3
"""Compare visible WPS PDF TOC page numbers with the rendered heading pages."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import unicodedata
from pathlib import Path


def norm(value: str) -> str:
    value = unicodedata.normalize("NFKC", value)
    return re.sub(r"\s+", "", value).casefold()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--toc-start", type=int, default=9)
    parser.add_argument("--toc-end", type=int, default=12)
    parser.add_argument("--body-start", type=int, default=13)
    args = parser.parse_args()
    text = subprocess.run(["pdftotext", "-layout", str(args.pdf), "-"], check=True, capture_output=True, text=True).stdout
    pages = text.split("\f")
    toc_entries = []
    entry_rx = re.compile(
        r"^\s*(第\s*\d+\s*章|\d+(?:\.\d+)*|结\s*论|参考文献|附录\s*[A-Z])\s*(.*?)\s*\.{2,}\s*(\d+)\s*$"
    )
    for physical_page in range(args.toc_start, args.toc_end + 1):
        for line in pages[physical_page - 1].splitlines():
            match = entry_rx.match(line)
            if not match:
                continue
            number, title, toc_page = match.groups()
            title = title.strip(" .\t")
            toc_entries.append({
                "locator": re.sub(r"\s+", "", number),
                "title": title,
                "toc_page": int(toc_page),
                "toc_pdf_page": physical_page,
            })

    body_pages = pages[args.body_start - 1:]
    results = []
    for item in toc_entries:
        needle = norm(item["locator"] + item["title"])
        matches = []
        # Top-level front/back matter labels such as "结论" and "参考文献"
        # have no suffix title; check the page implied by the TOC and verify the
        # label there instead of matching ordinary mentions elsewhere.
        if not item["title"]:
            expected_pdf_page = item["toc_page"] + args.body_start - 1
            candidates = [(expected_pdf_page, pages[expected_pdf_page - 1])]
        else:
            candidates = list(enumerate(body_pages, start=11))
        for offset, page_text in candidates:
            if needle and needle in norm(page_text):
                footer_match = re.search(r"(?:^|\n)\s*(\d+)\s*$", page_text.rstrip())
                footer = int(footer_match.group(1)) if footer_match else offset - args.body_start + 1
                matches.append({"pdf_page": offset, "printed_page": footer})
        actual = matches[0] if matches else None
        results.append({
            **item,
            "actual_heading_pages": matches,
            "first_heading_pdf_page": actual["pdf_page"] if actual else None,
            "first_heading_printed_page": actual["printed_page"] if actual else None,
            "match": bool(actual and actual["printed_page"] == item["toc_page"]),
        })

    mismatches = [r for r in results if not r["match"]]
    report = {
        "status": "PASS" if toc_entries and not mismatches else "REVIEW_REQUIRED",
        "pdf": str(args.pdf),
        "pdf_sha256": hashlib.sha256(args.pdf.read_bytes()).hexdigest(),
        "pdf_pages": len(pages) - (1 if pages and not pages[-1].strip() else 0),
        "toc_pdf_pages": list(range(args.toc_start, args.toc_end + 1)),
        "entries_checked": len(results),
        "matched_entries": len(results) - len(mismatches),
        "mismatches": mismatches,
        "entries": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "entries"}, ensure_ascii=False, indent=2))
    if report["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
