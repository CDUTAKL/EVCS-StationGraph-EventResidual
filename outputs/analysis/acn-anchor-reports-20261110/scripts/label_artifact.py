# -*- coding: utf-8 -*-
"""标签伪影诊断。

问题：接入—断开均分标签下的"非零键"和事件边界键中，有多少实际落在
设备上报功率≈0 的完成后空窗（标签伪影），换成完成时刻截断后消失多少？
这对论文第4章"非零层排序相关仅0.420"的解读直接相关：需要先分清
非零层误差里有多少是标签构造驱动、多少是模型问题。

口径：与 extended_analysis 完全一致（严格完成时刻规则，60s 缺口桥接，
功率覆盖率>=0.95 子集，n=1,794）。逐 15min 片记录：
均分电量、截断电量、功率积分电量、电表差分电量、
该片落在完成前/后的时长占比。汇总四类分析：
  A. 伪非零键：标签>0 但实测功率≈0 的片（绝对阈值 0.01 kWh 与相对阈值 5%）
  B. 误差位置分解：|标签-实测| 按完成后主导片/完成前主导片拆分
  C. 事件边界键：含接入/完成/断开时刻的片，伪非零键在均分与截断下各多少
  D. 按完成后占桩比分层的伪非零键率（与机制分解衔接）

输出: results_artifact/artifact_bins.csv, artifact_summary.json,
      artifact_node.csv, artifact_idle_strata.csv, fig_C1, fig_C2
"""
import json
import os

import numpy as np
import pandas as pd

import extended_analysis as ext
from anchor_analysis import load_items, fname_for

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "results_artifact")
os.makedirs(OUT, exist_ok=True)
MIN_COV = 0.95
ABS_EPS = 0.01      # 实测电量低于 0.01 kWh 视为"功率≈0"
REL_EPS = 0.05      # 或低于标签片电量的 5%


def main():
    items = load_items(ext.SRC)
    for it in items:
        done = it["_done"]
        it["_valid_done_strict"] = (not pd.isna(done)) and (it["_conn"] < done <= it["_disc"])
        it["_cut_strict"] = done if it["_valid_done_strict"] else it["_disc"]

    bin_rows = []
    session_keep = []
    n_seen = 0
    for it in items:
        st = it["stationID"]
        row0 = {"sessionID": it["sessionID"], "stationID": st,
                "kWh": it["kWhDelivered"], "valid_done": it["_valid_done_strict"],
                "conn": it["_conn"], "disc": it["_disc"], "done": it["_done"]}
        f = os.path.join(ext.RAW, fname_for(it))
        if not os.path.exists(f) or os.path.getsize(f) == 0:
            continue
        df = ext.read_session(ext.RAW, it)
        if df is None:
            continue
        u15 = ext.uniform_profile(it, it["_disc"], 15)
        c15 = ext.uniform_profile(it, it["_cut_strict"], 15)
        if u15 is None or c15 is None:
            continue
        pr = ext.power_parts(df, it, 15, 60, 0)
        if pr is None or pr["coverage"] < MIN_COV:
            continue
        n_seen += 1
        m15 = ext.meter_parts(df, it, 15, 0, "boundary")
        p_prof = pr["profile"].reindex(u15.index).fillna(0.0)
        m_prof = (m15["profile"].reindex(u15.index).fillna(0.0)
                  if m15 is not None else pd.Series(0.0, index=u15.index))
        c_full = c15.reindex(u15.index).fillna(0.0)
        done = it["_done"] if it["_valid_done_strict"] else it["_disc"]
        conn, disc = it["_conn"], it["_disc"]
        dur = (disc - conn).total_seconds()
        idle = (disc - done).total_seconds() / dur if dur > 0 else np.nan
        for bstart in u15.index:
            bend = bstart + pd.Timedelta(minutes=15)
            ov = (min(bend, disc) - max(bstart, conn)).total_seconds()
            if ov <= 0:
                continue
            pre = max(0.0, (min(bend, done) - max(bstart, conn)).total_seconds())
            post = max(0.0, (min(bend, disc) - max(bstart, done)).total_seconds())
            bin_rows.append({
                "sessionID": it["sessionID"], "stationID": st,
                "bin": bstart.isoformat(),
                "u_kwh": float(u15[bstart]), "c_kwh": float(c_full[bstart]),
                "p_kwh": float(p_prof[bstart]), "m_kwh": float(m_prof[bstart]),
                "pre_share": pre / ov, "post_share": post / ov,
                "idle_ratio": idle, "kWh": it["kWhDelivered"],
            })
        session_keep.append({**row0, "idle_ratio": idle,
                             "coverage": pr["coverage"]})
        if n_seen % 300 == 0:
            print(f"  {n_seen} sessions", flush=True)

    bins = pd.DataFrame(bin_rows)
    sess = pd.DataFrame(session_keep)
    bins.to_csv(os.path.join(OUT, "artifact_bins.csv"), index=False)
    sess.to_csv(os.path.join(OUT, "artifact_sessions.csv"), index=False)
    print(f"bins: {len(bins)}, sessions: {len(sess)}", flush=True)

    ok = sess[sess.valid_done].copy()
    bins_ok = bins[bins.sessionID.isin(set(ok.sessionID))].copy()
    bins_ok["err_u"] = (bins_ok.u_kwh - bins_ok.p_kwh).abs()
    bins_ok["err_c"] = (bins_ok.c_kwh - bins_ok.p_kwh).abs()
    post_bins = bins_ok[bins_ok.post_share >= 0.5]
    pre_bins = bins_ok[bins_ok.pre_share >= 0.5]

    # ---- A. 伪非零键 ----
    def false_stats(d, label_col):
        nz = d[d[label_col] > 0]
        fa = nz[nz.p_kwh < ABS_EPS]
        fr = nz[nz.p_kwh < REL_EPS * nz[label_col]]
        return {
            f"{label_col}_nonzero_bins": int(len(nz)),
            f"{label_col}_false_abs_n": int(len(fa)),
            f"{label_col}_false_abs_rate": float(len(fa) / len(nz)) if len(nz) else np.nan,
            f"{label_col}_false_rel_n": int(len(fr)),
            f"{label_col}_false_rel_rate": float(len(fr) / len(nz)) if len(nz) else np.nan,
            f"{label_col}_false_abs_kwh": float(fa[label_col].sum()),
            f"{label_col}_nonzero_kwh": float(nz[label_col].sum()),
        }

    A = {}
    for col in ["u_kwh", "c_kwh"]:
        A.update(false_stats(bins_ok, col))

    # ---- B. 误差位置分解 ----
    B = {
        "err_u_total_kwh": float(bins_ok.err_u.sum()),
        "err_u_post_kwh": float(post_bins.err_u.sum()),
        "err_u_pre_kwh": float(pre_bins.err_u.sum()),
        "err_c_total_kwh": float(bins_ok.err_c.sum()),
        "err_c_post_kwh": float(post_bins.err_c.sum()),
        "err_c_pre_kwh": float(pre_bins.err_c.sum()),
    }
    B["err_u_post_share"] = B["err_u_post_kwh"] / B["err_u_total_kwh"]
    B["err_c_post_share"] = B["err_c_post_kwh"] / B["err_c_total_kwh"]

    # ---- C. 事件边界键（含接入/完成/断开的片） ----
    ev_ids = set()
    for _, s in ok.iterrows():
        for t in [s["conn"], s["done"], s["disc"]]:
            ev_ids.add((s["sessionID"], t.floor("15min").isoformat()))
    bins_ok["is_event"] = [(sid, b) in ev_ids for sid, b in
                           zip(bins_ok.sessionID, bins_ok.bin)]
    evb = bins_ok[bins_ok.is_event]
    C = {
        "event_bins_n": int(len(evb)),
        "event_u_false_abs_n": int(((evb.u_kwh > 0) & (evb.p_kwh < ABS_EPS)).sum()),
        "event_c_false_abs_n": int(((evb.c_kwh > 0) & (evb.p_kwh < ABS_EPS)).sum()),
        "event_u_nonzero_n": int((evb.u_kwh > 0).sum()),
        "event_c_nonzero_n": int((evb.c_kwh > 0).sum()),
    }
    C["event_u_false_rate"] = (C["event_u_false_abs_n"] / C["event_u_nonzero_n"]
                               if C["event_u_nonzero_n"] else np.nan)
    C["event_c_false_rate"] = (C["event_c_false_abs_n"] / C["event_c_nonzero_n"]
                               if C["event_c_nonzero_n"] else np.nan)

    # ---- D. idle_ratio 分层 ----
    ok2 = ok.dropna(subset=["idle_ratio"]).copy()
    ok2["idle_bin"] = pd.cut(ok2.idle_ratio, [0, 0.1, 0.3, 0.6, 1.0],
                             right=False, include_lowest=True)
    strata_rows = []
    for ib, g in ok2.groupby("idle_bin", observed=True):
        gb = bins_ok[bins_ok.sessionID.isin(set(g.sessionID))]
        nz_u = gb[gb.u_kwh > 0]
        nz_c = gb[gb.c_kwh > 0]
        strata_rows.append({
            "idle_bin": str(ib), "n_sessions": int(len(g)),
            "u_false_abs_rate": float(((nz_u.p_kwh < ABS_EPS).sum()) / len(nz_u)) if len(nz_u) else np.nan,
            "c_false_abs_rate": float(((nz_c.p_kwh < ABS_EPS).sum()) / len(nz_c)) if len(nz_c) else np.nan,
            "err_u_per_session": float((gb.u_kwh - gb.p_kwh).abs().sum() / max(len(g), 1)),
            "err_c_per_session": float((gb.c_kwh - gb.p_kwh).abs().sum() / max(len(g), 1)),
        })
    strata = pd.DataFrame(strata_rows)
    strata.to_csv(os.path.join(OUT, "artifact_idle_strata.csv"), index=False)

    # ---- 节点表 ----
    node = (bins_ok.groupby("stationID")
            .apply(lambda g: pd.Series({
                "err_u_kwh": g.err_u.sum(),
                "err_u_post_share": g.loc[g.post_share >= 0.5, "err_u"].sum() / g.err_u.sum(),
                "err_c_kwh": g.err_c.sum(),
                "u_false_abs_rate": ((g.u_kwh > 0) & (g.p_kwh < ABS_EPS)).sum() / max((g.u_kwh > 0).sum(), 1),
                "c_false_abs_rate": ((g.c_kwh > 0) & (g.p_kwh < ABS_EPS)).sum() / max((g.c_kwh > 0).sum(), 1),
            }), include_groups=False)
            .reset_index())
    node.to_csv(os.path.join(OUT, "artifact_node.csv"), index=False)

    summary = {
        "n_sessions_power_subset": int(len(sess)),
        "n_sessions_valid_done": int(len(ok)),
        "n_bins": int(len(bins_ok)),
        "n_post_bins": int(len(post_bins)),
        "thresholds": {"abs_eps_kwh": ABS_EPS, "rel_eps": REL_EPS,
                       "post_bin": "post_share>=0.5"},
        "A_false_nonzero": A,
        "B_error_location": B,
        "C_event_boundary": C,
    }
    json.dump(summary, open(os.path.join(OUT, "artifact_summary.json"), "w"),
              ensure_ascii=False, indent=1)
    print(json.dumps(summary, ensure_ascii=False, indent=1), flush=True)

    # ---- 图 ----
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    labels = ["均分", "截断"]
    post = [B["err_u_post_kwh"], B["err_c_post_kwh"]]
    pre = [B["err_u_pre_kwh"], B["err_c_pre_kwh"]]
    ax[0].bar(labels, post, label="完成后主导片误差")
    ax[0].bar(labels, pre, bottom=post, label="完成前主导片误差")
    ax[0].set_ylabel("累计绝对误差 (kWh)")
    ax[0].set_title("误差位置分解（功率实测为参照）")
    ax[0].legend()
    x = np.arange(len(strata))
    ax[1].plot(x, strata.u_false_abs_rate, "o-", label="均分标签")
    ax[1].plot(x, strata.c_false_abs_rate, "s-", label="截断标签")
    ax[1].set_xticks(x)
    ax[1].set_xticklabels(strata.idle_bin, rotation=20)
    ax[1].set_xlabel("完成后占桩比分层")
    ax[1].set_ylabel("伪非零键占比（实测功率≈0）")
    ax[1].set_title("伪非零键率随占桩比的变化")
    ax[1].legend()
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_C1_artifact.png"), dpi=150)
    print("done ->", OUT, flush=True)


if __name__ == "__main__":
    main()
