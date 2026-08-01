"""论文图 provenance manifest 生成（审查 H-13，2026-08-01）。

为 18 张最终图建立唯一可追溯入口：图 → 生成脚本 → 输入工件 → 输出 SHA。
用法：.venv/bin/python scripts/figures/figure_manifest.py
输出：outputs/figures/manifest.json（含每图 sha256、mtime、生成脚本、输入文件）
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

FIG_DIR = Path("outputs/figures")
OUT = FIG_DIR / "manifest.json"

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


def sha256(path: Path) -> str:
    """计算文件 sha256（大文件分块读取）。"""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    """生成 manifest.json：18 张图 × (svg+png) 的哈希与来源映射。"""
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
        figures[name] = {"script": script, "formats": entries}
    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "note": "最终图 provenance；重绘后需重新生成本清单。图注/数值口径见对应批次脚本注释。",
        "figures": figures,
    }
    if missing:
        manifest["missing_files"] = missing
        print(f"⚠ 缺失文件：{missing}")
    OUT.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(f"✅ 已生成 {OUT}（{len(figures)} 张图）")


if __name__ == "__main__":
    sys.exit(main())
