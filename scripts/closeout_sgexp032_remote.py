#!/usr/bin/env python3
"""Verify completed SG-EXP-032 artifacts and produce a checksummed remote archive."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import tarfile


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def jload(path):
    return json.loads(Path(path).read_text())


def verify_manifest(folder):
    manifest = jload(folder / "manifest.json")
    if not manifest:
        raise ValueError(f"empty manifest: {folder}")
    for name, expected in manifest.items():
        path = folder / name
        if not path.is_file() or sha(path) != expected:
            raise ValueError(f"manifest mismatch: {path}")
    return len(manifest)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--bundle-sha256", required=True)
    args = ap.parse_args()
    root = args.root.resolve()
    pid = int((root / "trainer.pid").read_text().strip())
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        pass
    else:
        raise SystemExit(f"Training process still exists: {pid}")

    log = (root / "train.log").read_text(errors="replace")
    completed_lines = [line for line in log.splitlines() if '"completed":' in line]
    if len(completed_lines) != 6:
        raise ValueError(f"Expected six completion records, got {len(completed_lines)}")
    if "Traceback (most recent call last)" in log:
        raise ValueError("Traceback found in training log")

    formal = root / "results/formal"
    run_artifacts = []
    for model in ("mrg_full", "tcn_wide"):
        for seed in (2024, 2025, 2026):
            folder = formal / model / f"seed-{seed}"
            nfiles = verify_manifest(folder)
            required = ("config_resolved.json", "environment.json", "environment.txt", "best.pt", "last.pt",
                        "train_log.json", "metrics.json", "predictions_tuning.npz",
                        "predictions_calibration.npz", "predictions_test.npz", "run_summary.json", "exit_code.txt")
            if any(not (folder / name).is_file() for name in required):
                raise ValueError(f"required artifact missing: {folder}")
            cfg, summary, metrics, history = (jload(folder / name) for name in
                                              ("config_resolved.json", "run_summary.json", "metrics.json", "train_log.json"))
            if cfg.get("experiment") != "SG-EXP-032" or cfg.get("model") != model or int(cfg.get("seed")) != seed:
                raise ValueError(f"run identity mismatch: {folder}")
            if summary.get("status") != "complete" or int(summary.get("best_epoch", 0)) != int(metrics["selected_epoch"]):
                raise ValueError(f"run did not complete or selected epoch mismatch: {folder}")
            if (folder / "exit_code.txt").read_text().strip() != "0":
                raise ValueError(f"per-run exit marker is not 0: {folder}")
            if int(cfg.get("max_epochs")) != 60 or int(cfg.get("patience")) != 8:
                raise ValueError(f"training budget mismatch: {folder}")
            best_from_log = min(history, key=lambda row: float(row["tuning_mae"]))
            if int(best_from_log["epoch"]) != int(summary["best_epoch"]):
                raise ValueError(f"selected checkpoint does not match tuning log: {folder}")
            if not (folder / "best.pt").stat().st_size or not (folder / "last.pt").stat().st_size:
                raise ValueError(f"empty checkpoint: {folder}")
            run_artifacts.append({"model": model, "seed": seed, "manifest_entries": nfiles,
                                  "best_epoch": int(summary["best_epoch"]), "stopped_epoch": len(history),
                                  "train_seconds": float(sum(row["seconds"] for row in history)),
                                  "run_manifest_sha256": sha(folder / "manifest.json"),
                                  "best_sha256": sha(folder / "best.pt"), "last_sha256": sha(folder / "last.pt"),
                                  "test_predictions_sha256": sha(folder / "predictions_test.npz")})

    frozen = root / "workspace-v3/workspace/outputs/experiments/SG-EXP-032/frozen-contract"
    if not frozen.is_dir():
        raise ValueError("frozen contract directory missing")
    bundle_manifest = jload(root / "workspace-v3/workspace/BUNDLE_MANIFEST.json")
    ws = root / "workspace-v3/workspace"
    for name, expected in bundle_manifest.items():
        path = ws / name
        if not path.is_file() or sha(path) != expected:
            raise ValueError(f"bundle manifest mismatch: {path}")
    if sha(root / "SG-EXP-032-bundle-v3.tar.gz") != args.bundle_sha256:
        raise ValueError("remote uploaded bundle SHA mismatch")

    closeout = root / "closeout"
    if closeout.exists():
        raise FileExistsError(f"refusing to overwrite closeout directory: {closeout}")
    closeout.mkdir()
    shutil.copytree(formal, closeout / "results/formal")
    shutil.copytree(root / "results/remote-cuda-smoke", closeout / "results/remote-cuda-smoke")
    shutil.copytree(frozen, closeout / "frozen-contract")
    shutil.copy2(root / "SG-EXP-032-bundle-v3.tar.gz", closeout / "SG-EXP-032-bundle-v3.tar.gz")
    shutil.copy2(root / "train.log", closeout / "train.log")
    shutil.copy2(root / "trainer.pid", closeout / "trainer.pid")
    for name in ("remote-preflight.txt", "pretraining-gpu-check.txt"):
        source = root / name
        if source.is_file():
            shutil.copy2(source, closeout / name)

    # This zero marker is written only after all six run summaries, exit markers,
    # selected epochs and artifact manifests have passed this closeout check.
    (closeout / "exit_code.txt").write_text("0\n")
    metadata = {
        "experiment": "SG-EXP-032", "status": "completed_and_remote_artifacts_verified",
        "exit_code": 0, "exit_code_basis": "all six formal runs have exit_code.txt=0, completed run summaries, matching tuning-selected epoch, valid per-run manifests, six train-log completion sentinels, no traceback, and trainer PID absent; SSH background shell wait status was not retained separately",
        "remote_host_label": "AutoDL user-started instance autodl-container-38a84e9a75-8c21d369",
        "bundle_archive_sha256": args.bundle_sha256,
        "bundle_manifest_entries_verified": len(bundle_manifest),
        "formal_run_count": len(run_artifacts), "runs": run_artifacts,
        "completed_log_records": len(completed_lines), "trainer_pid": pid,
        "training_start_check_utc": "2026-10-15T01:43:28Z",
        "training_end_closeout_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "remote_instance_left_online_until_local_recovery": True,
    }
    (closeout / "autodl_run_summary.json").write_text(json.dumps(metadata, indent=2) + "\n")

    checksum_lines = []
    for path in sorted(p for p in closeout.rglob("*") if p.is_file() and p.name != "checksums.sha256"):
        checksum_lines.append(f"{sha(path)}  ./{path.relative_to(closeout).as_posix()}")
    (closeout / "checksums.sha256").write_text("\n".join(checksum_lines) + "\n")
    for line in checksum_lines:
        expected, rel = line.split(maxsplit=1)
        if sha(closeout / rel.strip()[2:]) != expected:
            raise ValueError(f"post-write closeout checksum mismatch: {rel}")

    archive = root / "SG-EXP-032-results.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        for path in sorted(closeout.rglob("*")):
            tar.add(path, arcname="closeout/" + path.relative_to(closeout).as_posix(), recursive=False)
    archive_sha = sha(archive)
    (root / "SG-EXP-032-results.tar.gz.sha256").write_text(f"{archive_sha}  {archive.name}\n")
    print(json.dumps({"status": metadata["status"], "archive": str(archive),
                      "archive_sha256": archive_sha, "archive_bytes": archive.stat().st_size,
                      "files_in_checksums": len(checksum_lines), "runs": run_artifacts}, indent=2))


if __name__ == "__main__":
    main()
