#!/bin/bash
# SG-EXP-006 relations 套件：备份 temporal-base 旧结果 → 清理残留 → 全量重跑（adaptive base 同构口径）
set -e
cd /root/EVCS-StationGraph-EventResidual
# 1. 备份 temporal-base 口径的 relations 结果（口径作废，保留追溯）
BK=/root/outputs/relations_temporal_base_backup
mkdir -p "$BK"
for v in relation-load relation-event relation-pattern relation-all; do
  d="outputs/experiments/SG-EXP-006/20260803-113723/children/SG-EXP-006-$v"
  if [ -d "$d" ]; then
    rm -rf "$BK/SG-EXP-006-$v"
    cp -r "$d" "$BK/"
    rm -rf "$d"
    echo "备份并移除 $v"
  fi
done
# 2. 清理 topk-5 残留空种子
rm -rf outputs/experiments/SG-EXP-006/20260803-113723/children/SG-EXP-006-topk-5/20260803-113723/seed-2024
echo "已清理 topk-5 空种子"
# 3. 启动全量重跑（8 变体 × 3 种子，adaptive base 同构口径）
export PYTHONPATH=/root/EVCS-StationGraph-EventResidual/src
CUDA_VISIBLE_DEVICES=1 setsid nohup .venv/bin/python scripts/resume_mechanism_suite.py > /root/outputs/sg_exp_006_relations_resume.log 2>&1 < /dev/null &
echo "PID=$!"
sleep 15
echo "===日志==="
head -40 /root/outputs/sg_exp_006_relations_resume.log
echo "===进程==="
ps aux | grep resume_mechanism | grep -v grep
