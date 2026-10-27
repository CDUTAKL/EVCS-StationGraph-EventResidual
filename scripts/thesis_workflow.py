#!/usr/bin/env python3
"""Gate-driven controller for the existing thesis blueprint CLI.

Subcommands from thesis_blueprint.py are reused as-is. This controller never
refreshes a baseline, writes a task report itself, scores the thesis, or exports
DOCX/PDF files. Only the explicit `execute` or `run` command can start Claude Code.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import thesis_task_gate as gate  # noqa: E402


READY_EXIT_GATES = {"READY_TO_PREPARE", "READY_TO_EXECUTE", "READY_TO_COLLECT", "AWAITING_CODEX_REVIEW"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def brief_gate(value: Dict[str, Any]) -> Dict[str, Any]:
    """Keep the controller's final report concise while preserving decisions."""
    return {
        "gate": value.get("gate", "BLOCKED"),
        "state": value.get("state"),
        "collection_status": value.get("collection_status"),
        "allowed_change_count": value.get("allowed_change_count"),
        "out_of_scope_change_count": value.get("out_of_scope_change_count"),
        "blockers": value.get("blockers", []),
        "warnings": value.get("warnings", []),
        "next_action": value.get("next_action"),
    }


def execute_existing(command: Sequence[str]) -> int:
    """Run an existing CLI with inherited stdin/stdout/stderr (including TTY)."""
    try:
        completed = subprocess.run(list(command), cwd=str(ROOT), check=False)
        return completed.returncode
    except KeyboardInterrupt:
        return 130


class WorkflowController:
    def __init__(
        self,
        task: str,
        model: Optional[str] = None,
        gate_fn: Callable[[str], Dict[str, Any]] = gate.check_task,
        runner: Callable[[Sequence[str]], int] = execute_existing,
    ) -> None:
        self.task, self.model, self.gate_fn, self.runner = task, model, gate_fn, runner
        self.report: Dict[str, Any] = {
            "schema_version": 1,
            "task": task,
            "started_at": utc_now(),
            "mode": None,
            "status": "running",
            "gate_checks": [],
            "steps": [],
        }

    def inspect(self, label: str) -> Dict[str, Any]:
        started = time.perf_counter()
        try:
            value = self.gate_fn(self.task)
        except Exception as exc:  # Fail closed if the preflight itself cannot read state.
            value = {"gate": "BLOCKED", "blockers": ["gate检查失败：{}".format(exc)], "warnings": []}
        elapsed = time.perf_counter() - started
        summary = brief_gate(value)
        summary.update({"label": label, "elapsed_seconds": round(elapsed, 4)})
        self.report["gate_checks"].append(summary)
        return value

    def command(self, stage: str, subcommand: str, extra: Sequence[str] = ()) -> int:
        command = [sys.executable, str(ROOT / "scripts" / "thesis_blueprint.py"), subcommand, self.task]
        command.extend(extra)
        started_at = utc_now()
        started = time.perf_counter()
        code = self.runner(command)
        elapsed = time.perf_counter() - started
        self.report["steps"].append({
            "stage": stage,
            "command": command,
            "started_at": started_at,
            "elapsed_seconds": round(elapsed, 3),
            "exit_code": int(code),
            "stdout_stderr": "forwarded unchanged to the caller's terminal",
        })
        return int(code)

    def finish(self, status: str, exit_code: int) -> int:
        self.report["status"] = status
        self.report["finished_at"] = utc_now()
        self.report["exit_code"] = exit_code
        self.report["elapsed_seconds"] = round(
            sum(item["elapsed_seconds"] for item in self.report["steps"])
            + sum(item["elapsed_seconds"] for item in self.report["gate_checks"]), 3
        )
        return exit_code

    def require_gate(self, expected: str, label: str) -> bool:
        value = self.inspect(label)
        actual = value.get("gate", "BLOCKED")
        if actual != expected:
            self.report["gate_mismatch"] = {"expected": expected, "actual": actual}
            return False
        return True

    def prepare(self) -> int:
        if not self.require_gate("READY_TO_PREPARE", "before_prepare"):
            return self.finish("blocked_by_gate", 2)
        code = self.command("validate", "validate")
        if code:
            self.inspect("after_validate_failure")
            return self.finish("command_failed", code)
        code = self.command("prepare", "prepare")
        post = self.inspect("after_prepare")
        if code:
            return self.finish("command_failed", code)
        if post.get("gate") != "READY_TO_EXECUTE":
            self.report["gate_mismatch"] = {"expected": "READY_TO_EXECUTE", "actual": post.get("gate")}
            return self.finish("post_prepare_gate_failed", 2)
        return self.finish("ready_to_execute", 0)

    def execute(self) -> int:
        if not self.require_gate("READY_TO_EXECUTE", "before_execute"):
            return self.finish("blocked_by_gate", 2)
        extra = ["--model", self.model] if self.model else []
        code = self.command("execute_claude", "execute", extra)
        post = self.inspect("after_execute")
        if code:
            return self.finish("command_failed", code)
        if post.get("gate") == "READY_TO_COLLECT":
            return self.finish("ready_to_collect", 0)
        if post.get("gate") == "AWAITING_CODEX_REVIEW":
            return self.finish("awaiting_codex_review", 0)
        self.report["gate_mismatch"] = {
            "expected": ["READY_TO_COLLECT", "AWAITING_CODEX_REVIEW"], "actual": post.get("gate")
        }
        return self.finish("post_execute_gate_failed", 2)

    def collect(self) -> int:
        if not self.require_gate("READY_TO_COLLECT", "before_collect"):
            return self.finish("blocked_by_gate", 2)
        code = self.command("collect", "collect")
        post = self.inspect("after_collect")
        if code:
            return self.finish("command_failed", code)
        if post.get("gate") == "AWAITING_CODEX_REVIEW":
            return self.finish("awaiting_codex_review", 0)
        self.report["gate_mismatch"] = {"expected": "AWAITING_CODEX_REVIEW", "actual": post.get("gate")}
        return self.finish("post_collect_gate_failed", 2)

    def run(self) -> int:
        current = self.inspect("before_run")
        status = current.get("gate", "BLOCKED")
        if status == "READY_TO_PREPARE":
            code = self.command("validate", "validate")
            if code:
                self.inspect("after_validate_failure")
                return self.finish("command_failed", code)
            code = self.command("prepare", "prepare")
            current = self.inspect("after_prepare")
            if code:
                return self.finish("command_failed", code)
            status = current.get("gate")
            if status != "READY_TO_EXECUTE":
                self.report["gate_mismatch"] = {"expected": "READY_TO_EXECUTE", "actual": status}
                return self.finish("post_prepare_gate_failed", 2)
        if status == "READY_TO_EXECUTE":
            extra = ["--model", self.model] if self.model else []
            code = self.command("execute_claude", "execute", extra)
            current = self.inspect("after_execute")
            if code:
                return self.finish("command_failed", code)
            if current.get("gate") == "READY_TO_COLLECT":
                code = self.command("collect", "collect")
                current = self.inspect("after_collect")
                if code:
                    return self.finish("command_failed", code)
            if current.get("gate") == "AWAITING_CODEX_REVIEW":
                return self.finish("awaiting_codex_review", 0)
            self.report["gate_mismatch"] = {"expected": "AWAITING_CODEX_REVIEW", "actual": current.get("gate")}
            return self.finish("post_execute_gate_failed", 2)
        if status == "READY_TO_COLLECT":
            code = self.command("collect", "collect")
            current = self.inspect("after_collect")
            if code:
                return self.finish("command_failed", code)
            if current.get("gate") == "AWAITING_CODEX_REVIEW":
                return self.finish("awaiting_codex_review", 0)
            self.report["gate_mismatch"] = {"expected": "AWAITING_CODEX_REVIEW", "actual": current.get("gate")}
            return self.finish("post_collect_gate_failed", 2)
        if status == "AWAITING_CODEX_REVIEW":
            return self.finish("awaiting_codex_review_no_action", 0)
        if status not in READY_EXIT_GATES:
            self.report["gate_mismatch"] = {"expected": "an executable gate", "actual": status}
            return self.finish("blocked_by_gate", 2)
        self.report["gate_mismatch"] = {"expected": "a state that run can advance", "actual": status}
        return self.finish("no_action_required_or_allowed", 2)

    def inspect_only(self) -> int:
        value = self.inspect("inspect")
        status = value.get("gate", "BLOCKED")
        return self.finish("inspection_complete", 0 if status in READY_EXIT_GATES else 2)


def self_check() -> Dict[str, Any]:
    """Exercise gate states in /tmp and controller routing with an in-memory fake runner."""
    gate_fixture = gate.self_check()
    checks = ["task gate: {}".format("; ".join(gate_fixture["checks"]))]
    calls: List[List[str]] = []

    def fake_runner(command: Sequence[str]) -> int:
        calls.append(list(command))
        return 0

    def sequence_gate(*values: Dict[str, Any]) -> Callable[[str], Dict[str, Any]]:
        remaining = list(values)

        def next_gate(_task: str) -> Dict[str, Any]:
            if not remaining:
                return {"gate": "BLOCKED", "blockers": ["fixture exhausted"], "warnings": []}
            return remaining.pop(0)

        return next_gate

    blocked = WorkflowController("fixture-blocked", gate_fn=sequence_gate({"gate": "BLOCKED"}), runner=fake_runner)
    if blocked.prepare() != 2 or calls:
        raise AssertionError("blocked gate must stop before any blueprint command")
    checks.append("blocked gate launches no command")

    calls.clear()
    prepared = WorkflowController(
        "fixture-ready",
        gate_fn=sequence_gate({"gate": "READY_TO_PREPARE"}, {"gate": "READY_TO_EXECUTE"}),
        runner=fake_runner,
    )
    if prepared.prepare() != 0 or any(Path(item[1]).name != "thesis_blueprint.py" for item in calls):
        raise AssertionError("ready prepare path must validate, prepare, and stop before execute")
    if [item[2] for item in calls] != ["validate", "prepare"]:
        raise AssertionError("prepare path issued unexpected commands")
    checks.append("ready prepare path validates and freezes once")

    calls.clear()
    full_run = WorkflowController(
        "fixture-run",
        gate_fn=sequence_gate(
            {"gate": "READY_TO_PREPARE"},
            {"gate": "READY_TO_EXECUTE"},
            {"gate": "READY_TO_COLLECT"},
            {"gate": "AWAITING_CODEX_REVIEW"},
        ),
        runner=fake_runner,
    )
    if full_run.run() != 0 or [item[2] for item in calls] != ["validate", "prepare", "execute", "collect"]:
        raise AssertionError("full-run fixture must collect after execute when the gate requests it")
    checks.append("run path advances prepare, execute, collect with fake runner only")

    calls.clear()
    execute_only = WorkflowController(
        "fixture-execute",
        gate_fn=sequence_gate(
            {"gate": "READY_TO_EXECUTE"},
            {"gate": "READY_TO_COLLECT", "state": "execution_interrupted"},
        ),
        runner=fake_runner,
    )
    if execute_only.execute() != 0 or execute_only.report["status"] != "ready_to_collect":
        raise AssertionError("single execute must stop at READY_TO_COLLECT")
    if [item[2] for item in calls] != ["execute"]:
        raise AssertionError("single execute must not collect automatically")
    checks.append("single execute stops at READY_TO_COLLECT")

    calls.clear()
    already_collected = WorkflowController(
        "fixture-already-collected",
        gate_fn=sequence_gate({"gate": "READY_TO_EXECUTE"}, {"gate": "AWAITING_CODEX_REVIEW"}),
        runner=fake_runner,
    )
    if already_collected.execute() != 0 or already_collected.report["status"] != "awaiting_codex_review":
        raise AssertionError("execute that already collected must finish awaiting review")
    if [item[2] for item in calls] != ["execute"]:
        raise AssertionError("execute must not issue a second collect after review is pending")
    checks.append("execute already awaiting review does not collect twice")

    calls.clear()
    collect_only = WorkflowController(
        "fixture-collect",
        gate_fn=sequence_gate({"gate": "READY_TO_COLLECT"}, {"gate": "AWAITING_CODEX_REVIEW"}),
        runner=fake_runner,
    )
    if collect_only.run() != 0 or [item[2] for item in calls] != ["collect"]:
        raise AssertionError("run at READY_TO_COLLECT must call collect")
    checks.append("run at READY_TO_COLLECT calls collect")

    calls.clear()
    awaiting = WorkflowController(
        "fixture-awaiting",
        gate_fn=sequence_gate({"gate": "AWAITING_CODEX_REVIEW"}),
        runner=fake_runner,
    )
    if awaiting.run() != 0 or awaiting.report["status"] != "awaiting_codex_review_no_action" or calls:
        raise AssertionError("run at AWAITING_CODEX_REVIEW must finish without action")
    checks.append("run at AWAITING_CODEX_REVIEW exits without action")
    return {
        "status": "passed",
        "checks": checks,
        "model_started": False,
        "repository_files_written": False,
        "temporary_fixture_created": True,
        "temporary_fixture_cleaned": True,
    }


def print_report(report: Dict[str, Any], as_json: bool) -> None:
    if as_json:
        print("WORKFLOW_SUMMARY_JSON")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return
    print("Workflow: {} (exit {})".format(report.get("status"), report.get("exit_code")))
    for item in report.get("steps", []):
        print("  {:24s} {:7.3f}s  exit={}".format(item["stage"], item["elapsed_seconds"], item["exit_code"]))
    for item in report.get("gate_checks", []):
        print("  gate {:20s} {:7.4f}s  {}".format(item["label"], item["elapsed_seconds"], item["gate"]))
        for blocker in item.get("blockers", []):
            print("    BLOCK {}".format(blocker))
        for warning in item.get("warnings", []):
            print("    WARN  {}".format(warning))
        if item.get("next_action"):
            actions = item["next_action"]
            print("    Next: {}".format("; ".join(actions) if isinstance(actions, list) else actions))
    if report.get("gate_mismatch"):
        print("  gate decision: {}".format(json.dumps(report["gate_mismatch"], ensure_ascii=False)))


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (
        ("inspect", "只读门禁检查"),
        ("prepare", "门禁通过后执行validate+prepare"),
        ("execute", "门禁通过后执行Claude；随后按门禁状态提示下一步"),
        ("collect", "门禁通过后执行现有collect"),
        ("run", "按门禁串行推进到本轮可达状态；可能启动Claude"),
    ):
        cmd = subparsers.add_parser(name, help=help_text)
        cmd.add_argument("task", help="蓝图任务ID或任务目录")
        cmd.add_argument("--json", action="store_true", help="在原始命令输出后附加结构化耗时JSON摘要")
        if name in {"execute", "run"}:
            cmd.add_argument("--model", default=None, help="可选Claude Code模型；默认沿用本机配置")
    selfcheck = subparsers.add_parser("self-check", help="用临时包和内存夹具核对状态迁移，不启动模型")

    args = parser.parse_args(argv)
    if args.command == "self-check":
        value = self_check()
        print(json.dumps(value, ensure_ascii=False, indent=2))
        return 0

    controller = WorkflowController(args.task, model=getattr(args, "model", None))
    controller.report["mode"] = args.command
    if args.command == "inspect":
        code = controller.inspect_only()
    elif args.command == "prepare":
        code = controller.prepare()
    elif args.command == "execute":
        code = controller.execute()
    elif args.command == "collect":
        code = controller.collect()
    else:
        code = controller.run()
    print_report(controller.report, args.json)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
