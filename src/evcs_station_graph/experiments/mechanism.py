"""SG-EXP-006 消融、候选关系与敏感性实验。

本模块只负责派生配置和汇总结果，不在代码中隐藏训练参数。每个子实验仍调用
统一训练入口，因此预测键、评价口径和模型保存格式与 SG-EXP-002～005 完全一致。
"""

from __future__ import annotations

import copy
import csv
import time
from pathlib import Path
from typing import Any

from evcs_station_graph.config import dump_yaml, load_experiment_config, load_yaml
from evcs_station_graph.data import TensorBundle
from evcs_station_graph.reproducibility import write_json
from evcs_station_graph.training import train_experiment


def run_mechanism_suite(
    project_path: str | Path,
    suite_path: str | Path,
    bundle: TensorBundle,
    output_root: str | Path,
    *,
    base_checkpoint: str | Path,
    overrides: tuple[str, ...] = (),
) -> Path:
    """运行 SG-EXP-006 的全部机制子实验并生成统一汇总。"""
    suite = load_yaml(suite_path)
    base_path = suite["base_experiment_config"]
    base_config = load_experiment_config(project_path, base_path, overrides)
    suite_seeds = suite.get("seeds")
    seeds_explicitly_overridden = any(
        item.split("=", 1)[0].strip() == "experiment.seeds"
        for item in overrides
        if "=" in item
    )
    if suite_seeds and not seeds_explicitly_overridden:
        if not all(isinstance(seed, int) for seed in suite_seeds):
            raise ValueError("SG-EXP-006 的随机种子必须全部为整数")
        base_config["experiment"]["seeds"] = list(suite_seeds)
    run_tag = time.strftime("%Y%m%d-%H%M%S")
    root = (
        Path(output_root).expanduser().resolve()
        / str(suite["experiment_id"])
        / run_tag
    )
    root.mkdir(parents=True, exist_ok=True)
    dump_yaml({"suite": suite, "base": base_config}, root / "config_resolved.yaml")

    variants = _build_variants(base_config, suite)
    if not variants:
        raise ValueError("SG-EXP-006 未配置任何消融、候选关系或敏感性子实验")
    rows: list[dict[str, Any]] = []
    child_runs: dict[str, str] = {}
    for variant_name, config, needs_checkpoint in variants:
        config["experiment"]["experiment_id"] = f"SG-EXP-006-{variant_name}"
        config["experiment"]["run_tag"] = run_tag
        config["experiment"]["result_authority"] = config["experiment"].get(
            "result_authority",
            suite.get("result_authority", "formal_candidate"),
        )
        child_root = train_experiment(
            config,
            bundle,
            root / "children",
            base_checkpoint=base_checkpoint if needs_checkpoint else None,
        )
        child_runs[variant_name] = str(child_root)
        summary = _read_json(child_root / "metrics_summary.json")
        rows.extend(_flatten_summary(variant_name, summary))

    _write_rows(rows, root / "mechanism_summary.csv")
    write_json(
        {
            "experiment_id": suite["experiment_id"],
            "run_tag": run_tag,
            "variant_count": len(variants),
            "child_runs": child_runs,
            "summary_csv": "mechanism_summary.csv",
            "four_cell_reconstruction_all_pass": all(
                row["four_cell_reconstruction_all_pass"] for row in rows
            ),
        },
        root / "manifest.json",
    )
    return root


def _build_variants(
    base: dict[str, Any],
    suite: dict[str, Any],
) -> list[tuple[str, dict[str, Any], bool]]:
    """根据实验套件配置构建所有机制子实验变体。

    从套件配置中读取三类实验：
    1. 消融实验（ablations）：通过点分键路径覆盖配置值，如禁用门控、移除图等
    2. 关系消融实验（relations）：将 enabled_relations 设置为单个关系名以消融到单关系，
       特殊值 "all" 启用全部三种关系（load/event/pattern）
    3. 敏感性实验（sensitivity）：包括 top_k 和 relation_dropout 的参数扫描

    Returns:
        三元组列表，每项为 (变体名称, 派生配置, 是否需要默认模型检查点)。
    """
    # 不需要加载 checkpoint 的模型：
    # - TCN/TCN_GCN/adaptive_graph：独立模型，不从底座初始化
    # - event_residual 且 gate.enabled=false：门控关闭时所有样本均进入修正路径，
    #   此时加载底座 checkpoint 无意义（底座被冻结但门控失效），且 checkpoint
    #   可能来自不同底座类型导致 state_dict 不匹配
    model_without_checkpoint = {"TCN", "TCN_GCN", "adaptive_graph"}
    variants: list[tuple[str, dict[str, Any], bool]] = []

    for name, override_map in suite.get("ablations", {}).items():
        config = copy.deepcopy(base)
        for key, value in override_map.items():
            _set_dotted(config, key, value)
        model_name = str(config["experiment"]["model"])
        needs_checkpoint = model_name not in model_without_checkpoint
        # 门控关闭的 event_residual 消融不加载底座 checkpoint
        if model_name in {"event_residual", "frozen_event_gated_residual_correction"}:
            gate_enabled = bool(config["experiment"].get("gate", {}).get("enabled", True))
            if not gate_enabled:
                needs_checkpoint = False
                # 门控关闭时底座不需要冻结——所有样本都进入修正路径，
                # 底座和修正器一起训练才有意义
                config["experiment"]["model_params"]["freeze_base"] = False
        variants.append((f"ablation-{name}", config, needs_checkpoint))

    # 关系消融：指定 graph.enabled_relations（单个关系名）来消融到单关系
    # 审查 2026-08-04：单关系变体的逐关系变换矩阵数量（W_r 数 = 关系数）与
    # base checkpoint（三/四关系）不同，state_dict 结构不匹配——必须从头训练，
    # needs_checkpoint 置 False（此前置 True 导致 checkpoint 加载崩溃）
    for relation_name in suite.get("relations", []):
        config = copy.deepcopy(base)
        if relation_name == "all":
            config["experiment"]["graph"]["enabled_relations"] = ["load", "event", "pattern"]
        else:
            config["experiment"]["graph"]["enabled_relations"] = [relation_name]
        # 从头训练：关闭 base 的 freeze_base（其原值依赖 005 的 checkpoint 冻结）
        config["experiment"]["model_params"]["freeze_base"] = False
        variants.append((f"relation-{relation_name}", config, False))

    sensitivity = suite.get("sensitivity", {})
    for top_k in sensitivity.get("top_k", []):
        config = copy.deepcopy(base)
        # 审查 2026-08-03：top_k 必须写入 model_params——factory 从
        # model_params.top_k 读取（AdaptiveGraph/StaticGraph 分支），
        # 写入 graph.top_k 不会生效（graph 下无对应读取点，曾导致
        # topk-7 变体实际以默认 5 训练、与 topk-5 预测逐位相同）
        config["experiment"]["model_params"]["top_k"] = int(top_k)
        variants.append((f"topk-{top_k}", config, True))
    for dropout in sensitivity.get("relation_dropout", []):
        config = copy.deepcopy(base)
        config["experiment"]["graph"]["relation_dropout"] = float(dropout)
        label = str(dropout).replace(".", "p")
        variants.append((f"dropout-{label}", config, True))
    return variants


def _flatten_summary(variant: str, summary: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    reconstruction = bool(summary["four_cell_reconstruction_all_pass"])
    for scope, metrics in summary["scopes"].items():
        for metric, values in metrics.items():
            rows.append(
                {
                    "variant": variant,
                    "scope": scope,
                    "metric": metric,
                    "mean": values["mean"],
                    "std": values["std"],
                    "four_cell_reconstruction_all_pass": reconstruction,
                }
            )
    return rows


def _write_rows(rows: list[dict[str, Any]], path: Path) -> None:
    if not rows:
        raise RuntimeError("机制实验汇总为空，拒绝生成空结果文件")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _read_json(path: Path) -> dict[str, Any]:
    import json

    return json.loads(path.read_text(encoding="utf-8"))


def _set_dotted(config: dict[str, Any], dotted_key: str, value: Any) -> None:
    """按点分键设置嵌套字典值，自动创建不存在的中间键。"""
    cursor = config
    parts = dotted_key.split(".")
    for part in parts[:-1]:
        child = cursor.setdefault(part, {})
        if not isinstance(child, dict):
            raise ValueError(f"无法覆盖非映射配置项：{dotted_key}（{part} 不是字典）")
        cursor = child
    cursor[parts[-1]] = value
