"""Audited data-only figure redraws. No inferred or image-generated measurements.

Run from repository root: .venv/bin/python scripts/figures/batch_priority_results.py
Optional --preview exports 180dpi candidates; default is 1200dpi PNG + text SVG.
"""
from pathlib import Path
import argparse
import importlib
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.text import Text
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch
from _skill_compat import setup_style

OUT = Path('outputs/figures/priority-review-20260907')
OUT.mkdir(parents=True, exist_ok=True)
PREVIEW = False

def export(fig, name, size):
    # Font floor is measured at final physical size, not at a zoomed-in preview.
    fig.set_size_inches(*size)
    for text in fig.findobj(Text):
        if text.get_text():
            text.set_fontsize(max(9, text.get_fontsize()))
    fig.savefig(OUT / (name + '.svg'), bbox_inches='tight', facecolor='white')
    fig.savefig(OUT / (name + '.png'), dpi=180 if PREVIEW else 1200,
                bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(name, flush=True)

def asymmetry():
    data = json.loads(Path('outputs/analysis/transfer_entropy/transfer_entropy_summary.json').read_text())
    from evcs_station_graph.data import load_tensor_bundle
    ids = list(load_tensor_bundle('data/processed/SG-DATA-005-primary-tensor.npz').node_ids)
    mat = np.asarray(data['te_matrix'])
    sig = {(e['source'], e['target']) for e in data['significant_edges']}
    rows = [(ids[i], ids[j], float(mat[i,j]), float(mat[j,i]),
             (ids[i],ids[j]) in sig or (ids[j],ids[i]) in sig)
            for i in range(len(ids)) for j in range(i+1,len(ids))]
    assert len(rows) == 45
    fig, ax = plt.subplots(figsize=(5.8,5.0))
    limit = max(max(r[2:4]) for r in rows)*1.15
    ax.plot([0,limit], [0,limit], '--', color='#9AA5AF', lw=1, label='双向相等')
    for flag, label, color, marker in [(True,'至少一方向达名义阈值','#49799D','o'),
                                      (False,'两方向均未达名义阈值','#B4BDC5','s')]:
        subset = [r for r in rows if r[4] == flag]
        ax.scatter([r[2] for r in subset], [r[3] for r in subset],
                   s=38, c=color, marker=marker, edgecolors='white', linewidths=.6,label=label,zorder=3)
    for k,p in enumerate(data['asymmetry']['top_asymmetric_pairs'][:3]):
        i,j=ids.index(p['node_i']),ids.index(p['node_j'])
        ax.annotate(p['node_i'][3:]+' / '+p['node_j'][3:],(mat[i,j],mat[j,i]),
                    xytext=(12,12+12*k),textcoords='offset points',fontsize=9,
                    arrowprops={'arrowstyle':'-','color':'#808B95','lw':.7})
    ax.set(xlim=(0,limit),ylim=(0,limit),xlabel='传递熵 TE(i → j)',ylabel='传递熵 TE(j → i)')
    ax.set_aspect('equal')
    ax.spines[['top','right']].set_visible(False)
    ax.legend(frameon=False,fontsize=9,loc='lower right')
    fig.tight_layout()
    (OUT/'fig5_3_source.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
    export(fig,'fig5_3_asymmetry',(5.8,5.0))

def pcmci():
    data=json.loads(Path('outputs/analysis/pcmci/pcmci_summary.json').read_text())
    names=['confirmed_edges','te_only_edges','pcmci_only_edges']
    groups=[{tuple(e) for e in data[k] if e[0]!=e[1]} for k in names]
    assert [len(g) for g in groups]==[44,32,6]
    assert all(not(groups[i]&groups[j]) for i in range(3) for j in range(i))
    ids=sorted({n for g in groups for e in g for n in e})
    matrix=np.zeros((len(ids),len(ids)),int)
    for k,g in enumerate(groups,1):
        for s,t in g: matrix[ids.index(s),ids.index(t)]=k
    np.fill_diagonal(matrix,4)
    colors=['#FFFFFF','#5483A5','#C5CDD4','#D2AF82','#EEF1F3']
    labels=['双检验达名义阈值（44）','仅TE达阈值（32）','仅PCMCI+达阈值（6）']
    fig,(ax,bars)=plt.subplots(1,2,figsize=(7.8,4.8),gridspec_kw={'width_ratios':[1.35,1]})
    fig.set_layout_engine('none')
    ax.imshow(matrix,cmap=ListedColormap(colors),vmin=0,vmax=4,interpolation='nearest')
    for i in range(10):
        for j in range(10):
            if i!=j and matrix[i,j]:
                ax.text(j,i,['','●','×','+'][matrix[i,j]],ha='center',va='center',fontsize=9,
                        color='white' if matrix[i,j]==1 else '#404850')
    ax.set_xticks(range(10),[s[3:] for s in ids],rotation=45)
    ax.set_yticks(range(10),[s[3:] for s in ids])
    ax.set_xticks(np.arange(11)-.5,minor=True);ax.set_yticks(np.arange(11)-.5,minor=True)
    ax.grid(which='minor',color='white',lw=1);ax.tick_params(which='both',length=0)
    ax.set(xlabel='目标节点',ylabel='源节点')
    left=np.zeros(10)
    for k,g in enumerate(groups):
        counts=np.array([sum(s==n for s,t in g) for n in ids])
        bars.barh(range(10),counts,left=left,color=colors[k+1],height=.65,
                  edgecolor='white',hatch=['','..','//'][k])
        left+=counts
    assert left.max()<=9 and left.sum()==82
    bars.set_yticks(range(10),[s[3:] for s in ids]);bars.invert_yaxis()
    bars.set(xlim=(0,10),xlabel='节点间出边数')
    bars.set_xticks([0,3,6,9]);bars.spines[['top','right']].set_visible(False)
    for i,v in enumerate(left): bars.text(v+.12,i,str(int(v)),va='center',fontsize=9)
    fig.legend(handles=[Patch(facecolor=colors[k+1],label=labels[k],hatch=['','..','//'][k]) for k in range(3)],
               loc='upper center',ncol=1,frameon=False,bbox_to_anchor=(.51,1.01),fontsize=9)
    fig.subplots_adjust(top=.76,bottom=.17,left=.09,right=.97,wspace=.35)
    (OUT/'fig5_5_source.json').write_text(json.dumps({'nodes':ids,'matrix':matrix.tolist(),
        'counts':[44,32,6],'excluded_self_edges':10},ensure_ascii=False,indent=2))
    export(fig,'fig5_5_pcmci_validation_network',(7.8,4.8))

def forest():
    data=json.loads(Path('outputs/analysis/bootstrap_significance.json').read_text())
    labels={'TCN - StaticGraph':'MRG-GCN vs TCN',
            'StaticGraph - AdaptiveGraph':'AdaptiveGraph vs MRG-GCN',
            'AdaptiveGraph - EventResidual':'EventResidual vs AdaptiveGraph',
            'StaticGraph - MLP':'MLP vs MRG-GCN','TCN - MLP':'MLP vs TCN',
            'AdaptiveGraph - no_event_gate':'no-event-gate vs AdaptiveGraph'}
    fig,axes=plt.subplots(2,1,figsize=(7.8,5.6))
    fig.set_layout_engine('none')
    fig.subplots_adjust(left=.33,right=.97,top=.94,bottom=.13,hspace=.4)
    for ax,key,title in zip(axes,['global','event_window'],['A  全局预测键','B  标签事件预测键']):
        rows=[(labels[c['name']],c['pooled'][key]) for c in data['comparisons'] if key in c['pooled']]
        for i,(label,p) in enumerate(rows):
            d,lo,hi=p['observed_diff'],p['ci_lower'],p['ci_upper']
            ax.errorbar(d,i,xerr=[[d-lo],[hi-d]],fmt='o',ms=5,color='#49799D' if d>0 else '#8D989F',
                        capsize=3,lw=1,zorder=3)
            ax.annotate(f'{d:+.4f}',(hi,i),xytext=(7,0),textcoords='offset points',va='center',fontsize=9)
        ax.set_yticks(range(len(rows)),[r[0] for r in rows]);ax.invert_yaxis()
        ax.set_ylim(len(rows)-.5,-.7)
        ax.set_xlim((-.012,.022) if key=='global' else (-.043,.045))
        ax.axvline(0,color='#929DA6',lw=.9);ax.grid(axis='x',color='#E8EDF0',lw=.6)
        ax.spines[['top','right']].set_visible(False)
        ax.text(0,1.06,title,transform=ax.transAxes,fontsize=10)
    fig.text(.63,.025,'MAE(后者) − MAE(前者)（kWh/15 min）',ha='center',fontsize=10)
    export(fig,'fig3_11_bootstrap_difference',(7.8,5.6))

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
    forest();asymmetry();pcmci()

if __name__=='__main__': main()
