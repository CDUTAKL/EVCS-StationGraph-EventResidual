#!/usr/bin/env python3
"""Create and verify hash manifests for thesis review/release artifacts."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = 1


def run_git(*args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(ROOT), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def repo_path(value: str | Path) -> tuple[Path, str]:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    path = path.resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError(f"path must be inside the repository: {value}")
    return path, path.relative_to(ROOT).as_posix()


def porcelain_for(path: str) -> str:
    return run_git("status", "--porcelain=v1", "--", path)


def is_tracked(path: str) -> bool:
    result = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "--error-unmatch", "--", path],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def dirty_state(exclude: str | None = None) -> dict[str, Any]:
    lines = run_git("status", "--porcelain=v1", "--untracked-files=all").splitlines()
    if exclude:
        lines = [line for line in lines if line[3:] != exclude]
    canonical = "\n".join(lines)
    return {
        "clean": not lines,
        "path_count": len(lines),
        "paths_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
    }


def parse_artifact(spec: str) -> tuple[str, str]:
    if "=" not in spec:
        raise argparse.ArgumentTypeError("artifact must be ROLE=PATH")
    role, path = spec.split("=", 1)
    if not role.strip() or not path.strip():
        raise argparse.ArgumentTypeError("artifact must be ROLE=PATH")
    return role.strip(), path.strip()


def create_manifest(args: argparse.Namespace) -> dict[str, Any]:
    if not args.artifact:
        raise ValueError("provide at least one --artifact ROLE=PATH")
    output_path, output_rel = repo_path(args.output)
    if output_path.exists() and output_path.is_dir():
        raise ValueError(f"output is a directory: {output_rel}")

    artifacts = []
    seen_roles: set[str] = set()
    for role, raw_path in args.artifact:
        if role in seen_roles:
            raise ValueError(f"duplicate artifact role: {role}")
        seen_roles.add(role)
        path, rel = repo_path(raw_path)
        if not path.is_file():
            raise ValueError(f"artifact does not exist or is not a file: {rel}")
        artifacts.append({
            "role": role,
            "path": rel,
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
            "git_tracked": is_tracked(rel),
            "git_status": "clean" if is_tracked(rel) and not porcelain_for(rel) else (
                "modified" if is_tracked(rel) else "untracked"
            ),
        })

    state = dirty_state(exclude=output_rel)
    if args.status == "release":
        if not state["clean"]:
            raise ValueError(
                f"release requires a clean worktree (excluding this manifest); "
                f"found {state['path_count']} changed paths"
            )
        not_clean = [a["path"] for a in artifacts if not a["git_tracked"] or a["git_status"] != "clean"]
        if not_clean:
            raise ValueError("release artifacts must be committed and clean: " + ", ".join(not_clean))

    try:
        branch = run_git("symbolic-ref", "--short", "HEAD")
    except subprocess.CalledProcessError:
        branch = "DETACHED"
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "kind": "thesis-release-manifest",
        "release_id": args.version,
        "status": args.status,
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "repository": {
            "branch": branch,
            "source_commit": run_git("rev-parse", "HEAD"),
            "worktree_before_manifest": state,
        },
        "artifacts": artifacts,
        "notes": args.note or [],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp = output_path.with_name(output_path.name + ".tmp")
    temp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(output_path)
    return manifest


def verify_manifest(args: argparse.Namespace) -> dict[str, Any]:
    manifest_path, manifest_rel = repo_path(args.manifest)
    obj = json.loads(manifest_path.read_text(encoding="utf-8"))
    if obj.get("kind") != "thesis-release-manifest" or obj.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported or invalid thesis manifest")
    errors = []
    checked = 0
    for item in obj.get("artifacts", []):
        path, rel = repo_path(item["path"])
        if not path.is_file():
            errors.append(f"missing: {rel}")
            continue
        checked += 1
        if path.stat().st_size != item.get("bytes"):
            errors.append(f"size mismatch: {rel}")
        if sha256(path) != item.get("sha256"):
            errors.append(f"sha256 mismatch: {rel}")
    try:
        run_git("cat-file", "-e", obj["repository"]["source_commit"] + "^{commit}")
    except subprocess.CalledProcessError:
        errors.append("recorded source commit is absent from this repository")
    state = dirty_state()
    if args.require_clean and not state["clean"]:
        errors.append(f"worktree has {state['path_count']} changed paths")
    result = {
        "status": "PASS" if not errors else "FAIL",
        "manifest": manifest_rel,
        "release_id": obj.get("release_id"),
        "release_status": obj.get("status"),
        "artifacts_checked": checked,
        "current_worktree": state,
        "errors": errors,
    }
    if errors:
        raise ValueError(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def document_inventory(args: argparse.Namespace) -> dict[str, Any]:
    from thesis_artifact_inventory import inventory, write_reports

    project, output = args.project.resolve(), args.output.resolve()
    manifest = args.canonical_manifest
    if not manifest.is_absolute():
        manifest = project / manifest
    report = inventory(project, output, args.scope or ["docs/thesis", "outputs/thesis"],
                       manifest, args.remote_proof.resolve() if args.remote_proof else None)
    write_reports(report, output)
    return {"status": "READ_ONLY_DRY_RUN", "output": str(output), "summary": report["summary"]}


def resolve_lfs_artifact(args: argparse.Namespace) -> dict[str, Any]:
    """Resolve an immutable LFS object for read-only comparison, without a copy."""
    _, relative = repo_path(args.path)
    reference = args.ref
    if args.commit_map:
        mapping_path = Path(args.commit_map)
        if not mapping_path.is_absolute():
            mapping_path = ROOT / mapping_path
        matches = [line.split(",", 1)[1] for line in mapping_path.read_text().splitlines()
                   if line.split(",", 1)[0].startswith(reference)]
        if len(matches) > 1:
            raise ValueError("ambiguous original commit prefix")
        if matches:
            reference = matches[0]
    entry = run_git("ls-tree", "-z", reference, "--", relative)
    if not entry:
        raise ValueError("artifact is absent from the requested commit")
    blob = entry.split("\t", 1)[0].split()[2]
    if int(run_git("cat-file", "-s", blob)) > 1024:
        raise ValueError("artifact is not an LFS pointer; no binary copy was created")
    pointer = dict(line.split(" ", 1) for line in run_git("cat-file", "blob", blob).splitlines())
    if pointer.get("version") != "https://git-lfs.github.com/spec/v1":
        raise ValueError("unsupported artifact pointer")
    oid = pointer.get("oid", "").removeprefix("sha256:")
    if len(oid) != 64 or any(char not in "0123456789abcdef" for char in oid):
        raise ValueError("invalid LFS content identity")
    env = run_git("lfs", "env")
    media = next((line.split("=", 1)[1] for line in env.splitlines()
                  if line.startswith("LocalMediaDir=")), None)
    if not media:
        raise ValueError("LFS local media directory is unavailable")
    path = Path(media) / oid[:2] / oid[2:4] / oid
    size = int(pointer["size"])
    if not path.is_file() or path.stat().st_size != size or sha256(path) != oid:
        raise ValueError("local LFS object is missing or corrupt; no fallback copy/download performed")
    return {"status": "PASS", "requested_ref": args.ref, "resolved_ref": reference,
            "artifact": relative, "sha256": oid, "bytes": size,
            "read_only_object_path": str(path), "new_document_copies": 0,
            "use": "Read only. Editing this content-addressed object would corrupt the LFS cache."}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create", help="write a candidate or clean release manifest")
    create.add_argument("--version", required=True, help="stable release/candidate ID")
    create.add_argument("--status", choices=("candidate", "release"), default="candidate")
    create.add_argument("--artifact", action="append", type=parse_artifact, metavar="ROLE=PATH", required=True)
    create.add_argument("--output", required=True, help="manifest path inside repository")
    create.add_argument("--note", action="append", default=[])
    verify = sub.add_parser("verify", help="recompute artifact hashes")
    verify.add_argument("manifest", help="manifest path inside repository")
    verify.add_argument("--require-clean", action="store_true", help="also require clean worktree")
    inventory = sub.add_parser("inventory", help="read-only Word/PDF and LFS inventory; never delete")
    inventory.add_argument("--project", type=Path, default=ROOT)
    inventory.add_argument("--output", type=Path, required=True)
    inventory.add_argument("--scope", action="append")
    inventory.add_argument("--canonical-manifest", type=Path,
                           default=Path("docs/thesis/git-lfs-migration-20261026/final-artifacts.json"))
    inventory.add_argument("--remote-proof", type=Path)
    inventory.add_argument("--dry-run", action="store_true")
    resolve = sub.add_parser("resolve", help="verify and locate an LFS artifact without copying it")
    resolve.add_argument("path")
    resolve.add_argument("--ref", default="HEAD")
    resolve.add_argument("--commit-map", help="explicit old/new commit CSV; preserve the requested source ID")
    args = parser.parse_args()
    try:
        commands = {"create": create_manifest, "verify": verify_manifest,
                    "inventory": document_inventory, "resolve": resolve_lfs_artifact}
        result = commands[args.command](args)
    except (ValueError, OSError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
