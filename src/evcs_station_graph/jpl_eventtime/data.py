"""JPL-only frozen tensor loader; deliberately separate from legacy FrozenData."""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
from torch.utils.data import Dataset

DATA_SHA256 = "1bfc42fab6f127b2ec1735b3821bb272a444185f1861bfe95f489d15e78738af"
SCHEMA = "jpl-eventtime-v1-not-legacy-TensorBundle"
FEATURES = (
    "access_count", "departure_count", "active_count", "local_hour_sin",
    "local_hour_cos", "local_weekday_sin", "local_weekday_cos",
)
NODE_IDS = (
    "AG-1F08", "AG-1F10", "AG-1F06", "AG-1F13", "AG-1F02",
    "AG-1F04", "AG-1F01", "AG-1F12", "AG-1F07", "AG-1F03",
)
ORIGIN_COUNTS = {"train": 74168, "tuning": 7826, "calibration": 7828, "test": 15816}
STEP_NS = 15 * 60 * 1_000_000_000
HISTORY = 96
HORIZON = 4


def sha256(path: str | Path) -> str:
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def split_bounds(length: int) -> dict[str, tuple[int, int]]:
    return {
        "train": (0, int(length * 0.70)),
        "tuning": (int(length * 0.70), int(length * 0.775)),
        "calibration": (int(length * 0.775), int(length * 0.85)),
        "test": (int(length * 0.85), length),
    }


class FrozenJPLData:
    """Validate the exact SG-DATA-007 data contract and expose runner-compatible windows."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.digest = sha256(self.path)
        if self.digest != DATA_SHA256:
            raise ValueError("JPL frozen tensor SHA256 mismatch; refusing modified or legacy data")

        with np.load(self.path, allow_pickle=False) as archive:
            self.arrays = {key: archive[key] for key in archive.files}
        a = self.arrays
        required = {
            "timestamps_ns", "node_ids", "feature_names", "features", "targets",
            "label_available_at_ns", "target_event", "rule_trigger", "graphs",
            "rule_thresholds", "feature_mean", "feature_std", "target_mean",
            "target_std", "rule_std", "label_jump_threshold", "train_origins",
            "tuning_origins", "calibration_origins", "test_origins", "schema",
        }
        if set(a) != required:
            raise ValueError(f"JPL tensor key contract mismatch: missing={sorted(required-set(a))}, "
                             f"extra={sorted(set(a)-required)}")
        if str(a["schema"].item()) != SCHEMA:
            raise ValueError("Refusing a non-JPL or legacy tensor schema")

        t = len(a["timestamps_ns"])
        if t != 106096 or a["features"].shape != (t, 10, 7) or a["targets"].shape != (t, 10):
            raise ValueError("JPL tensor dimensions differ from frozen SG-DATA-007")
        if tuple(a["feature_names"].tolist()) != FEATURES or tuple(a["node_ids"].tolist()) != NODE_IDS:
            raise ValueError("Frozen JPL feature order or training-only node order mismatch")
        if a["label_available_at_ns"].shape != (t, 10):
            raise ValueError("JPL label-maturity matrix shape mismatch")
        if a["target_event"].shape != (t, 10) or a["rule_trigger"].shape != (t, 10):
            raise ValueError("JPL event/trigger masks shape mismatch")
        if a["graphs"].shape != (3, 10, 10) or a["rule_thresholds"].shape != (10,):
            raise ValueError("JPL relation graph or rule threshold shape mismatch")
        if a["feature_mean"].shape != (7,) or a["feature_std"].shape != (7,):
            raise ValueError("JPL feature scaler shape mismatch")
        if a["target_mean"].shape != (10,) or a["target_std"].shape != (10,):
            raise ValueError("JPL target scaler shape mismatch")
        if a["rule_std"].shape != (10, 3) or a["label_jump_threshold"].shape != ():
            raise ValueError("JPL rule-statistic shape mismatch")
        if not np.all(np.diff(a["timestamps_ns"]) == STEP_NS):
            raise ValueError("JPL UTC time grid is not a complete 15-minute sequence")

        numeric = ("features", "targets", "graphs", "feature_mean", "feature_std",
                   "target_mean", "target_std", "rule_std")
        if any(not np.isfinite(a[key]).all() for key in numeric):
            raise ValueError("JPL tensor contains nonfinite values")
        if np.any(a["feature_std"] <= 0) or np.any(a["target_std"] <= 0) or np.any(a["rule_std"] <= 0):
            raise ValueError("JPL frozen train-only scale contains a nonpositive value")

        bounds = split_bounds(t)
        train_end = bounds["train"][1]
        train_cutoff = int(a["timestamps_ns"][train_end])
        immature_fit = np.flatnonzero(np.any(a["label_available_at_ns"][:train_end] >= train_cutoff, axis=1))
        fit_end = int(immature_fit[0]) if len(immature_fit) else train_end
        self.fit_prefix_end = fit_end
        for split, (lo, hi) in bounds.items():
            key = f"{split}_origins"
            origins = a[key]
            if origins.ndim != 1 or origins.dtype.kind not in "iu":
                raise ValueError(f"Invalid origin array for {split}")
            if len(origins) != ORIGIN_COUNTS[split] or np.any(np.diff(origins) <= 0):
                raise ValueError(f"Frozen origin count/order mismatch for {split}")
            if np.any(origins - HISTORY + 1 < lo) or np.any(origins + HORIZON >= hi):
                raise ValueError(f"Window crosses a frozen {split} segment boundary")
            cutoff_ns = int(a["timestamps_ns"][hi]) if hi < t else int(a["timestamps_ns"][-1]) + STEP_NS
            for horizon in range(1, HORIZON + 1):
                if np.any(a["label_available_at_ns"][origins + horizon] >= cutoff_ns):
                    raise ValueError(f"Immature proxy labels found in {split}")
            if split == "train" and np.any(origins + HORIZON >= fit_end):
                raise ValueError("Training target extends beyond the mature scaler/graph fit prefix")

        self.x = ((a["features"] - a["feature_mean"]) / a["feature_std"]).astype(np.float32)
        self.y = ((a["targets"] - a["target_mean"]) / a["target_std"]).astype(np.float32)

    def windows(self, split: str, limit: int | None = None) -> "JPLWindows":
        if split not in ORIGIN_COUNTS:
            raise ValueError(f"Unknown split: {split}")
        return JPLWindows(self, split, limit)

    def masks(self, origins: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        idx = origins[:, None] + np.arange(1, HORIZON + 1)[None, :]
        target = self.arrays["target_event"][idx]
        trigger = np.repeat(self.arrays["rule_trigger"][origins, None, :], HORIZON, axis=1)
        return target, trigger


class JPLWindows(Dataset):
    def __init__(self, data: FrozenJPLData, split: str, limit: int | None = None):
        self.data = data
        origins = data.arrays[f"{split}_origins"]
        self.origins = origins if limit is None else origins[:limit]

    def __len__(self) -> int:
        return len(self.origins)

    def __getitem__(self, index: int):
        origin = int(self.origins[index])
        return (self.data.x[origin - HISTORY + 1:origin + 1],
                self.data.y[origin + 1:origin + HORIZON + 1], origin)
