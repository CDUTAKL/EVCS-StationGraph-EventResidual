"""十五分钟节点负荷张量构建。

本模块只负责把上游时间片长表转换为紧凑的 ``[时间, 节点, 特征]`` 张量。
所有归一化统计量仅使用训练阶段可见数据拟合，测试集不会反向影响预处理。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from evcs_station_graph.reproducibility import sha256_file, write_json


@dataclass(frozen=True)
class TensorBundle:
    """内存中的节点时序张量及其元数据。

    本对象是研究管线的统一数据契约——所有模型训练和评价都从这里读取
    标准化后的特征、目标、事件标签和切分信息，不直接访问上游 CSV。

    各字段含义：
    - ``timestamps_ns``：形状 ``[T]`` 的 int64 纳秒时间戳
    - ``node_ids``：形状 ``[N]`` 的节点标识（spaceID 格式，如 CA-303）
    - ``feature_names``：特征名称元组，长度 ``F``，决定 ``features`` 的第三维语义
    - ``features``：形状 ``[T, N, F]`` 的**原始**特征（未标准化），用于事件分数计算和图构建
    - ``targets``：形状 ``[T, N]`` 的**原始**目标负荷（kWh/15min）
    - ``event_labels``：形状 ``[T, N]`` 的布尔事件标签，仅用于评价，不参与训练
    - ``split_origins``：三个切分的有效预测起点索引数组
    - ``feature_mean/std``：全局特征标准化参数（训练集拟合），形状 ``[F]``
    - ``target_mean/std``：per-node 目标标准化参数（训练集拟合），形状 ``[N]``

    设计决策：features/targets 保持原始值而不预标准化，是为了让事件分数计算
    和图构建直接使用物理量纲，而 NodeWindowDataset 在切片时动态标准化。
    """

    timestamps_ns: np.ndarray
    node_ids: np.ndarray
    feature_names: tuple[str, ...]
    features: np.ndarray
    targets: np.ndarray
    event_labels: np.ndarray
    split_origins: dict[str, np.ndarray]
    feature_mean: np.ndarray
    feature_std: np.ndarray
    target_mean: np.ndarray
    target_std: np.ndarray

    @property
    def timestamps(self) -> np.ndarray:
        """返回纳秒精度时间戳。"""
        return self.timestamps_ns.astype("datetime64[ns]")


def read_node_ids(path: str | Path) -> list[str]:
    """读取冻结节点清单，并保持文件中的顺序。"""
    table = pd.read_csv(path)
    if "node_id" not in table.columns:
        raise ValueError(f"节点清单缺少 node_id 列：{path}")
    nodes = table["node_id"].astype(str).tolist()
    if len(nodes) != len(set(nodes)):
        raise ValueError("节点清单存在重复 node_id")
    return nodes


def build_tensor_artifact(
    config: dict[str, Any],
    output_path: str | Path | None = None,
    metadata_path: str | Path | None = None,
    *,
    max_time_steps: int | None = None,
) -> tuple[Path, Path]:
    """从上游长表生成节点负荷张量并保存为 .npz 工件。

    处理流程：
    1. 从上游 CSV 按冻结节点清单过滤数据
    2. 验证时间×节点的笛卡尔积完整性（缺失值会导致后续窗口切片错误）
    3. 构建 ``[T, N, F]`` 特征张量和 ``[T, N]`` 目标/事件标签
    4. 仅使用训练集（前 train_end+1 个时间步）计算 z-score 标准化参数
    5. 保存张量、元数据和标准化参数到 .npz，并写出数据清单

    ``max_time_steps`` 仅供自动化测试和本地冒烟验证使用；正式数据构建必须为
    ``None``，以免把截断数据误当成正式实验输入。

    返回 (张量工件路径, 数据清单路径)。
    """
    paths = config["paths"]
    dataset = config["dataset"]
    project = config["project"]

    csv_path = Path(paths["upstream_timeslice_csv"]).expanduser().resolve()
    node_path = Path(paths["primary_node_list"]).expanduser().resolve()
    split_path = Path(dataset["split_manifest"]).expanduser().resolve()
    output = Path(output_path or paths["dataset_artifact"]).expanduser().resolve()
    metadata = Path(metadata_path or paths["dataset_metadata"]).expanduser().resolve()

    node_ids = read_node_ids(node_path)
    feature_names = tuple(dataset["feature_columns"])
    target_name = str(dataset["target_column"])
    event_columns = tuple(dataset["event"]["label_columns"])
    required = ["timestamp", "node_id", *dict.fromkeys((*feature_names, target_name, *event_columns))]

    chunks: list[pd.DataFrame] = []
    for chunk in pd.read_csv(csv_path, usecols=required, chunksize=500_000):
        selected = chunk.loc[chunk["node_id"].astype(str).isin(node_ids)].copy()
        if not selected.empty:
            selected["node_id"] = selected["node_id"].astype(str)
            chunks.append(selected)
    if not chunks:
        raise ValueError("上游时间片文件中未找到冻结节点")

    frame = pd.concat(chunks, ignore_index=True)
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="raise")
    frame = frame.sort_values(["timestamp", "node_id"], kind="stable")
    timestamps = np.sort(frame["timestamp"].unique())
    if max_time_steps is not None:
        timestamps = timestamps[:max_time_steps]
        frame = frame[frame["timestamp"].isin(timestamps)]

    expected_rows = len(timestamps) * len(node_ids)
    if len(frame) != expected_rows:
        raise ValueError(
            "节点时间笛卡尔积不完整："
            f"实际 {len(frame)} 行，预期 {expected_rows} 行"
        )

    time_index = pd.Index(timestamps)
    node_index = pd.Index(node_ids)
    frame["_t"] = time_index.get_indexer(frame["timestamp"])
    frame["_n"] = node_index.get_indexer(frame["node_id"])
    if (frame[["_t", "_n"]] < 0).any().any():
        raise ValueError("时间或节点索引构建失败")

    t_size, n_size, f_size = len(timestamps), len(node_ids), len(feature_names)
    features = np.zeros((t_size, n_size, f_size), dtype=np.float32)
    targets = np.zeros((t_size, n_size), dtype=np.float32)
    event_labels = np.zeros((t_size, n_size), dtype=np.bool_)
    row_t = frame["_t"].to_numpy()
    row_n = frame["_n"].to_numpy()
    features[row_t, row_n] = frame.loc[:, feature_names].to_numpy(np.float32)
    targets[row_t, row_n] = frame[target_name].to_numpy(np.float32)
    event_labels[row_t, row_n] = (
        frame.loc[:, event_columns].to_numpy(np.float32) > 0
    ).any(axis=1)

    split_origins = _load_split_origins(
        split_path,
        total_steps=t_size,
        history_steps=int(project["history_steps"]),
        forecast_steps=int(project["forecast_steps"]),
        truncated=max_time_steps is not None,
    )
    # ---- 归一化参数：仅使用训练集拟合 ----
    # 特征使用全局（跨时间、跨节点）z-score，目标使用 per-node z-score。
    # 这样设计的理由是：
    # - 特征全局标准化保留了不同节点的相对差异（节点 A 的系统性高负荷不会
    #   被 per-node 标准化抹平，图关系可以从这种差异中提取信息）
    # - 目标 per-node 标准化避免了负荷量级大的节点主导损失函数，使模型
    #   公平对待每个充电单元
    train_last = int(split_origins["train"][-1])
    fit_slice = slice(0, train_last + 1)
    feature_mean = features[fit_slice].mean(axis=(0, 1), dtype=np.float64).astype(np.float32)
    feature_std = features[fit_slice].std(axis=(0, 1), dtype=np.float64).astype(np.float32)
    feature_std = np.where(feature_std < 1e-6, 1.0, feature_std).astype(np.float32)
    target_mean = targets[fit_slice].mean(axis=0, dtype=np.float64).astype(np.float32)
    target_std = targets[fit_slice].std(axis=0, dtype=np.float64).astype(np.float32)
    target_std = np.where(target_std < 1e-6, 1.0, target_std).astype(np.float32)

    output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output,
        timestamps_ns=timestamps.astype("datetime64[ns]").astype(np.int64),
        node_ids=np.asarray(node_ids, dtype="U32"),
        feature_names=np.asarray(feature_names, dtype="U64"),
        features=features,
        targets=targets,
        event_labels=event_labels,
        train_origins=split_origins["train"],
        validation_origins=split_origins["validation"],
        test_origins=split_origins["test"],
        feature_mean=feature_mean,
        feature_std=feature_std,
        target_mean=target_mean,
        target_std=target_std,
    )

    manifest = {
        "artifact_id": "SG-DATA-005",
        "description": "15分钟节点代理负荷张量与冻结预测起点",
        "formal_data": max_time_steps is None,
        "source_csv": str(csv_path),
        "source_sha256": sha256_file(csv_path),
        "node_list": str(node_path),
        "node_list_sha256": sha256_file(node_path),
        "split_manifest": str(split_path),
        "split_manifest_sha256": sha256_file(split_path),
        "shape": {
            "time_steps": t_size,
            "nodes": n_size,
            "features": f_size,
        },
        "feature_names": list(feature_names),
        "target_name": target_name,
        "node_ids": node_ids,
        "time_start": str(timestamps[0]),
        "time_end": str(timestamps[-1]),
        "split_origin_counts": {key: int(len(value)) for key, value in split_origins.items()},
        "normalization": {
            "fit_scope": "train_only",
            "feature": "global_zscore_by_feature",
            "target": "per_node_zscore",
        },
        "semantic_boundary": (
            "load 为会话记录按15分钟重构的节点代理负荷，单位为 kWh/15min，"
            "不得表述为在线电表实测功率"
        ),
    }
    write_json(manifest, metadata)
    return output, metadata


def load_tensor_bundle(path: str | Path) -> TensorBundle:
    """读取节点张量工件。"""
    with np.load(Path(path).expanduser().resolve(), allow_pickle=False) as data:
        return TensorBundle(
            timestamps_ns=data["timestamps_ns"],
            node_ids=data["node_ids"],
            feature_names=tuple(data["feature_names"].tolist()),
            features=data["features"],
            targets=data["targets"],
            event_labels=data["event_labels"].astype(bool),
            split_origins={
                "train": data["train_origins"],
                "validation": data["validation_origins"],
                "test": data["test_origins"],
            },
            feature_mean=data["feature_mean"],
            feature_std=data["feature_std"],
            target_mean=data["target_mean"],
            target_std=data["target_std"],
        )


def _load_split_origins(
    path: Path,
    *,
    total_steps: int,
    history_steps: int,
    forecast_steps: int,
    truncated: bool,
) -> dict[str, np.ndarray]:
    """读取冻结切分清单或生成冒烟测试用切分。

    正式模式（truncated=False）：
        从 SG-DATA-002-node-screening.json 读取预定义的时间切分边界，
        确保所有实验使用完全相同的训练/验证/测试起源索引。

    截断模式（truncated=True）：
        在截断数据上按 60/20/20 比例划分，仅用于自动化测试。
        截断模式的切分与正式数据无关，结果标记为 implementation_smoke_only。
    """
    if truncated:
        valid = np.arange(history_steps - 1, total_steps - forecast_steps, dtype=np.int64)
        if len(valid) < 12:
            raise ValueError("冒烟数据至少需要 12 个有效预测起点")
        train_end = max(1, int(len(valid) * 0.6))
        val_end = max(train_end + 1, int(len(valid) * 0.8))
        return {
            "train": valid[:train_end],
            "validation": valid[train_end:val_end],
            "test": valid[val_end:],
        }

    payload = json.loads(path.read_text(encoding="utf-8"))
    output: dict[str, np.ndarray] = {}
    for source_name, target_name in (
        ("train", "train"),
        ("validation", "validation"),
        ("test", "test"),
    ):
        boundary = payload["split_boundaries"][source_name]
        values = np.arange(
            int(boundary["start_index"]),
            int(boundary["end_index"]) + 1,
            dtype=np.int64,
        )
        if values[0] < history_steps - 1 or values[-1] + forecast_steps >= total_steps:
            raise ValueError(f"{source_name} 切分超出张量可用范围")
        output[target_name] = values
    return output
