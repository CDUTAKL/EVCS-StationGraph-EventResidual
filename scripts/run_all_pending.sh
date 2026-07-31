#!/usr/bin/env bash
# 一次性批量跑完所有待跑训练（2026-07-31 批量）
# 卡 0：SG-EXP-006 补齐（relations 3 + dropout 2）→ AGCRN → napl/gate-mi 3 种子
# 卡 1：topk 敏感性（5/7）→ EERM（15 次）→ GRU 3 种子
# CPU（并行后台）：传统基线见 run_traditional_baselines.py（由本脚本末尾挂起）
# 用法（服务器）：bash scripts/run_all_pending.sh > outputs/analysis/batch_run.log 2>&1 &

set -u
cd /root/EVCS-StationGraph-EventResidual || exit 1
export PYTHONPATH=src
LOG_DIR="outputs/analysis/batch_run_$(date +%Y%m%d-%H%M)"
mkdir -p "$LOG_DIR"

run_variant_yaml() {
  # run_variant_yaml <yaml 名> <GPU>
  # 服务器未装 evcs-sg console script（setuptools 版本限制），用 python -m 等价调用
  local yaml=$1 gpu=$2
  echo "==> [$(date +%H:%M)] GPU$gpu: $yaml 启动"
  CUDA_VISIBLE_DEVICES=$gpu .venv/bin/python -m evcs_station_graph.cli run \
    --project configs/project.yaml --experiment "configs/experiments/batch/$yaml.yaml" \
    > "$LOG_DIR/$yaml.log" 2>&1
  echo "==> [$(date +%H:%M)] GPU$gpu: $yaml 退出码 $?"
}

run_variant_script() {
  # run_variant_script <变体名> <GPU> <输出目录>
  local variant=$1 gpu=$2 outdir=$3
  echo "==> [$(date +%H:%M)] GPU$gpu: $variant 3 种子启动"
  for s in 2024 2025 2026; do
    CUDA_VISIBLE_DEVICES=$gpu .venv/bin/python scripts/validate_variant_single_seed.py \
      --variant "$variant" --seed "$s" --output-dir "$outdir" \
      >> "$LOG_DIR/$variant.log" 2>&1
  done
  echo "==> [$(date +%H:%M)] GPU$gpu: $variant 完成"
}

# ===== 卡 0 队列 =====
(
  for v in relation-load relation-event relation-pattern dropout-0p2 dropout-0p4; do
    run_variant_yaml "$v" 0
  done
  echo "==> [$(date +%H:%M)] GPU0: AGCRN 3 种子启动"
  CUDA_VISIBLE_DEVICES=0 .venv/bin/python -m evcs_station_graph.cli run \
    --project configs/project.yaml --experiment configs/experiments/SG-EXP-008-agcrn-baseline.yaml \
    > "$LOG_DIR/agcrn.log" 2>&1
  echo "==> [$(date +%H:%M)] GPU0: AGCRN 退出码 $?"
  run_variant_script napl 0 outputs/analysis/batch_napl
  run_variant_script gate-mi 0 outputs/analysis/batch_gate_mi
) &
Q0=$!

# ===== 卡 1 队列 =====
(
  for v in topk-5 topk-7; do
    run_variant_yaml "$v" 1
  done
  echo "==> [$(date +%H:%M)] GPU1: EERM 15 次启动"
  CUDA_VISIBLE_DEVICES=1 .venv/bin/python scripts/run_eerm_invariant.py \
    --project configs/project.yaml --output-root outputs/experiments/SG-EXP-014 \
    > "$LOG_DIR/eerm.log" 2>&1
  echo "==> [$(date +%H:%M)] GPU1: EERM 退出码 $?"
  run_variant_script gru 1 outputs/analysis/batch_gru
) &
Q1=$!

# ===== CPU 后台：传统基线（若脚本存在） =====
if [ -f scripts/run_traditional_baselines.py ]; then
  echo "==> [$(date +%H:%M)] CPU: 传统基线后台启动"
  .venv/bin/python scripts/run_traditional_baselines.py > "$LOG_DIR/traditional.log" 2>&1 &
  QC=$!
else
  QC=""
fi

wait $Q0 $Q1
[ -n "$QC" ] && wait $QC
echo "===== 全部完成 [$(date +%H:%M)] ====="
