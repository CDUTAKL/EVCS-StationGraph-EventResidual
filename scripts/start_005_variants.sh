#!/bin/bash
# 005 翻身变体双卡并行：GPU0 → V1 联合微调；GPU1 → V2 联合微调+容量放大
set -e
cd /root/EVCS-StationGraph-EventResidual
export PYTHONPATH=/root/EVCS-StationGraph-EventResidual/src
CUDA_VISIBLE_DEVICES=0 setsid nohup .venv/bin/python -m evcs_station_graph.cli run \
  --project configs/project.yaml \
  --experiment configs/experiments/SG-EXP-005-v1-unfreeze.yaml \
  > /root/outputs/v1_unfreeze.log 2>&1 < /dev/null &
echo "GPU0 V1 PID=$!"
CUDA_VISIBLE_DEVICES=1 setsid nohup .venv/bin/python -m evcs_station_graph.cli run \
  --project configs/project.yaml \
  --experiment configs/experiments/SG-EXP-005-v2-unfreeze-big.yaml \
  > /root/outputs/v2_unfreeze_big.log 2>&1 < /dev/null &
echo "GPU1 V2 PID=$!"
sleep 15
echo "===V1 日志==="
head -15 /root/outputs/v1_unfreeze.log
echo "===V2 日志==="
head -15 /root/outputs/v2_unfreeze_big.log
echo "===进程==="
ps aux | grep -E "v1-unfreeze|v2-unfreeze" | grep -v grep
