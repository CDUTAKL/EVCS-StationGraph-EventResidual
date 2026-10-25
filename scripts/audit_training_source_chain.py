#!/usr/bin/env python3
"""Verify and index the frozen source-to-results chain for SG-EXP-031/032."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tarfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def verify_dir_manifest(root: Path, manifest_path: Path) -> dict:
    manifest = json.loads(manifest_path.read_text())
    mismatches = []
    verified = 0
    for name, expected in manifest.items():
        path = root / name
        if not path.is_file():
            mismatches.append({"path": name, "reason": "missing"})
        else:
            actual = sha256_file(path)
            if actual != expected:
                mismatches.append({"path": name, "reason": "sha256_mismatch", "expected": expected, "actual": actual})
            else:
                verified += 1
    return {
        "manifest_path": rel(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "entries": len(manifest),
        "entries_verified": verified,
        "status": "PASS" if not mismatches and verified == len(manifest) else "FAIL",
        "mismatches": mismatches,
    }


def verify_tar_manifest(archive: Path, manifest_member: str) -> dict:
    mismatches = []
    with tarfile.open(archive, "r:gz") as tf:
        member = tf.extractfile(manifest_member)
        if member is None:
            raise FileNotFoundError(f"manifest not in archive: {manifest_member}")
        manifest_bytes = member.read()
        manifest = json.loads(manifest_bytes)
        for name, expected in manifest.items():
            candidate = manifest_member.rsplit("/", 1)[0] + "/" + name
            file_member = tf.extractfile(candidate)
            if file_member is None:
                mismatches.append({"path": candidate, "reason": "missing"})
                continue
            actual = sha256_bytes(file_member.read())
            if actual != expected:
                mismatches.append({"path": candidate, "reason": "sha256_mismatch", "expected": expected, "actual": actual})
        git_identity_members = [
            name for name in tf.getnames()
            if name.endswith(("git-head.txt", "git-commit.txt", "working-tree.patch"))
        ]
        git_identity = {}
        for name in git_identity_members:
            item = tf.extractfile(name)
            data = item.read() if item else b""
            git_identity[name] = {
                "sha256": sha256_bytes(data),
                "content": data.decode("utf-8", "replace")[:500],
                "bytes": len(data),
            }
    return {
        "archive_path": rel(archive),
        "archive_sha256": sha256_file(archive),
        "manifest_member": manifest_member,
        "manifest_sha256": sha256_bytes(manifest_bytes),
        "entries": len(manifest),
        "entries_verified": len(manifest) - len(mismatches),
        "status": "PASS" if not mismatches else "FAIL",
        "mismatches": mismatches,
        "git_identity_files": git_identity,
    }


def verify_run_manifests(run_root: Path) -> dict:
    runs = []
    failures = []
    for manifest_path in sorted(run_root.rglob("manifest.json")):
        run_dir = manifest_path.parent
        manifest = json.loads(manifest_path.read_text())
        checks = []
        for name, expected in manifest.items():
            path = run_dir / name
            actual = sha256_file(path) if path.is_file() else None
            checks.append({
                "path": name,
                "expected_sha256": expected,
                "actual_sha256": actual,
                "passed": actual == expected,
            })
            if actual != expected:
                failures.append(rel(manifest_path) + ":" + name)
        run_summary_path = run_dir / "run_summary.json"
        run_summary = json.loads(run_summary_path.read_text()) if run_summary_path.exists() else {}
        runs.append({
            "manifest_path": rel(manifest_path),
            "manifest_sha256": sha256_file(manifest_path),
            "run_summary_path": rel(run_summary_path) if run_summary_path.exists() else None,
            "status": run_summary.get("status"),
            "model": run_summary.get("model", run_summary.get("variant")),
            "seed": run_summary.get("seed"),
            "best_epoch": run_summary.get("best_epoch"),
            "file_count": len(manifest),
            "files": checks,
        })
    return {
        "runs": len(runs),
        "files_verified": sum(r["file_count"] for r in runs) - len(failures),
        "files_expected": sum(r["file_count"] for r in runs),
        "status": "PASS" if runs and not failures else "FAIL",
        "mismatches": failures,
        "run_manifests": runs,
    }


def tracked(path: str) -> bool:
    result = subprocess.run(
        ["git", "ls-files", "--error-unmatch", path],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def build(output: Path) -> dict:
    e31 = Path("outputs/experiments/SG-EXP-031")
    e32 = Path("outputs/experiments/SG-EXP-032")
    e31_bundle = e31 / "bundle"
    e31_results = e31 / "recovered/results/SG-EXP-031"
    e32_results = e32 / "recovered/closeout/closeout/results/formal"
    e31_bundle_archive = e31 / "SG-EXP-031-bundle.tar.gz"
    e31_result_archive = e31 / "SG-EXP-031-results.tar.gz"
    e32_bundle_archive = e32 / "upload/SG-EXP-032-bundle.tar.gz"
    e32_result_archive = e32 / "recovered/SG-EXP-032-results.tar.gz"
    e31_audit = Path("outputs/analysis/SG-EXP-031-audit-20261015/audit.json")
    e32_audit = Path("outputs/analysis/SG-EXP-032-target-audit/audit.json")

    e31_entry = Path("scripts/jpl_relation_controls.py")
    e32_entry = Path("scripts/completion_target_sensitivity.py")

    e31_dir_manifest = verify_dir_manifest(e31_bundle, e31_bundle / "BUNDLE_MANIFEST.json")
    e32_tar_manifest = verify_tar_manifest(e32_bundle_archive, "workspace/BUNDLE_MANIFEST.json")
    e31_run_chain = verify_run_manifests(e31_results / "jpl")
    e32_run_chain = verify_run_manifests(e32_results)

    e31_audit_json = json.loads((ROOT / e31_audit).read_text())
    e32_audit_json = json.loads((ROOT / e32_audit).read_text())
    e31_git_head = (e31_bundle / "metadata/git-head.txt").read_text().strip()
    e31_worktree_patch = e31_bundle / "metadata/working-tree.patch"

    report = {
        "audit_id": "TRAINING-SOURCE-CHAIN-20261021",
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "audit_script": {
            "path": rel(Path(__file__).resolve()),
            "sha256": sha256_file(Path(__file__).resolve()),
        },
        "status": "PASS" if all([
            e31_dir_manifest["status"] == "PASS",
            e32_tar_manifest["status"] == "PASS",
            e31_run_chain["status"] == "PASS",
            e32_run_chain["status"] == "PASS",
            e31_audit_json.get("status") == "POST_HOC_DIAGNOSTIC",
            e32_audit_json.get("status") == "PASS",
        ]) else "FAIL",
        "experiments": {
            "SG-EXP-031": {
                "source_commit_recorded": e31_git_head,
                "working_tree_patch_bytes": e31_worktree_patch.stat().st_size,
                "entrypoint": {
                    "path": e31_entry.as_posix(),
                    "sha256": sha256_file(ROOT / e31_entry),
                    "matches_frozen_bundle": sha256_file(ROOT / e31_entry) == json.loads((e31_bundle / "BUNDLE_MANIFEST.json").read_text()).get("scripts/jpl_relation_controls.py"),
                    "git_tracked": tracked(e31_entry.as_posix()),
                },
                "training_code_sha256": e31_audit_json["frozen_bundle"]["training_code_sha256"],
                "training_plan_sha256": e31_audit_json["frozen_bundle"]["training_plan_sha256"],
                "data_sha256": e31_audit_json["dataset_sha256"],
                "original_graph_sha256": e31_audit_json["frozen_bundle"]["original_graph_sha256"],
                "result_archive": {"path": e31_result_archive.as_posix(), "sha256": sha256_file(ROOT / e31_result_archive)},
                "bundle_archive": {"path": e31_bundle_archive.as_posix(), "sha256": sha256_file(ROOT / e31_bundle_archive)},
                "bundle_manifest": e31_dir_manifest,
                "result_audit": {"path": e31_audit.as_posix(), "sha256": sha256_file(ROOT / e31_audit), "status": e31_audit_json.get("status"), "source_checksum_entries_verified": e31_audit_json.get("source_checksum_entries_verified"), "test_keys_per_run": e31_audit_json.get("prediction_alignment", {}).get("prediction_keys_per_run"), "run_count": len(e31_audit_json.get("run_rows", []))},
                "checkpoint_and_prediction_manifests": e31_run_chain,
            },
            "SG-EXP-032": {
                "source_commit_recorded": None,
                "source_commit_note": "Frozen training bundle has no git-head/commit identity file; exact source entrypoint and dependency files are identified by file hashes in the bundle manifest.",
                "entrypoint": {
                    "path": e32_entry.as_posix(),
                    "sha256": sha256_file(ROOT / e32_entry),
                    "matches_frozen_bundle": sha256_file(ROOT / e32_entry) == verify_tar_manifest(e32_bundle_archive, "workspace/BUNDLE_MANIFEST.json")["git_identity_files"].get("workspace/scripts/completion_target_sensitivity.py", {}).get("sha256", None),
                    "git_tracked": tracked(e32_entry.as_posix()),
                },
                "entrypoint_bundle_sha256": "6bb968944a4db08cb3458cf0dbdd4b07c192ce5c31cbcdefad44b9cb945ad753",
                "data_sha256": e32_audit_json.get("data_sha256"),
                "frozen_config_sha256": sha256_file(ROOT / e32 / "frozen-contract/config_frozen.json"),
                "frozen_contract_manifest_sha256": sha256_file(ROOT / e32 / "frozen-contract/manifest.json"),
                "result_archive": {"path": e32_result_archive.as_posix(), "sha256": sha256_file(ROOT / e32_result_archive)},
                "bundle_archive": {"path": e32_bundle_archive.as_posix(), "sha256": sha256_file(ROOT / e32_bundle_archive)},
                "bundle_manifest": e32_tar_manifest,
                "result_audit": {"path": e32_audit.as_posix(), "sha256": sha256_file(ROOT / e32_audit), "status": e32_audit_json.get("status"), "verified_result_manifest_entries": e32_audit_json.get("verified_result_manifest_entries"), "test_keys_per_run": e32_audit_json.get("test_prediction_keys_per_run"), "run_count": e32_audit_json.get("run_count")},
                "checkpoint_and_prediction_manifests": e32_run_chain,
            },
        },
    }
    # Resolve the SG-EXP-032 source file hash directly from its frozen tar manifest.
    with tarfile.open(ROOT / e32_bundle_archive, "r:gz") as tf:
        member = tf.extractfile("workspace/BUNDLE_MANIFEST.json")
        manifest = json.loads(member.read())
        expected_entry = manifest.get("scripts/completion_target_sensitivity.py")
    report["experiments"]["SG-EXP-032"]["entrypoint"]["matches_frozen_bundle"] = (
        report["experiments"]["SG-EXP-032"]["entrypoint"]["sha256"] == expected_entry
    )
    report["experiments"]["SG-EXP-032"]["entrypoint_bundle_sha256"] = expected_entry
    report["status"] = "PASS" if all([
        report["experiments"]["SG-EXP-031"]["entrypoint"]["matches_frozen_bundle"],
        report["experiments"]["SG-EXP-032"]["entrypoint"]["matches_frozen_bundle"],
        report["experiments"]["SG-EXP-031"]["checkpoint_and_prediction_manifests"]["status"] == "PASS",
        report["experiments"]["SG-EXP-032"]["checkpoint_and_prediction_manifests"]["status"] == "PASS",
    ]) else "FAIL"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    report["report_path"] = rel(output)
    report["report_sha256"] = sha256_file(output)
    print(json.dumps({
        "status": report["status"],
        "report_path": report["report_path"],
        "report_sha256": report["report_sha256"],
        "sg031_run_files": report["experiments"]["SG-EXP-031"]["checkpoint_and_prediction_manifests"]["files_verified"],
        "sg032_run_files": report["experiments"]["SG-EXP-032"]["checkpoint_and_prediction_manifests"]["files_verified"],
        "sg031_entrypoint_matches_bundle": report["experiments"]["SG-EXP-031"]["entrypoint"]["matches_frozen_bundle"],
        "sg032_entrypoint_matches_bundle": report["experiments"]["SG-EXP-032"]["entrypoint"]["matches_frozen_bundle"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 2


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=Path("docs/thesis/revision-20261021-evidence/training-source-chain.json"))
    args = ap.parse_args()
    return build(args.output)


if __name__ == "__main__":
    raise SystemExit(main())
