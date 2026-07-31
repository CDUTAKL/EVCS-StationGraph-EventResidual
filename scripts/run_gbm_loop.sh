#!/usr/bin/env bash
# GBM 40 模型逐进程编排（规避 macOS LightGBM 连续训练段错误）
# 用法（后台）：bash scripts/run_gbm_loop.sh > outputs/analysis/traditional_gbm_loop.log 2>&1 &
set -u
cd /Users/xushuyuan/Documents/Codex/EVCS-StationGraph-EventResidual || exit 1
export PYTHONPATH=src
OUT="outputs/analysis/traditional_baselines"
for model in LightGBM XGBoost; do
  for n in $(seq 0 9); do
    for h in $(seq 0 3); do
      .venv/bin/python scripts/run_gbm_worker.py "$model" "$n" "$h" "$OUT" || echo "FAILED $model n=$n h=$h"
    done
  done
done
echo "===== GBM 40 模型全部完成 [$(date +%H:%M)] ====="
