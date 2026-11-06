"""Inventario: stock, catálogo y movimientos."""
from __future__ import annotations

from ..dependencias import registrar_bitacora
from ..db import BaseDatos
from ..seguridad import UsuarioSesion
from .base import RepositorioBase


class RepositorioInventario(RepositorioBase):
    def __init__(self, bd: BaseDatos, rol_bd: str):
        super().__init__(bd, rol_bd)

    def stock(self) -> list[dict]:
        with self.cursor() as cur:
            cur.execute(
                """
                SELECT p.id AS producto_id,
                       p.sku,
                       p.nombre,
                       COALESCE((SELECT SUM(s.cantidad) FROM almacen.stock s
                                  WHERE s.producto_id = p.id), 0)::int AS stock_total,
                       p.stock_minimo,
                       (SELECT COUNT(*) FROM almacen.stock s
                         WHERE s.producto_id = p.id AND s.cantidad > 0)::int
                         AS numero_ubicaciones,
                       (SELECT MIN(l.caducidad) FROM almacen.lotes l
                         WHERE l.producto_id = p.id
                           AND l.cantidad > 0
                           AND l.caducidad >= CURRENT_DATE) AS proximo_vencimiento
                FROM almacen.productos p
                WHERE p.activo = TRUE
                ORDER BY p.nombre
                """
            )
            filas = list(cur.fetchall())
        for fila in filas:
            fila["bajo_minimo"] = fila["stock_total"] <= fila["stock_minimo"]
        return filas

    def catalogo(self) -> dict:
        with self.cursor() as cur:
            cur.execute(
                """
                SELECT id, sku, nombre,
                       peso_kg::float8 AS peso_kg,
                       volumen_m3::float8 AS volumen_m3,
                       stock_minimo
                FROM almacen.productos
                WHERE activo = TRUE
                ORDER BY nombre
                """
            )
            productos = list(cur.fetchall())
            cur.execute(
                """
                SELECT id, codigo, pasillo, rack, nivel, tipo_zona, activo
                FROM almacen.ubicaciones
                WHERE activo = TRUE
                ORDER BY orden_picking
                """
            )
            ubicaciones = list(cur.fetchall())
        return {"productos": productos, "ubicaciones": ubicaciones}

    def movimientos(self, limite: int = 80) -> list[dict]:
        with self.cursor() as cur:
            cur.execute(
                """
                SELECT m.id,
                       p.nombre AS producto,
                       p.sku,
                       u.codigo AS ubicacion,
                       m.tipo,
                       m.cantidad,
                       us.nombre AS usuario,
                       m.fecha
                FROM almacen.movimientos m
                JOIN almacen.productos p ON p.id = m.producto_id
                JOIN almacen.ubicaciones u ON u.id = m.ubicacion_id
                LEFT JOIN seguridad.usuarios us ON us.id = m.usuario_id
                ORDER BY m.fecha DESC, m.id DESC
                LIMIT %s
                """,
                (limite,),
            )
            return list(cur.fetchall())

    def traslados(self, limite: int = 80) -> list[dict]:
        with self.cursor() as cur:
            cur.execute(
                """
                SELECT t.id, p.nombre AS producto, t.cantidad,
                       o.codigo AS origen, d.codigo AS destino,
                       u.nombre AS usuario, t.comentario, t.fecha
                FROM almacen.traslados t
                JOIN almacen.productos p ON p.id = t.producto_id
                JOIN almacen.ubicaciones o ON o.id = t.ubicacion_origen_id
                JOIN almacen.ubicaciones d ON d.id = t.ubicacion_destino_id
                LEFT JOIN seguridad.usuarios u ON u.id = t.usuario_id
                ORDER BY t.fecha DESC, t.id DESC
                LIMIT %s
                """,
                (limite,),
            )
            return list(cur.fetchall())

    def registrar_traslado(
        self,
        *,
        producto_id: int,
        cantidad: int,
        ubicacion_origen_id: int,
        ubicacion_destino_id: int,
        comentario: str | None,
        usuario: UsuarioSesion,
    ) -> dict:
        if ubicacion_origen_id == ubicacion_destino_id:
            raise ValueError("La ubicación de origen y destino deben ser distintas.")
        with self.cursor() as cur:
            cur.execute(
                """
                SELECT id, codigo, activo FROM almacen.ubicaciones
                WHERE id = ANY(%s)
                """,
                ([ubicacion_origen_id, ubicacion_destino_id],),
            )
            ubicaciones = {fila["id"]: fila for fila in cur.fetchall()}
            if len(ubicaciones) != 2:
                raise ValueError("La ubicación de origen o destino no existe.")
            if not all(fila["activo"] for fila in ubicaciones.values()):
                raise ValueError("La ubicación de origen o destino está inactiva.")
            cur.execute(
                """
                SELECT cantidad FROM almacen.stock
                WHERE producto_id = %s AND ubicacion_id = %s
                """,
                (producto_id, ubicacion_origen_id),
            )
            stock = cur.fetchone()
            if stock is None or stock["cantidad"] < cantidad:
                raise ValueError(
                    "No hay stock suficiente en la ubicación de origen para el traslado."
                )
            cur.execute(
                """
                INSERT INTO almacen.traslados
                    (producto_id, cantidad, ubicacion_origen_id,
                     ubicacion_destino_id, usuario_id, comentario)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (producto_id, cantidad, ubicacion_origen_id, ubicacion_destino_id,
                 usuario.id, comentario),
            )
            traslado_id = cur.fetchone()["id"]
            cur.execute(
                """
                INSERT INTO almacen.movimientos
                    (producto_id, ubicacion_id, tipo, cantidad, usuario_id)
                VALUES (%s, %s, 'SALIDA', %s, %s)
                """,
                (producto_id, ubicacion_origen_id, cantidad, usuario.id),
            )
            cur.execute(
                """
                INSERT INTO almacen.movimientos
                    (producto_id, ubicacion_id, tipo, cantidad, usuario_id)
                VALUES (%s, %s, 'ENTRADA', %s, %s)
                """,
                (producto_id, ubicacion_destino_id, cantidad, usuario.id),
            )
            registrar_bitacora(
                cur, usuario, "TRASLADO_INVENTARIO", entidad="traslado",
                entidad_id=traslado_id,
                detalle={"producto_id": producto_id, "cantidad": cantidad,
                         "origen": ubicaciones[ubicacion_origen_id]["codigo"],
                         "destino": ubicaciones[ubicacion_destino_id]["codigo"]},
            )
        return next(
            (fila for fila in self.traslados(1) if fila["id"] == traslado_id),
            None,
        )

    def registrar_movimiento(
        self,
        *,
        producto_id: int,
        ubicacion_id: int,
        tipo: str,
        cantidad: int,
        usuario: UsuarioSesion,
    ) -> dict:
        with self.cursor() as cur:
            cur.execute(
                """
                INSERT INTO almacen.movimientos
                    (producto_id, ubicacion_id, tipo, cantidad, usuario_id)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (producto_id, ubicacion_id, tipo, cantidad, usuario.id),
            )
            movimiento_id = cur.fetchone()["id"]
            cur.execute(
                """
                SELECT m.id,
                       p.nombre AS producto,
                       p.sku,
                       u.codigo AS ubicacion,
                       m.tipo,
                       m.cantidad,
                       us.nombre AS usuario,
                       m.fecha
                FROM almacen.movimientos m
                JOIN almacen.productos p ON p.id = m.producto_id
                JOIN almacen.ubicaciones u ON u.id = m.ubicacion_id
                LEFT JOIN seguridad.usuarios us ON us.id = m.usuario_id
                WHERE m.id = %s
                """,
                (movimiento_id,),
            )
            movimiento = cur.fetchone()
            registrar_bitacora(
                cur, usuario, "MOVIMIENTO_INVENTARIO", entidad="movimiento",
                entidad_id=movimiento_id,
                detalle={
                    "producto": movimiento["producto"],
                    "tipo": tipo,
                    "cantidad": cantidad,
                    "ubicacion": movimiento["ubicacion"],
                },
            )
            return movimiento
