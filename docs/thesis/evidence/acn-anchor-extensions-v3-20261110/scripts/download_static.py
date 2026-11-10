# -*- coding: utf-8 -*-
"""按会话清单从 jsDelivr CDN 批量下载 ACN-Data Static 时序文件。

数据源: https://github.com/tongxin-li/ACN-Data-Static
目录:   time series data/caltech/California_Garage_01/
命名:   {stationID}-{connectionTimeUTC with microseconds}.csv.gz
        与 sessions API 的 sessionID 前四段一致。

用法: python3 download_static.py <sessions.json> <outdir> [workers]
断点续传: 已存在且非空的文件自动跳过。
"""
import json
import os
import sys
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor

# 固定到已登记的 main 提交，避免分支更新造成复现版本漂移。
SOURCE_REF = os.environ.get("ACN_STATIC_REF", "abb7cf15cc7108913e965d4375cc7270d532b65f")
BASE = (f"https://cdn.jsdelivr.net/gh/tongxin-li/ACN-Data-Static@{SOURCE_REF}/"
        "time%20series%20data/caltech/California_Garage_01/")


def load_items(path):
    text = open(path, encoding="utf-8").read().rstrip()
    try:
        return json.loads(text)["_items"]
    except json.JSONDecodeError:
        # 兼容截断的 JSON: 去掉尾部逗号后补齐结束符
        if text.endswith(","):
            text = text[:-1] + "]}"
        return json.loads(text)["_items"]


def fname_for(it):
    sid = it["sessionID"]                      # 2_39_78_362_2018-04-25 11:08:04.400812
    parts = sid.split("_", 4)                  # [2,39,78,362, 2018-04-25 11:08:04.400812]
    station = "-".join(parts[:4])
    ts = parts[4].replace(" ", "T").replace(":", "-").replace(".", "-")
    return f"{station}-{ts}.csv.gz"


def fetch(args):
    fname, outdir = args
    dest = os.path.join(outdir, fname)
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return fname, "skip"
    url = BASE + fname
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "acn-anchor/1.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read()
            if r.status == 200 and data[:2] == b"\x1f\x8b":
                with open(dest, "wb") as f:
                    f.write(data)
                return fname, "ok"
            return fname, f"bad:{r.status}"
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return fname, "missing"
            time.sleep(2 * (attempt + 1))
        except Exception:
            time.sleep(2 * (attempt + 1))
    return fname, "fail"


def main():
    src, outdir = sys.argv[1], sys.argv[2]
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 12
    os.makedirs(outdir, exist_ok=True)
    items = load_items(src)
    tasks = [(fname_for(it), outdir) for it in items]
    # 去重(同一文件绝不重复请求)
    tasks = list({t[0]: t for t in tasks}.values())
    print(f"total {len(tasks)} files, workers={workers}")
    from collections import Counter
    cnt = Counter()
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for i, (fname, status) in enumerate(ex.map(fetch, tasks), 1):
            cnt[status] += 1
            if i % 200 == 0 or i == len(tasks):
                print(f"[{i}/{len(tasks)}] {dict(cnt)} elapsed={time.time()-t0:.0f}s", flush=True)
    print("DONE", dict(cnt))


if __name__ == "__main__":
    main()
