# Thesis blueprint dashboard

From the project root, start the read-only dashboard with:

```bash
python3 scripts/thesis_blueprint_dashboard.py
```

Open the printed `http://127.0.0.1:8765/` address. Use the task selector to view an existing task; the page refreshes automatically every five seconds. Stop the server with `Ctrl-C`. To choose another loopback port, pass `--port 8766` (or another available port).

The server binds only to `127.0.0.1`. It reads only the task ID, known lifecycle timestamps/status, blueprint `allowed_paths`, collected in-scope changed paths, execution-report `model`, known numeric telemetry fields, a PID field from task state, and a small allowlisted statusline snapshot in the system temporary directory. It does not read or display prompts, execution packets, context snapshots, environment values, transcripts, arbitrary report text, or secrets. Paths are displayed as text. The dashboard never launches Claude Code and does not modify task files.

The task launcher records the Claude CLI child PID immediately after process creation and uses a task-specific statusline overlay for that session only; it does not edit the user's `~/.claude/settings.json` or change the configured provider. The statusline adapter stores only an allowlisted model display name, context/session token counters, context-window occupancy, client-reported estimated cost, duration, and optional reported rate-limit fields under the system temporary directory with owner-only permissions. It discards the original statusline payload and all unknown fields. The dashboard reports whether the recorded PID currently exists; this is an operating-system process check, not proof of provider-side completion.

Token and usage values appear from live Claude statusline telemetry when available, or from numeric fields explicitly recorded in `execution-report.json` (at the report level or under `usage`, `token_usage`, or `usage_metrics`). Context token counts are labeled as such; they are not presented as account-wide cumulative usage. Provider and account quota each show “not available” when the configured provider/session does not emit exact rate-limit fields. DeepSeek-compatible endpoints commonly omit Claude subscription quota data, so the dashboard will not infer it from token counts or cost. A reported cost is labeled as a client estimate.

The lifecycle view distinguishes preparation, an active `executing` state, execution return, collection, and the pending Codex review handoff. A collection report is a handoff record and does not mean that Codex accepted the work.
