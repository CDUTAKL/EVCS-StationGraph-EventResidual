#!/bin/bash
# 夜跑结果快速检查脚本
# 用法：bash scripts/check_night_run.sh
# 前提：SSH 密钥已配置（~/.ssh/claude_code_server）

SERVER="root@10.14.92.65"
SSH_KEY="~/.ssh/claude_code_server"
PROJECT_DIR="/root/EVCS-StationGraph-EventResidual"

echo "========================================"
echo "  SG-EXP-002~006 夜跑结果检查"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================"
echo

# ── 1. 检查服务器连接 ──
echo "▶ [1/6] 服务器连接..."
ssh -i ~/.ssh/claude_code_server -o ConnectTimeout=5 root@10.14.92.65 'echo "  ✓ 连接成功"' 2>/dev/null
if [ $? -ne 0 ]; then
  echo "  ✗ 无法连接服务器 10.14.92.65"
  exit 1
fi
echo

# ── 2. 检查夜跑进程是否还在运行 ──
echo "▶ [2/6] 夜跑进程状态..."
ssh -i ~/.ssh/claude_code_server root@10.14.92.65 '
if ps aux | grep -v grep | grep night_run > /dev/null 2>&1; then
  echo "  ⏳ 夜跑仍在运行中"
  ps aux | grep -v grep | grep night_run | awk "{print \"    PID=\" \$2 \" CPU=\" \$3 \"% MEM=\" \$4 \"%\"}"
else
  echo "  ✓ 夜跑已结束"
fi
'
echo

# ── 3. 查找夜跑输出目录 ──
echo "▶ [3/6] 夜跑输出目录..."
NIGHT_DIR=$(ssh -i ~/.ssh/claude_code_server root@10.14.92.65 "ls -td $PROJECT_DIR/outputs/night_run/*/ 2>/dev/null | head -1")
if [ -z "$NIGHT_DIR" ]; then
  echo "  ✗ 未找到夜跑输出目录"
  exit 1
fi
echo "  目录: $NIGHT_DIR"
echo

# ── 4. 读取 night_manifest.json ──
echo "▶ [4/6] 实验完成状态..."
ssh -i ~/.ssh/claude_code_server root@10.14.92.65 "
if [ -f ${NIGHT_DIR}night_manifest.json ]; then
  python3 -c \"
import json, sys
with open('${NIGHT_DIR}night_manifest.json') as f:
    m = json.load(f)

print(f'  运行标签: {m.get(\"run_tag\", \"unknown\")}')
print(f'  开始时间: {m.get(\"started_at\", \"unknown\")}')
print(f'  结束时间: {m.get(\"finished_at\", \"unknown\")}')
print()

experiments = m.get('experiments', {})
completed = 0
failed = 0
for exp_id, info in experiments.items():
    status = info.get('status', 'unknown')
    seeds = info.get('seeds_completed', [])
    n_seeds = len(seeds)
    if status == 'completed':
        completed += 1
        print(f'  ✓ {exp_id}: {n_seeds}/3 种子完成')
    elif status == 'failed':
        failed += 1
        print(f'  ✗ {exp_id}: 失败 — {info.get(\"error\", \"unknown error\")}')
    else:
        print(f'  ⏳ {exp_id}: {status} ({n_seeds}/3 种子)')

print()
print(f'  完成: {completed}, 失败: {failed}, 其他: {len(experiments)-completed-failed}')
\" 2>/dev/null || echo '  ⚠ night_manifest.json 解析失败'
else
  echo '  ✗ night_manifest.json 不存在'
fi
"
echo

# ── 5. SG-EXP-005 关键指标（事件窗口改善） ──
echo "▶ [5/6] SG-EXP-005 事件残差修正 — 关键指标..."
ssh -i ~/.ssh/claude_code_server root@10.14.92.65 "
import json, glob, os
base = '${NIGHT_DIR}'
for seed_dir in sorted(glob.glob(os.path.join(base, 'SG-EXP-005', 'seed_*'))):
    seed = os.path.basename(seed_dir)
    metrics_path = os.path.join(seed_dir, 'metrics_summary.json')
    diag_path = os.path.join(seed_dir, 'diagnostics.json')

    if os.path.exists(metrics_path):
        with open(metrics_path) as f:
            m = json.load(f)
        scopes = m.get('scopes', {})

        global_mae = scopes.get('global', {}).get('mae', 'N/A')
        event_mae = scopes.get('event_window', {}).get('mae', 'N/A')
        stable_mae = scopes.get('stable_window', {}).get('mae', 'N/A')

        print(f'  {seed}:')
        print(f'    global MAE:  {global_mae}')
        print(f'    event MAE:   {event_mae}')
        print(f'    stable MAE:  {stable_mae}')

        # 四格诊断
        if os.path.exists(diag_path):
            with open(diag_path) as f:
                d = json.load(f)
            cells = d.get('four_cell', {})
            recon = cells.get('weighted_reconstructed_mae')
            if recon is not None and isinstance(global_mae, float):
                diff = abs(recon - global_mae)
                status = '✓' if diff < 1e-9 else '✗'
                print(f'    四格还原:  {status} (diff={diff:.2e})')
    else:
        print(f'  {seed}: metrics_summary.json 不存在')
    print()
" 2>/dev/null || echo '  ⚠ 无法读取 SG-EXP-005 指标'
echo

# ── 6. 全部实验 MAE 汇总 ──
echo "▶ [6/6] 全部实验 MAE 汇总..."
ssh -i ~/.ssh/claude_code_server root@10.14.92.65 "
import json, glob, os
base = '${NIGHT_DIR}'
for exp_dir in sorted(glob.glob(os.path.join(base, 'SG-EXP-*'))):
    exp_id = os.path.basename(exp_dir)
    print(f'  {exp_id}:')
    for seed_dir in sorted(glob.glob(os.path.join(exp_dir, 'seed_*'))):
        seed = os.path.basename(seed_dir)
        metrics_path = os.path.join(seed_dir, 'metrics_summary.json')
        if os.path.exists(metrics_path):
            with open(metrics_path) as f:
                m = json.load(f)
            scopes = m.get('scopes', {})
            g = scopes.get('global', {}).get('mae', 'N/A')
            e = scopes.get('event_window', {}).get('mae', 'N/A')
            s = scopes.get('stable_window', {}).get('mae', 'N/A')
            print(f'    {seed}: global={g}  event={e}  stable={s}')
        else:
            print(f'    {seed}: 无指标文件')
    print()
" 2>/dev/null || echo '  ⚠ 无法汇总指标'

echo "========================================"
echo "  检查完毕"
echo "========================================"
echo
echo "下一步："
echo "  - 若全部完成 → 进入 Step 1（P0 基线实验）"
echo "  - 若有失败   → 先排查失败原因"
echo "  - 若仍在运行 → 等待完成或检查进度"
