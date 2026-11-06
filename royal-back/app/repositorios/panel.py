"""Indicadores del panel principal."""
from __future__ import annotations

from ..db import BaseDatos
from .base import RepositorioBase


class RepositorioPanel(RepositorioBase):
    def __init__(self, bd: BaseDatos, rol_bd: str):
        super().__init__(bd, rol_bd)

    def resumen(self) -> dict:
        with self.cursor() as cur:
            cur.execute(
                """
                SELECT
                    (SELECT COUNT(*)::int FROM operaciones.rutas
                      WHERE fecha = CURRENT_DATE
                        AND estado <> 'CANCELADA') AS rutas_hoy,
                    (SELECT COUNT(*)::int FROM operaciones.rutas
                      WHERE estado = 'EN_RUTA') AS rutas_en_ruta,
                    (SELECT COUNT(*)::int FROM operaciones.pedidos
                      WHERE estado IN ('LISTO', 'ASIGNADO')) AS pedidos_pendientes,
                    (SELECT COUNT(*)::int FROM operaciones.entregas
                      WHERE resultado = 'ENTREGADO'
                        AND registrado_en::date = CURRENT_DATE) AS entregas_hoy,
                    (SELECT COUNT(*)::int FROM operaciones.entregas
                      WHERE resultado = 'FALLIDO'
                        AND registrado_en::date = CURRENT_DATE) AS fallidas_hoy,
                    (SELECT COUNT(*)::int FROM operaciones.bultos
                      WHERE estado = 'EN_RUTA') AS bultos_en_ruta,
                    (SELECT COUNT(*)::int FROM (
                        SELECT p.id
                        FROM almacen.productos p
                        LEFT JOIN almacen.stock s ON s.producto_id = p.id
                        GROUP BY p.id, p.stock_minimo
                        HAVING COALESCE(SUM(s.cantidad), 0) <= p.stock_minimo
                    ) bajos) AS stock_bajo,
                    COALESCE((
                        SELECT ROUND(
                            100.0 * COUNT(*) FILTER (WHERE s.cantidad > 0)
                            / NULLIF(COUNT(*), 0), 1)
                        FROM almacen.stock s
                    ), 0)::float8 AS ocupacion_pct,
                    COALESCE((
                        SELECT SUM(r.distancia_km)::float8
                        FROM operaciones.rutas r
                        WHERE r.fecha = CURRENT_DATE AND r.estado <> 'CANCELADA'
                    ), 0) AS distancia_hoy_km,
                    (SELECT COUNT(*)::int FROM operaciones.pedidos
                      WHERE estado = 'EN_PICKING') AS pedidos_en_picking,
                    (SELECT COUNT(*)::int FROM operaciones.pedidos
                      WHERE estado = 'EMPACADO') AS pedidos_en_empaque,
                    (SELECT COUNT(*)::int FROM operaciones.picking_tareas
                      WHERE estado = 'PENDIENTE') AS tareas_picking_pendientes,
                    (SELECT COUNT(*)::int FROM operaciones.recepciones
                      WHERE fecha::date = CURRENT_DATE) AS recepciones_hoy,
                    (SELECT COUNT(*)::int FROM operaciones.incidencias_recepcion
                      WHERE fecha::date = CURRENT_DATE) AS incidencias_hoy,
                    COALESCE((
                        SELECT SUM(ABS(diferencia))::int
                        FROM auditoria.conteos_ciclicos
                        WHERE fecha::date = CURRENT_DATE AND diferencia < 0
                    ), 0) AS mermas_hoy,
                    (SELECT COUNT(*)::int FROM almacen.productos p
                      WHERE p.activo = TRUE
                        AND NOT EXISTS (
                            SELECT 1 FROM almacen.movimientos m
                            WHERE m.producto_id = p.id
                              AND m.fecha >= CURRENT_TIMESTAMP - INTERVAL '30 days'
                        )) AS productos_estancados
                """
            )
            return cur.fetchone()

    def productividad_hoy(self) -> list[dict]:
        with self.cursor() as cur:
            cur.execute(
                """
                SELECT u.nombre AS operador,
                       COUNT(t.id)::int AS tareas,
                       COALESCE(SUM(t.cantidad_picada), 0)::int AS lineas
                FROM operaciones.picking_tareas t
                JOIN seguridad.usuarios u ON u.id = t.completado_por
                WHERE t.completado_en::date = CURRENT_DATE
                GROUP BY u.id, u.nombre
                ORDER BY lineas DESC, tareas DESC
                LIMIT 5
                """
            )
            return list(cur.fetchall())
