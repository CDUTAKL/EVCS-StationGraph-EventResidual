"""Limit all backup names, deleting only bytes recoverable from a verified archive.

An over-limit unique backup without archive proof stops cleanup. It is never
discarded just because it is old or ignored by Git.
"""
from pathlib import Path
import argparse
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4*1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keep", type=int, default=3)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if args.keep < 1:
        parser.error("--keep must be positive")
    proof = {}
    for path in (ROOT/"outputs/archives").glob("thesis-cache-*/manifest.json"):
        receipt = path.parent/"remote-verification.json"
        if not receipt.is_file():
            continue
        m, remote = json.loads(path.read_text()), json.loads(receipt.read_text())
        pack = path.parent/"history.zip"
        if not remote.get("remote_download_verified") or remote.get("archive_sha256") != m["archive_sha256"]:
            continue
        if not pack.is_file() or sha(pack) != m["archive_sha256"]:
            continue
        for row in m["files"]:
            proof[(row["path"], row["sha256"])] = row["bytes"]
    candidates = []
    for ext in ["docx", "pdf"]:
        files = sorted((ROOT/".cache/thesis-delivery/backup").glob("*."+ext),
                       key=lambda p: (p.stat().st_mtime, p.name), reverse=True)
        for path in files[args.keep:]:
            digest = sha(path)
            rel = str(path.relative_to(ROOT))
            if proof.get((rel, digest)) != path.stat().st_size:
                print(f"Retain unarchived backup: {rel}", file=sys.stderr)
                return 2
            candidates.append((path, digest))
    for path, digest in candidates:
        print(path.resolve(), path.stat().st_size, digest, flush=True)
        if args.apply:
            assert sha(path) == digest
            path.unlink()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
