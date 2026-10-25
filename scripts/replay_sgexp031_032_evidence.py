#!/usr/bin/env python3
"""Minimal, non-destructive evidence package for SG-EXP-031/032.

Verifies the existing source/result archives and their internal manifests,
inventories configs/environments/checkpoints/predictions, and reruns the
existing independent saved-prediction metric audits into a fresh output
directory. It does not train, does not run checkpoint forward inference, and
does not reconstruct training.

Usage:
  python3 scripts/replay_sgexp031_032_evidence.py --out <package.json>
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
E31 = Path("outputs/experiments/SG-EXP-031")
E32 = Path("outputs/experiments/SG-EXP-032")
EXPECTED = {
    "SG-EXP-031": {
        "result_archive": (E31 / "SG-EXP-031-results.tar.gz",
                           "4eb436fbf30823d4df9b3e1be9f34652f849bdf7a130ce1c4229d9b2964f8c5f"),
        "bundle_archive": (E31 / "SG-EXP-031-bundle.tar.gz",
                           "5361c41a147592d0ea6bb14cd2282637f4906015a0dc76f4563d2b0e388b4d8a"),
        "bundle_manifest": E31 / "bundle/BUNDLE_MANIFEST.json",
        "bundle_manifest_sha256": "3ba32eee77da8bea6895804f5c4f1bf4924d3ff394b4aabce84c394fc482ee8b",
        "run_root": E31 / "recovered/results/SG-EXP-031/jpl",
        "runs": [(v, s) for v in ("full", "load_to_self", "event_to_self", "pattern_to_self")
                 for s in (2024, 2025, 2026)],
        "audit_script": "scripts/audit_sgexp031_results.py",
        "audit_source": E31 / "recovered/results/SG-EXP-031",
        "archived_audit": "outputs/analysis/SG-EXP-031-audit-20261015/audit.json",
        "entrypoint": "scripts/jpl_relation_controls.py",
        "entrypoint_sha256": "ac5f7a998ad198af30f07971f929b7abc43300e7aecb9e65e645d633920b9cba",
        "data_sha256": "1bfc42fab6f127b2ec1735b3821bb272a444185f1861bfe95f489d15e78738af",
    },
    "SG-EXP-032": {
        "result_archive": (E32 / "recovered/SG-EXP-032-results.tar.gz",
                           "b6f73aeb350db65f1d25ee59c19bcf8b316270049f46aaeee59ff971947670b3"),
        "bundle_archive": (E32 / "upload/SG-EXP-032-bundle.tar.gz",
                           "d53015b7de8150ad00efaa631449df57360c2987094c102e3f175561dee001df"),
        "bundle_manifest": E32 / "frozen-contract/manifest.json",
        "bundle_manifest_sha256": "e8f5b8498cc03f9c483a1a54991914ffb926d369595f3a553912298c6c1ea566",
        "run_root": E32 / "recovered/closeout/closeout/results/formal",
        "runs": [(m, s) for m in ("mrg_full", "tcn_wide") for s in (2024, 2025, 2026)],
        "audit_script": "scripts/audit_sgexp032_results.py",
        "audit_source": E32 / "recovered/closeout/closeout/results/formal",
        "archived_audit": "outputs/analysis/SG-EXP-032-target-audit/audit.json",
        "entrypoint": "scripts/completion_target_sensitivity.py",
        "entrypoint_sha256": "6bb968944a4db08cb3458cf0dbdd4b07c192ce5c31cbcdefad44b9cb945ad753",
        "data_sha256": "5802a65e2f7f0e045d54df3359eb52e9de73c5c6f4af06c67ada7db22747293f",
    },
}


def sha256_bytes(data: bytes) -> str:
    import hashlib

    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def normalize_member(name: str) -> str:
    return name[2:] if name.startswith("./") else name


def lookup(hashes: dict, name: str):
    name = normalize_member(name)
    if name in hashes:
        return hashes[name]
    matches = [value for key, value in hashes.items() if key.endswith("/" + name)]
    return matches[0] if len(matches) == 1 else None


def scan_tar(archive: Path) -> dict:
    hashes, checksums, checksum_member = {}, None, None
    with tarfile.open(archive, "r:gz") as handle:
        for member in handle:
            if not member.isfile():
                continue
            name = normalize_member(member.name)
            stream = handle.extractfile(member)
            if member.size <= 2_000_000:
                data = stream.read()
                hashes[name] = sha256_bytes(data)
                if name.split("/")[-1] == "checksums.sha256" and checksums is None:
                    checksums = data.decode("utf-8", "replace")
                    checksum_member = name
            else:
                digest = __import__("hashlib").sha256()
                for chunk in iter(lambda: stream.read(1 << 20), b""):
                    digest.update(chunk)
                hashes[name] = digest.hexdigest()
    return {"hashes": hashes, "checksums": checksums, "checksum_member": checksum_member}


def verify_checksums(archive: Path) -> dict:
    scanned = scan_tar(archive)
    text = scanned["checksums"]
    if text is None:
        return {"path": rel(archive), "sha256": sha256_file(archive), "status": "MISSING_CHECKSUM_LIST"}
    rows, mismatches = [], []
    base = scanned["checksum_member"].rsplit("/", 1)[0] + "/" if "/" in scanned["checksum_member"] else ""
    for line in text.splitlines():
        if not line.strip():
            continue
        expected, name = line.split(maxsplit=1)
        name = normalize_member(name.strip())
        actual = scanned["hashes"].get(name) or scanned["hashes"].get(base + name)
        if actual is None:
            actual = lookup(scanned["hashes"], name)
        rows.append({"path": name, "expected_sha256": expected, "actual_sha256": actual,
                     "passed": actual == expected})
        if actual != expected:
            mismatches.append(name)
    return {"path": rel(archive), "sha256": sha256_file(archive), "entries": len(rows),
            "verified": len(rows) - len(mismatches),
            "status": "PASS" if rows and not mismatches else "FAIL", "mismatches": mismatches}


def verify_bundle_tar(archive: Path, manifest_member: str) -> dict:
    scanned = scan_tar(archive)
    wanted = normalize_member(manifest_member)
    found = next((name for name in scanned["hashes"]
                  if name == wanted or name.split("/")[-1] == wanted.split("/")[-1]), None)
    if found is None:
        return {"archive_path": rel(archive), "archive_sha256": sha256_file(archive),
                "manifest_member": manifest_member, "status": "MISSING_MANIFEST"}
    manifest_bytes = None
    with tarfile.open(archive, "r:gz") as handle:
        for item in handle:
            if normalize_member(item.name) == found:
                manifest_bytes = handle.extractfile(item).read()
                break
    manifest = json.loads(manifest_bytes)
    base = found.rsplit("/", 1)[0] + "/" if "/" in found else ""
    mismatches = []
    for name, expected in manifest.items():
        target = base + name
        actual = lookup(scanned["hashes"], target)
        if actual != expected:
            mismatches.append({"path": target, "expected": expected, "actual": actual})
    return {"archive_path": rel(archive), "archive_sha256": sha256_file(archive),
            "manifest_member": found, "manifest_sha256": sha256_bytes(manifest_bytes),
            "entries": len(manifest), "verified": len(manifest) - len(mismatches),
            "status": "PASS" if not mismatches else "FAIL", "mismatches": mismatches}


def verify_dir_manifest(base: Path, manifest_path: Path) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    mismatches, verified = [], 0
    for name, expected in manifest.items():
        path = base / name
        actual = sha256_file(path) if path.is_file() else None
        if actual == expected:
            verified += 1
        else:
            mismatches.append({"path": name, "expected": expected, "actual": actual})
    return {"manifest_path": rel(manifest_path), "manifest_sha256": sha256_file(manifest_path),
            "entries": len(manifest), "verified": verified,
            "status": "PASS" if not mismatches and manifest else "FAIL", "mismatches": mismatches}


def inventory_run(run_dir: Path, label: str, seed: int) -> dict:
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    files, mismatches = [], []
    for name, expected in manifest.items():
        path = run_dir / name
        actual = sha256_file(path) if path.is_file() else None
        row = {"name": name, "bytes": path.stat().st_size if path.is_file() else None,
               "sha256": actual, "expected_sha256": expected, "passed": actual == expected}
        files.append(row)
        if actual != expected:
            mismatches.append(name)
    config = json.loads((run_dir / "config_resolved.json").read_text(encoding="utf-8"))
    environment = json.loads((run_dir / "environment.json").read_text(encoding="utf-8"))
    metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    summary = json.loads((run_dir / "run_summary.json").read_text(encoding="utf-8"))
    test = metrics.get("splits", {}).get("test", {})
    return {
        "label": label, "seed": seed, "path": rel(run_dir), "status": summary.get("status"),
        "best_epoch": summary.get("best_epoch"),
        "trainable_parameters": config.get("trainable_parameters"),
        "contract": {key: config.get(key) for key in
                     ("max_epochs", "patience", "batch_size", "lr", "weight_decay", "selection",
                      "dataset_sha256", "code_sha256")},
        "environment": {key: environment.get(key) for key in
                        ("python", "platform", "torch", "numpy", "cuda", "device", "gpu")},
        "checkpoint_sha256": {row["name"]: row["sha256"] for row in files if row["name"].endswith(".pt")},
        "prediction_sha256": {row["name"]: row["sha256"] for row in files if row["name"].startswith("predictions_")},
        "test_mae": test.get("mae"),
        "files": files, "status_manifest": "PASS" if not mismatches else "FAIL",
        "mismatches": mismatches,
    }


def run_audit(script: str, source: Path, out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=False)
    command = [sys.executable, str(ROOT / script), "--source", str(ROOT / source),
               "--out", str(out_dir), "--bootstrap-draws", "10000"]
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=1800)
    outputs = []
    for path in sorted(out_dir.rglob("*")):
        if path.is_file():
            outputs.append({"name": path.relative_to(out_dir).as_posix(),
                            "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    audit = None
    audit_path = out_dir / "audit.json"
    if audit_path.is_file():
        payload = json.loads(audit_path.read_text(encoding="utf-8"))
        audit = {
            "status": payload.get("status"),
            "source_checksum_entries_verified": payload.get("source_checksum_entries_verified"),
            "verified_result_manifest_entries": payload.get("verified_result_manifest_entries"),
            "run_count": payload.get("run_count", len(payload.get("run_rows", []))),
            "test_keys_per_run": payload.get("test_prediction_keys_per_run")
            or payload.get("prediction_alignment", {}).get("prediction_keys_per_run"),
            "primary_difference": payload.get("mean_paired_test_mae_difference_kwh_per_15min"),
        }
    return {"command": " ".join(command), "returncode": completed.returncode,
            "stdout_tail": completed.stdout.strip().splitlines()[-8:],
            "stderr_tail": completed.stderr.strip().splitlines()[-8:],
            "audit": audit, "outputs": outputs}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--audit-out", type=Path, default=None)
    args = parser.parse_args()

    use_temp = args.audit_out is None
    audit_root = Path(tempfile.mkdtemp(prefix="sgexp031-032-replay-")) if use_temp else args.audit_out
    if not use_temp:
        audit_root.mkdir(parents=True, exist_ok=True)
        if any(audit_root.iterdir()):
            raise SystemExit(f"Refusing to overwrite non-empty audit output directory: {audit_root}")

    report = {
        "audit_id": "SGEXP-031-032-REPLAY-20261022",
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "replay_script": {"path": rel(Path(__file__)), "sha256": sha256_file(Path(__file__))},
        "scope": {
            "does": ["verify archive and internal manifest hashes",
                     "recompute metrics from saved predictions",
                     "inventory configs, environments, checkpoints, and predictions"],
            "does_not": ["checkpoint forward inference", "retraining",
                         "training-process reconstruction", "network access"],
        },
        "privacy_and_access": [
            "Frozen archives preserve source code, processed inputs, run metadata, checkpoints, and saved predictions.",
            "No credentials, raw session records, or user identifiers are copied into this index.",
            "Local working-tree artifacts only; nothing is published or uploaded.",
        ],
        "commands": {
            "replay": "python3 scripts/replay_sgexp031_032_evidence.py --out <package.json>",
            "sg031_audit": "python3 scripts/audit_sgexp031_results.py --source <recovered-sg031> --out <fresh-empty-dir> --bootstrap-draws 10000",
            "sg032_audit": "python3 scripts/audit_sgexp032_results.py --source <formal-results> --out <fresh-empty-dir> --bootstrap-draws 10000",
        },
        "experiments": {},
    }

    all_ok = True
    for experiment, spec in EXPECTED.items():
        result_path, result_expected = spec["result_archive"]
        bundle_path, bundle_expected = spec["bundle_archive"]
        result_sha = sha256_file(ROOT / result_path)
        bundle_sha = sha256_file(ROOT / bundle_path)
        archive_ok = result_sha == result_expected and bundle_sha == bundle_expected
        all_ok = all_ok and archive_ok

        internal = verify_checksums(ROOT / result_path)
        if experiment == "SG-EXP-032":
            bundle_manifest = verify_bundle_tar(ROOT / bundle_path, "workspace/BUNDLE_MANIFEST.json")
            disk_manifest = verify_dir_manifest(ROOT / E32 / "frozen-contract", ROOT / spec["bundle_manifest"])
        else:
            bundle_manifest = verify_bundle_tar(ROOT / bundle_path, "BUNDLE_MANIFEST.json")
            disk_manifest = verify_dir_manifest(ROOT / E31 / "bundle", ROOT / spec["bundle_manifest"])

        manifest_ok = (internal["status"] == "PASS" and bundle_manifest["status"] == "PASS"
                       and disk_manifest["status"] == "PASS"
                       and disk_manifest["manifest_sha256"] == spec["bundle_manifest_sha256"])
        all_ok = all_ok and manifest_ok

        runs = []
        for label, seed in spec["runs"]:
            run_dir = ROOT / spec["run_root"] / label / f"seed-{seed}"
            runs.append(inventory_run(run_dir, label, seed))
        run_status = "PASS" if all(row["status_manifest"] == "PASS" for row in runs) else "FAIL"
        all_ok = all_ok and run_status == "PASS"

        entrypoint_sha = sha256_file(ROOT / spec["entrypoint"])
        entrypoint_ok = entrypoint_sha == spec["entrypoint_sha256"]
        all_ok = all_ok and entrypoint_ok

        audit_dir = audit_root / f"{experiment}-audit"
        audit = run_audit(spec["audit_script"], spec["audit_source"], audit_dir)
        audit_status = audit.get("audit", {}).get("status")
        audit_ok = audit["returncode"] == 0 and audit_status in {"PASS", "POST_HOC_DIAGNOSTIC"}
        all_ok = all_ok and audit_ok

        report["experiments"][experiment] = {
            "archives": {
                "result": {"path": rel(ROOT / result_path), "bytes": (ROOT / result_path).stat().st_size,
                           "sha256": result_sha, "expected_sha256": result_expected,
                           "hash_match": result_sha == result_expected},
                "bundle": {"path": rel(ROOT / bundle_path), "bytes": (ROOT / bundle_path).stat().st_size,
                           "sha256": bundle_sha, "expected_sha256": bundle_expected,
                           "hash_match": bundle_sha == bundle_expected},
            },
            "internal_result_checksums": internal,
            "bundle_manifest": bundle_manifest,
            "disk_manifest": disk_manifest,
            "source_identity": {
                "entrypoint": {"path": spec["entrypoint"], "sha256": entrypoint_sha,
                               "expected_sha256": spec["entrypoint_sha256"],
                               "matches_frozen_bundle": entrypoint_ok, "git_tracked": False},
                "data_sha256": spec["data_sha256"],
                "git_identity": (
                    {"recorded_commit": "fce67da891d95ae5021942e3e34fb088c1a9fc2a",
                     "working_tree_patch_bytes": (ROOT / E31 / "bundle/metadata/working-tree.patch").stat().st_size,
                     "limit": "Git commit identifies only the recorded baseline; the entrypoint was untracked and the working-tree patch was empty. Source identity is the frozen bundle manifest, not the commit alone."}
                    if experiment == "SG-EXP-031" else
                    {"recorded_commit": None,
                     "limit": "No verified historical Git commit is present in the frozen SG-EXP-032 bundle; source identity is the file-hash manifest only."}
                ),
            },
            "run_inventory": {"runs": len(runs), "status": run_status,
                              "files_expected": sum(len(row["files"]) for row in runs),
                              "files_verified": sum(sum(1 for f in row["files"] if f["passed"]) for row in runs),
                              "runs_detail": runs},
            "saved_prediction_replay": audit,
            "status": "PASS" if archive_ok and manifest_ok
            and run_status == "PASS" and entrypoint_ok and audit_ok else "FAIL",
        }

    if use_temp:
        shutil.rmtree(audit_root, ignore_errors=True)
        report["audit_output_directory"] = "temporary directory removed after hashing outputs"
    else:
        report["audit_output_directory"] = rel(audit_root)

    report["status"] = "PASS" if all_ok else "FAIL"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "out": args.out.as_posix(),
        "sg031_audit": report["experiments"]["SG-EXP-031"]["saved_prediction_replay"].get("audit"),
        "sg032_audit": report["experiments"]["SG-EXP-032"]["saved_prediction_replay"].get("audit"),
        "sg031_runs": report["experiments"]["SG-EXP-031"]["run_inventory"]["files_verified"],
        "sg032_runs": report["experiments"]["SG-EXP-032"]["run_inventory"]["files_verified"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
