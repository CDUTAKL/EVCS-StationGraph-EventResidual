#!/usr/bin/env python3
"""Read-only Word/PDF inventory and conservative duplicate-cleanup proposals.

The script writes small reports only. It never deletes, moves, copies or opens
document artifacts, and does not run LFS prune or modify Git configuration.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
from zoneinfo import ZoneInfo


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git(root: Path, *args: str) -> bytes:
    return subprocess.check_output(["git", *args], cwd=root)


def paths(raw: bytes) -> set[str]:
    return {part.decode("utf-8") for part in raw.split(b"\0") if part}


def atomic_json(path: Path, value: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    os.replace(temporary, path)


def inventory(root: Path, output: Path, scopes: list[str], canonical_manifest: Path,
              remote_proof: Path | None = None) -> dict:
    canonical = {item["path"]: item for item in json.loads(canonical_manifest.read_text())}
    tracked = paths(git(root, "ls-files", "-z"))
    changed = paths(git(root, "diff", "HEAD", "--name-only", "-z"))
    lfs = json.loads(git(root, "lfs", "ls-files", "--all", "--json"))["files"]
    head_lfs = json.loads(git(root, "lfs", "ls-files", "--json"))["files"]
    head_oids = {item["oid"] for item in head_lfs}
    proof_path = remote_proof or root / "docs/thesis/git-lfs-migration-20261026/remote-verification.json"
    proof = json.loads(proof_path.read_text()) if proof_path.is_file() else {}
    proved = {item["sha256"] for item in proof.get("files", [])
              if item.get("remote_fresh_download_verified") is True}
    references = []
    for folder in (root / "docs/thesis", root / "scripts"):
        for file in folder.rglob("*"):
            if (not file.is_file() or file.suffix not in {".md", ".json", ".py"}
                    or file.resolve().is_relative_to(output.resolve())):
                continue
            references.append((file.relative_to(root).as_posix(),
                               file.read_text(encoding="utf-8", errors="replace")))
    files = []
    seen = set()
    for scope in scopes:
        folder = (root / scope).resolve()
        if not folder.is_relative_to(root) or any(part in {".git", ".venv"} for part in Path(scope).parts):
            raise ValueError(f"scope outside document boundary: {scope}")
        for file in sorted(folder.rglob("*")):
            if not file.is_file() or file.suffix.lower() not in {".docx", ".pdf"}:
                continue
            if not file.resolve().is_relative_to(root):
                raise ValueError(f"external document symlink requires separate review: {file}")
            name = file.relative_to(root).as_posix()
            if name in seen:
                continue
            seen.add(name)
            stat = file.stat()
            digest = sha256(file)
            refs = [path for path, text in references if name in text or file.name in text]
            role = ("canonical" if name in canonical else "tracked_archive" if name in tracked
                    else "local_candidate_or_archive")
            item = {"path": name, "sha256": digest, "bytes": stat.st_size,
                    "mtime_ns": stat.st_mtime_ns, "role": role,
                    "git_tracked": name in tracked, "git_clean": name in tracked and name not in changed,
                    "lfs_oids": sorted({x["oid"] for x in lfs if x["oid"] == digest}),
                    "reference_hints": refs, "reference_hint_requires_human_resolution": bool(refs),
                    "source_task": "20261026-finalization" if name in canonical or "candidate-final-20261026" in file.name else None,
                    "proposed_action": "retain"}
            if role == "canonical":
                expected = canonical[name]
                item["canonical_hash_matches"] = (digest == expected["sha256"] and stat.st_size == expected["bytes"])
                if not item["canonical_hash_matches"]:
                    raise ValueError(f"canonical artifact differs from accepted manifest: {name}")
            files.append(item)
    groups = defaultdict(list)
    for item in files:
        groups[(item["sha256"], item["bytes"])].append(item)
    duplicates = []
    for (digest, size), members in groups.items():
        if len(members) < 2:
            continue
        keepers = [item for item in members if item["role"] == "canonical" or item["git_clean"]]
        keeper = min(keepers, key=lambda item: (item["role"] != "canonical", item["path"])) if keepers else None
        for item in members:
            if item["role"] != "local_candidate_or_archive" or keeper is None:
                continue
            item["duplicate_of"] = keeper["path"]
            item["proposed_action"] = ("review_referenced_duplicate" if item["reference_hints"]
                                       else "eligible_unreferenced_git_backed_duplicate")
        duplicates.append({"sha256": digest, "bytes_each": size,
                           "paths": [item["path"] for item in members],
                           "git_backed_keeper": keeper["path"] if keeper else None})
    objects = {}
    for item in lfs:
        oid = item["oid"]
        record = objects.setdefault(oid, {"oid_sha256": oid, "bytes": item["size"],
                                        "paths_in_history": [], "in_head": oid in head_oids,
                                        "local_object_present": item["downloaded"],
                                        "fresh_remote_download_verified": oid in proved})
        if item["name"] not in record["paths_in_history"]:
            record["paths_in_history"].append(item["name"])
    eligible = [item for item in files if item["proposed_action"] == "eligible_unreferenced_git_backed_duplicate"]
    return {"schema_version": 1, "mode": "read_only_dry_run", "project": str(root),
            "generated_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
            "head": git(root, "rev-parse", "HEAD").decode().strip(),
            "canonical_manifest": {"path": str(canonical_manifest), "sha256": sha256(canonical_manifest)},
            "remote_proof": {"path": str(proof_path), "sha256": sha256(proof_path)} if proof_path.is_file() else None,
            "scopes": scopes, "uncommitted_tracked_paths": sorted(changed),
            "summary": {"file_count": len(files), "logical_bytes": sum(item["bytes"] for item in files),
                        "roles": dict(Counter(item["role"] for item in files)),
                        "duplicate_content_groups": len(duplicates),
                        "eligible_duplicate_count": len(eligible),
                        "eligible_duplicate_logical_bytes": sum(item["bytes"] for item in eligible),
                        "lfs_unique_object_count": len(objects)},
            "files": files, "duplicate_groups": duplicates, "lfs_objects": list(objects.values()),
            "limits": ["Reference hints are conservative text matches, not a deletion authorization.",
                       "Logical byte sums do not measure APFS physical space reclaim.",
                       "No unique document or audit-linked artifact is automatically deleted.",
                       "Historical LFS objects without a fresh download are not marked remotely revalidated."]}


def write_reports(report: dict, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    atomic_json(output / "inventory.json", report)
    s = report["summary"]
    (output / "README.md").write_text(
        "# Word/PDF版本与LFS清单\n\n"
        f"只读扫描{', '.join(report['scopes'])}；共{s['file_count']}份Word/PDF，"
        f"逻辑大小{s['logical_bytes']/1024**3:.3f} GiB。正式入口{ s['roles'].get('canonical',0) }份，"
        f"历史LFS唯一对象{s['lfs_unique_object_count']}个。详见inventory.json。\n\n"
        f"发现{s['duplicate_content_groups']}组相同内容；其中{s['eligible_duplicate_count']}份"
        f"未引用且有Git内同内容保留者，逻辑大小{s['eligible_duplicate_logical_bytes']/1024**3:.3f} GiB。"
        "这只是清理提案，本入口不删除任何文件。审计引用、唯一内容、实际磁盘占用和恢复性需另行核对。\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--scope", action="append")
    parser.add_argument("--canonical-manifest", type=Path,
                        default=Path("docs/thesis/git-lfs-migration-20261026/final-artifacts.json"))
    parser.add_argument("--remote-proof", type=Path)
    parser.add_argument("--dry-run", action="store_true", help="Explicit acknowledgement; this tool is always read-only")
    args = parser.parse_args()
    root, output = args.project.resolve(), args.output.resolve()
    manifest = args.canonical_manifest if args.canonical_manifest.is_absolute() else root / args.canonical_manifest
    proof = args.remote_proof.resolve() if args.remote_proof else None
    report = inventory(root, output, args.scope or ["docs/thesis", "outputs/thesis"], manifest, proof)
    write_reports(report, output)
    print(json.dumps(report["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main()
