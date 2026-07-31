#!/usr/bin/env bash
# 第二轮批量（2026-07-31）：修复 evcs-sg 入口缺失 + EERM 越界 bug 后的重跑
# 仅含第一轮失败的任务（napl/gru 已成功，不重跑）
# 卡 0：relations 3 + dropout 2 + AGCRN；卡 1：topk 2 + EERM 15 次
set -u
cd /root/EVCS-StationGraph-EventResidual || exit 1
export PYTHONPATH=src
LOG_DIR="outputs/analysis/batch_run2_$(date +%Y%m%d-%H%M)"
mkdir -p "$LOG_DIR"

run_variant_yaml() {
  local yaml=$1 gpu=$2
  echo "==> [$(date +%H:%M)] GPU$gpu: $yaml 启动"
  CUDA_VISIBLE_DEVICES=$gpu .venv/bin/python -m evcs_station_graph.cli run \
    --project configs/project.yaml --experiment "configs/experiments/batch/$yaml.yaml" \
    > "$LOG_DIR/$yaml.log" 2>&1
  echo "==> [$(date +%H:%M)] GPU$gpu: $yaml 退出码 $?"
}

(
  for v in relation-load relation-event relation-pattern dropout-0p2 dropout-0p4; do
    run_variant_yaml "$v" 0
  done
  echo "==> [$(date +%H:%M)] GPU0: AGCRN 3 种子启动"
  CUDA_VISIBLE_DEVICES=0 .venv/bin/python -m evcs_station_graph.cli run \
    --project configs/project.yaml --experiment configs/experiments/SG-EXP-008-agcrn-baseline.yaml \
    > "$LOG_DIR/agcrn.log" 2>&1
  echo "==> [$(date +%H:%M)] GPU0: AGCRN 退出码 $?"
) &
Q0=$!

(
  for v in topk-5 topk-7; do
    run_variant_yaml "$v" 1
  done
  echo "==> [$(date +%H:%M)] GPU1: EERM 15 次启动"
  CUDA_VISIBLE_DEVICES=1 .venv/bin/python scripts/run_eerm_invariant.py \
    --project configs/project.yaml --output-root outputs/experiments/SG-EXP-014 \
    > "$LOG_DIR/eerm.log" 2>&1
  echo "==> [$(date +%H:%M)] GPU1: EERM 退出码 $?"
) &
Q1=$!

wait $Q0 $Q1
echo "===== 第二轮全部完成 [$(date +%H:%M)] ====="
