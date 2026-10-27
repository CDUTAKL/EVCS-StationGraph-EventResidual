"""第 2 章数据章新增 4 图：图 2-7~2-10。

- 图 2-9 特征相关性矩阵：7 特征 Spearman 秩相关，全局展平样本。
- 图 2-10 星期×小时负荷热力图：日内（24 h）× 周内（7 d）双周期聚合视图。
- 图 2-7 事件四分量构成：冻结规则事件窗口内 access/departure/|Δactive|/|Δload|
  的逐节点归一化平均贡献（与事件分数定义一致，per-node std 归一化）。
- 图 2-8 事件窗口长度分布：冻结规则（验证集 95 分位，触发后向未来扩展 2 步）
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
from matplotlib.gridspec import GridSpec

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
# 图内采用短标签，完整含义保留在图注和正文，避免缩放后长中文标签互相挤压。
FEATURE_SHORT = ["负荷", "接入", "离站", "活跃", "占用", "需求", "跳变"]
EVENT_COMPONENT_LABELS = ["接入", "离站", "活跃变化", "负荷变化"]

BUNDLE = load_tensor_bundle("data/processed/SG-DATA-005-primary-tensor.npz")


def _final(fig, name: str, size: tuple) -> None:
    """导出 SVG + 1200 DPI PNG，并清理 SVG 行尾空白。

    输入：fig 为 matplotlib Figure，name 为输出基名（不含扩展名），
    size 为 (宽, 高) 英寸（即论文纸面尺寸）。
    输出：无返回值，写出 <name>.svg 与 <name>.png。
    边界：SVG 由 matplotlib 写入时会带行尾空格（多行 path 数据），
    这里统一 rstrip 以满足仓库空白检查；不修改任何图元内容。
    """
    export_figure(fig, basename=str(FIG_DIR / name), formats=["svg", "png"],
                  dpi=1200, size_inches=size, grayscale_preview=False)
    svg_path = FIG_DIR / f"{name}.svg"
    svg_path.write_text(
        "\n".join(line.rstrip() for line in svg_path.read_text(encoding="utf-8").splitlines()) + "\n",
        encoding="utf-8",
    )
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


def redraw_fig2_9() -> None:
    """图 2-9：7 特征 Spearman 相关矩阵（全局展平，抗零值稀疏）。"""
    feats = BUNDLE.features  # [T, N, F]
    flat = feats.reshape(-1, feats.shape[2])  # 展平 [T*N, F]：跨节点全局相关性
    corr = pd.DataFrame(flat, columns=FEATURE_CN).corr(method="spearman").to_numpy()

    fig, ax = plt.subplots(figsize=(6.4, 5.35))
    # 当前矩阵的相关系数均为非负，使用白—蓝顺序色阶突出高相关状态特征，
    # 避免在 [-1, 1] 发散色阶下将 0.99 与 0.20 都压成相近的浅红色。
    cmap = LinearSegmentedColormap.from_list(
        "corr_blue", ["#F7FAFC", "#C9DCE8", BLUE])
    im = ax.imshow(corr, cmap=cmap, vmin=0, vmax=1)
    for i in range(corr.shape[0]):
        for j in range(corr.shape[1]):
            val = corr[i, j]
            # 高相关格使用白字，弱相关格使用深灰字；对角线仍保留 1.00 作为校验。
            color = "white" if val > 0.58 else GRAY_D
            ax.text(j, i, f"{val:.2f}", ha="center", va="center",
                    fontsize=8.0, color=color, fontweight="medium")
    ax.set_xticks(range(len(FEATURE_CN)))
    ax.set_yticks(range(len(FEATURE_CN)))
    ax.set_xticklabels(FEATURE_SHORT, fontsize=8.7)
    ax.set_yticklabels(FEATURE_SHORT, fontsize=8.7)
    ax.set_xlabel("输入特征", fontsize=8.8, labelpad=8)
    ax.set_ylabel("输入特征", fontsize=8.8, labelpad=8)
    # 白色细网格明确单元格边界，避免数值与色块边界混在一起。
    n = len(FEATURE_CN)
    ax.set_xticks(np.arange(-0.5, n, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, n, 1), minor=True)
    ax.grid(which="minor", color="white", lw=1.1)
    ax.tick_params(which="both", length=0)
    for spine in ax.spines.values():
        spine.set_color(GRAY_L)
    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.035,
                        ticks=[0, 0.25, 0.50, 0.75, 1.00])
    cbar.set_label("Spearman ρ", fontsize=8.6, labelpad=6)
    cbar.ax.tick_params(labelsize=7.6, length=3)
    fig.subplots_adjust(left=0.15, right=0.875, bottom=0.15, top=0.965)
    _final(fig, "fig2_10_feature_correlation", (6.4, 5.35))
    return None


def redraw_fig2_10() -> None:
    """图 2-10：星期×小时聚合负荷热力图（全节点均值，双周期视图）。"""
    t = BUNDLE.targets  # [T, N]
    # 时间戳按数据协议以 UTC 存储；星期与小时聚合必须使用站点当地日历。
    ts = pd.to_datetime(BUNDLE.timestamps_ns, utc=True).tz_convert("America/Los_Angeles")
    df = pd.DataFrame({"load": t.mean(axis=1), "ts": ts})
    df["weekday"] = df["ts"].dt.weekday  # 0=周一
    df["hour"] = df["ts"].dt.hour
    pivot = df.pivot_table(index="weekday", columns="hour",
                           values="load", aggfunc="mean")
    mat = pivot.reindex([0, 1, 2, 3, 4, 5, 6]).to_numpy()

    fig, ax = plt.subplots(figsize=(7.6, 3.6))
    cmap = LinearSegmentedColormap.from_list(
        "load_ramp", ["#FFFFFF", "#C9DCE8", "#2C5F8A"])
    im = ax.imshow(mat, cmap=cmap, aspect="auto", zorder=1,
                   vmin=0, vmax=mat.max())
    # 周末不再用暖色底纹覆盖数据色阶；改用同一蓝灰色系的分隔线、标签和独立标识。
    weekend_color = "#5F7890"
    ax.axhline(4.5, color=weekend_color, lw=1.15, alpha=0.82, zorder=3)
    ax.set_xticks(range(24))
    ax.set_xticklabels([f"{h:02d}" for h in range(24)], fontsize=7.2)
    ax.set_yticks(range(7))
    weekday_labels = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    ax.set_yticklabels(weekday_labels, fontsize=7.8)
    for idx in (5, 6):
        ax.get_yticklabels()[idx].set_color(weekend_color)
        ax.get_yticklabels()[idx].set_fontweight("bold")
    ax.set_xlabel("当地小时（0–23；America/Los_Angeles）", fontsize=8.2)
    ax.set_ylabel("星期", fontsize=8.6)
    ax.tick_params(length=0)
    # 标出 6 小时相位边界，帮助读者快速识别日内节律，但不增加单元格文字。
    for hour in (6, 12, 18):
        ax.axvline(hour - 0.5, color="white", lw=0.8, alpha=0.65, zorder=3)
    cbar = fig.colorbar(im, ax=ax, fraction=0.045, pad=0.03)
    cbar.set_label("节点代理负荷均值（kWh/15 min）", fontsize=7.6)
    cbar.ax.tick_params(labelsize=7.5)
    _clean(ax, grid_axis=None)
    _final(fig, "fig2_11_weekday_hour_heatmap", (7.6, 3.6))
    return None


# redraw_fig2_7（图2-9 事件分量构成）已于 2026-10-27 随该图撤出主文而删除；
# 原图归档于 outputs/figures/archive/2026-10-27-fig2-9-withdrawn/。


def redraw_fig2_8() -> None:
    """图 2-8：事件窗口长度分布 + 逐节点窗口数（冻结规则，向未来扩展）。

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

    # 只保留 A/B 两个数据面板；统计摘要放入图注，不在图中央叠加文字卡片。
    fig = plt.figure(figsize=(9.8, 4.25), constrained_layout=False)
    gs = GridSpec(1, 2, figure=fig, width_ratios=[1.15, 1.45],
                  left=0.075, right=0.985, bottom=0.22, top=0.80, wspace=0.30)

    ax = fig.add_subplot(gs[0, 0])
    max_len = max(int(lens.max()), 6)
    xs = np.arange(1, max_len + 1)
    counts = np.bincount(lens.astype(int), minlength=max_len + 1)[1:]
    colors = [BLUE if x == 3 else ORANGE if x == 6 else GRAY_L for x in xs]
    ax.bar(xs, counts, width=0.66, color=colors, edgecolor="white", lw=0.8, zorder=3)
    for x, c in zip(xs, counts):
        if c > 0:
            if c > 3:
                ax.text(x, c - max(counts) * 0.035, str(c), ha="center", va="top",
                        fontsize=7.0, color="white", fontweight="bold")
            else:
                ax.text(x, c + max(counts) * 0.025, str(c), ha="center", va="bottom",
                        fontsize=7.0, color=GRAY_D)
    ax.set_xlabel("窗口长度（15 min 时间片）", fontsize=8.4)
    ax.set_ylabel("窗口数", fontsize=8.4)
    ax.set_xticks(xs)
    ax.set_ylim(0, max(counts) * 1.18)
    _clean(ax)
    fig.text(0.075, 0.885, "A 事件窗口长度分布", ha="left", va="center",
             fontsize=9.2, color=GRAY_D)

    ax = fig.add_subplot(gs[0, 1])
    ys = np.arange(len(BUNDLE.node_ids))
    ax.barh(ys, per_node_count, height=0.62, color=ORANGE,
            edgecolor="white", lw=0.6, zorder=3)
    for yi, c in enumerate(per_node_count):
        ax.text(c + 0.8, yi, str(c), ha="left", va="center",
                fontsize=7.0, color=GRAY_D)
    ax.set_yticks(ys)
    ax.set_yticklabels(BUNDLE.node_ids, fontsize=7.4)
    ax.set_xlabel("事件窗口数（测试集）", fontsize=8.4)
    ax.set_xlim(0, max(per_node_count) * 1.18)
    ax.invert_yaxis()
    _clean(ax, "x")
    fig.text(0.53, 0.885, "B 逐节点窗口数", ha="left", va="center",
             fontsize=9.2, color=GRAY_D)
    _final(fig, "fig2_12_event_window_length", (9.8, 4.25))
    return None


if __name__ == "__main__":
    print("=== 批次 11：第 2 章主文 3 图 ===")
    redraw_fig2_8()
    redraw_fig2_9()
    print("批次 11 完成")
