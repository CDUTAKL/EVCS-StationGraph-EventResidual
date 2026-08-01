"""论文图 provenance manifest 生成与校验（审查 H-13，2026-08-01）。

为 18 张最终图建立唯一可追溯入口：图 → 生成脚本(SHA) → 输入工件(SHA) → 输出 SHA
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

FIG_DIR = Path("outputs/figures")
OUT = FIG_DIR / "manifest.json"
SCRIPT_DIR = Path("scripts/figures")
BUNDLE_PATH = Path("data/processed/SG-DATA-005-primary-tensor.npz")

# 图 → 最终生成脚本（batch4~8；batch3 已废弃勿运行）
FINAL_SCRIPTS = {
    "fig2_3_load_heatmap": "batch5_restyle.py",
    "fig2_3b_autocorrelation": "batch4_redraw.py",
    "fig2_4_weekly_curves": "batch5_restyle.py",
    "fig2_5_load_distribution": "batch4_redraw.py",
    "fig2_6_event_hourly": "batch4_redraw.py",
    "fig3_1_model_mae_comparison": "batch4_redraw.py",
    "fig3_3_lre_matrices": "batch5_restyle.py",
    "fig3_5_training_curve": "batch5_restyle.py",
    "fig3_6_bootstrap_significance": "batch4_redraw.py",
    "fig3_7_alpha_convergence": "batch5_restyle.py",
    "fig4_2_intervention": "batch5_restyle.py",
    "fig4_4_four_cell": "batch4_redraw.py",
    "fig5_2_transfer_entropy": "batch5_restyle.py",
    "fig5_3_asymmetry": "batch6_te_coverage_enhance.py",
    "fig5_4_coverage": "batch6_te_coverage_enhance.py",
    "fig5_5_quantile_per_node": "batch7_fig5_5_quantile.py",
    "fig5_6_mechanism_enhance": "batch8_fig5_6_enhance.py",
    "fig5_8_cate": "batch5_restyle.py",
}

# 图 → 关键输入工件（存在性 + SHA 校验）
INPUTS_BY_FIGURE = {
    "fig2_3_load_heatmap": [BUNDLE_PATH],
    "fig2_3b_autocorrelation": [BUNDLE_PATH],
    "fig2_4_weekly_curves": [BUNDLE_PATH],
    "fig2_5_load_distribution": [BUNDLE_PATH],
    "fig2_6_event_hourly": [BUNDLE_PATH],
    "fig3_1_model_mae_comparison": [],
    "fig3_3_lre_matrices": [Path("outputs/experiments/SG-EXP-004/20260731-102456/relation_matrices.npz")],
    "fig3_5_training_curve": [],
    "fig3_6_bootstrap_significance": [Path("outputs/analysis/bootstrap_significance.json")],
    "fig3_7_alpha_convergence": [],
    "fig4_2_intervention": [Path("outputs/analysis/gate_intervention/intervention_summary.json")],
    "fig4_4_four_cell": [Path("outputs/experiments/SG-EXP-004/20260731-102456/seed-2024/metrics.json")],
    "fig5_2_transfer_entropy": [Path("outputs/analysis/transfer_entropy/transfer_entropy_summary.json")],
    "fig5_3_asymmetry": [Path("outputs/analysis/transfer_entropy/transfer_entropy_summary.json")],
    "fig5_4_coverage": [Path("outputs/analysis/conformal_prediction/conformal_summary.json")],
    "fig5_5_quantile_per_node": [Path("outputs/analysis/conformal_prediction/conformal_summary.json")],
    "fig5_6_mechanism_enhance": [
        Path("outputs/analysis/variant_quick_check/variant_napl.json"),
        Path("outputs/analysis/variant_quick_check/variant_gate-mi.json"),
    ],
    "fig5_8_cate": [Path("outputs/analysis/counterfactual_cate/counterfactual_cate_summary.json")],
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


def build_manifest() -> dict:
    """构建完整 manifest（含 script SHA、inputs、git commit）。"""
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
        inputs = []
        for ip in INPUTS_BY_FIGURE.get(name, []):
            if ip.is_file():
                inputs.append({"path": str(ip), "sha256": sha256(ip)})
            else:
                inputs.append({"path": str(ip), "missing": True})
        sp = SCRIPT_DIR / script
        figures[name] = {
            "script": {
                "path": script,
                "sha256": sha256(sp) if sp.is_file() else None,
            },
            "inputs": inputs,
            "formats": entries,
        }
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit(),
        "dataset": {"path": str(BUNDLE_PATH),
                    "sha256": sha256(BUNDLE_PATH) if BUNDLE_PATH.is_file() else None},
        "missing_files": missing,
        "figures": figures,
    }


def check(manifest: dict) -> bool:
    """校验当前文件与 manifest 一致；不一致返回 False。"""
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
    return ok


def main() -> None:
    """生成或校验 manifest（--check 时不一致退出码 1）。"""
    parser = argparse.ArgumentParser(description="图 provenance manifest")
    parser.add_argument("--check", action="store_true", help="校验模式")
    args = parser.parse_args()

    manifest = build_manifest()
    if args.check:
        if not OUT.is_file():
            print("✗ manifest 不存在，请先生成")
            sys.exit(1)
        recorded = json.loads(OUT.read_text())
        ok = check(recorded)
        print("✅ manifest 校验通过" if ok else "✗ manifest 校验失败")
        sys.exit(0 if ok else 1)

    OUT.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(f"✅ 已生成 {OUT}（{len(manifest['figures'])} 张图，commit {manifest['git_commit']}）")
    return None


if __name__ == "__main__":
    sys.exit(main() or 0)
