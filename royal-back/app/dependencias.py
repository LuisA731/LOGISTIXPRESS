"""Dependencias compartidas y bitácora."""
from __future__ import annotations

from functools import lru_cache
from typing import Any

from psycopg import Cursor
from psycopg.types.json import Jsonb

from .config import ajustes
from .db import BaseDatos
from .seguridad import UsuarioSesion


@lru_cache
def obtener_bd() -> BaseDatos:
    return BaseDatos(ajustes.dsn)


def registrar_bitacora(
    cur: Cursor,
    usuario: UsuarioSesion,
    accion: str,
    *,
    entidad: str | None = None,
    entidad_id: str | int | None = None,
    detalle: dict[str, Any] | None = None,
) -> None:
    cur.execute(
        """
        INSERT INTO seguridad.bitacora
            (usuario_id, usuario_nombre, rol, accion, entidad, entidad_id, detalle)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (
            usuario.id,
            usuario.nombre,
            usuario.rol,
            accion,
            entidad,
            str(entidad_id) if entidad_id is not None else None,
            Jsonb(detalle or {}),
        ),
    )


def registrar_bitacora_segura(
    bd: BaseDatos,
    usuario: UsuarioSesion,
    accion: str,
    *,
    entidad: str | None = None,
    entidad_id: str | int | None = None,
    detalle: dict[str, Any] | None = None,
) -> None:
    """Best-effort para acciones que no deben fallar por la bitácora."""
    try:
        with bd.cursor(usuario.rol_bd) as cur:
            registrar_bitacora(
                cur, usuario, accion,
                entidad=entidad, entidad_id=entidad_id, detalle=detalle,
            )
    except Exception:
        pass
