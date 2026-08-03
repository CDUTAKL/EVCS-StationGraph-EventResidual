#!/bin/bash
# 005 持平牌变体 V3：触发阈值 0.95→0.97 + 残差 bound 0.5→0.3
# 目标：减少格 3 误修正样本，全局回到 ≈0.0138（与 StaticGraph 持平）
set -e
cd /root/EVCS-StationGraph-EventResidual
export PYTHONPATH=/root/EVCS-StationGraph-EventResidual/src
CUDA_VISIBLE_DEVICES=0 setsid nohup .venv/bin/python -m evcs_station_graph.cli run \
  --project configs/project.yaml \
  --experiment configs/experiments/SG-EXP-005-event-residual.yaml \
  --set experiment.experiment_id=SG-EXP-005-v3-threshold-bounded \
  --set dataset.event.trigger_quantile=0.97 \
  --set experiment.model_params.residual_bound=0.3 \
  --base-checkpoint outputs/night_run/20260730-171821/SG-EXP-005/20260730-171821 \
  > /root/outputs/v3_threshold_bounded.log 2>&1 < /dev/null &
echo "GPU0 V3 PID=$!"
sleep 15
echo "===V3 日志==="
head -15 /root/outputs/v3_threshold_bounded.log
echo "===进程==="
ps aux | grep "v3-threshold" | grep -v grep
