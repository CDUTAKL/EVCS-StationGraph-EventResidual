"""统一训练入口。"""

from evcs_station_graph.training.engine import train_experiment, train_single_seed
from evcs_station_graph.training.factory import build_model

__all__ = ["build_model", "train_experiment", "train_single_seed"]
