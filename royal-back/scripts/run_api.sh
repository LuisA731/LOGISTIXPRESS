#!/usr/bin/env bash
# Levanta la API y sirve el dashboard en loopback.
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

VENV_DIR="${VENV_DIR:-.venv}"
[[ -x "$VENV_DIR/bin/uvicorn" ]] || {
  echo "ERROR: ejecuta primero scripts/setup_project.sh" >&2
  exit 1
}

HOST="${API_HOST:-127.0.0.1}"
PORT="${API_PORT:-8000}"

echo "==> Dashboard: http://$HOST:$PORT"
echo "==> API docs:  http://$HOST:$PORT/docs"

ARGS=(main:app --host "$HOST" --port "$PORT")
if [[ "${API_RELOAD:-0}" == "1" ]]; then
  ARGS+=(--reload)
fi
exec "$VENV_DIR/bin/uvicorn" "${ARGS[@]}"
