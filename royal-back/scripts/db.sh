#!/usr/bin/env bash
# Gestión del contenedor PostgreSQL de LogistiXpress.
# Uso: ./scripts/db.sh {setup|schema|seed|start|stop|reset|status|logs|psql}
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

PODMAN="${PODMAN:-podman}"
CONTAINER="${CONTAINER:-logistixpress-db}"
IMAGE="${IMAGE:-docker.io/library/postgres:16-alpine}"
VOLUME="${VOLUME:-logistixpress-pgdata}"
PORT="${PORT:-5432}"
PGUSER="${PGUSER:-postgres}"
PGPASSWORD="${PGPASSWORD:-postgres}"
PGDB="${PGDB:-logistixpress}"
SCHEMA_SQL="${SCHEMA_SQL:-$PROJECT_ROOT/db/01_esquema.sql}"
SEED_SQL="${SEED_SQL:-$PROJECT_ROOT/db/02_semilla.sql}"

need_podman() {
  command -v "$PODMAN" >/dev/null 2>&1 || {
    echo "ERROR: '$PODMAN' no está instalado." >&2
    echo "  Fedora/RHEL:   sudo dnf install podman" >&2
    echo "  Debian/Ubuntu: sudo apt install podman" >&2
    echo "  También puedes usar PODMAN=docker ./scripts/db.sh ..." >&2
    exit 1
  }
}

wait_ready() {
  echo "==> Esperando a PostgreSQL..."
  for _ in $(seq 1 40); do
    if "$PODMAN" exec "$CONTAINER" pg_isready -U "$PGUSER" -d "$PGDB" >/dev/null 2>&1; then
      echo "    PostgreSQL listo en localhost:$PORT"
      return 0
    fi
    sleep 1
  done
  echo "ERROR: PostgreSQL no respondió a tiempo." >&2
  "$PODMAN" logs "$CONTAINER" >&2 || true
  exit 1
}

load_sql() {
  local archivo="$1"
  [[ -f "$archivo" ]] || { echo "ERROR: no existe $archivo" >&2; exit 1; }
  echo "==> Cargando $(basename "$archivo")"
  "$PODMAN" exec -i "$CONTAINER" \
    psql -v ON_ERROR_STOP=1 -U "$PGUSER" -d "$PGDB" < "$archivo"
}

cmd_setup() {
  need_podman
  if "$PODMAN" container inspect "$CONTAINER" >/dev/null 2>&1; then
    echo "==> El contenedor $CONTAINER ya existe; se reutiliza."
    "$PODMAN" start "$CONTAINER" >/dev/null 2>&1 || true
    wait_ready
    echo "==> No se recargan esquema ni semilla para no sobrescribir datos."
    echo "    Usa './scripts/db.sh reset' para recrear desde cero."
  else
    echo "==> Creando contenedor $CONTAINER ($IMAGE)"
    "$PODMAN" run -d \
      --name "$CONTAINER" \
      -e POSTGRES_USER="$PGUSER" \
      -e POSTGRES_PASSWORD="$PGPASSWORD" \
      -e POSTGRES_DB="$PGDB" \
      -p "127.0.0.1:${PORT}:5432" \
      -v "${VOLUME}:/var/lib/postgresql/data" \
      "$IMAGE" >/dev/null
    wait_ready
    load_sql "$SCHEMA_SQL"
    load_sql "$SEED_SQL"
  fi
  echo "==> DSN: postgresql://$PGUSER:$PGPASSWORD@127.0.0.1:$PORT/$PGDB"
}

cmd_schema() { need_podman; load_sql "$SCHEMA_SQL"; }
cmd_seed()   { need_podman; load_sql "$SEED_SQL"; }
cmd_start()  { need_podman; "$PODMAN" start "$CONTAINER"; wait_ready; }
cmd_stop()   { need_podman; "$PODMAN" stop "$CONTAINER"; }
cmd_status() { need_podman; "$PODMAN" ps -a --filter "name=$CONTAINER"; }
cmd_logs()   { need_podman; "$PODMAN" logs -f "$CONTAINER"; }
cmd_psql()   { need_podman; "$PODMAN" exec -it "$CONTAINER" psql -U "$PGUSER" -d "$PGDB"; }

cmd_reset() {
  need_podman
  echo "==> Eliminando contenedor y volumen (se BORRAN los datos)"
  "$PODMAN" rm -f "$CONTAINER" >/dev/null 2>&1 || true
  "$PODMAN" volume rm "$VOLUME" >/dev/null 2>&1 || true
  cmd_setup
}

case "${1:-}" in
  setup)  cmd_setup ;;
  schema) cmd_schema ;;
  seed)   cmd_seed ;;
  start)  cmd_start ;;
  stop)   cmd_stop ;;
  reset)  cmd_reset ;;
  status) cmd_status ;;
  logs)   cmd_logs ;;
  psql)   cmd_psql ;;
  *) echo "Uso: $0 {setup|schema|seed|start|stop|reset|status|logs|psql}" >&2; exit 1 ;;
esac
