# Project environment protection

- Treat `.venv/` as protected project state. Document/PDF/figure work never authorizes changing it. Do not delete, recreate, sync, upgrade, or install into it without an explicit environment maintenance task.
- Do not use bare `uv run`, `uv sync`, or `uv venv` in this repository for ad hoc tools. `uv run --with` can resolve the project and replace an incompatible existing environment.
- Prefer the bundled document runtime or an already verified interpreter. If a document tool needs temporary dependencies, use `uv run --no-project --no-config --python <explicit-verified-interpreter> --with <package> ...` from a temporary directory outside the repository. Never use the project `.venv` as the temporary tool environment.
- Before any authorized environment mutation, save interpreter identity, full package versions, metadata hashes, and a restorable backup; first build and verify a separate candidate environment. Never replace the sole working environment to test a hypothesis.
- Environment checks use explicit interpreter paths and `PYTHONDONTWRITEBYTECODE=1` or `-B`. `uv pip check --python .venv/bin/python` is read-only. Do not treat import success as experiment reproduction or evidence that versions match.
- Keep research environment snapshots distinct from document runtimes. Historical CUDA requirements must not be installed into a Mac environment.
- If an accidental environment change occurs, stop package operations, preserve the current state, locate historical snapshots, report exact differences, and distinguish compatibility verification from exact restoration.
