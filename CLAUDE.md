# Claude Code project rules

## Task entry

- Thesis writing and evidence work starts from a task blueprint in `docs/thesis/blueprints/tasks/<task-id>/blueprint.json`.
- The task packet `EXECUTION_PACKET.md` is the bounded, current instruction for that run. Read its selected evidence excerpts and named manuscript sections only; do not reconstruct current status from archived plans, old chats, or the full experiment registry.
- `docs/thesis/thesis-manuscript.md` is the canonical text source. The current research brief, claim-evidence map, experiment registry, and scoring publication status are the evidence console; the blueprint selects the relevant portions for each task.
- This is an execution handoff shared by the existing 12 workflow steps. Keep their stages, review gates, and scoring rules unchanged.
- For formal scoring, follow `docs/thesis/AGENTS.md` and the local scoring protocol. A revision task is not a scoring task unless the blueprint says so.

## Execution boundaries

- Read the repository `AGENTS.md` environment-protection rules. `.venv/` is protected state: no installation, sync, upgrade, deletion, or recreation during thesis/document tasks. Use a separate document runtime; never run bare `uv run --with` in this project. An environment-maintenance task requires a snapshot and restorable backup before any change, then validation in a separate candidate environment.

- Edit only paths listed in the blueprint. Do not stage, commit, tag, publish, or overwrite the official DOCX.
- Do not start training, remote jobs, network collection, or GPU work unless the blueprint explicitly authorizes that operation and defines its budget and evidence output.
- Do not change frozen data, labels, splits, metrics, results, citations, or claim scope unless the task names the change and its source evidence.
- Do not add or run tests unless the task requests verification. Run only the checks listed in the blueprint.
- Use only skills named in `blueprint.json` under `claude_skills`; Codex-global skills are not automatically available to Claude Code.
- Keep source data, credentials, SSH details, checkpoints, and generated experiment outputs out of task packets and Git.
- If evidence is missing, a requested edit would widen a claim, or work outside the allowed paths is necessary, stop and record the blocker in `execution-report.json`.
- `allowed_paths` is an audit constraint, not an OS-level file boundary. Do not modify `.git/`, `.claude/settings*.json`, credentials, or handoff control files; `collect` cannot detect writes to Git-ignored paths.
- Local Bash tasks require Claude Code 2.1.219+ for `sandbox.network.strictAllowlist`; older or unknown versions fail closed. `network_access_allowed=false` keeps `allowedDomains: []` plus `deniedDomains: ["*"]`; true puts only `network_domains` in `allowedDomains`.
- `WebFetch(domain:...)` allow rules and user/project `sandbox.network.allowedDomains` can widen the Bash sandbox allowlist. Declare every such host literally in `network_domains` or the launch fails closed. `strictAllowlist` does not gate WebSearch/WebFetch. Remote tasks do not use the local sandbox; `network_domains` is an authorization list, not a remote network ACL.
- Do not bypass permission prompts or use `--dangerously-skip-permissions`.
- Reuse the blueprint's single candidate output path. Do not create extra dated/numbered DOCX or PDF copies unless the task explicitly requests an archived deliverable. Official Word/PDF history is managed by Git LFS; Codex owns final acceptance and replacement.

## Skill resources

- `claude_skills` names resolve from `.claude/skills/<name>` then `~/.claude/skills/<name>`; symlinks are followed. Run `realpath ~/.claude/skills/<name>` before invoking skill-local scripts.
- Skill-local `scripts/...` and `references/...` paths are relative to the real skill directory. Kit-level scripts and `docs/thesis/...` references live under `~/Documents/Codex/EVCS-EventGraph-Thesis/files-mentioned-by-the-user-research/research-workflow-kit/`. Never assume a skill script exists under this project's `scripts/`.
- Naming a skill does not grant Bash. The blueprint must list the exact script command in `checks_to_run`; otherwise treat the skill as read-only guidance and record the blocker.
- When `claude_skills` is non-empty, the launcher adds the `Skill` tool and a generic `Skill` ask rule. Claude Code evaluates deny → ask → allow, and a matching ask rule takes precedence over allow; no `Skill(<name>)` allow rules are added because they cannot pre-approve under the generic ask. All Skill invocations, including listed skills, require manual confirmation. Unlisted skills are not hard-denied by name and may be invoked if the user approves; the "only listed skills" rule remains an instruction-level constraint.
- `cdut-professional-master-thesis-format` is unavailable until its missing `assets/cdut-professional-master-20230905.docx` is restored and provenance confirmed. Do not create placeholders or copy unconfirmed templates. On macOS, its PowerShell/Word finalization is unavailable; do not claim Word/PDF visual approval.
- Record the actual model identifier in `execution-report.json`; if the provider reports `unrecognized_model`, record the exact diagnostic under `unresolved` without guessing or replacing the model.

## Return contract

Before finishing, update the task's `execution-report.json` with the requested summary, changed paths, evidence used, checks performed, unresolved points, and any claim or number changes. Leave final acceptance to Codex review; do not mark the thesis score or delivery gate as passed.
