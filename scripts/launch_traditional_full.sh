#!/usr/bin/env bash
# CPU 后台：传统基线全量（Persistence/ARIMA/LightGBM/XGBoost，新版代码）
set -u
cd /root/EVCS-StationGraph-EventResidual || exit 1
export PYTHONPATH=src
mkdir -p outputs/analysis/traditional_full
.venv/bin/python scripts/run_traditional_baselines.py \
  > outputs/analysis/traditional_full/traditional_full.log 2>&1
echo "==> [$(date +%H:%M)] 传统基线全量退出码 $?"
