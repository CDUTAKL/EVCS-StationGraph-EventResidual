#!/usr/bin/env bash
#
# SG-EXP-002～006 正式实验入口。
#
# 该脚本会先执行自动化测试，再依次训练三随机种子的时间基线、固定图、
# 自适应图、事件残差修正模型，并运行消融、敏感性与四格诊断。
# 正式运行耗时较长；中途退出不会把不完整目录标记为正式结果。

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${PROJECT_ROOT}"

PYTHON="${PROJECT_ROOT}/.venv/bin/python"
PYTEST="${PROJECT_ROOT}/.venv/bin/pytest"
CLI="${PROJECT_ROOT}/.venv/bin/evcs-sg"
DATASET="${PROJECT_ROOT}/data/processed/SG-DATA-005-primary-tensor.npz"

if [[ ! -x "${PYTHON}" || ! -x "${CLI}" ]]; then
  echo "未找到项目虚拟环境，请先在项目根目录安装开发依赖。"
  exit 1
fi

if [[ ! -f "${DATASET}" ]]; then
  echo "未找到正式节点张量，开始从项目配置构建。"
  "${CLI}" prepare-data \
    --project configs/project.yaml \
    --output "${DATASET}" \
    --metadata data/manifests/SG-DATA-005-primary-tensor.json
fi

echo "执行自动化测试与语法检查。"
"${PYTEST}" -q
"${PYTHON}" -m compileall -q src tests

echo "运行 SG-EXP-002～006 正式三随机种子流水线。"
"${CLI}" run-pipeline \
  --project configs/project.yaml \
  --suite configs/experiments/SG-EXP-006-mechanism.yaml \
  --output-root outputs/formal

echo "正式流水线结束。请以 artifact_validation_report.json 的 formal_ready=true 为准。"
