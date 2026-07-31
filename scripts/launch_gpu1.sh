#!/usr/bin/env bash
# 卡 1 队列：topk 敏感性（5/7）→ EERM 15 次（立即启动，卡 1 空闲）
set -u
cd /root/EVCS-StationGraph-EventResidual || exit 1
export PYTHONPATH=src
LOG_DIR="outputs/analysis/batch_run2_gpu1"
mkdir -p "$LOG_DIR"
for v in topk-5 topk-7; do
  echo "==> [$(date +%H:%M)] GPU1: $v 启动"
  CUDA_VISIBLE_DEVICES=1 .venv/bin/python -m evcs_station_graph.cli run \
    --project configs/project.yaml --experiment "configs/experiments/batch/$v.yaml" \
    > "$LOG_DIR/$v.log" 2>&1
  echo "==> [$(date +%H:%M)] GPU1: $v 退出码 $?"
done
echo "==> [$(date +%H:%M)] GPU1: EERM 15 次启动"
CUDA_VISIBLE_DEVICES=1 .venv/bin/python scripts/run_eerm_invariant.py \
  --project configs/project.yaml --output-root outputs/experiments/SG-EXP-014 \
  > "$LOG_DIR/eerm.log" 2>&1
echo "==> [$(date +%H:%M)] GPU1: EERM 退出码 $?"
echo "===== GPU1 队列全部完成 [$(date +%H:%M)] ====="
