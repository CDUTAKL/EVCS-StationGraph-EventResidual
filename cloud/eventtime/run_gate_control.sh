#!/usr/bin/env bash
# Approved six-run study; errors also archive and request shutdown.
set -Eeuo pipefail
cd "$(dirname "$0")/../.."
PYTHON_BIN="${PYTHON_BIN:-/root/miniconda3/bin/python}"
export CUBLAS_WORKSPACE_CONFIG=:4096:8
export CUDA_VISIBLE_DEVICES=0
mkdir -p results/cloud_logs
log_dir="$(mktemp -d results/cloud_logs/gate-control-XXXXXX)"
finish() {
    run_code=$?
    trap - EXIT
    set +e
    "$PYTHON_BIN" scripts/finalize_eventtime.py --log-dir "$log_dir" --exit-code "$run_code" --auto-shutdown 1
    archive_code=$?
    if [ "$run_code" = 0 ] && [ "$archive_code" != 0 ]; then run_code="$archive_code"; fi
    echo 'Archive completed/attempted. Requesting shutdown; verify billing status in AutoDL.'
    /usr/bin/shutdown >"$log_dir/shutdown_request.log" 2>&1
    shutdown_code=$?
    if [ "$shutdown_code" != 0 ]; then echo "SHUTDOWN FAILED ($shutdown_code): stop manually." >&2; fi
    exit "$run_code"
}
trap finish EXIT
"$PYTHON_BIN" scripts/gate_control_experiment.py check | tee "$log_dir/check.json"
"$PYTHON_BIN" -m pytest tests/test_gate_control.py -q | tee "$log_dir/tests.log"
"$PYTHON_BIN" scripts/gate_control_experiment.py smoke 2>&1 | tee "$log_dir/smoke.log"
"$PYTHON_BIN" scripts/gate_control_experiment.py benchmark 2>&1 | tee "$log_dir/benchmark.log"
"$PYTHON_BIN" scripts/gate_control_experiment.py formal 2>&1 | tee "$log_dir/formal.log"
