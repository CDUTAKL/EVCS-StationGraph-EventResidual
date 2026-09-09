"""优先订正的六幅方法/口径示意图（2026-09-07）。

这些图只表达已冻结的模型拓扑和标签口径，不由 ImageGen 生成数据或连接关系。
统一导出 SVG + 1200 dpi PNG；配色沿用论文结果图的低饱和蓝灰、浅棕、浅粉和浅黄。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon, Rectangle

sys.path.insert(0, str(Path.home() / ".claude/skills/scipilot-figure-skill/scripts"))
try:
    from export_figure import export_figure
    from setup_style import setup_style
except ImportError:
    from _skill_compat import export_figure, setup_style

FIG_DIR = Path("outputs/figures")
FIG_DIR.mkdir(parents=True, exist_ok=True)
setup_style(journal="general", lang="zh")

BLUE = "#2C5F8A"
BLUE_L = "#DCE8F2"
BLUE_XL = "#F2F6FA"
BEIGE = "#F4EBDD"
PINK = "#F4E1E5"
YELLOW = "#F3E6B3"
GREEN_L = "#E7EFE8"
GRAY_D = "#404040"
GRAY_M = "#808080"
GRAY_L = "#B9C2C9"
WHITE = "#FFFFFF"


def _save(fig, stem: str, size: tuple[float, float]) -> None:
    export_figure(fig, basename=str(FIG_DIR / stem), formats=["svg", "png"],
                  dpi=1200, size_inches=size, grayscale_preview=False)
    plt.close(fig)
    print(f"  ✅ {stem}")


def _ax(size=(12, 6.75)):
    fig, ax = plt.subplots(figsize=size)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")
    return fig, ax


def _card(ax, x, y, w, h, text, *, fc=WHITE, ec=BLUE, fs=10.0,
          lw=1.2, radius=0.8, weight="normal"):
    patch = FancyBboxPatch((x, y), w, h,
                           boxstyle=f"round,pad=0.35,rounding_size={radius}",
                           facecolor=fc, edgecolor=ec, linewidth=lw)
    ax.add_patch(patch)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=fs, color=GRAY_D, fontweight=weight, linespacing=1.18)
    return patch


def _arrow(ax, x1, y1, x2, y2, *, color=GRAY_D, lw=1.15, style="-|>",
           rad=0.0, z=5):
    connection = f"arc3,rad={rad}" if rad else "arc3"
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle=style, color=color, lw=lw,
                                shrinkA=2, shrinkB=2,
                                connectionstyle=connection), zorder=z)


def _tensor(ax, x, y, w=11, h=8, label="H", dim=None, fc=BLUE_L,
            ec=BLUE, depth=2.1, skew=2.2, fs=9.0):
    """简洁三维张量块：正面网格 + 顶面 + 右侧面，避免顶部透视错误。"""
    front = Rectangle((x, y), w, h, facecolor=fc, edgecolor=ec, linewidth=1.0)
    ax.add_patch(front)
    top = Polygon([(x, y + h), (x + skew, y + h + depth),
                   (x + w + skew, y + h + depth), (x + w, y + h)],
                  closed=True, facecolor="#EEF4F8", edgecolor=ec, linewidth=1.0)
    side = Polygon([(x + w, y), (x + w + skew, y + depth),
                    (x + w + skew, y + h + depth), (x + w, y + h)],
                   closed=True, facecolor="#C9D7E2", edgecolor=ec, linewidth=1.0)
    ax.add_patch(top)
    ax.add_patch(side)
    for i in range(1, 4):
        ax.plot([x + w * i / 4, x + w * i / 4], [y, y + h],
                color=ec, lw=0.55)
    for i in range(1, 3):
        ax.plot([x, x + w], [y + h * i / 3, y + h * i / 3],
                color=ec, lw=0.55)
    ax.text(x + w / 2, y + h + depth + 2.1, label, ha="center", va="bottom",
            fontsize=fs, color=GRAY_D)
    if dim:
        ax.text(x + w / 2, y - 2.1, dim, ha="center", va="top",
                fontsize=fs - 1.2, color=GRAY_M)


def _section(ax, x, y, w, h, label, *, fc=BLUE_XL, ec=GRAY_L, fs=9.0):
    patch = FancyBboxPatch((x, y), w, h,
                           boxstyle="round,pad=0.25,rounding_size=1.0",
                           facecolor=fc, edgecolor=ec, linewidth=1.0,
                           linestyle="-")
    ax.add_patch(patch)
    ax.text(x + 1.6, y + h - 2.4, label, ha="left", va="top",
            fontsize=fs, color=GRAY_D, fontweight="bold")
    return patch


def fig2_10_dual_window_definition() -> None:
    fig, ax = _ax((10.8, 6.0))
    _card(ax, 35, 83, 30, 9, "同一测试预测键", fc=BLUE_L, fs=11, weight="bold")
    _arrow(ax, 50, 83, 50, 77, color=BLUE, lw=1.5)
    _section(ax, 6, 43, 88, 32, "双口径并列定义", fc=BLUE_XL, ec=BLUE)
    # 上分支：目标标签只用于评价
    _card(ax, 12, 60, 22, 9, "target_event", fc=PINK, ec="#C88999", fs=10, weight="bold")
    _card(ax, 39, 60, 22, 9, "标签事件窗口", fc=WHITE, ec=BLUE, fs=9.5)
    _card(ax, 66, 60, 22, 9, "分层评价", fc=WHITE, ec=BLUE, fs=9.5)
    _arrow(ax, 34, 64.5, 39, 64.5, color=BLUE)
    _arrow(ax, 61, 64.5, 66, 64.5, color=BLUE)
    ax.text(12, 55.5, "占测试预测键 1.43% · 事后评价口径", fontsize=8.0, color=GRAY_M)
    # 下分支：冻结规则用于可部署路由
    _card(ax, 12, 47, 22, 9, "rule_trigger", fc=YELLOW, ec="#B8912F", fs=10, weight="bold")
    _card(ax, 39, 47, 22, 9, "冻结规则触发", fc=WHITE, ec=BLUE, fs=9.5)
    _card(ax, 66, 47, 22, 9, "区间路由", fc=WHITE, ec=BLUE, fs=9.5)
    _arrow(ax, 34, 51.5, 39, 51.5, color=BLUE)
    _arrow(ax, 61, 51.5, 66, 51.5, color=BLUE)
    ax.text(12, 42.5, "占测试预测键 0.43% · 预测时可见路由口径", fontsize=8.0, color=GRAY_M)
    # 小型交叉诊断节点，代替旧图中突兀的大“对照”框
    _arrow(ax, 77, 60, 77, 35, color=GRAY_M, lw=1.0)
    _arrow(ax, 77, 47, 77, 35, color=GRAY_M, lw=1.0)
    _card(ax, 64, 25, 26, 9, "四格诊断\n(target_event × rule_trigger)",
          fc=BEIGE, ec="#B8912F", fs=8.8)
    ax.text(50, 15, "两种口径不能混用：标签事件用于分层评价，冻结规则用于部署路由",
            ha="center", va="center", fontsize=9.0, color=GRAY_D)
    _save(fig, "fig2_10_dual_window_definition", (10.8, 6.0))


def _prop_card(ax, x, y, title, *, fc=BLUE_XL):
    _card(ax, x, y, 23, 11, title, fc=fc, ec=BLUE, fs=8.6)
    for i, (txt, color) in enumerate([("负荷", BLUE_L), ("行为", PINK), ("轮廓", YELLOW)]):
        _card(ax, x + 2, y + 2.0 + i * 2.4, 7.0, 1.7, txt,
              fc=color, ec=GRAY_L, fs=6.8, lw=0.7, radius=0.25)
    ax.text(x + 15.0, y + 5.5, "β_l\n关系融合", ha="center", va="center",
            fontsize=8.0, color=GRAY_D)


def fig3_1_mrggcn_architecture() -> None:
    fig, ax = _ax((7.5, 10.0))
    ax.text(50, 98, "MRG-GCN 主模型路径", ha="center", va="top",
            fontsize=12, color=GRAY_D, fontweight="bold")
    _tensor(ax, 43, 87, w=14, h=7, label="历史输入 X", dim="B×96×N")
    _arrow(ax, 50, 86.8, 50, 82.5, color=BLUE, lw=1.45)
    _card(ax, 34, 76, 32, 7, "因果扩张 TCN ×6", fc=BLUE_L, fs=10, weight="bold")
    _arrow(ax, 50, 75.8, 50, 71.5, color=BLUE, lw=1.45)
    _tensor(ax, 43, 64, w=14, h=7, label="H⁽⁰⁾", dim="B×N×D")
    _arrow(ax, 50, 63.8, 50, 59.8, color=BLUE, lw=1.35)
    _prop_card(ax, 38.5, 49, "第一层关系传播")
    _arrow(ax, 50, 48.8, 50, 44.5, color=BLUE, lw=1.35)
    _tensor(ax, 43, 37.2, w=14, h=7, label="H⁽¹⁾", dim="B×N×D")
    _arrow(ax, 50, 37.0, 50, 33.2, color=BLUE, lw=1.25)
    _card(ax, 31, 27, 38, 6, "残差 MLP 精炼\nLinear → GELU → Dropout → Linear + 残差",
          fc=BEIGE, ec="#B8912F", fs=8.4)
    _arrow(ax, 50, 26.8, 50, 23.3, color=BLUE, lw=1.25)
    _tensor(ax, 43, 16.2, w=14, h=7, label="H⁽¹,ref⁾", dim="B×N×D")
    _arrow(ax, 50, 16.0, 50, 12.8, color=BLUE, lw=1.25)
    _prop_card(ax, 38.5, 2.0, "第二层关系传播", fc=BLUE_XL)
    # 第二层输出、跨层拼接和预测头采用右侧紧凑路径，明确 H1ref 不进入拼接。
    _tensor(ax, 70, 7.0, w=12, h=6.5, label="H⁽²⁾", dim="B×N×D")
    _arrow(ax, 62, 7.5, 70, 10, color=BLUE, lw=1.15, rad=-0.12)
    _tensor(ax, 8, 7.0, w=12, h=6.5, label="H⁽⁰⁾", dim="跳连")
    _tensor(ax, 24, 7.0, w=12, h=6.5, label="H⁽¹⁾", dim="跳连")
    _arrow(ax, 20, 10, 39, 10, color=GRAY_M, lw=1.0, rad=0.12)
    _arrow(ax, 36, 10, 39, 10, color=GRAY_M, lw=1.0)
    _arrow(ax, 82, 10, 61, 10, color=GRAY_M, lw=1.0, rad=-0.12)
    _card(ax, 38, 6, 23, 8, "跨层拼接\n[ H⁽⁰⁾ ‖ H⁽¹⁾ ‖ H⁽²⁾ ]", fc=BEIGE, ec="#B8912F", fs=8.0)
    _card(ax, 38, 0.4, 23, 4.3, "预测头\nLinear–LayerNorm–GELU–Dropout–Linear", fc=GREEN_L, ec="#597A62", fs=7.0)
    _arrow(ax, 49.5, 6, 49.5, 4.8, color=BLUE, lw=1.0)
    ax.text(5, 0.7, "H⁽¹,ref⁾只进入第二层；跨层拼接只接收 H⁽⁰⁾、H⁽¹⁾、H⁽²⁾",
            fontsize=7.1, color=GRAY_M)
    _save(fig, "fig3_1_mrggcn_architecture", (7.5, 10.0))


def fig3_2_relation_propagation_unit() -> None:
    fig, ax = _ax((12, 6.75))
    ax.text(50, 96, "多关系门控传播单元（第 l 层）", ha="center", va="top",
            fontsize=12, color=GRAY_D, fontweight="bold")
    _tensor(ax, 3, 43, w=12, h=12, label="H⁽ˡ⁾", dim="B×N×D")
    rels = [(22, 66, "Â_load H⁽ˡ⁾", BLUE_L), (22, 49, "Â_event H⁽ˡ⁾", PINK),
            (22, 32, "Â_pattern H⁽ˡ⁾", YELLOW)]
    for x, y, txt, fc in rels:
        _card(ax, x, y, 22, 10, txt, fc=fc, ec=BLUE, fs=8.6)
        _arrow(ax, 15, 49, x, y + 5, color=GRAY_M, lw=0.9, rad=0.08 if y > 49 else -0.08)
    _card(ax, 49, 42, 15, 14, "β_l\nSoftmax\n关系融合", fc=BEIGE, ec="#B8912F", fs=9.0, weight="bold")
    for _, y, _, _ in rels:
        _arrow(ax, 44, y + 5, 49, 49, color=BLUE, lw=1.0)
    ax.text(56.5, 38.5, "M = Σ β_l,r W_r(Â_r H⁽ˡ⁾)", ha="center", va="center",
            fontsize=7.3, color=GRAY_M)
    _card(ax, 68, 42, 13, 14, "节点门控\nG_l = σ(·)", fc=BLUE_XL, ec=BLUE, fs=9.0, weight="bold")
    _arrow(ax, 64, 49, 68, 49, color=BLUE, lw=1.25)
    _card(ax, 85, 42, 12, 14, "残差 +\nLayerNorm", fc=GREEN_L, ec="#597A62", fs=8.4, weight="bold")
    _arrow(ax, 81, 49, 85, 49, color=BLUE, lw=1.25)
    _tensor(ax, 87, 66, w=10, h=7, label="H⁽ˡ⁺¹⁾", dim="B×N×D")
    _arrow(ax, 91, 56, 91, 66, color=BLUE, lw=1.25)
    ax.text(50, 18, "H⁽ˡ⁺¹⁾ = LayerNorm(H⁽ˡ⁾ + Dropout(G_l ⊙ M))",
            ha="center", va="center", fontsize=9.3, color=GRAY_D)
    ax.text(50, 9, "三类关系先独立传递，再经 β 融合与节点门控；关系矩阵不直接连接输出状态",
            ha="center", va="center", fontsize=8.1, color=GRAY_M)
    _save(fig, "fig3_2_relation_propagation_unit", (12, 6.75))


def fig3_3_temporal_skip_fusion() -> None:
    fig, ax = _ax((12, 6.75))
    ax.text(50, 96, "时间编码与跨层融合预测结构", ha="center", va="top",
            fontsize=12, color=GRAY_D, fontweight="bold")
    # 上方是严格串行状态路径。
    y = 70
    stages = [(3, "X", BLUE_L), (14, "因果 TCN\n×6", BLUE_L), (28, "H⁽⁰⁾", BLUE_L),
              (39, "第一层\n传播", PINK), (51, "H⁽¹⁾", BLUE_L),
              (62, "残差 MLP\n精炼", BEIGE), (75, "H⁽¹,ref⁾", BLUE_L),
              (86, "第二层\n传播", PINK)]
    for x, txt, fc in stages:
        w = 9 if txt in {"X", "H⁽⁰⁾", "H⁽¹⁾", "H⁽¹,ref⁾"} else 10
        _card(ax, x, y, w, 13, txt, fc=fc, ec=BLUE if fc != BEIGE else "#B8912F",
              fs=8.0, weight=txt in {"X", "H⁽⁰⁾", "H⁽¹⁾", "H⁽¹,ref⁾"})
    for (x1, txt1, _), (x2, txt2, _) in zip(stages[:-1], stages[1:]):
        w1 = 9 if txt1 in {"X", "H⁽⁰⁾", "H⁽¹⁾", "H⁽¹,ref⁾"} else 10
        _arrow(ax, x1 + w1, y + 6.5, x2, y + 6.5, color=BLUE, lw=1.05)
    _tensor(ax, 90, 71, w=7, h=10, label="H⁽²⁾", dim="B×N×D", fs=8.4)
    _arrow(ax, 96, 76, 90, 76, color=BLUE, lw=1.05)
    # 下方只接原始层状态 H0/H1/H2，H1ref 没有跳入拼接。
    ax.plot([30, 30, 15, 15], [70, 60, 60, 51], color=GRAY_M, lw=1.0)
    ax.plot([53, 53, 32, 32], [70, 55, 55, 51], color=GRAY_M, lw=1.0)
    ax.plot([93, 93, 51, 51], [71, 50, 50, 51], color=GRAY_M, lw=1.0)
    for x, label in [(15, "H⁽⁰⁾"), (32, "H⁽¹⁾"), (51, "H⁽²⁾")]:
        _card(ax, x, 37, 13, 10, label + "\n跨层输入", fc=BLUE_XL, ec=BLUE, fs=8.0)
        _arrow(ax, x + 6.5, 37, 50, 30, color=GRAY_M, lw=0.9)
    _card(ax, 38, 22, 24, 8, "跨层拼接\nH⁽⁰⁾ ‖ H⁽¹⁾ ‖ H⁽²⁾", fc=BEIGE, ec="#B8912F", fs=9.0, weight="bold")
    _arrow(ax, 50, 22, 50, 16, color=BLUE, lw=1.2)
    _card(ax, 35, 7, 30, 9, "预测头\nLinear–LayerNorm–GELU–Dropout–Linear", fc=GREEN_L, ec="#597A62", fs=8.0)
    _arrow(ax, 50, 7, 50, 3.2, color=BLUE, lw=1.1)
    _tensor(ax, 70, 3, w=16, h=7, label="Ŷ", dim="B×4×N", fs=9.0)
    _arrow(ax, 65, 11, 70, 7, color=BLUE, lw=1.0, rad=-0.12)
    ax.text(50, 0.5, "串行传播：H⁰ → H¹ → H¹,ref → H²；跨层拼接不包含 H¹,ref",
            ha="center", va="bottom", fontsize=7.8, color=GRAY_M)
    _save(fig, "fig3_3_temporal_skip_fusion", (12, 6.75))


def fig3_4_lre_construction() -> None:
    fig, ax = _ax((12, 6.75))
    ax.text(50, 96, "LRE 三关系构建：训练期统计、分路稀疏、独立归一化",
            ha="center", va="top", fontsize=12, color=GRAY_D, fontweight="bold")
    rows = [(70, "训练期负荷序列", "|Pearson|", "Â_load", BLUE_L),
            (48, "训练期行为信号", "Cosine", "Â_event", PINK),
            (26, "96步负荷轮廓", "欧氏指数核", "Â_pattern", YELLOW)]
    for y, source, metric, out, fc in rows:
        _card(ax, 4, y, 18, 10, source, fc=BLUE_XL, ec=BLUE, fs=8.5)
        _arrow(ax, 22, y + 5, 29, y + 5, color=BLUE)
        _card(ax, 29, y, 16, 10, metric, fc=fc, ec=GRAY_L, fs=8.4)
        _arrow(ax, 45, y + 5, 52, y + 5, color=BLUE)
        _card(ax, 52, y, 14, 10, "Top-k\nk=3", fc=BEIGE, ec="#B8912F", fs=8.5)
        _arrow(ax, 66, y + 5, 72, y + 5, color=BLUE)
        _card(ax, 72, y, 13, 10, "无向并集", fc=WHITE, ec=BLUE, fs=8.4)
        _arrow(ax, 85, y + 5, 91, y + 5, color=BLUE)
        _card(ax, 91, y, 8, 10, out, fc=BLUE_L, ec=BLUE, fs=7.5, weight="bold")
    ax.text(58, 17, "D⁻¹ᐟ² A D⁻¹ᐟ²", ha="center", va="center", fontsize=10, color=GRAY_D)
    ax.text(58, 11, "每一类关系独立归一化后作为传播输入，不在构图阶段三者合并",
            ha="center", va="center", fontsize=8.2, color=GRAY_M)
    _card(ax, 6, 5, 28, 8, "仅训练集构建\n测试集不参与关系统计", fc=GREEN_L, ec="#597A62", fs=8.6)
    _card(ax, 66, 5, 28, 8, "统计关系 ≠ 物理拓扑\n也不直接等同于因果关系", fc=BEIGE, ec="#B8912F", fs=8.4)
    _save(fig, "fig3_4_lre_construction", (12, 6.75))


def fig5_6_conformal_method() -> None:
    fig, ax = _ax((12, 6.75))
    ax.text(50, 96, "冻结规则路由的分层共形方法", ha="center", va="top",
            fontsize=12, color=GRAY_D, fontweight="bold")
    # 公共校准主干，两个分层分支都从同一个残差节点出发。
    for x, txt, fc in [(5, "冻结主模型", BLUE_L), (22, "验证集前向", BLUE_L),
                       (39, "残差 r=|y−ŷ|", BEIGE), (56, "按冻结规则分层", BLUE_XL)]:
        _card(ax, x, 75, 14, 10, txt, fc=fc, ec=BLUE if fc != BEIGE else "#B8912F", fs=8.4)
    _arrow(ax, 19, 80, 22, 80, color=BLUE)
    _arrow(ax, 36, 80, 39, 80, color=BLUE)
    _arrow(ax, 53, 80, 56, 80, color=BLUE)
    # 两个校准分支。
    _section(ax, 5, 44, 42, 23, "校准层", fc=PINK, ec="#C88999")
    _card(ax, 9, 51, 15, 9, "rule_trigger=1\n事件层", fc=WHITE, ec="#C88999", fs=8.1)
    _card(ax, 28, 51, 15, 9, "q_evt", fc=BEIGE, ec="#B8912F", fs=9.0, weight="bold")
    _arrow(ax, 24, 55.5, 28, 55.5, color=BLUE)
    _section(ax, 53, 44, 42, 23, "校准层", fc=BLUE_XL, ec=BLUE)
    _card(ax, 57, 51, 15, 9, "rule_trigger=0\n稳定层", fc=WHITE, ec=BLUE, fs=8.1)
    _card(ax, 76, 51, 15, 9, "q_stable,n", fc=BEIGE, ec="#B8912F", fs=8.6, weight="bold")
    _arrow(ax, 72, 55.5, 76, 55.5, color=BLUE)
    _arrow(ax, 63, 75, 16, 60, color=BLUE, rad=0.12)
    _arrow(ax, 63, 75, 64, 60, color=BLUE, rad=-0.12)
    # 部署路径明确使用可见规则，不让目标标签接入路由。
    _card(ax, 8, 27, 22, 9, "预测时刻可见\n冻结规则信号", fc=YELLOW, ec="#B8912F", fs=8.3)
    _card(ax, 39, 27, 22, 9, "选择区间半宽 q", fc=GREEN_L, ec="#597A62", fs=8.8, weight="bold")
    _card(ax, 70, 27, 22, 9, "ŷ ± q", fc=BLUE_L, ec=BLUE, fs=10, weight="bold")
    _arrow(ax, 30, 31.5, 39, 31.5, color=BLUE, lw=1.3)
    _arrow(ax, 61, 31.5, 70, 31.5, color=BLUE, lw=1.3)
    _arrow(ax, 35, 51, 50, 36, color=GRAY_M, lw=0.9, rad=0.12)
    _arrow(ax, 84, 51, 50, 36, color=GRAY_M, lw=0.9, rad=-0.12)
    _card(ax, 24, 8, 52, 8, "α=0.1 · 目标覆盖率90% · target_event仅用于事后评价，不驱动部署路由",
          fc=WHITE, ec=GRAY_L, fs=8.0)
    _save(fig, "fig5_6_conformal_method", (12, 6.75))


if __name__ == "__main__":
    fig2_10_dual_window_definition()
    fig3_1_mrggcn_architecture()
    fig3_2_relation_propagation_unit()
    fig3_3_temporal_skip_fusion()
    fig3_4_lre_construction()
    fig5_6_conformal_method()
