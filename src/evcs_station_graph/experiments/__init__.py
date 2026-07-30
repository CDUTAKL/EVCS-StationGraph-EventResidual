"""实验编排入口。

本模块管理 SG-EXP-002～006 的正式运行顺序与跨实验工件检查。
核心流程：SG-EXP-002（TCN）→ SG-EXP-003（固定图）→ SG-EXP-004（自适应图）
→ SG-EXP-005（事件残差，加载 SG-EXP-002 检查点）→ SG-EXP-006（16 个机制变体）。

注意：SG-EXP-005/006 按随机种子加载 SG-EXP-002 的对应检查点，
避免种子错配导致基线不可比。
"""

from evcs_station_graph.experiments.mechanism import run_mechanism_suite
from evcs_station_graph.experiments.pipeline import run_formal_pipeline
from evcs_station_graph.experiments.validation import validate_pipeline_artifacts

__all__ = [
    "run_formal_pipeline",
    "run_mechanism_suite",
    "validate_pipeline_artifacts",
]
