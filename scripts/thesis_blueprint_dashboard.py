#!/usr/bin/env python3
"""Serve a small, read-only local dashboard for thesis blueprint handoffs.

The server exposes only an allowlisted projection of task JSON. It never reads
execution packets, context snapshots, baselines, environment variables, or task
transcripts, and it never starts Claude Code.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import ipaddress
import json
import math
import os
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path, PurePosixPath
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import parse_qs, urlsplit


ROOT = Path(__file__).resolve().parents[1]
TASKS_DIR = ROOT / "docs" / "thesis" / "blueprints" / "tasks"
LIVE_DIR = Path(tempfile.gettempdir()) / "thesis-blueprint-live"
TASK_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{1,79}\Z")
TIMESTAMP_RE = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})\Z"
)
MODEL_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/\-\[\]()+ ]{0,119}\Z")
MAX_JSON_BYTES = 2 * 1024 * 1024
# Give the task statusline up to one minute to produce another snapshot. This
# spans twelve five-second page refreshes and accommodates sparse callbacks;
# older values stay visible but cannot be described as live.
MAX_STATUSLINE_AGE_SECONDS = 60

STATUS_LABELS = {
    "draft": "草稿",
    "ready": "已准备",
    "executing": "Claude正在执行",
    "execution_not_started": "Claude尚未启动",
    "returned": "执行已返回",
    "execution_interrupted": "执行已中断",
    "awaiting_codex_review": "等待Codex复核",
    "scope_violation": "超出任务范围",
    "baseline_changed": "任务基线发生变化",
    "report_incomplete": "执行报告不完整",
}

TELEMETRY_FIELDS = {
    "input_tokens": "Input tokens",
    "output_tokens": "Output tokens",
    "total_tokens": "Total tokens",
    "cache_read_input_tokens": "Cache read input tokens",
    "cache_creation_input_tokens": "Cache creation input tokens",
    "cost_usd": "Reported cost (USD)",
    "total_cost_usd": "Reported total cost (USD)",
    "duration_ms": "Reported duration (ms)",
    "provider_quota_remaining": "Provider quota remaining",
    "provider_quota_used": "Provider quota used",
    "provider_quota_percent": "Provider quota percent",
    "account_quota_remaining": "Account quota remaining",
    "account_quota_used": "Account quota used",
    "account_quota_percent": "Account quota percent",
}
TELEMETRY_CONTAINERS = ("usage", "token_usage", "usage_metrics")
PID_FIELDS = ("actual_pid", "claude_pid", "pid")


def read_task_json(directory: Path, filename: str) -> Dict[str, Any]:
    """Read one known JSON file without following symlinks or accepting huge input."""
    path = directory / filename
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_JSON_BYTES:
            return {}
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def read_live_telemetry(task_id: str) -> Dict[str, Any]:
    if not TASK_ID_RE.fullmatch(task_id):
        return {}
    try:
        if LIVE_DIR.is_symlink() or not LIVE_DIR.is_dir():
            return {}
        path = LIVE_DIR / (task_id + ".json")
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 16_384:
            return {}
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def live_telemetry_projection(value: Dict[str, Any]) -> Dict[str, Any]:
    allowed = {
        "context_input_tokens": "Context input tokens",
        "context_output_tokens": "Context output tokens",
        "context_window_size": "Context window size",
        "context_used_percent": "Context used percent",
        "current_input_tokens": "Current input tokens",
        "current_output_tokens": "Current output tokens",
        "cache_read_input_tokens": "Cache read input tokens",
        "cache_creation_input_tokens": "Cache creation input tokens",
        "estimated_cost_usd": "Client-estimated cost (USD)",
        "duration_ms": "Session duration (ms)",
    }
    items = []
    for key, label in allowed.items():
        field = value.get(key)
        if measured_number(field):
            items.append({"label": label, "value": field})
    limits = value.get("rate_limits")
    quota_available = False
    if isinstance(limits, dict):
        for window in ("five_hour", "seven_day", "seven_day_sonnet", "seven_day_opus"):
            entry = limits.get(window)
            if isinstance(entry, dict):
                used = entry.get("used_percentage")
                if measured_number(used):
                    items.append({"label": "Reported account limit · {} used percent".format(window.replace("_", " ")), "value": used})
                    quota_available = True
                reset = safe_timestamp(entry.get("resets_at"))
                if reset:
                    items.append({"label": "Reported account limit · {} reset".format(window.replace("_", " ")), "value": reset})
                    quota_available = True
    model = value.get("model")
    if not isinstance(model, str) or len(model) > 120 or not MODEL_RE.fullmatch(model):
        model = None
    return {
        "model": model,
        "updated_at": safe_timestamp(value.get("updated_at")),
        "telemetry": items,
        "quota_available": quota_available,
        "present": bool(value),
    }


def snapshot_age_seconds(updated_at: Optional[str], now: Optional[datetime] = None) -> Optional[float]:
    """Return age since the adapter received this statusline snapshot.

    The adapter timestamp is receipt time, not a provider-side measurement time.
    Invalid or future timestamps are unknown and must never be treated as fresh.
    """
    if updated_at is None:
        return None
    try:
        observed = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
    except ValueError:
        return None
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    age = (current.astimezone(timezone.utc) - observed.astimezone(timezone.utc)).total_seconds()
    if age < 0:
        return None
    return round(age, 1)


def process_liveness(pid: Optional[int]) -> str:
    """Check whether a recorded PID exists, without sending it a signal."""
    if pid is None:
        return "unknown"
    try:
        os.kill(pid, 0)
        return "alive"
    except ProcessLookupError:
        return "absent"
    except PermissionError:
        # EPERM means the process exists but could not be signalled.
        return "alive"
    except OSError:
        return "unknown"


def process_identity(pid: Optional[int]) -> str:
    """Verify only the recorded PID's executable name; never expose its argv."""
    if pid is None:
        return "unknown"
    try:
        result = subprocess.run(
            ["ps", "-p", str(pid), "-o", "ucomm="],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    if result.returncode != 0:
        return "absent"
    name = Path(result.stdout.strip()).name.casefold()
    if not name:
        return "unknown"
    return "claude" if name in {"claude", "claude.exe"} else "other"


def execution_report_state(report: Dict[str, Any]) -> str:
    """Distinguish an untouched template from a submitted execution report."""
    if not report:
        return "missing"
    summary = report.get("summary")
    substantive = bool(isinstance(summary, str) and summary.strip())
    substantive = substantive or any(
        isinstance(report.get(key), list) and bool(report[key])
        for key in ("changed_paths", "evidence_used", "claim_or_number_changes", "checks", "unresolved", "blockers")
    )
    if not substantive:
        return "template"
    required_lists = (
        "changed_paths",
        "evidence_used",
        "claim_or_number_changes",
        "checks",
        "unresolved",
        "blockers",
    )
    has_summary = isinstance(summary, str) and bool(summary.strip())
    has_model = bool(safe_model(report))
    if has_summary and has_model and all(isinstance(report.get(key), list) for key in required_lists):
        return "filled"
    return "partial"


def runtime_projection(
    task_marked_executing: bool,
    pid_state: str,
    snapshot_present: bool,
    snapshot_updated_at: Optional[str],
    now: Optional[datetime] = None,
    pid_identity: str = "unknown",
) -> Dict[str, Any]:
    """Combine task, process, and snapshot state without treating old data as live."""
    age = snapshot_age_seconds(snapshot_updated_at, now=now)
    fresh = snapshot_present and age is not None and age <= MAX_STATUSLINE_AGE_SECONDS
    return {
        "telemetry_age_seconds": age,
        "telemetry_fresh": fresh,
        "telemetry_stale": snapshot_present and not fresh,
        "telemetry_live": task_marked_executing and pid_state == "alive" and pid_identity == "claude" and fresh,
        "process_exited": task_marked_executing and (pid_state == "absent" or pid_identity == "other"),
    }


def safe_timestamp(value: Any) -> Optional[str]:
    if not isinstance(value, str) or len(value) > 40 or not TIMESTAMP_RE.fullmatch(value):
        return None
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return value


def safe_project_path(value: Any) -> Optional[str]:
    """Keep display paths relative and filter credential or environment paths."""
    if not isinstance(value, str) or not value or len(value) > 500:
        return None
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        return None
    normalized = value.replace("\\", "/")
    if normalized.startswith(("/", "//")) or re.match(r"^[A-Za-z]:", normalized):
        return None
    parts = PurePosixPath(normalized).parts
    if not parts or any(part in {"", ".", ".."} for part in parts):
        return None
    lower_parts = [part.lower() for part in parts]
    name = lower_parts[-1]
    if any(part in {".git", ".claude", ".ssh"} for part in lower_parts):
        return None
    if name == ".env" or name.startswith(".env.") or name.startswith("id_rsa"):
        return None
    if name.endswith((".pem", ".key", ".p12", ".pfx")):
        return None
    if normalized == ".gitignore" or normalized == "scripts/thesis_blueprint.py":
        return None
    if normalized == "scripts" or normalized == "docs/thesis/blueprints" or normalized.startswith("docs/thesis/blueprints/"):
        return None
    if any(
        normalized == prefix or normalized.startswith(prefix + "/")
        for prefix in ("data/external", "data/interim", "data/processed")
    ):
        return None
    if "*" in parts[0] or "?" in parts[0] or "[" in parts[0]:
        return None
    return normalized


def matches_allowed(path: str, allowed: Iterable[str]) -> bool:
    for pattern in allowed:
        if path == pattern or fnmatch.fnmatchcase(path, pattern):
            return True
        if pattern.endswith("/") and path.startswith(pattern):
            return True
        if not any(char in pattern for char in "*?[") and path.startswith(pattern.rstrip("/") + "/"):
            return True
    return False


def safe_allowed_paths(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    paths = []
    for item in value[:200]:
        safe = safe_project_path(item)
        if safe and safe not in paths:
            paths.append(safe)
    return paths


def safe_changed_paths(collection: Dict[str, Any], report: Dict[str, Any], allowed: List[str]) -> Dict[str, Any]:
    """Show verified collected in-scope paths, or clearly mark report-only claims."""
    collected = bool(collection)
    source = collection.get("allowed_changes") if collected else report.get("changed_paths")
    result: List[str] = []
    if isinstance(source, list):
        for item in source[:500]:
            raw = item.get("path") if isinstance(item, dict) else item
            path = safe_project_path(raw)
            if path and matches_allowed(path, allowed) and path not in result:
                result.append(path)
    out_of_scope = collection.get("out_of_scope_changes")
    out_count = len(out_of_scope) if isinstance(out_of_scope, list) else 0
    return {
        "paths": result,
        "source": "collection report" if collected else "execution report (not yet collected)",
        "collected": collected,
        "out_of_scope_count": out_count,
    }


def measured_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def report_telemetry(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Read only known numeric telemetry fields at report level or under usage objects."""
    scopes = [report]
    for container_name in TELEMETRY_CONTAINERS:
        nested = report.get(container_name)
        if isinstance(nested, dict):
            scopes.append(nested)
    found: List[Dict[str, Any]] = []
    seen = set()
    for scope in scopes:
        for key, label in TELEMETRY_FIELDS.items():
            value = scope.get(key)
            if key not in seen and measured_number(value):
                found.append({"label": label, "value": value})
                seen.add(key)
    return found


def actual_pid(state: Dict[str, Any]) -> Optional[int]:
    for key in PID_FIELDS:
        value = state.get(key)
        if isinstance(value, int) and not isinstance(value, bool) and value > 0:
            return value
    return None


def safe_model(report: Dict[str, Any]) -> Optional[str]:
    value = report.get("model")
    if isinstance(value, str) and len(value) <= 120 and MODEL_RE.fullmatch(value):
        return value
    return None


def task_ids() -> List[str]:
    try:
        entries = TASKS_DIR.iterdir()
    except OSError:
        return []
    ids = []
    for entry in entries:
        if not TASK_ID_RE.fullmatch(entry.name) or entry.is_symlink():
            continue
        try:
            if entry.is_dir() and (entry / "state.json").is_file() and not (entry / "state.json").is_symlink():
                ids.append(entry.name)
        except OSError:
            continue
    return sorted(ids)


def task_projection(task_id: str) -> Optional[Dict[str, Any]]:
    if not TASK_ID_RE.fullmatch(task_id):
        return None
    directory = TASKS_DIR / task_id
    try:
        if directory.is_symlink() or not directory.is_dir() or directory.resolve().parent != TASKS_DIR.resolve():
            return None
    except OSError:
        return None

    blueprint = read_task_json(directory, "blueprint.json")
    state = read_task_json(directory, "state.json")
    report = read_task_json(directory, "execution-report.json")
    collection = read_task_json(directory, "collection-report.json")
    allowed = safe_allowed_paths(blueprint.get("allowed_paths"))
    status = state.get("status")
    known_status = status if isinstance(status, str) and status in STATUS_LABELS else "unknown"
    prepared = safe_timestamp(state.get("prepared_at"))
    started = safe_timestamp(state.get("execution_started_at"))
    finished = safe_timestamp(state.get("execution_finished_at"))
    collected_at = safe_timestamp(state.get("collected_at")) or safe_timestamp(collection.get("collected_at"))
    has_collection = bool(collection)
    has_execution = bool(report)
    report_state = execution_report_state(report)
    task_marked_executing = known_status == "executing"
    # Review is a human/agent record, not acceptance inferred from collection.
    # Bind it to the current manuscript so later edits invalidate the badge.
    review_record = state.get("codex_review")
    review_record = review_record if isinstance(review_record, dict) else {}
    source_hash = None
    source = ROOT / "docs/thesis/thesis-manuscript.md"
    if review_record:
        try:
            if not source.is_symlink() and source.is_file() and source.stat().st_size <= MAX_JSON_BYTES:
                source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
        except OSError:
            pass
    review = codex_review_projection(review_record, collection, source_hash)
    pending_review = has_collection and review["status"] != "passed"
    exit_code = state.get("claude_exit_code")
    if not isinstance(exit_code, int) or isinstance(exit_code, bool):
        exit_code = None

    report_metrics = report_telemetry(report)
    telemetry = report_metrics
    live = live_telemetry_projection(read_live_telemetry(task_id))
    if live["present"]:
        telemetry = live["telemetry"]
    provider_quota = [item for item in telemetry if item["label"].startswith("Provider quota")]
    account_quota = [item for item in telemetry if item["label"].startswith("Account quota")]
    if live["present"] and live["quota_available"]:
        account_quota = [item for item in telemetry if item["label"].startswith("Reported account limit")]
    pid = actual_pid(state)
    pid_state = process_liveness(pid)
    pid_identity = process_identity(pid) if pid_state == "alive" else pid_state
    pid_present = pid_state == "alive"
    runtime = runtime_projection(
        task_marked_executing,
        pid_state,
        live["present"],
        live["updated_at"],
        pid_identity=pid_identity,
    )
    process_exited = runtime["process_exited"]
    status_label = STATUS_LABELS.get(known_status, "Unknown state")
    if task_marked_executing and pid_state == "alive" and pid_identity == "other":
        status_label = "记录的PID当前对应其他进程，Claude状态待核实"
    elif process_exited:
        status_label = "Claude进程已退出，任务状态待收尾"
    elif task_marked_executing and pid is None:
        status_label = "任务标记执行中，尚未记录PID"
    elif task_marked_executing and pid_state == "unknown":
        status_label = "任务标记执行中，PID状态无法确认"
    elif task_marked_executing and pid_state == "alive" and pid_identity == "claude" and not runtime["telemetry_fresh"]:
        status_label = "记录PID对应Claude Code，状态遥测已过期"
    telemetry_source = "statusline" if live["present"] else "execution-report" if report_metrics else "none"
    if review["status"] == "passed":
        status_label = "正文修订已由Codex复核（当前版本）"

    return {
        "task_id": task_id,
        "status": known_status,
        "status_label": status_label,
        "times": {
            "created": safe_timestamp(state.get("created_at")),
            "updated": safe_timestamp(state.get("updated_at")),
            "prepared": prepared,
            "execution_started": started,
            "execution_finished": finished,
            "collected": collected_at,
        },
        "lifecycle": {
            "prepared": bool(prepared),
            "executing": task_marked_executing,
            "process_exited": process_exited,
            "execution_started": bool(started),
            "returned": bool(finished) or known_status in {"returned", "execution_interrupted"},
            "collected": has_collection,
            "pending_codex_review": pending_review,
        },
        "launch": {
            "model": live["model"] or safe_model(report),
            "actual_pid": pid,
            "pid_present": pid_present,
            "pid_state": pid_state,
            "pid_identity": pid_identity,
            "execution_started_at": started,
            "execution_finished_at": finished,
            "exit_code": exit_code,
            "execution_report_present": has_execution,
            "execution_report_state": report_state,
        },
        "allowed_paths": allowed,
        "changed": safe_changed_paths(collection, report, allowed),
        "codex_review": review,
        "telemetry": telemetry,
        "telemetry_source": telemetry_source,
        "telemetry_snapshot_present": live["present"],
        "telemetry_updated_at": live["updated_at"],
        "telemetry_age_seconds": runtime["telemetry_age_seconds"],
        "telemetry_fresh": runtime["telemetry_fresh"],
        "telemetry_stale": runtime["telemetry_stale"],
        "telemetry_max_age_seconds": MAX_STATUSLINE_AGE_SECONDS,
        "telemetry_live": runtime["telemetry_live"],
        "provider_quota_available": bool(provider_quota),
        "account_quota_available": bool(account_quota),
    }


def codex_review_projection(record: Dict[str, Any], collection: Dict[str, Any], source_hash: Optional[str]) -> Dict[str, Any]:
    status = "missing"
    if record.get("status") == "passed":
        expected = record.get("source_sha256")
        clean = collection.get("status") == "awaiting_codex_review" and collection.get("acceptance") == "pending_codex_review"
        clean = clean and all(collection.get(key) == [] for key in (
            "out_of_scope_changes", "unexpected_package_files", "protected_package_changes", "executor_report_errors"
        ))
        if not clean:
            status = "collection_incomplete"
        elif not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected) or source_hash is None:
            status = "unverified"
        else:
            status = "passed" if expected == source_hash else "stale"
    labels = {
        "missing": "等待Codex复核",
        "passed": "当前正文版本已复核；Word/PDF须另行验收",
        "stale": "正文已变化，既有复核须更新",
        "unverified": "复核版本无法核验",
        "collection_incomplete": "回收存在异常，尚不能显示复核通过",
    }
    return {"status": status, "label": labels[status], "reviewed_at": safe_timestamp(record.get("reviewed_at"))}


INDEX_HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Thesis blueprint handoffs</title>
  <style>
    :root { color-scheme: light; --ink:#182230; --muted:#667085; --line:#e4e7ec; --blue:#175cd3; --green:#067647; --amber:#b54708; --bg:#f8fafc; }
    * { box-sizing:border-box; }
    body { margin:0; background:var(--bg); color:var(--ink); font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }
    main { max-width:1100px; margin:0 auto; padding:28px 20px 52px; }
    header { display:flex; justify-content:space-between; align-items:flex-end; gap:16px; margin-bottom:22px; }
    h1 { font-size:25px; margin:0 0 4px; letter-spacing:-.02em; }
    h2 { font-size:16px; margin:0 0 14px; }
    p { margin:0; }
    .muted,.hint { color:var(--muted); font-size:13px; }
    .controls { display:flex; align-items:center; gap:10px; flex-wrap:wrap; }
    select,button { font:inherit; color:var(--ink); border:1px solid #cfd4dc; border-radius:8px; padding:9px 11px; background:white; }
    button { cursor:pointer; }
    .card { background:white; border:1px solid var(--line); border-radius:12px; padding:18px; margin:14px 0; box-shadow:0 1px 2px #1018280a; }
    .topline { display:flex; justify-content:space-between; align-items:flex-start; gap:16px; }
    .taskid { overflow-wrap:anywhere; color:var(--muted); font-size:13px; }
    .badge { display:inline-block; padding:5px 9px; background:#eff8ff; color:#175cd3; border-radius:99px; font-weight:600; font-size:13px; white-space:nowrap; }
    .grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:10px; }
    .step { border:1px solid var(--line); border-radius:9px; padding:12px; min-height:92px; }
    .step strong { display:block; font-size:13px; margin-bottom:6px; }
    .step span { color:var(--muted); font-size:13px; }
    .step.done { border-color:#abefc6; background:#f6fef9; }
    .step.active { border-color:#b2ddff; background:#f5faff; }
    .step.warning { border-color:#fedf89; background:#fffaeb; }
    .columns { display:grid; grid-template-columns:1fr 1fr; gap:14px; }
    ul { margin:0; padding-left:20px; }
    li { margin:5px 0; overflow-wrap:anywhere; }
    .empty { color:var(--muted); font-style:italic; }
    .facts { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:12px 20px; }
    .fact dt { color:var(--muted); font-size:12px; margin-bottom:2px; }
    .fact dd { margin:0; overflow-wrap:anywhere; }
    .notice { padding:10px 12px; border-radius:8px; background:#fffaeb; color:#93370d; font-size:13px; margin-top:12px; }
    .notice.live { background:#ecfdf3; color:#05603a; }
    .notice.stale { background:#fff1f3; color:#b42318; }
    .error { color:#b42318; }
    @media(max-width:760px) { header,.topline { align-items:flex-start; flex-direction:column; } .grid { grid-template-columns:1fr 1fr; } .columns,.facts { grid-template-columns:1fr; } }
  </style>
</head>
<body>
<main>
  <header>
      <div><h1>论文修订协作面板</h1><p class="muted">本机只读页面 · 页面每5秒刷新；statusline更新按其自身回调</p></div>
    <div class="controls"><label for="task-select">任务</label><select id="task-select" aria-label="选择任务"></select><button id="refresh" type="button">刷新</button></div>
  </header>
  <p id="message" class="muted" role="status">正在读取任务列表…</p>
  <section id="dashboard" hidden>
    <article class="card topline">
      <div><div id="task-id" class="taskid"></div><p id="status-line" style="margin-top:8px"></p></div>
      <span id="status-badge" class="badge"></span>
    </article>
    <section class="card">
      <h2>任务流程状态</h2>
      <div class="grid" id="lifecycle"></div>
      <p class="hint" style="margin-top:12px">回收报告只表示Claude已交回文件，仍须Codex复核；本面板不代表验收通过。</p>
    </section>
    <section class="card">
      <h2>启动凭据</h2>
      <dl class="facts" id="launch-facts"></dl>
    </section>
    <div class="columns">
      <section class="card"><h2>本任务允许修改的文件</h2><ul id="allowed-paths"></ul></section>
      <section class="card"><h2>实际变更文件</h2><p id="changed-source" class="hint" style="margin-bottom:8px"></p><ul id="changed-paths"></ul><p id="out-of-scope" class="hint" style="margin-top:10px"></p></section>
    </div>
    <section class="card">
      <h2>时间记录</h2>
      <dl class="facts" id="times"></dl>
    </section>
    <section class="card">
      <h2>Token与额度信息</h2>
      <ul id="telemetry"></ul>
      <p id="telemetry-freshness" class="notice" role="status"></p>
      <p id="quota-note" class="hint"></p>
    </section>
  </section>
</main>
<script>
(() => {
  const select = document.getElementById('task-select');
  const dashboard = document.getElementById('dashboard');
  const message = document.getElementById('message');
  let requestNumber = 0;

  function text(node, value) { node.textContent = value == null ? '' : String(value); }
  function clear(node) { while (node.firstChild) node.removeChild(node.firstChild); }
  function itemList(node, items, emptyText) {
    clear(node);
    if (!items || !items.length) {
      const li = document.createElement('li');
      li.className = 'empty'; li.textContent = emptyText; node.appendChild(li); return;
    }
    items.forEach(value => { const li = document.createElement('li'); li.textContent = String(value); node.appendChild(li); });
  }
  function factList(node, pairs) {
    clear(node);
    pairs.forEach(([label, value]) => {
      const wrap = document.createElement('div'); wrap.className = 'fact';
      const dt = document.createElement('dt'); dt.textContent = label;
      const dd = document.createElement('dd'); dd.textContent = value == null ? 'Not recorded' : String(value);
      wrap.append(dt, dd); node.appendChild(wrap);
    });
  }
  function step(parent, label, state, className) {
    const box = document.createElement('div'); box.className = 'step ' + className;
    const strong = document.createElement('strong'); strong.textContent = label;
    const span = document.createElement('span'); span.textContent = state;
    box.append(strong, span); parent.appendChild(box);
  }
  async function loadTasks() {
    const previous = select.value;
    const response = await fetch('/api/tasks', { cache:'no-store' });
    if (!response.ok) throw new Error('无法读取任务列表');
    const data = await response.json();
    clear(select);
    data.tasks.forEach(id => { const option = document.createElement('option'); option.value = id; option.textContent = id; select.appendChild(option); });
    if (data.tasks.includes(previous)) select.value = previous;
    if (!data.tasks.length) { dashboard.hidden = true; message.textContent = '没有找到含状态记录的任务目录。'; return; }
    await loadTask();
  }
  async function loadTask() {
    const id = select.value;
    if (!id) return;
    const currentRequest = ++requestNumber;
    const response = await fetch('/api/task?id=' + encodeURIComponent(id), { cache:'no-store' });
    if (!response.ok) throw new Error('无法读取所选任务');
    const data = await response.json();
    if (currentRequest !== requestNumber) return;
    dashboard.hidden = false; message.textContent = '';
    text(document.getElementById('task-id'), data.task_id);
    text(document.getElementById('status-badge'), data.status_label);
    text(document.getElementById('status-line'), data.status_label);

    const steps = document.getElementById('lifecycle'); clear(steps);
    step(steps, '任务包已准备', data.lifecycle.prepared ? '准备于 ' + (data.times.prepared || '已记录') : '尚未记录', data.lifecycle.prepared ? 'done' : '');
    let executingText;
    let executingClass = '';
    if (data.lifecycle.process_exited) {
      executingText = data.launch.pid_identity === 'other'
        ? '记录的PID当前对应其他进程，无法确认原Claude仍运行'
        : 'Claude进程已退出，等待任务状态写入退出码/回收';
      executingClass = 'warning';
    } else if (data.lifecycle.executing) {
      if (data.launch.pid_state === 'alive' && data.launch.pid_identity === 'claude') {
        if (data.telemetry_live) {
          executingText = 'Claude Code进程已核验，状态遥测在更新';
          executingClass = 'active';
        } else {
          executingText = '记录PID对应Claude Code；遥测已过期，无法判断正在执行还是等待权限/输入';
          executingClass = 'warning';
        }
      } else if (data.launch.pid_state === 'unknown') {
        executingText = data.launch.actual_pid == null ? '任务标记执行中，尚无PID记录' : '任务标记执行中，PID状态无法确认';
        executingClass = 'warning';
      } else if (data.launch.pid_state === 'alive') {
        executingText = 'PID存在，但进程名称未能核验为Claude Code';
        executingClass = 'warning';
      } else {
        executingText = '任务标记执行中，尚未确认进程';
        executingClass = 'warning';
      }
    } else {
      executingText = data.times.execution_finished ? 'Claude已结束' : data.lifecycle.execution_started ? 'Claude已启动，当前非执行状态' : '尚未记录';
      if (data.lifecycle.execution_started) executingClass = 'done';
    }
    step(steps, 'Claude是否启动/运行', executingText, executingClass);
    step(steps, '任务是否回收', data.lifecycle.collected ? '已生成回收报告' : data.lifecycle.returned ? '执行已返回，尚无回收报告' : '尚未记录', data.lifecycle.collected ? 'done' : '');
    const review = data.codex_review || {};
    step(steps, 'Codex复核', data.lifecycle.collected ? (review.label || '等待Codex复核') : '尚未收到回收报告', review.status === 'passed' ? 'done' : data.lifecycle.pending_codex_review ? 'active' : '');

    const launch = data.launch;
    factList(document.getElementById('launch-facts'), [
      ['会话报告的模型名', launch.model || '尚未报告'],
      ['Claude进程PID', launch.actual_pid == null ? '尚未记录' : launch.actual_pid],
      ['本机进程检查', launch.pid_identity === 'claude' ? 'PID对应Claude Code可执行程序' : launch.pid_identity === 'other' ? 'PID对应其他程序' : launch.pid_state === 'absent' ? '该PID已不存在' : '无法核验进程身份'],
      ['实际启动时间', launch.execution_started_at],
      ['实际结束时间', launch.execution_finished_at],
      ['Claude退出码', launch.exit_code],
      ['执行报告', launch.execution_report_state === 'filled' ? '已填写' : launch.execution_report_state === 'partial' ? '部分填写' : launch.execution_report_state === 'template' ? '文件存在但仍为空白模板' : '尚未生成'],
    ]);
    itemList(document.getElementById('allowed-paths'), data.allowed_paths, '未记录允许修改的文件。');
    itemList(document.getElementById('changed-paths'), data.changed.paths, '暂未发现授权范围内的修改。');
    text(document.getElementById('changed-source'), data.changed.source);
    text(document.getElementById('out-of-scope'), data.changed.out_of_scope_count ? data.changed.out_of_scope_count + ' out-of-scope changed path(s) recorded; paths are hidden.' : '');
    factList(document.getElementById('times'), [
      ['任务创建', data.times.created], ['状态更新', data.times.updated], ['任务准备', data.times.prepared],
      ['Claude启动', data.times.execution_started], ['Claude结束', data.times.execution_finished], ['文件回收', data.times.collected],
      ['最新状态遥测', data.telemetry_updated_at],
      ['状态快照年龄', data.telemetry_age_seconds == null ? null : data.telemetry_age_seconds + ' 秒' + (data.telemetry_stale ? ' · 已过期' : '')],
    ]);

    const metrics = (data.telemetry || []).map(metric => metric.label + ': ' + metric.value);
    let emptyTelemetryText;
    if (data.telemetry_snapshot_present) {
      emptyTelemetryText = '最近的statusline快照没有包含可显示的用量字段。';
    } else if (data.telemetry_source === 'execution-report') {
      emptyTelemetryText = '执行报告没有包含明确的数值用量字段。';
    } else {
      emptyTelemetryText = '本任务尚无statusline或报告用量遥测。';
    }
    itemList(document.getElementById('telemetry'), metrics, emptyTelemetryText);

    const freshness = document.getElementById('telemetry-freshness');
    freshness.className = 'notice';
    if (data.telemetry_snapshot_present) {
      const ageText = data.telemetry_age_seconds == null ? '年龄无法确认' : '最后收到于 ' + data.telemetry_age_seconds + ' 秒前';
      if (data.telemetry_live) {
        freshness.classList.add('live');
        freshness.textContent = 'Live statusline snapshot · ' + ageText + '. 页面每5秒刷新；statusline回调频率独立。';
      } else if (data.telemetry_stale) {
        freshness.classList.add('stale');
        freshness.textContent = 'Last statusline snapshot · ' + ageText + '（阈值 ' + data.telemetry_max_age_seconds + ' 秒）。以下数值保留供参考，当前不视为实时。';
      } else if (data.lifecycle.process_exited) {
        freshness.textContent = 'Last statusline snapshot · ' + ageText + '。Claude进程已退出，以下是最后观测值，不代表最终账单。';
      } else if (!data.lifecycle.executing) {
        freshness.textContent = 'Last statusline snapshot · ' + ageText + '。任务当前不在执行状态，以下不是实时用量。';
      } else {
        freshness.classList.add('stale');
        freshness.textContent = 'Last statusline snapshot · ' + ageText + '。PID未确认存活，以下数值不视为实时。';
      }
    } else if (data.telemetry_source === 'execution-report') {
      freshness.textContent = '以下数值来自execution-report.json，是报告记录值，不是实时状态行快照。';
    } else {
      freshness.textContent = '未记录statusline快照；页面刷新不会产生新的遥测数据。';
    }

    const quotaParts = [];
    if (!data.provider_quota_available) quotaParts.push('服务商额度：当前会话未提供。');
    if (!data.account_quota_available) quotaParts.push('账户额度：当前服务商/会话未提供。');
    if (data.provider_quota_available || data.account_quota_available) quotaParts.push('额度只显示明确记录的rate_limits或报告字段；statusline额度来自Claude Code提供的快照，并非独立服务商查询。');
    quotaParts.push('Token反映上下文/会话字段，不等于账户累计用量；费用是客户端估算值。');
    text(document.getElementById('quota-note'), quotaParts.join(' '));
  }
  async function refresh() {
    try { await loadTasks(); }
    catch (error) { dashboard.hidden = true; message.className = 'error'; message.textContent = error.message; }
  }
  select.addEventListener('change', () => loadTask().catch(error => { message.className='error'; message.textContent=error.message; }));
  document.getElementById('refresh').addEventListener('click', refresh);
  refresh();
  window.setInterval(refresh, 5000);
})();
</script>
</body>
</html>
"""


class DashboardHandler(BaseHTTPRequestHandler):
    server_version = "ThesisBlueprintDashboard/1.0"

    def log_message(self, format: str, *args: Any) -> None:
        # Keep request paths and local task identifiers out of terminal logs.
        return

    def _send(self, status: int, content_type: str, payload: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; connect-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; object-src 'none'; base-uri 'none'",
        )
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler interface
        try:
            if not ipaddress.ip_address(self.client_address[0]).is_loopback:
                self._send(403, "text/plain; charset=utf-8", b"Local access only")
                return
        except ValueError:
            self._send(403, "text/plain; charset=utf-8", b"Local access only")
            return

        parsed = urlsplit(self.path)
        if parsed.path == "/" and not parsed.query:
            self._send(200, "text/html; charset=utf-8", INDEX_HTML.encode("utf-8"))
            return
        if parsed.path == "/api/tasks":
            body = json.dumps({"tasks": task_ids()}, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            self._send(200, "application/json; charset=utf-8", body)
            return
        if parsed.path == "/api/task":
            values = parse_qs(parsed.query, keep_blank_values=False).get("id", [])
            result = task_projection(values[0]) if len(values) == 1 else None
            if result is None:
                self._send(404, "application/json; charset=utf-8", b'{"error":"Task not found"}')
                return
            body = json.dumps(result, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")
            self._send(200, "application/json; charset=utf-8", body)
            return
        self._send(404, "text/plain; charset=utf-8", b"Not found")


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve a read-only thesis blueprint handoff dashboard.")
    parser.add_argument("--port", type=int, default=8765, help="loopback TCP port (default: 8765; use 0 for an ephemeral port)")
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error("--port must be between 0 and 65535")
    try:
        server = ThreadingHTTPServer(("127.0.0.1", args.port), DashboardHandler)
    except OSError as exc:
        parser.error("cannot bind 127.0.0.1:{} ({})".format(args.port, exc))
    host, port = server.server_address
    print("Read-only thesis dashboard at http://{}:{}/ (Ctrl-C to stop)".format(host, port))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDashboard stopped.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
