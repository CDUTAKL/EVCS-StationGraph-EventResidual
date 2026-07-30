"""数据张量、滑动窗口与预测键接口。

本模块负责把上游时间片长表转换为紧凑的 ``[T, N, F]`` 张量，并提供
惰性滑动窗口数据集。所有归一化统计量仅使用训练阶段可见数据拟合，
测试集不会反向影响预处理。

核心职责：
- ``build_tensor_artifact``：从上游 CSV 构建正式节点张量工件
- ``load_tensor_bundle``：将 .npz 文件恢复为内存中的 TensorBundle
- ``NodeWindowDataset``：按预测起点惰性切片，避免磁盘复制大量重叠窗口
- ``build_prediction_key_frame``：生成与逐点预测严格一一对应的长表键
"""

from evcs_station_graph.data.dataset import (
    NodeWindowDataset,
    WindowSpec,
    build_prediction_key_frame,
    iter_prediction_keys,
)
from evcs_station_graph.data.tensor import (
    TensorBundle,
    build_tensor_artifact,
    load_tensor_bundle,
    read_node_ids,
)

__all__ = [
    "NodeWindowDataset",
    "TensorBundle",
    "WindowSpec",
    "build_prediction_key_frame",
    "build_tensor_artifact",
    "iter_prediction_keys",
    "load_tensor_bundle",
    "read_node_ids",
]
