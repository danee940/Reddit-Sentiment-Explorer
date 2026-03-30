#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${ROOT_DIR}/logs"
PID_FILE="${LOG_DIR}/local-dev.pids"

kill_pid() {
  local pid="$1"
  local name="$2"

  if [[ -z "${pid}" || ! "${pid}" =~ ^[0-9]+$ ]]; then
    return
  fi

  if ! kill -0 "${pid}" 2>/dev/null; then
    echo "${name} (${pid}): not running"
    return
  fi

  kill "${pid}" 2>/dev/null || true
  local waited=0
  while kill -0 "${pid}" 2>/dev/null && [[ "${waited}" -lt 30 ]]; do
    sleep 0.2
    waited=$((waited + 1))
  done

  if kill -0 "${pid}" 2>/dev/null; then
    kill -9 "${pid}" 2>/dev/null || true
    echo "${name} (${pid}): stopped (SIGKILL)"
  else
    echo "${name} (${pid}): stopped"
  fi
}

if [[ ! -f "${PID_FILE}" ]]; then
  echo "No ${PID_FILE}; nothing to stop (or PIDs were already cleared)."
  exit 0
fi

api_pid=""
dashboard_pid=""
worker_pid=""

while IFS= read -r line || [[ -n "${line}" ]]; do
  [[ -z "${line}" ]] && continue
  case "${line}" in
    api=*) api_pid="${line#api=}" ;;
    dashboard=*) dashboard_pid="${line#dashboard=}" ;;
    worker=*) worker_pid="${line#worker=}" ;;
  esac
done <"${PID_FILE}"

kill_pid "${worker_pid}" "worker"
kill_pid "${dashboard_pid}" "dashboard"
kill_pid "${api_pid}" "api"

rm -f "${PID_FILE}"
