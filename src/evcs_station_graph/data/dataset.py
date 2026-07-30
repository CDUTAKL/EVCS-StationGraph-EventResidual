"""预测窗口数据集与预测键生成。

滑动窗口样本结构：给定一个预测起点 ``origin_index``（时间索引），
- 历史窗口：``[origin - history_steps + 1, origin]`` 共 ``history_steps`` 个时间步
- 预测目标：``[origin + 1, origin + forecast_steps]`` 共 ``forecast_steps`` 个时间步

每个样本的键为 ``(split, origin_index, horizon, node_id)`` 四元组，
保证每条预测可追溯至具体时间点和节点。
"""

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


class NodeWindowDataset(Dataset):  # type: ignore[type-arg]
    """按预测起点惰性切片，避免在磁盘上复制大量重叠窗口。

    设计决策：不在构建时预标准化 features/targets，而是在 __getitem__ 中
    动态标准化。这样 TensorBundle 中的原始值仍可用于事件分数计算和图构建，
    而模型看到的始终是标准化后的数据。

    每个样本包含：
    - ``x``：形状 ``[history_steps, N, F]`` 的标准化特征窗口
    - ``y``：形状 ``[forecast_steps, N]`` 的标准化目标
    - ``target_event``：形状 ``[forecast_steps, N]`` 的布尔事件标签
    - ``origin_index``：预测起点的全局时间索引（用于查找触发规则）
    """

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
        # 历史窗口包含预测起点本身：[origin - H + 1, origin]（闭区间）
        # 这对应"使用截至当前时刻的已知信息预测未来"的因果设定
        start = origin - self.spec.history_steps + 1
        stop = origin + 1
        # 预测目标为紧接预测起点的 H 个未来时间步：(origin, origin + H]
        future = slice(origin + 1, origin + 1 + self.spec.forecast_steps)
        # 使用预计算的标准化参数动态归一化，保持原始 TensorBundle 不变
        x = self.features[start:stop]
        y = self.targets[future]
        target_event = self.bundle.event_labels[future]
        # ascontiguousarray 确保 PyTorch 可以直接接管内存而不触发复制
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
    """生成与逐点预测严格一一对应的长表键。

    主键为 ``(split, origin_index, horizon, node_id)`` 四元组，保证每条预测
    可追溯到具体的预测起点时间、预测步长和目标节点。跨实验比较前必须先验证
    键集合一致（行数、hash_sum、hash_xor），避免因切分差异导致的不可比。

    返回的 DataFrame 包含以下辅助列：
    - ``forecast_origin``：预测起点的实际时间戳
    - ``target_index`` / ``target_time``：预测目标的时间索引和实际时间戳
    - ``node_index``：节点在特征张量第三维的位置
    """
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
