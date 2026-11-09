# -*- coding: utf-8 -*-
"""ACN-Data Static 前五项补充分析。

1. 积分规则与参数敏感性
2. 高覆盖子集代表性
3. 均分标签偏差机制分解
4. 多时间尺度与聚合尺度
5. 统计不确定性与显著性

参考口径：有效完成时刻必须满足 接入 < 完成 <= 断开；完成等于接入的零时长
会话因无法承载正交付电量，按无效完成时刻回退断开时刻。
"""
import json
import math
import os
import pickle
import sys
import warnings
from collections import Counter, defaultdict

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=UserWarning)

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.environ.get("ACN_SESSIONS", "/mnt/agents/upload/acndata_sessions-2.json")
RAW = os.environ.get("ACN_TS_DIR", "/mnt/agents/acn_static_cg1")
OUT = os.environ.get("ACN_EXTENDED_OUT", os.path.join(BASE, "results_extended"))
os.makedirs(OUT, exist_ok=True)

sys.path.insert(0, BASE)
from anchor_analysis import fname_for, read_session  # noqa: E402

GAPS = [15, 30, 60, 300]
COV_THRESHOLDS = [0.90, 0.95, 0.99]
OFFSETS = [0, 5, 10]
RESOLUTIONS = [15, 30, 60]
MAIN10 = {"CA-303", "CA-305", "CA-307", "CA-304", "CA-311",
          "CA-317", "CA-315", "CA-327", "CA-489", "CA-321"}
MIN15 = pd.Timedelta(minutes=15)
EPOCH = pd.Timestamp("1970-01-01", tz="UTC")
MIN_COV = 0.95


def grid_for(t0, t1, bw, offset_min=0):
    """以 offset 为相位起点，生成覆盖 [t0,t1] 的等宽网格。"""
    bw = pd.Timedelta(minutes=bw)
    origin = EPOCH + pd.Timedelta(minutes=offset_min)
    start = origin + math.floor((t0 - origin) / bw) * bw
    end = origin + math.ceil((t1 - origin) / bw) * bw
    if end <= start:
        end = start + bw
    return pd.date_range(start, end, freq=bw)


def cumulative_meter(df):
    meter = df["Energy Delivered (kWh)"].astype(float)
    if meter.dropna().empty:
        return None
    imax = meter.values.argmax()
    meter = meter.iloc[: imax + 1].dropna()
    meter = meter[~meter.index.duplicated(keep="last")]
    meter = meter.cummax()
    if len(meter) < 2 or float(meter.iloc[-1]) <= 0:
        return None
    return meter


def interp_val(m, t):
    return float(np.interp(pd.Timestamp(t).value, m.index.values.astype("int64"), m.values))


def meter_parts(df, it, bw=15, offset=0, edge_mode="boundary"):
    """累计电量差分到时间片。

    boundary: 在每个分箱与会话时段的交集中，用插值累计量端点相减。
    rescale : 先按完整分箱差分，再将会话总能量按比例重新归一。
    """
    m = cumulative_meter(df)
    if m is None:
        return None
    t0, t1 = it["_conn"], it["_disc"]
    grid = grid_for(t0, t1, bw, offset)
    if len(grid) < 2:
        return None
    e0, e1 = interp_val(m, t0), interp_val(m, t1)
    total = e1 - e0
    if total <= 0:
        return None
    if edge_mode == "boundary":
        gs = grid.values.astype("datetime64[ns]").astype("int64") / 1e9
        t0s, t1s = t0.value / 1e9, t1.value / 1e9
        lo = np.maximum(gs[:-1], t0s)
        hi = np.minimum(gs[1:], t1s)
        prof_vals = np.interp(hi, m.index.values.astype("int64")/1e9, m.values) - \
                    np.interp(lo, m.index.values.astype("int64")/1e9, m.values)
        prof_vals[hi <= lo] = 0.0
        prof = pd.Series(prof_vals, index=grid[:-1])
    elif edge_mode == "rescale":
        mg = np.interp(grid.values.astype("int64"), m.index.values.astype("int64"), m.values)
        raw = np.diff(mg)
        s = raw.sum()
        if s <= 0:
            return None
        prof = pd.Series(raw * total / s, index=grid[:-1])
    else:
        raise ValueError(edge_mode)
    return {"profile": prof, "total": total, "series": m}


def power_parts(df, it, bw=15, max_gap=np.inf, offset=0):
    """功率分段线性积分。仅连接不超过 max_gap 的相邻有效采样点。"""
    t0, t1 = it["_conn"], it["_disc"]
    d = df.loc[(df.index >= t0) & (df.index <= t1)]
    p = d["Power (kW)"].astype(float)
    p = p[~p.index.duplicated(keep="last")]
    if p.notna().sum() < 2:
        return None
    grid = grid_for(t0, t1, bw, offset)
    if len(grid) < 2:
        return None
    ns = p.index.values.astype("datetime64[ns]").astype("int64") / 1e9
    pv = p.values
    valid = ~np.isnan(pv)
    adj = np.where(valid[:-1] & valid[1:])[0]
    if len(adj) == 0:
        return None
    all_dt = ns[adj + 1] - ns[adj]
    gap_stats = {
        "n_long_gap60": int((all_dt > 60).sum()),
        "max_gap_sec": float(all_dt.max()) if len(all_dt) else np.nan,
        "long_gap60_seconds": float(all_dt[all_dt > 60].sum()),
    }
    session_sec_preview = (t1 - t0).total_seconds()
    gap_stats["coverage_unbridged"] = float(all_dt.sum()/session_sec_preview) if session_sec_preview > 0 else np.nan
    keep = all_dt <= max_gap
    idx = adj[keep]
    if len(idx) == 0:
        return None
    ta, tb = ns[idx], ns[idx + 1]
    pa, pb = pv[idx], pv[idx + 1]
    dt = tb - ta
    inwin = (tb > t0.value / 1e9) & (ta < t1.value / 1e9) & (dt > 0)
    ta, tb, pa, pb, dt = ta[inwin], tb[inwin], pa[inwin], pb[inwin], dt[inwin]
    if len(dt) == 0:
        return None
    session_sec = (t1 - t0).total_seconds()
    coverage = float(dt.sum() / session_sec) if session_sec > 0 else 0.0
    total = float((0.5 * (pa + pb) * dt / 3600.0).sum())
    grid_s = grid.values.astype("datetime64[ns]").astype("int64") / 1e9
    ia = np.clip(np.searchsorted(grid_s, ta, side="right") - 1, 0, len(grid) - 2)
    ib = np.clip(np.searchsorted(grid_s, tb, side="right") - 1, 0, len(grid) - 2)
    out = np.zeros(len(grid) - 1)
    slope = (pb - pa) / dt

    same = ia == ib
    t0s, t1s = t0.value / 1e9, t1.value / 1e9
    # 同片区间向量化分配
    js = np.where(same)[0]
    if len(js):
        lo = np.maximum(np.maximum(ta[js], grid_s[ia[js]]), t0s)
        hi = np.minimum(np.minimum(tb[js], grid_s[ia[js]+1]), t1s)
        good = hi > lo
        jj = js[good]
        e = (pa[jj]*(hi[good]-lo[good]) + slope[jj]*((hi[good]-ta[jj])**2-(lo[good]-ta[jj])**2)/2)/3600.0
        out += np.bincount(ia[jj], weights=e, minlength=len(out))
    # 跨片区间展开后向量化分配
    jc = np.where(~same)[0]
    if len(jc):
        counts = ib[jc] - ia[jc] + 1
        seg_idx = np.repeat(jc, counts)
        bin_idx = np.concatenate([np.arange(ia[j], ib[j]+1) for j in jc])
        lo = np.maximum(np.maximum(ta[seg_idx], grid_s[bin_idx]), t0s)
        hi = np.minimum(np.minimum(tb[seg_idx], grid_s[bin_idx+1]), t1s)
        good = hi > lo
        jj = seg_idx[good]; kk = bin_idx[good]
        e = (pa[jj]*(hi[good]-lo[good]) + slope[jj]*((hi[good]-ta[jj])**2-(lo[good]-ta[jj])**2)/2)/3600.0
        out += np.bincount(kk, weights=e, minlength=len(out))
    prof = pd.Series(out, index=grid[:-1])
    gap_stats["long_gap60_share"] = gap_stats["long_gap60_seconds"] / session_sec if session_sec > 0 else np.nan
    return {"profile": prof, "total": total, "coverage": coverage, **gap_stats}


def power_integral_between(p, start, end, max_gap=60):
    """在给定时间区间内，对相邻有效点做裁剪后的分段线性积分。"""
    if pd.isna(start) or pd.isna(end) or end <= start:
        return 0.0
    p = p.dropna()
    p = p[~p.index.duplicated(keep="last")]
    if len(p) < 2:
        return 0.0
    ns = p.index.values.astype("datetime64[ns]").astype("int64") / 1e9
    pv = p.values
    idx = np.where(~np.isnan(pv[:-1]) & ~np.isnan(pv[1:]))[0]
    if len(idx) == 0:
        return 0.0
    ta, tb = ns[idx], ns[idx + 1]
    pa, pb = pv[idx], pv[idx + 1]
    dt = tb - ta
    keep = (dt > 0) & (dt <= max_gap) & (tb > start.value / 1e9) & (ta < end.value / 1e9)
    ta, tb, pa, pb, dt = ta[keep], tb[keep], pa[keep], pb[keep], dt[keep]
    if len(dt) == 0:
        return 0.0
    lo = np.maximum(ta, start.value / 1e9)
    hi = np.minimum(tb, end.value / 1e9)
    slope = (pb - pa) / dt
    e = pa * (hi - lo) + slope * ((hi - ta) ** 2 - (lo - ta) ** 2) / 2
    return float((e[e > 0] / 3600.0).sum()) if np.any(e > 0) else 0.0


def uniform_profile(it, end_time, bw=15, offset=0):
    if pd.isna(end_time) or end_time <= it["_conn"]:
        return None
    grid = grid_for(it["_conn"], end_time, bw, offset)
    if len(grid) < 2:
        return None
    return pd.Series(float(it["kWhDelivered"]) / (len(grid) - 1), index=grid[:-1])


def after_done_overlap_seconds(end_time, done, grid, bw):
    if pd.isna(done) or done < grid[0] or done > end_time:
        return np.nan
    total = 0.0
    for a, b in zip(grid[:-1], grid[1:]):
        lo, hi = max(done, a), min(end_time, b)
        if hi > lo:
            total += (hi - lo).total_seconds()
    return total / (bw * 60.0)


def tvd(p, q):
    p = p / p.sum()
    q = q / q.sum()
    a = pd.concat([p, q], axis=1).fillna(0).values
    return 0.5 * np.abs(a[:, 0] - a[:, 1]).sum()


def infer_step(index):
    diffs = pd.Series(index).diff().dropna()
    return diffs.median() if len(diffs) else MIN15


def series_metrics(m, u, c):
    step = infer_step(m.index)
    grid = pd.date_range(m.index.min(), m.index.max() + step, freq=step)[:-1]
    m, u, c = m.reindex(grid).fillna(0), u.reindex(grid).fillna(0), c.reindex(grid).fillna(0)
    d_mae, d_cut = m - u, m - c
    return {
        "E_meas": float(m.sum()), "mae_uniform": float(d_mae.abs().mean()),
        "mae_cut": float(d_cut.abs().mean()),
        "rmse_uniform": float(np.sqrt((d_mae ** 2).mean())),
        "corr_uniform": float(np.corrcoef(m.values, u.values)[0, 1]) if m.std() > 0 and u.std() > 0 else np.nan,
        "zero_meas": float((m <= 1e-12).mean()),
        "zero_uniform": float((u <= 1e-12).mean()),
        "zero_cut": float((c <= 1e-12).mean()),
        "tvd_uniform": tvd(u.clip(lower=0), m.clip(lower=0)),
        "tvd_cut": tvd(c.clip(lower=0), m.clip(lower=0)),
    }


def new_store():
    return {"m": defaultdict(pd.Series), "u": defaultdict(pd.Series),
            "c": defaultdict(pd.Series), "n": Counter()}


def add_store(store, st, m, u, c):
    store["m"][st] = store["m"][st].add(m, fill_value=0)
    store["u"][st] = store["u"][st].add(u, fill_value=0)
    store["c"][st] = store["c"][st].add(c, fill_value=0)
    store["n"][st] += 1


def combined_profile(d, stations=None):
    if stations is not None:
        d = {k: v for k, v in d.items() if k in stations}
    if not d:
        return pd.Series(dtype=float)
    out = pd.Series(dtype=float)
    for v in d.values():
        out = out.add(v, fill_value=0)
    return out.sort_index()


def node_stats_from_store(store, stations=None):
    if stations is None:
        stations = sorted(store["m"])
    rows = []
    for st in stations:
        if st not in store["m"]:
            continue
        r = {"stationID": st, "n": store["n"][st]}
        r.update(series_metrics(store["m"][st], store["u"][st], store["c"][st]))
        rows.append(r)
    return pd.DataFrame(rows)


def site_metrics(store, stations=None):
    m = combined_profile(store["m"], stations)
    u = combined_profile(store["u"], stations)
    c = combined_profile(store["c"], stations)
    if m.empty:
        return None, None, None, None
    # 共用当前分辨率的规则网格，避免不同节点首末片造成错位。
    step = infer_step(m.index)
    grid = pd.date_range(m.index.min(), m.index.max() + step, freq=step)[:-1]
    m, u, c = m.reindex(grid).fillna(0), u.reindex(grid).fillna(0), c.reindex(grid).fillna(0)
    met = series_metrics(m, u, c)
    # 日峰值及峰值时刻误差
    day = m.index.floor("D")
    dm, du, dc = m.groupby(day).max(), u.groupby(day).max(), c.groupby(day).max()
    common = dm.index.intersection(du.index).intersection(dc.index)
    dm, du, dc = dm.loc[common], du.loc[common], dc.loc[common]
    im = m.loc[m.index.floor("D").isin(common)].groupby(lambda x: x.floor("D")).idxmax()
    iu = u.loc[u.index.floor("D").isin(common)].groupby(lambda x: x.floor("D")).idxmax()
    ic = c.loc[c.index.floor("D").isin(common)].groupby(lambda x: x.floor("D")).idxmax()
    peak_mae_u = float((dm - du).abs().mean())
    peak_mae_c = float((dm - dc).abs().mean())
    peak_time_u = float((im.loc[common] - iu.loc[common]).abs().dt.total_seconds().div(60).mean())
    peak_time_c = float((im.loc[common] - ic.loc[common]).abs().dt.total_seconds().div(60).mean())
    ramp_mae_u = float((m.diff().dropna() - u.diff().dropna()).abs().mean())
    ramp_mae_c = float((m.diff().dropna() - c.diff().dropna()).abs().mean())
    met.update({"peak_mae_uniform": peak_mae_u, "peak_mae_cut": peak_mae_c,
                "peak_time_err_uniform_min": peak_time_u, "peak_time_err_cut_min": peak_time_c,
                "ramp_mae_uniform": ramp_mae_u, "ramp_mae_cut": ramp_mae_c,
                "daily_peak_corr_uniform": float(np.corrcoef(dm.values, du.values)[0, 1]),
                "daily_peak_corr_cut": float(np.corrcoef(dm.values, dc.values)[0, 1])})
    return m, u, c, met


def smd(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    x, y = x[~np.isnan(x)], y[~np.isnan(y)]
    if len(x) < 2 or len(y) < 2:
        return np.nan
    sp = math.sqrt(((len(x)-1)*x.var(ddof=1) + (len(y)-1)*y.var(ddof=1)) / (len(x)+len(y)-2))
    return float((x.mean()-y.mean())/sp) if sp > 0 else np.nan


def cramers_v(table):
    table = np.asarray(table, float)
    if table.ndim != 2 or table.shape[0] < 2 or table.shape[1] < 2:
        return np.nan
    n = table.sum()
    if n <= 0:
        return np.nan
    chi2 = 0.0
    rows = table.sum(axis=1, keepdims=True)
    cols = table.sum(axis=0, keepdims=True)
    exp = rows * cols / n
    chi2 = float(((table-exp)**2/np.maximum(exp, 1e-12)).sum())
    r, k = table.shape
    return math.sqrt(chi2 / (n * (min(r, k)-1)))


def holm(pvals):
    p = np.asarray(pvals, float)
    order = np.argsort(p)
    out = np.empty_like(p)
    running = 0.0
    m = len(p)
    for rank, idx in enumerate(order):
        val = (m-rank)*p[idx]
        running = max(running, val)
        out[idx] = min(1.0, running)
    return out


def boot_paired_median(x, y, B=10000, seed=20261109):
    rng = np.random.default_rng(seed)
    x, y = np.asarray(x, float), np.asarray(y, float)
    good = ~(np.isnan(x) | np.isnan(y))
    x, y = x[good], y[good]
    n = len(x)
    diffs = []
    for _ in range(B // 1000):
        idx = rng.integers(0, n, (1000, n))
        diffs.append(np.median(x[idx], axis=1) - np.median(y[idx], axis=1))
    d = np.concatenate(diffs)
    p = min(1.0, 2.0 * min(float((d <= 0).mean()), float((d >= 0).mean())))
    return {"n": n, "median_x": float(np.median(x)), "median_y": float(np.median(y)),
            "median_diff": float(np.median(x)-np.median(y)),
            "ci_low": float(np.percentile(d, 2.5)), "ci_high": float(np.percentile(d, 97.5)),
            "p_boot": p}


def boot_paired_mean(x, y, B=10000, seed=20261109):
    rng = np.random.default_rng(seed)
    x, y = np.asarray(x, float), np.asarray(y, float)
    good = ~(np.isnan(x) | np.isnan(y))
    x, y = x[good], y[good]
    n = len(x)
    diffs = []
    for _ in range(B // 1000):
        idx = rng.integers(0, n, (1000, n))
        diffs.append(np.mean(x[idx], axis=1) - np.mean(y[idx], axis=1))
    d = np.concatenate(diffs)
    p = min(1.0, 2.0 * min(float((d <= 0).mean()), float((d >= 0).mean())))
    return {"n": n, "mean_x": float(np.mean(x)), "mean_y": float(np.mean(y)),
            "mean_diff": float(np.mean(x)-np.mean(y)),
            "ci_low": float(np.percentile(d, 2.5)), "ci_high": float(np.percentile(d, 97.5)),
            "p_boot": p}


def signflip_paired_p(x, y, B=20000, seed=20261109):
    rng = np.random.default_rng(seed)
    d = np.asarray(x, float)-np.asarray(y, float)
    d = d[~np.isnan(d)]
    obs = d.mean()
    signs = rng.choice([-1.0, 1.0], size=(B, len(d)))
    sim = (d*signs).mean(axis=1)
    return min(1.0, 2.0*min(float((sim <= 0).mean()), float((sim >= 0).mean())))


def site_day_bootstrap(m, u, c, B=2000, seed=20261109):
    rng = np.random.default_rng(seed)
    day_values = m.index.floor("D").values
    days = np.array(sorted(pd.unique(day_values)))
    blocks = {d: (m[day_values == d], u[day_values == d], c[day_values == d]) for d in days}
    diffs = np.empty(B)
    for b in range(B):
        take = rng.choice(days, size=len(days), replace=True)
        mb, ub, cb = zip(*(blocks[d] for d in take))
        mi, ui, ci = pd.concat(mb), pd.concat(ub), pd.concat(cb)
        diffs[b] = (mi-ui.reindex(mi.index).fillna(0)).abs().mean() - (mi-ci.reindex(mi.index).fillna(0)).abs().mean()
    obs = (m-u.reindex(m.index).fillna(0)).abs().mean() - (m-c.reindex(m.index).fillna(0)).abs().mean()
    p = min(1.0, 2.0*min(float((diffs <= 0).mean()), float((diffs >= 0).mean())))
    return {"mean_diff": float(obs), "ci_low": float(np.percentile(diffs, 2.5)),
            "ci_high": float(np.percentile(diffs, 97.5)), "p_boot": p}


def main():
    import statsmodels.formula.api as smf
    from anchor_analysis import load_items
    items = load_items(SRC)
    # 严格有效完成时刻：正交付电量不能落入零时长区间。
    for it in items:
        done = it["_done"]
        it["_valid_done_strict"] = (not pd.isna(done)) and (it["_conn"] < done <= it["_disc"])
        it["_cut_old"] = it["_cut"]  # 旧规则允许 完成=接入
        it["_cut_strict"] = done if it["_valid_done_strict"] else it["_disc"]

    station_to_space = {}
    rows = []
    failed = []

    # 主存储
    A_all = new_store()
    A_all_old = new_store()
    A_all_strict = new_store()
    ref_power = new_store()  # 60s 缺口、15min、覆盖率>=0.95
    ref_power_valid_done = new_store()
    ref_power_fallback = new_store()
    gap_stores = {g: new_store() for g in GAPS}
    cov_stores = {ct: new_store() for ct in COV_THRESHOLDS}
    origin_stores = {o: new_store() for o in OFFSETS}
    edge_stores = {e: new_store() for e in ["boundary", "rescale"]}
    scale_stores = {r: new_store() for r in RESOLUTIONS}

    ref_power_session = {}  # 保存 coverage>=0.90 的 15min 功率，供覆盖率敏感性使用
    gap_energy = {g: [] for g in GAPS}
    ref_power_energy = []

    for k, it in enumerate(items, 1):
        st = it["stationID"]
        station_to_space[st] = it.get("spaceID", "")
        row = {"sessionID": it["sessionID"], "stationID": st, "spaceID": it.get("spaceID", ""),
               "kWh": it["kWhDelivered"], "ok": False,
               "conn": it["_conn"], "disc": it["_disc"], "done": it["_done"],
               "valid_done_strict": it["_valid_done_strict"], "cut_fallback": not it["_valid_done_strict"],
               "dur_min": (it["_disc"]-it["_conn"]).total_seconds()/60,
               "start_hour": it["_conn"].hour + it["_conn"].minute/60,
               "month": it["_conn"].strftime("%Y-%m"), "week": it["_conn"].strftime("%G-W%V"),
               "weekday": it["_conn"].strftime("%A"), "is_weekend": int(it["_conn"].dayofweek >= 5)}
        f = os.path.join(RAW, fname_for(it))
        if not os.path.exists(f) or os.path.getsize(f) == 0:
            failed.append({"sessionID": it["sessionID"], "reason": "missing_or_empty"})
            rows.append(row)
            continue
        try:
            df = read_session(RAW, it)
        except Exception:
            df = None
        if df is None:
            failed.append({"sessionID": it["sessionID"], "reason": "read_error"})
            rows.append(row)
            continue

        m15 = meter_parts(df, it, 15, 0, "boundary")
        if m15 is None:
            failed.append({"sessionID": it["sessionID"], "reason": "meter_unusable"})
            rows.append(row)
            continue
        u15 = uniform_profile(it, it["_disc"], 15)
        c15_old = uniform_profile(it, it["_cut_old"], 15)
        c15_strict = uniform_profile(it, it["_cut_strict"], 15)
        # 旧规则允许“完成=接入”，但这会使正交付电量落入零时长区间；
        # 正式分析保留该会话，完成时刻按无效处理，代理终点回退断开时刻。
        c15_old_store = c15_old if c15_old is not None else c15_strict
        if u15 is None or c15_strict is None:
            failed.append({"sessionID": it["sessionID"], "reason": "invalid_time_bounds"})
            rows.append(row)
            continue

        row["ok"] = True
        row["e_meter"] = m15["total"]
        row["rel_err_meter"] = (m15["total"]-it["kWhDelivered"])/it["kWhDelivered"]
        row["tvd_uniform"] = tvd(u15.clip(lower=0), m15["profile"].clip(lower=0))
        row["tvd_cut_old"] = tvd(c15_old.clip(lower=0), m15["profile"].clip(lower=0)) if c15_old is not None else np.nan
        row["tvd_cut_strict"] = tvd(c15_strict.clip(lower=0), m15["profile"].clip(lower=0))
        row["mae_uniform_session"] = float((m15["profile"].reindex(u15.index).fillna(0)-u15).abs().mean())
        row["mae_cut_strict_session"] = float((m15["profile"].reindex(c15_strict.index).fillna(0)-c15_strict).abs().mean())
        add_store(A_all, st, m15["profile"], u15, c15_strict)
        add_store(A_all_old, st, m15["profile"], u15, c15_old_store)
        add_store(A_all_strict, st, m15["profile"], u15, c15_strict)

        # 精确的完成后电量：累计电量按插值端点切分
        if it["_valid_done_strict"]:
            ms = m15["series"]
            e_conn, e_done, e_disc = interp_val(ms, it["_conn"]), interp_val(ms, it["_done"]), interp_val(ms, it["_disc"])
            denom = e_disc-e_conn
            row["idle_ratio"] = (it["_disc"]-it["_done"]).total_seconds()/(it["_disc"]-it["_conn"]).total_seconds()
            row["charge_ratio"] = (it["_done"]-it["_conn"]).total_seconds()/(it["_disc"]-it["_conn"]).total_seconds()
            row["share_after_done_meter_exact"] = (e_disc-e_done)/denom if denom > 0 else np.nan
            nbin = len(u15)
            row["share_after_done_uniform_exact"] = after_done_overlap_seconds(it["_disc"], it["_done"], u15.index.union(u15.index[-1:]+pd.Timedelta(minutes=15)), 15)/nbin if nbin else np.nan

        # 参考功率及 60s 长缺口
        pr = power_parts(df, it, 15, 60, 0)
        if pr is not None:
            row.update({x: pr[x] for x in ["n_long_gap60", "max_gap_sec", "long_gap60_seconds", "long_gap60_share", "coverage_unbridged"]})
            row["e_power"] = pr["total"]
            row["power_coverage"] = pr["coverage"]
            row["rel_err_power"] = (pr["total"]-it["kWhDelivered"])/it["kWhDelivered"]
            row["power_subset"] = pr["coverage"] >= MIN_COV
            row["power_subset_unbridged"] = pr["coverage_unbridged"] >= MIN_COV
            if pr["coverage"] >= MIN_COV:
                add_store(ref_power, st, pr["profile"], u15, c15_strict)
                add_store(ref_power_valid_done if it["_valid_done_strict"] else ref_power_fallback,
                          st, pr["profile"], u15, c15_strict)
                # 完成时刻由功率积分精确切分；不桥接对照按自身覆盖率独立判定
                if it["_valid_done_strict"]:
                    p = df["Power (kW)"].astype(float)
                    e_after = power_integral_between(p, it["_done"], it["_disc"], 60)
                    row["share_after_done_power_exact"] = e_after/pr["total"] if pr["total"] > 0 else np.nan
                ref_power_energy.append({"kWh": it["kWhDelivered"], "e_power": pr["total"], "coverage": pr["coverage"]})
            if it["_valid_done_strict"] and pr["coverage_unbridged"] >= MIN_COV:
                p = df["Power (kW)"].astype(float)
                e_total_unbridged = power_integral_between(p, it["_conn"], it["_disc"], np.inf)
                e_after_unbridged = power_integral_between(p, it["_done"], it["_disc"], np.inf)
                row["power_subset_unbridged"] = True
                row["share_after_done_power_exact_unbridged"] = \
                    e_after_unbridged/e_total_unbridged if e_total_unbridged > 0 else np.nan
            if pr["coverage"] >= 0.90:
                ref_power_session[it["sessionID"]] = (st, pr["profile"], u15, c15_strict)
                if pr["coverage"] >= 0.90:
                    add_store(cov_stores[0.90], st, pr["profile"], u15, c15_strict)
                if pr["coverage"] >= 0.95:
                    add_store(cov_stores[0.95], st, pr["profile"], u15, c15_strict)
                if pr["coverage"] >= 0.99:
                    add_store(cov_stores[0.99], st, pr["profile"], u15, c15_strict)
        else:
            row.update({"e_power": np.nan, "power_coverage": 0.0, "n_long_gap60": np.nan,
                        "max_gap_sec": np.nan, "long_gap60_seconds": np.nan, "long_gap60_share": np.nan,
                        "coverage_unbridged": np.nan, "rel_err_power": np.nan, "power_subset": False,
                        "share_after_done_power_exact": np.nan, "power_subset_unbridged": False,
                        "share_after_done_power_exact_unbridged": np.nan})

        # 最大缺口敏感性
        for g in GAPS:
            if g == 60:
                pg = pr
            else:
                pg = power_parts(df, it, 15, g, 0)
            if pg is None:
                continue
            gap_energy[g].append({"kWh": it["kWhDelivered"], "e_power": pg["total"], "coverage": pg["coverage"]})
            if pg["coverage"] >= MIN_COV:
                add_store(gap_stores[g], st, pg["profile"], u15, c15_strict)

        # 分箱相位与累计电量端点处理
        for off in OFFSETS:
            mo = meter_parts(df, it, 15, off, "boundary")
            po = power_parts(df, it, 15, 60, off)
            uo = uniform_profile(it, it["_disc"], 15, off)
            co = uniform_profile(it, it["_cut_strict"], 15, off)
            if all(v is not None for v in (mo, po, uo, co)) and po["coverage"] >= MIN_COV:
                add_store(origin_stores[off], st, mo["profile"], uo, co)
        for edge in ["boundary", "rescale"]:
            me = meter_parts(df, it, 15, 0, edge)
            if me is not None and pr is not None and pr["coverage"] >= MIN_COV:
                add_store(edge_stores[edge], st, me["profile"], u15, c15_strict)

        # 15/30/60min 多尺度
        for res in RESOLUTIONS:
            mr = meter_parts(df, it, res, 0, "boundary")
            prr = power_parts(df, it, res, 60, 0)
            ur = uniform_profile(it, it["_disc"], res, 0)
            cr = uniform_profile(it, it["_cut_strict"], res, 0)
            if all(v is not None for v in (mr, prr, ur, cr)) and prr["coverage"] >= MIN_COV:
                add_store(scale_stores[res], st, mr["profile"], ur, cr)

        rows.append(row)
        if k % 500 == 0:
            print("processed", k, "/", len(items), flush=True)

    sess = pd.DataFrame(rows)
    sess.to_csv(os.path.join(OUT, "extended_sessions.csv"), index=False)
    # 保存主扫描检查点，供后处理阶段排错或复用，避免重复解压 2,341 个时序文件。
    with open(os.path.join(OUT, "extended_stores.pkl"), "wb") as f:
        pickle.dump({"station_to_space": station_to_space, "A_all_strict": A_all_strict,
                     "A_all_old": A_all_old, "ref_power": ref_power,
                     "ref_power_valid_done": ref_power_valid_done, "ref_power_fallback": ref_power_fallback,
                     "gap_stores": gap_stores, "cov_stores": cov_stores,
                     "origin_stores": origin_stores, "edge_stores": edge_stores,
                     "scale_stores": scale_stores}, f, protocol=pickle.HIGHEST_PROTOCOL)
    pd.DataFrame(failed).to_csv(os.path.join(OUT, "extended_failures.csv"), index=False)

    # --- 敏感性：最大缺口 ---
    gap_rows = []
    for g in GAPS:
        arr = pd.DataFrame(gap_energy[g])
        sub = arr[arr.coverage >= MIN_COV]
        nd = node_stats_from_store(gap_stores[g])
        gap_rows.append({"factor": "max_gap_seconds", "value": g, "n_integrated": len(arr),
                         "n_subset": len(sub), "median_rel_err": float(sub.assign(e=sub.e_power/sub.kWh-1)["e"].median()) if len(sub) else np.nan,
                         "within5_pct": float((abs(sub.e_power/sub.kWh-1) <= .05).mean()) if len(sub) else np.nan,
                         "node_mae_uniform": float(nd.mae_uniform.mean()), "node_mae_cut": float(nd.mae_cut.mean()),
                         "mae_reduction_pct": 100*(1-nd.mae_cut.mean()/nd.mae_uniform.mean())})
    pd.DataFrame(gap_rows).to_csv(os.path.join(OUT, "sensitivity_max_gap.csv"), index=False)

    # --- 敏感性：覆盖率门槛 ---
    cov_rows = []
    for ct in COV_THRESHOLDS:
        nd = node_stats_from_store(cov_stores[ct])
        cov_rows.append({"factor": "coverage_threshold", "value": ct, "n_subset": int(nd.n.sum()),
                         "node_mae_uniform": float(nd.mae_uniform.mean()), "node_mae_cut": float(nd.mae_cut.mean()),
                         "mae_reduction_pct": 100*(1-nd.mae_cut.mean()/nd.mae_uniform.mean())})
    pd.DataFrame(cov_rows).to_csv(os.path.join(OUT, "sensitivity_coverage.csv"), index=False)

    # --- 敏感性：完成时刻规则与零时长会话 ---
    done_rows = []
    for name, store in [("A_all_old_rule", A_all_old), ("A_all_strict_rule", A_all_strict)]:
        nd = node_stats_from_store(store)
        done_rows.append({"rule": name, "n_sessions": int(nd.n.sum()), "node_mae_uniform": float(nd.mae_uniform.mean()),
                          "node_mae_cut": float(nd.mae_cut.mean()), "mae_reduction_pct": 100*(1-nd.mae_cut.mean()/nd.mae_uniform.mean())})
    for name, store in [("B_high_all", ref_power), ("B_high_valid_done", ref_power_valid_done),
                        ("B_high_fallback", ref_power_fallback)]:
        nd = node_stats_from_store(store)
        done_rows.append({"rule": name, "n_sessions": int(nd.n.sum()), "node_mae_uniform": float(nd.mae_uniform.mean()),
                          "node_mae_cut": float(nd.mae_cut.mean()), "mae_reduction_pct": 100*(1-nd.mae_cut.mean()/nd.mae_uniform.mean())})
    pd.DataFrame(done_rows).to_csv(os.path.join(OUT, "sensitivity_done_rule.csv"), index=False)

    # --- 敏感性：分箱相位 ---
    origin_rows = []
    for off, store in origin_stores.items():
        nd = node_stats_from_store(store)
        origin_rows.append({"factor": "bin_offset_minutes", "value": off, "n_sessions": int(nd.n.sum()),
                            "node_mae_uniform": float(nd.mae_uniform.mean()), "node_mae_cut": float(nd.mae_cut.mean()),
                            "mae_reduction_pct": 100*(1-nd.mae_cut.mean()/nd.mae_uniform.mean())})
    pd.DataFrame(origin_rows).to_csv(os.path.join(OUT, "sensitivity_bin_offset.csv"), index=False)

    # --- 敏感性：累计电量端点处理 ---
    edge_rows = []
    for edge, store in edge_stores.items():
        nd = node_stats_from_store(store)
        edge_rows.append({"factor": "meter_edge_mode", "value": edge, "n_sessions": int(nd.n.sum()),
                          "node_mae_uniform": float(nd.mae_uniform.mean()), "node_mae_cut": float(nd.mae_cut.mean()),
                          "mae_reduction_pct": 100*(1-nd.mae_cut.mean()/nd.mae_uniform.mean())})
    pd.DataFrame(edge_rows).to_csv(os.path.join(OUT, "sensitivity_meter_edge.csv"), index=False)

    # --- 高覆盖子集代表性 ---
    ok = sess[sess.ok == True].copy()
    for col in ["conn", "disc", "done"]:
        ok[col] = pd.to_datetime(ok[col], utc=True, errors="coerce")
    ok["valid_done_strict"] = ok.valid_done_strict.astype(str).str.lower().isin(["true", "1"])
    ok["power_subset"] = ok.power_subset.astype(str).str.lower().isin(["true", "1"])
    ok["power_subset_unbridged"] = ok.power_subset_unbridged.astype(str).str.lower().isin(["true", "1"])
    high = ok[ok.power_subset]
    low = ok[~ok.power_subset]
    rep_rows = []
    rep_vars = [("kWh", "交付电量"), ("dur_min", "接入时长"), ("start_hour", "接入小时"),
                ("idle_ratio", "完成后占桩比"), ("charge_ratio", "充电时长占比"),
                ("tvd_uniform", "均分TVD"), ("tvd_cut_strict", "截断TVD"),
                ("mae_uniform_session", "会话均分MAE"), ("mae_cut_strict_session", "会话截断MAE"),
                ("rel_err_meter", "电表总量相对误差"), ("long_gap60_share", "长缺口时长占比")]
    from scipy.stats import ks_2samp, chi2_contingency
    for col, label in rep_vars:
        x, y = high[col], low[col]
        stat, p = ks_2samp(x.dropna(), y.dropna())
        rep_rows.append({"variable": col, "label": label, "high_n": int(x.notna().sum()), "low_n": int(y.notna().sum()),
                         "high_mean": float(x.mean()), "low_mean": float(y.mean()),
                         "high_median": float(x.median()), "low_median": float(y.median()),
                         "smd": smd(x, y), "ks_stat": float(stat), "ks_p": float(p)})
    rep = pd.DataFrame(rep_rows)
    rep["holm_p"] = holm(rep.ks_p)
    rep.to_csv(os.path.join(OUT, "representativeness_numeric.csv"), index=False)

    cat_rows = []
    for col in ["month", "weekday", "spaceID", "cut_fallback", "valid_done_strict"]:
        tab = pd.crosstab(ok[col], ok.power_subset)
        chi2, p, _, _ = chi2_contingency(tab)
        cat_rows.append({"variable": col, "cramers_v": cramers_v(tab.values), "chi2_p": float(p),
                         "n_levels": len(tab)})
    catrep = pd.DataFrame(cat_rows)
    catrep["holm_p"] = holm(catrep.chi2_p)
    catrep.to_csv(os.path.join(OUT, "representativeness_categorical.csv"), index=False)

    # 倾向得分与共同支持：只用会话元数据，避免声称解决不可观测选择。
    from sklearn.compose import ColumnTransformer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler
    fit = ok.dropna(subset=["kWh", "dur_min", "start_hour", "month", "weekday", "spaceID"]).copy()
    fit["high_mask"] = fit["power_subset"].eq(True).astype(bool)
    X = fit[["kWh", "dur_min", "start_hour", "month", "weekday", "spaceID"]]
    y = fit.power_subset.astype(int).values
    pre = ColumnTransformer([("num", StandardScaler(), ["kWh", "dur_min", "start_hour"]),
                             ("cat", OneHotEncoder(handle_unknown="ignore"), ["month", "weekday", "spaceID"])])
    clf = Pipeline([("pre", pre), ("lr", LogisticRegression(max_iter=2000, C=1.0))])
    clf.fit(X, y)
    ps = clf.predict_proba(X)[:, 1]
    fit["propensity"] = ps
    fit["iptw"] = np.where(fit["high_mask"], 1.0/np.clip(ps, .01, .99), 1.0/np.clip(1-ps, .01, .99))
    fit.to_csv(os.path.join(OUT, "propensity_scores.csv"), index=False)
    qs = np.linspace(0, 1, 21)
    psrow = {"quantile": qs,
             "high": np.quantile(fit.loc[fit["high_mask"], "propensity"], qs),
             "non_high": np.quantile(fit.loc[~fit["high_mask"], "propensity"], qs)}
    pd.DataFrame(psrow).to_csv(os.path.join(OUT, "propensity_quantiles.csv"), index=False)

    # 加权后的连续变量 SMD 仅用于平衡诊断
    wrows = []
    for col, label in rep_vars:
        xh, xl = fit.loc[fit["high_mask"], col].dropna(), fit.loc[~fit["high_mask"], col].dropna()
        wh, wl = fit.loc[fit["high_mask"], "iptw"].loc[xh.index], fit.loc[~fit["high_mask"], "iptw"].loc[xl.index]
        mh = np.average(xh, weights=wh); ml = np.average(xl, weights=wl)
        vh = np.average((xh-mh)**2, weights=wh); vl = np.average((xl-ml)**2, weights=wl)
        pooled = math.sqrt((vh+vl)/2)
        wrows.append({"variable": col, "label": label, "smd_unweighted": smd(xh, xl),
                      "smd_weighted": (mh-ml)/pooled if pooled > 0 else np.nan,
                      "weighted_high_mean": mh, "weighted_low_mean": ml})
    pd.DataFrame(wrows).to_csv(os.path.join(OUT, "representativeness_weighted_smd.csv"), index=False)

    # --- 机制分解 ---
    mech = ok[ok.valid_done_strict].copy()
    mech["tvd_reduction"] = mech.tvd_uniform - mech.tvd_cut_strict
    mech["mae_reduction"] = mech.mae_uniform_session - mech.mae_cut_strict_session
    edges = [0.0, 0.1, 0.3, 0.6, 1.0]
    labels = ["[0,0.1)", "[0.1,0.3)", "[0.3,0.6)", "[0.6,1.0]"]
    strata = []
    for i, lab in enumerate(labels):
        if i < 3:
            part = mech[(mech.idle_ratio >= edges[i]) & (mech.idle_ratio < edges[i+1])]
        else:
            part = mech[(mech.idle_ratio >= edges[i]) & (mech.idle_ratio <= edges[i+1])]
        if part.empty:
            continue
        strata.append({"stratum": lab, "n": len(part), "idle_median": part.idle_ratio.median(),
                       "tvd_uniform_median": part.tvd_uniform.median(), "tvd_cut_median": part.tvd_cut_strict.median(),
                       "tvd_reduction_median": part.tvd_reduction.median(),
                       "mae_reduction_median": part.mae_reduction.median(),
                       "uniform_after_done_weighted": float((part.share_after_done_uniform_exact*part.kWh).sum()/part.kWh.sum()),
                       "meter_after_done_weighted": float((part.share_after_done_meter_exact*part.kWh).sum()/part.kWh.sum())})
    pd.DataFrame(strata).to_csv(os.path.join(OUT, "mechanism_idle_strata.csv"), index=False)

    # 解释回归：节点固定效应 + 按节点聚类稳健标准误
    regdf = mech.dropna(subset=["idle_ratio", "kWh", "dur_min", "start_hour", "long_gap60_share"]).copy()
    for col in ["kWh", "dur_min", "long_gap60_share"]:
        regdf["z_"+col] = (regdf[col]-regdf[col].mean())/regdf[col].std(ddof=0)
    regdf["idle2"] = regdf.idle_ratio ** 2
    regdf["start_sin"] = np.sin(2*np.pi*regdf.start_hour/24)
    regdf["start_cos"] = np.cos(2*np.pi*regdf.start_hour/24)
    reg_rows = []
    fallback_term = " + cut_fallback" if regdf.cut_fallback.nunique() > 1 else ""
    base_terms = ["Intercept", "idle_ratio", "idle2", "z_kWh", "z_dur_min", "start_sin", "start_cos", "z_long_gap60_share"]
    for outcome in ["tvd_uniform", "tvd_cut_strict", "tvd_reduction"]:
        model = smf.ols(f"{outcome} ~ idle_ratio + idle2 + z_kWh + z_dur_min + start_sin + start_cos + z_long_gap60_share{fallback_term} + C(stationID)", data=regdf).fit(cov_type="cluster", cov_kwds={"groups": regdf.stationID})
        terms = base_terms + (["cut_fallback"] if "cut_fallback" in model.params.index else [])
        for term in terms:
            ci = model.conf_int().loc[term]
            reg_rows.append({"outcome": outcome, "term": term, "coef": model.params[term], "se": model.bse[term],
                             "t": model.tvalues[term], "p": model.pvalues[term],
                             "ci_low": ci[0], "ci_high": ci[1], "n": int(model.nobs), "r2": model.rsquared})
    pd.DataFrame(reg_rows).to_csv(os.path.join(OUT, "mechanism_regression.csv"), index=False)

    # 精确完成后电量汇总
    share_rows = []
    for name, df_, col in [("A_meter_all_valid_done", mech, "share_after_done_meter_exact"),
                           ("A_uniform_all_valid_done", mech, "share_after_done_uniform_exact")]:
        share_rows.append({"series": name, "n": int(df_[col].notna().sum()), "median": float(df_[col].median()),
                           "weighted": float((df_[col]*df_.kWh).sum()/df_.kWh.sum())})
    hp = ok[(ok.power_subset) & (ok.valid_done_strict)].dropna(subset=["share_after_done_power_exact"])
    share_rows.append({"series": "B_power_high_valid_done_maxgap60", "n": len(hp),
                       "median": float(hp.share_after_done_power_exact.median()),
                       "weighted": float((hp.share_after_done_power_exact*hp.kWh).sum()/hp.kWh.sum())})
    hpu = ok[(ok.power_subset_unbridged) & (ok.valid_done_strict)].dropna(subset=["share_after_done_power_exact_unbridged"])
    share_rows.append({"series": "B_power_high_valid_done_unbridged", "n": len(hpu),
                       "median": float(hpu.share_after_done_power_exact_unbridged.median()),
                       "weighted": float((hpu.share_after_done_power_exact_unbridged*hpu.kWh).sum()/hpu.kWh.sum())})
    pd.DataFrame(share_rows).to_csv(os.path.join(OUT, "after_done_exact_summary.csv"), index=False)

    zero_eq = ok[(ok.done == ok.conn)]
    zero_eq.to_csv(os.path.join(OUT, "zero_duration_sessions.csv"), index=False)

    # --- 多尺度 ---
    station_main = {st for st, sp in station_to_space.items() if sp in MAIN10}
    scale_rows = []
    site_series = {}
    for res, store in scale_stores.items():
        nd_all = node_stats_from_store(store)
        nd_main = node_stats_from_store(store, sorted(station_main))
        m_all, u_all, c_all, site_all = site_metrics(store)
        m_main, u_main, c_main, site_main = site_metrics(store, station_main)
        site_series[("all52", res)] = (m_all, u_all, c_all)
        site_series[("main10", res)] = (m_main, u_main, c_main)
        for scale, nd, site, n_nodes, nsess in [
            ("52节点均值", nd_all, site_all, len(nd_all), int(nd_all.n.sum()) if len(nd_all) else 0),
            ("修正10节点均值", nd_main, site_main, len(nd_main), int(nd_main.n.sum()) if len(nd_main) else 0)]:
            if nd.empty:
                continue
            scale_rows.append({"resolution_min": res, "scale": scale, "n_nodes": n_nodes, "n_sessions": nsess,
                               "mae_uniform": float(nd.mae_uniform.mean()), "mae_cut": float(nd.mae_cut.mean()),
                               "mae_reduction_pct": 100*(1-nd.mae_cut.mean()/nd.mae_uniform.mean()),
                               "rmse_uniform": float(nd.rmse_uniform.mean()), "corr_uniform": float(nd.corr_uniform.mean()),
                               "zero_meas": float(nd.zero_meas.mean()), "zero_uniform": float(nd.zero_uniform.mean()), "zero_cut": float(nd.zero_cut.mean()),
                               "tvd_uniform": float(nd.tvd_uniform.mean()), "tvd_cut": float(nd.tvd_cut.mean()),
                               "daily_peak_mae_uniform": site["peak_mae_uniform"], "daily_peak_mae_cut": site["peak_mae_cut"],
                               "peak_time_err_uniform_min": site["peak_time_err_uniform_min"], "peak_time_err_cut_min": site["peak_time_err_cut_min"],
                               "ramp_mae_uniform": site["ramp_mae_uniform"], "ramp_mae_cut": site["ramp_mae_cut"],
                               "daily_peak_corr_uniform": site["daily_peak_corr_uniform"], "daily_peak_corr_cut": site["daily_peak_corr_cut"]})
        all_ns = int(sum(store["n"].values()))
        main_ns = int(sum(store["n"][st] for st in station_main if st in store["n"]))
        for scale, site, nsite in [("全站52节点聚合", site_all, all_ns),
                                   ("修正10节点聚合", site_main, main_ns)]:
            if site is None:
                continue
            scale_rows.append({"resolution_min": res, "scale": scale, "n_nodes": 52 if scale.startswith("全站") else 10,
                               "n_sessions": nsite,
                               "mae_uniform": site["mae_uniform"], "mae_cut": site["mae_cut"],
                               "mae_reduction_pct": 100*(1-site["mae_cut"]/site["mae_uniform"]),
                               "rmse_uniform": site["rmse_uniform"], "corr_uniform": site["corr_uniform"],
                               "zero_meas": site["zero_meas"], "zero_uniform": site["zero_uniform"], "zero_cut": site["zero_cut"],
                               "tvd_uniform": site["tvd_uniform"], "tvd_cut": site["tvd_cut"],
                               "daily_peak_mae_uniform": site["peak_mae_uniform"], "daily_peak_mae_cut": site["peak_mae_cut"],
                               "peak_time_err_uniform_min": site["peak_time_err_uniform_min"], "peak_time_err_cut_min": site["peak_time_err_cut_min"],
                               "ramp_mae_uniform": site["ramp_mae_uniform"], "ramp_mae_cut": site["ramp_mae_cut"],
                               "daily_peak_corr_uniform": site["daily_peak_corr_uniform"], "daily_peak_corr_cut": site["daily_peak_corr_cut"]})
    scale_df = pd.DataFrame(scale_rows)
    scale_df.to_csv(os.path.join(OUT, "multiscale_metrics.csv"), index=False)

    # --- 不确定性与显著性 ---
    unc_rows = []
    def add_unc(name, est, unit):
        est = dict(est)
        est.update({"analysis": name, "unit": unit})
        unc_rows.append(est)

    add_unc("会话TVD中位数：均分-截断（A，全量）", boot_paired_median(ok.tvd_uniform, ok.tvd_cut_strict, 10000, 101), "TVD")
    ndA = node_stats_from_store(A_all_strict)
    add_unc("52节点平均MAE差：均分-截断（A）", boot_paired_mean(ndA.mae_uniform, ndA.mae_cut, 10000, 102), "kWh/片")
    ndB = node_stats_from_store(ref_power)
    add_unc("52节点平均MAE差：均分-截断（B）", boot_paired_mean(ndB.mae_uniform, ndB.mae_cut, 10000, 103), "kWh/片")
    ndBmain = node_stats_from_store(ref_power, sorted(station_main))
    add_unc("修正10节点平均MAE差：均分-截断（B）", boot_paired_mean(ndBmain.mae_uniform, ndBmain.mae_cut, 10000, 104), "kWh/片")

    site_unc = {}
    for key, (m, u, c) in site_series.items():
        site_unc[key] = site_day_bootstrap(m, u, c, 2000, 200+key[1])
    add_unc("全站聚合序列MAE差（15min，日块bootstrap）", site_unc[("all52", 15)], "kWh/片")

    # 加权完成后占比的 bootstrap CI
    def boot_weighted_mean(x, w, B=10000, seed=1):
        rng = np.random.default_rng(seed)
        x, w = np.asarray(x, float), np.asarray(w, float)
        good = ~(np.isnan(x)|np.isnan(w))
        x, w = x[good], w[good]
        vals = []
        for _ in range(B//1000):
            idx = rng.integers(0, len(x), (1000, len(x)))
            vals.append((x[idx]*w[idx]).sum(axis=1)/w[idx].sum(axis=1))
        v = np.concatenate(vals)
        return {"n": len(x), "mean_x": float(np.average(x, weights=w)), "mean_y": np.nan,
                "mean_diff": np.nan, "ci_low": float(np.percentile(v, 2.5)),
                "ci_high": float(np.percentile(v, 97.5)), "p_boot": np.nan}
    add_unc("A均分标签完成后电量加权占比", boot_weighted_mean(mech.share_after_done_uniform_exact, mech.kWh, 10000, 301), "占比")
    add_unc("B功率完成后电量加权占比（60s缺口规则）", boot_weighted_mean(hp.share_after_done_power_exact, hp.kWh, 10000, 302), "占比")
    add_unc("B功率完成后电量加权占比（不桥接缺口对照）", boot_weighted_mean(hpu.share_after_done_power_exact_unbridged, hpu.kWh, 10000, 303), "占比")
    unc = pd.DataFrame(unc_rows)
    unc.to_csv(os.path.join(OUT, "uncertainty_primary.csv"), index=False)

    # 多尺度配对检验：节点层面按节点聚类bootstrap；全站序列按日块bootstrap；再作Holm校正。
    pvals, p_index = [], []
    for i, r in scale_df.iterrows():
        res = int(r.resolution_min)
        if r.scale == "52节点均值":
            nd = node_stats_from_store(scale_stores[res])
            p = boot_paired_mean(nd.mae_uniform, nd.mae_cut, 10000, 400+res)["p_boot"]
        elif r.scale == "修正10节点均值":
            nd = node_stats_from_store(scale_stores[res], sorted(station_main))
            p = boot_paired_mean(nd.mae_uniform, nd.mae_cut, 10000, 500+res)["p_boot"]
        elif r.scale == "全站52节点聚合":
            p = site_unc[("all52", res)]["p_boot"]
        else:
            p = site_unc[("main10", res)]["p_boot"]
        pvals.append(p); p_index.append(i)
    scale_df["mae_reduction_p_nominal"] = np.nan
    scale_df.loc[p_index, "mae_reduction_p_nominal"] = pvals
    scale_df["mae_reduction_p_holm"] = np.nan
    scale_df.loc[p_index, "mae_reduction_p_holm"] = holm(pvals)
    scale_df.to_csv(os.path.join(OUT, "multiscale_metrics.csv"), index=False)

    # --- 图件 ---
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    gapdf = pd.read_csv(os.path.join(OUT, "sensitivity_max_gap.csv"))
    fig, ax1 = plt.subplots(figsize=(7, 4))
    x = np.arange(len(gapdf))
    ax1.bar(x, gapdf.mae_reduction_pct, color="#2ca02c", alpha=.85, label="节点MAE降幅")
    ax1.set_xticks(x); ax1.set_xticklabels(gapdf.value.astype(str))
    ax1.set_xlabel("最大可连接采样间隔（秒）"); ax1.set_ylabel("MAE降幅（%）")
    ax2 = ax1.twinx(); ax2.plot(x, gapdf.within5_pct*100, "o-", color="#1f77b4", label="能量误差≤5%")
    ax2.set_ylabel("能量一致率（%）"); ax2.set_ylim(0, 105)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "fig_E1_max_gap_sensitivity.png"), dpi=180); plt.close(fig)

    sm = pd.read_csv(os.path.join(OUT, "representativeness_weighted_smd.csv")).sort_values("smd_unweighted")
    fig, ax = plt.subplots(figsize=(8, 5))
    y = np.arange(len(sm))
    ax.scatter(sm.smd_unweighted, y, label="加权前", color="#d62728")
    ax.scatter(sm.smd_weighted, y, label="IPTW加权后", color="#1f77b4")
    ax.axvline(-.1, color="gray", ls="--", lw=.8); ax.axvline(.1, color="gray", ls="--", lw=.8)
    ax.set_yticks(y); ax.set_yticklabels(sm.label); ax.set_xlabel("标准化均差（SMD）")
    ax.legend(); fig.tight_layout(); fig.savefig(os.path.join(OUT, "fig_E2_representativeness_smd.png"), dpi=180); plt.close(fig)

    st = pd.read_csv(os.path.join(OUT, "mechanism_idle_strata.csv"))
    x = np.arange(len(st)); w = .36
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    axes[0].bar(x-w/2, st.tvd_uniform_median, w, label="均分", color="#d62728")
    axes[0].bar(x+w/2, st.tvd_cut_median, w, label="截断", color="#2ca02c")
    axes[0].set_xticks(x); axes[0].set_xticklabels(st.stratum, rotation=18, ha="right")
    axes[0].set_ylabel("TVD中位数"); axes[0].legend(); axes[0].set_title("按完成后占桩比分层")
    axes[1].bar(x, st.uniform_after_done_weighted*100, color="#d62728", alpha=.8)
    axes[1].set_xticks(x); axes[1].set_xticklabels(st.stratum, rotation=18, ha="right")
    axes[1].set_ylabel("加权占比（%）"); axes[1].set_title("均分标签分配到完成后的电量")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "fig_E3_mechanism_strata.png"), dpi=180); plt.close(fig)

    sel = scale_df[scale_df.scale.isin(["52节点均值", "修正10节点均值", "全站52节点聚合", "修正10节点聚合"])]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    labels = sel.apply(lambda r: f"{int(r.resolution_min)}min\n{r.scale}", axis=1)
    ax.bar(np.arange(len(sel)), sel.mae_reduction_pct, color="#2ca02c")
    ax.set_xticks(np.arange(len(sel))); ax.set_xticklabels(labels, rotation=35, ha="right")
    ax.set_ylabel("MAE降幅（%）"); fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_E4_multiscale_reduction.png"), dpi=180); plt.close(fig)

    # 森林图只展示同为 kWh/片 的 MAE 配对差，避免不同单位混在同一坐标轴。
    mae_unc = unc[unc.unit == "kWh/片"].copy()
    center = mae_unc["mean_diff"].fillna(mae_unc["mean_x"])
    fig, ax = plt.subplots(figsize=(8, 4.5))
    yy = np.arange(len(mae_unc))
    ax.errorbar(center, yy,
                xerr=np.vstack([center-mae_unc.ci_low, mae_unc.ci_high-center]), fmt="o", color="#1f77b4")
    ax.axvline(0, color="gray", ls="--")
    ax.set_yticks(yy); ax.set_yticklabels(mae_unc.analysis); ax.set_xlabel("均分-截断的 MAE 差及95%置信区间（kWh/片）")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "fig_E5_uncertainty_forest.png"), dpi=180); plt.close(fig)

    # 汇总关键数值，供报告引用。
    summary = {
        "n_raw": int(len(sess)), "n_ok": int(ok.shape[0]),
        "n_power_subset": int(ok.power_subset.sum()),
        "n_power_subset_unbridged": int(ok.power_subset_unbridged.sum()),
        "n_valid_done_strict": int(ok.valid_done_strict.sum()),
        "n_zero_duration_valid": int(zero_eq.shape[0]),
        "long_gap60_segments": int(ok.n_long_gap60.sum()),
        "long_gap60_max_sec": float(ok.max_gap_sec.max()),
        "ref_A_node_mae_uniform": float(ndA.mae_uniform.mean()),
        "ref_A_node_mae_cut": float(ndA.mae_cut.mean()),
        "ref_B_node_mae_uniform": float(ndB.mae_uniform.mean()),
        "ref_B_node_mae_cut": float(ndB.mae_cut.mean()),
        "ref_B_main10_mae_uniform": float(ndBmain.mae_uniform.mean()),
        "ref_B_main10_mae_cut": float(ndBmain.mae_cut.mean()),
        "ref_B_main10_n": int(ndBmain.n.sum()),
        "power_after_done_weighted_maxgap60": float((hp.share_after_done_power_exact*hp.kWh).sum()/hp.kWh.sum()),
        "power_after_done_n_maxgap60": int(len(hp)),
        "power_after_done_weighted_unbridged": float((hpu.share_after_done_power_exact_unbridged*hpu.kWh).sum()/hpu.kWh.sum()),
        "power_after_done_n_unbridged": int(len(hpu)),
    }
    with open(os.path.join(OUT, "extended_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
