#!/usr/bin/env python3
"""Render Claude Code status and persist only allowlisted usage telemetry.

Claude Code sends a statusline JSON snapshot on stdin. This adapter deliberately
discards prompts, paths, session identifiers, transcripts, and unknown fields.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


TASK_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{1,79}\Z")
MODEL_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/\-\[\]()+ ]{0,119}\Z")
MAX_INPUT_BYTES = 1_000_000
LIVE_DIR = Path(tempfile.gettempdir()) / "thesis-blueprint-live"


def number(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0:
        return value
    return None


def token_count(value: Any) -> Optional[int]:
    value = number(value)
    if value is None:
        return None
    return int(value)


def safe_model(value: Any) -> Optional[str]:
    if isinstance(value, str) and len(value) <= 120 and MODEL_RE.fullmatch(value):
        return value
    return None


def safe_reset(value: Any) -> Optional[str]:
    if not isinstance(value, str) or len(value) > 40:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.isoformat()


def snapshot(payload: Dict[str, Any]) -> Dict[str, Any]:
    model_data = payload.get("model")
    model = safe_model(model_data.get("display_name")) if isinstance(model_data, dict) else None
    context = payload.get("context_window")
    context = context if isinstance(context, dict) else {}
    usage = payload.get("current_usage")
    usage = usage if isinstance(usage, dict) else {}
    cost = payload.get("cost")
    cost = cost if isinstance(cost, dict) else {}

    result: Dict[str, Any] = {
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model": model,
    }
    fields = {
        "context_input_tokens": token_count(context.get("total_input_tokens")),
        "context_output_tokens": token_count(context.get("total_output_tokens")),
        "context_window_size": token_count(context.get("context_window_size")),
        "context_used_percent": number(context.get("used_percentage")),
        "current_input_tokens": token_count(usage.get("input_tokens")),
        "current_output_tokens": token_count(usage.get("output_tokens")),
        "cache_read_input_tokens": token_count(usage.get("cache_read_input_tokens")),
        "cache_creation_input_tokens": token_count(usage.get("cache_creation_input_tokens")),
        "estimated_cost_usd": number(cost.get("total_cost_usd")),
        "duration_ms": token_count(cost.get("total_duration_ms")),
    }
    result.update({key: value for key, value in fields.items() if value is not None})

    # Claude subscription/gateway rate limits are optional. DeepSeek-compatible
    # providers may omit them; absence must remain visible as unavailable.
    limits = payload.get("rate_limits")
    if isinstance(limits, dict):
        safe_limits: Dict[str, Dict[str, Any]] = {}
        for window in ("five_hour", "seven_day", "seven_day_sonnet", "seven_day_opus"):
            item = limits.get(window)
            if not isinstance(item, dict):
                continue
            values: Dict[str, Any] = {}
            used = number(item.get("used_percentage"))
            reset = safe_reset(item.get("resets_at"))
            if used is not None:
                values["used_percentage"] = used
            if reset is not None:
                values["resets_at"] = reset
            if values:
                safe_limits[window] = values
        if safe_limits:
            result["rate_limits"] = safe_limits
    return result


def write_snapshot(task_id: str, value: Dict[str, Any]) -> None:
    LIVE_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    if LIVE_DIR.is_symlink():
        raise OSError("telemetry directory must not be a symlink")
    try:
        LIVE_DIR.chmod(0o700)
    except OSError:
        pass
    target = LIVE_DIR / (task_id + ".json")
    temporary = LIVE_DIR / (task_id + ".json.tmp")
    data = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    with temporary.open("w", encoding="utf-8") as handle:
        os.chmod(temporary, 0o600)
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, target)


def display(value: Dict[str, Any]) -> str:
    parts = [value.get("model") or "Claude Code"]
    if "context_used_percent" in value:
        parts.append("上下文 {:.0f}%".format(value["context_used_percent"]))
    token_items = []
    if "context_input_tokens" in value:
        token_items.append("in {:,}".format(value["context_input_tokens"]))
    if "context_output_tokens" in value:
        token_items.append("out {:,}".format(value["context_output_tokens"]))
    if token_items:
        parts.append("上下文token " + "/".join(token_items))
    if "estimated_cost_usd" in value:
        parts.append("估算费用 ${:.4f}".format(value["estimated_cost_usd"]))
    limits = value.get("rate_limits", {})
    if limits:
        rendered = ["{} {:.0f}% used".format(name, item["used_percentage"]) for name, item in limits.items() if "used_percentage" in item]
        if rendered:
            parts.append("已报告额度 " + ", ".join(rendered))
    else:
        parts.append("额度不可用")
    return " | ".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", required=True)
    args = parser.parse_args()
    if not TASK_ID_RE.fullmatch(args.task):
        print("Claude Code状态不可用")
        return 0
    try:
        raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
        if len(raw) > MAX_INPUT_BYTES:
            raise ValueError("status payload too large")
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("status payload must be an object")
        current = snapshot(payload)
        write_snapshot(args.task, current)
        print(display(current))
    except Exception:
        # Statusline errors must not interfere with Claude Code itself.
        print("Claude Code进程状态正常 | token/额度遥测暂不可用")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
