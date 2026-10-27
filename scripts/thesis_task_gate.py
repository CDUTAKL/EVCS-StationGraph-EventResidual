#!/usr/bin/env python3
"""Read-only preflight for one thesis blueprint task.

This command reuses thesis_blueprint's schema and snapshot rules. It never
launches Claude Code and never writes to the project or task package.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import thesis_blueprint as blueprint  # noqa: E402


def check_task(task: str) -> Dict[str, Any]:
    directory = blueprint.task_dir(task)
    result: Dict[str, Any] = {
        "schema_version": 1,
        "task": blueprint.relpath(directory),
        "gate": "BLOCKED",
        "checks": [],
        "blockers": [],
        "warnings": [],
        "next_action": None,
    }
    try:
        bp, state, baseline = blueprint.read_task_files(directory)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        result["blockers"].append("蓝图/状态/基线无法读取或蓝图无效：{}".format(exc))
        return result

    result["task_id"] = bp.get("task_id")
    result["state"] = state.get("status", "missing")
    result["allowed_paths"] = bp.get("allowed_paths", [])
    if not baseline:
        if not (directory / "state.json").is_file():
            result["blockers"].append("缺少state.json；不能确定任务是否允许准备")
        elif state.get("status") in {"draft", "execution_not_started"}:
            result["gate"] = "READY_TO_PREPARE"
            result["checks"].append("蓝图结构和来源定位通过；尚无冻结基线")
            result["next_action"] = [
                "python3 scripts/thesis_blueprint.py validate {}".format(bp["task_id"]),
                "python3 scripts/thesis_blueprint.py prepare {}".format(bp["task_id"]),
            ]
        else:
            result["blockers"].append("任务状态为{}，但缺少baseline.json".format(state.get("status")))
        return result

    if not (directory / "state.json").is_file():
        result["blockers"].append("缺少state.json")
    expected_baseline = state.get("baseline_sha256")
    actual_baseline = blueprint.sha256_file(directory / "baseline.json")
    if expected_baseline != actual_baseline:
        result["blockers"].append("state.json中的baseline_sha256与baseline.json不一致")
    else:
        result["checks"].append("冻结基线哈希匹配")

    for filename, expected in baseline.get("protected_package_hashes", {}).items():
        path = directory / filename
        if not path.is_file() or blueprint.sha256_file(path) != expected:
            result["blockers"].append("冻结任务文件缺失或哈希变化：{}".format(filename))
    if not result["blockers"]:
        result["checks"].append("蓝图、证据摘录和执行包冻结哈希匹配")

    status = state.get("status")
    collection_path = directory / "collection-report.json"
    collection = None
    if collection_path.exists():
        try:
            collection = blueprint.read_json(collection_path)
        except (OSError, ValueError) as exc:
            result["blockers"].append("collection-report.json无法读取：{}".format(exc))

    # Sources and skills must remain frozen until Claude starts. After collection,
    # the packet hashes preserve what the executor saw; edited source files may
    # be the intended task output and are compared through the collection report.
    verify_launch_inputs = collection is None and status == "ready"
    if verify_launch_inputs:
        source_errors = []
        for raw, expected in baseline.get("source_hashes", {}).items():
            try:
                path = blueprint.project_path(raw, must_exist=True)
                if not path.is_file() or blueprint.sha256_file(path) != expected:
                    source_errors.append(raw)
            except (ValueError, OSError):
                source_errors.append(raw)
        if source_errors:
            result["blockers"].append("冻结证据源缺失或已变化：{}".format(", ".join(source_errors[:20])))
        else:
            result["checks"].append("冻结证据源哈希匹配")

        skill_errors = []
        for name, expected in baseline.get("claude_skill_hashes", {}).items():
            try:
                current = blueprint.sha256_file(blueprint.validate_skill(name))
            except (ValueError, OSError):
                skill_errors.append(name)
                continue
            if current != expected:
                skill_errors.append(name)
        if skill_errors:
            result["blockers"].append("任务准备后指定Claude skill发生变化或不可用：{}".format(", ".join(skill_errors)))
        resource_hashes = baseline.get("claude_skill_resource_hashes")
        if resource_hashes is not None:
            try:
                current_resources = blueprint.skill_resource_hash_map(baseline.get("claude_skill_hashes", {}).keys())
            except (ValueError, OSError) as exc:
                current_resources = None
                result["blockers"].append("无法核对Claude skill引用资源：{}".format(exc))
            if current_resources is not None and current_resources != resource_hashes:
                result["blockers"].append("任务准备后Claude skill引用资源发生变化")

    try:
        current = blueprint.current_snapshot(directory, baseline)
        changes = blueprint.changes_since_baseline(baseline, current)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        result["blockers"].append("无法重建当前工作区快照：{}".format(exc))
        changes, current = [], {}
    allowed_changes = [item["path"] for item in changes if blueprint.matches_allowed(item["path"], bp["allowed_paths"])]
    out_of_scope = [item["path"] for item in changes if not blueprint.matches_allowed(item["path"], bp["allowed_paths"])]
    result["allowed_change_count"] = len(allowed_changes)
    result["allowed_changes"] = allowed_changes[:30]
    result["out_of_scope_change_count"] = len(out_of_scope)
    result["out_of_scope_changes"] = out_of_scope[:30]
    if len(allowed_changes) > 30 or len(out_of_scope) > 30:
        result["warnings"].append("变更路径明细仅显示前30项；JSON同时返回完整计数")
    if collection is None and current and current.get("head") != baseline.get("head"):
        result["blockers"].append("HEAD已从冻结基线变化；需人工核查，不可沿用本任务基线")
    if collection is None and out_of_scope:
        result["blockers"].append("冻结后发现授权范围外变化：{}".format(", ".join(out_of_scope[:20])))

    status = state.get("status")
    package_files = {
        path.relative_to(directory).as_posix()
        for path in directory.rglob("*") if path.is_file()
    }
    required_files = {
        "blueprint.json", "context-snapshot.json", "EXECUTION_PACKET.md",
        "execution-report.json", "baseline.json", "state.json",
    }
    missing_files = sorted(required_files - package_files)
    if missing_files:
        result["blockers"].append("任务包缺少必要文件：{}".format(", ".join(missing_files)))
    unexpected = sorted(package_files - blueprint.PACKAGE_FILES)
    result["unexpected_task_file_count"] = len(unexpected)
    result["unexpected_task_files"] = unexpected[:30]
    if unexpected and collection is None:
        result["blockers"].append("任务包含未登记文件：{}".format(", ".join(unexpected)))

    result["collection_status"] = collection.get("status") if collection else None
    if collection is not None:
        if collection.get("schema_version") != 1:
            result["blockers"].append("collection report的schema_version不是当前支持的1")
        if collection.get("task_id") != bp.get("task_id"):
            result["blockers"].append("collection report的task_id与蓝图不一致")
        if not isinstance(collection.get("allowed_changes", []), list):
            result["blockers"].append("collection report的allowed_changes不是数组")
        if collection.get("acceptance") != "pending_codex_review":
            result["blockers"].append("collection report缺少pending_codex_review交接标记")

    if status in {"draft", "execution_not_started"}:
        result["blockers"].append("任务已存在基线，但状态仍为{}；不自动刷新或覆盖".format(status))
    elif status == "ready" and collection is None:
        if not result["blockers"]:
            result["gate"] = "READY_TO_EXECUTE"
            result["next_action"] = ["python3 scripts/thesis_blueprint.py execute {}".format(bp["task_id"])]
    elif status == "executing" and collection is None:
        result["blockers"].append("任务仍标记为executing；先确认Claude进程已退出并按中断恢复流程处理，不能并发回收")
    elif status in {"returned", "execution_interrupted"} and collection is None:
        if not result["blockers"]:
            result["gate"] = "READY_TO_COLLECT"
            result["next_action"] = ["python3 scripts/thesis_blueprint.py collect {}".format(bp["task_id"])]
    elif collection is not None:
        collected_items = collection.get("allowed_changes", [])
        collected_names = {item.get("path") for item in collected_items if isinstance(item, dict)}
        committed_since_baseline: set[str] = set()
        try:
            baseline_head = baseline.get("head")
            current_head = current.get("head") if current else None
            if baseline_head and current_head and baseline_head != current_head:
                committed = blueprint.git_bytes([
                    "diff", "--name-only", "--no-renames", "-z", baseline_head, current_head
                ]).decode("utf-8", "surrogateescape")
                committed_since_baseline = {part for part in committed.split("\0") if part}
        except (OSError, RuntimeError, ValueError) as exc:
            result["blockers"].append("无法核对baseline后的已提交路径：{}".format(exc))
        current_task_changes = {
            path for path in committed_since_baseline.union(item["path"] for item in changes)
            if blueprint.matches_allowed(path, bp["allowed_paths"])
        }
        if collection.get("status") == "awaiting_codex_review" and current_task_changes != collected_names:
            result["blockers"].append("collection report后的授权文件集合发生变化")
        hash_drift = []
        for item in collected_items:
            if not isinstance(item, dict) or not isinstance(item.get("path"), str):
                hash_drift.append("collection report中的allowed_changes结构无效")
                continue
            expected_after = item.get("after", {})
            path = blueprint.project_path(item["path"])
            actual_after = blueprint.stat_record(path, include_hash=True)
            fields = ("exists", "kind", "size", "sha256", "target")
            if any(actual_after.get(field) != expected_after.get(field) for field in fields):
                hash_drift.append(item["path"])
        if hash_drift:
            result["blockers"].append("回收后授权产物缺失或内容已变化：{}".format(", ".join(hash_drift[:20])))
        if current and collection.get("current_head") != current.get("head"):
            result["warnings"].append("HEAD在collection后变化；已逐项核对回收报告中的授权产物")
        if out_of_scope:
            result["warnings"].append("collection后/基线后有{}项范围外路径变化；请确认不影响本任务复核".format(len(out_of_scope)))
        if unexpected:
            result["warnings"].append("任务包内有{}个未登记文件，需一并人工检查".format(len(unexpected)))
        cstatus = collection.get("status")
        if cstatus == "awaiting_codex_review" and not result["blockers"]:
            result["gate"] = "AWAITING_CODEX_REVIEW"
            result["next_action"] = ["检查collection-report.json、任务差异及每个允许改动，再决定是否接受"]
        else:
            result["warnings"].append("回收状态为{}；该状态不是验收结论".format(cstatus or "未知"))
            if not result["blockers"]:
                result["gate"] = "REVIEW_REQUIRED"
                result["next_action"] = ["先处理collection report中的问题；保留本任务包，不覆盖或刷新"]
    else:
        result["warnings"].append("状态{}没有匹配的自动门禁规则".format(status or "缺失"))

    if result["blockers"]:
        result["gate"] = "BLOCKED"
        result["next_action"] = ["停止自动推进；根据blockers人工核查，不要刷新基线覆盖既有结果"]
    elif not result["checks"]:
        result["warnings"].append("没有足够证据证明通过")
    return result


def self_check() -> Dict[str, Any]:
    """Exercise task-state transitions with a temporary package outside the repo."""
    directory_context = tempfile.TemporaryDirectory(prefix="thesis-task-gate-")
    directory = Path(directory_context.name) / "fixture"
    directory.mkdir()
    original = {
        "task_dir": blueprint.task_dir,
        "relpath": blueprint.relpath,
        "read_task_files": blueprint.read_task_files,
        "current_snapshot": blueprint.current_snapshot,
        "changes_since_baseline": blueprint.changes_since_baseline,
    }
    package = {
        "task_id": "GATE-FIXTURE",
        "allowed_paths": [],
        "execution_policy": {},
    }
    for filename, content in (
        ("blueprint.json", "{}\n"),
        ("context-snapshot.json", "{}\n"),
        ("EXECUTION_PACKET.md", "fixture\n"),
        ("execution-report.json", "{}\n"),
    ):
        (directory / filename).write_text(content, encoding="utf-8")
    state: Dict[str, Any] = {}
    baseline: Dict[str, Any] = {}
    try:
        blueprint.task_dir = lambda _task: directory
        blueprint.relpath = lambda _path: "fixture"
        blueprint.read_task_files = lambda _directory: (package, state, baseline)
        baseline.update({
            "head": "fixture-head",
            "paths": {},
            "allowed_paths": [],
            "source_hashes": {},
            "claude_skill_hashes": {},
            "protected_package_hashes": {
                name: blueprint.sha256_file(directory / name)
                for name in ("blueprint.json", "context-snapshot.json", "EXECUTION_PACKET.md")
            },
        })
        (directory / "baseline.json").write_text(json.dumps(baseline), encoding="utf-8")
        blueprint.current_snapshot = lambda _directory, _baseline: {"head": "fixture-head", "paths": {}}
        blueprint.changes_since_baseline = lambda _baseline, _current: []
        checks = []

        for status in ("returned", "execution_interrupted"):
            state.clear()
            state.update({"status": status, "baseline_sha256": blueprint.sha256_file(directory / "baseline.json")})
            (directory / "state.json").write_text(json.dumps(state), encoding="utf-8")
            (directory / "collection-report.json").unlink(missing_ok=True)
            result = check_task("fixture")
            if result["gate"] != "READY_TO_COLLECT":
                raise AssertionError("{} without collection must be READY_TO_COLLECT: {}".format(status, result))
        checks.append("returned and execution_interrupted wait for collect")

        state.clear()
        state.update({"status": "executing", "baseline_sha256": blueprint.sha256_file(directory / "baseline.json")})
        (directory / "state.json").write_text(json.dumps(state), encoding="utf-8")
        (directory / "collection-report.json").unlink(missing_ok=True)
        result = check_task("fixture")
        if result["gate"] != "BLOCKED":
            raise AssertionError("an active executing state must block concurrent collection")
        checks.append("active executing state blocks concurrent collect")

        state.clear()
        state.update({"status": "returned", "baseline_sha256": blueprint.sha256_file(directory / "baseline.json")})
        (directory / "state.json").write_text(json.dumps(state), encoding="utf-8")
        collection = {
            "schema_version": 1,
            "task_id": "GATE-FIXTURE",
            "status": "awaiting_codex_review",
            "acceptance": "pending_codex_review",
            "current_head": "fixture-head",
            "allowed_changes": [],
        }
        (directory / "collection-report.json").write_text(json.dumps(collection), encoding="utf-8")
        result = check_task("fixture")
        if result["gate"] != "AWAITING_CODEX_REVIEW":
            raise AssertionError("a completed collection must await review: {}".format(result))
        checks.append("collected task awaits Codex review")

        baseline["protected_package_hashes"]["EXECUTION_PACKET.md"] = "0" * 64
        (directory / "baseline.json").write_text(json.dumps(baseline), encoding="utf-8")
        state["baseline_sha256"] = blueprint.sha256_file(directory / "baseline.json")
        (directory / "state.json").write_text(json.dumps(state), encoding="utf-8")
        result = check_task("fixture")
        if result["gate"] != "BLOCKED":
            raise AssertionError("corrupt protected packet must block: {}".format(result))
        checks.append("protected package hash drift blocks progression")
        return {
            "status": "passed",
            "checks": checks,
            "repository_files_written": False,
            "temporary_fixture_created": True,
            "temporary_fixture_cleaned": True,
        }
    finally:
        for name, value in original.items():
            setattr(blueprint, name, value)
        directory_context.cleanup()


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task", nargs="?", help="蓝图任务ID或项目内任务目录")
    parser.add_argument("--json", action="store_true", help="输出机器可读JSON")
    parser.add_argument("--self-check", action="store_true", help="用临时任务包检查状态门禁，不修改仓库")
    args = parser.parse_args(argv)
    if args.self_check:
        print(json.dumps(self_check(), ensure_ascii=False, indent=2))
        return 0
    if not args.task:
        parser.error("请提供任务ID，或使用--self-check")
    try:
        report = check_task(args.task)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        report = {"gate": "BLOCKED", "blockers": [str(exc)], "next_action": None}
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("Gate: {}".format(report["gate"]))
        print("Task: {}".format(report.get("task_id", args.task)))
        if "allowed_change_count" in report:
            print("Changes: allowed={}, out-of-scope={}".format(
                report["allowed_change_count"], report["out_of_scope_change_count"]
            ))
        for item in report.get("checks", []):
            print("PASS  {}".format(item))
        for item in report.get("warnings", []):
            print("WARN  {}".format(item))
        for item in report.get("blockers", []):
            print("BLOCK {}".format(item))
        if report.get("next_action"):
            print("Next:")
            for item in report["next_action"]:
                print("  {}".format(item))
    return 0 if report["gate"].startswith("READY_") or report["gate"] == "AWAITING_CODEX_REVIEW" else 2


if __name__ == "__main__":
    raise SystemExit(main())
