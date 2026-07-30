"""统一实验编排与检查点解析测试。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from evcs_station_graph.experiments.mechanism import _build_variants
from evcs_station_graph.cli import _load_orchestration_config
from evcs_station_graph.experiments.validation import (
    _prediction_key_fingerprint,
    _same_key_space,
)
from evcs_station_graph.training.engine import _resolve_seed_checkpoint


def test_seed_checkpoint_must_match_seed(tmp_path: Path) -> None:
    """三随机种子运行不得误用其他种子的默认模型。"""
    checkpoint = tmp_path / "seed-2025" / "model.pt"
    checkpoint.parent.mkdir(parents=True)
    checkpoint.write_bytes(b"test")

    assert _resolve_seed_checkpoint(tmp_path, 2025) == checkpoint
    with pytest.raises(FileNotFoundError, match="随机种子 2024"):
        _resolve_seed_checkpoint(tmp_path, 2024)


def test_mechanism_suite_builds_expected_variants() -> None:
    """消融、候选关系和敏感性配置应全部展开，且不遗漏联合关系。"""
    base = {
        "experiment": {
            "model": "event_residual",
            "model_params": {"residual_bound": 0.5},
            "gate": {"enabled": True},
            "graph": {"top_k": 5, "enabled_relations": ["load", "event", "pattern"]},
        }
    }
    suite = {
        "ablations": {
            "no_graph": {"experiment.model": "TCN"},
            "no_event_gate": {"experiment.gate.enabled": False},
        },
        "relations": ["load", "event", "pattern", "all"],
        "sensitivity": {"top_k": [3, 7], "relation_dropout": [0.2]},
    }

    variants = _build_variants(base, suite)
    names = [name for name, _, _ in variants]

    assert names == [
        "ablation-no_graph",
        "ablation-no_event_gate",
        "relation-load",
        "relation-event",
        "relation-pattern",
        "relation-all",
        "topk-3",
        "topk-7",
        "dropout-0p2",
    ]
    no_graph = next(item for item in variants if item[0] == "ablation-no_graph")
    no_event = next(item for item in variants if item[0] == "ablation-no_event_gate")
    assert no_graph[2] is False
    assert no_event[2] is True

    # relation_dropout 敏感性取值必须写入派生配置的 graph 段——
    # 工厂从 experiment.graph.relation_dropout 读取该值并传入模型
    dropout_variant = next(item for item in variants if item[0] == "dropout-0p2")
    assert dropout_variant[1]["experiment"]["graph"]["relation_dropout"] == 0.2


def test_orchestration_applies_dataset_override_before_loading(tmp_path: Path) -> None:
    """编排命令应先应用覆盖项，再决定加载哪个节点张量。"""
    project_path = Path("configs/project.yaml").resolve()
    suite_path = Path("configs/experiments/SG-EXP-006-mechanism.yaml").resolve()
    overridden = tmp_path / "smoke.npz"

    config = _load_orchestration_config(
        project_path,
        suite_path,
        (f"paths.dataset_artifact={overridden}",),
        command="run-mechanism",
    )

    assert Path(config["paths"]["dataset_artifact"]) == overridden


def test_prediction_key_fingerprint_is_order_independent(tmp_path: Path) -> None:
    """跨方法比较允许行顺序不同，但预测键集合必须完全一致。"""
    rows = pd.DataFrame(
        {
            "split": ["test", "test"],
            "origin_index": [100, 100],
            "horizon": [1, 2],
            "node_id": ["CA-303", "CA-303"],
        }
    )
    first = tmp_path / "first.csv.gz"
    second = tmp_path / "second.csv.gz"
    rows.to_csv(first, index=False)
    rows.iloc[::-1].to_csv(second, index=False)

    left = _prediction_key_fingerprint(first)
    right = _prediction_key_fingerprint(second)

    assert left["unique"] is True
    assert _same_key_space(left, right)
