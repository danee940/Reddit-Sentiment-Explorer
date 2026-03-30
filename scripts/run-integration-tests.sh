#!/usr/bin/env bash
set -euo pipefail

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root_dir"

if [[ -f "${root_dir}/.env" ]]; then
  set -o allexport
  source "${root_dir}/.env"
  set +o allexport
fi

if ! docker info >/dev/null 2>&1; then
  echo "Docker is not available or the daemon is not running." >&2
  exit 1
fi

docker compose up -d db

until docker compose exec -T db pg_isready -U postgres -d reddit_sentiment >/dev/null 2>&1; do
  sleep 1
done

docker compose exec -T db createdb -U postgres reddit_sentiment_test 2>/dev/null || true

export LLM_PROVIDER="${LLM_PROVIDER:-mock}"

exec python -m pytest tests/integration "$@"
