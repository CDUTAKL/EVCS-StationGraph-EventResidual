#!/usr/bin/env bash
# Durable AutoDL queue. Shutdown follows local recovery, outside this wrapper.
set -euo pipefail
cd /root/autodl-tmp/SG-EXP-031
export PYTHONDONTWRITEBYTECODE=1
task_python=/root/miniconda3/bin/python
task_out=results/SG-EXP-031
finish() {
  task_code=$?
  trap - EXIT
  printf '%s\n' "$task_code" > "$task_out/exit_code.txt"
  "$task_python" - "$task_out" "$task_code" <<'PY'
import json,sys,datetime
from pathlib import Path
p=Path(sys.argv[1]);code=int(sys.argv[2])
(p/'autodl_run_summary.json').write_text(json.dumps(dict(exit_code=code,status='completed_unreviewed' if code==0 else 'failed',ended_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),shutdown_status='pending_local_recovery'),indent=2)+'\n')
PY
  find "$task_out" -type f ! -name checksums.sha256 -print0 | sort -z | xargs -0 sha256sum > "$task_out/checksums.sha256"
  tar -czf /root/autodl-tmp/SG-EXP-031-results.tar.gz "$task_out"
  exit "$task_code"
}
trap finish EXIT
"$task_python" scripts/jpl_relation_controls.py all --device cuda --out "$task_out"
