#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${ROOT_DIR}/logs"
PID_FILE="${LOG_DIR}/local-dev.pids"

export API_BASE_URL="http://localhost:8000"
export DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/reddit_sentiment"
export PYTHONPATH="src"
export DASHBOARD_DEBUG="1"
export PYTHONUNBUFFERED="1"

free_port() {
  local port="$1"
  local pids

  pids="$(lsof -ti :"${port}" 2>/dev/null || true)"
  if [[ -z "${pids}" ]]; then
    return
  fi

  kill ${pids} 2>/dev/null || true
  sleep 1

  pids="$(lsof -ti :"${port}" 2>/dev/null || true)"
  if [[ -n "${pids}" ]]; then
    kill -9 ${pids} 2>/dev/null || true
  fi
}

cleanup_partial() {
  if [[ "${CLEANUP_DONE:-0}" == "1" ]]; then
    return
  fi
  CLEANUP_DONE=1

  if [[ -n "${API_PID:-}" ]]; then kill "${API_PID}" 2>/dev/null || true; fi
  if [[ -n "${DASHBOARD_PID:-}" ]]; then kill "${DASHBOARD_PID}" 2>/dev/null || true; fi
  if [[ -n "${WORKER_PID:-}" ]]; then kill "${WORKER_PID}" 2>/dev/null || true; fi

  local job_pids
  job_pids="$(jobs -pr || true)"
  if [[ -n "${job_pids}" ]]; then
    kill ${job_pids} 2>/dev/null || true
  fi

  wait 2>/dev/null || true
}

on_interrupt() {
  cleanup_partial
  exit 130
}

start_process() {
  local process_name="$1"
  shift
  local logfile="${LOG_DIR}/${process_name}.log"
  "$@" > >(
    stdbuf -oL bash -c '
      logfile="$1"
      while IFS= read -r line || [[ -n "$line" ]]; do
        printf "%s %s\n" "$(date -Iseconds)" "$line"
      done >> "$logfile"
    ' _ "$logfile"
  ) 2>&1 &
  STARTED_PID="$!"
}

trap on_interrupt INT TERM

cd "${ROOT_DIR}"
docker compose up -d db
free_port 8000
free_port 8050
mkdir -p "${LOG_DIR}"
: > "${LOG_DIR}/api.log"
: > "${LOG_DIR}/dashboard.log"
: > "${LOG_DIR}/worker.log"

start_process api "${ROOT_DIR}/.venv/bin/python" -m uvicorn reddit_sentiment.api.main:app --host 0.0.0.0 --port 8000 --reload --access-log
API_PID="${STARTED_PID}"

start_process dashboard "${ROOT_DIR}/.venv/bin/python" -m reddit_sentiment.dashboard_runner
DASHBOARD_PID="${STARTED_PID}"

start_process worker "${ROOT_DIR}/.venv/bin/python" -m reddit_sentiment.worker
WORKER_PID="${STARTED_PID}"

{
  echo "api=${API_PID}"
  echo "dashboard=${DASHBOARD_PID}"
  echo "worker=${WORKER_PID}"
} >"${PID_FILE}"

trap - INT TERM

echo "Local dev started (API :8000, dashboard :8050). Logs: ${LOG_DIR}/*.log"
echo "Stop with: ${ROOT_DIR}/scripts/stop-local-dev.sh"
