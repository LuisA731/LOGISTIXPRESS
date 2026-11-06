"""Consulta de rastreo público interno por guía."""
from __future__ import annotations

from ..db import BaseDatos
from .base import RepositorioBase


class RepositorioRastreo(RepositorioBase):
    def __init__(self, bd: BaseDatos, rol_bd: str):
        super().__init__(bd, rol_bd)

    def consultar(self, guia: str) -> dict | None:
        with self.cursor() as cur:
            cur.execute(
                """
                SELECT b.id,
                       b.guia,
                       b.descripcion,
                       b.estado,
                       b.peso_kg::float8    AS peso_kg,
                       b.volumen_m3::float8 AS volumen_m3,
                       p.folio               AS pedido_folio,
                       p.estado              AS pedido_estado,
                       p.fecha_compromiso,
                       c.nombre              AS cliente,
                       c.tipo_cliente,
                       c.zona,
                       c.direccion,
                       c.telefono,
                       r.folio               AS ruta_folio,
                       r.estado              AS ruta_estado
                FROM operaciones.bultos b
                JOIN operaciones.pedidos p ON p.id = b.pedido_id
                JOIN operaciones.clientes c ON c.id = p.cliente_id
                LEFT JOIN LATERAL (
                    SELECT ru.folio, ru.estado
                    FROM operaciones.ruta_bultos rb
                    JOIN operaciones.ruta_paradas rp ON rp.id = rb.ruta_parada_id
                    JOIN operaciones.rutas ru ON ru.id = rp.ruta_id
                    WHERE rb.bulto_id = b.id
                    ORDER BY ru.generada_en DESC
                    LIMIT 1
                ) r ON TRUE
                WHERE upper(b.guia) = upper(%s)
                """,
                (guia.strip(),),
            )
            bulto = cur.fetchone()
            if bulto is None:
                return None

            cur.execute(
                """
                SELECT e.estado,
                       e.descripcion,
                       e.ubicacion,
                       u.nombre AS usuario,
                       e.fecha
                FROM operaciones.eventos_rastreo e
                LEFT JOIN seguridad.usuarios u ON u.id = e.usuario_id
                WHERE e.bulto_id = %s
                ORDER BY e.fecha DESC, e.id DESC
                """,
                (bulto["id"],),
            )
            bulto["eventos"] = list(cur.fetchall())
            return bulto

    def recientes(self, limite: int = 8) -> list[dict]:
        with self.cursor() as cur:
            cur.execute(
                """
                SELECT guia, cliente, estado, pedido_folio, fecha
                FROM (
                    SELECT DISTINCT ON (b.id)
                           b.guia,
                           c.nombre AS cliente,
                           e.estado,
                           p.folio AS pedido_folio,
                           e.fecha
                    FROM operaciones.eventos_rastreo e
                    JOIN operaciones.bultos b ON b.id = e.bulto_id
                    JOIN operaciones.pedidos p ON p.id = b.pedido_id
                    JOIN operaciones.clientes c ON c.id = p.cliente_id
                    ORDER BY b.id, e.fecha DESC, e.id DESC
                ) ultimo
                ORDER BY fecha DESC
                LIMIT %s
                """,
                (limite,),
            )
            return list(cur.fetchall())

    def eventos_recientes(self, limite: int = 8) -> list[dict]:
        with self.cursor() as cur:
            cur.execute(
                """
                SELECT e.estado,
                       e.descripcion,
                       e.ubicacion,
                       u.nombre AS usuario,
                       b.guia,
                       e.fecha
                FROM operaciones.eventos_rastreo e
                JOIN operaciones.bultos b ON b.id = e.bulto_id
                LEFT JOIN seguridad.usuarios u ON u.id = e.usuario_id
                ORDER BY e.fecha DESC, e.id DESC
                LIMIT %s
                """,
                (limite,),
            )
            return list(cur.fetchall())
