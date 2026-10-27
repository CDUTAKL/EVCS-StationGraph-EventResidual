# Thesis artifact inventory and cleanup

`scripts/thesis_artifact_lifecycle.py` inventories one task-scoped directory below `outputs/thesis/candidate-*`. It reports file size, SHA-256, modification time, references found in repository Markdown/JSON/scripts, repeated hashes, and the official manuscript/DOCX/PDF locations that are protected. It does not inventory or delete `.git`, `.venv`, `data`, or `outputs/analysis`; reference scanning is limited to readable text records under `docs`, `scripts`, and `outputs/thesis`. It checks repository-relative, candidate-relative, candidate-relative suffix, absolute, home-relative, unique-filename, and SHA-256 references. When multiple files share a relative suffix, a reference conservatively protects each matching candidate. A missing text reference is only a review signal; it does not establish that a file is disposable.

## Preview

Use a temporary path for the preview so inventory does not add another repository artifact:

```sh
python3 scripts/thesis_artifact_lifecycle.py plan \
  --root outputs/thesis/candidate-current \
  --out /tmp/thesis-artifact-cleanup-plan.json
shasum -a 256 /tmp/thesis-artifact-cleanup-plan.json
```

Every entry defaults to `action: retain`. Exact same-hash copies without a detected path reference are marked `review_exact_duplicate`; other unreferenced files are marked `preserve_unreferenced_review`. Reports also include source files and matching lines. Hash-only citations are retained as evidence and do not make an otherwise unreferenced duplicate path irreplaceable when another identical copy remains.

## Explicit cleanup

Cleanup is limited to a manually selected exact duplicate. First inspect the entire plan and edit only the chosen entry's `action` from `retain` to `delete`. Then compute the SHA-256 of that edited plan and run a dry validation:

```sh
shasum -a 256 /tmp/thesis-artifact-cleanup-plan.json
python3 scripts/thesis_artifact_lifecycle.py apply \
  --plan /tmp/thesis-artifact-cleanup-plan.json \
  --plan-sha256 YOUR_SHA256_AFTER_REVIEW
```

The command above does not delete files. Deletion additionally requires `--execute`. Before unlinking, the tool checks the exact plan hash and the inventory-script hash, candidate-root boundary, regular-file status, size, SHA-256, modification time, current path references, the hash/size/time of every scanned reference record, and that an identical retained copy remains. It reruns the inventory and stops if a selected file or any scanned reference source has changed or gained a path reference. If the script changes after the preview, generate a new plan. Symlinks, canonical official files, non-duplicate files, and files outside the candidate root are never eligible.

The tool does not automatically decide whether historical audit artifacts remain useful. Keep evidence whose review context or recovery purpose is uncertain. In particular, do not remove files just because Git ignores them or Git does not track them.
