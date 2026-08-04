"""论文图批次 16：三张流程/框架示意图（图 2-1 / 图 4-1 / 图 5-1）。

示意类图形（2026-08-04 用户要求"精致复杂、细节拉满"）：
- 图 2-1 数据重构流程：会话 CSV → 审计门禁 → 15 min 能量聚合 →
  张量构建 → 数据划分（第 2 章）
- 图 4-1 三层机制诊断框架：L1 门控归因 / L2 结构验证 / L3 误差归属
  的"问题→检验→证据→结论"四环节协议（第 4 章）
- 图 5-1 第 5 章技术路线图：三问题 → 三方向 → 三证据 → 统一闭环

统一规范：无标题、无章节号/实验代号/文件名、SVG+PNG 1200 DPI、
色盲安全配色 + 冗余编码、中文渲染。
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

sys.path.insert(0, str(Path.home() / ".claude/skills/scipilot-figure-skill/scripts"))
try:
    from export_figure import export_figure  # noqa: E402
    from setup_style import setup_style  # noqa: E402
except ImportError:  # 无 skill 环境回退
    from _skill_compat import export_figure, setup_style  # noqa: E402

FIG_DIR = Path("outputs/figures")
FIG_DIR.mkdir(parents=True, exist_ok=True)
setup_style(journal="general", lang="zh")

# 色盲安全低饱和色板（冗余编码：颜色 + 形状 + 线型共同区分）
BLUE = "#2C5F8A"      # 深蓝（主流程 / 第一层）
ORANGE = "#D08A3C"    # 低饱和橙（第二层 / 证据）
GREEN = "#4C7A5C"     # 低饱和绿（第三层 / 结论）
RED_S = "#B05A4A"     # 低饱和红（约束 / 警示）
GRAY_D = "#404040"
GRAY_M = "#808080"
GRAY_L = "#C8C8C8"
BG = "#F5F2EC"        # 米白卡片底


def final(fig, name: str, size: tuple[float, float]) -> None:
    """统一导出：SVG 矢量 + PNG 1200 DPI（论文硬性约束）。"""
    export_figure(
        fig, basename=str(FIG_DIR / name),
        formats=["svg", "png"], dpi=1200, size_inches=size,
        grayscale_preview=False,
    )
    print("  ✅ {}".format(name))


def _card(ax, x, y, w, h, text, *, fc=BG, ec=GRAY_M, fs=9, weight="normal",
          align="center", lw=1.0, radius=0.02, text_color=GRAY_D):
    """圆角卡片：白底描边 + 居中文本（可多行，\\n 换行）。"""
    box = FancyBboxPatch(
        (x, y), w, h, boxstyle=f"round,pad=0.006,rounding_size={radius}",
        fc=fc, ec=ec, lw=lw, zorder=3,
    )
    ax.add_patch(box)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=fs, color=text_color, fontweight=weight, zorder=4)


def _arrow(ax, x1, y1, x2, y2, *, color=GRAY_M, lw=1.4, style="-|>",
           ls="-", ms=11, zorder=2, shrink=0.0):
    """流程箭头：默认实线实心箭头，可换虚线。"""
    ax.add_patch(FancyArrowPatch(
        (x1, y1), (x2, y2), arrowstyle=style, mutation_scale=ms,
        color=color, lw=lw, linestyle=ls, shrinkA=shrink, shrinkB=shrink,
        zorder=zorder,
    ))


def _badge(ax, cx, cy, r, text, *, fc=BLUE, fs=8, tc="white"):
    """编号徽章：圆形色块 + 白色编号（冗余编码）。"""
    circle = mpatches.Circle((cx, cy), r, fc=fc, ec="white", lw=1.2, zorder=5)
    ax.add_patch(circle)
    ax.text(cx, cy, text, ha="center", va="center", fontsize=fs,
            color=tc, fontweight="bold", zorder=6)


# ========== 图 2-1 数据重构流程 ==========

def fig2_1_data_reconstruction() -> None:
    """第 2 章：数据重构流程示意图。

    布局（横版）：左=数据源、中=审计门禁→能量聚合→张量构建、
    右=数据划分；底部约束条标注无泄漏口径。
    """
    fig, ax = plt.subplots(figsize=(12.2, 6.0))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 60)
    ax.axis("off")

    # ---------- 左：数据源 ----------
    _card(ax, 2, 34, 20, 22,
          "充电运营平台\n充电会话记录 CSV\n\n31,424 条会话 · 约 3.4 年\n"
          "2018-04-25 ~ 2021-09-14\n\n字段：节点标识 / 起止时刻\n"
          "充电能量 / 会话状态",
          fc=BG, ec=BLUE, lw=1.4, fs=8.5)
    ax.text(12, 57.6, "数据源", ha="center", fontsize=10,
            fontweight="bold", color=BLUE)
    # 字段标签微注（审计对象）
    ax.text(12, 31.5, "审计对象：\n时间戳一致性 · 节点标识 · 能量字段",
            ha="center", va="top", fontsize=7, color=GRAY_M)

    # 左→中 主箭头
    _arrow(ax, 22.5, 45, 27.5, 45, color=BLUE, lw=1.8, ms=12)

    # ---------- 中：三步流程（竖直） ----------
    mid_x, mid_w = 32, 38
    steps = [
        ("审计门禁", "① 时间片计数与采样间隔核验\n② 节点标识唯一映射审计\n"
         "③ 缺失值 / 枚举值逐字段统计", BLUE),
        ("能量聚合", "会话能量按 15 min 固定间隔\n归并到对应时间片\n"
         "逐充电单元（spaceID）生成代理负荷", ORANGE),
        ("张量构建", "节点代理负荷张量 [T, N, F]\nT = 118,818 · N = 10 · F = 7\n"
         "特征：负荷 / 接入 / 离站 / 活跃\n占用率 / 需求强度 / 负荷跳变", GREEN),
    ]
    y_pos = 47
    step_h = 10
    for title, body, color in steps:
        _card(ax, mid_x, y_pos - step_h, mid_w, step_h, body,
              fc=BG, ec=color, lw=1.4, fs=8)
        _badge(ax, mid_x + 1.6, y_pos - step_h / 2, 1.5, title[:1],
               fc=color)
        ax.text(mid_x + 4.2, y_pos - step_h / 2, title, ha="left",
                va="center", fontsize=9, fontweight="bold", color=color)
        if y_pos > 47:
            _arrow(ax, mid_x + mid_w / 2, y_pos - step_h - 0.6,
                   mid_x + mid_w / 2, y_pos - step_h + 1.2, color=GRAY_M,
                   lw=1.3, ms=10)
        y_pos -= step_h + 2.5
    # 审计结果旁注（门禁通过）
    ax.text(mid_x + mid_w + 1.2, 47 - step_h / 2, "通过",
            ha="left", va="center", fontsize=8, color=GREEN,
            fontweight="bold")

    # 中→右 主箭头
    _arrow(ax, 70.5, 45, 75.5, 45, color=BLUE, lw=1.8, ms=12)

    # ---------- 右：数据划分 ----------
    _card(ax, 76, 28, 22, 26,
          "数据划分（按预测起点）\n\n训练 83,103\n验证 17,807\n测试 17,809\n\n"
          "窗口严格按 split 边界\n索引，不跨边界、\n不使用未来信息",
          fc=BG, ec=GREEN, lw=1.4, fs=8.5)
    ax.text(87, 58.2, "训练 / 验证 / 测试", ha="center", fontsize=10,
            fontweight="bold", color=GREEN)

    # ---------- 底部约束条 ----------
    bar = mpatches.FancyBboxPatch(
        (4, 6), 92, 7, boxstyle="round,pad=0.008,rounding_size=0.5",
        fc="#FDF3F1", ec=RED_S, lw=1.3, zorder=3,
    )
    ax.add_patch(bar)
    ax.text(50, 9.5,
            "无泄漏口径：测试集不参与任何统计量、阈值与节点清单的确定；\n"
            "重构张量与原始会话文件的时间片计数逐一核对一致（审计门禁通过）",
            ha="center", va="center", fontsize=8.5, color=RED_S, zorder=4)

    # 步骤语义小箭头（审计 → 聚合 → 张量 的过程标注）
    ax.text(51, 5.2, "重构管线", ha="center", fontsize=7, color=GRAY_M)

    fig.tight_layout()
    final(fig, "fig2_1_data_reconstruction", (12.2, 6.0))
    plt.close(fig)


# ========== 图 4-1 三层机制诊断框架 ==========

def fig4_1_three_layer_framework() -> None:
    """第 4 章：三层机制诊断框架示意图。

    三层纵向堆叠，每层为"研究问题 → 检验方法 → 关键证据 → 判定结论"
    四环节；左侧层标签，底部"可解释→可干预→可评估"闭环条。
    """
    fig, ax = plt.subplots(figsize=(13.2, 8.0))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    layers = [
        ("L1", "门控归因", BLUE,
         "模型依赖\n什么关系？",
         "关系级 β 门控\n权重明细与\n参数干预",
         "干预全部退化\n+95.9% ~ +233.6%\n（9 组干预）",
         "关系门控携带\n真实任务信息\n（可解释）"),
        ("L2", "结构验证", ORANGE,
         "图结构能否\n被参数替代？",
         "知识蒸馏\n教师 StaticGraph\n→ 学生 TCN",
         "学生始终 ≈0.029\n未弥合与教师\n0.01376 的 2.1 倍",
         "结构知识\n不可蒸馏\n（不可替代）"),
        ("L3", "误差归属", GREEN,
         "预测误差\n集中在哪里？",
         "四格诊断\n事件 × 规则\n交叉分层",
         "事件格 0.276 vs\n稳定格 0.010\n（约 28 倍）",
         "分层评价必要\n全局指标被稀释\n（可评估）"),
    ]

    # 顶部协议名（正文语义文字，非图题）
    ax.text(50, 96.5, "三层机制诊断协议：以实验回答模型行为问题",
            ha="center", fontsize=10.5, fontweight="bold", color=GRAY_D)

    y_top = 88
    row_h = 14
    gap = 2.6
    # 列宽合计 78 + 三处间距 6.0 = 84，起点 12.5 → 最右 96.5（画布 100 内留边）
    cols = [("研究问题", 12), ("检验方法", 26), ("关键证据", 20), ("判定结论", 20)]
    x_cursor = 12.5
    col_centers = []
    for name, w in cols:
        col_centers.append(x_cursor + w / 2)
        x_cursor += w + 2.0
    # 列头
    for name, cx in zip([c[0] for c in cols], col_centers):
        ax.text(cx, y_top + 1.6, name, ha="center", fontsize=7.5,
                color=GRAY_M)

    for i, (label, title, color, q, method, evidence, conclusion) in enumerate(layers):
        y = y_top - i * (row_h + gap)
        # 层标签（左侧竖排色条）
        tag = mpatches.FancyBboxPatch(
            (3.5, y - row_h / 2), 8.0, row_h,
            boxstyle="round,pad=0.01,rounding_size=0.4",
            fc=color, ec=color, lw=0, zorder=3,
        )
        ax.add_patch(tag)
        ax.text(7.5, y, label, ha="center", va="center", fontsize=11,
                color="white", fontweight="bold", zorder=4)
        ax.text(7.5, y - row_h / 2 + 2.2, title, ha="center", va="center",
                fontsize=7, color="white", zorder=4)

        contents = [q, method, evidence, conclusion]
        fcs = [BG, BG, "#FDF6EC", "#F0F5F0"]
        for j, (txt, cx) in enumerate(zip(contents, col_centers)):
            w = cols[j][1]
            _card(ax, cx - w / 2, y - row_h / 2, w, row_h, txt,
                  fc=fcs[j], ec=color, lw=1.2, fs=7.8)
            if j < 3:
                _arrow(ax, cx + w / 2 - 0.4, y, col_centers[j + 1] - cols[j + 1][1] / 2 + 0.4, y,
                       color=GRAY_M, lw=1.0, ms=8, shrink=0)

        # 层间递进箭头（左缘）
        if i < 2:
            _arrow(ax, 7.5, y - row_h / 2 - 0.7, 7.5, y - row_h - gap + row_h / 2 + 0.7,
                   color=color, lw=1.6, ms=10)
            ax.text(11.2, y - row_h - gap / 2, "证据递进", fontsize=6.5,
                    color=GRAY_M)

    # 底部闭环条
    loop = mpatches.FancyBboxPatch(
        (10, 6), 80, 9, boxstyle="round,pad=0.008,rounding_size=0.5",
        fc=BG, ec=GRAY_D, lw=1.3, zorder=3,
    )
    ax.add_patch(loop)
    for k, t in enumerate(["可解释", "可干预", "可评估"]):
        cx = 25 + k * 25
        _badge(ax, cx - 9, 10.5, 1.4, str(k + 1), fc=[BLUE, ORANGE, GREEN][k])
        ax.text(cx + 1, 10.5, t, ha="left", va="center", fontsize=9.5,
                fontweight="bold", color=GRAY_D)
        if k < 2:
            _arrow(ax, cx + 8, 10.5, cx + 12, 10.5, color=GRAY_M, lw=1.2,
                   ms=9)
    ax.text(50, 5.2, "三层结论贯通至第 5 章预测支持探索（区间化 / 分层归因）",
            ha="center", fontsize=7, color=GRAY_M)

    fig.tight_layout()
    final(fig, "fig4_1_three_layer_framework", (13.2, 8.0))
    plt.close(fig)


# ========== 图 5-1 第 5 章技术路线图 ==========

def fig5_1_exploration_roadmap() -> None:
    """第 5 章：预测支持探索技术路线图。

    三问题 → 三方向 → 三证据 → 统一闭环：问题-方法-证据箭头链，
    底部"可解释 → 可干预 → 可评估"闭环弧。
    """
    fig, ax = plt.subplots(figsize=(13.4, 7.8))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    # ---------- 顶部：三个问题 ----------
    questions = [
        ("统计相关能否\n方向化？", BLUE),
        ("点预测能否给出\n可靠性区间？", ORANGE),
        ("机制影响能否\n分层归因？", GREEN),
    ]
    q_w, q_h = 24, 11
    q_centers = []
    for k, (txt, color) in enumerate(questions):
        cx = 18 + k * 32
        q_centers.append(cx)
        _card(ax, cx - q_w / 2, 84, q_w, q_h, txt, fc=BG, ec=color,
              lw=1.6, fs=9.5, weight="bold", radius=0.03)
        _badge(ax, cx - q_w / 2 + 2.6, 89.5, 1.6, str(k + 1), fc=color)

    # 问题 → 方法 箭头
    for cx in q_centers:
        _arrow(ax, cx, 83.4, cx, 79.6, color=GRAY_M, lw=1.5, ms=11)

    # ---------- 中部：三列方法 ----------
    methods = [
        ("方向性分析", BLUE,
         ["传递熵方向性检验", "（8 分位分箱 · 循环平移\n置换检验 n=100）",
          "PCMCI+ 条件独立确认", "（偏相关 · 滞后上限 4 步）"]),
        ("区间预测", ORANGE,
         ["规则路由分层共形", "（Split Conformal 基础）",
          "事件窗口 / 稳定窗口", "分别校准区间半宽"]),
        ("分层归因", GREEN,
         ["分层参数干预敏感度", "（对学习值确定性扰动）",
          "事件窗口 × 稳定窗口", "分窗口评估代价"]),
    ]
    m_w, m_h = 28, 17
    for k, (title, color, lines) in enumerate(methods):
        cx = 18 + k * 32
        _card(ax, cx - m_w / 2, 62, m_w, m_h, "\n".join(lines),
              fc=BG, ec=color, lw=1.4, fs=7.8)
        ax.text(cx, 62 + m_h + 2.0, title, ha="center", fontsize=9.5,
                fontweight="bold", color=color)

    # 方法 → 证据 箭头
    for cx in q_centers:
        _arrow(ax, cx, 61.4, cx, 57.6, color=GRAY_M, lw=1.5, ms=11)

    # ---------- 底部：三列证据 ----------
    evidences = [
        ("方向性证据", BLUE,
         "90 条有向候选中 76 条显著\n（84.4%）\n44 / 76 经 PCMCI+ 确认\n（57.9%，探索性）"),
        ("区间性证据", ORANGE,
         "事件窗口覆盖率\n1.9% → 3.9%（规则路由）\noracle 事后上界 86.1%\n（不可部署）"),
        ("分层性证据", GREEN,
         "干预全部退化\n+95.9% ~ +233.6%\n稳定窗口敏感度远高于\n事件窗口"),
    ]
    e_w, e_h = 28, 14
    for k, (title, color, txt) in enumerate(evidences):
        cx = 18 + k * 32
        _card(ax, cx - e_w / 2, 43, e_w, e_h, txt, fc="#FDF6EC",
              ec=color, lw=1.4, fs=7.8)
        ax.text(cx, 43 + e_h + 1.8, title, ha="center", fontsize=9,
                fontweight="bold", color=color)

    # ---------- 底部统一闭环 ----------
    loop_y = 26
    loop = mpatches.FancyBboxPatch(
        (10, loop_y - 6), 80, 12, boxstyle="round,pad=0.01,rounding_size=0.5",
        fc=BG, ec=GRAY_D, lw=1.4, zorder=3,
    )
    ax.add_patch(loop)
    ax.text(50, loop_y + 4.2, "统一分析闭环", ha="center", fontsize=8.5,
            color=GRAY_M)
    for k, t in enumerate(["可解释", "可干预", "可评估"]):
        cx = 27 + k * 23
        _badge(ax, cx - 8, loop_y, 1.5, "ⅠⅡⅢ"[k], fc=[BLUE, ORANGE, GREEN][k])
        ax.text(cx + 1, loop_y, t, ha="left", va="center", fontsize=9.5,
                fontweight="bold", color=GRAY_D)
        if k < 2:
            _arrow(ax, cx + 7.5, loop_y, cx + 11, loop_y, color=GRAY_M,
                   lw=1.2, ms=9)
    # 闭环回收箭头（右 → 左）
    ax.text(90, loop_y + 0.5, "反馈", ha="center", fontsize=6.5,
            color=GRAY_M, rotation=0)

    # 底部定位句
    ax.text(50, 12.5,
            "本章不承诺解决事件窗口预测，而是刻画其可预测性边界、\n"
            "提供分层决策工具与分层归因证据（探索性 / 支持性定位）",
            ha="center", fontsize=8, color=GRAY_D)

    fig.tight_layout()
    final(fig, "fig5_1_exploration_roadmap", (13.4, 7.8))
    plt.close(fig)


if __name__ == "__main__":
    print("=== 批次 16：三张流程/框架示意图 ===")
    fig2_1_data_reconstruction()
    fig4_1_three_layer_framework()
    fig5_1_exploration_roadmap()
    print("=== 完成 ===")
