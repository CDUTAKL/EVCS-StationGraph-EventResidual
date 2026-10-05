#!/usr/bin/env python3
"""Build the allowlisted SG-EXP-028 upload tarball; refuses overwrite and raw-session inclusion."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = "SG-DATA-007-jpl-eventtime-v1"
DATA_SHA = "1bfc42fab6f127b2ec1735b3821bb272a444185f1861bfe95f489d15e78738af"


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def read(rel: str) -> bytes:
    return (ROOT / rel).read_bytes()


def build(out: Path) -> dict:
    out = out.resolve()
    if out.exists():
        raise FileExistsError(f"Refusing to overwrite existing upload package: {out}")
    data_rel = "outputs/visibility/SG-DATA-007-jpl-eventtime-v1/dataset.npz"
    dataset = read(data_rel)
    if sha_bytes(dataset) != DATA_SHA:
        raise ValueError("Frozen JPL tensor hash mismatch; package not created")
    freeze = json.loads(read("docs/thesis/JPL-validation-freeze-20261005.json"))
    if freeze.get("dataset_sha256") != DATA_SHA or freeze.get("protocol") != PROTOCOL:
        raise ValueError("Frozen JPL freeze record identity/hash mismatch")
    source_manifest = read("outputs/visibility/SG-DATA-007-jpl-eventtime-v1/manifest.json")
    if sha_bytes(source_manifest) != freeze.get("data_manifest_sha256"):
        raise ValueError("JPL source manifest differs from the frozen record")
    frozen_source_map = {
        "configs/data/SG-DATA-007-jpl-eventtime-v1.json": "configs/data/SG-DATA-007-jpl-eventtime-v1.json",
        "configs/experiments/SG-EXP-028-jpl-independent-site.json": "configs/experiments/SG-EXP-028-jpl-independent-site.json",
        "docs/thesis/SG-EXP-028-jpl-independent-site-validation.md": "docs/thesis/SG-EXP-028-jpl-independent-site-validation.md",
        "src/evcs_station_graph/eventtime/models.py": "src/evcs_station_graph/eventtime/models.py",
        "src/evcs_station_graph/eventtime/gate_control.py": "src/evcs_station_graph/eventtime/gate_control.py",
        "src/evcs_station_graph/eventtime/runner.py": "src/evcs_station_graph/eventtime/runner.py",
        "src/evcs_station_graph/models/graph.py": "src/evcs_station_graph/models/graph.py",
        "src/evcs_station_graph/models/tcn.py": "src/evcs_station_graph/models/tcn.py",
        "src/evcs_station_graph/models/common.py": "src/evcs_station_graph/models/common.py",
    }
    for frozen_path, expected in freeze["frozen_files"].items():
        source = frozen_source_map.get(frozen_path, frozen_path)
        if sha_bytes(read(source)) != expected:
            raise ValueError(f"Source no longer matches the frozen JPL design: {frozen_path}")

    files: dict[str, bytes] = {}
    def add(source: str, target: str | None = None) -> None:
        dest = target or source
        if dest in files:
            raise ValueError(f"Duplicate bundle path: {dest}")
        files[dest] = read(source)

    add("scripts/jpl_experiment.py")
    add("scripts/archive_jpl_run.py")
    add("cloud/jpl/run_autodl.sh")
    add("cloud/jpl/README.md")
    add("cloud/jpl/requirements.txt")
    add("docs/thesis/JPL-validation-freeze-20261005.json", "metadata/JPL-validation-freeze-20261005.json")
    add("docs/thesis/SG-EXP-028-jpl-independent-site-validation.md", "metadata/SG-EXP-028-validation.md")
    add("configs/data/SG-DATA-007-jpl-eventtime-v1.json", "configs/SG-DATA-007-data.json")
    add("configs/experiments/SG-EXP-028-jpl-independent-site.json", "configs/SG-EXP-028-experiment.json")
    add("outputs/visibility/SG-DATA-007-jpl-eventtime-v1/protocol.json", "metadata/SG-DATA-007-protocol.json")
    add("outputs/visibility/SG-DATA-007-jpl-eventtime-v1/manifest.json", "metadata/SG-DATA-007-source-manifest.json")
    add(data_rel, "data/jpl/dataset.npz")

    source_paths = [
        "src/evcs_station_graph/__init__.py",
        "src/evcs_station_graph/eventtime/__init__.py",
        "src/evcs_station_graph/eventtime/data.py",
        "src/evcs_station_graph/eventtime/runner.py",
        "src/evcs_station_graph/eventtime/models.py",
        "src/evcs_station_graph/eventtime/gate_control.py",
        "src/evcs_station_graph/eventtime/parallel.py",
        "src/evcs_station_graph/models/__init__.py",
        "src/evcs_station_graph/models/common.py",
        "src/evcs_station_graph/models/graph.py",
        "src/evcs_station_graph/models/tcn.py",
        "src/evcs_station_graph/jpl_eventtime/__init__.py",
        "src/evcs_station_graph/jpl_eventtime/data.py",
    ]
    for rel in source_paths:
        add(rel)

    # The generated manifest is deliberately excluded from its own member list.
    manifest = {name: sha_bytes(value) for name, value in sorted(files.items())}
    files["BUNDLE_PROVENANCE.json"] = (json.dumps({
        "experiment": "SG-EXP-028", "protocol": PROTOCOL,
        "status": "prepared_no_training_executed",
        "dataset_sha256": DATA_SHA,
        "raw_session_records_included": False,
        "api_token_or_credentials_included": False,
        "source_acquisition_manifest_sha256": sha_bytes(read("outputs/visibility/SG-DATA-007-jpl-eventtime-v1/manifest.json")),
        "test_predictions_included": False,
        "formal_training_authorized": False,
        "source_files": source_paths,
    }, indent=2, ensure_ascii=False) + "\n").encode()
    manifest = {name: sha_bytes(value) for name, value in sorted(files.items())}
    files["BUNDLE_MANIFEST.json"] = (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode()

    out.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(out, "w:gz", compresslevel=6) as archive:
        for name, value in sorted(files.items()):
            info = tarfile.TarInfo("evcs-jpl-sg-exp-028/" + name)
            info.size = len(value)
            info.mode = 0o755 if name.endswith(".sh") else 0o644
            info.mtime = 0
            archive.addfile(info, io.BytesIO(value))
    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    out.with_suffix(out.suffix + ".sha256").write_text(f"{digest}  {out.name}\n", encoding="utf-8")
    summary = {"archive": str(out), "sha256": digest, "bytes": out.stat().st_size,
               "files": len(files), "protocol": PROTOCOL, "training_performed": False,
               "test_predictions_created": False}
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "outputs/experiments/SG-EXP-028/package/SG-EXP-028-JPL-AutoDL.tar.gz")
    args = parser.parse_args()
    build(args.out)
