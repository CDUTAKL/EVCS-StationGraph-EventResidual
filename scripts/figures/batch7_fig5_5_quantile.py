"""论文图批次 7：fig5_5 per-node 分位数重设计（用户 2026-08-01 反馈"太丑"）。

数据事实（决定设计）：
- q_global / q_stable 为 per-node 分位数（10 节点各异，量级 1e-4~1e-3）
- q_event 为事件层**统一分位数**（10 节点同一值 0.695，事件窗口样本不足 per-node 拟合）
- 事件层分位数是全局的 687×~5321×（均值 2440×）——分层共形加宽区间的核心证据

设计（双面板）：
- 左面板：10 节点 × 3 层分组柱（全局灰 / 稳定中灰 / 事件深蓝），log y 轴展示三个数量级差异；
  事件层等高柱即"共享分位数"的事实视觉，柱顶标注一次 0.695
- 右面板：每节点"事件/全局"分位数膨胀倍数横向柱 + 3 种子误差棒 + 均值参考线（2440×）

统一规范：无标题、无文件名/代号、SVG+PNG 1200DPI、文字不遮挡图形。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path.home() / ".claude/skills/scipilot-figure-skill/scripts"))
try:
    from export_figure import export_figure  # noqa: E402
    from setup_style import setup_style  # noqa: E402
except ImportError:  # 无 skill 环境回退（审查 L-03）
    from _skill_compat import export_figure, setup_style  # noqa: E402

sys.path.insert(0, "src")
from evcs_station_graph.data import load_tensor_bundle  # noqa: E402

FIG_DIR = Path("outputs/figures")
FIG_DIR.mkdir(parents=True, exist_ok=True)

setup_style(journal="general", lang="zh")
BLUE = "#2C5F8A"      # 深蓝（事件层）
ORANGE = "#D08A3C"    # 低饱和橙
GRAY_D = "#404040"    # 深灰
GRAY_M = "#808080"    # 中灰（稳定窗口）
GRAY_L = "#C8C8C8"    # 浅灰（全局）
BUNDLE = load_tensor_bundle("data/processed/SG-DATA-005-primary-tensor.npz")


def final(fig, name: str, size: tuple[float, float]) -> None:
    """统一导出：SVG 矢量 + PNG 1200 DPI（论文硬性约束）。"""
    export_figure(
        fig, basename=str(FIG_DIR / name),
        formats=["svg", "png"], dpi=1200, size_inches=size,
        grayscale_preview=False,
    )
    print(f"  ✅ {name}")


def _clean_ax(ax, xlabel=None, ylabel=None):
    """统一轴风格：细边框 + 浅网格 + 标签。"""
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color(GRAY_D)
    ax.tick_params(labelsize=8, colors=GRAY_D)
    ax.grid(axis="y", color=GRAY_L, lw=0.5, alpha=0.6, zorder=0)
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=9)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=9)


def fig5_5_quantile() -> None:
    c = json.load(open("outputs/analysis/conformal_prediction/conformal_summary.json"))
    seeds = c["per_seed"]
    # 3 种子均值/标准差
    qg = np.mean([s["q_global_per_node"] for s in seeds], axis=0)
    qs = np.mean([s["q_stable_per_node"] for s in seeds], axis=0)
    qe = np.mean([s["q_event_per_node"] for s in seeds], axis=0)
    ratio = qe / np.maximum(qg, 1e-12)
    ratio_std = np.std([np.array(s["q_event_per_node"]) / np.maximum(
        np.array(s["q_global_per_node"]), 1e-12) for s in seeds], axis=0, ddof=1)
    labels = [n.split("-")[1] for n in BUNDLE.node_ids]
    x = np.arange(10)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8.8, 4.0),
                                   gridspec_kw={"width_ratios": [1.5, 1.0]})

    # ---- 左面板：3 层分位数（log 轴，展示三个数量级差异） ----
    w = 0.26
    ax1.bar(x - w, qg, w, label="全局", color=GRAY_L, edgecolor="white",
            linewidth=0.4, zorder=3)
    ax1.bar(x, qs, w, label="规则未触发层", color=GRAY_M, edgecolor="white",
            linewidth=0.4, zorder=3)
    ax1.bar(x + w, qe, w, label="规则触发层", color=BLUE, edgecolor="white",
            linewidth=0.4, zorder=3)
    # 触发层为共享分位数：只在第一根柱顶标注一次
    ax1.text(x[0] + w, qe[0] * 1.15, f"{qe[0]:.3f}", ha="center", va="bottom",
             fontsize=8, color=BLUE, fontweight="bold")
    # 必要说明：触发层统一分位数（校准分层 = 测试路由变量 = 冻结规则触发，
    # 审查 2026-08-01 一致化口径；标注在图右上空白区）
    ax1.text(0.99, 0.97, "规则触发层统一分位数\n（触发样本稀疏，无法逐节点拟合）",
             transform=ax1.transAxes, ha="right", va="top", fontsize=7,
             color=GRAY_D)
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, fontsize=8)
    ax1.set_xlabel("充电节点", fontsize=9)
    # 量纲修正（审查 2026-08-01）：分位数在反标准化残差上计算（engine._predict），
    # 物理单位 kWh/15 min，非标准化尺度
    ax1.set_ylabel("90% 残差分位数（kWh/15 min，对数轴）", fontsize=8.5)
    ax1.set_yscale("log")
    ax1.set_ylim(1e-4, 1.4)
    ax1.tick_params(labelsize=8)
    _clean_ax(ax1)
    ax1.legend(fontsize=7.5, frameon=False, ncol=3, loc="lower left",
               bbox_to_anchor=(0.0, 0.0))

    # ---- 右面板：事件/全局膨胀倍数（per-node 横向柱 + 误差棒 + 均值线） ----
    y = np.arange(10)
    ax2.barh(y, ratio, height=0.6, color=BLUE, alpha=0.85, edgecolor="white",
             linewidth=0.5, zorder=3)
    ax2.errorbar(ratio, y, xerr=ratio_std, fmt="none", ecolor=GRAY_D,
                 capsize=2.5, lw=0.7, zorder=4)
    # 柱外数值标注（右侧，不遮挡柱体）
    for yi, v in zip(y, ratio):
        ax2.text(v + ratio_std[yi] + 80, yi, f"{v:.0f}×", va="center",
                 fontsize=7.5, color=GRAY_D)
    # 均值参考线（24.4 倍即 2440% 的均值 2440×）
    mean_r = ratio.mean()
    ax2.axvline(mean_r, color=ORANGE, lw=1.2, ls="--", zorder=2)
    ax2.text(mean_r + 80, 9.35, f"均值 {mean_r:.0f}×", fontsize=7.5,
             color=ORANGE, ha="left")
    ax2.set_yticks(y)
    ax2.set_yticklabels(labels, fontsize=8)
    ax2.set_xlabel("触发层/全局 分位数倍数（3 种子均值 ± std）", fontsize=8.5)
    ax2.set_xlim(0, ratio.max() * 1.28)
    ax2.tick_params(labelsize=8)
    _clean_ax(ax2)

    final(fig, "fig5_9_quantile_per_node", (8.8, 4.0))


if __name__ == "__main__":
    print("=== 批次 7：fig5_5 分层分位数重设计 ===")
    fig5_5_quantile()
    print("批次 7 完成")
