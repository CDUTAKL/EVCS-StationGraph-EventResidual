"""配对 Bootstrap 显著性检验的单元测试。"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts.bootstrap_significance import (
    align_predictions,
    load_predictions,
    paired_bootstrap_mae_diff,
    window_mask,
)


# ---------- 辅助函数 ----------


def _make_predictions(
    seed: int,
    n: int = 600,
    shift: float = 0.0,
    noise_std: float = 0.5,
    drop_tail: int = 0,
) -> pd.DataFrame:
    """构造合成预测表，两模型使用相同 seed 可获得一致主键。"""
    rng = np.random.default_rng(seed)
    origins = np.arange(n)
    horizons = rng.integers(1, 5, size=n)
    node_ids = rng.choice(["N001", "N002", "N003"], size=n)
    y_true = rng.normal(0.0, 1.0, size=n)
    y_pred = y_true + rng.normal(shift, noise_std, size=n)
    # 约 20% 样本为事件窗口，保证 event_window 测试有足够样本
    target_event = rng.random(n) < 0.2
    rule_trigger = target_event & (rng.random(n) < 0.7)

    df = pd.DataFrame(
        {
            "split": np.repeat("test", n),
            "origin_index": origins,
            "horizon": horizons,
            "node_id": node_ids,
            "y_true": y_true,
            "y_pred": y_pred,
            "target_event": target_event,
            "rule_trigger": rule_trigger,
        }
    )
    if drop_tail > 0:
        df = df.iloc[:-drop_tail].reset_index(drop=True)
    return df


# ---------- 功能测试 ----------


def test_bootstrap_detects_systematic_improvement() -> None:
    """当提议模型系统性优于基线时，Bootstrap 应拒绝零假设（p < 0.01）且 CI > 0。"""
    base_df = _make_predictions(seed=1, shift=0.6, noise_std=1.0)
    prop_df = _make_predictions(seed=1, shift=0.0, noise_std=0.1)
    rng = np.random.default_rng(2024)

    aligned = align_predictions(base_df, prop_df)
    mask = window_mask(
        "event_window", aligned["target_event"], aligned["rule_trigger"]
    )
    result = paired_bootstrap_mae_diff(
        aligned["base_pred"],
        aligned["prop_pred"],
        aligned["truth"],
        mask,
        n_resamples=2000,
        rng=rng,
    )

    assert result["p_value_one_sided"] < 0.01
    assert result["ci_lower"] > 0.0


def test_identical_predictions_yield_zero_effect() -> None:
    """两模型预测完全相同时，差值分布应退化为 0，p 值为 1.0，CI 为 [0, 0]。"""
    base_df = _make_predictions(seed=2, shift=0.0, noise_std=0.3)
    prop_df = base_df.copy()
    rng = np.random.default_rng(2024)

    aligned = align_predictions(base_df, prop_df)
    mask = window_mask("global", aligned["target_event"], aligned["rule_trigger"])
    result = paired_bootstrap_mae_diff(
        aligned["base_pred"],
        aligned["prop_pred"],
        aligned["truth"],
        mask,
        n_resamples=500,
        rng=rng,
    )

    assert result["p_value_one_sided"] == 1.0
    assert result["ci_lower"] == 0.0
    assert result["ci_upper"] == 0.0
    assert result["observed_diff"] == 0.0


def test_key_mismatch_raises() -> None:
    """两模型预测键不一致时必须显式报错。"""
    base_df = _make_predictions(seed=3)
    prop_df = _make_predictions(seed=3, drop_tail=10)

    with pytest.raises(ValueError):
        align_predictions(base_df, prop_df)


def test_reproducibility_with_same_seed() -> None:
    """相同随机数种子应产生逐位一致的结果。"""
    base_df = _make_predictions(seed=4, shift=0.3, noise_std=0.5)
    prop_df = _make_predictions(seed=4, shift=0.0, noise_std=0.3)

    aligned = align_predictions(base_df, prop_df)
    mask = window_mask("global", aligned["target_event"], aligned["rule_trigger"])

    rng1 = np.random.default_rng(99)
    rng2 = np.random.default_rng(99)
    result1 = paired_bootstrap_mae_diff(
        aligned["base_pred"],
        aligned["prop_pred"],
        aligned["truth"],
        mask,
        n_resamples=500,
        rng=rng1,
    )
    result2 = paired_bootstrap_mae_diff(
        aligned["base_pred"],
        aligned["prop_pred"],
        aligned["truth"],
        mask,
        n_resamples=500,
        rng=rng2,
    )

    assert result1 == result2


def test_load_predictions_rejects_invalid_event_values(tmp_path) -> None:
    """load_predictions 应拒绝 target_event / rule_trigger 中的非法取值。"""
    bad_path = tmp_path / "bad_event.csv.gz"
    pd.DataFrame(
        [
            {
                "split": "test",
                "origin_index": 0,
                "horizon": 1,
                "node_id": "N001",
                "y_true": 1.0,
                "y_pred": 1.0,
                "target_event": "maybe",  # 非法字符串
                "rule_trigger": False,
            }
        ]
    ).to_csv(bad_path, index=False, compression="gzip")

    with pytest.raises(ValueError):
        load_predictions(bad_path)


def test_align_predictions_rejects_mismatched_event_flags() -> None:
    """两模型事件标志不一致时必须显式报错。"""
    base_df = _make_predictions(seed=5)
    prop_df = _make_predictions(seed=5)
    prop_df.loc[0, "target_event"] = not prop_df.loc[0, "target_event"]

    with pytest.raises(ValueError):
        align_predictions(base_df, prop_df)


def test_align_predictions_rejects_mismatched_y_true() -> None:
    """两模型真实值不一致时必须显式报错。"""
    base_df = _make_predictions(seed=6)
    prop_df = _make_predictions(seed=6)
    prop_df.loc[0, "y_true"] += 1.0

    with pytest.raises(ValueError):
        align_predictions(base_df, prop_df)


def test_n_resamples_zero_raises() -> None:
    """n_resamples <= 0 必须报错。"""
    base_df = _make_predictions(seed=7)
    prop_df = _make_predictions(seed=7)
    rng = np.random.default_rng(0)
    aligned = align_predictions(base_df, prop_df)
    mask = window_mask("global", aligned["target_event"], aligned["rule_trigger"])

    with pytest.raises(ValueError):
        paired_bootstrap_mae_diff(
            aligned["base_pred"],
            aligned["prop_pred"],
            aligned["truth"],
            mask,
            n_resamples=0,
            rng=rng,
        )


# ---------- 防御性测试 ----------


def test_empty_window_raises() -> None:
    """空窗口掩码必须报错，避免产出无意义的统计量。"""
    n = 50
    truth = np.zeros(n, dtype=np.float64)
    base_pred = np.zeros(n, dtype=np.float64)
    prop_pred = np.zeros(n, dtype=np.float64)
    mask = np.zeros(n, dtype=bool)
    rng = np.random.default_rng(0)

    with pytest.raises(ValueError):
        paired_bootstrap_mae_diff(
            base_pred, prop_pred, truth, mask, n_resamples=100, rng=rng
        )


def test_nonfinite_values_raise() -> None:
    """非有限值必须显式报错。"""
    n = 50
    truth = np.full(n, np.nan, dtype=np.float64)
    base_pred = np.zeros(n, dtype=np.float64)
    prop_pred = np.zeros(n, dtype=np.float64)
    mask = np.ones(n, dtype=bool)
    rng = np.random.default_rng(0)

    with pytest.raises(ValueError):
        paired_bootstrap_mae_diff(
            base_pred, prop_pred, truth, mask, n_resamples=100, rng=rng
        )


def test_load_predictions_rejects_missing_columns(tmp_path) -> None:
    """load_predictions 应拒绝缺少必要列的文件。"""
    bad_path = tmp_path / "bad.csv.gz"
    pd.DataFrame({"split": ["test"], "origin_index": [0]}).to_csv(
        bad_path, index=False, compression="gzip"
    )

    with pytest.raises(ValueError):
        load_predictions(bad_path)


def test_load_predictions_rejects_duplicate_keys(tmp_path) -> None:
    """load_predictions 应拒绝重复主键。"""
    bad_path = tmp_path / "dup.csv.gz"
    row = {
        "split": "test",
        "origin_index": 0,
        "horizon": 1,
        "node_id": "N001",
        "y_true": 0.0,
        "y_pred": 0.0,
        "target_event": False,
        "rule_trigger": False,
    }
    pd.DataFrame([row, row]).to_csv(bad_path, index=False, compression="gzip")

    with pytest.raises(ValueError):
        load_predictions(bad_path)
