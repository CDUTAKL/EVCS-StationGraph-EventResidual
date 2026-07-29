"""配置读取、合并与校验。

研究代码只从配置文件接收实验参数，避免把数据路径、随机种子和模型超参数
散落在训练脚本中。配置采用 YAML；命令行覆盖项使用 ``a.b=value`` 形式。
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable

import yaml


class ConfigError(ValueError):
    """配置缺失或取值不合法。"""


def load_yaml(path: str | Path) -> dict[str, Any]:
    """读取 YAML 文件并保证根节点为字典。"""
    config_path = Path(path).expanduser().resolve()
    if not config_path.exists():
        raise ConfigError(f"配置文件不存在：{config_path}")
    with config_path.open("r", encoding="utf-8") as handle:
        value = yaml.safe_load(handle) or {}
    if not isinstance(value, dict):
        raise ConfigError(f"配置文件根节点必须是映射：{config_path}")
    return value


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """递归合并配置，后者覆盖前者。"""
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged


def load_experiment_config(
    project_path: str | Path,
    experiment_path: str | Path,
    overrides: Iterable[str] = (),
) -> dict[str, Any]:
    """加载项目配置与实验配置，并应用命令行覆盖项。"""
    config = deep_merge(load_yaml(project_path), {"experiment": load_yaml(experiment_path)})
    for item in overrides:
        if "=" not in item:
            raise ConfigError(f"覆盖项必须为 key=value：{item}")
        dotted_key, raw_value = item.split("=", 1)
        _set_dotted(config, dotted_key, yaml.safe_load(raw_value))
    validate_common_config(config)
    return config


def validate_common_config(config: dict[str, Any]) -> None:
    """校验所有实验共用的关键参数。"""
    project = config.get("project", {})
    if not project.get("id"):
        raise ConfigError("缺少 project.id")
    if int(project.get("history_steps", 0)) <= 0:
        raise ConfigError("project.history_steps 必须为正整数")
    if int(project.get("forecast_steps", 0)) <= 0:
        raise ConfigError("project.forecast_steps 必须为正整数")
    if int(project.get("time_resolution_minutes", 0)) <= 0:
        raise ConfigError("project.time_resolution_minutes 必须为正整数")

    seeds = config.get("experiment", {}).get("seeds", config.get("reporting", {}).get("seeds"))
    if not seeds or not all(isinstance(seed, int) for seed in seeds):
        raise ConfigError("实验必须提供整数随机种子列表")


def dump_yaml(config: dict[str, Any], path: str | Path) -> None:
    """将解析后的配置保存为可追溯文件。"""
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(config, handle, allow_unicode=True, sort_keys=False)


def _set_dotted(config: dict[str, Any], dotted_key: str, value: Any) -> None:
    cursor = config
    parts = dotted_key.split(".")
    for part in parts[:-1]:
        child = cursor.setdefault(part, {})
        if not isinstance(child, dict):
            raise ConfigError(f"无法覆盖非映射配置项：{dotted_key}")
        cursor = child
    cursor[parts[-1]] = value
