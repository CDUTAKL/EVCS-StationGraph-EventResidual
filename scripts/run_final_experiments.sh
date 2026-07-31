#!/bin/bash
# SG-EXP-011~014 + D5-1 一次性全量夜跑（双 GPU 并行）
#
# GPU 0 (约 14h):
#   SG-EXP-011  DecompGCN one_to_one 主实验（3 种子）
#   SG-EXP-012a 路由消融 full（3 种子）
#   SG-EXP-012b 路由消融 swapped（3 种子）
#
# GPU 1 (约 9h):
#   SG-EXP-013  GCN→TCN 知识蒸馏（4α×3种子）
#   SG-EXP-014  EERM 不变学习（5λ×3种子）
#
# 用法：bash scripts/run_final_experiments.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

export PYTHONPATH="${PROJECT_DIR}/src:${PYTHONPATH:-}"

RUN_TAG="$(date +%Y%m%d-%H%M%S)"
LOG_DIR="outputs/final_night_run/${RUN_TAG}/logs"
mkdir -p "$LOG_DIR"

VENV_PYTHON=".venv/bin/python"
PROJECT="configs/project.yaml"
DATASET="data/processed/SG-DATA-005-primary-tensor.npz"

# 查找 SG-EXP-003 最新结果（供 KD 教师使用）
TEACHER_ROOT=""
for candidate_base in "outputs/experiments/SG-EXP-003" "outputs/night_run"; do
    if [ -d "$candidate_base" ]; then
        if [[ "$candidate_base" == *"night_run"* ]]; then
            for nd in "$candidate_base"/*/; do
                sg_dir="${nd}SG-EXP-003"
                if [ -d "$sg_dir" ]; then
                    TEACHER_ROOT=$(ls -dt "$sg_dir"/*/ 2>/dev/null | head -1)
                    [ -n "$TEACHER_ROOT" ] && break 2
                fi
            done
        else
            TEACHER_ROOT=$(ls -dt "$candidate_base"/*/ 2>/dev/null | head -1)
            [ -n "$TEACHER_ROOT" ] && break
        fi
    fi
done

if [ -z "$TEACHER_ROOT" ]; then
    echo "错误：未找到 SG-EXP-003 StaticGraph 结果。"
    echo "请先运行 SG-EXP-003 或设置 TEACHER_ROOT 环境变量。"
    exit 1
fi

echo "============================================"
echo "全量夜跑：SG-EXP-011 ~ 014 + D5-1"
echo "运行标签：${RUN_TAG}"
echo "教师模型：${TEACHER_ROOT}"
echo "日志目录：${LOG_DIR}"
echo "PYTHONPATH：${PYTHONPATH}"
echo "============================================"
echo ""

# 验证 Python 导入
$VENV_PYTHON -c "
from evcs_station_graph.models.decomp_gcn import DecompGCNForecast
from evcs_station_graph.training import train_experiment
print('模块导入验证通过')
" || { echo "模块导入失败，终止"; exit 1; }

# ============================================
# GPU 0: SG-EXP-011 → SG-EXP-012a → SG-EXP-012b
# ============================================
(
    export CUDA_VISIBLE_DEVICES=0
    export PYTHONPATH="${PROJECT_DIR}/src:${PYTHONPATH:-}"

    echo "=== [GPU 0] SG-EXP-011 DecompGCN one_to_one 主实验 ==="
    $VENV_PYTHON -m evcs_station_graph.cli run \
        --project "$PROJECT" \
        --experiment configs/experiments/SG-EXP-011-decomp-gcn.yaml \
        > "$LOG_DIR/sg_exp_011.log" 2>&1
    echo "[GPU 0] SG-EXP-011 完成 (exit=$?)"

    echo "=== [GPU 0] SG-EXP-012a 路由消融 full ==="
    $VENV_PYTHON -m evcs_station_graph.cli run \
        --project "$PROJECT" \
        --experiment configs/experiments/SG-EXP-012a-routing-full.yaml \
        > "$LOG_DIR/sg_exp_012a.log" 2>&1
    echo "[GPU 0] SG-EXP-012a 完成 (exit=$?)"

    echo "=== [GPU 0] SG-EXP-012b 路由消融 swapped ==="
    $VENV_PYTHON -m evcs_station_graph.cli run \
        --project "$PROJECT" \
        --experiment configs/experiments/SG-EXP-012b-routing-swapped.yaml \
        > "$LOG_DIR/sg_exp_012b.log" 2>&1
    echo "[GPU 0] SG-EXP-012b 完成 (exit=$?)"

    echo "[GPU 0] 全部完成"
) &
PID_GPU0=$!

# ============================================
# GPU 1: SG-EXP-013 KD → SG-EXP-014 EERM
# ============================================
(
    export CUDA_VISIBLE_DEVICES=1
    export PYTHONPATH="${PROJECT_DIR}/src:${PYTHONPATH:-}"

    echo "=== [GPU 1] SG-EXP-013 GCN→TCN 知识蒸馏 ==="
    $VENV_PYTHON scripts/run_knowledge_distillation.py \
        --project "$PROJECT" \
        --teacher-root "$TEACHER_ROOT" \
        --output-root outputs/experiments/SG-EXP-013 \
        > "$LOG_DIR/sg_exp_013_kd.log" 2>&1
    echo "[GPU 1] SG-EXP-013 完成 (exit=$?)"

    echo "=== [GPU 1] SG-EXP-014 EERM 环境不变学习 ==="
    $VENV_PYTHON scripts/run_eerm_invariant.py \
        --project "$PROJECT" \
        --output-root outputs/experiments/SG-EXP-014 \
        > "$LOG_DIR/sg_exp_014_eerm.log" 2>&1
    echo "[GPU 1] SG-EXP-014 完成 (exit=$?)"

    echo "[GPU 1] 全部完成"
) &
PID_GPU1=$!

# ============================================
# 等待双 GPU 完成
# ============================================
echo ""
echo "GPU 0 PID: $PID_GPU0"
echo "GPU 1 PID: $PID_GPU1"
echo ""
echo "等待双 GPU 实验完成..."
echo "监控命令:"
echo "  tail -f $LOG_DIR/sg_exp_011.log"
echo "  tail -f $LOG_DIR/sg_exp_013_kd.log"
echo ""

wait $PID_GPU0
RET0=$?
wait $PID_GPU1
RET1=$?

echo ""
echo "============================================"
echo "GPU 实验全部完成"
echo "GPU 0 exit=$RET0"
echo "GPU 1 exit=$RET1"
echo "============================================"

# ============================================
# D5-1: Gate 可解释性分析（CPU，GPUs 空闲后执行）
# ============================================
echo ""
echo "=== [CPU] D5-1 Gate 可解释性分析 ==="
$VENV_PYTHON scripts/analyze_gate_interpretability.py \
    --sg003-root "$TEACHER_ROOT" \
    > "$LOG_DIR/d5_1_gate_analysis.log" 2>&1
echo "[CPU] D5-1 完成 (exit=$?)"

echo ""
echo "============================================"
echo "全量夜跑完成！"
echo "工件目录：outputs/experiments/SG-EXP-011~014/"
echo "Gate 分析：outputs/analysis/gate_interpretability/"
echo "日志目录：${LOG_DIR}"
echo "============================================"
