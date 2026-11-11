#!/bin/bash
# 发布正式件：替换前备份，自动只保留最近 KEEP 个备份（防止磁盘被塞满）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
KEEP="${KEEP:-3}"
DOCX="outputs/thesis/基于站内多关系图与机制诊断的充电节点短期负荷预测研究_正式论文.docx"
PDF="outputs/thesis/基于站内多关系图与机制诊断的充电节点短期负荷预测研究_正式论文.pdf"
BK=".cache/thesis-delivery/backup"
mkdir -p "$BK"

if [ -f "$DOCX" ]; then
  h=$(shasum -a 256 "$DOCX" | cut -c1-8)
  cp -p "$DOCX" "$BK/official-before-$h.docx"
fi
if [ -f "$PDF" ]; then
  h=$(shasum -a 256 "$PDF" | cut -c1-8)
  cp -p "$PDF" "$BK/official-before-$h.pdf"
fi

# 统一清点所有备份命名；超限文件须已有经远端核验的无损归档。
# 不再遗漏 before-school-* / before-training-*，也不静默丢弃唯一历史件。
python3 scripts/prune_verified_thesis_backups.py --keep "$KEEP" --apply

echo "[publish] backup kept: $(find "$BK" -maxdepth 1 -name '*.docx' | wc -l | tr -d ' ') docx, $(find "$BK" -maxdepth 1 -name '*.pdf' | wc -l | tr -d ' ') pdf"
echo "[publish] cache size: $(du -sh .cache/thesis-delivery 2>/dev/null | cut -f1)"
