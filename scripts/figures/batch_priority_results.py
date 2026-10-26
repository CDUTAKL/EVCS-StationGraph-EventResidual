"""Audited data-only figure redraws. No inferred or image-generated measurements.

Run from repository root: .venv/bin/python scripts/figures/batch_priority_results.py
Optional --preview exports 180dpi candidates; default is 1200dpi PNG + text SVG.
"""
from pathlib import Path
import argparse
import importlib
import json
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.text import Text
from matplotlib.legend_handler import HandlerTuple
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle

# 样式与其余批次脚本同源：优先用 skill 版 setup_style（中文字体 PingFang SC），
# 无 skill 环境时回退 _skill_compat（审查 L-03 的同一套约定）。直接用
# _skill_compat 会把本图中文落到 Arial Unicode MS，与同章 fig5_9 的 PingFang SC
# 并排可见差异。
sys.path.insert(0, str(Path.home() / ".claude/skills/scipilot-figure-skill/scripts"))
try:
    from setup_style import setup_style  # noqa: E402
except ImportError:  # 无 skill 环境回退（审查 L-03）
    from _skill_compat import setup_style  # noqa: E402

OUT = Path('outputs/figures/priority-review-20260907')
OUT.mkdir(parents=True, exist_ok=True)
PREVIEW = False

def export(fig, name, size, min_pt=9, pad_inches=None):
    """导出单张图：OUT/<name>.svg（矢量）+ OUT/<name>.png（1200 DPI）。

    输入：fig（已绘制完成的 Figure）、name（不含扩展名）、size=(宽, 高)/英寸、
          min_pt（字号线：导出前把所有文字抬到不低于该磅值，取 9 是历史约定——
          字号在最终物理尺寸下测量，而非放大预览下）、pad_inches（tight 外扩量，
          None 表示沿用 matplotlib 默认值，不改变既有调用方的成品尺寸）。
    输出：OUT 目录下的 .svg 与 .png；函数无返回值。
    边界：bbox_inches="tight" 会裁到内容外框，成品尺寸随内容而变；需要严格等于
          size 时，调用方须先铺满画布的隐形矩形并传 pad_inches=0（见 pcmci()）。
    """
    # Font floor is measured at final physical size, not at a zoomed-in preview.
    fig.set_size_inches(*size)
    for text in fig.findobj(Text):
        if text.get_text():
            text.set_fontsize(max(min_pt, text.get_fontsize()))
    svg_path = OUT / (name + '.svg')
    pad_kw = {} if pad_inches is None else {'pad_inches': pad_inches}
    fig.savefig(svg_path, bbox_inches='tight', facecolor='white', **pad_kw)
    fig.savefig(OUT / (name + '.png'), dpi=180 if PREVIEW else 1200,
                bbox_inches='tight', facecolor='white', **pad_kw)
    plt.close(fig)
    # Matplotlib 把多行 path 数据写成带行尾空格的行；清理后 SVG 才能通过
    # 仓库的空白检查（git diff --check）。
    svg_path.write_text(
        "\n".join(line.rstrip() for line in svg_path.read_text(encoding="utf-8").splitlines()) + "\n",
        encoding="utf-8",
    )
    print(name, flush=True)

# fig5_3（双向传递熵与方向不对称性）的生成已迁移至
# scripts/figures/batch6_te_coverage_enhance.py 的 fig5_4_asymmetry()：
# 该版本含顶部/右侧边缘分布、1/2/3 编号三处联动与 ASYM<=0.30 比例对称带。
# 本脚本不再产出同名图，避免两个脚本对同一文件名写入不同内容。

# ========== fig5_5 PCMCI+ 条件独立核验的配色 ==========
# 素雅色板与同章 fig5_9（batch5_restyle.fig_parameter_intervention）一致：
# 深蓝主色 + 低饱和橙 + 中灰，全程不使用 hatch 纹理。
BLUE = '#2C5F8A'        # 深蓝：双检验达名义阈值（主色，最强证据）
ORANGE = '#D08A3C'      # 低饱和橙：仅 PCMCI+ 达阈值
GRAY_D = '#404040'      # 深灰：坐标轴、正文标注
GRAY_M = '#808080'      # 中灰：仅 TE 达阈值
GRAY_L = '#C8C8C8'      # 浅灰：网格线、空白格图例描边
DIAG_FILL = '#D5DCE1'   # 对角线填充：浅蓝灰，明显区分于空白的未达阈值格
GRID_XL = '#E8EDF0'     # 极浅灰：矩阵单元分隔线（白底上的格子边界）
# 三类状态：(图例文字, 符号色, marker, 符号尺寸)。矩阵单元与图例样张同出这一份
# 定义，保证一一对应。marker 取三种实心形状（圆/方/三角）而非 x/+：白底上实心
# 符号更醒目，且形状本身即构成灰度冗余编码，不依赖颜色即可区分三类。
EDGE_STYLE = [('双检验达名义阈值（44）', BLUE, 'o', BLUE, 8.5),
              ('仅 TE 达阈值（32）', GRAY_M, 's', GRAY_M, 7.5),
              ('仅 PCMCI+ 达阈值（6）', ORANGE, '^', ORANGE, 8.5)]


def pcmci():
    """绘制 fig5_5：PCMCI+ 条件独立核验（左 10×10 有向状态矩阵 + 右逐节点出边堆叠条）。

    输入：outputs/analysis/pcmci/pcmci_summary.json 的 confirmed_edges /
          te_only_edges / pcmci_only_edges 三键。
    输出：OUT/fig5_5_pcmci_validation_network.{svg,png}（16:9 画布，宽取论文版心
          5.59 in）与 OUT/fig5_5_source.json（绘图所用矩阵与计数，便于逐边核对）。
    边界：自回归对（源节点=目标节点）不参与两侧统计，对角线仅以浅灰填充 + 短横线
          标记“不检验”；三类达阈值状态互斥，由断言保证（44/32/6）。
    对齐：两面板共用同一 PLOT_BOTTOM/PLOT_HEIGHT，并共用同一 y 范围 (n-.5, -.5)。
          这是本图最易错处——条形若只调 barh + invert_yaxis()，matplotlib 会给它
          自动加约 0.15 单位边距（实际跨度 ~10.6 而非 10），两面板等高但跨度不同，
          行标签便呈喇叭口错开（实测顶/底各偏 5 pt）。
    """
    data = json.loads(Path('outputs/analysis/pcmci/pcmci_summary.json').read_text())
    names = ['confirmed_edges', 'te_only_edges', 'pcmci_only_edges']
    groups = [{tuple(e) for e in data[k] if e[0] != e[1]} for k in names]
    assert [len(g) for g in groups] == [44, 32, 6]
    assert all(not (groups[i] & groups[j]) for i in range(3) for j in range(i))
    ids = sorted({n for g in groups for e in g for n in e})
    assert len(ids) == 10                 # 节点集由边表推导，须与站内 10 节点一致
    n = len(ids)
    matrix = np.zeros((n, n), int)
    for k, g in enumerate(groups, 1):
        for s, t in g:
            matrix[ids.index(s), ids.index(t)] = k
    np.fill_diagonal(matrix, 4)           # 4 = 自回归对（源=目标），两侧均不统计
    tick_labels = [s[3:] if s.startswith('CA-') else s for s in ids]

    # ========== 布局：16:9 画布，各块位置由英寸推导 ==========
    # 幅面宽取论文版心 5.59 in（14.66 cm），高按 16:9 定为 3.14 in。所有左边界/
    # 宽度先以英寸给出再折算为 figure 比例，改画布时只需改 FIG_W/FIG_H。
    FIG_W, FIG_H = 5.59, 5.59 * 9.0 / 16.0      # 5.59 × 3.144 in
    fig = plt.figure(figsize=(FIG_W, FIG_H))
    fig.set_layout_engine('none')

    PLOT_BOTTOM, PLOT_HEIGHT = 0.170, 0.640     # 数据区（两面板严格等高同底）
    # 矩阵单元取横向长方形而非正方形：16:9 幅面下数据区仅 2.01 in 高，若强制正方形
    # 则每格只有 0.20 in（14.5 pt），装不下 7.2 pt 的三位数刻度（实宽约 12 pt），
    # x 标签会连成一片。放开纵横比后格宽 0.245 in（17.6 pt），标签才排得开。
    MAT_W_IN, MAT_H_IN = 2.45, PLOT_HEIGHT * FIG_H
    MAT_LEFT_IN, GAP_IN, BAR_W_IN = 0.58, 0.48, 1.94
    BAR_LEFT_IN = MAT_LEFT_IN + MAT_W_IN + GAP_IN

    ax = fig.add_axes([MAT_LEFT_IN / FIG_W, PLOT_BOTTOM, MAT_W_IN / FIG_W, PLOT_HEIGHT])
    bars = fig.add_axes([BAR_LEFT_IN / FIG_W, PLOT_BOTTOM, BAR_W_IN / FIG_W, PLOT_HEIGHT])

    # ========== 阶段 1：10×10 有向状态矩阵（行=源节点，列=目标节点） ==========
    # 白底 + 格内符号，而非满格色块：82/100 个格子若全填饱和色会铺成一片色海，
    # 与同章 fig5_9 的单色渐变热图并置时量感失衡。符号取三种实心形状，形状与颜色
    # 双重编码，白底上既清晰又透气。
    ax.set_facecolor('white')
    ax.set_xlim(-.5, n - .5)
    ax.set_ylim(n - .5, -.5)
    ax.set_xticks(np.arange(n + 1) - .5, minor=True)
    ax.set_yticks(np.arange(n + 1) - .5, minor=True)
    ax.grid(which='minor', color=GRID_XL, lw=0.5)
    ax.tick_params(which='both', length=0)
    for i in range(n):                    # 对角线：浅灰填充 + 短横线，表示不检验
        ax.add_patch(Rectangle((i - .5, i - .5), 1, 1, facecolor=DIAG_FILL,
                               edgecolor='none', zorder=1))
    for k, (_, _, marker, ink, ms) in enumerate(EDGE_STYLE, start=1):
        rows, cols = np.where(matrix == k)
        ax.plot(cols, rows, linestyle='none', marker=marker, ms=ms,
                mfc=ink, mec='white', mew=0.8, zorder=4)
    diag = np.arange(n)
    ax.plot(diag, diag, linestyle='none', marker='_', ms=7.0, mec=GRAY_D, mew=1.2,
            zorder=4)
    ax.set_xticks(range(n))
    # 不旋转：格宽 0.20 in 足以容纳三位数标签，且与 y 轴标签、右侧条形同向。
    ax.set_xticklabels(tick_labels, fontsize=7.2)
    ax.set_yticks(range(n))
    ax.set_yticklabels(tick_labels, fontsize=7.2)
    ax.set_xlabel('目标节点', fontsize=8.0, labelpad=2.0)
    ax.set_ylabel('源节点', fontsize=8.0, labelpad=1.0)
    for spine in ax.spines.values():
        spine.set_color(GRAY_D)
        spine.set_linewidth(0.6)

    # ========== 阶段 2：逐节点出边数（与矩阵同 y 范围，保证行标签共线） ==========
    left = np.zeros(n)
    for k, (_, color, _, _, _) in enumerate(EDGE_STYLE):
        counts = np.array([sum(s == node for s, t in groups[k]) for node in ids])
        bars.barh(range(n), counts, left=left, color=color, height=0.62,
                  edgecolor='white', linewidth=0.5, zorder=3)
        left += counts
    assert left.max() <= 9 and left.sum() == 82
    bars.set_yticks(range(n))
    bars.set_yticklabels(tick_labels, fontsize=7.2)
    # 显式钉死与矩阵相同的 y 范围（不可改用 invert_yaxis：barh 会自动加边距）
    bars.set_ylim(n - .5, -.5)
    bars.set_xlim(0, 10.6)
    bars.set_xticks([0, 3, 6, 9])
    bars.tick_params(axis='x', labelsize=7.2)
    bars.set_xlabel('节点间出边数', fontsize=8.0, labelpad=2.0)
    bars.spines[['top', 'right']].set_visible(False)
    bars.spines[['left', 'bottom']].set_color(GRAY_D)
    bars.spines[['left', 'bottom']].set_linewidth(0.6)
    # 水平条形图需竖向网格线，故不沿用 _clean_ax 的 grid(axis='y')
    bars.grid(axis='x', color=GRAY_L, lw=0.55, alpha=0.72)
    bars.set_axisbelow(True)
    for i, v in enumerate(left):
        bars.text(v + 0.18, i, str(int(v)), va='center', ha='left', fontsize=7.2,
                  color=GRAY_D)

    # ========== 阶段 3：图例（纯符号 + 背景态，两行置顶） ==========
    # 矩阵已改白底符号，图例相应不再用色块样张，否则图例形式与图面不符。
    edge_handles = [
        Line2D([], [], linestyle='none', marker=marker, ms=ms,
               mfc=ink, mec='white', mew=0.8)
        for _, _, marker, ink, ms in EDGE_STYLE
    ]
    legend_kw = dict(handler_map={tuple: HandlerTuple(ndivide=1)}, loc='upper left',
                     frameon=False, fontsize=7.5, handlelength=1.8, handleheight=1.25,
                     handletextpad=0.45, borderpad=0.0, borderaxespad=0.0)
    fig.legend(edge_handles, [style[0] for style in EDGE_STYLE],
               bbox_to_anchor=(0.045, 0.995), ncol=3, columnspacing=1.3, **legend_kw)
    fig.legend([Patch(facecolor='#FFFFFF', edgecolor=GRAY_L, linewidth=0.6),
                (Patch(facecolor=DIAG_FILL, edgecolor='none'),
                 Line2D([], [], linestyle='none', marker='_', ms=7.0, mec=GRAY_D,
                        mew=1.0))],
               ['两者均未达阈值（8）', '自回归对，不检验（10）'],
               bbox_to_anchor=(0.045, 0.930), ncol=2, columnspacing=1.3, **legend_kw)
    # 隐形矩形铺满画布：tight bbox 才等于画布本身，成品尺寸严格等于版心宽
    fig.add_artist(Rectangle((0.0, 0.0), 1.0, 1.0, transform=fig.transFigure,
                             facecolor='none', edgecolor='none', linewidth=0.0))
    (OUT / 'fig5_5_source.json').write_text(json.dumps({'nodes': ids, 'matrix': matrix.tolist(),
        'counts': [44, 32, 6], 'excluded_self_edges': 10}, ensure_ascii=False, indent=2))
    # min_pt=6：本图按纸面尺寸绘制，最小正文标注 7.2 pt，不套用历史的 9 pt 下限
    # （9 pt 会破坏与 fig5_9 的 6.5~8.6 pt 字号层级的一致性）。
    export(fig, 'fig5_5_pcmci_validation_network', (FIG_W, FIG_H), min_pt=6, pad_inches=0.0)


def forest():
    data=json.loads(Path('outputs/analysis/bootstrap_significance.json').read_text())
    # 比较名用中文短名：export() 的字号下限为 9 pt，而"EventResidual vs
    # AdaptiveGraph"这类英文全名在 9 pt 下宽约 3.6 in，会把 5.59 in 画布
    # 的数据区挤到 2 in 以内。中文名与图 3-16 的行文风格一致。
    labels={'TCN - StaticGraph':'MRG-GCN vs TCN',
            'StaticGraph - AdaptiveGraph':'自适应图 vs MRG-GCN',
            'AdaptiveGraph - EventResidual':'事件残差 vs 自适应图',
            'StaticGraph - MLP':'MLP vs MRG-GCN','TCN - MLP':'MLP vs TCN',
            'AdaptiveGraph - no_event_gate':'门控关闭 vs 自适应图'}
    # 与图 3-9（JPL 配对区间）同一视觉语言：主蓝表正向差值、暖灰表负向差值，
    # 白描边圆点 + 带端帽误差棒；零线统一用 #929DA6。
    BLUE='#2C5F8A';WARM='#A89A88'
    # 画布取论文显示尺寸（版心宽 14.66 cm = 5.77 in，图按 5.59 in 排版）。
    # layout='none' 必须在创建时给定：setup_style 默认开 constrained_layout，
    # 事后 set_layout_engine('none') 在 matplotlib 3.11 下仍会让
    # subplots_adjust 被静默忽略，导致两面板标题与刻度标签叠合。
    # 抗"空洞"设计（2026-10-26 反馈）：逐行标 [CI 下界, 上界]（森林图标准
    # 的信息列，两行错位排在差值下方）、斑马纹行带、面板高度按行数 4:5 分配、
    # 标记与误差棒加粗。
    fig,axes=plt.subplots(2,1,figsize=(5.59,4.35),layout='none',
                          gridspec_kw={'height_ratios':[4,5]})
    fig.subplots_adjust(left=.245,right=.975,top=.93,bottom=.15,hspace=.40)
    for ax,key,title in zip(axes,['global','event_window'],['A  全局预测键','B  标签事件预测键']):
        rows=[(labels[c['name']],c['pooled'][key]) for c in data['comparisons'] if key in c['pooled']]
        for i in range(len(rows)):
            if i%2==0:
                ax.axhspan(i-.5,i+.5,color='#F3F6F8',zorder=0)
        for i,(label,p) in enumerate(rows):
            d,lo,hi=p['observed_diff'],p['ci_lower'],p['ci_upper']
            color=BLUE if d>0 else WARM
            ax.errorbar(d,i,xerr=[[d-lo],[hi-d]],fmt='o',ms=6.2,color=color,
                        mec='white',mew=0.8,ecolor=color,elinewidth=1.5,
                        capsize=3.5,capthick=1.5,zorder=3)
            ax.annotate(f'{d:+.4f}',(hi,i),xytext=(7,5),textcoords='offset points',
                        va='center',fontsize=7.4,color='#404040')
            ax.annotate(f'[{lo:+.4f}, {hi:+.4f}]',(hi,i),xytext=(7,-7),
                        textcoords='offset points',va='center',fontsize=6.2,
                        color='#8A9299')
        ax.set_yticks(range(len(rows)),[r[0] for r in rows]);ax.invert_yaxis()
        # 显式 9 pt：默认 10 pt 下"门控关闭 vs 自适应图"宽约 1.39 in，
        # 会超出 left 预留的标签区并把成品宽度撑过版心。
        ax.tick_params(axis='y',labelsize=9)
        ax.set_ylim(len(rows)-.5,-.7)
        # 面板 A 右界放宽到 0.024：CI 区间文字排在最长正向差值（+0.0158）右侧，
        # 旧界 0.022 会把 "[lo, hi]" 第二行顶出数据区。
        ax.set_xlim((-.012,.024) if key=='global' else (-.043,.045))
        ax.axvline(0,color='#929DA6',lw=.9);ax.grid(axis='x',color='#E8EDF0',lw=.6)
        ax.set_axisbelow(True)
        ax.spines[['top','right']].set_visible(False)
        ax.text(0,1.06,title,transform=ax.transAxes,fontsize=9.5,
                fontweight='bold',color='#2B2B2B')
    # 用面板 B 的 xlabel 而非 fig.text：自动落在刻度标签之下，不与刻度重叠
    axes[1].set_xlabel('MAE（后者）− MAE（前者）（kWh/15 min）',fontsize=9)
    # min_pt=6：数值标注按 7.4 pt 设计（与图 3-15 同级），不套用历史 9 pt
    # 下限，否则标注会被整体抬高、与图 3-15 并排版式不一致。
    export(fig,'fig3_13_bootstrap_difference',(5.59,4.35),min_pt=6)

def main():
    global PREVIEW
    parser=argparse.ArgumentParser();parser.add_argument('--preview',action='store_true')
    args=parser.parse_args();PREVIEW=args.preview
    tasks=[('batch5_restyle',['fig_load_heatmap','fig_weekly_curves']),
           ('batch4_redraw',['redraw_event_timeline']),
           ('batch11_chapter2_extra',['redraw_fig2_10']),
           ('batch12_chapter3_extra',['redraw_fig3_9']),
           ('batch13_chapter4_5_extra',['redraw_fig4_6','redraw_fig4_7'])]
    for name,funcs in tasks:
        module=importlib.import_module(name)
        module.final=export;module._final=export
        for fn in funcs: getattr(module,fn)()
    setup_style(journal='general',lang='zh')
    forest();pcmci()

if __name__=='__main__': main()
