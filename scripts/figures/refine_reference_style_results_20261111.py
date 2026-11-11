"""Recompose selected thesis plots using the approved intervention-plot style.

All numerical observations are read through the prior data-validation loaders.
The zero-weight strip has a categorical x-axis; no quantitative TE coordinate is
jittered. No observations are dropped, and correlations use all original values.
"""
from pathlib import Path
import hashlib
import json
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import MaxNLocator, FormatStrFormatter
import numpy as np
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parent))
import revise_selected_results_20261111 as base

ROOT, OUT = base.ROOT, base.OUT
BLUE, ORANGE, GRAY = "#2F6F9F", "#C58B45", "#B5B5B5"
DARK, BASE, GRID = "#454545", "#8C979F", "#E5ECF0"
plt.rcParams.update({"font.family": ["Arial", "PingFang SC"], "font.size": 9,
    "axes.labelcolor": DARK, "text.color": DARK, "xtick.color": DARK,
    "ytick.color": DARK, "axes.spines.top": False, "axes.spines.right": False,
    "svg.fonttype": "none", "pdf.fonttype": 42,
    "figure.constrained_layout.use": False})


def clean(ax, axis="y"):
    ax.set_axisbelow(True)
    ax.grid(axis=axis, color=GRID, lw=.65)
    ax.tick_params(length=3, width=.65, pad=4, labelsize=8)
    for side in ["left", "bottom"]:
        ax.spines[side].set_color(DARK)
        ax.spines[side].set_linewidth(.65)


def title(fig, x, text):
    fig.text(x, .845, text, va="bottom", fontsize=10, weight="bold")


def legend(fig, handles, x, y=.99, columns=2):
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(x,y),
               ncol=columns, frameon=False, fontsize=8.5, columnspacing=1.4,
               handletextpad=.5, borderaxespad=0)


def save(fig, stem, data):
    data["visual_reference"] = "approved gate-intervention result plot"
    data["palette"] = [BLUE, ORANGE, GRAY]
    base.export(fig, stem, data)


def jpl():
    f, iv = base.jpl._load_per_seed(), base.jpl._load_intervals()
    seeds = list(base.jpl.SEEDS)
    model_ids = ["tcn_wide", "agcrn_full", "mrg_shared_gate"]
    labels = ["TCN", "完整 AGCRN", "共享门控"]
    ref = f[f.model == "mrg_full"].set_index("seed").loc[seeds,"mae"].to_numpy()
    ref_mean = float(ref.mean())
    fig = plt.figure(figsize=(6.5,3.65))
    a = fig.add_axes([.145,.260,.355,.555])
    c = fig.add_axes([.655,.260,.315,.555])
    title(fig,.145,"(a)  整体MAE与模型间差距")
    title(fig,.655,"(b)  逐种子配对差与时间块区间")
    legend(fig,[Line2D([],[],marker="o",ls="none",color=BASE,label="MRG-GCN基线"),
                Line2D([],[],marker="o",ls="none",color=BLUE,label="对照均值 ± SD")],.145,columns=1)
    legend(fig,[Patch(color=color,label=str(seed)) for color,seed in zip([BLUE,ORANGE,GRAY],seeds)],.655,columns=3)
    effects=[]
    for row,(mid,label) in enumerate(zip(model_ids,labels)):
        val=f[f.model==mid].set_index("seed").loc[seeds,"mae"].to_numpy()
        mean,sd=float(val.mean()),float(val.std(ddof=1))
        a.hlines(row,ref_mean,mean,color="#C6D2DA",lw=2.4,zorder=2)
        a.scatter(ref_mean,row,s=35,color=BASE,edgecolor="white",lw=.7,zorder=4)
        a.errorbar(mean,row,xerr=sd,fmt="o",color=BLUE,ecolor="#53636E",
                   ms=6,capsize=3,elinewidth=1,markeredgecolor="white",zorder=5)
        a.text(.08545,row,f"{mean:.5f}",ha="right",va="center",fontsize=8.3)
        delta=val-ref
        for offset,d,color in zip([-.23,0,.23],delta,[BLUE,ORANGE,GRAY]):
            c.barh(row+offset,float(d),height=.18,color=color,edgecolor="white",lw=.35,zorder=3)
        item=iv.loc[mid]
        d,lo,hi=[float(item[k]) for k in ["difference","ci98_333333_lower","ci98_333333_upper"]]
        c.errorbar(d,row+.47,xerr=[[d-lo],[hi-d]],fmt="D",ms=3.3,
                   color=DARK,ecolor=DARK,capsize=2.5,elinewidth=.85,zorder=5)
        effects.append({"model":mid,"seed_differences":delta.tolist(),"mean_difference":d,"interval":[lo,hi]})
    a.axvline(ref_mean,color=BASE,lw=.9,ls=(0,(3,2)),zorder=1)
    a.set_ylim(2.75,-.65);a.set_xlim(.0802,.08565)
    a.set_yticks(range(3),labels)
    a.set_xticks([.081,.082,.083,.084,.085])
    a.set_xlabel("整体 MAE（kWh/15 min）",labelpad=8)
    a.text(ref_mean,2.64,f"{ref_mean:.5f}",ha="center",fontsize=8,color=BASE,
           bbox={"facecolor":"white","edgecolor":"none","pad":1})
    c.set_ylim(2.75,-.65);c.set_xlim(0,.0062)
    c.set_yticks(range(3),labels)
    c.set_xticks([0,.002,.004,.006],["0",".002",".004",".006"])
    c.set_xlabel("MAE差（对照 − MRG-GCN）",labelpad=8)
    clean(a);clean(c)
    fig.text(.97,.075,"黑色菱形与线：均值及七日块98.33%校正区间",ha="right",fontsize=7.7,color=DARK)
    fig.text(.97,.030,"三种子SD与时间块区间分开读取；差值单位均为kWh/15 min",ha="right",fontsize=7.7,color=BASE)
    save(fig,"fig3_9_jpl_mae_primary",{"sources":{str(p):base.digest(p) for p in
        [base.jpl.PER_SEED_CSV,base.jpl.INTERVALS_CSV,base.jpl.SUMMARY_CSV]},
        "seeds":seeds,"effects":effects,"sample_sd":True,
        "interval":"24 seven-day blocks; 10000 paired bootstrap resamples; Bonferroni 98.333% percentile",
        "observations_excluded":0})


def current():
    r,_=base.current.load_evidence()
    nodes=sorted(r,key=lambda n:-r[n]["tv_distance"])
    tv=np.array([r[n]["tv_distance"] for n in nodes]);peak=np.array([r[n]["peak_share_ratio"] for n in nodes])
    fig=plt.figure(figsize=(6.4,4.4))
    a=fig.add_axes([.145,.190,.355,.625]);c=fig.add_axes([.635,.190,.335,.625])
    title(fig,.145,"(a)  电流与均摊份额的形态差异")
    title(fig,.635,"(b)  峰值片份额相对均匀片的倍数")
    legend(fig,[Line2D([],[],marker="o",ls="none",color=BASE,label="零差异参照"),
                Line2D([],[],marker="o",ls="none",color=BLUE,label="单会话总变差距离")],.145,columns=1)
    legend(fig,[Patch(color=ORANGE,label="单会话峰值集中度"),
                Line2D([],[],ls=(0,(3,2)),color=BASE,label="样本中位数")],.635,columns=1)
    for row,(t,p) in enumerate(zip(tv,peak)):
        a.hlines(row,0,t,color="#C6D2DA",lw=2.1,zorder=2)
        a.scatter(0,row,s=23,color=BASE,edgecolor="white",lw=.5,zorder=4,clip_on=False)
        a.scatter(t,row,s=40,color=BLUE,edgecolor="white",lw=.8,zorder=4)
        a.annotate(f"{t:.3f}",(t,row),xytext=(6,0),textcoords="offset points",va="center",fontsize=8.2)
        c.barh(row,p-1,left=1,height=.52,color=ORANGE,edgecolor="white",lw=.5,zorder=3)
        c.annotate(f"{p:.2f}×",(p,row),xytext=(5,0),textcoords="offset points",va="center",fontsize=8.2)
    a.axvline(np.median(tv),color=BASE,lw=.9,ls=(0,(3,2)),zorder=1)
    c.axvline(np.median(peak),color=BASE,lw=.9,ls=(0,(3,2)),zorder=1)
    a.set_xlim(0,.76);c.set_xlim(1,5.12)
    for ax in [a,c]:ax.set_ylim(7.7,-.7);clean(ax)
    a.set_yticks(range(8),nodes);c.set_yticks(range(8),[""]*8)
    a.set_xticks([0,.2,.4,.6]);c.set_xticks([1,2,3,4,5])
    a.set_xlabel("总变差距离",labelpad=8);c.set_xlabel("峰值片份额 / 均匀份额",labelpad=8)
    fig.text(.145,.060,f"中位数 {np.median(tv):.3f}",color=BLUE,fontsize=9)
    fig.text(.635,.060,f"中位数 {np.median(peak):.2f}×",color=ORANGE,fontsize=9)
    fig.text(.97,.018,"8条有效便利样本；两面板按相同会话顺序排列",ha="right",fontsize=7.8,color=BASE)
    save(fig,"fig5_8_acn_current_shape",{"sources":{str(base.current.REPLAY_PATH.relative_to(ROOT)):base.digest(base.current.REPLAY_PATH)},
        "rows":[{"node":n,"tv_distance":float(t),"peak_share_ratio":float(p)} for n,t,p in zip(nodes,tv,peak)],
        "preselected":10,"eligible":8,"previously_excluded":2,"new_exclusions":0,
        "bar_baseline":1,"inference":"descriptive convenience sample; no uncertainty estimate"})


def pcmci():
    path=ROOT/"outputs/analysis/pcmci/pcmci_summary.json";d=json.loads(path.read_text())
    groups=[{tuple(e) for e in d[k] if e[0]!=e[1]} for k in ["confirmed_edges","te_only_edges","pcmci_only_edges"]]
    assert list(map(len,groups))==[44,32,6]
    assert all(not groups[i]&groups[j] for i in range(3) for j in range(i))
    ids=sorted({n for g in groups for edge in g for n in edge})
    te=groups[0]|groups[1];pc=groups[0]|groups[2]
    nt=np.array([sum(s==n for s,t in te) for n in ids]);np_=np.array([sum(s==n for s,t in pc) for n in ids])
    assert nt.sum()==76 and np_.sum()==50
    fig=plt.figure(figsize=(6.5,4.6))
    a=fig.add_axes([.145,.170,.355,.650]);c=fig.add_axes([.715,.170,.255,.650])
    title(fig,.145,"(a)  两法逐节点出边数比较")
    title(fig,.715,"(b)  全部有向对的交集构成")
    legend(fig,[Line2D([],[],marker="o",ls="none",color=BASE,label="TE名义候选"),
                Line2D([],[],marker="o",ls="none",color=BLUE,label="PCMCI+名义候选")],.145,columns=1)
    legend(fig,[Patch(color=BLUE,label="两法均达"),Patch(color=ORANGE,label="仅TE达"),
                Patch(color="#979797",label="仅PCMCI+达"),Patch(color="#CBCBCB",label="两法均未达")],.600,columns=2)
    for row,(n,t,p) in enumerate(zip(ids,nt,np_)):
        a.hlines(row,min(t,p),max(t,p),color="#C6D2DA",lw=2.3,zorder=2)
        a.scatter(t,row,s=43,color=BASE,edgecolor="white",lw=.7,zorder=3)
        a.scatter(p,row,s=23,color=BLUE,edgecolor="white",lw=.5,zorder=4)
        a.text(10.5,row,f"{t}/{p}",ha="right",va="center",fontsize=8)
    a.set_xlim(-.3,10.8);a.set_ylim(9.7,-.7)
    a.set_yticks(range(10),ids);a.set_xticks([0,3,6,9]);a.set_xlabel("节点间出边数",labelpad=8)
    labels=["两法均达","仅TE达","仅PCMCI+达","两法均未达"]
    counts=[44,32,6,8];colors=[BLUE,ORANGE,"#979797","#CBCBCB"]
    for row,(label,n,color) in enumerate(zip(labels,counts,colors)):
        c.barh(row,n,height=.56,color=color,edgecolor="white",lw=.5,zorder=3)
        c.text(n+1.2,row,f"{n}（{n/90:.1%}）",va="center",fontsize=8.1)
    c.set_xlim(0,70);c.set_ylim(3.7,-.7);c.set_yticks(range(4),labels)
    c.set_xticks([0,20,40,60]);c.set_xlabel("有向节点对数",labelpad=8)
    clean(a);clean(c)
    fig.text(.50,.052,"行端数字：TE / PCMCI+",ha="right",fontsize=7.8,color=BASE)
    fig.text(.97,.052,"总计90对；10个自回归对排除",ha="right",fontsize=7.8,color=BASE)
    fig.text(.97,.018,"历史未校正名义阈值对照，重合不等于确认",ha="right",fontsize=7.8,color=BASE)
    save(fig,"fig5_4_pcmci_validation_network",{"sources":{str(path.relative_to(ROOT)):base.digest(path)},
        "nodes":ids,"te_outgoing":nt.tolist(),"pcmci_outgoing":np_.tolist(),"counts":counts,
        "nonself_directed_pairs":90,"self_pairs_excluded":10,
        "threshold":"historical nominal uncorrected; no statistical confirmation claim"})


def categorical_offsets(values, center):
    """Spread marks only within a categorical column, preserving every y value."""
    out=np.full(len(values),center,dtype=float)
    placed=[]
    for idx in np.argsort(values,kind="stable"):
        for offset in [0,-.08,.08,-.16,.16,-.24,.24]:
            x=center+offset
            if not any(abs(values[idx]-y)<.00017 and abs(x-px)<.075 for px,y in placed):
                break
        out[idx]=x;placed.append((x,values[idx]))
    return out


def te():
    tm,rel,pairs,directed,_=base.te_source.load_and_validate()
    fig=plt.figure(figsize=(6.1,6.15));summary={}
    colors=[BLUE,ORANGE,"#82939E"]
    ytops=[.900,.625,.350];height=.175
    for panel,((key,label,_color),color,top) in enumerate(zip(base.te_source.RELATIONS,colors,ytops)):
        x=np.array([rel[key][i,j] for i,j in directed]);y=np.array([tm[i,j] for i,j in directed]);zero=x==0
        rho=float(spearmanr(x,y).statistic)
        z=fig.add_axes([.14,top-height,.165,height]);a=fig.add_axes([.390,top-height,.575,height])
        fig.text(.14,top+.035,f"({chr(97+panel)})  {label}",fontsize=10,weight="bold",color=color)
        fig.text(.965,top+.035,f"Spearman ρ = {rho:.2f}；n = 90",ha="right",fontsize=8.8)
        z.text(.5,1.02,f"权重=0（n={zero.sum()}）",transform=z.transAxes,ha="center",fontsize=8,color=BASE)
        a.text(.0,1.02,f"非零权重（n={(~zero).sum()}）",transform=a.transAxes,fontsize=8,color=BASE)
        for direction,marker,center in [(0,"o",-.33),(1,"^",.33)]:
            direction_mask=np.arange(90)%2==direction
            v=y[zero&direction_mask]
            z.scatter(categorical_offsets(v,center),v,s=13,marker=marker,
                      facecolor="white",edgecolor=color,lw=.7,zorder=3)
            mask=(~zero)&direction_mask
            a.scatter(x[mask],y[mask],s=16,marker=marker,
                      facecolor=color if direction==0 else "white",edgecolor=color,
                      lw=.65,alpha=.82,zorder=3)
        for i,j in pairs:
            if rel[key][i,j]>0:
                a.plot([rel[key][i,j]]*2,[tm[i,j],tm[j,i]],color="#BDC7CE",lw=.55,alpha=.5,zorder=1)
        lo,hi=float(x[~zero].min()),float(x[~zero].max());pad=max((hi-lo)*.08,.001)
        a.set_xlim(lo-pad,hi+pad);a.xaxis.set_major_locator(MaxNLocator(4));a.xaxis.set_major_formatter(FormatStrFormatter('%.3f'))
        z.set_xlim(-.66,.66);z.set_xticks([-.33,.33],["i→j","j→i"])
        z.set_ylabel("TE（nats）",fontsize=8.5,labelpad=6)
        for ax in [z,a]:
            ax.set_ylim(0,.0068);ax.set_yticks([0,.002,.004,.006]);clean(ax,axis="both")
        a.set_yticklabels([])
        if panel == 2:
            a.set_xlabel("LRE非零权重",fontsize=8.5,labelpad=4)
        summary[key]={"n":90,"zero_n":int(zero.sum()),"nonzero_n":int((~zero).sum()),
                      "rho":rho,"weights":x.tolist(),"te":y.tolist(),"nonzero_xlim":[lo-pad,hi+pad]}
    fig.text(.14,.035,"○ / △：相反方向；零权重栏横向分散仅用于避让，TE数值不变",fontsize=7.7,color=BASE)
    fig.text(.14,.012,"非零权重横轴按各关系的实际范围展开；全部观测参与ρ计算",fontsize=7.7,color=BASE)
    save(fig,"fig5_3_te_vs_relations",{"sources":{str(p.relative_to(ROOT)):base.digest(p) for p in
        [base.te_source.TE_PATH,base.te_source.REL_PATH,base.te_source.RUN_MANIFEST,base.te_source.BUNDLE_PATH]},
        "summaries":summary,"excluded":0,"y_jitter":False,"nonzero_x_jitter":False,
        "zero_strip":"categorical direction columns with display-only horizontal collision avoidance"})


if __name__=="__main__":
    jpl();current();pcmci();te()
    path=ROOT/"outputs/analysis/figure-revision-20261111/reference-style-manifest.json"
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps({"backend":"python","figures":base.SOURCES,
        "output_sha256":{f.name:base.digest(f) for stem in base.SOURCES for f in [OUT/(stem+'.svg'),OUT/(stem+'.png')]}
    },ensure_ascii=False,indent=2))
    print("Four figures recomposed from frozen observations.")
