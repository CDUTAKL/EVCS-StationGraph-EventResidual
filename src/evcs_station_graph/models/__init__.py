"""预测模型公共导出。

本模块包含四个预测模型及其公共接口：

- ``TemporalConvNet`` (SG-EXP-002)：仅使用节点自身历史的默认 TCN，作为稳定时段的默认预测路径
- ``StaticGraphForecast`` (SG-EXP-003)：TCN 编码 + 训练期固定的统计交互图消息传递
- ``AdaptiveGraphForecast`` (SG-EXP-004)：TCN 编码 + 节点嵌入学习的自适应图（融合固定先验）
- ``EventResidualCorrection`` (SG-EXP-005)：冻结默认模型 + 事件门控下的有界残差修正

所有模型通过 ``ForecastModel`` 统一接口输出 ``ForecastOutput``，
保证训练和评价代码不依赖具体模型实现。
"""

from evcs_station_graph.models.common import ForecastModel, ForecastOutput
from evcs_station_graph.models.graph import AdaptiveGraphForecast, StaticGraphForecast
from evcs_station_graph.models.residual import EventResidualCorrection
from evcs_station_graph.models.tcn import TemporalConvNet

__all__ = [
    "AdaptiveGraphForecast",
    "EventResidualCorrection",
    "ForecastModel",
    "ForecastOutput",
    "StaticGraphForecast",
    "TemporalConvNet",
]
