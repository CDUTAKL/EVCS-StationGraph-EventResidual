"""第 2 章数据章新增 4 图：图 2-7~2-10。

- 图 2-7 特征相关性矩阵：7 特征 Spearman 相关（抗稀疏零值），全局展平样本。
- 图 2-8 星期×小时负荷热力图：日内（24 h）× 周内（7 d）双周期聚合视图。
- 图 2-9 事件四分量构成：触发样本处 access/departure/|Δactive|/load_jump
  的逐节点归一化平均贡献（与事件分数定义一致，per-node std 归一化）。
- 图 2-10 事件窗口长度分布：冻结规则（验证集 95 分位 + 因果前向扩展 2 步）
  在测试集上的窗口长度直方图与占比。

全部从 SG-DATA-005 直接计算，无新实验；输出同名 SVG + 1200 DPI PNG。
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap

sys.path.insert(0, str(Path.home() / ".claude/skills/scipilot-figure-skill/scripts"))
try:
    from export_figure import export_figure  # noqa: E402
    from setup_style import setup_style  # noqa: E402
except ImportError:  # 无 skill 环境回退
    from _skill_compat import export_figure, setup_style  # noqa: E402

sys.path.insert(0, "src")
from evcs_station_graph.data import load_tensor_bundle  # noqa: E402
from evcs_station_graph.evaluation.rules import apply_frozen_event_rule, fit_frozen_event_rule  # noqa: E402

FIG_DIR = Path("outputs/figures")
FIG_DIR.mkdir(parents=True, exist_ok=True)
setup_style(journal="general", lang="zh")

BLUE = "#2C5F8A"
ORANGE = "#D08A3C"
GRAY_D = "#404040"
GRAY_M = "#808080"
GRAY_L = "#C8C8C8"
GRAY_XL = "#E6E9EC"
RED = "#B05A4A"
GREEN = "#597A62"

# 特征中文名（与 feature_names 顺序一一对应）
FEATURE_CN = ["负荷", "接入数", "离站数", "活跃数", "占用率", "需求强度", "负荷跳变"]
# 事件分数 4 分量（与 rules.py 定义一致）：索引 1/2/3/6
EVENT_COMPONENTS = [
    (1, "接入"),
    (2, "离站"),
    (3, "活跃变化"),
    (6, "负荷跳变"),
]

BUNDLE = load_tensor_bundle("data/processed/SG-DATA-005-primary-tensor.npz")


def _final(fig, name: str, size: tuple) -> None:
    """导出 SVG + 1200 DPI PNG。"""
    export_figure(fig, basename=str(FIG_DIR / name), formats=["svg", "png"],
                  dpi=1200, size_inches=size, grayscale_preview=False)
    print(f"  ✅ {name}")


def _clean(ax, grid_axis="y") -> None:
    """去除上/右边框，网格线保持浅色。"""
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color(GRAY_D)
    ax.tick_params(labelsize=8, colors=GRAY_D)
    if grid_axis:
        ax.grid(axis=grid_axis, color=GRAY_L, lw=0.55, alpha=0.72, zorder=0)


def redraw_fig2_7() -> None:
    """图 2-7：7 特征 Spearman 相关矩阵（全局展平，抗零值稀疏）。"""
    feats = BUNDLE.features  # [T, N, F]
    flat = feats.reshape(-1, feats.shape[2])  # 展平 [T*N, F]：跨节点全局相关性
    corr = pd.DataFrame(flat, columns=FEATURE_CN).corr(method="spearman").to_numpy()

    fig, ax = plt.subplots(figsize=(5.6, 5.0))
    # 蓝-白-红 diverging 色阶：负相关蓝、正相关红（零值稀疏数据下相关系数偏低）
    cmap = LinearSegmentedColormap.from_list(
        "rdbu_soft", ["#8EABC0", "#FFFFFF", "#C98A83"])
    im = ax.imshow(corr, cmap=cmap, vmin=-1, vmax=1)
    for i in range(corr.shape[0]):
        for j in range(corr.shape[1]):
            val = corr[i, j]
            # 文本对比度阈值：|r|>0.45 用白字（深色底），否则用深灰字（浅色底）
            color = "white" if abs(val) > 0.45 else GRAY_D
            ax.text(j, i, f"{val:.2f}", ha="center", va="center",
                    fontsize=7.6, color=color)
    ax.set_xticks(range(len(FEATURE_CN)))
    ax.set_yticks(range(len(FEATURE_CN)))
    ax.set_xticklabels(FEATURE_CN, fontsize=8.2, rotation=45, ha="right")
    ax.set_yticklabels(FEATURE_CN, fontsize=8.2)
    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_color(GRAY_L)
    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.ax.tick_params(labelsize=7.5)
    _final(fig, "fig2_7_feature_correlation", (5.6, 5.0))
    return None


def redraw_fig2_8() -> None:
    """图 2-8：星期×小时聚合负荷热力图（全节点均值，双周期视图）。"""
    t = BUNDLE.targets  # [T, N]
    ts = pd.to_datetime(BUNDLE.timestamps)
    df = pd.DataFrame({"load": t.mean(axis=1), "ts": ts})
    df["weekday"] = df["ts"].dt.weekday  # 0=周一
    df["hour"] = df["ts"].dt.hour
    pivot = df.pivot_table(index="weekday", columns="hour",
                           values="load", aggfunc="mean")
    mat = pivot.reindex([0, 1, 2, 3, 4, 5, 6]).to_numpy()

    fig, ax = plt.subplots(figsize=(7.6, 3.6))
    cmap = LinearSegmentedColormap.from_list(
        "load_ramp", ["#FFFFFF", "#C9DCE8", "#2C5F8A"])
    # 周末行浅橙底纹置于热力图之上但半透明（alpha=0.35）：
    # 既标识周末又不遮挡数据（全不透明会盖住周末行数值）
    for wk in (5, 6):
        ax.add_patch(plt.Rectangle((-0.5, wk - 0.5), 24, 1,
                                   facecolor="#F5E9D8", edgecolor="none",
                                   alpha=0.35, zorder=2))
    im = ax.imshow(mat, cmap=cmap, aspect="auto", zorder=1,
                   vmin=0, vmax=np.percentile(mat, 99))
    ax.set_xticks(range(24))
    ax.set_xticklabels([f"{h:02d}" for h in range(24)], fontsize=7.2)
    ax.set_yticks(range(7))
    ax.set_yticklabels(["周一", "周二", "周三", "周四", "周五", "周六", "周日"],
                       fontsize=7.8)
    ax.set_xlabel("小时（0–23）", fontsize=8.6)
    ax.set_ylabel("星期", fontsize=8.6)
    ax.tick_params(length=0)
    cbar = fig.colorbar(im, ax=ax, fraction=0.045, pad=0.03)
    cbar.set_label("全站负荷均值（kWh/15 min）", fontsize=7.6)
    cbar.ax.tick_params(labelsize=7.5)
    _clean(ax, grid_axis=None)
    _final(fig, "fig2_8_weekday_hour_heatmap", (7.6, 3.6))
    return None


def redraw_fig2_9() -> None:
    """图 2-9：事件四分量构成——验证+测试触发样本处各分量归一化平均贡献。

    事件分数 = 4 分量 per-node std 归一化后求和（rules.py 定义）；
    本图展示每个节点触发样本的平均归一化分量，堆叠柱观察构成。
    """
    feats = BUNDLE.features
    # 与事件分数定义（rules.py _compute_score_stats）一致：std 只在训练集估计，
    # 不引入测试集统计量（审查 M5）
    train_end = BUNDLE.split_origins["train"][-1] + 1
    stds = feats[:train_end].std(axis=0)  # [N, F]
    stds = np.where(stds < 1e-12, 1.0, stds)  # 常数列避免除零
    norm = feats / stds[None, :, :]  # [T, N, F] 逐节点逐特征归一化
    active = feats[:, :, 3]
    delta_active = np.abs(np.diff(active, axis=0, prepend=active[:1]))  # 一阶差分

    rule = fit_frozen_event_rule(BUNDLE)
    trig_test = apply_frozen_event_rule(
        BUNDLE, BUNDLE.split_origins["test"], rule)  # [O, N]
    # origin 即时间索引：触发矩阵映射回 [T, N] 全局时间轴，才能与特征切片对齐
    trig_TN = np.zeros((BUNDLE.features.shape[0], BUNDLE.node_ids.shape[0]),
                       dtype=bool)
    trig_TN[BUNDLE.split_origins["test"]] = trig_test

    # 逐节点平均：trig_TN 按列聚合 4 分量值（fidx=3 用一阶差分）
    per_node = np.zeros((BUNDLE.node_ids.shape[0], len(EVENT_COMPONENTS)))
    for ci, (fidx, _name) in enumerate(EVENT_COMPONENTS):  # 双层嵌套解包：(序号, (特征索引, 名称))
        for ni in range(BUNDLE.node_ids.shape[0]):
            col_mask = trig_TN[:, ni]  # [T] 该节点触发掩码
            if col_mask.any():
                if fidx == 3:
                    vals = delta_active[col_mask, ni]  # 2D [T,N] 列切片
                else:
                    vals = norm[col_mask, ni, fidx]  # 3D [T,N,F] 元素切片
                per_node[ni, ci] = vals.mean()

    fig, ax = plt.subplots(figsize=(7.8, 3.9))
    colors = [BLUE, ORANGE, GREEN, "#7A6FA0"]
    labels = [n for _, n in EVENT_COMPONENTS]
    x = np.arange(len(BUNDLE.node_ids))
    bottom = np.zeros(len(BUNDLE.node_ids))
    for ci, color in enumerate(colors):
        ax.bar(x, per_node[:, ci], bottom=bottom, color=color, width=0.62,
               edgecolor="white", linewidth=0.5, label=labels[ci], zorder=3)
        bottom += per_node[:, ci]
    ax.set_xticks(x)
    ax.set_xticklabels(BUNDLE.node_ids, fontsize=7.6, rotation=45, ha="right")
    ax.set_ylabel("归一化分量均值", fontsize=8.6)
    ax.set_ylim(0, bottom.max() * 1.12)
    ax.legend(fontsize=7.4, frameon=False, ncol=4, loc="upper right")
    _clean(ax)
    _final(fig, "fig2_9_event_component_composition", (7.8, 3.9))
    return None


def redraw_fig2_10() -> None:
    """图 2-10：事件窗口长度分布 + 逐节点窗口数（冻结规则，含因果扩展）。

    A：窗口长度直方图（扩展 2 步后几乎全部 3 片，合并后可达 6 片）；
    B：逐节点窗口数条形图（展示节点间触发频率差异）。
    """
    rule = fit_frozen_event_rule(BUNDLE)
    trig = apply_frozen_event_rule(BUNDLE, BUNDLE.split_origins["test"], rule)
    # 连续 True 段的长度 = 窗口长度（时间片数；同一节点的时间轴）
    lens, per_node_count = [], []
    for ni in range(trig.shape[1]):
        col = trig[:, ni].astype(int)
        # 段起止：diff 边界（np.diff + pad 处理首尾）
        padded = np.concatenate(([0], col, [0]))
        starts = np.where(np.diff(padded) == 1)[0]
        ends = np.where(np.diff(padded) == -1)[0]
        lens.extend(int(e - s) for s, e in zip(starts, ends))
        per_node_count.append(len(starts))
    lens = np.asarray(lens)

    fig, axes = plt.subplots(1, 2, figsize=(8.8, 3.5))
    ax = axes[0]
    # 横轴范围：至少覆盖 4 片（扩展 2 步后最小窗口 3 片，留出右边界）
    max_len = max(lens.max(), 4)
    bins = np.arange(0.5, max_len + 1.5, 1.0)
    ax.hist(lens, bins=bins, color=BLUE, edgecolor="white", lw=0.8, zorder=3)
    ax.set_xlabel("窗口长度（15 min 时间片）", fontsize=8.4)
    ax.set_ylabel("窗口数", fontsize=8.4)
    ax.set_xticks(np.arange(1, max_len + 1))
    ax.text(0.98, 0.96, f"共 {len(lens)} 个；平均 {lens.mean():.1f} 片，最长 {lens.max()} 片",
            transform=ax.transAxes, ha="right", va="top",
            fontsize=6.9, color=GRAY_M)
    _clean(ax)

    ax = axes[1]
    xs = np.arange(len(BUNDLE.node_ids))
    ax.bar(xs, per_node_count, width=0.62, color=ORANGE,
           edgecolor="white", lw=0.6, zorder=3)
    for xi, c in enumerate(per_node_count):
        ax.text(xi, c + 0.8, str(c), ha="center", va="bottom",
                fontsize=6.8, color=GRAY_D)
    ax.set_xticks(xs)
    ax.set_xticklabels(BUNDLE.node_ids, fontsize=6.8, rotation=45, ha="right")
    ax.set_ylabel("事件窗口数（测试集）", fontsize=8.4)
    _clean(ax)
    _final(fig, "fig2_10_event_window_length", (8.8, 3.5))
    return None


if __name__ == "__main__":
    print("=== 批次 11：第 2 章数据章新增 4 图 ===")
    redraw_fig2_7()
    redraw_fig2_8()
    redraw_fig2_9()
    redraw_fig2_10()
    print("批次 11 完成")
