"""Picking, packing y control de calidad previo al embarque."""
from __future__ import annotations

from datetime import date

from ..dependencias import registrar_bitacora
from ..db import BaseDatos
from ..errores import ErrorNegocio
from ..modelos.esquemas_operaciones import ConfirmarTareaIn
from ..seguridad import UsuarioSesion
from .base import RepositorioBase


class RepositorioPicking(RepositorioBase):
    def __init__(self, bd: BaseDatos, rol_bd: str):
        super().__init__(bd, rol_bd)

    # ------------------------------------------------------------------
    # Consulta
    # ------------------------------------------------------------------
    def pedidos(self, limite: int = 100) -> list[dict]:
        with self.cursor() as cur:
            cur.execute(
                """
                SELECT id FROM operaciones.pedidos
                WHERE estado IN ('BORRADOR', 'EN_PICKING', 'PICKING_COMPLETO',
                                 'EMPACADO', 'LISTO')
                ORDER BY creado_en DESC
                LIMIT %s
                """,
                (limite,),
            )
            ids = [fila["id"] for fila in cur.fetchall()]
        return [pedido for pedido_id in ids if (pedido := self.pedido(pedido_id))]

    def pedido(self, pedido_id: int) -> dict | None:
        with self.cursor() as cur:
            cur.execute(
                """
                SELECT p.id, p.folio, c.nombre AS cliente,
                       c.codigo AS cliente_codigo, c.direccion, c.telefono,
                       p.estado, p.prioridad, p.fecha_compromiso,
                       p.peso_kg::float8 AS peso_kg,
                       p.volumen_m3::float8 AS volumen_m3
                FROM operaciones.pedidos p
                JOIN operaciones.clientes c ON c.id = p.cliente_id
                WHERE p.id = %s
                """,
                (pedido_id,),
            )
            pedido = cur.fetchone()
            if pedido is None:
                return None

            cur.execute(
                """
                SELECT d.id, d.producto_id, pr.nombre AS producto, pr.sku, d.cantidad,
                       (pr.peso_kg * d.cantidad)::float8 AS peso_kg,
                       (pr.volumen_m3 * d.cantidad)::float8 AS volumen_m3
                FROM operaciones.pedido_detalle d
                JOIN almacen.productos pr ON pr.id = d.producto_id
                WHERE d.pedido_id = %s
                ORDER BY d.id
                """,
                (pedido_id,),
            )
            pedido["lineas"] = list(cur.fetchall())

            cur.execute(
                """
                SELECT t.id, t.pedido_id, p.nombre AS producto, p.sku,
                       u.codigo AS ubicacion, t.cantidad, t.cantidad_picada,
                       t.estado, t.orden
                FROM operaciones.picking_tareas t
                JOIN almacen.productos p ON p.id = t.producto_id
                JOIN almacen.ubicaciones u ON u.id = t.ubicacion_id
                WHERE t.pedido_id = %s
                ORDER BY t.orden, t.id
                """,
                (pedido_id,),
            )
            pedido["tareas"] = list(cur.fetchall())

            cur.execute(
                """
                SELECT id, guia, descripcion,
                       peso_kg::float8 AS peso_kg,
                       volumen_m3::float8 AS volumen_m3, estado
                FROM operaciones.bultos
                WHERE pedido_id = %s
                ORDER BY guia
                """,
                (pedido_id,),
            )
            bultos = list(cur.fetchall())

            cur.execute(
                """
                SELECT e.id, e.folio, e.estado,
                       e.peso_kg::float8 AS peso_kg,
                       e.volumen_m3::float8 AS volumen_m3,
                       u.nombre AS validado_por, e.creado_en
                FROM operaciones.empaques e
                LEFT JOIN seguridad.usuarios u ON u.id = e.validado_por
                WHERE e.pedido_id = %s
                ORDER BY e.creado_en DESC
                LIMIT 1
                """,
                (pedido_id,),
            )
            empaque = cur.fetchone()
            if empaque is not None:
                empaque["bultos"] = bultos
            pedido["empaque"] = empaque
            pedido["bultos"] = bultos
            return pedido

    # ------------------------------------------------------------------
    # Ola de picking
    # ------------------------------------------------------------------
    def generar_ola(self, usuario: UsuarioSesion) -> dict:
        with self.cursor() as cur:
            cur.execute(
                """
                SELECT p.id AS pedido_id, p.folio, d.producto_id, d.cantidad,
                       pr.nombre AS producto, pr.sku
                FROM operaciones.pedidos p
                JOIN operaciones.pedido_detalle d ON d.pedido_id = p.id
                JOIN almacen.productos pr ON pr.id = d.producto_id
                WHERE p.estado = 'BORRADOR'
                ORDER BY p.id, d.id
                FOR UPDATE OF p
                """
            )
            filas = list(cur.fetchall())
            if not filas:
                raise ErrorNegocio(
                    "No hay pedidos en BORRADOR para generar una ola de picking.", 409
                )

            # Un pedido puede tener el mismo producto en varias líneas;
            # la tarea de picking se genera una sola vez por producto.
            agrupadas: dict[tuple[int, int], dict] = {}
            pedidos: dict[int, str] = {}
            for fila in filas:
                pedidos[fila["pedido_id"]] = fila["folio"]
                clave = (fila["pedido_id"], fila["producto_id"])
                if clave not in agrupadas:
                    agrupadas[clave] = dict(fila)
                else:
                    agrupadas[clave]["cantidad"] += fila["cantidad"]

            asignado_ubicacion: dict[int, int] = {}
            tareas: list[tuple] = []
            faltantes: list[str] = []
            for fila in agrupadas.values():
                cur.execute(
                    """
                    SELECT s.ubicacion_id, s.cantidad, u.codigo,
                           u.pasillo, u.orden_picking
                    FROM almacen.stock s
                    JOIN almacen.ubicaciones u ON u.id = s.ubicacion_id
                    WHERE s.producto_id = %s
                      AND u.activo = TRUE
                      AND u.tipo_zona = 'GENERAL'
                    ORDER BY u.pasillo ASC, u.orden_picking ASC, s.cantidad DESC
                    """,
                    (fila["producto_id"],),
                )
                ubicacion = next(
                    (
                        candidata for candidata in cur.fetchall()
                        if candidata["cantidad"]
                        - asignado_ubicacion.get(candidata["ubicacion_id"], 0)
                        >= fila["cantidad"]
                    ),
                    None,
                )
                if ubicacion is None:
                    faltantes.append(
                        f"{fila['producto']} ({fila['sku']}) x {fila['cantidad']} "
                        f"para {fila['folio']}"
                    )
                    continue
                asignado_ubicacion[ubicacion["ubicacion_id"]] = (
                    asignado_ubicacion.get(ubicacion["ubicacion_id"], 0)
                    + fila["cantidad"]
                )
                tareas.append(
                    (
                        fila["pedido_id"], fila["producto_id"], ubicacion["ubicacion_id"],
                        fila["cantidad"], ubicacion["pasillo"], ubicacion["orden_picking"],
                    )
                )

            if faltantes:
                raise ErrorNegocio(
                    "No hay stock suficiente en zona GENERAL para: "
                    + "; ".join(faltantes),
                    409,
                )

            # La ruta de picking se ordena por pasillo y orden_picking.
            tareas.sort(key=lambda tarea: (tarea[4], tarea[5], tarea[0]))
            cur.execute("SELECT nextval('operaciones.folio_ola_seq') AS numero")
            numero = cur.fetchone()["numero"]
            folio = f"OLA-{date.today():%Y%m%d}-{numero:04d}"
            cur.execute(
                """
                INSERT INTO operaciones.picking_olas
                    (folio, estado, creado_por)
                VALUES (%s, 'EN_PROCESO', %s)
                RETURNING id
                """,
                (folio, usuario.id),
            )
            ola_id = cur.fetchone()["id"]
            cur.executemany(
                """
                INSERT INTO operaciones.picking_tareas
                    (ola_id, pedido_id, producto_id, ubicacion_id, cantidad, orden)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                [
                    (ola_id, pedido_id, producto_id, ubicacion_id, cantidad, orden + 1)
                    for orden, (pedido_id, producto_id, ubicacion_id, cantidad, _, _)
                    in enumerate(tareas)
                ],
            )
            cur.execute(
                "UPDATE operaciones.pedidos SET estado = 'EN_PICKING' WHERE id = ANY(%s)",
                (list(pedidos),),
            )
            registrar_bitacora(
                cur, usuario, "OLA_PICKING_GENERADA", entidad="picking_ola",
                entidad_id=ola_id,
                detalle={"folio": folio, "pedidos": len(pedidos), "tareas": len(tareas)},
            )
        return {
            "id": ola_id, "folio": folio, "fecha": date.today(), "estado": "EN_PROCESO",
            "pedidos": len(pedidos), "tareas": len(tareas),
            "mensaje": f"Ola {folio} generada para {len(pedidos)} pedido(s) "
                       f"con {len(tareas)} tarea(s) de surtido.",
        }

    def confirmar_tarea(
        self, tarea_id: int, datos: ConfirmarTareaIn, usuario: UsuarioSesion
    ) -> dict:
        with self.cursor() as cur:
            cur.execute(
                """
                SELECT t.id, t.ola_id, t.pedido_id, t.producto_id, t.ubicacion_id,
                       t.cantidad, t.estado, p.sku, u.codigo AS ubicacion,
                       pe.folio AS pedido_folio, pr.nombre AS producto
                FROM operaciones.picking_tareas t
                JOIN almacen.productos p ON p.id = t.producto_id
                JOIN almacen.ubicaciones u ON u.id = t.ubicacion_id
                JOIN operaciones.pedidos pe ON pe.id = t.pedido_id
                JOIN almacen.productos pr ON pr.id = t.producto_id
                WHERE t.id = %s
                FOR UPDATE OF t
                """,
                (tarea_id,),
            )
            tarea = cur.fetchone()
            if tarea is None:
                raise ErrorNegocio("La tarea de picking no existe.", 404)
            if tarea["estado"] != "PENDIENTE":
                raise ErrorNegocio("Esta tarea ya fue surtida o marcada.", 409)
            if datos.sku and datos.sku.strip().upper() != tarea["sku"].upper():
                raise ErrorNegocio(
                    f"El SKU escaneado no corresponde. Debes surtir {tarea['sku']}.", 409
                )
            if datos.ubicacion and datos.ubicacion.strip().upper() != tarea["ubicacion"].upper():
                raise ErrorNegocio(
                    f"La ubicación escaneada no corresponde. Debes ir a {tarea['ubicacion']}.",
                    409,
                )
            cur.execute(
                """
                INSERT INTO almacen.movimientos
                    (producto_id, ubicacion_id, tipo, cantidad, usuario_id)
                VALUES (%s, %s, 'SALIDA', %s, %s)
                """,
                (tarea["producto_id"], tarea["ubicacion_id"], tarea["cantidad"], usuario.id),
            )
            cur.execute(
                """
                UPDATE operaciones.picking_tareas
                SET estado = 'PICKEADO', cantidad_picada = cantidad,
                    completado_por = %s, completado_en = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (usuario.id, tarea_id),
            )
            cur.execute(
                """
                SELECT COUNT(*)::int AS pendientes
                FROM operaciones.picking_tareas
                WHERE pedido_id = %s AND estado = 'PENDIENTE'
                """,
                (tarea["pedido_id"],),
            )
            pendientes_pedido = cur.fetchone()["pendientes"]
            if pendientes_pedido == 0:
                cur.execute(
                    "UPDATE operaciones.pedidos SET estado = 'PICKING_COMPLETO' WHERE id = %s",
                    (tarea["pedido_id"],),
                )
            cur.execute(
                """
                SELECT COUNT(*)::int AS pendientes
                FROM operaciones.picking_tareas
                WHERE ola_id = %s AND estado = 'PENDIENTE'
                """,
                (tarea["ola_id"],),
            )
            pendientes_ola = cur.fetchone()["pendientes"]
            if pendientes_ola == 0:
                cur.execute(
                    "UPDATE operaciones.picking_olas SET estado = 'COMPLETADA' WHERE id = %s",
                    (tarea["ola_id"],),
                )
            registrar_bitacora(
                cur, usuario, "TAREA_PICKING_CONFIRMADA", entidad="picking_tarea",
                entidad_id=tarea_id,
                detalle={
                    "pedido": tarea["pedido_folio"],
                    "producto": tarea["producto"],
                    "cantidad": tarea["cantidad"],
                    "ubicacion": tarea["ubicacion"],
                },
            )
        return self.pedido(tarea["pedido_id"])

    # ------------------------------------------------------------------
    # Empaque y QC
    # ------------------------------------------------------------------
    def empacar(self, pedido_id: int, usuario: UsuarioSesion) -> dict:
        with self.cursor() as cur:
            cur.execute(
                "SELECT id, folio, estado FROM operaciones.pedidos "
                "WHERE id = %s FOR UPDATE",
                (pedido_id,),
            )
            pedido = cur.fetchone()
            if pedido is None:
                raise ErrorNegocio("El pedido no existe.", 404)
            if pedido["estado"] != "PICKING_COMPLETO":
                raise ErrorNegocio(
                    "El pedido debe tener todo el picking confirmado antes de empacar.", 409
                )
            cur.execute(
                "SELECT COUNT(*)::int AS total FROM operaciones.bultos WHERE pedido_id = %s",
                (pedido_id,),
            )
            if cur.fetchone()["total"] > 0:
                raise ErrorNegocio("El pedido ya tiene bultos generados.", 409)

            cur.execute(
                """
                SELECT d.producto_id, d.cantidad, p.nombre, p.peso_kg::float8 AS peso_kg,
                       p.volumen_m3::float8 AS volumen_m3
                FROM operaciones.pedido_detalle d
                JOIN almacen.productos p ON p.id = d.producto_id
                WHERE d.pedido_id = %s
                ORDER BY d.id
                """,
                (pedido_id,),
            )
            lineas = list(cur.fetchall())
            if not lineas:
                raise ErrorNegocio("El pedido no tiene líneas para empacar.", 409)
            peso_total = sum(linea["peso_kg"] * linea["cantidad"] for linea in lineas)
            volumen_total = sum(
                linea["volumen_m3"] * linea["cantidad"] for linea in lineas
            )
            cur.execute("SELECT nextval('operaciones.folio_empaque_seq') AS numero")
            numero = cur.fetchone()["numero"]
            folio_empaque = f"EMP-{date.today():%Y%m%d}-{numero:04d}"
            cur.execute(
                """
                INSERT INTO operaciones.empaques
                    (folio, pedido_id, estado, peso_kg, volumen_m3, usuario_id)
                VALUES (%s, %s, 'EN_PROCESO', %s, %s, %s)
                RETURNING id
                """,
                (folio_empaque, pedido_id, round(peso_total, 3),
                 round(volumen_total, 4), usuario.id),
            )
            empaque_id = cur.fetchone()["id"]

            for linea in lineas:
                cur.execute("SELECT nextval('operaciones.folio_guia_seq') AS numero")
                guia = f"LX-{cur.fetchone()['numero']:05d}"
                peso = round(linea["peso_kg"] * linea["cantidad"], 3)
                volumen = round(linea["volumen_m3"] * linea["cantidad"], 4)
                cur.execute(
                    """
                    INSERT INTO operaciones.bultos
                        (guia, pedido_id, empaque_id, descripcion,
                         peso_kg, volumen_m3, estado)
                    VALUES (%s, %s, %s, %s, %s, %s, 'EN_BODEGA')
                    RETURNING id
                    """,
                    (
                        guia, pedido_id, empaque_id,
                        f"{linea['nombre']} · {linea['cantidad']} pieza(s)",
                        peso, volumen,
                    ),
                )
                bulto_id = cur.fetchone()["id"]
                cur.execute(
                    """
                    INSERT INTO operaciones.eventos_rastreo
                        (bulto_id, estado, descripcion, ubicacion, usuario_id)
                    VALUES (%s, 'ETIQUETADO',
                            'Bulto empacado, pesado y etiquetado en mesa de salida',
                            'Zona de empaque', %s)
                    """,
                    (bulto_id, usuario.id),
                )
            cur.execute(
                "UPDATE operaciones.pedidos SET estado = 'EMPACADO' WHERE id = %s",
                (pedido_id,),
            )
            registrar_bitacora(
                cur, usuario, "PEDIDO_EMPACADO", entidad="pedido", entidad_id=pedido_id,
                detalle={"folio": pedido["folio"], "empaque": folio_empaque,
                         "bultos": len(lineas)},
            )
        return self.pedido(pedido_id)

    def aprobar(self, pedido_id: int, usuario: UsuarioSesion) -> dict:
        with self.cursor() as cur:
            cur.execute(
                "SELECT id, folio, estado FROM operaciones.pedidos "
                "WHERE id = %s FOR UPDATE",
                (pedido_id,),
            )
            pedido = cur.fetchone()
            if pedido is None:
                raise ErrorNegocio("El pedido no existe.", 404)
            if pedido["estado"] != "EMPACADO":
                raise ErrorNegocio(
                    "El pedido debe estar empacado para aprobar el control de calidad.", 409
                )
            cur.execute(
                """
                SELECT id, folio, estado FROM operaciones.empaques
                WHERE pedido_id = %s ORDER BY creado_en DESC LIMIT 1
                FOR UPDATE
                """,
                (pedido_id,),
            )
            empaque = cur.fetchone()
            if empaque is None:
                raise ErrorNegocio("El pedido no tiene un empaque registrado.", 409)
            cur.execute(
                """
                UPDATE operaciones.empaques
                SET estado = 'VALIDADO', validado_por = %s,
                    validado_en = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (usuario.id, empaque["id"]),
            )
            cur.execute(
                "UPDATE operaciones.pedidos SET estado = 'LISTO' WHERE id = %s",
                (pedido_id,),
            )
            registrar_bitacora(
                cur, usuario, "EMPAQUE_APROBADO", entidad="pedido", entidad_id=pedido_id,
                detalle={"folio": pedido["folio"], "empaque": empaque["folio"],
                         "bultos": len(self._bultos_pedido_cur(cur, pedido_id))},
            )
        return self.pedido(pedido_id)

    @staticmethod
    def _bultos_pedido_cur(cur, pedido_id: int) -> list[dict]:
        cur.execute(
            "SELECT id FROM operaciones.bultos WHERE pedido_id = %s", (pedido_id,)
        )
        return list(cur.fetchall())
