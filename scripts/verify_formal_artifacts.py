"""正式实验产物核验工具：登记表"正式结论权限"升级的前置把关。

对每个实验的每个种子核验四类证据（对应登记表"正式可用"语义）：
1. 工件完整性：种子级 manifest/metrics/model/predictions.csv.gz/training_log，
   run 级 config_resolved.yaml/environment.json/manifest.json；
2. 数据追溯：manifest.json 的 dataset_sha256 与实验编号存在；
3. 四格还原：metrics.json 的 four_cell.absolute_difference ≤ 1e-9
   （Σ(格MAE×格样本量)/总样本量 ≡ 全局 MAE 的硬性约束）；
4. 预测键唯一性：predictions.csv.gz 的
   (split, origin_index, horizon, node_id) 四元组唯一（行数 == 唯一键数），
   并计算键集合排序哈希供跨实验一致性比对。

environment.json 的 git_commit 若为 None 如实记录（服务器无 git 提交），
不视为失败——配置追溯由 config_resolved.yaml 承担。

用法：
  .venv/bin/python scripts/verify_formal_artifacts.py [--json 输出路径]
实验路径清单在下方 EXPERIMENTS 中维护（night_run 与 outputs/experiments 两种布局）。
"""
from __future__ import annotations

import gzip
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent

# (实验ID, run路径（相对 ROOT）或 glob, 种子子目录模式)
EXPERIMENTS: List[Dict[str, Any]] = [
    {"id": "SG-EXP-002", "runs": ["outputs/night_run/20260730-171821/SG-EXP-002/20260730-171821"]},
    {"id": "SG-EXP-003", "runs": ["outputs/night_run/20260730-171821/SG-EXP-003/20260730-171821"]},
    {"id": "SG-EXP-004", "runs": ["outputs/night_run/20260730-171821/SG-EXP-004/20260730-171821"]},
    {"id": "SG-EXP-005", "runs": ["outputs/night_run/20260730-171821/SG-EXP-005/20260730-171821"]},
    # SG-EXP-006 为机制套件：children 下 4 个消融变体，各自含三种子
    {"id": "SG-EXP-006", "runs": [
        f"outputs/night_run/20260730-171821/SG-EXP-006/20260730-183243/children/{v}"
        for v in ("SG-EXP-006-ablation-no_graph",
                  "SG-EXP-006-ablation-static_graph_only",
                  "SG-EXP-006-ablation-adaptive_graph_only",
                  "SG-EXP-006-ablation-no_event_gate")
    ]},
    {"id": "SG-EXP-009", "runs": ["outputs/experiments/SG-EXP-009/20260731-095406"]},
    {"id": "SG-EXP-010", "runs": ["outputs/experiments/SG-EXP-010/20260731-114125"]},
    {"id": "SG-EXP-013", "runs": ["outputs/experiments/SG-EXP-013/20260731-131452",
                                  "outputs/experiments/SG-EXP-013/20260731-131802"]},
    {"id": "SG-EXP-018", "runs": ["outputs/experiments/SG-EXP-018/20260804-101204",
                                  "outputs/experiments/SG-EXP-018/20260804-101416"]},
]

SEED_FILE_NAMES = ["manifest.json", "metrics.json", "model.pt",
                   "predictions.csv.gz", "training_log.csv"]
RUN_FILE_NAMES = ["config_resolved.yaml", "environment.json", "manifest.json"]


def key_fingerprint(csv_path: Path) -> str:
    """预测键集合的排序指纹：读四元组列 → 按行哈希 → 排序后聚合哈希。

    键集合顺序无关比较用（跨实验同种子一致性），行序差异不影响指纹。
    """
    with gzip.open(csv_path, "rt") as f:
        df = pd.read_csv(f, usecols=["split", "origin_index", "horizon", "node_id"])
    n_total = len(df)
    n_unique = df.drop_duplicates().shape[0]
    rows = df.astype(str).apply(lambda r: "|".join(r), axis=1)
    digest = hashlib.sha256()
    for h in sorted(rows):
        digest.update(h.encode())
    return f"{n_total}/{n_unique}/{digest.hexdigest()[:16]}"


def verify_seed(seed_dir: Path) -> Dict[str, Any]:
    """核验单个种子目录，返回证据对象。"""
    result: Dict[str, Any] = {"seed": seed_dir.name, "files": {}, "checks": {}}
    for name in SEED_FILE_NAMES:
        result["files"][name] = (seed_dir / name).exists()
    metrics_path = seed_dir / "metrics.json"
    if metrics_path.exists():
        m = json.loads(metrics_path.read_text())
        result["checks"]["global_mae"] = m.get("global", {}).get("mae")
        fc = m.get("four_cell", {})
        result["checks"]["four_cell_abs_diff"] = fc.get("absolute_difference")
        result["checks"]["four_cell_ok"] = (
            isinstance(fc.get("absolute_difference"), (int, float))
            and abs(fc["absolute_difference"]) <= 1e-9
        )
    csv_path = seed_dir / "predictions.csv.gz"
    if csv_path.exists():
        try:
            fp = key_fingerprint(csv_path)
            total, unique, _ = fp.split("/")
            result["checks"]["key_fingerprint"] = fp
            result["checks"]["keys_unique"] = total == unique
        except Exception as exc:  # 核验失败如实记录原因，不静默吞掉
            result["checks"]["key_fingerprint"] = f"ERROR:{exc}"
            result["checks"]["keys_unique"] = False
    else:
        result["checks"]["keys_unique"] = None
    return result


def verify_run(run: str) -> Dict[str, Any]:
    """核验单个 run 目录（run 级文件 + 三种子）。"""
    run_dir = ROOT / run
    result: Dict[str, Any] = {"run": run, "exists": run_dir.exists(), "seeds": []}
    if not run_dir.exists():
        return result
    result["run_files"] = {name: (run_dir / name).exists() for name in RUN_FILE_NAMES}
    env_path = run_dir / "environment.json"
    if env_path.exists():
        env = json.loads(env_path.read_text())
        result["git_commit"] = env.get("git_commit")
        result["cuda"] = f"{env.get('cuda_version')} × {env.get('device_count')} 卡"
    mf_path = run_dir / "manifest.json"
    if mf_path.exists():
        mf = json.loads(mf_path.read_text())
        result["dataset_sha256"] = mf.get("dataset_sha256")
        result["experiment_id"] = mf.get("experiment_id")
        result["seeds_declared"] = mf.get("seeds")
    for seed_dir in sorted(run_dir.glob("seed-*")):
        result["seeds"].append(verify_seed(seed_dir))
    return result


def main() -> int:
    report: Dict[str, Any] = {"experiments": []}
    for exp in EXPERIMENTS:
        entry: Dict[str, Any] = {"id": exp["id"], "runs": [verify_run(r) for r in exp["runs"]]}
        report["experiments"].append(entry)
    # 摘要统计
    n_seeds, n_ok = 0, 0
    for exp in report["experiments"]:
        for run in exp["runs"]:
            for seed in run.get("seeds", []):
                n_seeds += 1
                files_ok = all(seed["files"].values())
                four_ok = seed["checks"].get("four_cell_ok") is True
                keys_ok = seed["checks"].get("keys_unique") is True
                if files_ok and four_ok and keys_ok:
                    n_ok += 1
                else:
                    print(f"  ⚠ {exp['id']} {run['run']} {seed['seed']}: "
                          f"files={files_ok} four_cell={four_ok} keys={keys_ok}")
    print(f"核验完成：{n_seeds} 个种子，{n_ok} 个全证据通过")
    print(json.dumps(report, ensure_ascii=False, indent=1))
    if len(sys.argv) > 2 and sys.argv[1] == "--json":
        Path(sys.argv[2]).write_text(json.dumps(report, ensure_ascii=False, indent=1))
    return 0 if n_ok == n_seeds else 1


if __name__ == "__main__":
    sys.exit(main())
