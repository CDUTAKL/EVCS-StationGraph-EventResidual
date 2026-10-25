"""Read-only environment inventory; writes reports only to an explicit output path.

Run with the interpreter being inspected, using -B. Never installs packages,
invokes uv run/sync, or loads checkpoints. Historical freeze is a reference,
not proof of the environment immediately preceding an incident.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata as metadata
import json
import platform
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


def sha(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def canonical(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--historical-freeze", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    target = args.out.resolve()
    if target.is_relative_to(root / ".venv"):
        parser.error("report output must be outside .venv")
    if target.exists():
        parser.error("report already exists; choose a new path")
    packages = {}
    metadata_hashes = {}
    for dist in metadata.distributions():
        name = canonical(dist.metadata["Name"])
        packages[name] = dist.version
        for entry in dist.files or []:
            if str(entry).endswith((".dist-info/METADATA", ".dist-info/RECORD")):
                file = Path(dist.locate_file(entry))
                if file.is_file():
                    metadata_hashes[str(file)] = sha(file)
    historical = {}
    skipped = []
    for line in args.historical_freeze.read_text().splitlines():
        match = re.fullmatch(r"([A-Za-z0-9_.-]+)==([^\s]+)", line.strip())
        if match:
            historical[canonical(match[1])] = match[2]
        elif line.strip() and not line.startswith("WARNING:"):
            skipped.append(line)
    missing = {n: v for n, v in historical.items() if n not in packages}
    changed = {n: {"historical": v, "current": packages[n]}
               for n, v in historical.items() if n in packages and packages[n] != v}
    evidence = root / "docs/thesis/revision-20261022-evidence/reproducibility-package.json"
    verified = []
    if evidence.exists():
        references = {}

        def walk(value):
            if isinstance(value, dict):
                path = value.get("path")
                digest = value.get("sha256")
                if isinstance(path, str) and isinstance(digest, str) and re.fullmatch(r"[a-f0-9]{64}", digest):
                    references[path] = digest
                for item in value.values():
                    walk(item)
            elif isinstance(value, list):
                for item in value:
                    walk(item)

        walk(json.loads(evidence.read_text()))
        for rel, expected in references.items():
            path = (root / rel).resolve()
            if not path.is_relative_to(root):
                continue
            actual = sha(path) if path.is_file() else None
            verified.append({"path": rel, "expected_sha256": expected,
                             "actual_sha256": actual, "match": actual == expected})
    preserved = {}
    for rel in ["pyproject.toml", "requirements-server.txt", "cloud/jpl/requirements.txt",
                "cloud/eventtime/requirements.txt", ".venv/pyvenv.cfg",
                "docs/thesis/thesis-manuscript.md",
                "docs/thesis/revision-20261023-layout/thesis-layout-final-1200dpi.docx",
                "docs/thesis/revision-20261023-layout/thesis-layout-final-1200ppi.pdf"]:
        path = root / rel
        if path.is_file():
            preserved[rel] = sha(path)
    record = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version, "executable": sys.executable,
        "base_executable": getattr(sys, "_base_executable", None),
        "prefix": sys.prefix, "base_prefix": sys.base_prefix,
        "machine": platform.machine(), "sys_path": sys.path,
        "packages": dict(sorted(packages.items())),
        "metadata_hashes": metadata_hashes,
        "historical_reference": {"path": str(args.historical_freeze.resolve()),
                                 "sha256": sha(args.historical_freeze),
                                 "limitation": "Historical run snapshot, not incident-time full backup",
                                 "non_pinned_lines": skipped},
        "missing_from_historical": missing,
        "changed_from_historical": changed,
        "new_vs_historical": {n: v for n, v in packages.items() if n not in historical},
        "preserved_file_hashes": preserved,
        "archived_evidence_hash_checks": verified,
        "archive_hash_failures": [x for x in verified if not x["match"]],
        "mutations": "report only; no install, environment rebuild, training, or inference",
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"out": str(target), "packages": len(packages),
                      "missing": len(missing), "changed": len(changed),
                      "evidence_checked": len(verified),
                      "evidence_failed": len(record["archive_hash_failures"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
