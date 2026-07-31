#!/usr/bin/env bash
# 卡 0 队列：等待 gate-mi 最后种子结束 → relations 3 + dropout 2 → AGCRN 3 种子
set -u
cd /root/EVCS-StationGraph-EventResidual || exit 1
export PYTHONPATH=src
LOG_DIR="outputs/analysis/batch_run2_gpu0"
mkdir -p "$LOG_DIR"
echo "==> [$(date +%H:%M)] 等待 gate-mi 释放卡 0..."
for i in $(seq 1 120); do
  n=$(ps aux | grep "validate_variant_single_seed.py --variant gate-mi" | grep -v grep | wc -l)
  [ "$n" -eq 0 ] && break
  sleep 30
done
echo "==> [$(date +%H:%M)] gate-mi 已结束，卡 0 队列启动"
for v in relation-load relation-event relation-pattern dropout-0p2 dropout-0p4; do
  echo "==> [$(date +%H:%M)] GPU0: $v 启动"
  CUDA_VISIBLE_DEVICES=0 .venv/bin/python -m evcs_station_graph.cli run \
    --project configs/project.yaml --experiment "configs/experiments/batch/$v.yaml" \
    > "$LOG_DIR/$v.log" 2>&1
  echo "==> [$(date +%H:%M)] GPU0: $v 退出码 $?"
done
echo "==> [$(date +%H:%M)] GPU0: AGCRN 3 种子启动"
CUDA_VISIBLE_DEVICES=0 .venv/bin/python -m evcs_station_graph.cli run \
  --project configs/project.yaml --experiment configs/experiments/SG-EXP-008-agcrn-baseline.yaml \
  > "$LOG_DIR/agcrn.log" 2>&1
echo "==> [$(date +%H:%M)] GPU0: AGCRN 退出码 $?"
echo "===== GPU0 队列全部完成 [$(date +%H:%M)] ====="
