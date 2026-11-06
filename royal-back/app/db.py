"""Pool de conexiones PostgreSQL (psycopg 3)."""
from __future__ import annotations

import threading
from contextlib import contextmanager

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

ROLES_BD_VALIDOS = {"rol_admin", "rol_operador", "rol_auditor"}


class BaseDatos:
    def __init__(self, dsn: str):
        self._dsn = dsn
        self._pool = ConnectionPool(
            dsn,
            min_size=1,
            max_size=8,
            open=False,
            timeout=6,
            kwargs={"row_factory": dict_row},
        )
        self._lock = threading.Lock()

    def _abrir(self) -> None:
        if self._pool.closed:
            with self._lock:
                if self._pool.closed:
                    self._pool.open(wait=True, timeout=6)

    @contextmanager
    def cursor(self, rol: str | None = None):
        """Abre una transacción y aplica el rol de BD con SET LOCAL ROLE.

        El rol se fija dentro de la transacción, por lo que PostgreSQL aplica
        los GRANT del modelo y al cerrar se vuelve al rol de servicio.
        """
        if rol is not None and rol not in ROLES_BD_VALIDOS:
            raise ValueError(f"Rol de base de datos inválido: {rol}")
        self._abrir()
        with self._pool.connection() as conexion:
            with conexion.cursor() as cur:
                if rol:
                    # El rol proviene de una lista blanca interna, no del cliente.
                    cur.execute(f"SET LOCAL ROLE {rol}")
                yield cur

    def ping(self) -> bool:
        try:
            with self.cursor() as cur:
                cur.execute("SELECT 1 AS ok")
                return cur.fetchone()["ok"] == 1
        except Exception:
            return False

    def cerrar(self) -> None:
        self._pool.close()
