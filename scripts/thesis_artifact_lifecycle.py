#!/usr/bin/env python3
"""Inventory thesis candidate files and require a hash-bound explicit cleanup plan.

This tool never treats an untracked file as junk. Inventory and plan are read-only.
Deletion is limited to manually approved exact duplicates inside outputs/thesis/candidate-*.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import stat
import sys
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
THESIS_ROOT = (ROOT / "outputs" / "thesis").resolve()
CANONICAL = {
    "manuscript": "docs/thesis/thesis-manuscript.md",
    "docx": "outputs/thesis/基于站内多关系图与机制诊断的充电节点短期负荷预测研究_正式论文.docx",
    "pdf": "outputs/thesis/基于站内多关系图与机制诊断的充电节点短期负荷预测研究_正式论文.pdf",
}
TEXT_SUFFIXES = {".md", ".txt", ".json", ".py", ".sh", ".csv", ".tsv", ".yaml", ".yml", ".toml", ".ini"}
MAX_TEXT_BYTES = 3 * 1024 * 1024
EXCLUDED_PARTS = {".git", ".venv", "data", "analysis", "__pycache__", "node_modules"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def build_reference_matcher(tokens: dict[str, list[tuple[str, str]]]):
    """Build a compact multi-pattern matcher so repository scanning is linear in text size."""
    transitions: list[dict[str, int]] = [{}]
    outputs: list[list[str]] = [[]]
    for token in tokens:
        state = 0
        for char in token:
            next_state = transitions[state].get(char)
            if next_state is None:
                next_state = len(transitions)
                transitions[state][char] = next_state
                transitions.append({})
                outputs.append([])
            state = next_state
        outputs[state].append(token)

    failures = [0] * len(transitions)
    queue = deque()
    for state in transitions[0].values():
        queue.append(state)
    while queue:
        state = queue.popleft()
        for char, next_state in transitions[state].items():
            queue.append(next_state)
            fallback = failures[state]
            while fallback and char not in transitions[fallback]:
                fallback = failures[fallback]
            failures[next_state] = transitions[fallback].get(char, 0)
            outputs[next_state].extend(outputs[failures[next_state]])
    return transitions, failures, outputs


def find_reference_tokens(line: str, matcher):
    transitions, failures, outputs = matcher
    state = 0
    for char in line:
        while state and char not in transitions[state]:
            state = failures[state]
        state = transitions[state].get(char, 0)
        for token in outputs[state]:
            yield token


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def validate_candidate_root(raw: str) -> Path:
    path = Path(raw)
    if not path.is_absolute():
        path = ROOT / path
    resolved = path.resolve(strict=True)
    try:
        rel = resolved.relative_to(THESIS_ROOT)
    except ValueError as exc:
        raise ValueError("根目录必须位于 outputs/thesis/candidate-* 内") from exc
    if not rel.parts or not rel.parts[0].startswith("candidate-"):
        raise ValueError("只允许扫描 outputs/thesis/candidate-* 工作目录")
    if not resolved.is_dir() or resolved == THESIS_ROOT:
        raise ValueError("候选根目录必须是存在的子目录")
    return resolved


def candidate_files(root: Path) -> list[Path]:
    files = []
    for path in sorted(root.rglob("*")):
        if any(part in EXCLUDED_PARTS for part in path.relative_to(root).parts):
            continue
        try:
            info = path.lstat()
        except OSError:
            continue
        if stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode):
            files.append(path)
    return files


def reference_sources() -> list[Path]:
    paths: list[Path] = []
    roots = [ROOT / "docs", ROOT / "scripts", THESIS_ROOT]
    top_files = [ROOT / "AGENTS.md", ROOT / "README.md", ROOT / ".gitignore"]
    for top in top_files:
        if top.is_file():
            paths.append(top)
    for directory in roots:
        if not directory.is_dir():
            continue
        for path in directory.rglob("*"):
            try:
                relative = path.relative_to(ROOT)
            except ValueError:
                continue
            if any(part in EXCLUDED_PARTS for part in relative.parts):
                continue
            if not path.is_symlink() and path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
                paths.append(path)
    return sorted(set(paths))


def scan_references(files: list[Path], candidate_root: Path) -> tuple[
    dict[str, list[dict[str, Any]]], dict[str, list[str]], list[dict[str, Any]], list[str]
]:
    """Find exact relative paths, unique basenames, and SHA-256 references in text records."""
    basename_count: dict[str, int] = defaultdict(int)
    for path in files:
        basename_count[path.name] += 1
    tokens: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for path in files:
        relative_parts = path.relative_to(candidate_root).parts
        key = Path(*relative_parts).as_posix()
        tokens[key].append((key, "candidate_relative_path"))
        for offset in range(1, len(relative_parts)):
            suffix = Path(*relative_parts[offset:]).as_posix()
            tokens[suffix].append((key, "candidate_relative_path_suffix"))
        repo_rel = path.relative_to(ROOT).as_posix()
        tokens[repo_rel].append((key, "repository_relative_path"))
        tokens[path.resolve().as_posix()].append((key, "absolute_path"))
        try:
            home_rel = path.resolve().relative_to(Path.home().resolve()).as_posix()
        except ValueError:
            pass
        else:
            tokens["~/" + home_rel].append((key, "home_relative_path"))
        if basename_count[path.name] == 1:
            tokens[path.name].append((key, "unique_filename"))
    hashes: dict[str, list[str]] = defaultdict(list)
    for path in files:
        if not path.is_symlink():
            try:
                hashes[sha256(path)].append(path.relative_to(candidate_root).as_posix())
            except OSError:
                pass
    for digest, members in hashes.items():
        for key in members:
            tokens[digest].append((key, "sha256"))

    refs: dict[str, dict[tuple[str, str], set[str]]] = defaultdict(lambda: defaultdict(set))
    matcher = build_reference_matcher(tokens)
    source_manifest = []
    unstable_sources = []
    for source in reference_sources():
        try:
            before = source.stat()
            if before.st_size > MAX_TEXT_BYTES:
                continue
            raw = source.read_bytes()
            after = source.stat()
            record = {
                "path": source.relative_to(ROOT).as_posix(),
                "bytes": len(raw),
                "mtime_ns": after.st_mtime_ns,
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
            if before.st_size != after.st_size or before.st_mtime_ns != after.st_mtime_ns or before.st_size != len(raw):
                unstable_sources.append(record["path"])
            source_manifest.append(record)
            text = raw.decode("utf-8")
        except (OSError, UnicodeError):
            continue
        source_rel = source.relative_to(ROOT).as_posix()
        for line_no, line in enumerate(text.splitlines(), 1):
            for token in find_reference_tokens(line, matcher):
                for target, kind in tokens[token]:
                    refs[target][(source_rel, kind)].add(str(line_no))

    rendered: dict[str, list[dict[str, Any]]] = {}
    for target, hits in refs.items():
        rendered[target] = [
            {"source": source, "match": kind, "lines": sorted((int(n) for n in line_numbers))[:30]}
            for (source, kind), line_numbers in sorted(hits.items())
        ]
    return rendered, dict(hashes), source_manifest, unstable_sources


def inventory(root: Path) -> dict[str, Any]:
    files = candidate_files(root)
    refs, hash_groups, source_manifest, unstable_sources = scan_references(files, root)
    canonical_paths = {v: str((ROOT / v).resolve()) for v in CANONICAL.values()}
    rows = []
    for path in files:
        rel = path.relative_to(root).as_posix()
        info = path.lstat()
        is_link = stat.S_ISLNK(info.st_mode)
        try:
            digest = None if is_link else sha256(path)
        except OSError:
            digest = None
        references = refs.get(rel, [])
        path_references = [item for item in references if item["match"] != "sha256"]
        same_hash = hash_groups.get(digest, []) if digest else []
        duplicate_peers = [item for item in same_hash if item != rel]
        if is_link:
            disposition = "preserve_symlink_review"
        elif path_references:
            disposition = "preserve_referenced"
        elif duplicate_peers:
            disposition = "review_exact_duplicate"
        else:
            disposition = "preserve_unreferenced_review"
        rows.append({
            "path": rel,
            "bytes": info.st_size,
            "mtime_ns": info.st_mtime_ns,
            "sha256": digest,
            "symlink": is_link,
            "references": references,
            "duplicate_peers": duplicate_peers,
            "disposition": disposition,
            "action": "retain",
        })

    grouped = {digest: sorted(items) for digest, items in hash_groups.items() if len(items) > 1}
    duplicate_bytes = sum(row["bytes"] for row in rows if row["disposition"] == "review_exact_duplicate")
    return {
        "schema_version": 1,
        "tool_sha256": sha256(Path(__file__).resolve()),
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "repository_root": str(ROOT),
        "candidate_root": str(root),
        "scope": "candidate directory only; .git, .venv, data, outputs/analysis excluded",
        "canonical_artifacts_protected": canonical_paths,
        "summary": {
            "file_count": len(rows),
            "total_bytes": sum(row["bytes"] for row in rows),
            "exact_duplicate_groups": len(grouped),
            "bytes_in_unreferenced_duplicate_members_for_manual_review": duplicate_bytes,
            "automatic_deletions": 0,
        },
        "duplicate_groups": grouped,
        "reference_source_manifest": source_manifest,
        "unstable_reference_sources": unstable_sources,
        "files": rows,
    }


def cmd_plan(args: argparse.Namespace) -> int:
    root = validate_candidate_root(args.root)
    plan = inventory(root)
    plan["plan_type"] = "thesis_artifact_cleanup_preview"
    data = canonical_json(plan)
    if args.out:
        output = Path(args.out).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(data)
        print(json.dumps({"status": "preview_only", "plan_path": str(output), "plan_file_sha256": sha256(output), "summary": plan["summary"]}, ensure_ascii=False, indent=2))
    else:
        sys.stdout.buffer.write(data)
    return 0


def cmd_apply(args: argparse.Namespace) -> int:
    plan_path = Path(args.plan).expanduser().resolve(strict=True)
    if sha256(plan_path) != args.plan_sha256:
        raise ValueError("计划文件SHA-256与确认值不一致；计划可能已被修改")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    if plan.get("plan_type") != "thesis_artifact_cleanup_preview" or plan.get("schema_version") != 1:
        raise ValueError("不支持的清理计划格式")
    if plan.get("tool_sha256") != sha256(Path(__file__).resolve()):
        raise ValueError("生成清理预览的脚本版本已变化；请重新生成计划")
    root = validate_candidate_root(plan["candidate_root"])
    proposed = [row for row in plan.get("files", []) if row.get("action") == "delete"]
    if not proposed:
        print(json.dumps({"status": "no_deletions_approved", "deleted": 0}, ensure_ascii=False))
        return 0
    fresh = inventory(root)
    if plan.get("reference_source_manifest") != fresh.get("reference_source_manifest"):
        raise ValueError("reference-source files changed since preview; generate a new plan")
    if fresh.get("unstable_reference_sources"):
        raise ValueError("reference-source files changed while scanning; retry after workspace is stable")
    current = {row["path"]: row for row in fresh["files"]}
    approved = []
    delete_paths = {row["path"] for row in proposed}
    for row in proposed:
        rel = row.get("path")
        if row.get("disposition") != "review_exact_duplicate":
            raise ValueError("仅允许复核过的精确重复文件进入apply: {}".format(rel))
        if any(ref.get("match") != "sha256" for ref in row.get("references", [])):
            raise ValueError("计划标记的文件已有引用，不可删除: {}".format(rel))
        latest = current.get(rel)
        if latest is None or latest["symlink"]:
            raise ValueError("文件缺失或为符号链接，拒绝删除: {}".format(rel))
        for key in ("bytes", "mtime_ns", "sha256"):
            if latest.get(key) != row.get(key):
                raise ValueError("文件{}已变化，拒绝删除: {}".format(key, rel))
        if any(ref.get("match") != "sha256" for ref in latest.get("references", [])):
            raise ValueError("文件出现新的路径引用，拒绝删除: {}".format(rel))
        peers = set(latest.get("duplicate_peers", [])) - delete_paths
        if not peers:
            raise ValueError("删除后没有保留的同哈希副本: {}".format(rel))
        target = root / rel
        resolved = target.resolve(strict=True)
        if root not in resolved.parents:
            raise ValueError("文件路径越出候选根目录: {}".format(rel))
        approved.append((rel, target, row))
    if not args.execute:
        print(json.dumps({"status": "validated_dry_run", "would_delete": [rel for rel, _, _ in approved]}, ensure_ascii=False, indent=2))
        return 0
    verify_reference_sources(plan.get("reference_source_manifest", []))
    deleted = []
    for rel, target, expected in approved:
        resolved = target.resolve(strict=True)
        if root not in resolved.parents:
            raise ValueError("执行前路径解析越出候选根目录，停止: {}".format(rel))
        info = target.lstat()
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode) or info.st_size != expected["bytes"] or info.st_mtime_ns != expected["mtime_ns"] or sha256(target) != expected["sha256"]:
            raise ValueError("执行前复核发现文件变化，停止: {}".format(rel))
        target.unlink()
        deleted.append(rel)
    print(json.dumps({"status": "deleted_after_explicit_plan_confirmation", "deleted": deleted}, ensure_ascii=False, indent=2))
    return 0


def verify_reference_sources(records: list[dict[str, Any]]) -> None:
    for record in records:
        path = ROOT / record["path"]
        try:
            info = path.lstat()
        except OSError as exc:
            raise ValueError("reference-source file disappeared before cleanup: {}".format(record["path"])) from exc
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
            raise ValueError("reference-source path changed type before cleanup: {}".format(record["path"]))
        if info.st_size != record["bytes"] or info.st_mtime_ns != record["mtime_ns"] or sha256(path) != record["sha256"]:
            raise ValueError("reference-source file changed before cleanup: {}".format(record["path"]))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    preview = sub.add_parser("plan", help="生成只读盘点/清理预览；默认所有文件保留")
    preview.add_argument("--root", default="outputs/thesis/candidate-current", help="candidate-*目录，必须位于outputs/thesis下")
    preview.add_argument("--out", help="将预览JSON写到指定位置；建议使用/tmp")
    preview.set_defaults(func=cmd_plan)
    apply = sub.add_parser("apply", help="仅执行经人工编辑批准的精确重复清理计划")
    apply.add_argument("--plan", required=True, help="人工复核并编辑过的计划JSON")
    apply.add_argument("--plan-sha256", required=True, help="编辑后计划文件的SHA-256摘要")
    apply.add_argument("--execute", action="store_true", help="省略时仅复核，不删除")
    apply.set_defaults(func=cmd_apply)
    args = parser.parse_args()
    try:
        return args.func(args)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
