# -*- coding: utf-8 -*-
"""锚定分析图表生成。读取 results/session_anchor.csv 与节点序列, 输出 PNG。"""
import os
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["figure.dpi"] = 150
plt.rcParams["font.sans-serif"] = ["Noto Sans CJK SC", "Noto Sans CJK JP", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
OUT = sys.argv[1] if len(sys.argv) > 1 else "results"
TS_DIR = os.environ.get("ACN_TS_DIR", os.path.join("data", "static"))
SESSIONS = os.environ.get("ACN_SESSIONS", os.path.join("data", "acndata_sessions-2.json"))
sess = pd.read_csv(os.path.join(OUT, "session_anchor.csv"))
ok = sess[sess["ok"]].copy()

# ---- 图1: 示例会话累计能量曲线 ----
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from anchor_analysis import load_items, fname_for, read_session, meter_profile_from_df, uniform_profile  # noqa

items = load_items(SESSIONS)
for it in items:
    it["_conn"] = pd.to_datetime(it["connectionTime"], utc=True)
    it["_disc"] = pd.to_datetime(it["disconnectTime"], utc=True)
    it["_done"] = pd.to_datetime(it["doneChargingTime"], utc=True) if it.get("doneChargingTime") else pd.NaT
by_sid = {it["sessionID"]: it for it in items}
# 选两条: 完成后停留占比高的 + TVD 中位附近的
rank = ok.sort_values("share_after_done_uniform", ascending=False)
picks = [rank.iloc[3]["sessionID"], ok.loc[(ok["tvd_uniform"] - ok["tvd_uniform"].median()).abs().idxmin(), "sessionID"]]
fig, axes = plt.subplots(1, 2, figsize=(11, 3.8))
for ax, sid in zip(axes, picks):
    it = by_sid[sid]
    prof, e_meter, _, _ = meter_profile_from_df(read_session(TS_DIR, it), it)
    pu, _ = uniform_profile(it, "_disc")
    pc, _ = uniform_profile(it, "_cut")
    t = prof.index + pd.Timedelta(minutes=7.5)
    ax.step(t, prof.cumsum(), where="mid", label="设备电表(实测)", lw=1.8, color="#1f77b4")
    ax.step(pu.index + pd.Timedelta(minutes=7.5), pu.cumsum(), where="mid", label="接入—断开均分", lw=1.5, ls="--", color="#d62728")
    ax.step(pc.index + pd.Timedelta(minutes=7.5), pc.cumsum(), where="mid", label="完成时刻截断", lw=1.5, ls=":", color="#2ca02c")
    ax.axvline(it["_done"], color="gray", ls=":", lw=1)
    ax.text(it["_done"], ax.get_ylim()[1] * 0.05, " 充电完成", rotation=90, color="gray", fontsize=8)
    ax.set_title(f"{it['spaceID']}  {sid.split('_')[-1][:16]}", fontsize=10)
    ax.set_xlabel("时间 (UTC)"); ax.set_ylabel("累计能量 (kWh)")
    ax.legend(fontsize=8); ax.tick_params(axis="x", labelrotation=30, labelsize=8)
fig.suptitle("会话累计能量: 设备实测 vs 两种代理口径", y=1.02)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "fig1_example_sessions.png"), bbox_inches="tight")
plt.close(fig)

# ---- 图2: TVD 分布 ----
fig, ax = plt.subplots(figsize=(6.5, 3.8))
bins = np.linspace(0, 1, 51)
for col, lab, c in [("tvd_uniform", "接入—断开均分", "#d62728"), ("tvd_uniform_len", "按重叠长度均分", "#ff9896"), ("tvd_cut", "完成时刻截断", "#2ca02c")]:
    ax.hist(ok[col].dropna(), bins=bins, histtype="step", lw=1.8, label=lab, color=c, density=True)
ax.set_xlabel("总变差距离 TVD (会话片份额, n=%d)" % len(ok))
ax.set_ylabel("密度"); ax.legend(fontsize=9)
ax.set_title("代理标签与设备实测片分布的形态偏差")
fig.tight_layout()
fig.savefig(os.path.join(OUT, "fig2_tvd_hist.png"), bbox_inches="tight")
plt.close(fig)

# ---- 图3: CA-303 节点 15 min 序列 ----
import anchor_analysis as aa
node_meas, node_uni, node_cut = {}, {}, {}
for it in items:
    df = aa.read_session(TS_DIR, it)
    if df is None:
        continue
    r = aa.meter_profile_from_df(df, it)
    if r is None:
        continue
    prof = r[0]
    u = aa.uniform_profile(it, "_disc")
    c = aa.uniform_profile(it, "_cut")
    node_meas[it["stationID"]] = node_meas.get(it["stationID"], pd.Series(dtype=float)).add(prof, fill_value=0)
    if u:
        node_uni[it["stationID"]] = node_uni.get(it["stationID"], pd.Series(dtype=float)).add(u[0], fill_value=0)
    if c:
        node_cut[it["stationID"]] = node_cut.get(it["stationID"], pd.Series(dtype=float)).add(c[0], fill_value=0)
st = "2-39-139-28"  # CA-303
m = node_meas[st]
grid = pd.date_range(m.index.min(), m.index.max() + pd.Timedelta(minutes=15), freq="15min")[:-1]
m = m.reindex(grid).fillna(0)
u = node_uni[st].reindex(grid).fillna(0)
c = node_cut[st].reindex(grid).fillna(0)
fig, ax = plt.subplots(figsize=(11, 3.6))
tt = grid + pd.Timedelta(minutes=7.5)
ax.plot(tt, m, lw=0.9, label="设备电表(实测)", color="#1f77b4")
ax.plot(tt, u, lw=0.9, label="接入—断开均分", color="#d62728", alpha=0.85)
ax.plot(tt, c, lw=0.9, label="完成时刻截断", color="#2ca02c", alpha=0.85)
ax.set_ylabel("kWh/15min"); ax.set_title("CA-303 (2-39-139-28) 节点 15 min 能量: 实测 vs 代理 (2018-05-01 至 2018-06-11)")
ax.legend(fontsize=9); ax.tick_params(axis="x", labelrotation=30, labelsize=8)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "fig3_node_ca303.png"), bbox_inches="tight")
plt.close(fig)

# ---- 图4: 10 节点 MAE 对比 ----
node = pd.read_csv(os.path.join(OUT, "node_anchor_summary.csv"))
# 与论文表 2-2 的冻结主分析集合一致；勿替换为窗口内高负荷候选节点。
ten = ["CA-303", "CA-304", "CA-305", "CA-307", "CA-311",
       "CA-315", "CA-317", "CA-321", "CA-327", "CA-489"]
nn = node.set_index("spaceID").loc[ten]
x = np.arange(len(ten)); w = 0.38
fig, ax = plt.subplots(figsize=(8, 3.8))
ax.bar(x - w / 2, nn["mae_uniform"], w, label="接入—断开均分", color="#d62728")
ax.bar(x + w / 2, nn["mae_cut"], w, label="完成时刻截断", color="#2ca02c")
for i, (a, b) in enumerate(zip(nn["mae_uniform"], nn["mae_cut"])):
    ax.text(i, max(a, b) + 0.004, f"-{(1-b/a)*100:.0f}%", ha="center", fontsize=8)
ax.set_xticks(x); ax.set_xticklabels(ten, fontsize=9)
ax.set_ylabel("节点 15 min MAE (kWh/15min)")
ax.set_title("论文 10 个主节点: 代理标签 vs 设备实测 (2018-05/06 窗口)")
ax.legend(fontsize=9)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "fig4_node_mae.png"), bbox_inches="tight")
plt.close(fig)

# ---- 图5: 完成后电量占比: 均分标签 vs 实测 ----
fig, ax = plt.subplots(figsize=(6.5, 3.8))
bins = np.linspace(0, 0.8, 41)
ax.hist(ok["share_after_done_uniform"].clip(0, 0.8), bins=bins, histtype="step", lw=1.8, label="接入—断开均分标签", color="#d62728", density=True)
ax.hist(ok["share_after_done_measured"].clip(0, 0.8), bins=bins, histtype="step", lw=1.8, label="累计电表差分（A）", color="#1f77b4", density=True)
ax.hist(ok["share_after_done_power"].dropna().clip(0, 0.8), bins=bins, histtype="step", lw=1.5, label="功率积分（B子集）", color="#9467bd", density=True)
ax.set_xlabel("落在充电完成时刻之后的电量占比")
ax.set_ylabel("密度"); ax.legend(fontsize=9)
ax.set_title("均分标签把多少电量放到了充电完成之后")
fig.tight_layout()
fig.savefig(os.path.join(OUT, "fig5_share_after_done.png"), bbox_inches="tight")
plt.close(fig)
# ---- 图6: 基准B(设备功率积分) 10 节点 MAE 对比 ----
nodep = pd.read_csv(os.path.join(OUT, "node_power_summary.csv"))
np10 = nodep.set_index("spaceID").loc[ten]
fig, ax = plt.subplots(figsize=(8, 3.8))
ax.bar(x - w / 2, np10["mae_uniform"], w, label="接入—断开均分", color="#d62728")
ax.bar(x + w / 2, np10["mae_cut"], w, label="完成时刻截断(含回退)", color="#2ca02c")
for i, (a, b) in enumerate(zip(np10["mae_uniform"], np10["mae_cut"])):
    ax.text(i, max(a, b) + 0.004, f"-{(1-b/a)*100:.0f}%", ha="center", fontsize=8)
ax.set_xticks(x); ax.set_xticklabels(ten, fontsize=9)
ax.set_ylabel("节点 15 min MAE (kWh/15min)")
ax.set_title("基准B: 与设备 Power(kW) 积分序列对比 (高覆盖子集, n=%d)" % int(nodep["n_sessions_power"].sum()))
ax.legend(fontsize=9)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "fig6_power_mae.png"), bbox_inches="tight")
plt.close(fig)

# ---- 图7: 设备实测功率曲线与 15 min 积分示例 ----
sample6 = [f for f in os.listdir(TS_DIR)
           if f.startswith("2-39-139-28-2018-06")][0]
d6 = pd.read_csv(os.path.join(TS_DIR, sample6), index_col=0, parse_dates=True)
fig, axes = plt.subplots(2, 1, figsize=(9, 5.2), sharex=True,
                         gridspec_kw={"height_ratios": [1.4, 1]})
axes[0].plot(d6.index, d6["Power (kW)"], lw=0.8, color="#1f77b4")
axes[0].set_ylabel("设备上报功率 (kW)")
axes[0].set_title("CA-303 实测功率曲线 (约4s采样) 与 15 min 积分电量\n" + sample6.replace(".csv.gz", ""), fontsize=10)
p15 = d6["Power (kW)"].resample("15min").mean() * 0.25
axes[1].bar(p15.index, p15.values, width=0.009, color="#2ca02c")
axes[1].set_ylabel("15 min 电量(kWh,均值×0.25h示意)")
axes[1].tick_params(axis="x", labelrotation=30, labelsize=8)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "fig7_power_trace.png"), bbox_inches="tight")
plt.close(fig)
print("figures saved to", OUT)
