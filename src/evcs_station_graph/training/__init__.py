"""统一训练入口。

本模块提供实验训练的统一接口，确保所有实验使用相同的训练循环、
评价协议和检查点格式。不同配置通过 ``config`` 字典驱动，避免
各实验自行复制训练逻辑。

核心入口：
- ``build_model``：根据配置字典创建模型，处理 SG-EXP-005 的检查点加载
- ``train_experiment``：按配置运行全部随机种子并汇总结果
- ``train_single_seed``：单种子训练循环，生成完整工件（模型、指标、预测文件）
"""

from evcs_station_graph.training.engine import train_experiment, train_single_seed
from evcs_station_graph.training.factory import build_model

__all__ = ["build_model", "train_experiment", "train_single_seed"]
