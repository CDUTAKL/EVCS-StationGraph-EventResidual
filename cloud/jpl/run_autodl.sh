#!/usr/bin/env bash
# Deliberately does not start formal training without a second explicit confirmation.
set -Eeuo pipefail
cd "$(dirname "$0")/../.."
PYTHON_BIN="${PYTHON_BIN:-/root/miniconda3/bin/python}"
if [ ! -x "$PYTHON_BIN" ]; then PYTHON_BIN="${PYTHON_BIN_FALLBACK:-python3}"; fi
mode="${1:-preflight}"
case "$mode" in preflight|smoke|formal) ;; *) echo 'Use preflight, smoke, or formal.' >&2; exit 2;; esac
mkdir -p run_logs
log_dir="$(mktemp -d run_logs/SG-EXP-028-XXXXXX)"
if [ "$mode" = preflight ]; then
    "$PYTHON_BIN" scripts/jpl_experiment.py preflight | tee "$log_dir/preflight.json"
elif [ "$mode" = smoke ]; then
    "$PYTHON_BIN" scripts/jpl_experiment.py smoke 2>&1 | tee "$log_dir/smoke.log"
else
    if [ "${CONFIRM_FORMAL:-}" != "SG-EXP-028" ]; then
        echo 'Formal execution blocked. Set CONFIRM_FORMAL=SG-EXP-028 only after explicit authorization.' >&2
        exit 2
    fi
    run_code=0
    resume_args=()
    if [ "${RESUME:-0}" = "1" ]; then resume_args+=(--resume); fi
    "$PYTHON_BIN" scripts/jpl_experiment.py run-suite --gpus "${GPU_IDS:-0}" "${resume_args[@]}" 2>&1 | tee "$log_dir/formal.log" || run_code=$?
    set +e
    "$PYTHON_BIN" scripts/archive_jpl_run.py --run-log "$log_dir"
    archive_code=$?
    set -e
    if [ "$run_code" -ne 0 ]; then exit "$run_code"; fi
    if [ "$archive_code" -ne 0 ]; then exit "$archive_code"; fi
    if [ "${AUTO_SHUTDOWN:-0}" = "1" ]; then
        echo 'Requesting instance shutdown; confirm stopped/billing state in the provider console.'
        /usr/bin/shutdown
    else
        echo 'Run archive created; instance remains on. Stop billing in the provider console when ready.'
    fi
fi
