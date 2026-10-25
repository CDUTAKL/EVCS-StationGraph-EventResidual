# Thesis task blueprint interface

This is a handoff interface used by the existing 12-step thesis workflow. It does not add a scoring rubric or a new research stage.

## Roles

- **Codex** reads the current evidence console, chooses the relevant sources and locators, writes the task objective, scope, locked claims, steps, and acceptance criteria, then reviews the returned changes.
- **Claude Code** executes only the prepared blueprint and returns a structured report. The local Claude Code default model is used; this project records the user's configured model as DeepSeek without overriding Claude Code's provider configuration.
- **The script** freezes selected evidence excerpts and the workspace baseline, writes the compact execution packet, launches Claude Code when requested, and reports the actual file changes. It never accepts the work, changes scores, or commits files.

## Task lifecycle

```text
new -> edit blueprint -> validate -> prepare -> execute Claude Code -> collect -> Codex review -> accepted by task owner
```

The prepared packet contains only the selected console excerpts, evidence excerpts, allowed paths, named Claude Code skills, and task instructions. Put a skill's exact directory name in `claude_skills`; validation checks its `SKILL.md`, frontmatter, and referenced local resources, and the launcher exposes Claude Code's `Skill` tool only when a skill is named. Codex skills are not automatically installed in Claude Code. `markdown_heading` locators select one heading and its body; `line_range` uses one-based inclusive lines; `whole_file` is for short sources only. Each source and the selected skill's `SKILL.md` plus every referenced local resource are frozen by SHA-256 and rechecked before launch.

`collect` compares the workspace with the task-start snapshot, including a repository that was already dirty. It hashes task-allowed files and uses size/mtime fingerprints for files that were already dirty outside the task scope. It also reports paths changed by any post-baseline commit. This keeps large pre-existing deliverables from being reread; detected out-of-scope changes are surfaced for review. The launcher uses a per-session settings overlay, manual permission mode, disables plugins enabled in user and project settings, and starts with `--strict-mcp-config` and no MCP config. Local shell work runs in a fail-closed sandbox (`sandbox.enabled`, `failIfUnavailable`, `allowUnsandboxedCommands: false`) and requires Claude Code 2.1.219+ for `sandbox.network.strictAllowlist`; older or unknown versions fail closed before launch. When `network_access_allowed` is false the network policy keeps `allowedDomains: []` and adds `deniedDomains: ["*"]`; when true it puts only the declared `network_domains` in `allowedDomains`. In both cases `strictAllowlist: true` makes unlisted hosts a deterministic deny rather than a prompt. `strictAllowlist` applies only to sandboxed Bash commands, not to WebSearch/WebFetch. Remote execution does not use the local sandbox, requires both `network_access_allowed=true` and a non-empty `network_domains` authorization list, and asks before every Bash command; that list is not a remote network ACL. Git mutations are denied unless explicitly allowed. The task's write-path list and post-run diff are audit controls, not an OS-level file boundary: Claude's native file tools still operate within the project workspace, and `collect` cannot see writes to Git-ignored paths. Codex must inspect every changed path. Do not run two write tasks at once in this shared worktree.

`allowed_paths` validation rejects the project root, root-level wildcards, `.git/`, `.claude/`, `.ssh/`, raw-data directories, credential-like filenames, the task package directory, `.gitignore`, and the handoff control files (`scripts/thesis_blueprint.py`, `docs/thesis/blueprints/`). These are fail-closed blueprint checks; they do not sandbox Claude's file tools. In particular, do not list Git-ignored paths as writable: `collect` uses `git ls-files --others --exclude-standard` and cannot detect changes there.

## Skill resolution and availability

`claude_skills` contains exact skill directory names. Validation resolves `.claude/skills/<name>/SKILL.md` in this project first, then `~/.claude/skills/<name>/SKILL.md`; symlinks are followed and the frontmatter `name` must match. The `SKILL.md` and every referenced local resource (`assets/`, `references/`, `scripts/`, `agents/`, `tests/`) are frozen by SHA-256 at `prepare` and rechecked before launch. A missing resource blocks `validate`/`prepare`; do not create empty placeholder files to make a skill pass.

Several skills are symlinks whose real roots are outside this repository. Resolve them before running any skill-local command:

| Skill | Real root / note |
|---|---|
| `research-paper-writing`, `research-results-analysis`, `research-data-availability`, `research-code-quality` | `~/Documents/Codex/EVCS-EventGraph-Thesis/files-mentioned-by-the-user-research/research-workflow-kit/skills/<name>`; kit-level scripts and `docs/thesis/...` references are under the kit root `~/Documents/Codex/EVCS-EventGraph-Thesis/files-mentioned-by-the-user-research/research-workflow-kit/` |
| `scipilot-figure-skill` | `~/.codex/skills/scipilot-figure-skill` |
| `cdut-professional-master-thesis-format` | `~/.claude/skills/cdut-professional-master-thesis-format` (real directory) |

Use `realpath ~/.claude/skills/<name>` and prefix script paths with the resolved root (for example, `<skill-root>/scripts/profile_data.py`). Do not run `python scripts/<skill-script>.py` from the project root; those scripts are not in this repository. Some skill prose names `docs/thesis/...` files that exist only in the kit; use the project copy when it exists (for example `docs/thesis/terminology-ledger.md`, `docs/thesis/data-availability.md`) and the kit copy otherwise (`nature-style-writing-checklist.md`, `paper-type-taxonomy.md`, `section-citation-map.md`, `evidence-promotion-policy.md`). State which copy was used in the execution report.

Naming a skill does not grant Bash. Bash is exposed only when `checks_to_run` is non-empty or training/remote execution is explicitly allowed. If a skill's workflow needs to run a script, put the exact command in `checks_to_run`; otherwise the skill can be loaded but its scripts cannot be executed.

When `claude_skills` is non-empty, the launcher adds the `Skill` tool to `--tools` and adds a generic `Skill` rule to `permissions.ask`. Claude Code evaluates permissions in the order deny → ask → allow, and a matching ask rule takes precedence over allow; specific rules do not override a generic rule. Therefore every Skill invocation, including the skills listed in the blueprint, requires manual confirmation. The launcher does not add `Skill(<name>)` allow rules because they would not pre-approve anything under the generic ask rule. Unlisted skills are not hard-denied by name: there is no built-in "deny every skill except this list" rule, and after the user approves the prompt an unlisted skill may still be invoked. The packet's "only listed skills" requirement remains an instruction-level constraint. The launcher does not disable all skills or deny the whole `Skill` tool.

`cdut-professional-master-thesis-format` is currently unavailable in this workspace: its `assets/cdut-professional-master-20230905.docx` reference template is missing, so validation fails closed. Candidate files named `1.成都理工大学专业学位硕士学位论文模板20230905(1).docx` exist under the kit's `outputs/thesis-docx/` and `tmp/10B-1-docx-assembly/` directories with different SHA-256 values; they were not copied or treated as authoritative. The owner must confirm provenance and install the exact expected asset before any template audit. Do not fabricate a template, copy an unconfirmed DOCX, or claim template comparison. The skill's finalization script is PowerShell/Word-COM based (`scripts/finalize_with_word.ps1`); this macOS machine has no `pwsh`/`powershell` and no Microsoft Word, so Word finalization and Word-rendered PDF approval are unavailable. LibreOffice (`soffice`) is installed, but a LibreOffice conversion is not equivalent to Word finalization and must not be reported as a completed Word/PDF visual audit.

### Local Bash network policy

`strictAllowlist` is set only when a local Bash sandbox is used. The launcher reads the local `claude --version`; if the version is below 2.1.219 or cannot be parsed, it aborts instead of silently falling back to prompt-based network handling.

Claude Code merges `WebFetch(domain:...)` allow rules and `sandbox.network.allowedDomains` from settings into the sandbox allowlist. The launcher therefore scans user, project, and project-local settings for those rules whenever a local Bash sandbox is used. Any rule not literally present in the blueprint's `network_domains` blocks launch (case-insensitive; a trailing dot is ignored). Matching is deliberately exact: a wildcard is not treated as covering a narrower declared host. Project-local `allowedDomains`/`WebFetch` rules are also left out of the allowlist when `strictAllowlist` is on, but the launcher still fails closed to avoid depending on that nuance. Managed/policy settings are outside the script's read set; if they add allowlist entries, the operator must verify them separately. Error messages report source labels and counts, not hostnames from `settings.local.json`.

`strictAllowlist` limits sandboxed Bash only. WebSearch/WebFetch remain governed by tool permissions and are not gated by `strictAllowlist`. Remote tasks do not use this sandbox; `network_domains` is an authorization list for the task and per-command approval, not a remote network ACL.

## Commands

From the repository root:

```bash
python3 scripts/thesis_blueprint.py new \
  --id REV-20261018-abstract \
  --title "Revise abstract and contribution statement" \
  --type content_revision \
  --stage 11

# Edit docs/thesis/blueprints/tasks/REV-20261018-abstract/blueprint.json:
# add workflow_stage, the exact manuscript/evidence sections, allowed paths,
# steps, and acceptance criteria. steps and acceptance_criteria must be non-empty.

python3 scripts/thesis_blueprint.py validate REV-20261018-abstract
python3 scripts/thesis_blueprint.py prepare REV-20261018-abstract
python3 scripts/thesis_blueprint.py execute REV-20261018-abstract
python3 scripts/thesis_blueprint.py collect REV-20261018-abstract

# Offline launch-config check: no model call, no network.
python3 scripts/thesis_blueprint.py self-check
```

`run <task-id>` performs prepare, interactive execution, and collection in sequence. It requires a terminal and the local `claude` command. It uses Claude Code's configured model/provider unless `--model` is supplied; the launcher does not override provider configuration. The model invocation, packet creation, and collection are automatic after the user starts the command. Permission prompts for shell, Git, and Web tools may require user input; remote commands always require approval. Local Bash tasks also require Claude Code 2.1.219+ for `strictAllowlist`; older or unknown versions fail closed before launch. The launcher never enables `--dangerously-skip-permissions`. If Claude Code is unavailable or a run is interrupted, use `prepare`, launch Claude Code manually with the generated `EXECUTION_PACKET.md`, then run `collect`.

`collect` writes `collection-report.json` with `awaiting_codex_review`, `scope_violation`, `baseline_changed`, or `report_incomplete` status. These are handoff states, not acceptance decisions. Codex reviews the task diff and report, updates only the relevant evidence/impact index, then uses the existing 12-step gates and, when requested, the existing cached scoring and release tools.

The launcher passes the task prompt as a positional argument before the variadic `--disallowedTools` option, so Claude receives the packet instruction automatically. In `execution-report.json`, `changed_paths` lists workspace edits relative to the project root; omit the report itself. For compatibility, collection tolerates the exact current task's report path if included. It does not exempt other task files, protected packet files, omitted workspace edits, or invented changes.

## Source selection rules

- Prefer a small heading or line range from `thesis-brief.md`, `claim-evidence-map.md`, `experiment-registry.md`, `data-availability.md`, or the scoring console, as appropriate to the task.
- Add the exact experiment report, source reading, or result audit required by the requested claim. Do not attach the entire experiment registry or archived review packet by default.
- For manuscript edits, include only the relevant heading(s) and the canonical manuscript path in `allowed_paths`.
- For score review, obey `docs/thesis/AGENTS.md`; the executor may prepare evidence but cannot publish a score.
- For DOCX/PDF work, list exact artifacts and checks. A generated or incrementally audited page is not visually approved until a person or Codex actually reviews it.
- If `network_access_allowed` is true, list only the required shell hosts in `network_domains`; WebSearch/WebFetch remain approval-gated. Domains listed without `network_access_allowed=true` are rejected. Any existing `WebFetch(domain:...)` allow rule or user/project `sandbox.network.allowedDomains` entry must also be declared literally in `network_domains`, or a local Bash launch fails closed. Remote execution also requires `network_access_allowed=true` and a non-empty `network_domains` host whitelist, and is always approval-gated.
- Record the actual Claude Code model identifier in `execution-report.json` under `model`; `user_reported_model` is only the operator's label. `collect` checks that `model` is non-empty but cannot verify it against the provider. If the provider returns `unrecognized_model`, record the exact model string and diagnostic under `unresolved`; do not guess or auto-replace the model.



## 交互任务停滞与语言修订恢复（2026-10-20）

`execute`当前使用manual交互权限；逐次Edit可能等待终端批准，Codex聊天中的确认不自动转发给Claude。PID存在或页面刷新不表示模型正在工作。发生停滞时先保留日志、正文和任务报告，核对最后的工具请求，不向不可见提示盲目输入确认。

对仅需文本建议的任务，本轮验证了无工具输出方式：禁用文件、命令、MCP、技能和网页工具，使用print输出，权限模式保持manual且潜在请求直接拒绝；Codex随后核验并应用建议。临时safe-mode仅用于隔离插件与自动注入上下文，未修改用户级设置。LANGUAGE-006在102.4秒内完成并干净回收，详见`../revision-20261020-delivery/language-recovery/delivery-followup.md`。这不是默认execute的新增参数或自动代批功能。

Codex完成正文复核后，可在任务state.json中记录codex_review的status、source_sha256和reviewed_at；面板仅在干净回收且当前正文哈希一致时显示通过。该状态只对应正文版本，不能替代Word/PDF验收或正式评分。
