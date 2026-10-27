"""论文图 provenance manifest 生成与校验（新增图3-17、图5-9，2026-10-26）。

为主文图建立唯一可追溯入口：图 → 生成脚本(SHA)（若为历史PNG示意图则明确标记缺失）
→ 输入工件(SHA) → 输出 SHA → git commit → 数据集 SHA。

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

# 6 个对比模型的 seed-* metrics.json；全局MAE、逐步长、分层窗口和逐节点图
# 使用同一组已登记模型产物，当前对应图3-11、3-12、3-14、3-15。
MAE_5_MODELS_INPUTS = [
    ("glob", "outputs/night_run/20260730-171821/SG-EXP-002/*/seed-*/metrics.json"),
    ("glob", "outputs/night_run/20260730-171821/SG-EXP-003/*/seed-*/metrics.json"),
    ("glob", "outputs/night_run/20260730-171821/SG-EXP-004/*/seed-*/metrics.json"),
    ("glob", "outputs/experiments/SG-EXP-008/*/seed-*/metrics.json"),
    ("glob", "outputs/experiments/SG-EXP-009/*/seed-*/metrics.json"),
    ("glob", "outputs/experiments/SG-EXP-010/*/seed-*/metrics.json"),
]

# 图 → 最终生成脚本。方法示意图登记生成提示词或来源核验脚本；
# fig5_1 虽为衔接示意图，但包含 TE/PCMCI+ 计数，故纳入本 manifest。
FINAL_SCRIPTS = {
    # 三幅ImageGen示意图与一幅结果图风格图已在2026-09-11替换；
    # ImageGen原生资产不伪装为SVG，图4-4由确定性脚本输出SVG+PNG。
    "fig1_1_research_gap_map": None,
    "fig1_2_roadmap": "imagegen_priority_registry.py",
    "fig2_1_data_reconstruction": "imagegen_priority_registry.py",
    "fig2_2_node_coverage": "batch10_fig2_2_coverage.py",
    "fig2_3_load_heatmap": "batch_priority_results.py",
    "fig2_4_autocorrelation": "batch4_redraw.py",
    "fig2_5_weekly_curves": "batch24_result_figures_20261006.py",
    "fig2_6_load_distribution": "batch4_redraw.py",
    "fig2_7_event_score_flow": "imagegen_priority_registry.py",
    "fig2_8_event_hourly": "batch_priority_results.py",
    "fig2_9_dual_window_definition": "imagegen_priority_registry.py",
    "fig2_10_feature_correlation": "batch11_chapter2_extra.py",
    "fig2_11_weekday_hour_heatmap": "batch_priority_results.py",
    "fig2_12_jpl_validation_protocol": "imagegen_priority_registry.py",
    "fig3_5_lre_matrices": "batch24_result_figures_20261006.py",
    "fig3_1_mrggcn_architecture": "imagegen_priority_registry.py",
    "fig3_2_relation_propagation_unit": "imagegen_priority_registry.py",
    "fig3_3_temporal_skip_fusion": "imagegen_priority_registry.py",
    "fig3_4_lre_construction": "imagegen_priority_registry.py",
    "fig3_6_gate_residual_detail": "imagegen_priority_registry.py",
    "fig3_7_cross_layer_detail": "imagegen_priority_registry.py",
    "fig3_8_train_predict_pipeline": "imagegen_priority_registry.py",
    "fig3_9_jpl_mae_primary": "batch23_jpl_figs.py",
    "fig3_10_jpl_stratified_mae": "batch23_jpl_figs.py",
    "fig3_11_model_mae_comparison": "batch4_redraw.py",
    "fig3_12_mae_by_horizon": "refine_requested_20260920.py",
    "fig3_13_bootstrap_difference": "batch_priority_results.py",
    "fig3_14_mae_by_window": "batch12_chapter3_extra.py",
    "fig3_15_mae_by_node": "batch12_chapter3_extra.py",
    "fig3_16_mechanism_ablation": "batch12_chapter3_extra.py",
    "fig3_17_proxy_label_stability": "fig3_17_proxy_label_stability.py",
    "fig4_1_three_layer_framework": "imagegen_priority_registry.py",
    "fig4_2_beta_profile": "batch25_beta_te_results_20261006.py",
    "fig4_3_intervention": "batch5_restyle.py",
    "fig4_5_four_cell": "redraw_fig4_4_result_style_20260911.py",
    "fig4_6_residual_distribution": "batch_priority_results.py",
    "fig4_7_error_vs_event_intensity": "refine_requested_20260920.py",
    "fig5_1_te_pcmci_flow": "imagegen_priority_registry.py",
    "fig5_2_transfer_entropy": "batch25_beta_te_results_20261006.py",
    "fig5_3_asymmetry": "batch6_te_coverage_enhance.py",
    "fig5_4_te_vs_relations": "batch13_chapter4_5_extra.py",
    "fig5_5_pcmci_validation_network": "refine_requested_20260920.py",
    "fig5_6_conformal_method": "imagegen_priority_registry.py",
    "fig5_7_coverage": "batch6_te_coverage_enhance.py",
    "fig5_8_quantile_per_node": "batch9_advisor_redraw.py",
    "fig5_9_acn_current_shape": "fig5_9_acn_current_shape.py",
    "fig4_4_parameter_intervention": "batch5_restyle.py",
}

# 仅保留PNG的示意图：其余正式数据图登记SVG与PNG两种格式。
PNG_ONLY = {
    "fig5_1_te_pcmci_flow",
    "fig2_1_data_reconstruction",
    "fig2_12_jpl_validation_protocol",
    "fig3_6_gate_residual_detail",
    "fig3_7_cross_layer_detail",
    "fig4_1_three_layer_framework",
    "fig1_1_research_gap_map",
    "fig2_7_event_score_flow",
    "fig3_1_mrggcn_architecture",
    "fig3_2_relation_propagation_unit",
    "fig3_3_temporal_skip_fusion",
    "fig3_4_lre_construction",
    "fig3_8_train_predict_pipeline",
    "fig1_2_roadmap",
    "fig2_9_dual_window_definition",
    "fig5_6_conformal_method",
}

# 图 → 关键输入工件（存在性 + SHA 校验；glob 模式展开为匹配文件列表）
# 审查 H-13（2026-08-01）：fig3_1 数值硬编码于脚本，其数据源为正式三种子
# metrics.json（night_run/20260730-171821）；fig3_5/3_7 读取训练日志。
# 示意图（2026-08-04）：fig2_1/fig4_1/fig5_1（batch16）与 fig3_2（batch17）
# 为纯手工绘制的流程/架构示意图，无数据输入工件，登记空列表以通过
# --check-repository 的输入登记完整性检查。
INPUTS_BY_FIGURE = {
    "fig1_1_research_gap_map": [],
    "fig1_2_roadmap": [
        Path("docs/thesis/JPL-imagegen-diagrams-20261006.md"),
        Path("docs/thesis/JPL-imagegen-style-redraw-20261006.md"),
        Path("docs/thesis/roadmap-evaluation-grid-polish-20261006.md"),
        Path("docs/thesis/roadmap-four-stage-redesign-20261006.md"),
        Path("outputs/figures/fig1_2_roadmap_source.json"),
    ],
    "fig2_1_data_reconstruction": [
        Path("docs/thesis/flowchart-annotation-cleanup-20261006.md"),
        Path("outputs/figures/fig2_1_data_reconstruction_source.json"),
    ],
    "fig2_2_node_coverage": [Path("data/processed/SG-DATA-002-node-coverage-stability.csv")],
    "fig2_3_load_heatmap": [BUNDLE_PATH],
    "fig2_4_autocorrelation": [BUNDLE_PATH],
    "fig2_5_weekly_curves": [BUNDLE_PATH,
        Path("outputs/figures/fig2_5_weekly_curves_source.json"),
        Path("outputs/figures/fig2_5_weekly_curves_source.csv")],
    "fig2_6_load_distribution": [BUNDLE_PATH],
    "fig2_7_event_score_flow": [
        Path("docs/thesis/seven-figure-refresh-20261006-imagegen.json"),
        Path("outputs/figures/fig2_7_event_score_flow_source.json"),
    ],
    "fig2_8_event_hourly": [BUNDLE_PATH],
    "fig2_9_dual_window_definition": [
        Path("docs/thesis/flowchart-annotation-cleanup-20261006.md"),
        Path("outputs/figures/fig2_9_dual_window_definition_source.json"),
    ],
    "fig2_10_feature_correlation": [BUNDLE_PATH],
    "fig2_11_weekday_hour_heatmap": [BUNDLE_PATH],
    "fig2_12_jpl_validation_protocol": [
        Path("docs/thesis/JPL-imagegen-diagrams-20261006.md"),
        Path("docs/thesis/JPL-imagegen-style-redraw-20261006.md"),
        Path("docs/thesis/JPL-protocol-lifangning-layout-study-20261006.md"),
        Path("docs/thesis/flowchart-annotation-cleanup-20261006.md"),
        Path("outputs/figures/fig2_12_jpl_validation_protocol_source.json"),
        Path("docs/thesis/roadmap-evaluation-grid-polish-20261006.md"),
        Path("configs/data/SG-DATA-007-jpl-eventtime-v1.json"),
        Path("configs/experiments/SG-EXP-028-jpl-independent-site.json"),
        Path("docs/thesis/JPL-validation-freeze-20261005.json"),
        Path("docs/thesis/experiment-reports/SG-EXP-028-jpl-independent-site-validation-report.md"),
    ],
    "fig3_9_jpl_mae_primary": [
        Path("outputs/SG-EXP-028-analysis/per_seed.csv"),
        Path("outputs/SG-EXP-028-analysis/paired_intervals.csv"),
        Path("outputs/SG-EXP-028-analysis/model_summary.csv"),
    ],
    "fig3_10_jpl_stratified_mae": [
        Path("outputs/SG-EXP-028-analysis/per_seed.csv"),
        Path("outputs/SG-EXP-028-analysis/model_summary.csv"),
    ],
    "fig3_11_model_mae_comparison": [
        Path("outputs/analysis/traditional_baselines/formal_baselines_locked.json"),
        ("glob", "outputs/night_run/20260730-171821/SG-EXP-002/*/seed-*/metrics.json"),
        ("glob", "outputs/night_run/20260730-171821/SG-EXP-003/*/seed-*/metrics.json"),
        ("glob", "outputs/night_run/20260730-171821/SG-EXP-004/*/seed-*/metrics.json"),
        ("glob", "outputs/night_run/20260730-171821/SG-EXP-005/*/seed-*/metrics.json"),
        ("glob", "outputs/experiments/SG-EXP-008/*/seed-*/metrics.json"),
        ("glob", "outputs/experiments/SG-EXP-009/*/seed-*/metrics.json"),
        ("glob", "outputs/experiments/SG-EXP-010/*/seed-*/metrics.json"),
        ("glob", "outputs/experiments/SG-EXP-018/*/seed-*/metrics.json"),
    ],
    "fig3_1_mrggcn_architecture": [],
    "fig3_2_relation_propagation_unit": [],
    "fig3_3_temporal_skip_fusion": [],
    "fig3_4_lre_construction": [],
    "fig3_8_train_predict_pipeline": [
        Path("docs/thesis/seven-figure-refresh-20261006-imagegen.json"),
        Path("outputs/figures/fig3_8_train_predict_pipeline_source.json"),
    ],
    "fig3_5_lre_matrices": [BUNDLE_PATH,
        Path("outputs/experiments/SG-EXP-004/20260731-102456/relation_matrices.npz"),
        Path("outputs/experiments/SG-EXP-004/20260731-102456/manifest.json"),
        Path("outputs/figures/fig3_5_lre_matrices_alignment_audit.json"),
        Path("outputs/figures/fig3_5_lre_matrices_source.json"),
        Path("outputs/figures/fig3_5_lre_matrices_source.csv")],
    "fig3_12_mae_by_horizon": MAE_5_MODELS_INPUTS,
    "fig3_13_bootstrap_difference": [Path("outputs/analysis/bootstrap_significance.json")],
    "fig3_14_mae_by_window": MAE_5_MODELS_INPUTS,
    "fig3_15_mae_by_node": MAE_5_MODELS_INPUTS,
    "fig3_16_mechanism_ablation": [
        ("glob", "outputs/night_run/20260730-171821/SG-EXP-006/*/children/SG-EXP-006-ablation-*/*/seed-*/metrics.json"),
        ("glob", "outputs/experiments/SG-EXP-004/*/seed-*/metrics.json"),
    ],
    "fig3_17_proxy_label_stability": [
        Path("outputs/analysis/SG-ANA-20261026-proxy-stability/table3_16_spearman.csv"),
        Path("outputs/analysis/SG-ANA-20261026-proxy-stability/tableA2_rank_stability.csv"),
    ],
    "fig3_6_gate_residual_detail": [],
    "fig3_7_cross_layer_detail": [
        Path("docs/thesis/seven-figure-refresh-20261006-imagegen.json"),
        Path("outputs/figures/fig3_7_cross_layer_detail_source.json")],
    "fig4_1_three_layer_framework": [
        Path("docs/thesis/seven-figure-refresh-20261006-imagegen.json"),
        Path("outputs/figures/fig4_1_three_layer_framework_source.json")],
    "fig4_2_beta_profile": [
        Path("outputs/night_run/20260730-171821/SG-EXP-003/20260730-171821/seed-2024/model.pt"),
        Path("outputs/night_run/20260730-171821/SG-EXP-003/20260730-171821/seed-2025/model.pt"),
        Path("outputs/night_run/20260730-171821/SG-EXP-003/20260730-171821/seed-2026/model.pt"),
        Path("outputs/figures/fig4_2_beta_profile_source.csv"),
        Path("outputs/figures/fig4_2_beta_profile_source.json"),
    ],
    "fig4_3_intervention": [Path("outputs/analysis/gate_intervention/intervention_summary.json")],
    "fig4_5_four_cell": [
        Path("outputs/analysis/SG-EXP-020-legacy-evidence-v1/four_cell_summary.csv"),
        Path("outputs/analysis/SG-EXP-020-legacy-evidence-v1/four_cell_per_seed.csv"),
    ],
    "fig4_6_residual_distribution": [
        ("glob", "outputs/experiments/SG-EXP-009/*/seed-2024/predictions.csv.gz"),
        ("glob", "outputs/night_run/20260730-171821/SG-EXP-002/*/seed-2024/predictions.csv.gz"),
        ("glob", "outputs/night_run/20260730-171821/SG-EXP-003/*/seed-2024/predictions.csv.gz"),
    ],
    "fig4_7_error_vs_event_intensity": [Path("outputs/experiments/SG-EXP-004/20260731-102456/seed-2024/predictions.csv.gz")],
    "fig5_1_te_pcmci_flow": [
        Path("docs/thesis/seven-figure-refresh-20261006-imagegen.json"),
        Path("outputs/figures/fig5_1_te_pcmci_flow_source.json"),
        Path("outputs/analysis/transfer_entropy/transfer_entropy_summary.json"),
        Path("outputs/analysis/pcmci/pcmci_summary.json"),
    ],
    "fig5_2_transfer_entropy": [
        Path("outputs/analysis/transfer_entropy/transfer_entropy_summary.json"),
        Path("outputs/figures/fig5_2_transfer_entropy_source.csv"),
        Path("outputs/figures/fig5_2_transfer_entropy_source.json")],
    "fig5_3_asymmetry": [Path("outputs/analysis/transfer_entropy/transfer_entropy_summary.json")],
    "fig5_4_te_vs_relations": [
        Path("outputs/analysis/transfer_entropy/transfer_entropy_summary.json"),
        Path("outputs/experiments/SG-EXP-004/20260731-102456/relation_matrices.npz"),
    ],
    "fig5_5_pcmci_validation_network": [Path("outputs/analysis/pcmci/pcmci_summary.json")],
    "fig5_6_conformal_method": [],
    "fig5_7_coverage": [Path("outputs/analysis/conformal_prediction/conformal_summary.json")],
    "fig5_8_quantile_per_node": [Path("outputs/analysis/conformal_prediction/conformal_summary.json")],
    "fig5_9_acn_current_shape": [
        Path("docs/thesis/revision-20261025-practice/acn-current-shape-replay.json"),
        Path("outputs/figures/fig5_9_acn_current_shape_source.json"),
    ],
    "fig4_4_parameter_intervention": [
        Path("outputs/analysis/counterfactual_cate/counterfactual_cate_summary.json"),
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
        expected_formats = ("png",) if name in PNG_ONLY else ("svg", "png")
        for ext in expected_formats:
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
        sp = SCRIPT_DIR / script if script else None
        dependencies = list(INPUTS_BY_FIGURE.get(name, []))
        if script == "batch_priority_results.py":
            dependencies += [Path("scripts/figures") / p for p in (
                "batch5_restyle.py", "batch4_redraw.py", "batch11_chapter2_extra.py",
                "batch12_chapter3_extra.py", "batch13_chapter4_5_extra.py", "_skill_compat.py")]
            dependencies += [BUNDLE_PATH]
        if script == "imagegen_priority_registry.py":
            dependencies += [Path("outputs/figures/priority-review-20260907/imagegen_provenance.json"),
                             Path("src/evcs_station_graph/models/graph.py")]
        figures[name] = {
            "script": {
                "path": script,
                "sha256": sha256(sp) if sp and sp.is_file() else None,
            },
            "inputs": _expand_inputs(dependencies),
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
        expected_formats = ("png",) if name in PNG_ONLY else ("svg", "png")
        for ext in expected_formats:
            p = FIG_DIR / f"{name}.{ext}"
            cur = sha256(p) if p.is_file() else None
            if cur != info["formats"].get(ext, {}).get("sha256"):
                ok = False
                print(f"  ✗ {name}.{ext} SHA 不一致")
        script_path = info["script"].get("path")
        if script_path:
            sp = SCRIPT_DIR / script_path
            if not sp.is_file() or sha256(sp) != info["script"]["sha256"]:
                ok = False
                print(f"  ✗ 脚本 {script_path} 缺失或已变化")
        # 示意图（batch16/17）合法地无输入工件（INPUTS_BY_FIGURE 登记空列表）；
        # 此处检查"是否已登记"而非"是否非空"，防漏登记。
        if name not in INPUTS_BY_FIGURE:
            ok = False
            print(f"  ✗ {name} 未在 INPUTS_BY_FIGURE 登记输入工件")
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
        expected_formats = ("png",) if name in PNG_ONLY else ("svg", "png")
        for ext in expected_formats:
            p = FIG_DIR / f"{name}.{ext}"
            cur = sha256(p) if p.is_file() else None
            recorded = info["formats"].get(ext, {}).get("sha256")
            if cur != recorded:
                ok = False
                print(f"  ✗ {name}.{ext}: 当前 {cur} ≠ manifest {recorded}")
        script_path = info["script"].get("path")
        if script_path:
            sp = SCRIPT_DIR / script_path
            cur_s = sha256(sp) if sp.is_file() else None
            if cur_s != info["script"]["sha256"]:
                ok = False
                print(f"  ✗ 脚本 {script_path} 已变化")
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
