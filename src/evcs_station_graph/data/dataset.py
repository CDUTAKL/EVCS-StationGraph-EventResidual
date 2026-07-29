"""预测窗口数据集与预测键生成。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset

from evcs_station_graph.data.tensor import TensorBundle


@dataclass(frozen=True)
class WindowSpec:
    """滑动窗口定义。"""

    history_steps: int
    forecast_steps: int


class NodeWindowDataset(Dataset[dict[str, torch.Tensor]]):
    """按预测起点惰性切片，避免在磁盘上复制大量重叠窗口。"""

    def __init__(
        self,
        bundle: TensorBundle,
        split: str,
        spec: WindowSpec,
        *,
        max_samples: int | None = None,
    ) -> None:
        if split not in bundle.split_origins:
            raise KeyError(f"未知切分：{split}")
        self.bundle = bundle
        self.split = split
        self.spec = spec
        origins = bundle.split_origins[split]
        self.origins = origins[:max_samples] if max_samples is not None else origins
        self.features = (
            bundle.features - bundle.feature_mean[None, None, :]
        ) / bundle.feature_std[None, None, :]
        self.targets = (
            bundle.targets - bundle.target_mean[None, :]
        ) / bundle.target_std[None, :]

    def __len__(self) -> int:
        return len(self.origins)

    def __getitem__(self, index: int) -> dict[str, torch.Tensor]:
        origin = int(self.origins[index])
        start = origin - self.spec.history_steps + 1
        stop = origin + 1
        future = slice(origin + 1, origin + 1 + self.spec.forecast_steps)
        x = self.features[start:stop]
        y = self.targets[future]
        target_event = self.bundle.event_labels[future]
        return {
            "x": torch.from_numpy(np.ascontiguousarray(x)).float(),
            "y": torch.from_numpy(np.ascontiguousarray(y)).float(),
            "target_event": torch.from_numpy(np.ascontiguousarray(target_event)).bool(),
            "origin_index": torch.tensor(origin, dtype=torch.long),
        }


def build_prediction_key_frame(
    bundle: TensorBundle,
    split: str,
    forecast_steps: int,
    *,
    origins: np.ndarray | None = None,
) -> pd.DataFrame:
    """生成与逐点预测严格一一对应的长表键。"""
    selected_origins = bundle.split_origins[split] if origins is None else origins
    rows: list[dict[str, object]] = []
    timestamps = bundle.timestamps
    for origin in selected_origins:
        for horizon in range(1, forecast_steps + 1):
            target_index = int(origin) + horizon
            for node_index, node_id in enumerate(bundle.node_ids.tolist()):
                rows.append(
                    {
                        "split": split,
                        "origin_index": int(origin),
                        "forecast_origin": str(timestamps[int(origin)]),
                        "horizon": horizon,
                        "target_index": target_index,
                        "target_time": str(timestamps[target_index]),
                        "node_index": node_index,
                        "node_id": str(node_id),
                    }
                )
    frame = pd.DataFrame.from_records(rows)
    if frame.duplicated(["split", "origin_index", "horizon", "node_id"]).any():
        raise ValueError("预测键存在重复")
    return frame


def iter_prediction_keys(
    bundle: TensorBundle,
    split: str,
    forecast_steps: int,
) -> Iterator[tuple[int, int, str]]:
    """流式产生 ``(预测起点, 步长, 节点)``，用于大规模一致性检查。"""
    for origin in bundle.split_origins[split]:
        for horizon in range(1, forecast_steps + 1):
            for node_id in bundle.node_ids:
                yield int(origin), horizon, str(node_id)
