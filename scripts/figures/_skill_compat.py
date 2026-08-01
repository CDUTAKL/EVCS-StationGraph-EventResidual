"""scipilot-figure-skill 缺失时的最小兼容实现（审查 L-03，2026-08-01）。

绘图批次脚本优先从 ~/.claude/skills/scipilot-figure-skill/scripts 导入
export_figure/setup_style；该路径在非本机环境不可用时，回退到本模块的
最小实现（SVG + PNG 1200DPI + 素雅色板），保证生成物格式与风格一致。

用法（各批次脚本导入段）：
    try:
        from export_figure import export_figure
        from setup_style import setup_style
    except ImportError:
        from _skill_compat import export_figure, setup_style
"""

from __future__ import annotations

import matplotlib as mpl
import matplotlib.pyplot as plt

# 素雅色板（对齐 batch4~8 约定）
_ELEGANT_COLORS = ["#2C5F8A", "#D08A3C", "#404040", "#808080", "#C8C8C8", "#B05A4A"]


# 中文字体候选（审查 L-03，2026-08-01：无 skill 环境（如 Linux 服务器）默认
# DejaVu Sans 无法渲染中文，会出方框/缺字——显式指定 CJK 候选并检测）
_CJK_FONTS = ["Noto Sans CJK SC", "Source Han Sans SC", "Microsoft YaHei",
              "SimHei", "Arial Unicode MS", "PingFang SC", "Heiti SC"]


def _ensure_cjk_font() -> None:
    """检测可用中文字体；全部缺失时显式报错（避免静默输出方框图）。"""
    from matplotlib import font_manager

    available = {f.name for f in font_manager.fontManager.ttflist}
    found = [f for f in _CJK_FONTS if f in available]
    if not found:
        raise RuntimeError(
            "未找到可用中文字体（候选：Noto Sans CJK SC / Source Han Sans SC / "
            "SimHei / Microsoft YaHei 等）。无法可靠导出中文论文图，请安装任一 CJK 字体。"
        )
    return None


def setup_style(journal: str | None = "general", lang: str | None = "zh") -> None:
    """最小样式：CJK 字体候选 + 素雅色板（无 skill 环境回退）。"""
    _ensure_cjk_font()
    mpl.rcParams["font.family"] = ["sans-serif"]
    mpl.rcParams["font.sans-serif"] = _CJK_FONTS + ["DejaVu Sans"]
    mpl.rcParams["axes.prop_cycle"] = mpl.cycler(color=_ELEGANT_COLORS)
    mpl.rcParams["axes.unicode_minus"] = False
    mpl.rcParams["svg.fonttype"] = "none"


def export_figure(
    fig,
    basename: str,
    formats: tuple[str, ...] = ("svg", "png"),
    dpi: int = 1200,
    size_inches: tuple[float, float] | None = None,
    grayscale_preview: bool = False,
) -> None:
    """最小导出：SVG 矢量 + PNG 1200DPI（论文硬性约束，与 skill 版一致）。"""
    if size_inches is not None:
        fig.set_size_inches(size_inches)
    for fmt in formats:
        fig.savefig(f"{basename}.{fmt}", format=fmt, dpi=dpi,
                    bbox_inches="tight")
    plt.close(fig)
