#!/usr/bin/env bash
# Watch the exact SG-EXP-031 launcher and shut AutoDL down after verified archive.
set -euo pipefail
mode=${1:?watch or validate required}
watch_pid=${2:?launcher PID required}
watch_start=${3:?launcher start-time token required}
root=/root/autodl-tmp
job="$root/SG-EXP-031"
results="$job/results/SG-EXP-031"
archive="$root/SG-EXP-031-results.tar.gz"
guardian="$root/SG-EXP-031-autoshutdown"
mkdir -p "$guardian"

identity_matches() {
  [[ -r "/proc/$watch_pid/stat" && -r "/proc/$watch_pid/cmdline" ]] || return 1
  current_start=$(awk '{print $22}' "/proc/$watch_pid/stat")
  current_command=$(tr '\0' ' ' < "/proc/$watch_pid/cmdline")
  [[ "$current_start" == "$watch_start" && "$current_command" == 'bash /root/autodl-tmp/SG-EXP-031-run.sh ' ]]
}

if [[ "$mode" == validate ]]; then
  identity_matches || { echo 'launcher identity mismatch'; exit 2; }
  [[ -x /usr/bin/shutdown && -f "$job/scripts/jpl_relation_controls.py" && -x /root/miniconda3/bin/python ]] || {
    echo 'required shutdown/runtime/runner path missing'; exit 3;
  }
  echo 'VALIDATED: exact launcher identity and shutdown/runtime paths'
  exit 0
fi
[[ "$mode" == watch ]] || { echo 'unknown mode'; exit 2; }
identity_matches || { echo 'refusing to arm: launcher identity mismatch'; exit 2; }
[[ ! -e "$guardian/status.json" ]] || { echo 'guardian already armed or has prior status'; exit 3; }
printf '{"status":"armed","launcher_pid":%s,"launcher_start_ticks":"%s"}\n' "$watch_pid" "$watch_start" > "$guardian/status.json"

while identity_matches; do sleep 30; done

# The wrapper's EXIT handler writes its summary/checksums and archive before its
# launcher process exits. Allow filesystem flush and validate before shutdown.
for attempt in $(seq 1 120); do
  if [[ -s "$results/autodl_run_summary.json" && -s "$results/exit_code.txt" && -s "$results/checksums.sha256" && -s "$archive" ]]; then
    break
  fi
  sleep 5
done
[[ -s "$results/autodl_run_summary.json" && -s "$results/exit_code.txt" && -s "$results/checksums.sha256" && -s "$archive" ]] || {
  printf '{"status":"held_open","reason":"completion archive or status files missing"}\n' > "$guardian/status.json"
  exit 4
}
(cd "$results" && sha256sum --quiet -c checksums.sha256)
tar -tzf "$archive" >/dev/null
archive_sha=$(sha256sum "$archive" | awk '{print $1}')
run_code=$(cat "$results/exit_code.txt" | tr -d '[:space:]')
summary_code=$(/root/miniconda3/bin/python -c 'import json,sys;print(json.load(open(sys.argv[1]))["exit_code"])' "$results/autodl_run_summary.json")
[[ "$run_code" == "$summary_code" ]] || {
  printf '{"status":"held_open","reason":"exit code disagreement"}\n' > "$guardian/status.json"
  exit 5
}
ended=$(date -u +%Y-%m-%dT%H:%M:%SZ)
printf '{"status":"verified_shutdown_requested","run_exit_code":%s,"archive":"%s","archive_sha256":"%s","requested_at_utc":"%s"}\n' \
  "$run_code" "$archive" "$archive_sha" "$ended" > "$guardian/status.json"
sync
/usr/bin/shutdown
