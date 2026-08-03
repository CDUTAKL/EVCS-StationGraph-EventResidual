#!/bin/bash
# SG-EXP-006 双卡并行：中断串行主进程 → 清理 topk-5 半成品 → 双卡并行剩余 4 变体
set -e
cd /root/EVCS-StationGraph-EventResidual
export PYTHONPATH=/root/EVCS-StationGraph-EventResidual/src
# 1. 中断串行主进程（topk-5 seed-2024 半成品将被清理）
pkill -f resume_mechanism_suite || true
sleep 2
# 2. 清理 topk-5 半成品（并行进程将从头训练）
rm -rf outputs/experiments/SG-EXP-006/20260803-113723/children/SG-EXP-006-topk-5
echo "已清理 topk-5 半成品"
# 3. 双卡并行：GPU0 → topk-5,topk-7；GPU1 → dropout-0p2,dropout-0p4
CUDA_VISIBLE_DEVICES=0 setsid nohup .venv/bin/python scripts/resume_partial.py --variants topk-5,topk-7 > /root/outputs/par_gpu0.log 2>&1 < /dev/null &
P0=$!
CUDA_VISIBLE_DEVICES=1 setsid nohup .venv/bin/python scripts/resume_partial.py --variants dropout-0p2,dropout-0p4 > /root/outputs/par_gpu1.log 2>&1 < /dev/null &
P1=$!
echo "GPU0 PID=$P0（topk-5, topk-7）"
echo "GPU1 PID=$P1（dropout-0p2, dropout-0p4）"
sleep 20
echo "===GPU0 日志==="
head -20 /root/outputs/par_gpu0.log
echo "===GPU1 日志==="
head -20 /root/outputs/par_gpu1.log
echo "===进程==="
ps aux | grep resume_partial | grep -v grep
