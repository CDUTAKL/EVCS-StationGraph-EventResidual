# Project environment protection

- Treat `.venv/` as protected project state. Document/PDF/figure work never authorizes changing it. Do not delete, recreate, sync, upgrade, or install into it without an explicit environment maintenance task.
- Do not use bare `uv run`, `uv sync`, or `uv venv` in this repository for ad hoc tools. `uv run --with` can resolve the project and replace an incompatible existing environment.
- Prefer the bundled document runtime or an already verified interpreter. If a document tool needs temporary dependencies, use `uv run --no-project --no-config --python <explicit-verified-interpreter> --with <package> ...` from a temporary directory outside the repository. Never use the project `.venv` as the temporary tool environment.
- Before any authorized environment mutation, save interpreter identity, full package versions, metadata hashes, and a restorable backup; first build and verify a separate candidate environment. Never replace the sole working environment to test a hypothesis.
- Environment checks use explicit interpreter paths and `PYTHONDONTWRITEBYTECODE=1` or `-B`. `uv pip check --python .venv/bin/python` is read-only. Do not treat import success as experiment reproduction or evidence that versions match.
- Keep research environment snapshots distinct from document runtimes. Historical CUDA requirements must not be installed into a Mac environment.
- If an accidental environment change occurs, stop package operations, preserve the current state, locate historical snapshots, report exact differences, and distinguish compatibility verification from exact restoration.

# Thesis artifact lifecycle

- Keep one canonical manuscript source, one official DOCX, and one official PDF. The official binaries use the existing title-based filenames in `outputs/thesis/` and Git LFS; Git supplies their revision history.
- Routine edits reuse one task-scoped candidate directory. Do not create `v1`, `v2`, date-stamped copies, or extra full PDF renders for every iteration. A separately named deliverable requires an explicit request or a recorded milestone reason.
- Reuse the existing hash-bound incremental audit/cache for daily candidates. Final delivery still requires its full-page visual acceptance; an unreviewed page cannot inherit a pass merely because it was not selected by the impact index.
- Only an authorized finalization task may replace official artifacts. After their hashes and remote LFS availability are verified, remove task-created scratch copies; retain lightweight audit records and only backups required for recovery or cited evidence. Inventory and check references before deleting pre-existing files.
- Before publishing a new delivery, recheck the canonical source workspace against the frozen manuscript/figure inputs and confirm the active writing task has finished. A clean isolated checkout does not prove the shared source workspace is frozen.
