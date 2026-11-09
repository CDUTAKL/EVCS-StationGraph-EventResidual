# -*- coding: utf-8 -*-
"""ACN-Data Static 设备功率/电表锚定分析 (v3)。

相对 v1/v2 的修正:
  1. power_energy 由右端点求和改为真正的分段线性梯形积分, 并显式处理缺测:
     仅在相邻两点均非缺测时积分, 不跨缺测段桥接; 同时报告功率时间覆盖率。
  2. 完成时刻截断遵循论文规则: 仅当 接入<=完成<=断开 且完成时刻非空时使用完成时刻,
     否则回退到断开时刻。
  3. 新增功率积分 15 min 序列基准 (仅高覆盖会话), 与均分/截断代理在同一会话子集上比较。
  4. 总能量、覆盖率与分箱积分均先按接入/断开时刻裁剪；覆盖率分母为完整会话时长。
  5. 新增 B 子集上的同样本电表对照，以及由功率积分序列直接计算的完成后电量占比。

基准 A (全量有效会话): Energy Delivered 累计电表差分 (cummax 单调包络)。
基准 B (高功率覆盖子集): Power (kW) 分段线性积分到 15 min 片。
"""
import json
import os
import sys
import numpy as np
import pandas as pd

BIN = pd.Timedelta(minutes=15)
MIN_COV = 0.95  # 功率时间覆盖率阈值, 低于此不进入基准 B


def load_items(path):
    text = open(path, encoding="utf-8").read().rstrip()
    try:
        items = json.loads(text)["_items"]
    except json.JSONDecodeError:
        if text.endswith(","):
            text = text[:-1] + "]}"
        items = json.loads(text)["_items"]
    for it in items:
        it["_conn"] = pd.to_datetime(it["connectionTime"], utc=True)
        it["_disc"] = pd.to_datetime(it["disconnectTime"], utc=True)
        it["_done"] = pd.to_datetime(it["doneChargingTime"], utc=True) if it.get("doneChargingTime") else pd.NaT
        # 论文规则: 顺序有效才用完成时刻, 否则回退断开时刻
        valid_done = (not pd.isna(it["_done"])) and (it["_conn"] <= it["_done"] <= it["_disc"])
        it["_cut"] = it["_done"] if valid_done else it["_disc"]
        it["_cut_fallback"] = not valid_done
    return items


def fname_for(it):
    parts = it["sessionID"].split("_", 4)
    return "-".join(parts[:4]) + "-" + parts[4].replace(" ", "T").replace(":", "-").replace(".", "-") + ".csv.gz"


def read_session(ts_dir, it):
    f = os.path.join(ts_dir, fname_for(it))
    if not os.path.exists(f) or os.path.getsize(f) == 0:
        return None
    try:
        return pd.read_csv(f, index_col=0, parse_dates=True)
    except Exception:
        return None


def meter_profile_from_df(df, it):
    """电表差分 15 min 能量剖面。返回 (profile, 电表总量, 电压非空数, 功率非空数)。"""
    n_v = int(df["Voltage (V)"].notna().sum())
    n_p = int(df["Power (kW)"].notna().sum())
    meter = df["Energy Delivered (kWh)"].astype(float)
    if meter.dropna().empty:
        return None
    imax = meter.values.argmax()
    meter = meter.iloc[: imax + 1].dropna()
    meter = meter[~meter.index.duplicated(keep="last")]
    meter = meter.cummax()  # 单调包络, 消除 UNPLUGGED 归零与中途复位
    e_meter_total = float(meter.iloc[-1])
    if len(meter) < 2 or e_meter_total <= 0:
        return None
    t0, t1 = it["_conn"], it["_disc"]
    grid = pd.date_range(t0.floor("15min"), t1.ceil("15min"), freq="15min")
    m = meter.reindex(meter.index.union(grid)).interpolate("time").ffill().bfill()
    m = m.loc[grid]

    def val_at(t):
        return float(np.interp(t.value, m.index.values.astype("int64"), m.values))

    e_at = [val_at(t) for t in [t0, t1]]
    diff = np.diff(m.values)
    prof = pd.Series(diff, index=grid[:-1])
    if len(prof) == 1:
        prof.iloc[0] = e_at[1] - e_at[0]
    else:
        prof.iloc[0] *= (grid[1] - t0) / BIN
        prof.iloc[-1] *= (t1 - grid[-2]) / BIN
    return prof, e_meter_total, n_v, n_p


def power_profile_from_df(df, it):
    """Power (kW) 分段线性梯形积分到 15 min 片。

    仅对相邻两点均非缺测的区间积分 (不跨缺测段桥接)。
    返回 (profile, 总能量kWh, 时间覆盖率) 或 None。
    """
    t0, t1 = it["_conn"], it["_disc"]
    # 先按接入/断开时刻裁剪, 再计算总能量、覆盖率与分箱积分, 保证三者同一边界
    df = df.loc[(df.index >= t0) & (df.index <= t1)]
    p = df["Power (kW)"].astype(float)
    if p.notna().sum() < 2:
        return None
    grid = pd.date_range(t0.floor("15min"), t1.ceil("15min"), freq="15min")
    if len(grid) < 2:
        return None
    ns = p.index.values.astype("datetime64[ns]").astype("int64") / 1e9
    pv = p.values
    valid = ~np.isnan(pv)
    idx = np.where(valid[:-1] & valid[1:])[0]
    if len(idx) == 0:
        return None
    ta, tb = ns[idx], ns[idx + 1]
    pa, pb = pv[idx], pv[idx + 1]
    dt = tb - ta
    keep = (dt > 0) & (tb > t0.value / 1e9) & (ta < t1.value / 1e9)
    ta, tb, pa, pb, dt = ta[keep], tb[keep], pa[keep], pb[keep], dt[keep]
    if len(dt) == 0:
        return None
    # 分母固定为接入至断开的完整会话时长；首末采样点未覆盖的端部不计为已覆盖。
    total_seconds = (t1 - t0).total_seconds()
    coverage = float(dt.sum() / total_seconds) if total_seconds > 0 else 0.0
    e_total = float((0.5 * (pa + pb) * dt / 3600.0).sum())

    grid_s = grid.values.astype("datetime64[ns]").astype("int64") / 1e9
    ia = np.clip(np.searchsorted(grid_s, ta, side="right") - 1, 0, len(grid) - 2)
    ib = np.clip(np.searchsorted(grid_s, tb, side="right") - 1, 0, len(grid) - 2)
    out = np.zeros(len(grid) - 1)
    slope = (pb - pa) / dt  # kW/s

    def seg_energy(j, lo, hi):
        # ∫ p dt, p 在 [ta,tb] 上线性
        return (pa[j] * (hi - lo) + slope[j] * ((hi - ta[j]) ** 2 - (lo - ta[j]) ** 2) / 2) / 3600.0

    same = ia == ib
    # 同片区间: 直接梯形 (含 t0/t1 边界裁剪)
    for j in np.where(same)[0]:
        lo = max(ta[j], grid_s[ia[j]], t0.value / 1e9)
        hi = min(tb[j], grid_s[ia[j] + 1], t1.value / 1e9)
        if hi > lo:
            out[ia[j]] += seg_energy(j, lo, hi)
    # 跨片区间: 逐片交集积分 (dt 中位约 4s, 跨片对占比很小)
    for j in np.where(~same)[0]:
        for k in range(ia[j], ib[j] + 1):
            lo = max(ta[j], grid_s[k], t0.value / 1e9)
            hi = min(tb[j], grid_s[k + 1], t1.value / 1e9)
            if hi > lo:
                out[k] += seg_energy(j, lo, hi)
    return pd.Series(out, index=grid[:-1]), e_total, coverage


def uniform_profile(it, end_field):
    """均分代理 (论文口径): 覆盖片每片 E/|B|; 同时给出按重叠长度加权版本。"""
    t0, t1 = it["_conn"], it[end_field]
    if pd.isna(t1) or t1 <= t0:
        return None
    grid = pd.date_range(t0.floor("15min"), t1.ceil("15min"), freq="15min")
    n = len(grid) - 1
    if n <= 0:
        return None
    prof = pd.Series(it["kWhDelivered"] / n, index=grid[:-1])
    overlap = pd.Series(
        [(min(t1, b + BIN) - max(t0, b)).total_seconds() / 900.0 for b in grid[:-1]],
        index=grid[:-1],
    )
    prof_len = it["kWhDelivered"] * overlap / overlap.sum()
    return prof, prof_len


def tvd(p, q):
    p = p / p.sum()
    q = q / q.sum()
    aligned = pd.concat([p, q], axis=1).fillna(0).values
    return 0.5 * np.abs(aligned[:, 0] - aligned[:, 1]).sum()


def node_stats(m, u, c):
    grid = pd.date_range(m.index.min(), m.index.max() + BIN, freq="15min")[:-1]
    m = m.reindex(grid).fillna(0)
    u = u.reindex(grid).fillna(0)
    c = c.reindex(grid).fillna(0)
    return {
        "E_meas_kWh": float(m.sum()),
        "zero_rate_measured": float((m <= 1e-9).mean()),
        "zero_rate_uniform": float((u <= 1e-9).mean()),
        "zero_rate_cut": float((c <= 1e-9).mean()),
        "mae_uniform": float((m - u).abs().mean()),
        "mae_cut": float((m - c).abs().mean()),
        "rmse_uniform": float(np.sqrt(((m - u) ** 2).mean())),
        "corr_uniform": float(np.corrcoef(m.values, u.values)[0, 1]) if m.std() > 0 and u.std() > 0 else np.nan,
    }


def main():
    src, ts_dir, out = sys.argv[1], sys.argv[2], sys.argv[3]
    os.makedirs(out, exist_ok=True)
    items = load_items(src)

    rows = []
    nm, nu, nc = {}, {}, {}           # 基准 A: 电表 (全量)
    pmeas, puni, pcutd = {}, {}, {}   # 基准 B: 功率 (高覆盖子集)
    sm, su, sc = {}, {}, {}           # 同样本对照: B 子集上的电表基准与代理标签
    for k, it in enumerate(items):
        df = read_session(ts_dir, it)
        if df is None:
            rows.append({"sessionID": it["sessionID"], "ok": False})
            continue
        r = meter_profile_from_df(df, it)
        if r is None:
            rows.append({"sessionID": it["sessionID"], "ok": False})
            continue
        prof, e_meter, n_v, n_p = r
        pw = power_profile_from_df(df, it)
        E = it["kWhDelivered"]
        u = uniform_profile(it, "_disc")
        c = uniform_profile(it, "_cut")
        row = {
            "sessionID": it["sessionID"], "stationID": it["stationID"], "spaceID": it["spaceID"],
            "ok": True, "kWh": E, "e_meter": e_meter,
            "rel_err_meter": (e_meter - E) / E, "n_volt": n_v, "n_power": n_p,
            "cut_fallback": bool(it["_cut_fallback"]),
            "dur_min": (it["_disc"] - it["_conn"]).total_seconds() / 60,
            "charge_min": (it["_done"] - it["_conn"]).total_seconds() / 60 if not pd.isna(it["_done"]) else np.nan,
            "n_bins": len(prof),
        }
        if pw is not None:
            pprof, e_power, cov = pw
            row.update({
                "e_power": e_power, "power_coverage": cov,
                "rel_err_power": (e_power - E) / E,
                "power_subset": cov >= MIN_COV,
            })
        else:
            row.update({"e_power": np.nan, "power_coverage": 0.0,
                        "rel_err_power": np.nan, "power_subset": False})
        if not pd.isna(it["_done"]):
            row["share_after_done_measured"] = float(prof[prof.index >= it["_done"]].sum() / prof.sum())
        if u is not None:
            pu, pu_len = u
            row["tvd_uniform"] = tvd(pu.clip(lower=0), prof.clip(lower=0))
            row["tvd_uniform_len"] = tvd(pu_len.clip(lower=0), prof.clip(lower=0))
            row["mae_uniform"] = float((pu - prof.reindex(pu.index).fillna(0)).abs().sum() / len(pu))
            if not pd.isna(it["_done"]):
                row["share_after_done_uniform"] = float(pu[pu.index >= it["_done"]].sum() / E)
            nu[it["stationID"]] = nu.get(it["stationID"], pd.Series(dtype=float)).add(pu, fill_value=0)
        if c is not None:
            pcut = c[0]
            row["tvd_cut"] = tvd(pcut.clip(lower=0), prof.clip(lower=0))
            row["mae_cut"] = float((pcut - prof.reindex(pcut.index).fillna(0)).abs().sum() / len(pcut))
            nc[it["stationID"]] = nc.get(it["stationID"], pd.Series(dtype=float)).add(pcut, fill_value=0)
        nm[it["stationID"]] = nm.get(it["stationID"], pd.Series(dtype=float)).add(prof, fill_value=0)
        # 基准 B: 高功率覆盖子集, 代理标签用同一会话集合
        if row["power_subset"] and u is not None and c is not None:
            pmeas[it["stationID"]] = pmeas.get(it["stationID"], pd.Series(dtype=float)).add(pprof, fill_value=0)
            puni[it["stationID"]] = puni.get(it["stationID"], pd.Series(dtype=float)).add(u[0], fill_value=0)
            pcutd[it["stationID"]] = pcutd.get(it["stationID"], pd.Series(dtype=float)).add(c[0], fill_value=0)
            sm[it["stationID"]] = sm.get(it["stationID"], pd.Series(dtype=float)).add(prof, fill_value=0)
            su[it["stationID"]] = su.get(it["stationID"], pd.Series(dtype=float)).add(u[0], fill_value=0)
            sc[it["stationID"]] = sc.get(it["stationID"], pd.Series(dtype=float)).add(c[0], fill_value=0)
            if not pd.isna(it["_done"]):
                row["share_after_done_power"] = float(pprof[pprof.index >= it["_done"]].sum() / pprof.sum()) if pprof.sum() > 0 else np.nan
        if (k + 1) % 500 == 0:
            print(f"processed {k+1}/{len(items)}", flush=True)
        rows.append(row)

    sess = pd.DataFrame(rows)
    sess.to_csv(os.path.join(out, "session_anchor.csv"), index=False)

    # 节点级: 基准 A
    stats = []
    for st in sorted(nm):
        d = node_stats(nm[st], nu.get(st, pd.Series(dtype=float)), nc.get(st, pd.Series(dtype=float)))
        space = sess.loc[sess["stationID"] == st, "spaceID"]
        d.update({"stationID": st, "spaceID": space.iloc[0] if len(space) else "",
                  "n_sessions": int((sess["stationID"] == st).sum())})
        stats.append(d)
    node = pd.DataFrame(stats)
    node.to_csv(os.path.join(out, "node_anchor_summary.csv"), index=False)

    # 节点级: 基准 B (功率高覆盖子集)
    stats_p = []
    for st in sorted(pmeas):
        d = node_stats(pmeas[st], puni[st], pcutd[st])
        sub = sess[(sess["stationID"] == st) & (sess["power_subset"])]
        d.update({"stationID": st, "spaceID": sub["spaceID"].iloc[0],
                  "n_sessions_power": len(sub),
                  "coverage_median": float(sub["power_coverage"].median())})
        stats_p.append(d)
    node_p = pd.DataFrame(stats_p)
    node_p.to_csv(os.path.join(out, "node_power_summary.csv"), index=False)

    # 同样本对照: 在 B 子集上同时计算电表基准, 消除样本集合差异
    stats_s = []
    for st in sorted(sm):
        db = node_stats(pmeas[st], puni[st], pcutd[st])
        da = node_stats(sm[st], su[st], sc[st])
        stats_s.append({
            "stationID": st, "spaceID": node_p.set_index("stationID").loc[st, "spaceID"],
            "n_sessions": int(node_p.set_index("stationID").loc[st, "n_sessions_power"]),
            "mae_uniform_power": db["mae_uniform"], "mae_cut_power": db["mae_cut"],
            "mae_uniform_meter_same": da["mae_uniform"], "mae_cut_meter_same": da["mae_cut"],
            "E_power_kWh": db["E_meas_kWh"], "E_meter_same_kWh": da["E_meas_kWh"],
        })
    pd.DataFrame(stats_s).to_csv(os.path.join(out, "node_same_subset.csv"), index=False)

    ok = sess[sess["ok"]].copy()
    print("=== 会话级 (基准 A 电表) ===")
    print("有效会话:", len(ok), "/", len(sess))
    print("电表电量 vs kWhDelivered: 中位相对误差 %.4f, |err|<=5%% 占比 %.3f"
          % (ok["rel_err_meter"].median(), (ok["rel_err_meter"].abs() <= 0.05).mean()))
    print("截断回退到断开时刻的会话数:", int(ok["cut_fallback"].sum()))
    print("TVD 均分 %.3f / 重叠长度 %.3f / 截断 %.3f (中位数)"
          % (ok["tvd_uniform"].median(), ok["tvd_uniform_len"].median(), ok["tvd_cut"].median()))
    print("完成后电量占比: 均分 会话等权 %.3f 电量加权 %.3f; 实测 会话等权 %.3f 电量加权 %.3f"
          % (ok["share_after_done_uniform"].median(),
             (ok["share_after_done_uniform"] * ok["kWh"]).sum() / ok["kWh"].sum(),
             ok["share_after_done_measured"].median(),
             (ok["share_after_done_measured"] * ok["kWh"]).sum() / ok["kWh"].sum()))
    print("\n=== 功率积分能量一致性 (修正后: 分段线性梯形积分) ===")
    pw_all = ok.dropna(subset=["rel_err_power"])
    print("全体有功率会话 n=%d: 中位相对误差 %.4f, |err|<=5%% 占比 %.3f"
          % (len(pw_all), pw_all["rel_err_power"].median(), (pw_all["rel_err_power"].abs() <= 0.05).mean()))
    pw_hi = ok[ok["power_subset"]]
    print("高覆盖(coverage>=%.2f) n=%d: 中位相对误差 %.4f, |err|<=5%% 占比 %.3f"
          % (MIN_COV, len(pw_hi), pw_hi["rel_err_power"].median(), (pw_hi["rel_err_power"].abs() <= 0.05).mean()))
    print("功率时间覆盖率: 中位数 %.4f, <0.95 占比 %.3f"
          % (ok["power_coverage"].median(), (ok["power_coverage"] < MIN_COV).mean()))
    sp = ok.dropna(subset=["share_after_done_power"])
    print("完成后电量占比(功率积分序列, B子集 n=%d): 会话等权中位数 %.4f, 电量加权 %.4f"
          % (len(sp), sp["share_after_done_power"].median(),
             (sp["share_after_done_power"] * sp["kWh"]).sum() / sp["kWh"].sum()))
    nsame = pd.DataFrame(stats_s)
    print("同样本对照(B子集 %d会话): 功率基准 MAE均分 %.4f 截断 %.4f | 电表基准 MAE均分 %.4f 截断 %.4f"
          % (int(nsame["n_sessions"].sum()), nsame["mae_uniform_power"].mean(), nsame["mae_cut_power"].mean(),
             nsame["mae_uniform_meter_same"].mean(), nsame["mae_cut_meter_same"].mean()))
    print("同样本能量总量比 电表/功率 = %.4f" % (nsame["E_meter_same_kWh"].sum() / nsame["E_power_kWh"].sum()))
    print("\n=== 节点级 ===")
    print("基准A 52节点: MAE均分 %.4f 截断 %.4f corr %.3f 零片率 实测/均分/截断 %.3f/%.3f/%.3f"
          % (node["mae_uniform"].mean(), node["mae_cut"].mean(), node["corr_uniform"].mean(),
             node["zero_rate_measured"].mean(), node["zero_rate_uniform"].mean(), node["zero_rate_cut"].mean()))
    print("基准B 功率子集 %d节点 %d会话: MAE均分 %.4f 截断 %.4f corr %.3f 零片率 实测/均分/截断 %.3f/%.3f/%.3f"
          % (len(node_p), int(node_p["n_sessions_power"].sum()),
             node_p["mae_uniform"].mean(), node_p["mae_cut"].mean(), node_p["corr_uniform"].mean(),
             node_p["zero_rate_measured"].mean(), node_p["zero_rate_uniform"].mean(), node_p["zero_rate_cut"].mean()))
    ten = ["CA-303", "CA-305", "CA-307", "CA-311", "CA-317", "CA-319", "CA-324", "CA-327", "CA-489", "CA-496"]
    print("\n10 主节点 (基准A | 基准B):")
    for sp in ten:
        ra = node.set_index("spaceID").loc[sp]
        line = "%s: A 均分=%.4f 截断=%.4f" % (sp, ra["mae_uniform"], ra["mae_cut"])
        if sp in set(node_p["spaceID"]):
            rb = node_p.set_index("spaceID").loc[sp]
            line += " | B(n=%d) 均分=%.4f 截断=%.4f" % (rb["n_sessions_power"], rb["mae_uniform"], rb["mae_cut"])
        else:
            line += " | B 无高覆盖会话"
        print(line)


if __name__ == "__main__":
    main()
