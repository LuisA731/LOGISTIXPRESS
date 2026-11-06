"""CRUD de datos maestros y pedidos."""
from __future__ import annotations

from datetime import date

from ..dependencias import registrar_bitacora
from ..db import BaseDatos
from ..errores import ErrorNegocio
from ..modelos.esquemas_operaciones import (
    ClienteActualizar,
    ClienteIn,
    LoteActualizar,
    LoteIn,
    PedidoActualizar,
    PedidoIn,
    ProductoActualizar,
    ProductoIn,
    ProveedorActualizar,
    ProveedorIn,
    UbicacionActualizar,
    UbicacionIn,
)
from ..seguridad import UsuarioSesion
from .base import RepositorioBase


class RepositorioMaestros(RepositorioBase):
    def __init__(self, bd: BaseDatos, rol_bd: str):
        super().__init__(bd, rol_bd)

    # ------------------------------------------------------------------
    # Clientes
    # ------------------------------------------------------------------
    def clientes(self) -> list[dict]:
        with self.cursor() as cur:
            cur.execute(
                """
                SELECT id, codigo, nombre, tipo_cliente, zona, direccion, colonia,
                       telefono, contacto,
                       latitud::float8 AS latitud, longitud::float8 AS longitud, activo
                FROM operaciones.clientes
                ORDER BY activo DESC, nombre
                """
            )
            return list(cur.fetchall())

    def crear_cliente(self, datos: ClienteIn, usuario: UsuarioSesion) -> dict:
        with self.cursor() as cur:
            cur.execute(
                """
                INSERT INTO operaciones.clientes
                    (codigo, nombre, tipo_cliente, zona, direccion, colonia,
                     telefono, contacto, latitud, longitud)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, codigo, nombre, tipo_cliente, zona, direccion, colonia,
                          telefono, contacto,
                          latitud::float8 AS latitud, longitud::float8 AS longitud, activo
                """,
                (
                    datos.codigo.strip().upper(), datos.nombre.strip(), datos.tipo_cliente,
                    datos.zona, datos.direccion, datos.colonia, datos.telefono,
                    datos.contacto, datos.latitud, datos.longitud,
                ),
            )
            cliente = cur.fetchone()
            registrar_bitacora(
                cur, usuario, "CLIENTE_CREADO", entidad="cliente",
                entidad_id=cliente["id"],
                detalle={"codigo": cliente["codigo"], "nombre": cliente["nombre"]},
            )
            return cliente

    def actualizar_cliente(
        self, cliente_id: int, datos: ClienteActualizar, usuario: UsuarioSesion
    ) -> dict:
        with self.cursor() as cur:
            cur.execute(
                """
                UPDATE operaciones.clientes
                SET nombre = COALESCE(%s, nombre),
                    tipo_cliente = COALESCE(%s, tipo_cliente),
                    zona = COALESCE(%s, zona),
                    direccion = COALESCE(%s, direccion),
                    colonia = COALESCE(%s, colonia),
                    telefono = COALESCE(%s, telefono),
                    contacto = COALESCE(%s, contacto),
                    latitud = COALESCE(%s, latitud),
                    longitud = COALESCE(%s, longitud),
                    activo = COALESCE(%s, activo)
                WHERE id = %s
                RETURNING id, codigo, nombre, tipo_cliente, zona, direccion, colonia,
                          telefono, contacto,
                          latitud::float8 AS latitud, longitud::float8 AS longitud, activo
                """,
                (
                    datos.nombre, datos.tipo_cliente, datos.zona, datos.direccion,
                    datos.colonia, datos.telefono, datos.contacto, datos.latitud,
                    datos.longitud, datos.activo, cliente_id,
                ),
            )
            cliente = cur.fetchone()
            if cliente is None:
                raise ErrorNegocio("El cliente no existe.", 404)
            registrar_bitacora(
                cur, usuario, "CLIENTE_ACTUALIZADO", entidad="cliente",
                entidad_id=cliente_id,
                detalle={"codigo": cliente["codigo"], "activo": cliente["activo"]},
            )
            return cliente

    # ------------------------------------------------------------------
    # Productos
    # ------------------------------------------------------------------
    def productos(self) -> list[dict]:
        with self.cursor() as cur:
            cur.execute(
                """
                SELECT p.id, p.sku, p.nombre, p.stock_minimo,
                       p.peso_kg::float8 AS peso_kg,
                       p.volumen_m3::float8 AS volumen_m3,
                       p.activo,
                       COALESCE((SELECT SUM(s.cantidad) FROM almacen.stock s
                                  WHERE s.producto_id = p.id), 0)::int AS stock_total
                FROM almacen.productos p
                ORDER BY p.activo DESC, p.nombre
                """
            )
            return list(cur.fetchall())

    def crear_producto(self, datos: ProductoIn, usuario: UsuarioSesion) -> dict:
        with self.cursor() as cur:
            cur.execute(
                """
                INSERT INTO almacen.productos
                    (sku, nombre, stock_minimo, peso_kg, volumen_m3)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, sku, nombre, stock_minimo,
                          peso_kg::float8 AS peso_kg,
                          volumen_m3::float8 AS volumen_m3, activo
                """,
                (
                    datos.sku.strip().upper(), datos.nombre.strip(), datos.stock_minimo,
                    datos.peso_kg, datos.volumen_m3,
                ),
            )
            producto = cur.fetchone()
            producto["stock_total"] = 0
            registrar_bitacora(
                cur, usuario, "PRODUCTO_CREADO", entidad="producto",
                entidad_id=producto["id"],
                detalle={"sku": producto["sku"], "nombre": producto["nombre"]},
            )
            return producto

    def actualizar_producto(
        self, producto_id: int, datos: ProductoActualizar, usuario: UsuarioSesion
    ) -> dict:
        with self.cursor() as cur:
            cur.execute(
                """
                UPDATE almacen.productos
                SET nombre = COALESCE(%s, nombre),
                    stock_minimo = COALESCE(%s, stock_minimo),
                    peso_kg = COALESCE(%s, peso_kg),
                    volumen_m3 = COALESCE(%s, volumen_m3),
                    activo = COALESCE(%s, activo)
                WHERE id = %s
                RETURNING id, sku, nombre, stock_minimo,
                          peso_kg::float8 AS peso_kg,
                          volumen_m3::float8 AS volumen_m3, activo
                """,
                (
                    datos.nombre, datos.stock_minimo, datos.peso_kg, datos.volumen_m3,
                    datos.activo, producto_id,
                ),
            )
            producto = cur.fetchone()
            if producto is None:
                raise ErrorNegocio("El producto no existe.", 404)
            cur.execute(
                "SELECT COALESCE(SUM(cantidad), 0)::int AS total FROM almacen.stock "
                "WHERE producto_id = %s",
                (producto_id,),
            )
            producto["stock_total"] = cur.fetchone()["total"]
            registrar_bitacora(
                cur, usuario, "PRODUCTO_ACTUALIZADO", entidad="producto",
                entidad_id=producto_id,
                detalle={"sku": producto["sku"], "activo": producto["activo"]},
            )
            return producto

    # ------------------------------------------------------------------
    # Ubicaciones
    # ------------------------------------------------------------------
    def ubicaciones(self) -> list[dict]:
        with self.cursor() as cur:
            cur.execute(
                """
                SELECT u.id, u.codigo, u.pasillo, u.rack, u.nivel, u.orden_picking,
                       u.tipo_zona, u.activo,
                       COALESCE((SELECT SUM(s.cantidad) FROM almacen.stock s
                                  WHERE s.ubicacion_id = u.id), 0)::int AS stock_total
                FROM almacen.ubicaciones u
                ORDER BY u.activo DESC, u.orden_picking
                """
            )
            return list(cur.fetchall())

    def crear_ubicacion(self, datos: UbicacionIn, usuario: UsuarioSesion) -> dict:
        with self.cursor() as cur:
            cur.execute(
                """
                INSERT INTO almacen.ubicaciones
                    (codigo, pasillo, rack, nivel, orden_picking, tipo_zona)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id, codigo, pasillo, rack, nivel, orden_picking,
                          tipo_zona, activo
                """,
                (
                    datos.codigo.strip().upper(), datos.pasillo.strip().upper(),
                    datos.rack.strip(), datos.nivel, datos.orden_picking, datos.tipo_zona,
                ),
            )
            ubicacion = cur.fetchone()
            ubicacion["stock_total"] = 0
            registrar_bitacora(
                cur, usuario, "UBICACION_CREADA", entidad="ubicacion",
                entidad_id=ubicacion["id"],
                detalle={"codigo": ubicacion["codigo"], "zona": ubicacion["tipo_zona"]},
            )
            return ubicacion

    def actualizar_ubicacion(
        self, ubicacion_id: int, datos: UbicacionActualizar, usuario: UsuarioSesion
    ) -> dict:
        with self.cursor() as cur:
            cur.execute(
                """
                UPDATE almacen.ubicaciones
                SET pasillo = COALESCE(%s, pasillo),
                    rack = COALESCE(%s, rack),
                    nivel = COALESCE(%s, nivel),
                    orden_picking = COALESCE(%s, orden_picking),
                    tipo_zona = COALESCE(%s, tipo_zona),
                    activo = COALESCE(%s, activo)
                WHERE id = %s
                RETURNING id, codigo, pasillo, rack, nivel, orden_picking,
                          tipo_zona, activo
                """,
                (
                    datos.pasillo, datos.rack, datos.nivel, datos.orden_picking,
                    datos.tipo_zona, datos.activo, ubicacion_id,
                ),
            )
            ubicacion = cur.fetchone()
            if ubicacion is None:
                raise ErrorNegocio("La ubicación no existe.", 404)
            cur.execute(
                "SELECT COALESCE(SUM(cantidad), 0)::int AS total FROM almacen.stock "
                "WHERE ubicacion_id = %s",
                (ubicacion_id,),
            )
            ubicacion["stock_total"] = cur.fetchone()["total"]
            registrar_bitacora(
                cur, usuario, "UBICACION_ACTUALIZADA", entidad="ubicacion",
                entidad_id=ubicacion_id,
                detalle={"codigo": ubicacion["codigo"], "zona": ubicacion["tipo_zona"]},
            )
            return ubicacion

    # ------------------------------------------------------------------
    # Lotes
    # ------------------------------------------------------------------
    def lotes(self) -> list[dict]:
        with self.cursor() as cur:
            cur.execute(
                """
                SELECT l.id, l.producto_id, p.nombre AS producto, p.sku,
                       u.codigo AS ubicacion, l.lote, l.caducidad, l.cantidad, l.condicion
                FROM almacen.lotes l
                JOIN almacen.productos p ON p.id = l.producto_id
                JOIN almacen.ubicaciones u ON u.id = l.ubicacion_id
                ORDER BY l.caducidad NULLS LAST, l.lote
                """
            )
            return list(cur.fetchall())

    def crear_lote(self, datos: LoteIn, usuario: UsuarioSesion) -> dict:
        with self.cursor() as cur:
            cur.execute(
                """
                INSERT INTO almacen.lotes
                    (producto_id, ubicacion_id, lote, caducidad, cantidad, condicion)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    datos.producto_id, datos.ubicacion_id, datos.lote.strip().upper(),
                    datos.caducidad, datos.cantidad, datos.condicion,
                ),
            )
            lote_id = cur.fetchone()["id"]
            registrar_bitacora(
                cur, usuario, "LOTE_CREADO", entidad="lote", entidad_id=lote_id,
                detalle={"lote": datos.lote, "producto_id": datos.producto_id},
            )
        return self._lote(lote_id)

    def actualizar_lote(
        self, lote_id: int, datos: LoteActualizar, usuario: UsuarioSesion
    ) -> dict:
        with self.cursor() as cur:
            cur.execute(
                """
                UPDATE almacen.lotes
                SET ubicacion_id = COALESCE(%s, ubicacion_id),
                    caducidad = COALESCE(%s, caducidad),
                    cantidad = COALESCE(%s, cantidad),
                    condicion = COALESCE(%s, condicion)
                WHERE id = %s
                RETURNING id
                """,
                (datos.ubicacion_id, datos.caducidad, datos.cantidad,
                 datos.condicion, lote_id),
            )
            fila = cur.fetchone()
            if fila is None:
                raise ErrorNegocio("El lote no existe.", 404)
            registrar_bitacora(
                cur, usuario, "LOTE_ACTUALIZADO", entidad="lote", entidad_id=lote_id,
            )
        return self._lote(lote_id)

    def _lote(self, lote_id: int) -> dict:
        with self.cursor() as cur:
            cur.execute(
                """
                SELECT l.id, l.producto_id, p.nombre AS producto, p.sku,
                       u.codigo AS ubicacion, l.lote, l.caducidad, l.cantidad, l.condicion
                FROM almacen.lotes l
                JOIN almacen.productos p ON p.id = l.producto_id
                JOIN almacen.ubicaciones u ON u.id = l.ubicacion_id
                WHERE l.id = %s
                """,
                (lote_id,),
            )
            return cur.fetchone()

    # ------------------------------------------------------------------
    # Proveedores
    # ------------------------------------------------------------------
    def proveedores(self) -> list[dict]:
        with self.cursor() as cur:
            cur.execute(
                """
                SELECT id, codigo, nombre, contacto, telefono, correo, activo
                FROM operaciones.proveedores
                ORDER BY activo DESC, nombre
                """
            )
            return list(cur.fetchall())

    def crear_proveedor(self, datos: ProveedorIn, usuario: UsuarioSesion) -> dict:
        with self.cursor() as cur:
            cur.execute(
                """
                INSERT INTO operaciones.proveedores
                    (codigo, nombre, contacto, telefono, correo)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, codigo, nombre, contacto, telefono, correo, activo
                """,
                (
                    datos.codigo.strip().upper(), datos.nombre.strip(), datos.contacto,
                    datos.telefono, datos.correo,
                ),
            )
            proveedor = cur.fetchone()
            registrar_bitacora(
                cur, usuario, "PROVEEDOR_CREADO", entidad="proveedor",
                entidad_id=proveedor["id"],
                detalle={"codigo": proveedor["codigo"], "nombre": proveedor["nombre"]},
            )
            return proveedor

    def actualizar_proveedor(
        self, proveedor_id: int, datos: ProveedorActualizar, usuario: UsuarioSesion
    ) -> dict:
        with self.cursor() as cur:
            cur.execute(
                """
                UPDATE operaciones.proveedores
                SET nombre = COALESCE(%s, nombre),
                    contacto = COALESCE(%s, contacto),
                    telefono = COALESCE(%s, telefono),
                    correo = COALESCE(%s, correo),
                    activo = COALESCE(%s, activo)
                WHERE id = %s
                RETURNING id, codigo, nombre, contacto, telefono, correo, activo
                """,
                (
                    datos.nombre, datos.contacto, datos.telefono, datos.correo,
                    datos.activo, proveedor_id,
                ),
            )
            proveedor = cur.fetchone()
            if proveedor is None:
                raise ErrorNegocio("El proveedor no existe.", 404)
            registrar_bitacora(
                cur, usuario, "PROVEEDOR_ACTUALIZADO", entidad="proveedor",
                entidad_id=proveedor_id, detalle={"codigo": proveedor["codigo"]},
            )
            return proveedor

    # ------------------------------------------------------------------
    # Pedidos
    # ------------------------------------------------------------------
    def pedidos(self, limite: int = 200) -> list[dict]:
        with self.cursor() as cur:
            cur.execute(
                """
                SELECT p.id, p.folio, p.cliente_id, c.nombre AS cliente,
                       c.codigo AS cliente_codigo,
                       p.estado, p.prioridad, p.fecha_pedido, p.fecha_compromiso,
                       p.peso_kg::float8 AS peso_kg,
                       p.volumen_m3::float8 AS volumen_m3, p.observaciones,
                       (SELECT COUNT(*)::int FROM operaciones.pedido_detalle d
                         WHERE d.pedido_id = p.id) AS num_lineas,
                       (SELECT COUNT(*)::int FROM operaciones.bultos b
                         WHERE b.pedido_id = p.id) AS num_bultos
                FROM operaciones.pedidos p
                JOIN operaciones.clientes c ON c.id = p.cliente_id
                ORDER BY p.creado_en DESC
                LIMIT %s
                """,
                (limite,),
            )
            return list(cur.fetchall())

    def pedido(self, pedido_id: int) -> dict | None:
        with self.cursor() as cur:
            cur.execute(
                """
                SELECT p.id, p.folio, p.cliente_id, c.nombre AS cliente,
                       c.codigo AS cliente_codigo,
                       p.estado, p.prioridad, p.fecha_pedido, p.fecha_compromiso,
                       p.peso_kg::float8 AS peso_kg,
                       p.volumen_m3::float8 AS volumen_m3, p.observaciones,
                       (SELECT COUNT(*)::int FROM operaciones.pedido_detalle d
                         WHERE d.pedido_id = p.id) AS num_lineas,
                       (SELECT COUNT(*)::int FROM operaciones.bultos b
                         WHERE b.pedido_id = p.id) AS num_bultos
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
            return pedido

    def _lineas_validadas(
        self, cur, lineas
    ) -> tuple[dict[int, int], float, float]:
        agrupadas: dict[int, int] = {}
        for linea in lineas:
            if linea.cantidad <= 0:
                raise ErrorNegocio("Las cantidades del pedido deben ser mayores a cero.", 400)
            agrupadas[linea.producto_id] = agrupadas.get(linea.producto_id, 0) + linea.cantidad
        ids = list(agrupadas)
        cur.execute(
            """
            SELECT id, nombre, peso_kg::float8 AS peso_kg,
                   volumen_m3::float8 AS volumen_m3, activo
            FROM almacen.productos WHERE id = ANY(%s)
            """,
            (ids,),
        )
        productos = {fila["id"]: fila for fila in cur.fetchall()}
        if len(productos) != len(ids):
            raise ErrorNegocio("Uno de los productos del pedido no existe.", 400)
        if any(not fila["activo"] for fila in productos.values()):
            raise ErrorNegocio("Uno de los productos del pedido está inactivo.", 409)
        peso = sum(productos[pid]["peso_kg"] * cantidad for pid, cantidad in agrupadas.items())
        volumen = sum(
            productos[pid]["volumen_m3"] * cantidad for pid, cantidad in agrupadas.items()
        )
        return agrupadas, round(peso, 3), round(volumen, 4)

    def crear_pedido(self, datos: PedidoIn, usuario: UsuarioSesion) -> dict:
        with self.cursor() as cur:
            cur.execute(
                "SELECT id, activo FROM operaciones.clientes WHERE id = %s",
                (datos.cliente_id,),
            )
            cliente = cur.fetchone()
            if cliente is None or not cliente["activo"]:
                raise ErrorNegocio("El cliente no existe o está inactivo.", 400)
            agrupadas, peso, volumen = self._lineas_validadas(cur, datos.lineas)
            cur.execute("SELECT nextval('operaciones.folio_pedido_seq') AS numero")
            numero = cur.fetchone()["numero"]
            folio = f"PED-{date.today():%Y}-{numero:04d}"
            cur.execute(
                """
                INSERT INTO operaciones.pedidos
                    (folio, cliente_id, estado, prioridad, fecha_pedido,
                     fecha_compromiso, peso_kg, volumen_m3, observaciones)
                VALUES (%s, %s, 'BORRADOR', %s, CURRENT_DATE, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    folio, datos.cliente_id, datos.prioridad, datos.fecha_compromiso,
                    peso, volumen, datos.observaciones,
                ),
            )
            pedido_id = cur.fetchone()["id"]
            cur.executemany(
                "INSERT INTO operaciones.pedido_detalle (pedido_id, producto_id, cantidad) "
                "VALUES (%s, %s, %s)",
                [(pedido_id, pid, cantidad) for pid, cantidad in agrupadas.items()],
            )
            registrar_bitacora(
                cur, usuario, "PEDIDO_CREADO", entidad="pedido", entidad_id=pedido_id,
                detalle={"folio": folio, "cliente_id": datos.cliente_id,
                         "lineas": len(agrupadas), "peso_kg": peso},
            )
        return self.pedido(pedido_id)

    def actualizar_pedido(
        self, pedido_id: int, datos: PedidoActualizar, usuario: UsuarioSesion
    ) -> dict:
        with self.cursor() as cur:
            cur.execute(
                "SELECT folio, estado FROM operaciones.pedidos WHERE id = %s FOR UPDATE",
                (pedido_id,),
            )
            fila = cur.fetchone()
            if fila is None:
                raise ErrorNegocio("El pedido no existe.", 404)
            if fila["estado"] != "BORRADOR":
                raise ErrorNegocio(
                    "Solo se puede editar un pedido en estado BORRADOR.", 409
                )
            if datos.lineas is not None and not datos.lineas:
                raise ErrorNegocio("El pedido debe conservar al menos una línea.", 400)
            if datos.cliente_id is not None:
                cur.execute(
                    "SELECT id, activo FROM operaciones.clientes WHERE id = %s",
                    (datos.cliente_id,),
                )
                cliente = cur.fetchone()
                if cliente is None or not cliente["activo"]:
                    raise ErrorNegocio("El cliente no existe o está inactivo.", 400)
            peso = None
            volumen = None
            if datos.lineas is not None:
                agrupadas, peso, volumen = self._lineas_validadas(cur, datos.lineas)
                cur.execute(
                    "DELETE FROM operaciones.pedido_detalle WHERE pedido_id = %s",
                    (pedido_id,),
                )
                cur.executemany(
                    "INSERT INTO operaciones.pedido_detalle (pedido_id, producto_id, cantidad) "
                    "VALUES (%s, %s, %s)",
                    [(pedido_id, pid, cantidad) for pid, cantidad in agrupadas.items()],
                )
            cur.execute(
                """
                UPDATE operaciones.pedidos
                SET cliente_id = COALESCE(%s, cliente_id),
                    prioridad = COALESCE(%s, prioridad),
                    fecha_compromiso = COALESCE(%s, fecha_compromiso),
                    observaciones = COALESCE(%s, observaciones),
                    peso_kg = COALESCE(%s, peso_kg),
                    volumen_m3 = COALESCE(%s, volumen_m3)
                WHERE id = %s
                """,
                (
                    datos.cliente_id, datos.prioridad, datos.fecha_compromiso,
                    datos.observaciones, peso, volumen, pedido_id,
                ),
            )
            registrar_bitacora(
                cur, usuario, "PEDIDO_ACTUALIZADO", entidad="pedido",
                entidad_id=pedido_id, detalle={"folio": fila["folio"]},
            )
        return self.pedido(pedido_id)

    def cancelar_pedido(self, pedido_id: int, usuario: UsuarioSesion) -> dict:
        with self.cursor() as cur:
            cur.execute(
                "SELECT folio, estado FROM operaciones.pedidos WHERE id = %s FOR UPDATE",
                (pedido_id,),
            )
            pedido = cur.fetchone()
            if pedido is None:
                raise ErrorNegocio("El pedido no existe.", 404)
            if pedido["estado"] not in {"BORRADOR", "LISTO"}:
                raise ErrorNegocio(
                    "Solo se puede cancelar un pedido en BORRADOR o LISTO sin ruta.", 409
                )
            cur.execute(
                "UPDATE operaciones.pedidos SET estado = 'CANCELADO' WHERE id = %s",
                (pedido_id,),
            )
            registrar_bitacora(
                cur, usuario, "PEDIDO_CANCELADO", entidad="pedido",
                entidad_id=pedido_id, detalle={"folio": pedido["folio"]},
            )
        return self.pedido(pedido_id)

