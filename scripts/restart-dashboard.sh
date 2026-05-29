#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "${ROOT_DIR}"

export API_BASE_URL="http://localhost:8000"
export DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/reddit_sentiment"
export PYTHONPATH="src"
export DASHBOARD_DEBUG="1"

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

pkill -f "python -m reddit_sentiment.dashboard_runner" 2>/dev/null || true
pkill -f "gunicorn reddit_sentiment.dashboard:server" 2>/dev/null || true
free_port 8050

exec "${ROOT_DIR}/.venv/bin/python" -m reddit_sentiment.dashboard_runner
