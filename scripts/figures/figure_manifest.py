"""论文图 provenance manifest 生成与校验（审查 H-13，2026-08-01）。

为 19 张最终图建立唯一可追溯入口：图 → 生成脚本(SHA) → 输入工件(SHA) → 输出 SHA
→ git commit → 数据集 SHA。

用法：
  .venv/bin/python scripts/figures/figure_manifest.py             # 生成 manifest.json
  .venv/bin/python scripts/figures/figure_manifest.py --check     # 校验（不一致退出非零）
输出：outputs/figures/manifest.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple, Union

FIG_DIR = Path("outputs/figures")
OUT = FIG_DIR / "manifest.json"
SCRIPT_DIR = Path("scripts/figures")
BUNDLE_PATH = Path("data/processed/SG-DATA-005-primary-tensor.npz")

# 5 个对比模型的 seed-* metrics.json（审查 H2：004 与图 3-1 同口径用正式流水线
# night_run；009/010 仅 experiments 存在；图 3-4/3-8/3-9 共享此输入集合）
MAE_5_MODELS_INPUTS = [
    ("glob", "outputs/night_run/20260730-171821/SG-EXP-002/*/seed-*/metrics.json"),
    ("glob", "outputs/night_run/20260730-171821/SG-EXP-003/*/seed-*/metrics.json"),
    ("glob", "outputs/night_run/20260730-171821/SG-EXP-004/*/seed-*/metrics.json"),
    ("glob", "outputs/experiments/SG-EXP-009/*/seed-*/metrics.json"),
    ("glob", "outputs/experiments/SG-EXP-010/*/seed-*/metrics.json"),
]

# 图 → 最终生成脚本（batch4~13；batch3 已废弃勿运行）
FINAL_SCRIPTS = {
    "fig2_2_node_coverage": "batch10_fig2_2_coverage.py",
    "fig2_3_load_heatmap": "batch5_restyle.py",
    "fig2_3b_autocorrelation": "batch4_redraw.py",
    "fig2_4_weekly_curves": "batch5_restyle.py",
    "fig2_5_load_distribution": "batch4_redraw.py",
    "fig2_6_event_hourly": "batch4_redraw.py",
    "fig2_7_feature_correlation": "batch11_chapter2_extra.py",
    "fig2_8_weekday_hour_heatmap": "batch11_chapter2_extra.py",
    "fig2_9_event_component_composition": "batch11_chapter2_extra.py",
    "fig2_10_event_window_length": "batch11_chapter2_extra.py",
    "fig3_1_model_mae_comparison": "batch4_redraw.py",
    "fig3_3_lre_matrices": "batch5_restyle.py",
    "fig3_4_mae_by_horizon": "batch12_chapter3_extra.py",
    "fig3_5_training_curve": "batch9_advisor_redraw.py",
    "fig3_6_bootstrap_difference": "batch9_advisor_redraw.py",
    "fig3_7_alpha_convergence": "batch9_advisor_redraw.py",
    "fig3_8_mae_by_window": "batch12_chapter3_extra.py",
    "fig3_9_mae_by_node": "batch12_chapter3_extra.py",
    "fig3_10_mechanism_ablation": "batch12_chapter3_extra.py",
    "fig3_11_event_window_forecast": "batch12_chapter3_extra.py",
    "fig4_2_intervention": "batch5_restyle.py",
    "fig4_4_four_cell": "batch9_advisor_redraw.py",
    "fig4_6_residual_distribution": "batch13_chapter4_5_extra.py",
    "fig4_7_error_vs_event_intensity": "batch13_chapter4_5_extra.py",
    "fig5_2_transfer_entropy": "batch5_restyle.py",
    "fig5_3_asymmetry": "batch6_te_coverage_enhance.py",
    "fig5_4_coverage": "batch9_advisor_redraw.py",
    "fig5_5_quantile_per_node": "batch9_advisor_redraw.py",
    "fig5_6_mechanism_enhance": "batch9_advisor_redraw.py",
    "fig5_8_parameter_intervention": "batch5_restyle.py",
    "fig5_10_coverage_width": "batch13_chapter4_5_extra.py",
    "fig5_11_te_vs_relations": "batch13_chapter4_5_extra.py",
}

# 图 → 关键输入工件（存在性 + SHA 校验；glob 模式展开为匹配文件列表）
# 审查 H-13（2026-08-01）：fig3_1 数值硬编码于脚本，其数据源为正式三种子
# metrics.json（night_run/20260730-171821）；fig3_5/3_7 读取训练日志。
INPUTS_BY_FIGURE = {
    "fig2_2_node_coverage": [Path("data/processed/SG-DATA-002-node-coverage-stability.csv")],
    "fig2_3_load_heatmap": [BUNDLE_PATH],
    "fig2_3b_autocorrelation": [BUNDLE_PATH],
    "fig2_4_weekly_curves": [BUNDLE_PATH],
    "fig2_5_load_distribution": [BUNDLE_PATH],
    "fig2_6_event_hourly": [BUNDLE_PATH],
    "fig2_7_feature_correlation": [BUNDLE_PATH],
    "fig2_8_weekday_hour_heatmap": [BUNDLE_PATH],
    "fig2_9_event_component_composition": [BUNDLE_PATH],
    "fig2_10_event_window_length": [BUNDLE_PATH],
    "fig3_1_model_mae_comparison": [
        ("glob", "outputs/night_run/20260730-171821/SG-EXP-002/*/seed-*/metrics.json"),
        ("glob", "outputs/night_run/20260730-171821/SG-EXP-003/*/seed-*/metrics.json"),
        ("glob", "outputs/night_run/20260730-171821/SG-EXP-004/*/seed-*/metrics.json"),
    ],
    "fig3_3_lre_matrices": [Path("outputs/experiments/SG-EXP-004/20260731-102456/relation_matrices.npz")],
    "fig3_4_mae_by_horizon": MAE_5_MODELS_INPUTS,
    "fig3_5_training_curve": [
        ("glob", "outputs/experiments/SG-EXP-004/*/seed-*/training_log.csv"),
    ],
    "fig3_6_bootstrap_difference": [Path("outputs/analysis/bootstrap_significance.json")],
    "fig3_7_alpha_convergence": [
        ("glob", "outputs/experiments/SG-EXP-004/*/seed-*/training_log.csv"),
    ],
    "fig3_8_mae_by_window": MAE_5_MODELS_INPUTS,
    "fig3_9_mae_by_node": MAE_5_MODELS_INPUTS,
    "fig3_10_mechanism_ablation": [
        ("glob", "outputs/night_run/20260730-171821/SG-EXP-006/*/children/SG-EXP-006-ablation-*/*/seed-*/metrics.json"),
        ("glob", "outputs/experiments/SG-EXP-004/*/seed-*/metrics.json"),
    ],
    "fig3_11_event_window_forecast": [Path("outputs/experiments/SG-EXP-004/20260731-102456/seed-2024/predictions.csv.gz")],
    "fig4_2_intervention": [Path("outputs/analysis/gate_intervention/intervention_summary.json")],
    "fig4_4_four_cell": [Path("outputs/experiments/SG-EXP-004/20260731-102456/seed-2024/metrics.json")],
    "fig4_6_residual_distribution": [
        ("glob", "outputs/experiments/SG-EXP-004/*/seed-2024/predictions.csv.gz"),
        ("glob", "outputs/night_run/20260730-171821/SG-EXP-002/*/seed-2024/predictions.csv.gz"),
        ("glob", "outputs/night_run/20260730-171821/SG-EXP-003/*/seed-2024/predictions.csv.gz"),
    ],
    "fig4_7_error_vs_event_intensity": [Path("outputs/experiments/SG-EXP-004/20260731-102456/seed-2024/predictions.csv.gz")],
    "fig5_2_transfer_entropy": [Path("outputs/analysis/transfer_entropy/transfer_entropy_summary.json")],
    "fig5_3_asymmetry": [Path("outputs/analysis/transfer_entropy/transfer_entropy_summary.json")],
    "fig5_4_coverage": [Path("outputs/analysis/conformal_prediction/conformal_summary.json")],
    "fig5_5_quantile_per_node": [Path("outputs/analysis/conformal_prediction/conformal_summary.json")],
    "fig5_6_mechanism_enhance": [
        Path("outputs/analysis/variant_quick_check/variant_napl.json"),
        Path("outputs/analysis/variant_quick_check/variant_gate-mi.json"),
    ],
    "fig5_8_parameter_intervention": [Path("outputs/analysis/counterfactual_cate/counterfactual_cate_summary.json")],
    "fig5_10_coverage_width": [Path("outputs/analysis/conformal_prediction/conformal_summary.json")],
    "fig5_11_te_vs_relations": [
        Path("outputs/analysis/transfer_entropy/transfer_entropy_summary.json"),
        Path("outputs/experiments/SG-EXP-004/20260731-102456/relation_matrices.npz"),
    ],
}


def sha256(path: Path) -> str:
    """计算文件 sha256（大文件分块读取）。"""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_commit() -> str:
    """当前 HEAD 短哈希；非 git 环境返回 unknown。"""
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True, timeout=10)
        return out.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def _expand_inputs(specs) -> list[dict]:
    """展开输入规格：Path 直取，("glob", pattern) 展开为匹配文件列表。"""
    import glob as globmod

    out = []
    for spec in specs:
        if isinstance(spec, tuple) and spec[0] == "glob":
            for p in sorted(globmod.glob(spec[1])):
                if Path(p).is_file():
                    out.append({"path": p, "sha256": sha256(Path(p))})
        else:
            p = Path(spec)
            if p.is_file():
                out.append({"path": str(p), "sha256": sha256(p)})
            else:
                out.append({"path": str(p), "missing": True})
    return out


def build_manifest() -> dict:
    """构建完整 manifest（含 script SHA、inputs、source_commit）。"""
    figures = {}
    missing = []
    for name, script in FINAL_SCRIPTS.items():
        entries = {}
        for ext in ("svg", "png"):
            p = FIG_DIR / f"{name}.{ext}"
            if not p.is_file():
                missing.append(f"{name}.{ext}")
                continue
            entries[ext] = {
                "sha256": sha256(p),
                "size_bytes": p.stat().st_size,
                "mtime_utc": datetime.fromtimestamp(p.stat().st_mtime,
                                                    tz=timezone.utc).isoformat(),
            }
        sp = SCRIPT_DIR / script
        figures[name] = {
            "script": {
                "path": script,
                "sha256": sha256(sp) if sp.is_file() else None,
            },
            "inputs": _expand_inputs(INPUTS_BY_FIGURE.get(name, [])),
            "formats": entries,
        }
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        # 审查 H-13（2026-08-01）：记录生成图片前的代码状态。manifest 本身属于
        # 提交内容，无法在提交前得知最终 commit SHA——命名 source_commit 避免
        # 自引用歧义；包含 manifest 的提交由 Git 历史确定。
        "source_commit": git_commit(),
        "dataset": {"path": str(BUNDLE_PATH),
                    "sha256": sha256(BUNDLE_PATH) if BUNDLE_PATH.is_file() else None},
        "missing_files": missing,
        "figures": figures,
    }


def check_repository(manifest: dict) -> bool:
    """仓库完整性校验（CI 用，审查 2026-08-01）：只检查 Git 内内容——
    图输出 SHA、绘图脚本 SHA、输入记录完整性、missing_files 为空。
    不验证外部输入工件/数据集的哈希（干净 checkout 不含这些文件）。"""
    ok = True
    for name, info in manifest["figures"].items():
        for ext in ("svg", "png"):
            p = FIG_DIR / f"{name}.{ext}"
            cur = sha256(p) if p.is_file() else None
            if cur != info["formats"].get(ext, {}).get("sha256"):
                ok = False
                print(f"  ✗ {name}.{ext} SHA 不一致")
        sp = SCRIPT_DIR / info["script"]["path"]
        if not sp.is_file() or sha256(sp) != info["script"]["sha256"]:
            ok = False
            print(f"  ✗ 脚本 {info['script']['path']} 缺失或已变化")
        if not info.get("inputs"):
            ok = False
            print(f"  ✗ {name} 无输入工件记录")
        for item in info.get("inputs", []):
            if "path" not in item or "sha256" not in item:
                ok = False
                print(f"  ✗ {name} 输入记录不完整: {item}")
    if manifest.get("missing_files"):
        ok = False
        print(f"  ✗ missing_files 非空: {manifest['missing_files']}")
    return ok


def check(manifest: dict) -> bool:
    """本地完整 provenance 校验（输出图 + 脚本 + 输入工件 + 数据集）；不一致返回 False。"""
    ok = True
    for name, info in manifest["figures"].items():
        for ext in ("svg", "png"):
            p = FIG_DIR / f"{name}.{ext}"
            cur = sha256(p) if p.is_file() else None
            recorded = info["formats"].get(ext, {}).get("sha256")
            if cur != recorded:
                ok = False
                print(f"  ✗ {name}.{ext}: 当前 {cur} ≠ manifest {recorded}")
        sp = SCRIPT_DIR / info["script"]["path"]
        cur_s = sha256(sp) if sp.is_file() else None
        if cur_s != info["script"]["sha256"]:
            ok = False
            print(f"  ✗ 脚本 {info['script']['path']} 已变化")
        # 输入工件校验（审查 H-13：--check 需覆盖 inputs）
        for item in info.get("inputs", []):
            p = Path(item["path"])
            cur_i = sha256(p) if p.is_file() else None
            if cur_i != item.get("sha256"):
                ok = False
                print(f"  ✗ 输入 {item['path']}: 当前 {cur_i} ≠ manifest {item.get('sha256')}")
    # 顶层数据集校验
    ds = manifest.get("dataset", {})
    dsp = Path(ds.get("path", ""))
    cur_d = sha256(dsp) if dsp.is_file() else None
    if cur_d != ds.get("sha256"):
        ok = False
        print(f"  ✗ 数据集 {ds.get('path')}: 当前 {cur_d} ≠ manifest {ds.get('sha256')}")
    return ok


def main() -> None:
    """生成或校验 manifest（--check 本地完整 / --check-repository CI 仓库级）。"""
    parser = argparse.ArgumentParser(description="图 provenance manifest")
    parser.add_argument("--check", action="store_true",
                        help="本地完整校验（含数据集与输入工件哈希）")
    parser.add_argument("--check-repository", action="store_true",
                        help="仓库完整性校验（CI 用，仅检查 Git 内内容）")
    args = parser.parse_args()

    manifest = build_manifest()
    if args.check or args.check_repository:
        if not OUT.is_file():
            print("✗ manifest 不存在，请先生成")
            sys.exit(1)
        recorded = json.loads(OUT.read_text())
        ok = check_repository(recorded) if args.check_repository else check(recorded)
        print("✅ manifest 校验通过" if ok else "✗ manifest 校验失败")
        sys.exit(0 if ok else 1)

    OUT.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(f"✅ 已生成 {OUT}（{len(manifest['figures'])} 张图，source_commit "
          f"{manifest['source_commit']}）")
    return None


if __name__ == "__main__":
    sys.exit(main() or 0)
