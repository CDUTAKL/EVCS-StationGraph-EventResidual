# -*- coding: utf-8 -*-
"""ACN-Data Static 跨车场/跨时期功率覆盖率普查。

目的: 回答"CG1 2018年5—6月窗口的高功率覆盖率能否推广到其他车场与时期"。
方法: 对 GitHub 仓库 tongxin-li/ACN-Data-Static 的七个车场目录
      (caltech/{California_Garage_01, California_Garage_02, LIGO_01,
       N_Wilson_Garage_01, S_Wilson_Garage_01}, office_01/Parking_Lot_01,
       jpl/Arroyo_Garage_01)
      按 车场 x 年份 分层随机抽样，逐文件计算:
        - 是否有 Power (kW) 列、非空比例
        - 采样间隔中位数 / P95
        - 覆盖率 coverage_60s = 相邻有效采样间隔(dt<=60s)之和 / 文件时间跨度
        - 功率积分能量 (梯形, 不跨缺口)
        - 长缺口(>60s)次数与最长缺口
      汇总: 各 车场 x 年份 的覆盖率中位数、覆盖率>=0.95 占比等。

输入: /tmp/garage_files.json (由 GitHub API 抓取的各车场文件名清单)
输出: results_survey/survey_files.csv, survey_summary.csv, survey_meta.json

用法: python3 coverage_survey.py
"""
import io
import json
import os
import random
import re
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "results_survey")
os.makedirs(OUT, exist_ok=True)

# jsDelivr CDN 单文件下载（@main；整包超限但单文件可用）
CDN = ("https://cdn.jsdelivr.net/gh/tongxin-li/ACN-Data-Static@main/"
       "time%20series%20data/{dir}/{fname}")
GARAGE_DIR = {
    "CG1": "caltech/California_Garage_01",
    "CG2": "caltech/California_Garage_02",
    "LIGO": "caltech/LIGO_01",
    "NWG": "caltech/N_Wilson_Garage_01",
    "SWG": "caltech/S_Wilson_Garage_01",
    "OFFICE_PL1": "office_01/Parking_Lot_01",
    "JPL_AG1": "jpl/Arroyo_Garage_01",
}

# 每层抽样数上限
CELL_CAP = {"CG1": 30, "CG2": 20, "LIGO": 40, "NWG": 30, "SWG": 25,
            "OFFICE_PL1": 25, "JPL_AG1": 30}
SEED = 20261110

YEAR_RE = re.compile(r"-(\d{4})-\d{2}-\d{2}T")


def sample_plan(garage_files):
    rng = random.Random(SEED)
    plan = []  # (garage, year, fname)
    for g, files in sorted(garage_files.items()):
        if g not in GARAGE_DIR:
            continue
        by_year = {}
        for f in files:
            m = YEAR_RE.search(f)
            if m:
                by_year.setdefault(m.group(1), []).append(f)
        for y, fl in sorted(by_year.items()):
            fl = sorted(fl)
            k = min(CELL_CAP[g], len(fl))
            plan.extend((g, y, f) for f in rng.sample(fl, k))
    return plan


def fetch_one(task):
    g, y, fname = task
    url = CDN.format(dir=GARAGE_DIR[g], fname=urllib.request.quote(fname))
    dest = os.path.join("/tmp/acn_survey_raw", g)
    os.makedirs(dest, exist_ok=True)
    path = os.path.join(dest, fname)
    if not (os.path.exists(path) and os.path.getsize(path) > 20):
        for attempt in range(3):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "acn-survey/1.0"})
                with urllib.request.urlopen(req, timeout=90) as r:
                    data = r.read()
                if data[:2] == b"\x1f\x8b":
                    with open(path, "wb") as f:
                        f.write(data)
                    break
                return g, y, fname, f"bad:{r.status}"
            except Exception as e:
                if attempt == 2:
                    return g, y, fname, f"err:{e}"
                time.sleep(2 * (attempt + 1))
    return g, y, fname, "ok"


def analyse_file(path):
    """逐文件指标。返回 dict 或 None（不可解析）。"""
    try:
        df = pd.read_csv(path, compression="gzip")
    except Exception:
        return None
    cols = list(df.columns)
    # 时间列：优先找名字含 Time 的列；否则用第一列（部分车库文件首列无表头、直接是时间戳）
    tcol = next((c for c in cols if "Time" in c or "time" in c), None)
    if tcol is None:
        first = df.columns[0]
        probe = pd.to_datetime(df[first].head(20), errors="coerce", utc=True)
        if probe.notna().mean() > 0.8:
            tcol = first
    pcol = next((c for c in cols if "Power" in c), None)
    res = {
        "n_rows": len(df),
        "has_power": pcol is not None,
        "power_nonnull": float(df[pcol].notna().mean()) if pcol else np.nan,
        "cols": "|".join(cols),
    }
    if tcol is None or len(df) < 2:
        res.update(span_s=np.nan, dt_med_s=np.nan, dt_p95_s=np.nan,
                   coverage_60s=np.nan, energy_kwh=np.nan,
                   n_gaps60=np.nan, max_gap_s=np.nan)
        return res
    t = pd.to_datetime(df[tcol], errors="coerce", utc=True)
    ok = t.notna()
    df = df.loc[ok]
    t = t.loc[ok].sort_values()
    if len(t) < 2:
        res.update(span_s=np.nan, dt_med_s=np.nan, dt_p95_s=np.nan,
                   coverage_60s=np.nan, energy_kwh=np.nan,
                   n_gaps60=np.nan, max_gap_s=np.nan)
        return res
    ts = t.to_numpy(dtype="datetime64[ns]").astype("int64") / 1e9
    dt = np.diff(ts)
    span = ts[-1] - ts[0]
    valid = dt[(dt > 0) & (dt <= 60)]
    gaps = dt[dt > 60]
    res["span_s"] = float(span)
    res["dt_med_s"] = float(np.median(dt[dt > 0])) if np.any(dt > 0) else np.nan
    res["dt_p95_s"] = float(np.percentile(dt[dt > 0], 95)) if np.any(dt > 0) else np.nan
    res["coverage_60s"] = float(valid.sum() / span) if span > 0 else np.nan
    res["n_gaps60"] = int(len(gaps))
    res["max_gap_s"] = float(gaps.max()) if len(gaps) else 0.0
    # 功率积分（梯形，仅有效相邻段，不跨缺口）
    if pcol:
        p = pd.to_numeric(df[pcol], errors="coerce").to_numpy(dtype=float)
        tt = ts
        # 与 dt 对齐：段 i 介于 tt[i] 与 tt[i+1]
        seg_dt = np.diff(tt)
        good = (seg_dt > 0) & (seg_dt <= 60) & ~np.isnan(p[:-1]) & ~np.isnan(p[1:])
        if good.any():
            e = np.trapezoid(p[: len(seg_dt)][good], tt[: len(seg_dt)][good])
            # trapezoid 需连续坐标，这里逐段近似: 0.5*(p_i+p_{i+1})*dt
            e = float((0.5 * (p[: len(seg_dt)][good] + p[1:][good]) * seg_dt[good] / 3600.0).sum())
        else:
            e = 0.0
        res["energy_kwh"] = e
    else:
        res["energy_kwh"] = np.nan
    return res


def main():
    garage_files = json.load(open("/tmp/garage_files.json"))
    plan = sample_plan(garage_files)
    print(f"sample plan: {len(plan)} files across {len(set((g,y) for g,y,_ in plan))} cells",
          flush=True)

    dl_results = []
    with ThreadPoolExecutor(max_workers=12) as ex:
        for i, r in enumerate(ex.map(fetch_one, plan), 1):
            dl_results.append(r)
            if i % 25 == 0:
                print(f"  downloaded {i}/{len(plan)}", flush=True)
    fails = [r for r in dl_results if r[3] != "ok"]
    print(f"download failures: {len(fails)}", flush=True)
    for r in fails[:20]:
        print("  FAIL", r, flush=True)

    rows = []
    for g, y, fname, status in dl_results:
        if status != "ok":
            rows.append({"garage": g, "year": y, "file": fname, "status": status})
            continue
        path = os.path.join("/tmp/acn_survey_raw", g, fname)
        m = analyse_file(path)
        if m is None:
            rows.append({"garage": g, "year": y, "file": fname, "status": "parse_fail"})
            continue
        row = {"garage": g, "year": y, "file": fname, "status": "ok"}
        row.update(m)
        rows.append(row)
    files_df = pd.DataFrame(rows)
    files_df.to_csv(os.path.join(OUT, "survey_files.csv"), index=False)

    ok = files_df[files_df.status == "ok"].copy()
    summ = (ok.groupby(["garage", "year"])
              .agg(n=("file", "count"),
                   cov_med=("coverage_60s", "median"),
                   cov_q25=("coverage_60s", lambda s: s.quantile(0.25)),
                   cov_p95share=("coverage_60s", lambda s: (s >= 0.95).mean()),
                   cov_p90share=("coverage_60s", lambda s: (s >= 0.90).mean()),
                   dt_med_s=("dt_med_s", "median"),
                   power_nonnull_med=("power_nonnull", "median"),
                   energy_med=("energy_kwh", "median"),
                   n_gaps60_med=("n_gaps60", "median"))
              .reset_index())
    summ.to_csv(os.path.join(OUT, "survey_summary.csv"), index=False)
    print(summ.to_string(index=False), flush=True)

    meta = {
        "source": "https://github.com/tongxin-li/ACN-Data-Static @ main (jsDelivr CDN)",
        "survey_date_utc": datetime.now(timezone.utc).isoformat(),
        "seed": SEED,
        "cell_cap": CELL_CAP,
        "n_planned": len(plan),
        "n_downloaded": int((files_df.status == "ok").sum()),
        "garage_totals": {g: len(f) for g, f in garage_files.items() if g in GARAGE_DIR},
        "coverage_rule": "sum(adjacent dt<=60s)/file span; energy trapezoid without gap bridging",
    }
    json.dump(meta, open(os.path.join(OUT, "survey_meta.json"), "w"),
              ensure_ascii=False, indent=1)
    print("done ->", OUT, flush=True)


if __name__ == "__main__":
    main()
