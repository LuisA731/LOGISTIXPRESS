"""Recepción de mercancía, órdenes de compra e incidencias."""
from __future__ import annotations

from datetime import date

from ..dependencias import registrar_bitacora
from ..db import BaseDatos
from ..errores import ErrorNegocio
from ..modelos.esquemas_operaciones import OCIn, RecepcionIn
from ..seguridad import UsuarioSesion
from .base import RepositorioBase


class RepositorioRecepcion(RepositorioBase):
    def __init__(self, bd: BaseDatos, rol_bd: str):
        super().__init__(bd, rol_bd)

    # ------------------------------------------------------------------
    # Órdenes de compra / citas
    # ------------------------------------------------------------------
    def ordenes(self, limite: int = 200) -> list[dict]:
        with self.cursor() as cur:
            cur.execute(
                """
                SELECT oc.id, oc.folio, pr.nombre AS proveedor, oc.proveedor_id,
                       oc.estado, oc.fecha_esperada, oc.hora_estimada, oc.anden,
                       oc.observaciones,
                       COALESCE((SELECT SUM(cantidad_solicitada)::int
                                   FROM operaciones.orden_compra_lineas l
                                  WHERE l.orden_compra_id = oc.id), 0) AS total_solicitado,
                       COALESCE((SELECT SUM(cantidad_recibida)::int
                                   FROM operaciones.orden_compra_lineas l
                                  WHERE l.orden_compra_id = oc.id), 0) AS total_recibido
                FROM operaciones.ordenes_compra oc
                JOIN operaciones.proveedores pr ON pr.id = oc.proveedor_id
                ORDER BY oc.fecha_esperada DESC, oc.hora_estimada NULLS LAST
                LIMIT %s
                """,
                (limite,),
            )
            return list(cur.fetchall())

    def orden(self, orden_id: int, bloquear: bool = False) -> dict | None:
        bloqueo = " FOR UPDATE OF oc" if bloquear else ""
        with self.cursor() as cur:
            cur.execute(
                """
                SELECT oc.id, oc.folio, pr.nombre AS proveedor, oc.proveedor_id,
                       oc.estado, oc.fecha_esperada, oc.hora_estimada, oc.anden,
                       oc.observaciones,
                       COALESCE((SELECT SUM(cantidad_solicitada)::int
                                   FROM operaciones.orden_compra_lineas l
                                  WHERE l.orden_compra_id = oc.id), 0) AS total_solicitado,
                       COALESCE((SELECT SUM(cantidad_recibida)::int
                                   FROM operaciones.orden_compra_lineas l
                                  WHERE l.orden_compra_id = oc.id), 0) AS total_recibido
                FROM operaciones.ordenes_compra oc
                JOIN operaciones.proveedores pr ON pr.id = oc.proveedor_id
                WHERE oc.id = %s
                """ + bloqueo,
                (orden_id,),
            )
            orden = cur.fetchone()
            if orden is None:
                return None
            cur.execute(
                """
                SELECT l.id, l.producto_id, p.nombre AS producto, p.sku,
                       l.cantidad_solicitada, l.cantidad_recibida
                FROM operaciones.orden_compra_lineas l
                JOIN almacen.productos p ON p.id = l.producto_id
                WHERE l.orden_compra_id = %s
                ORDER BY l.id
                """,
                (orden_id,),
            )
            orden["lineas"] = list(cur.fetchall())
            return orden

    def crear_orden(self, datos: OCIn, usuario: UsuarioSesion) -> dict:
        agrupadas: dict[int, int] = {}
        for linea in datos.lineas:
            agrupadas[linea.producto_id] = (
                agrupadas.get(linea.producto_id, 0) + linea.cantidad_solicitada
            )
        with self.cursor() as cur:
            cur.execute(
                "SELECT id, activo FROM operaciones.proveedores WHERE id = %s",
                (datos.proveedor_id,),
            )
            proveedor = cur.fetchone()
            if proveedor is None or not proveedor["activo"]:
                raise ErrorNegocio("El proveedor no existe o está inactivo.", 400)
            cur.execute(
                "SELECT id, activo FROM almacen.productos WHERE id = ANY(%s)",
                (list(agrupadas),),
            )
            productos = {f["id"]: f for f in cur.fetchall()}
            if len(productos) != len(agrupadas):
                raise ErrorNegocio("Uno de los productos de la orden no existe.", 400)
            if any(not fila["activo"] for fila in productos.values()):
                raise ErrorNegocio("Uno de los productos de la orden está inactivo.", 409)
            cur.execute("SELECT nextval('operaciones.folio_oc_seq') AS numero")
            numero = cur.fetchone()["numero"]
            folio = f"OC-{date.today():%Y}-{numero:04d}"
            cur.execute(
                """
                INSERT INTO operaciones.ordenes_compra
                    (folio, proveedor_id, estado, fecha_esperada, hora_estimada,
                     anden, observaciones, creado_por)
                VALUES (%s, %s, 'PROGRAMADA', %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    folio, datos.proveedor_id, datos.fecha_esperada,
                    datos.hora_estimada, datos.anden, datos.observaciones, usuario.id,
                ),
            )
            orden_id = cur.fetchone()["id"]
            cur.executemany(
                """
                INSERT INTO operaciones.orden_compra_lineas
                    (orden_compra_id, producto_id, cantidad_solicitada)
                VALUES (%s, %s, %s)
                """,
                [(orden_id, pid, cantidad) for pid, cantidad in agrupadas.items()],
            )
            registrar_bitacora(
                cur, usuario, "ORDEN_COMPRA_CREADA", entidad="orden_compra",
                entidad_id=orden_id,
                detalle={"folio": folio, "proveedor_id": datos.proveedor_id,
                         "lineas": len(agrupadas)},
            )
        return self.orden(orden_id)

    def cancelar_orden(self, orden_id: int, usuario: UsuarioSesion) -> dict:
        with self.cursor() as cur:
            cur.execute(
                "SELECT folio, estado FROM operaciones.ordenes_compra "
                "WHERE id = %s FOR UPDATE",
                (orden_id,),
            )
            orden = cur.fetchone()
            if orden is None:
                raise ErrorNegocio("La orden de compra no existe.", 404)
            if orden["estado"] not in {"PROGRAMADA", "EN_RECEPCION"}:
                raise ErrorNegocio(
                    "Solo se puede cancelar una orden programada o en recepción.", 409
                )
            cur.execute(
                "UPDATE operaciones.ordenes_compra SET estado = 'CANCELADA' WHERE id = %s",
                (orden_id,),
            )
            registrar_bitacora(
                cur, usuario, "ORDEN_COMPRA_CANCELADA", entidad="orden_compra",
                entidad_id=orden_id, detalle={"folio": orden["folio"]},
            )
        return self.orden(orden_id)

    def sugerir_ubicacion(self, producto_id: int) -> dict | None:
        with self.cursor() as cur:
            cur.execute(
                """
                SELECT u.id, u.codigo, u.pasillo, u.rack, u.nivel, u.tipo_zona,
                       COALESCE(s.cantidad, 0)::int AS cantidad
                FROM almacen.ubicaciones u
                LEFT JOIN almacen.stock s
                       ON s.ubicacion_id = u.id AND s.producto_id = %s
                WHERE u.activo = TRUE AND u.tipo_zona = 'GENERAL'
                ORDER BY COALESCE(s.cantidad, 0) ASC, u.orden_picking ASC
                LIMIT 1
                """,
                (producto_id,),
            )
            return cur.fetchone()

    # ------------------------------------------------------------------
    # Recepción
    # ------------------------------------------------------------------
    def recibir(
        self,
        orden_id: int,
        datos: RecepcionIn,
        usuario: UsuarioSesion,
        *,
        foto_url: str | None = None,
    ) -> dict:
        with self.cursor() as cur:
            cur.execute(
                "SELECT id, folio, estado FROM operaciones.ordenes_compra "
                "WHERE id = %s FOR UPDATE",
                (orden_id,),
            )
            orden = cur.fetchone()
            if orden is None:
                raise ErrorNegocio("La orden de compra no existe.", 404)
            if orden["estado"] not in {"PROGRAMADA", "EN_RECEPCION", "CON_INCIDENCIA"}:
                raise ErrorNegocio(
                    f"La orden {orden['folio']} está en estado {orden['estado']} "
                    "y ya no puede recibir mercancía.",
                    409,
                )

            validadas = []
            for linea in datos.lineas:
                cur.execute(
                    """
                    SELECT l.id, l.producto_id, p.nombre AS producto,
                           l.cantidad_solicitada, l.cantidad_recibida
                    FROM operaciones.orden_compra_lineas l
                    JOIN almacen.productos p ON p.id = l.producto_id
                    WHERE l.id = %s AND l.orden_compra_id = %s
                    FOR UPDATE OF l
                    """,
                    (linea.linea_id, orden_id),
                )
                fila = cur.fetchone()
                if fila is None:
                    raise ErrorNegocio(
                        "Una de las líneas no pertenece a esta orden de compra.", 400
                    )
                pendiente = fila["cantidad_solicitada"] - fila["cantidad_recibida"]
                if linea.cantidad_recibida > pendiente:
                    raise ErrorNegocio(
                        f"La línea {fila['producto']} solo tiene {pendiente} "
                        "unidades pendientes de recibir.",
                        409,
                    )
                cur.execute(
                    "SELECT id, codigo, tipo_zona FROM almacen.ubicaciones "
                    "WHERE id = %s AND activo = TRUE",
                    (linea.ubicacion_id,),
                )
                ubicacion = cur.fetchone()
                if ubicacion is None:
                    raise ErrorNegocio(
                        "La ubicación de destino no existe o está inactiva.", 400
                    )
                validadas.append((linea, fila, ubicacion))

            cur.execute(
                """
                INSERT INTO operaciones.recepciones
                    (orden_compra_id, recibido_por, observaciones)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (orden_id, usuario.id, datos.observaciones),
            )
            recepcion_id = cur.fetchone()["id"]
            incidencias_auto = 0

            for linea, fila, ubicacion in validadas:
                cur.execute(
                    """
                    INSERT INTO almacen.movimientos
                        (producto_id, ubicacion_id, tipo, cantidad, usuario_id)
                    VALUES (%s, %s, 'ENTRADA', %s, %s)
                    """,
                    (fila["producto_id"], linea.ubicacion_id, linea.cantidad_recibida, usuario.id),
                )
                if linea.lote:
                    cur.execute(
                        """
                        INSERT INTO almacen.lotes
                            (producto_id, ubicacion_id, lote, caducidad,
                             cantidad, condicion)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (producto_id, lote) DO UPDATE SET
                            ubicacion_id = EXCLUDED.ubicacion_id,
                            caducidad = COALESCE(EXCLUDED.caducidad,
                                                 almacen.lotes.caducidad),
                            cantidad = almacen.lotes.cantidad + EXCLUDED.cantidad,
                            condicion = EXCLUDED.condicion
                        """,
                        (
                            fila["producto_id"], linea.ubicacion_id,
                            linea.lote.strip().upper(), linea.caducidad,
                            linea.cantidad_recibida, linea.condicion,
                        ),
                    )
                cur.execute(
                    """
                    INSERT INTO operaciones.recepcion_lineas
                        (recepcion_id, orden_compra_linea_id, producto_id,
                         ubicacion_id, lote, caducidad, condicion, cantidad_recibida)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        recepcion_id, fila["id"], fila["producto_id"], linea.ubicacion_id,
                        linea.lote.strip().upper() if linea.lote else None,
                        linea.caducidad, linea.condicion, linea.cantidad_recibida,
                    ),
                )
                cur.execute(
                    "UPDATE operaciones.orden_compra_lineas "
                    "SET cantidad_recibida = cantidad_recibida + %s WHERE id = %s",
                    (linea.cantidad_recibida, fila["id"]),
                )
                if linea.condicion != "BUENO":
                    incidencias_auto += 1
                    cur.execute(
                        """
                        INSERT INTO operaciones.incidencias_recepcion
                            (recepcion_id, producto_id, descripcion, responsable, comentario)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (
                            recepcion_id, fila["producto_id"],
                            f"Producto recibido en condición {linea.condicion}",
                            usuario.nombre,
                            f"Lote {linea.lote or 'sin lote'} · ubicación {ubicacion['codigo']}",
                        ),
                    )

            if datos.incidencia:
                cur.execute(
                    """
                    INSERT INTO operaciones.incidencias_recepcion
                        (recepcion_id, producto_id, descripcion, foto_url,
                         responsable, comentario)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        recepcion_id, datos.incidencia.producto_id,
                        datos.incidencia.descripcion.strip(), foto_url, usuario.nombre,
                        datos.incidencia.comentario,
                    ),
                )
                incidencias_auto += 1

            cur.execute(
                """
                SELECT COALESCE(SUM(cantidad_solicitada), 0)::int AS solicitado,
                       COALESCE(SUM(cantidad_recibida), 0)::int AS recibido
                FROM operaciones.orden_compra_lineas
                WHERE orden_compra_id = %s
                """,
                (orden_id,),
            )
            totales = cur.fetchone()
            completa = totales["recibido"] >= totales["solicitado"]
            if incidencias_auto:
                estado = "CON_INCIDENCIA"
            elif completa:
                estado = "RECIBIDA"
            else:
                estado = "EN_RECEPCION"
            cur.execute(
                """
                UPDATE operaciones.ordenes_compra
                SET estado = %s,
                    recibido_en = CASE WHEN %s THEN CURRENT_TIMESTAMP ELSE recibido_en END
                WHERE id = %s
                """,
                (estado, completa, orden_id),
            )
            registrar_bitacora(
                cur, usuario, "RECEPCION_REGISTRADA", entidad="recepcion",
                entidad_id=recepcion_id,
                detalle={
                    "orden": orden["folio"],
                    "lineas": len(validadas),
                    "recibido": totales["recibido"],
                    "solicitado": totales["solicitado"],
                    "incidencias": incidencias_auto,
                },
            )
        return self.recepcion(recepcion_id)

    def recepcion(self, recepcion_id: int) -> dict:
        with self.cursor() as cur:
            cur.execute(
                """
                SELECT r.id, oc.folio AS orden_folio, pr.nombre AS proveedor,
                       COALESCE(u.nombre, '—') AS recibido_por, r.fecha, r.observaciones
                FROM operaciones.recepciones r
                JOIN operaciones.ordenes_compra oc ON oc.id = r.orden_compra_id
                JOIN operaciones.proveedores pr ON pr.id = oc.proveedor_id
                LEFT JOIN seguridad.usuarios u ON u.id = r.recibido_por
                WHERE r.id = %s
                """,
                (recepcion_id,),
            )
            recepcion = cur.fetchone()
            if recepcion is None:
                raise ErrorNegocio("La recepción no existe.", 404)
            cur.execute(
                """
                SELECT p.nombre AS producto, p.sku, u.codigo AS ubicacion,
                       rl.lote, rl.caducidad, rl.condicion, rl.cantidad_recibida
                FROM operaciones.recepcion_lineas rl
                JOIN almacen.productos p ON p.id = rl.producto_id
                JOIN almacen.ubicaciones u ON u.id = rl.ubicacion_id
                WHERE rl.recepcion_id = %s
                ORDER BY rl.id
                """,
                (recepcion_id,),
            )
            recepcion["lineas"] = list(cur.fetchall())
            return recepcion

    def incidencias(self, limite: int = 100) -> list[dict]:
        with self.cursor() as cur:
            cur.execute(
                """
                SELECT i.id, oc.folio AS orden_folio, pr.nombre AS proveedor,
                       p.nombre AS producto, i.descripcion, i.foto_url,
                       i.responsable, i.comentario, i.fecha
                FROM operaciones.incidencias_recepcion i
                JOIN operaciones.recepciones r ON r.id = i.recepcion_id
                JOIN operaciones.ordenes_compra oc ON oc.id = r.orden_compra_id
                JOIN operaciones.proveedores pr ON pr.id = oc.proveedor_id
                LEFT JOIN almacen.productos p ON p.id = i.producto_id
                ORDER BY i.fecha DESC, i.id DESC
                LIMIT %s
                """,
                (limite,),
            )
            filas = list(cur.fetchall())
        for fila in filas:
            fila["foto_url"] = (
                f"/api/recepcion/incidencias/{fila['id']}/foto"
                if fila["foto_url"] else None
            )
        return filas

    def foto_incidencia(self, incidencia_id: int) -> dict | None:
        with self.cursor() as cur:
            cur.execute(
                "SELECT foto_url FROM operaciones.incidencias_recepcion WHERE id = %s",
                (incidencia_id,),
            )
            return cur.fetchone()
