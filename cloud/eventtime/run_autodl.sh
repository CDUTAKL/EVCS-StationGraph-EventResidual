#!/usr/bin/env bash
# Run only inside your own rented AutoDL instance. Formal commands default to shutdown.
set -Eeuo pipefail
cd "$(dirname "$0")/../.."
PYTHON_BIN="${PYTHON_BIN:-/root/miniconda3/bin/python}"
if [ ! -x "$PYTHON_BIN" ]; then PYTHON_BIN="${PYTHON_BIN_FALLBACK:-python3}"; fi
stage="${1:-check}"
case "$stage" in check|smoke|benchmark|phase1|phase2|all) ;; *) echo 'Invalid stage' >&2; exit 2;; esac
shift || true
for argument in "$@"; do
    case "$argument" in --out|--out=*) echo 'Cloud wrapper archives results/ only; custom --out requires the Python CLI and manual archival.' >&2; exit 2;; esac
done
case "$stage" in phase1|phase2|all) auto_shutdown="${AUTO_SHUTDOWN:-1}";; *) auto_shutdown="${AUTO_SHUTDOWN:-0}";; esac
mkdir -p results/cloud_logs
log_dir="$(mktemp -d results/cloud_logs/launch-XXXXXX)"
finish() {
    run_code=$?
    trap - EXIT
    set +e
    "$PYTHON_BIN" scripts/finalize_eventtime.py --log-dir "$log_dir" --exit-code "$run_code" --auto-shutdown "$auto_shutdown"
    archive_code=$?
    if [ "$auto_shutdown" = 1 ]; then
        echo 'Requesting AutoDL shutdown. Verify stopped status in the console.'
        /usr/bin/shutdown >"$log_dir/shutdown_request.log" 2>&1
        shutdown_code=$?
        if [ "$shutdown_code" != 0 ]; then
            echo "SHUTDOWN FAILED ($shutdown_code): stop instance manually now." >&2
        fi
    fi
    if [ "$run_code" = 0 ] && [ "$archive_code" != 0 ]; then run_code="$archive_code"; fi
    exit "$run_code"
}
trap finish EXIT
"$PYTHON_BIN" scripts/eventtime_experiment.py check | tee "$log_dir/check.json"
if [ "$stage" != check ]; then
    "$PYTHON_BIN" scripts/parallel_eventtime.py "$stage" --gpus "${GPU_IDS:-0,1,2,3}" "$@" 2>&1 | tee "$log_dir/train.log"
fi
