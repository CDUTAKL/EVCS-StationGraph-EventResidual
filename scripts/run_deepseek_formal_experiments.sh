#!/usr/bin/env bash
#
# DeepSeek 正式执行入口。
#
# 默认不会关机。仅在云实例中显式设置 AUTO_SHUTDOWN=1 时，才会在成功生成
# 完整证据后尝试关机。任何失败都会保留日志并返回非零状态。

set -Eeuo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${PROJECT_ROOT}"

RUN_TAG="$(date -u +%Y%m%d-%H%M%S)"
CONTROL_ROOT="${PROJECT_ROOT}/outputs/executor-runs/${RUN_TAG}"
LOG_FILE="${CONTROL_ROOT}/formal_execution.log"
mkdir -p "${CONTROL_ROOT}"

PYTHON="${PROJECT_ROOT}/.venv/bin/python"
PYTEST="${PROJECT_ROOT}/.venv/bin/pytest"
CLI="${PROJECT_ROOT}/.venv/bin/evcs-sg"
DATASET="${PROJECT_ROOT}/data/processed/SG-DATA-005-primary-tensor.npz"
AUTO_SHUTDOWN="${AUTO_SHUTDOWN:-0}"

exec > >(tee -a "${LOG_FILE}") 2>&1

START_UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
PIPELINE_ROOT=""

write_control_summary() {
  local exit_code="$1"
  {
    echo "run_tag=${RUN_TAG}"
    echo "start_utc=${START_UTC}"
    echo "end_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "exit_code=${exit_code}"
    echo "pipeline_root=${PIPELINE_ROOT}"
    echo "auto_shutdown=${AUTO_SHUTDOWN}"
  } > "${CONTROL_ROOT}/execution_status.txt"
}

on_exit() {
  local exit_code=$?
  write_control_summary "${exit_code}"
  if [[ "${exit_code}" -ne 0 ]]; then
    echo "正式执行失败，已保留日志：${LOG_FILE}"
  fi
}
trap on_exit EXIT

echo "开始 DeepSeek 正式执行：${START_UTC}"
echo "项目根目录：${PROJECT_ROOT}"

if [[ ! -x "${PYTHON}" || ! -x "${CLI}" || ! -x "${PYTEST}" ]]; then
  echo "缺少 .venv 或项目命令。请先执行：python3.11 -m venv .venv && .venv/bin/pip install -e '.[dev]'"
  exit 10
fi

"${PYTHON}" - <<'PY' | tee "${CONTROL_ROOT}/torch_environment.txt"
import json
import platform
import sys
import torch

info = {
    "python": sys.version,
    "platform": platform.platform(),
    "torch": torch.__version__,
    "cuda_available": torch.cuda.is_available(),
    "cuda_version": torch.version.cuda,
    "device_count": torch.cuda.device_count(),
    "devices": [
        {
            "index": index,
            "name": torch.cuda.get_device_name(index),
            "total_memory_gib": round(
                torch.cuda.get_device_properties(index).total_memory / 1024**3, 3
            ),
        }
        for index in range(torch.cuda.device_count())
    ],
}
print(json.dumps(info, ensure_ascii=False, indent=2))
if not torch.cuda.is_available():
    raise SystemExit("正式 GPU 实验要求 CUDA 可用；已中止，避免误用 CPU。")
PY

if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi | tee "${CONTROL_ROOT}/nvidia-smi.txt"
fi
"${PYTHON}" -m pip freeze > "${CONTROL_ROOT}/python-packages.txt"
uname -a > "${CONTROL_ROOT}/system.txt"

if [[ ! -f "${DATASET}" ]]; then
  echo "未找到正式节点张量，按冻结项目配置构建。"
  "${CLI}" prepare-data \
    --project configs/project.yaml \
    --output "${DATASET}" \
    --metadata data/manifests/SG-DATA-005-primary-tensor.json
fi

echo "执行自动化测试和语法检查。"
"${PYTEST}" -q
"${PYTHON}" -m compileall -q src tests scripts/summarize_formal_results.py

echo "执行 SG-EXP-002～006 正式三随机种子流水线。"
"${CLI}" run-pipeline \
  --project configs/project.yaml \
  --suite configs/experiments/SG-EXP-006-mechanism.yaml \
  --output-root outputs/formal

PIPELINE_ROOT="$(
  find "${PROJECT_ROOT}/outputs/formal/SG-PIPELINE-002-006" \
    -mindepth 1 -maxdepth 1 -type d -print 2>/dev/null | sort | tail -1
)"
if [[ -z "${PIPELINE_ROOT}" ]]; then
  echo "未找到正式流水线目录。"
  exit 20
fi

echo "生成执行阶段自动摘要：${PIPELINE_ROOT}"
"${PYTHON}" scripts/summarize_formal_results.py "${PIPELINE_ROOT}" \
  | tee "${CONTROL_ROOT}/automatic_summary_stdout.json"

echo "生成产物校验和。"
find "${PIPELINE_ROOT}" -type f -print0 \
  | sort -z \
  | xargs -0 shasum -a 256 > "${CONTROL_ROOT}/pipeline_sha256.txt"
shasum -a 256 "${DATASET}" > "${CONTROL_ROOT}/dataset_sha256.txt"

cp "${PIPELINE_ROOT}/automatic_result_summary.json" "${CONTROL_ROOT}/"
cp "${PIPELINE_ROOT}/automatic_result_summary.md" "${CONTROL_ROOT}/"
cp "${PIPELINE_ROOT}/artifact_validation_report.json" "${CONTROL_ROOT}/"
cp "${PIPELINE_ROOT}/pipeline_manifest.json" "${CONTROL_ROOT}/"

write_control_summary 0
trap - EXIT
echo "正式执行与证据留档完成。"
echo "控制目录：${CONTROL_ROOT}"
echo "流水线目录：${PIPELINE_ROOT}"

if [[ "${AUTO_SHUTDOWN}" == "1" ]]; then
  echo "AUTO_SHUTDOWN=1，准备关闭云实例。"
  sync
  if command -v shutdown >/dev/null 2>&1; then
    shutdown -h now
  else
    echo "系统缺少 shutdown 命令，请执行方在平台控制台关机。"
    exit 30
  fi
fi
