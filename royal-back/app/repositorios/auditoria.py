"""Auditoría: bitácora, conteos cíclicos y rotación."""
from __future__ import annotations

from datetime import date

from ..dependencias import registrar_bitacora
from ..db import BaseDatos
from ..seguridad import UsuarioSesion
from .base import RepositorioBase


class RepositorioAuditoria(RepositorioBase):
    def __init__(self, bd: BaseDatos, rol_bd: str):
        super().__init__(bd, rol_bd)

    def bitacora(
        self,
        *,
        limite: int = 120,
        accion: str | None = None,
        desde: date | None = None,
        hasta: date | None = None,
    ) -> list[dict]:
        with self.cursor() as cur:
            cur.execute(
                """
                SELECT id, usuario_nombre AS usuario, rol, accion, entidad,
                       entidad_id, detalle, fecha
                FROM seguridad.bitacora
                WHERE (%s::text IS NULL OR accion = %s::text)
                  AND (%s::date IS NULL OR fecha::date >= %s::date)
                  AND (%s::date IS NULL OR fecha::date <= %s::date)
                ORDER BY fecha DESC, id DESC
                LIMIT %s
                """,
                (accion, accion, desde, desde, hasta, hasta, limite),
            )
            return list(cur.fetchall())

    def conteos(self, limite: int = 80) -> list[dict]:
        with self.cursor() as cur:
            cur.execute(
                """
                SELECT cc.id,
                       u.codigo AS ubicacion,
                       p.nombre AS producto,
                       cc.cantidad_sistema,
                       cc.cantidad_fisica,
                       cc.diferencia,
                       us.nombre AS auditor,
                       cc.fecha
                FROM auditoria.conteos_ciclicos cc
                JOIN almacen.ubicaciones u ON u.id = cc.ubicacion_id
                JOIN almacen.productos p ON p.id = cc.producto_id
                JOIN seguridad.usuarios us ON us.id = cc.auditor_id
                ORDER BY cc.fecha DESC, cc.id DESC
                LIMIT %s
                """,
                (limite,),
            )
            return list(cur.fetchall())

    def registrar_conteo(
        self,
        *,
        ubicacion_id: int,
        producto_id: int,
        cantidad_fisica: int,
        usuario: UsuarioSesion,
    ) -> dict:
        with self.cursor() as cur:
            cur.execute(
                """
                SELECT COALESCE(SUM(cantidad), 0)::int AS cantidad_sistema
                FROM almacen.stock
                WHERE ubicacion_id = %s AND producto_id = %s
                """,
                (ubicacion_id, producto_id),
            )
            sistema = cur.fetchone()["cantidad_sistema"]
            cur.execute(
                """
                INSERT INTO auditoria.conteos_ciclicos
                    (ubicacion_id, producto_id, cantidad_sistema,
                     cantidad_fisica, auditor_id)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (ubicacion_id, producto_id, sistema, cantidad_fisica, usuario.id),
            )
            conteo_id = cur.fetchone()["id"]
            cur.execute(
                """
                SELECT cc.id,
                       u.codigo AS ubicacion,
                       p.nombre AS producto,
                       cc.cantidad_sistema,
                       cc.cantidad_fisica,
                       cc.diferencia,
                       us.nombre AS auditor,
                       cc.fecha
                FROM auditoria.conteos_ciclicos cc
                JOIN almacen.ubicaciones u ON u.id = cc.ubicacion_id
                JOIN almacen.productos p ON p.id = cc.producto_id
                JOIN seguridad.usuarios us ON us.id = cc.auditor_id
                WHERE cc.id = %s
                """,
                (conteo_id,),
            )
            conteo = cur.fetchone()
            registrar_bitacora(
                cur, usuario, "CONTEO_CICLICO", entidad="conteo_ciclico",
                entidad_id=conteo_id,
                detalle={
                    "ubicacion": conteo["ubicacion"],
                    "producto": conteo["producto"],
                    "diferencia": conteo["diferencia"],
                },
            )
            return conteo

    def rotacion(self, limite: int = 80) -> list[dict]:
        with self.cursor() as cur:
            cur.execute(
                """
                SELECT sku, nombre, total_salidas::int, total_entradas::int
                FROM auditoria.v_metricas_rotacion
                ORDER BY total_salidas ASC, nombre
                LIMIT %s
                """,
                (limite,),
            )
            return list(cur.fetchall())
