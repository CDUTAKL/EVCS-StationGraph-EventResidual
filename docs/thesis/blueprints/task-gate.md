# Blueprint task gate

`scripts/thesis_workflow.py` is the normal operator entry point for one existing 12-step task package. It checks `scripts/thesis_task_gate.py` at each controllable transition, then calls the existing `scripts/thesis_blueprint.py` command. The existing `execute` command may collect its report internally; the controller checks the resulting state immediately afterward and does not collect a second time. The controller itself never refreshes or overwrites a task baseline, scores the thesis, or exports DOCX/PDF. Only `run` and `execute` can start Claude Code; both require the task to pass the `READY_TO_EXECUTE` gate immediately before launch.

Run commands from the project root:

```sh
python3 scripts/thesis_workflow.py inspect REV-20261021-DATA-PROVENANCE
python3 scripts/thesis_workflow.py prepare REV-20261021-DATA-PROVENANCE
python3 scripts/thesis_workflow.py execute REV-20261021-DATA-PROVENANCE
python3 scripts/thesis_workflow.py collect REV-20261021-DATA-PROVENANCE
# One explicit command to advance a valid task through prepare and execution:
python3 scripts/thesis_workflow.py run REV-20261021-DATA-PROVENANCE
```

`inspect` only reads the package and working tree. `prepare` requires `READY_TO_PREPARE`, runs existing `validate` then `prepare`, and checks that the result is `READY_TO_EXECUTE`. `execute` runs only at `READY_TO_EXECUTE`; afterward it inspects the actual state. If that state is `READY_TO_COLLECT`, the single-step command stops there and reports the next step. `collect` runs only at `READY_TO_COLLECT`. `run` checks each visible transition, calls `collect` if execution leaves the task ready for collection, and stops on the first failed command or unexpected gate. If the task already awaits Codex review, `run` returns without changing it. It can start Claude only when explicitly invoked and only after all gates pass. All child stdout/stderr is inherited unchanged so interactive prompts remain visible. Afterward the controller prints each step's elapsed time; `--json` appends a structured timing and gate summary after the child output.

For a standalone read-only check, use `python3 scripts/thesis_task_gate.py TASK [--json]`. It checks blueprint validity, the baseline hash stored in `state.json`, protected packet hashes, source evidence hashes before execution, selected Claude skill and resource hashes before execution, current Git snapshot against the task baseline, allowed write paths, unexpected task-package files, and the collection report. It recommends only the next existing command or manual review.

Run `python3 scripts/thesis_workflow.py self-check` to exercise blocked, returned/interrupted, collected, and awaiting-review paths. The gate fixture uses a temporary package outside the project and removes it on exit; the controller fixture uses a fake command runner. It does not start a model or touch a real task package.

Gate results are deliberately limited:

| Gate | Meaning |
|---|---|
| `READY_TO_PREPARE` | The blueprint is valid and has no frozen baseline yet. Validate, then prepare. |
| `READY_TO_EXECUTE` | The prepared packet and workspace still match the frozen baseline. |
| `READY_TO_COLLECT` | Execution returned or was interrupted, and no collection report exists. The baseline and frozen package hashes still pass. A task still marked `executing` is blocked to prevent concurrent collection. |
| `AWAITING_CODEX_REVIEW` | Collection reports no scope violation, and the report still matches the observed changes. Codex must inspect the actual edits. |
| `REVIEW_REQUIRED` | A collection report exists but needs attention. |
| `BLOCKED` | A required file is missing, a hash or scope changed, or the state cannot be established safely. |

The gate does not verify scientific claims, hidden writes to ignored files, OS-level write isolation, Word/PDF layout, or visual acceptance. `AWAITING_CODEX_REVIEW` is only a handoff state; Codex must inspect the task diff and evidence before acceptance. Running `run` at this state returns successfully without repeating execution or collection.
