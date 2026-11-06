#!/usr/bin/env bash
# Puesta en marcha completa en desarrollo: dependencias, PostgreSQL y API.
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

"$PROJECT_ROOT/scripts/setup_project.sh"
"$PROJECT_ROOT/scripts/db.sh" setup

cat <<'MSG'

============================================================
 LogistiXpress listo:
   • Dashboard: http://127.0.0.1:8000
   • API docs:  http://127.0.0.1:8000/docs
   • Postgres:  localhost:5432 (contenedor: logistixpress-db)
   • Usuarios:  admin/admin123 · operador/operador123 · auditor/auditor123

 Levanta la aplicación con: ./scripts/run_api.sh
============================================================
MSG
