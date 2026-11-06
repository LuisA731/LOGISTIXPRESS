#!/usr/bin/env bash
# Puesta en marcha local: entorno virtual, dependencias y .env de ejemplo.
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${VENV_DIR:-.venv}"

echo "==> Creando entorno virtual en $VENV_DIR"
"$PYTHON_BIN" -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install -r requirements.txt

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "==> .env creado desde .env.example"
fi

mkdir -p data/evidencias
echo "==> Listo. Activa el entorno con: source $VENV_DIR/bin/activate"
echo "    Siguiente paso: ./scripts/db.sh setup && ./scripts/run_api.sh"
