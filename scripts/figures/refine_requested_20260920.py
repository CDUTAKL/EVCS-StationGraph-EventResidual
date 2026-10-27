"""Rebuild fig4_7 and fig5_5 from existing evidence; no new experiments."""
from pathlib import Path
import json
import hashlib
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from evcs_station_graph.data import load_tensor_bundle
from evcs_station_graph.evaluation.rules import fit_frozen_event_rule, visible_event_scores

OUT = ROOT / 'outputs/figures'
BLUE, GRAY, GOLD = '#476F8B', '#A2ABB2', '#BB9164'
# 2026-10-26：模块级字体统一为 PingFang SC 优先（此前 Arial Unicode MS 是
# 历史样式，与全篇其他图件的 setup_style 字体不一致；fig4_7 已先行切换，
# 本次把 fig3_12/fig5_5 一并迁移，intensity() 内的局部切换随之冗余删除）。
plt.rcParams.update({'font.family': ['PingFang SC', 'Arial Unicode MS', 'DejaVu Sans'],
    'font.size': 9, 'axes.labelsize': 9, 'axes.titlesize': 10,
    'axes.spines.top': False, 'axes.spines.right': False,
    'axes.edgecolor': '#64717A', 'axes.linewidth': .65,
    'xtick.color': '#47525A', 'ytick.color': '#47525A',
    'svg.fonttype': 'none', 'axes.unicode_minus': False})

def save(fig, stem):
    for ext in ['svg', 'png']:
        fig.savefig(OUT / f'{stem}.{ext}', dpi=1200, facecolor='white')
    plt.close(fig)
    p = OUT / f'{stem}.svg'
    p.write_text('\n'.join(s.rstrip() for s in p.read_text().splitlines())+'\n')

def clean(ax):
    ax.grid(axis='x', color='#E7EBEE', lw=.65)
    ax.set_axisbelow(True)
    ax.tick_params(length=3, width=.6)

def pcmci():
    source = ROOT / 'outputs/analysis/pcmci/pcmci_summary.json'
    data = json.loads(source.read_text())
    groups = [{tuple(e) for e in data[k] if e[0] != e[1]}
              for k in ['confirmed_edges', 'te_only_edges', 'pcmci_only_edges']]
    assert list(map(len, groups)) == [44, 32, 6]
    assert all(not groups[i] & groups[j] for i in range(3) for j in range(i))
    nodes = sorted({s for g in groups for e in g for s in e})
    matrix = np.zeros((10, 10), int)
    for k,g in enumerate(groups,1):
        for s,t in g: matrix[nodes.index(s), nodes.index(t)] = k
    fig = plt.figure(figsize=(7.5, 4.6))
    ax = fig.add_axes([.08,.17,.46,.69])
    ax.set(xlim=(-.5,9.5), ylim=(9.5,-.5), xlabel='目标节点', ylabel='源节点')
    ax.set_aspect('equal')
    labels = [n.replace('CA-','') for n in nodes]
    ax.set_xticks(range(10),labels); ax.set_yticks(range(10),labels)
    ax.set_xticks(np.arange(11)-.5,minor=True); ax.set_yticks(np.arange(11)-.5,minor=True)
    # 矩阵结构显性化（2026-10-27 反馈）：浅灰底 + 白色格线让格子可读，
    # 空白格（两者均未达阈值）不再与画布背景融为一体；对角线浅蓝灰填充
    # 保持"自回归对不检验"的区分（其上仍有 '_' 短横符号）。
    ax.set_facecolor('#F2F4F6')
    for i in range(10):
        ax.add_patch(Rectangle((i - .5, i - .5), 1, 1, facecolor='#E2E8EC',
                               edgecolor='none', zorder=1))
    ax.grid(which='minor',color='white',lw=1.0); ax.tick_params(which='both',length=0)
    for k,(color,marker) in enumerate(zip([BLUE,GRAY,GOLD],['o','s','^']),1):
        rows,cols = np.where(matrix==k)
        ax.scatter(cols,rows,s=54,c=color,marker=marker,edgecolors='white',linewidths=.5,zorder=3)
    ax.scatter(range(10),range(10),marker='_',c='#BCC5CB',s=50)
    ax.set_title('A  方向矩阵',loc='left',pad=10)
    # C 子图（检验交集堆叠条）已删除：其计数唯一的新信息是"8 对均未达阈值"
    # 与分母 90，已挪入论文图 5-5 图注；B 面板向下伸展收回原 C 区空间。
    b = fig.add_axes([.65,.15,.30,.71])
    for offset,axis,alpha in [(-.17,0,1),(.17,1,.40)]:
        left = np.zeros(10)
        for k,color in enumerate([BLUE,GRAY,GOLD],1):
            cnt=(matrix==k).sum(axis=1 if axis==0 else 0)
            b.barh(np.arange(10)+offset,cnt,left=left,height=.29,color=color,alpha=alpha)
            left+=cnt
    b.set_yticks(range(10),labels); b.set_ylim(9.7,-.7)
    b.set_xticks([0,3,6,9]); b.set_xlim(0,9.5)
    b.set_xlabel('边数',fontsize=8)
    b.set_title('B  出边 / 入边',loc='left',pad=10); clean(b)
    # 四类计数（共同/仅TE/仅PCMCI+/均未达阈值，与图例同序）仍写入溯源记录，
    # 供图注文字与审计核对。
    values=[44,32,6,8]
    handles=[Line2D([],[],marker=m,color=co,ls='',ms=6) for m,co in zip(['o','s','^'],[BLUE,GRAY,GOLD])]
    handles.append(Line2D([],[],marker='s',color='#E9EDF0',ls='',ms=6))
    fig.legend(handles,['共同','仅TE','仅PCMCI+','均未达阈值'],ncol=4,loc='upper center',bbox_to_anchor=(.52,.99),frameon=False,fontsize=8)
    save(fig,'fig5_5_pcmci_validation_network')
    return {'source':str(source.relative_to(ROOT)), 'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'matrix':matrix.tolist(),'nodes':nodes,'counts':values}

def intensity():
    bundle=load_tensor_bundle(str(ROOT/'data/processed/SG-DATA-005-primary-tensor.npz'))
    rule=fit_frozen_event_rule(bundle)
    scores=visible_event_scores(bundle,bundle.split_origins['test'],score_stats={k:np.asarray(v,dtype=np.float32) for k,v in rule.score_stats.items()})
    hits=sorted(ROOT.glob('outputs/experiments/SG-EXP-004/*/seed-2024/predictions.csv.gz')) or sorted(ROOT.glob('outputs/night_run/20260730-171821/SG-EXP-004/*/seed-2024/predictions.csv.gz'))
    assert len(hits)==1, hits
    df=pd.read_csv(hits[0]); df=df[df.split=='test'].copy()
    rows={o:i for i,o in enumerate(bundle.split_origins['test'])}
    score=np.array([scores[rows[o],n] for o,n in zip(df.origin_index,df.node_index)])
    q50,q95=np.percentile(scores[scores>0],[50,95])
    bins=pd.cut(score,[0,1e-6,q50,q95,np.inf],labels=False,include_lowest=True)
    err=np.abs(df.y_pred.to_numpy()-df.y_true.to_numpy())
    n=np.array([sum(bins==i) for i in range(4)])
    mae=np.array([err[bins==i].mean() for i in range(4)])
    assert n.sum()==len(df)==712360
    pop=n/n.sum()*100; contribution=n*mae/(n*mae).sum()*100
    labels=['分数为零','非零低档','非零中档','非零高档']
    # 主色用房屋蓝 #2C5F8A（模块级 BLUE=#476F8B 偏浅，与第4章其余图不一致）；
    # GOLD 保留作"非零高档"语义强调。
    HOUSE_BLUE = '#2C5F8A'
    fig,axes=plt.subplots(1,2,figsize=(7.5,3.65),gridspec_kw={'width_ratios':[1,1.15]})
    fig.subplots_adjust(left=.12,right=.97,bottom=.23,top=.83,wspace=.47)
    a,b=axes; colors=[GRAY,HOUSE_BLUE,HOUSE_BLUE,GOLD]
    for i in range(4):
        a.hlines(i,0,mae[i],color=colors[i],lw=2.5)
        a.scatter(mae[i],i,s=54,color=colors[i],zorder=3)
        a.text(mae[i]+.002,i,f'{mae[i]:.4f}',va='center',fontsize=8)
    a.set_yticks(range(4),labels); a.set_ylim(3.5,-.6); a.set_xlim(0,.075)
    a.set_xticks([0,.02,.04,.06]); a.set_xlabel('MAE（kWh/15 min）'); clean(a)
    a.set_title('A  各分箱误差水平',loc='left',pad=10)
    y=np.arange(4)
    for i in range(4):
        b.plot([pop[i],contribution[i]],[i-.16,i+.16],color='#CBD4DB',lw=1.2,zorder=2)
    b.scatter(pop,y-.16,s=42,facecolor='white',edgecolor=HOUSE_BLUE,label='样本占比',zorder=3)
    b.scatter(contribution,y+.16,s=42,color=HOUSE_BLUE,marker='D',label='绝对误差贡献',zorder=3)
    b.set_xscale('log'); b.set_xlim(.06,190); b.set_xticks([.1,1,10,100],['0.1','1','10','100'])
    b.minorticks_off()
    for off,vals in [(-.16,pop),(.16,contribution)]:
        for i,v in enumerate(vals):
            b.annotate(f'{v:.2f}',(v,i+off),xytext=(6,0),textcoords='offset points',va='center',fontsize=7.5)
    b.set_yticks(y,[f'n = {v:,}' for v in n]); b.set_ylim(3.5,-.6)
    b.set_xlabel('占比（%，对数坐标）'); clean(b)
    b.set_title('B  样本量与误差贡献',loc='left',pad=10)
    b.legend(loc='upper center',bbox_to_anchor=(.45,1.04),ncol=2,fontsize=7.5,frameon=False)
    fig.text(.12,.055,'AdaptiveGraph · seed-2024   |   非零分数按50%与95%分位分箱，仅用于描述性分析。',fontsize=8,color='#66737C')
    save(fig,'fig4_7_error_vs_event_intensity')
    return {'prediction_source':str(hits[0].relative_to(ROOT)),'sha256':hashlib.sha256(hits[0].read_bytes()).hexdigest(),'q50':float(q50),'q95':float(q95),'counts':n.tolist(),'mae':mae.tolist(),'sample_percent':pop.tolist(),'absolute_error_percent':contribution.tolist()}

def horizon():
    models=[('002','TCN','#AEB6BC','o','--'),('003','MRG-GCN','#2C5F8A','s','-'),
            ('004','AdaptiveGraph','#8EABC0','D','--'),('009','MLP','#8C979E','^','-.'),
            ('010','GWN','#6E7A81','P',':'),('008','AGCRN','#55606A','X','--')]
    # 2026-10-27 重构：删顶部图例，改线端直接标注（direct labeling）。
    # 末端值分两处密集（MLP/GWN/AGCRN 挤在 0.028–0.029，MRG/AdaptiveGraph
    # 挤在 0.024 附近），标注在右侧标注槽内等距排开、细引线连回线端。
    fig,ax=plt.subplots(figsize=(7.5,4.1))
    fig.subplots_adjust(left=.12,right=.79,bottom=.16,top=.94)
    hs=np.arange(1,5); records={}; ends=[]
    for exp,label,color,marker,ls in models:
        base='outputs/night_run/20260730-171821' if exp in ['002','003','004'] else 'outputs/experiments'
        paths=sorted(ROOT.glob(f'{base}/SG-EXP-{exp}/*/seed-*/metrics.json'))
        assert len(paths)==3
        vals=np.array([[v['mae'] for k,v in sorted(json.loads(p.read_text())['by_horizon'].items(),key=lambda kv:int(kv[0]))] for p in paths])
        mean=vals.mean(0); sd=vals.std(0,ddof=1)
        ax.plot(hs,mean,label=label,color=color,marker=marker,ls=ls,lw=2 if label=='MRG-GCN' else 1.2,
                ms=5.5,mfc='white' if label!='MRG-GCN' else color,mew=1,zorder=5 if label=='MRG-GCN' else 4)
        ax.fill_between(hs,mean-sd,mean+sd,color=color,alpha=.12,lw=0)
        ends.append((label,color,float(mean[-1])))
        records[label]={'paths':[str(p.relative_to(ROOT)) for p in paths],'mean':mean.tolist(),'sd':sd.tolist()}
    ax.set(xlim=(.85,4.15),ylim=(0,.041),xlabel='目标片区间（min）',ylabel='MAE（kWh/15 min）')
    ax.set_xticks(hs,['[0,15)','[15,30)','[30,45)','[45,60)'])
    ax.tick_params(axis='x',labelsize=8)
    ax.set_yticks([0,.01,.02,.03,.04]); ax.grid(axis='y',color='#E7EBEE',lw=.6)
    order=np.argsort([e[2] for e in ends])
    gutter=np.linspace(0.0248,0.0375,len(ends))
    for r,idx in enumerate(order):
        label,color,yv=ends[idx]
        ax.plot([4.03,4.09],[yv,gutter[r]],color=color,lw=.55,alpha=.65,clip_on=False,zorder=3)
        ax.text(4.12,gutter[r],f'{label}  {yv:.4f}',color=color,fontsize=8,
                ha='left',va='center',clip_on=False)
    save(fig,'fig3_12_mae_by_horizon')
    records['_time_axis']={
        'reference':'forecast_release_time',
        'tick_intervals_min':[[0,15],[15,30],[30,45],[45,60]],
        'interval_convention':'left-closed, right-open',
        'note':'No metric values or prediction keys changed; labels expose the existing target-bin mapping.'
    }
    (OUT/'fig3_12_revision_sources.json').write_text(json.dumps(records,indent=2)+'\n')

if __name__=='__main__':
    horizon()
    result={'fig5_5':pcmci(),'fig4_7':intensity()}
    (OUT/'revision_20260920_sources.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
