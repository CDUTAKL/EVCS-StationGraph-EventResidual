"""Lossless content-addressed archive for reviewed historical thesis cache files.

DOCX members are stored as their original compressed byte payloads, not decoded
and re-encoded OOXML. Ordered pieces preserve every original byte, including ZIP
headers and directory records. Other files use content-anchored chunks.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import mmap
import re
import struct
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for piece in iter(lambda: stream.read(4*1024*1024), b""):
            h.update(piece)
    return h.hexdigest()


def spans(path):
    size = path.stat().st_size
    if path.suffix.lower() == ".docx":
        end = 0
        with ZipFile(path) as z, path.open("rb") as stream:
            for item in sorted(z.infolist(), key=lambda item: item.header_offset):
                stream.seek(item.header_offset)
                header = stream.read(30)
                assert header[:4] == b"PK\x03\x04"
                fn, extra = struct.unpack_from("<HH", header, 26)
                start = item.header_offset + 30 + fn + extra
                if start > end:
                    yield end, start
                end = start + item.compress_size
                if end > start:
                    yield start, end
        if end < size:
            yield end, size
    elif size:
        with path.open("rb") as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as data:
            start = 0
            for hit in re.finditer(b"\x17\x8b[\x00-\x1f]", data):
                cut = hit.start()
                while cut-start > 4*1024*1024:
                    yield start, start+4*1024*1024
                    start += 4*1024*1024
                if cut-start >= 128*1024:
                    yield start, cut
                    start = cut
            while size-start > 4*1024*1024:
                yield start, start+4*1024*1024
                start += 4*1024*1024
            if start < size:
                yield start, size


def create(selection, archive_dir):
    archive_dir.mkdir(parents=True, exist_ok=True)
    target = archive_dir/"history.zip"
    if target.exists():
        raise RuntimeError("Refusing to overwrite an existing archive")
    selected = json.loads(selection.read_text())
    seen = set()
    manifest = {"schema": 1, "purpose": "lossless historical cache; not an official thesis publication", "files": []}
    with ZipFile(target, "x", compression=ZIP_DEFLATED, compresslevel=1, allowZip64=True) as pack:
        for row in selected:
            path = ROOT/row["path"]
            if sha(path) != row["sha256"]:
                raise RuntimeError(f"Input changed: {path}")
            record = dict(row)
            record["pieces"] = []
            record["mode"] = path.stat().st_mode & 0o777
            with path.open("rb") as stream:
                for start, end in spans(path):
                    stream.seek(start)
                    piece = stream.read(end-start)
                    assert len(piece) == end-start
                    digest = hashlib.sha256(piece).hexdigest()
                    if digest not in seen:
                        pack.writestr("objects/"+digest, piece)
                        seen.add(digest)
                    record["pieces"].append({"sha256": digest, "bytes": len(piece)})
            manifest["files"].append(record)
            print("archived", row["path"], flush=True)
    manifest["archive_sha256"] = sha(target)
    manifest["archive_bytes"] = target.stat().st_size
    manifest["input_bytes"] = sum(row["bytes"] for row in selected)
    manifest["unique_pieces"] = len(seen)
    (archive_dir/"manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+"\n")
    verify(archive_dir)


def verify(archive_dir, restore_root=None):
    manifest = json.loads((archive_dir/"manifest.json").read_text())
    archive = archive_dir/"history.zip"
    assert sha(archive) == manifest["archive_sha256"]
    with ZipFile(archive) as pack:
        for row in manifest["files"]:
            h, size = hashlib.sha256(), 0
            dest = None
            if restore_root is not None:
                relative = Path(row["path"])
                if relative.is_absolute() or ".." in relative.parts:
                    raise ValueError("Unsafe restore path")
                path = restore_root/relative
                if path.exists():
                    raise RuntimeError(f"Refusing to replace {path}")
                path.parent.mkdir(parents=True, exist_ok=True)
                dest = path.open("xb")
            try:
                for piece in row["pieces"]:
                    raw = pack.read("objects/"+piece["sha256"])
                    assert len(raw) == piece["bytes"] and hashlib.sha256(raw).hexdigest() == piece["sha256"]
                    h.update(raw)
                    size += len(raw)
                    if dest:
                        dest.write(raw)
            finally:
                if dest:
                    dest.close()
            assert size == row["bytes"] and h.hexdigest() == row["sha256"], row["path"]
    print("Verified all", len(manifest["files"]), "original file byte hashes.", flush=True)
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["create", "verify", "restore"])
    parser.add_argument("--archive-dir", type=Path, required=True)
    parser.add_argument("--selection", type=Path)
    parser.add_argument("--restore-root", type=Path)
    args = parser.parse_args()
    if args.mode == "create":
        if args.selection is None:
            parser.error("--selection required")
        create(args.selection, args.archive_dir)
    else:
        if args.mode == "restore" and args.restore_root is None:
            parser.error("--restore-root required")
        verify(args.archive_dir, args.restore_root if args.mode == "restore" else None)
