#!/usr/bin/env python3
"""Build a portable manifest without rewriting frozen source provenance.

Immutable origin fields come only from source-provenance.lock.json. Current
resolution locations are recorded separately as lookup_* fields. Missing or
mismatched sources fail before manifest.json is written.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import copy
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path

OUT = Path(__file__).resolve().parent
CONFIG_PATH = OUT / "config.json"
LOCK_PATH = OUT / "source-provenance.lock.json"
MANIFEST_PATH = OUT / "manifest.json"
CONFIG = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def project_root() -> Path:
    raw = os.environ.get("EVCS_PROJECT_ROOT", CONFIG.get("project_root", "."))
    path = Path(raw).expanduser()
    return path.resolve() if path.is_absolute() else (OUT / path).resolve()


def digest_file(path: Path) -> tuple[str, int]:
    h = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
            size += len(block)
    return h.hexdigest(), size


def digest_member(archive: Path, member: str) -> tuple[str, int]:
    h = hashlib.sha256()
    size = 0
    with tarfile.open(archive, "r:gz") as tf:
        stream = tf.extractfile(member)
        if stream is None:
            raise FileNotFoundError(f"archive member missing: {member}")
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
            size += len(block)
    return h.hexdigest(), size


def canonical_fields(record: dict) -> dict:
    return {
        "source_path": record.get("source_path"),
        "source_archive": record.get("source_archive"),
        "source_member": record.get("source_member"),
    }


def locate_origin(path_value: str | None, hint_value: str | None, root: Path) -> Path | None:
    if hint_value:
        return root / hint_value
    if path_value:
        path = Path(path_value).expanduser()
        return path if path.is_absolute() else root / path
    return None


def verify_input(record: dict, root: Path) -> dict:
    expected_sha = record["sha256"]
    expected_bytes = int(record["bytes"])
    local = OUT / record["package_path"]
    source_file = locate_origin(record.get("source_path"), record.get("lookup_path_hint"), root)
    source_archive = locate_origin(record.get("source_archive"), record.get("lookup_archive_hint"), root)

    # A present package copy is authoritative. Never hide a corrupt local copy
    # by falling back to another source location.
    if local.exists():
        found_sha, found_bytes = digest_file(local)
        if (found_sha, found_bytes) != (expected_sha, expected_bytes):
            raise ValueError(f"package input hash/size mismatch: {local}")
        return {
            "path": record["package_path"],
            **canonical_fields(record),
            "sha256": expected_sha,
            "bytes": expected_bytes,
            "lookup_path": str(local.absolute()),
            "lookup_root": "package",
        }

    if source_file is not None:
        if not source_file.is_file():
            raise FileNotFoundError(f"source input missing: {source_file}")
        found_sha, found_bytes = digest_file(source_file)
        if (found_sha, found_bytes) != (expected_sha, expected_bytes):
            raise ValueError(f"source input hash/size mismatch: {source_file}")
        return {
            "path": record["package_path"],
            **canonical_fields(record),
            "sha256": expected_sha,
            "bytes": expected_bytes,
            "lookup_path": str(source_file.resolve()),
            "lookup_root": str(root),
        }

    if source_archive is not None:
        if not source_archive.is_file():
            raise FileNotFoundError(f"source archive missing: {source_archive}")
        found_sha, found_bytes = digest_member(source_archive, record["source_member"])
        if (found_sha, found_bytes) != (expected_sha, expected_bytes):
            raise ValueError(
                f"source archive member hash/size mismatch: "
                f"{source_archive}::{record['source_member']}"
            )
        return {
            "path": record["package_path"],
            **canonical_fields(record),
            "sha256": expected_sha,
            "bytes": expected_bytes,
            "lookup_archive": str(source_archive.resolve()),
            "lookup_root": str(root),
        }

    raise ValueError(f"source record has no usable origin: {record['package_path']}")


def output_records() -> list[dict]:
    excluded = {"manifest.json", "source-provenance.lock.json"}
    outputs = []
    for path in sorted(OUT.rglob("*")):
        if not path.is_file() or path.name in excluded or "__pycache__" in path.parts:
            continue
        relative = path.relative_to(OUT).as_posix()
        sha, size = digest_file(path)
        outputs.append({"path": relative, "sha256": sha, "bytes": size})
    return outputs


def build_manifest(lock: dict | None = None, *, root: Path | None = None, lock_sha256: str | None = None) -> dict:
    if lock is None and not LOCK_PATH.is_file():
        raise FileNotFoundError(
            "source-provenance.lock.json is required; initialize provenance "
            "explicitly from an audited frozen manifest before rebuilding"
        )
    lock = lock or json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    root = root or project_root()
    inputs = [verify_input(item, root) for item in lock["inputs"]]
    scope = {
        "protocol": "Caltech event-time (SG-DATA-006-eventtime-v1)",
        "test_keys": 708560,
        "labels": ["uniform allocation", "completion-time-truncated allocation"],
        "training": "none; existing frozen predictions only",
        "network": "none",
        "raw_sessions_saved": False,
        "credentials_saved": False,
    }
    return {
        "schema_version": 2,
        "package": lock["package"],
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "analysis_command": (
            "EVCS_PROJECT_ROOT=<project-root> PYTHONDONTWRITEBYTECODE=1 "
            "python3 outputs/analysis/SG-ANA-20261026-proxy-stability/analyze.py"
        ),
        "environment": {"python": sys.version.split()[0], "platform": platform.platform()},
        "scope": scope,
        "source_provenance_lock_sha256": lock_sha256 or digest_file(LOCK_PATH)[0],
        "inputs": inputs,
        "outputs": output_records(),
        "provenance_policy": {
            "immutable_origin_fields": ["source_path", "source_archive", "source_member"],
            "current_resolution_fields": ["lookup_path", "lookup_archive", "lookup_root"],
            "missing_or_mismatched_input": "fail closed; do not write manifest",
        },
    }


def path_hint(path_value: str | None, root: Path) -> str | None:
    if not path_value:
        return None
    path = Path(path_value).expanduser()
    resolved = path.resolve() if path.is_absolute() else (root / path).resolve()
    try:
        return resolved.relative_to(root.resolve()).as_posix()
    except ValueError:
        return None


def package_path_from_frozen_item(raw_path: str) -> str:
    parts = Path(raw_path).parts
    try:
        index = parts.index("inputs")
    except ValueError as exc:
        raise ValueError(f"frozen input path has no inputs/ component: {raw_path}") from exc
    return Path(*parts[index:]).as_posix()


def reconcile_from_frozen_manifest(path: Path) -> int:
    """One-time, hash-bound correction from the externally frozen manifest.

    This is the only operation that may change origin fields. It first proves
    the exact frozen manifest hash, the current package inventory, and all
    source hashes. Ordinary rebuilds never call this path.
    """
    if not LOCK_PATH.is_file() or not MANIFEST_PATH.is_file():
        raise FileNotFoundError("existing provenance lock and manifest are required for reconciliation")
    old_lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    frozen_sha, _ = digest_file(path)
    if frozen_sha != old_lock.get("frozen_manifest_sha256"):
        raise ValueError("frozen manifest SHA-256 does not match the provenance lock")
    frozen = json.loads(path.read_text(encoding="utf-8"))
    frozen_by_path = {}
    for item in frozen.get("inputs", []):
        package_path = package_path_from_frozen_item(item["path"])
        if package_path in frozen_by_path:
            raise ValueError(f"duplicate frozen package input path: {package_path}")
        frozen_by_path[package_path] = item

    current_manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    current_by_path = {item["path"]: item for item in current_manifest.get("inputs", [])}
    old_by_path = {item["package_path"]: item for item in old_lock.get("inputs", [])}
    if set(frozen_by_path) != set(current_by_path) or set(frozen_by_path) != set(old_by_path):
        raise ValueError("frozen manifest, current manifest, and provenance lock input inventories differ")

    root = project_root()
    candidate = copy.deepcopy(old_lock)
    candidate_inputs = []
    for package_path in sorted(frozen_by_path):
        frozen_item = frozen_by_path[package_path]
        current_item = current_by_path[package_path]
        old_item = old_by_path[package_path]
        expected = (frozen_item["sha256"], int(frozen_item["bytes"]))
        for label, item in (("current manifest", current_item), ("old provenance lock", old_item)):
            observed = (item["sha256"], int(item["bytes"]))
            if observed != expected:
                raise ValueError(f"{label} content identity differs from frozen manifest: {package_path}")

        source_path = frozen_item.get("source_path")
        source_archive = frozen_item.get("source_archive")
        source_member = frozen_item.get("source_member")
        if not source_path and not source_archive:
            raise ValueError(f"frozen source location missing: {package_path}")
        if source_archive and not source_member:
            raise ValueError(f"frozen archive member missing: {package_path}")
        candidate_inputs.append({
            "package_path": package_path,
            "frozen_package_path": frozen_item["path"],
            "source_path": source_path,
            "source_archive": source_archive,
            "source_member": source_member,
            "lookup_path_hint": path_hint(source_path, root),
            "lookup_archive_hint": path_hint(source_archive, root),
            "sha256": expected[0],
            "bytes": expected[1],
        })
    candidate["source_of_truth"] = "Exact source_path/source_archive/source_member values copied from the SHA-256-verified frozen manifest."
    candidate["source_manifest_path"] = str(path.expanduser().resolve())
    candidate["inputs"] = candidate_inputs

    serialized_lock = json.dumps(candidate, ensure_ascii=False, indent=2) + "\n"
    lock_sha = hashlib.sha256(serialized_lock.encode("utf-8")).hexdigest()
    manifest = build_manifest(candidate, root=root, lock_sha256=lock_sha)
    serialized_manifest = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"

    lock_tmp = LOCK_PATH.with_suffix(".json.migration-tmp")
    manifest_tmp = MANIFEST_PATH.with_suffix(".json.migration-tmp")
    lock_tmp.write_text(serialized_lock, encoding="utf-8")
    manifest_tmp.write_text(serialized_manifest, encoding="utf-8")
    os.replace(lock_tmp, LOCK_PATH)
    os.replace(manifest_tmp, MANIFEST_PATH)
    print(f"reconciled {len(candidate_inputs)} origin records from hash-verified frozen manifest")
    return 0


def check_origin_immutability(current: dict, lock: dict) -> None:
    by_path = {item["path"]: item for item in current.get("inputs", [])}
    for record in lock["inputs"]:
        old = by_path.get(record["package_path"])
        if old is None:
            continue
        wanted = canonical_fields(record)
        observed = canonical_fields(old)
        if wanted != observed:
            raise ValueError(
                f"immutable source provenance drift for {record['package_path']}: "
                f"{observed!r} != {wanted!r}; refusing to overwrite manifest"
            )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="verify without writing")
    parser.add_argument(
        "--reconcile-from-frozen-manifest",
        type=Path,
        help="one-time correction of origin strings, allowed only from the exact SHA-256-locked frozen manifest",
    )
    args = parser.parse_args()
    try:
        if args.reconcile_from_frozen_manifest:
            return reconcile_from_frozen_manifest(args.reconcile_from_frozen_manifest)
        lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
        if MANIFEST_PATH.exists():
            current = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
            check_origin_immutability(current, lock)
        manifest = build_manifest()
    except (OSError, KeyError, ValueError, tarfile.TarError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.check:
        if not MANIFEST_PATH.is_file():
            print("ERROR: manifest.json is missing", file=sys.stderr)
            return 1
        current = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        for value in (manifest, current):
            value.pop("created_at_utc", None)
        if manifest != current:
            print("ERROR: manifest differs from locked sources or current outputs", file=sys.stderr)
            return 1
        print("manifest check passed")
        return 0

    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {MANIFEST_PATH} ({len(manifest['inputs'])} inputs, {len(manifest['outputs'])} outputs)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
