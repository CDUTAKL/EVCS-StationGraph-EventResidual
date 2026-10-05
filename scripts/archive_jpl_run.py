#!/usr/bin/env python3
"""Create a checksum-indexed archive of one SG-EXP-028 run; no shutdown side effects."""
import argparse
import hashlib
import json
from pathlib import Path
import tarfile
from datetime import datetime, timezone


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--run-log", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    run_log = args.run_log.resolve()
    results = (root / "results").resolve()
    run_log.relative_to(root)
    results.relative_to(root)
    archive_dir = root / "archives"
    archive_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archive = archive_dir / f"SG-EXP-028-{stamp}.tar.gz"
    provenance_roots = [root / "BUNDLE_MANIFEST.json", root / "BUNDLE_PROVENANCE.json",
                        root / "cloud/jpl", root / "configs", root / "data/jpl",
                        root / "metadata", root / "scripts/jpl_experiment.py",
                        root / "scripts/archive_jpl_run.py", root / "src"]
    provenance_files = []
    for item in provenance_roots:
        if item.is_file() and not item.is_symlink():
            provenance_files.append(item)
        elif item.is_dir():
            provenance_files.extend(p for p in item.rglob("*") if p.is_file() and not p.is_symlink())
    files = sorted(set([p for p in results.rglob("*") if p.is_file() and not p.is_symlink()] +
                       [p for p in run_log.rglob("*") if p.is_file() and not p.is_symlink()] +
                       provenance_files))
    if archive.exists():
        raise FileExistsError(archive)
    with tarfile.open(archive, "w:gz", compresslevel=1) as tar:
        for path in files:
            tar.add(path, arcname=str(path.relative_to(root)), recursive=False)
    value = {"experiment": "SG-EXP-028", "archive": archive.name,
             "sha256": digest(archive), "files": len(files),
             "results_dir": str(results), "created_utc": stamp}
    index = archive.with_suffix(".summary.json")
    index.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    archive.with_suffix(".sha256").write_text(f"{value['sha256']}  {archive.name}\n", encoding="utf-8")
    print(json.dumps(value, indent=2))


if __name__ == "__main__":
    main()
