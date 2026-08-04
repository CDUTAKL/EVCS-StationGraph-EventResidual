#!/bin/bash
# SG-EXP-018 GRU 三种子正式实验（2026-08-04 补跑）
# 双卡并行：GPU0 → seed-2024（完成后顺延 seed-2026）；GPU1 → seed-2025
set -e
cd /root/EVCS-StationGraph-EventResidual
export PYTHONPATH=/root/EVCS-StationGraph-EventResidual/src

CUDA_VISIBLE_DEVICES=0 setsid nohup bash -c '
  export PYTHONPATH=/root/EVCS-StationGraph-EventResidual/src
  cd /root/EVCS-StationGraph-EventResidual
  .venv/bin/python -m evcs_station_graph.cli run \
    --project configs/project.yaml \
    --experiment configs/experiments/SG-EXP-018-gru-baseline.yaml \
    --set experiment.seeds=[2024] \
    > /root/outputs/sg_018_seed_2024.log 2>&1
  .venv/bin/python -m evcs_station_graph.cli run \
    --project configs/project.yaml \
    --experiment configs/experiments/SG-EXP-018-gru-baseline.yaml \
    --set experiment.seeds=[2026] \
    > /root/outputs/sg_018_seed_2026.log 2>&1
' > /dev/null 2>&1 < /dev/null &
echo "GPU0 seed-2024/2026 PID=$!"

CUDA_VISIBLE_DEVICES=1 setsid nohup bash -c '
  export PYTHONPATH=/root/EVCS-StationGraph-EventResidual/src
  cd /root/EVCS-StationGraph-EventResidual
  .venv/bin/python -m evcs_station_graph.cli run \
    --project configs/project.yaml \
    --experiment configs/experiments/SG-EXP-018-gru-baseline.yaml \
    --set experiment.seeds=[2025] \
    > /root/outputs/sg_018_seed_2025.log 2>&1
' > /dev/null 2>&1 < /dev/null &
echo "GPU1 seed-2025 PID=$!"

sleep 15
echo "=== seed-2024 日志 ==="
head -15 /root/outputs/sg_018_seed_2024.log
echo "=== 进程 ==="
ps aux | grep "SG-EXP-018" | grep -v grep
