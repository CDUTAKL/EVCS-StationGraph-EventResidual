"""SG-EXP-028 JPL 验证新增结果图：图 3-15、图 3-16。

- 图 3-15 JPL 整体 MAE 与预登记时间块比较（双面板）：
    A. 四模型整体测试 MAE，三种子独立点 + 均值 ± 样本 SD；
    B. 三对照 baseline − MRG 配对差值 + 7 日块 Bonferroni 校正
       98.333333% percentile bootstrap 区间（24 块，10,000 次重采样）。
- 图 3-16 JPL 分层误差（2×2 小面板）：事件 / 稳定 / 零目标 / 非零目标 MAE，
  四模型 × 三种子点 + 均值 ± 样本 SD，各面板独立 y 轴并显式标刻度。

数据契约（绘图说明 §5）：
- 只从 outputs/SG-EXP-028-analysis/ 的 CSV 读取，不手写汇总值或区间端点；
- 主比较只取 paired_intervals.csv 中 block_days=7 的行，区间列取
  ci98_333333_lower/upper；block_days=1 为敏感性分析，不入图；
- 均值 ± SD 只指三个训练种子（2024/2025/2026）的样本均值与样本标准差，
  与右图时间块 bootstrap 区间是两种不同的不确定性表达；
- 逐种子均值/SD 与 model_summary.csv 逐项断言核对（rtol=1e-9）。

输出：outputs/figures/fig3_15_jpl_mae_primary.{svg,png}、
      outputs/figures/fig3_16_jpl_stratified_mae.{svg,png}
      （SVG + 1200 DPI PNG），各附 *_source.json 记录数据路径、SHA-256
      与运行环境版本。

从仓库根目录运行：.venv/bin/python scripts/figures/batch23_jpl_figs.py
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path.home() / ".claude/skills/scipilot-figure-skill/scripts"))
try:
    from export_figure import export_figure  # noqa: E402
    from setup_style import setup_style  # noqa: E402
except ImportError:  # 无 skill 环境回退（与 batch12/batch_priority_results 同一约定）
    from _skill_compat import export_figure, setup_style  # noqa: E402

FIG_DIR = Path("outputs/figures")
FIG_DIR.mkdir(parents=True, exist_ok=True)
setup_style(journal="general", lang="zh")

DATA_DIR = Path("outputs/SG-EXP-028-analysis")
PER_SEED_CSV = DATA_DIR / "per_seed.csv"
INTERVALS_CSV = DATA_DIR / "paired_intervals.csv"
SUMMARY_CSV = DATA_DIR / "model_summary.csv"

GRAY_D = "#404040"
GRAY_L = "#C8C8C8"
ZERO_LINE = "#929DA6"
GRID_XL = "#E8EDF0"

SEEDS = (2024, 2025, 2026)

# 模型顺序与配色固定（绘图说明 §2 / §5.4）：
# MRG-GCN 低饱和蓝灰；TCN 暖灰；AGCRN 中性灰棕；共享门控浅金灰。
MODELS = [
    ("mrg_full", "MRG-GCN", "#2C5F8A"),
    ("tcn_wide", "TCN", "#A89A88"),
    ("agcrn_full", "AGCRN", "#7D7264"),
    ("mrg_shared_gate", "共享门控", "#C7B07A"),
]
# 右图对照顺序：TCN、完整 AGCRN、共享门控（与 README §6.2 表一致）
BASELINES = [
    ("tcn_wide", "TCN"),
    ("agcrn_full", "完整 AGCRN"),
    ("mrg_shared_gate", "共享门控"),
]
# STRATA 第三元为 y 轴刻度格式：统一按面板量级固定小数位，避免 %.4g 在
# 同一根轴上混排 "0.42" 与 "0.426" 这类不同精度（数据已被契约断言冻结，
# 按面板写死精度是显式而安全的）。
STRATA = [
    ("event_mae", "事件", "%.3f"),
    ("stable_mae", "稳定", "%.4f"),
    ("zero_mae", "零目标", "%.3f"),
    ("nonzero_mae", "非零目标", "%.3f"),
]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _final(fig, name: str, size: tuple) -> None:
    """导出 SVG + 1200 DPI PNG，并清理 SVG 行尾空白（与 batch12 同一约定）。"""
    export_figure(fig, basename=str(FIG_DIR / name), formats=["svg", "png"],
                  dpi=1200, size_inches=size, grayscale_preview=False)
    svg_path = FIG_DIR / f"{name}.svg"
    svg_path.write_text(
        "\n".join(line.rstrip() for line in svg_path.read_text(encoding="utf-8").splitlines()) + "\n",
        encoding="utf-8",
    )
    print(f"  ✅ {name}")


def _write_source(name: str, extra: dict) -> None:
    """伴随日志：数据文件 SHA、环境版本与图件元信息（不写入图面）。"""
    payload = {
        "figure": name,
        "data_files": {p.name: _sha256(p) for p in (PER_SEED_CSV, INTERVALS_CSV, SUMMARY_CSV)},
        "python": sys.version.split()[0],
        "matplotlib": matplotlib.__version__,
        "pandas": pd.__version__,
        "numpy": np.__version__,
    }
    payload.update(extra)
    (FIG_DIR / f"{name}_source.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _clean(ax, grid_axis="y") -> None:
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color(GRAY_D)
        ax.spines[spine].set_linewidth(0.6)
    ax.tick_params(labelsize=7.2, colors=GRAY_D)
    if grid_axis:
        ax.grid(axis=grid_axis, color=GRAY_L, lw=0.55, alpha=0.72, zorder=0)
        ax.set_axisbelow(True)


def _load_per_seed() -> pd.DataFrame:
    """读取逐种子指标并做契约断言；返回按 MODELS 顺序索引的 DataFrame。"""
    df = pd.read_csv(PER_SEED_CSV)
    assert set(df["model"]) == {m for m, _, _ in MODELS}, "模型集与冻结矩阵不符"
    assert df.groupby("model")["seed"].apply(set).eq(set(SEEDS)).all(), "种子集不齐"
    assert (df["keys"] == 632640).all(), "测试键数异常"
    # 与 model_summary.csv 逐项核对三种子均值/样本 SD（绘图说明 §6 可溯源要求）
    summary = pd.read_csv(SUMMARY_CSV).set_index("model")
    for model, _, _ in MODELS:
        sub = df[df["model"] == model]
        for col in ("mae", "rmse", "event_mae", "stable_mae", "zero_mae", "nonzero_mae"):
            assert np.isclose(sub[col].mean(), summary.loc[model, f"{col}_mean"], rtol=1e-9), \
                f"{model}.{col} 均值与 model_summary.csv 不一致"
            assert np.isclose(sub[col].std(ddof=1), summary.loc[model, f"{col}_std"], rtol=1e-9), \
                f"{model}.{col} SD 与 model_summary.csv 不一致"
    return df


def _load_intervals() -> pd.DataFrame:
    """主比较区间：只取 block_days=7 与 Bonferroni 校正的 98.333333% 列。"""
    iv = pd.read_csv(INTERVALS_CSV)
    iv = iv[iv["block_days"] == 7].set_index("baseline")
    assert sorted(iv.index) == sorted(b for b, _ in BASELINES), "7 日块对照集不符"
    assert (iv["blocks"] == 24).all(), "七日块数应为 24"
    assert (iv["difference"] > 0).all(), "主比较差值应为正（baseline − MRG）"
    assert (iv["ci98_333333_lower"] > 0).all(), "校正区间下界应排除 0"
    return iv


def _draw_seed_panel(ax, df: pd.DataFrame, metric: str, ylabel: str | None,
                     show_xticklabels: bool = True,
                     dot_dx: float = 0.16, mean_dx: float = 0.28) -> None:
    """四模型 × 三种子点 + 均值 ± 样本 SD 误差条（两图共用的绘制原语）。

    dot_dx/mean_dx 控制种子点散布与均值符号的横向偏移；窄面板（图 3-16）
    需拉开避免点与均值菱形叠合。
    """
    x = np.arange(len(MODELS))
    for i, (model, _label, color) in enumerate(MODELS):
        sub = df[df["model"] == model].set_index("seed")
        vals = np.array([sub.loc[s, metric] for s in SEEDS])
        for k, v in enumerate(vals):
            ax.plot(i + (k - 1) * dot_dx, v, marker="o", ms=3.0, mfc=color,
                    mec="white", mew=0.6, linestyle="none", zorder=4, alpha=0.85)
        mean, sd = vals.mean(), vals.std(ddof=1)
        ax.errorbar(i + mean_dx, mean, yerr=sd, fmt="none", ecolor=color,
                    elinewidth=1.2, capsize=2.5, capthick=1.2, zorder=5)
        ax.plot(i + mean_dx, mean, marker="D", ms=4.0, mfc=color, mec="white",
                mew=0.7, linestyle="none", zorder=6)
    ax.set_xticks(x)
    if show_xticklabels:
        ax.set_xticklabels([label for _, label, _ in MODELS], fontsize=7.2)
    else:
        ax.set_xticklabels([] * len(MODELS))
    ax.set_xlim(-0.55, len(MODELS) - 0.55 + mean_dx + 0.12)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=8.0)
    _clean(ax)


def fig3_15() -> None:
    """图 3-15：JPL 整体 MAE（左）与预登记 7 日块配对差值区间（右）。"""
    df = _load_per_seed()
    iv = _load_intervals()

    FIG_W, FIG_H = 5.59, 2.55
    fig = plt.figure(figsize=(FIG_W, FIG_H))
    fig.set_layout_engine("none")
    ax_l = fig.add_axes([0.088, 0.195, 0.40, 0.66])
    # 右面板左移并收窄：xlabel 以面板中心对齐，全宽括号/减号经 CJK 回退字体
    # 渲染时 matplotlib 的 tight bbox 度量偏小，旧版靠底注把画布撑宽才未露馅；
    # 底注删除后须让 xlabel 真实宽度落在画布内（中心 0.769，右端约 5.47 in）。
    ax_r = fig.add_axes([0.599, 0.195, 0.34, 0.66])

    # ---- 左面板：四模型整体 MAE ----
    _draw_seed_panel(ax_l, df, "mae", "整体 MAE（kWh/15 min）")
    # y 轴不从 0 起：四种配置整体 MAE 集中在 0.081–0.084，零点起会让三种子
    # 散布不可辨；刻度显式标注，非静默截断（绘图说明 §5.7）。
    ax_l.set_ylim(0.0802, 0.0848)
    ax_l.set_yticks([0.081, 0.082, 0.083, 0.084])
    ax_l.tick_params(axis="y", labelsize=7.2)
    # 均值 ± SD 图例样张（右下角，避免遮点）
    from matplotlib.lines import Line2D
    handles = [
        Line2D([], [], marker="o", ms=3.0, linestyle="none", color=GRAY_D,
               mfc=GRAY_D, mec="white", mew=0.6, alpha=0.85),
        Line2D([], [], marker="D", ms=4.0, linestyle="none", color=GRAY_D,
               mfc=GRAY_D, mec="white", mew=0.7),
    ]
    ax_l.legend(handles, ["单个种子", "均值 ± SD"], loc="lower right",
                fontsize=7.0, frameon=False, handletextpad=0.35,
                borderaxespad=0.1, labelspacing=0.35)
    ax_l.text(0.0, 1.07, "A  整体测试 MAE", transform=ax_l.transAxes,
              fontsize=9, fontweight="bold", color="#2B2B2B")

    # ---- 右面板：baseline − MRG 配对差值 + 校正区间 ----
    ys = np.arange(len(BASELINES))[::-1]
    for y, (baseline, label) in zip(ys, BASELINES):
        row = iv.loc[baseline]
        d, lo, hi = (row["difference"], row["ci98_333333_lower"],
                     row["ci98_333333_upper"])
        color = dict((m, c) for m, _l, c in MODELS)[baseline]
        ax_r.errorbar(d, y, xerr=[[d - lo], [hi - d]], fmt="o", ms=5.0,
                      color=color, ecolor=color, elinewidth=1.3, capsize=3.0,
                      capthick=1.3, mec="white", mew=0.7, zorder=4)
        ax_r.annotate(f"{d:.4f}", (hi, y), xytext=(5, 0),
                      textcoords="offset points", va="center", fontsize=7.4,
                      color=GRAY_D)
    ax_r.axvline(0, color=ZERO_LINE, lw=0.9, zorder=2)
    ax_r.set_yticks(ys)
    ax_r.set_yticklabels([label for _, label in BASELINES], fontsize=7.4)
    ax_r.set_ylim(-0.6, len(BASELINES) - 0.4)
    ax_r.set_xlim(-0.0006, 0.0068)
    # 两行书写 xlabel：单行全宽括号/减号经 CJK 回退字体渲染时 matplotlib 的
    # tight bbox 度量偏小，右端会被裁掉 1–2 字符；拆成两行后每行真实宽度都
    # 落在纯 ASCII 数值标注（度量准确）定义的画布右缘之内，且保持居中。
    ax_r.set_xlabel("MAE 差值（对照 − MRG-GCN）\n（kWh/15 min）", fontsize=8.0)
    _clean(ax_r, grid_axis="x")
    ax_r.tick_params(axis="x", labelsize=7.2)
    ax_r.text(0.0, 1.07, "B  配对差值与预登记区间", transform=ax_r.transAxes,
              fontsize=9, fontweight="bold", color="#2B2B2B")
    # 区间语义（7 日块、24 块、10,000 次重采样、Bonferroni 98.33%）由论文
    # 图 3-15 图注承载，图内不再置底注（底注会拖出大面积空白）；机器可核对的
    # 同口径信息仍写入 fig3_15_jpl_mae_primary_source.json。

    _final(fig, "fig3_15_jpl_mae_primary", (FIG_W, FIG_H))
    _write_source("fig3_15_jpl_mae_primary", {
        "left_panel": "整体 MAE：三种子点 + 均值 ± 样本 SD（per_seed.csv::mae）",
        "right_panel": "paired_intervals.csv block_days=7；区间列 ci98_333333_*；"
                       "差值方向 baseline − MRG；24 个 7 日块；10,000 次重采样",
        "model_order": [m for m, _, _ in MODELS],
        "seeds": list(SEEDS),
    })


def fig3_16() -> None:
    """图 3-16：JPL 分层 MAE（事件/稳定/零目标/非零目标，2×2 独立 y 轴）。"""
    df = _load_per_seed()

    FIG_W, FIG_H = 5.59, 3.85
    fig = plt.figure(figsize=(FIG_W, FIG_H))
    fig.set_layout_engine("none")
    # 2×2 布局：上下各两面板，列间距容纳右列 y 轴刻度标签
    COL_LEFT, COL_W = [0.105, 0.625], 0.345
    ROW_BOT, ROW_H = [0.555, 0.115], 0.315
    axes = [fig.add_axes([COL_LEFT[c], ROW_BOT[r], COL_W, ROW_H])
            for r in range(2) for c in range(2)]

    from matplotlib.ticker import FormatStrFormatter, MaxNLocator
    for ax, (col, title, fmt) in zip(axes, STRATA):
        _draw_seed_panel(ax, df, col, None, show_xticklabels=True,
                         dot_dx=0.22, mean_dx=0.40)
        ax.set_title(title, fontsize=8.5, color="#2B2B2B", pad=4.0)
        # 各分层量级不同（事件 ~0.42 vs 零目标 ~0.008）：分面独立 y 轴（绘图
        # 说明 §5.7 / R2）。同一分层内模型差异仅占全量程 2–5%，从 0 起会让
        # 四组点在面板顶部压成一条线，分层结论（TCN 事件/非零目标更低、
        # MRG 零目标/稳定更低）完全不可辨；故按面板取数据范围 + 15% 留白，
        # 刻度显式标注、四面板刻度规则一致，并在图注中声明 y 轴非零起点。
        vals = df[col].to_numpy()
        lo, hi = vals.min(), vals.max()
        pad = 0.15 * (hi - lo)
        ax.set_ylim(lo - pad, hi + pad)
        ax.yaxis.set_major_locator(MaxNLocator(4))
        ax.yaxis.set_major_formatter(FormatStrFormatter(fmt))
        ax.tick_params(axis="x", labelsize=7.0)
    axes[0].set_ylabel("MAE（kWh/15 min）", fontsize=8.0)
    axes[2].set_ylabel("MAE（kWh/15 min）", fontsize=8.0)

    # 各面板已带模型名 x 刻度，不再另设图例
    _final(fig, "fig3_16_jpl_stratified_mae", (FIG_W, FIG_H))
    _write_source("fig3_16_jpl_stratified_mae", {
        "panels": {col: f"per_seed.csv::{col}；三种子点 + 均值 ± 样本 SD"
                   for col, _t, _f in STRATA},
        "strata_definition": "冻结事件/稳定掩码与零/非零目标分层，"
                             "定义以 SG-DATA-007 协议与测试导出为准",
        "y_axis": "四面板独立量程（数据范围 ±15% 留白），非零起点，刻度显式；"
                  "理由：同分层模型差异占全量程 2–5%，零起点下不可辨",
        "model_order": [m for m, _, _ in MODELS],
        "seeds": list(SEEDS),
    })


def main() -> None:
    fig3_15()
    fig3_16()


if __name__ == "__main__":
    main()
