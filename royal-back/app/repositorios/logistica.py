"""Repositorio de rutas, despacho, entregas y flota."""
from __future__ import annotations

from datetime import date

from ..dependencias import registrar_bitacora
from ..db import BaseDatos
from ..modelos.dominio import (
    BultoPlan,
    ClientePlan,
    ConductorPlan,
    PedidoPlan,
    PuntoGeo,
    VehiculoPlan,
    Zona,
)
from ..seguridad import UsuarioSesion
from .base import RepositorioBase


_SELECT_RUTA = """
SELECT r.id,
       r.folio,
       r.zona,
       r.fecha,
       r.estado,
       r.distancia_km::float8       AS distancia_km,
       r.distancia_base_km::float8  AS distancia_base_km,
       r.ahorro_pct::float8         AS ahorro_pct,
       r.eta_min::float8            AS eta_min,
       r.salida_en,
       r.cierre_en,
       v.id                           AS vehiculo_id,
       v.placas,
       v.modelo,
       v.capacidad_kg::float8        AS capacidad_kg,
       v.capacidad_m3::float8        AS capacidad_m3,
       c.id                           AS conductor_id,
       c.nombre                       AS conductor,
       c.telefono                     AS conductor_telefono,
       c.licencia                     AS conductor_licencia,
       (SELECT COUNT(*)::int FROM operaciones.ruta_paradas rp
         WHERE rp.ruta_id = r.id)                                  AS num_paradas,
       (SELECT COUNT(*)::int FROM operaciones.ruta_bultos rb
         JOIN operaciones.ruta_paradas rp ON rp.id = rb.ruta_parada_id
         WHERE rp.ruta_id = r.id)                                  AS num_bultos,
       COALESCE((SELECT SUM(p.peso_kg)::float8
                   FROM operaciones.ruta_paradas rp
                   JOIN operaciones.pedidos p ON p.id = rp.pedido_id
                  WHERE rp.ruta_id = r.id), 0)                     AS peso_total_kg,
       COALESCE((SELECT SUM(p.volumen_m3)::float8
                   FROM operaciones.ruta_paradas rp
                   JOIN operaciones.pedidos p ON p.id = rp.pedido_id
                  WHERE rp.ruta_id = r.id), 0)                     AS volumen_total_m3,
       COALESCE((SELECT mode() WITHIN GROUP (ORDER BY c.tipo_cliente)
                   FROM operaciones.ruta_paradas rp
                   JOIN operaciones.clientes c ON c.id = rp.cliente_id
                  WHERE rp.ruta_id = r.id), 'MIXTO')               AS tipo_principal
FROM operaciones.rutas r
JOIN operaciones.vehiculos v ON v.id = r.vehiculo_id
JOIN operaciones.conductores c ON c.id = r.conductor_id
"""


def _resumen_ruta(fila: dict) -> dict:
    return {
        "id": fila["id"],
        "folio": fila["folio"],
        "zona": fila["zona"],
        "fecha": fila["fecha"],
        "estado": fila["estado"],
        "vehiculo": {
            "id": fila["vehiculo_id"],
            "placas": fila["placas"],
            "modelo": fila["modelo"],
            "capacidad_kg": fila["capacidad_kg"],
            "capacidad_m3": fila["capacidad_m3"],
            "activo": True,
        },
        "conductor": {
            "id": fila["conductor_id"],
            "nombre": fila["conductor"],
            "telefono": fila["conductor_telefono"],
            "licencia": fila["conductor_licencia"],
            "activo": True,
        },
        "num_paradas": fila["num_paradas"],
        "num_bultos": fila["num_bultos"],
        "peso_total_kg": fila["peso_total_kg"],
        "volumen_total_m3": fila["volumen_total_m3"],
        "tipo_principal": fila["tipo_principal"],
        "distancia_km": fila["distancia_km"],
        "distancia_base_km": fila["distancia_base_km"],
        "ahorro_pct": fila["ahorro_pct"],
        "eta_min": fila["eta_min"],
        "salida_en": fila["salida_en"],
        "cierre_en": fila["cierre_en"],
        "mapa_url": f"/api/rutas/{fila['id']}/mapa",
    }


class RepositorioRutas(RepositorioBase):
    def __init__(self, bd: BaseDatos, rol_bd: str):
        super().__init__(bd, rol_bd)

    # ------------------------------------------------------------------
    # Planificación
    # ------------------------------------------------------------------
    def pedidos_listos(self, bloquear: bool = False) -> list[PedidoPlan]:
        bloqueo = " FOR UPDATE OF p SKIP LOCKED" if bloquear else ""
        sql = f"""
            SELECT p.id,
                   p.folio,
                   p.prioridad,
                   p.peso_kg::float8     AS peso_kg,
                   p.volumen_m3::float8  AS volumen_m3,
                   c.id                   AS cliente_id,
                   c.codigo,
                   c.nombre,
                   c.tipo_cliente,
                   c.zona,
                   c.direccion,
                   c.telefono,
                   c.latitud::float8      AS latitud,
                   c.longitud::float8     AS longitud
            FROM operaciones.pedidos p
            JOIN operaciones.clientes c ON c.id = p.cliente_id
            WHERE p.estado = 'LISTO'
              AND NOT EXISTS (
                  SELECT 1
                  FROM operaciones.ruta_paradas rp
                  JOIN operaciones.rutas r ON r.id = rp.ruta_id
                  WHERE rp.pedido_id = p.id
                    AND r.estado IN ('PLANIFICADA', 'EN_RUTA')
              )
            ORDER BY c.zona, p.prioridad DESC, p.id
            {bloqueo}
        """
        with self.cursor() as cur:
            cur.execute("SELECT pg_advisory_xact_lock(hashtext('logistixpress_plan'))")
            cur.execute(sql)
            pedidos = list(cur.fetchall())
            if not pedidos:
                return []

            ids = [p["id"] for p in pedidos]
            cur.execute(
                """
                SELECT b.id, b.guia, b.descripcion,
                       b.peso_kg::float8 AS peso_kg,
                       b.volumen_m3::float8 AS volumen_m3,
                       b.pedido_id
                FROM operaciones.bultos b
                WHERE b.pedido_id = ANY(%s)
                ORDER BY b.guia
                """,
                (ids,),
            )
            bultos_por_pedido: dict[int, list[dict]] = {}
            for bulto in cur.fetchall():
                bultos_por_pedido.setdefault(bulto["pedido_id"], []).append(bulto)

        resultado: list[PedidoPlan] = []
        for fila in pedidos:
            cliente = ClientePlan(
                id=fila["cliente_id"],
                codigo=fila["codigo"],
                nombre=fila["nombre"],
                tipo_cliente=fila["tipo_cliente"],
                zona=Zona(fila["zona"]),
                direccion=fila["direccion"],
                telefono=fila["telefono"],
                punto=PuntoGeo(fila["latitud"], fila["longitud"]),
            )
            bultos = [
                BultoPlan(
                    id=b["id"],
                    guia=b["guia"],
                    descripcion=b["descripcion"],
                    peso_kg=b["peso_kg"],
                    volumen_m3=b["volumen_m3"],
                )
                for b in bultos_por_pedido.get(fila["id"], [])
            ]
            resultado.append(
                PedidoPlan(
                    id=fila["id"],
                    folio=fila["folio"],
                    cliente=cliente,
                    prioridad=fila["prioridad"],
                    peso_kg=fila["peso_kg"],
                    volumen_m3=fila["volumen_m3"],
                    bultos=bultos,
                )
            )
        return resultado

    def flota(self) -> tuple[list[VehiculoPlan], list[ConductorPlan]]:
        with self.cursor() as cur:
            cur.execute(
                """
                SELECT id, placas, modelo,
                       capacidad_kg::float8 AS capacidad_kg,
                       capacidad_m3::float8 AS capacidad_m3
                FROM operaciones.vehiculos
                WHERE activo = TRUE
                ORDER BY capacidad_kg
                """
            )
            vehiculos = [
                VehiculoPlan(
                    id=f["id"], placas=f["placas"], modelo=f["modelo"],
                    capacidad_kg=f["capacidad_kg"], capacidad_m3=f["capacidad_m3"],
                )
                for f in cur.fetchall()
            ]
            cur.execute(
                """
                SELECT id, nombre, telefono, licencia
                FROM operaciones.conductores
                WHERE activo = TRUE
                ORDER BY id
                """
            )
            conductores = [
                ConductorPlan(
                    id=f["id"], nombre=f["nombre"],
                    telefono=f["telefono"], licencia=f["licencia"],
                )
                for f in cur.fetchall()
            ]
        return vehiculos, conductores

    def cancelar_planificadas(self, fecha: date, usuario: UsuarioSesion) -> int:
        with self.cursor() as cur:
            cur.execute(
                """
                SELECT id, folio FROM operaciones.rutas
                WHERE fecha = %s AND estado = 'PLANIFICADA'
                ORDER BY id
                FOR UPDATE
                """,
                (fecha,),
            )
            rutas = list(cur.fetchall())
            if not rutas:
                return 0

            ids = [r["id"] for r in rutas]
            cur.execute(
                """
                SELECT rp.ruta_id, rb.bulto_id
                FROM operaciones.ruta_bultos rb
                JOIN operaciones.ruta_paradas rp ON rp.id = rb.ruta_parada_id
                WHERE rp.ruta_id = ANY(%s)
                """,
                (ids,),
            )
            por_ruta: dict[int, list[int]] = {}
            for fila in cur.fetchall():
                por_ruta.setdefault(fila["ruta_id"], []).append(fila["bulto_id"])

            for ruta in rutas:
                for bulto_id in por_ruta.get(ruta["id"], []):
                    cur.execute(
                        """
                        INSERT INTO operaciones.eventos_rastreo
                            (bulto_id, ruta_id, estado, descripcion, ubicacion, usuario_id)
                        VALUES (%s, %s, 'CANCELADO',
                                'Plan de ruta cancelado para replanificación',
                                'CEDIS', %s)
                        """,
                        (bulto_id, ruta["id"], usuario.id),
                    )
                registrar_bitacora(
                    cur, usuario, "PLAN_CANCELADO", entidad="ruta",
                    entidad_id=ruta["id"], detalle={"folio": ruta["folio"]},
                )

            cur.execute(
                """
                UPDATE operaciones.pedidos SET estado = 'LISTO'
                WHERE id IN (
                    SELECT pedido_id FROM operaciones.ruta_paradas
                    WHERE ruta_id = ANY(%s)
                )
                """,
                (ids,),
            )
            bultos = [b for lista in por_ruta.values() for b in lista]
            if bultos:
                cur.execute(
                    "UPDATE operaciones.bultos SET estado = 'EN_BODEGA' WHERE id = ANY(%s)",
                    (bultos,),
                )
            cur.execute(
                """
                UPDATE operaciones.rutas
                SET estado = 'CANCELADA', cierre_en = CURRENT_TIMESTAMP
                WHERE id = ANY(%s)
                """,
                (ids,),
            )
            return len(rutas)

    def guardar_plan(self, plan, usuario: UsuarioSesion) -> list[dict]:
        guardadas: list[dict] = []
        with self.cursor() as cur:
            for viaje in plan.viajes:
                cur.execute("SELECT nextval('operaciones.folio_ruta_seq') AS numero")
                numero = cur.fetchone()["numero"]
                folio = f"R-{plan.fecha:%Y%m%d}-{numero:04d}"
                viaje.folio = folio
                metricas = viaje.metricas
                assert metricas is not None
                cur.execute(
                    """
                    INSERT INTO operaciones.rutas
                        (folio, zona, fecha, vehiculo_id, conductor_id, estado,
                         distancia_km, distancia_base_km, ahorro_pct, eta_min,
                         generada_por)
                    VALUES (%s, %s, %s, %s, %s, 'PLANIFICADA',
                            %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        folio,
                        viaje.zona.value,
                        plan.fecha,
                        viaje.vehiculo.id,
                        viaje.conductor.id,
                        metricas.distancia_km,
                        metricas.distancia_base_km,
                        metricas.ahorro_pct,
                        metricas.eta_min,
                        usuario.id,
                    ),
                )
                ruta_id = cur.fetchone()["id"]

                total_bultos = 0
                for parada in viaje.paradas:
                    pedido = parada.pedido
                    cur.execute(
                        """
                        INSERT INTO operaciones.ruta_paradas
                            (ruta_id, pedido_id, cliente_id, secuencia, latitud,
                             longitud, distancia_km, eta_min, estado)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'PENDIENTE')
                        RETURNING id
                        """,
                        (
                            ruta_id,
                            pedido.id,
                            pedido.cliente.id,
                            parada.secuencia,
                            pedido.cliente.punto.latitud,
                            pedido.cliente.punto.longitud,
                            parada.distancia_km,
                            parada.eta_min,
                        ),
                    )
                    parada_id = cur.fetchone()["id"]

                    bulto_ids = [b.id for b in pedido.bultos]
                    if bulto_ids:
                        cur.executemany(
                            """
                            INSERT INTO operaciones.ruta_bultos
                                (ruta_parada_id, bulto_id)
                            VALUES (%s, %s)
                            """,
                            [(parada_id, bulto_id) for bulto_id in bulto_ids],
                        )
                        cur.execute(
                            """
                            UPDATE operaciones.bultos SET estado = 'ASIGNADO'
                            WHERE id = ANY(%s)
                            """,
                            (bulto_ids,),
                        )
                        cur.executemany(
                            """
                            INSERT INTO operaciones.eventos_rastreo
                                (bulto_id, ruta_id, estado, descripcion,
                                 ubicacion, usuario_id)
                            VALUES (%s, %s, 'ASIGNADO', %s, 'CEDIS', %s)
                            """,
                            [
                                (
                                    bulto_id, ruta_id,
                                    f"Bulto asignado a la ruta {folio}",
                                    usuario.id,
                                )
                                for bulto_id in bulto_ids
                            ],
                        )
                        total_bultos += len(bulto_ids)

                    cur.execute(
                        "UPDATE operaciones.pedidos SET estado = 'ASIGNADO' WHERE id = %s",
                        (pedido.id,),
                    )

                registrar_bitacora(
                    cur, usuario, "RUTA_PLANIFICADA", entidad="ruta",
                    entidad_id=ruta_id,
                    detalle={
                        "folio": folio,
                        "zona": viaje.zona.value,
                        "paradas": len(viaje.paradas),
                        "bultos": total_bultos,
                        "distancia_km": metricas.distancia_km,
                        "ahorro_pct": metricas.ahorro_pct,
                    },
                )
                guardadas.append(
                    {
                        "id": ruta_id,
                        "folio": folio,
                        "zona": viaje.zona.value,
                    }
                )
        return guardadas

    # ------------------------------------------------------------------
    # Consulta
    # ------------------------------------------------------------------
    def listar_rutas(
        self,
        *,
        fecha: date | None = None,
        estado: str | None = None,
        limite: int = 100,
    ) -> list[dict]:
        with self.cursor() as cur:
            cur.execute(
                _SELECT_RUTA
                + """
                WHERE (%s::date IS NULL OR r.fecha = %s::date)
                  AND (%s::text IS NULL OR r.estado = %s::text)
                ORDER BY r.fecha DESC, r.generada_en DESC
                LIMIT %s
                """,
                (fecha, fecha, estado, estado, limite),
            )
            return [_resumen_ruta(f) for f in cur.fetchall()]

    def obtener_ruta(self, ruta_id: int) -> dict | None:
        with self.cursor() as cur:
            cur.execute(_SELECT_RUTA + " WHERE r.id = %s", (ruta_id,))
            fila = cur.fetchone()
            if fila is None:
                return None
            ruta = _resumen_ruta(fila)

            cur.execute(
                """
                SELECT rp.id,
                       rp.secuencia,
                       rp.estado,
                       rp.pedido_id,
                       rp.distancia_km::float8 AS distancia_km,
                       rp.eta_min::float8      AS eta_min,
                       rp.latitud::float8      AS latitud,
                       rp.longitud::float8     AS longitud,
                       p.folio                  AS pedido_folio,
                       c.id                     AS cliente_id,
                       c.codigo                 AS cliente_codigo,
                       c.nombre                 AS cliente,
                       c.tipo_cliente,
                       c.direccion,
                       c.telefono
                FROM operaciones.ruta_paradas rp
                JOIN operaciones.pedidos p ON p.id = rp.pedido_id
                JOIN operaciones.clientes c ON c.id = rp.cliente_id
                WHERE rp.ruta_id = %s
                ORDER BY rp.secuencia
                """,
                (ruta_id,),
            )
            paradas = list(cur.fetchall())

            cur.execute(
                """
                SELECT rb.ruta_parada_id,
                       b.id,
                       b.guia,
                       b.descripcion,
                       b.peso_kg::float8    AS peso_kg,
                       b.volumen_m3::float8 AS volumen_m3,
                       b.estado
                FROM operaciones.ruta_bultos rb
                JOIN operaciones.bultos b ON b.id = rb.bulto_id
                JOIN operaciones.ruta_paradas rp ON rp.id = rb.ruta_parada_id
                WHERE rp.ruta_id = %s
                ORDER BY b.guia
                """,
                (ruta_id,),
            )
            bultos: dict[int, list[dict]] = {}
            for bulto in cur.fetchall():
                bultos.setdefault(bulto["ruta_parada_id"], []).append(
                    {
                        "id": bulto["id"],
                        "guia": bulto["guia"],
                        "descripcion": bulto["descripcion"],
                        "peso_kg": bulto["peso_kg"],
                        "volumen_m3": bulto["volumen_m3"],
                        "estado": bulto["estado"],
                    }
                )

            cur.execute(
                """
                SELECT e.id, e.resultado, e.recibio_nombre, e.motivo_fallo,
                       e.comentario, e.reprogramado_para, e.firma_url, e.foto_url,
                       e.registrado_en, rp.id AS ruta_parada_id
                FROM operaciones.entregas e
                JOIN operaciones.ruta_paradas rp ON rp.id = e.ruta_parada_id
                WHERE rp.ruta_id = %s
                """,
                (ruta_id,),
            )
            entregas = {f["ruta_parada_id"]: f for f in cur.fetchall()}

        detalle_paradas = []
        for p in paradas:
            entrega = entregas.get(p["id"])
            entrega_out = None
            if entrega:
                entrega_out = {
                    "id": entrega["id"],
                    "resultado": entrega["resultado"],
                    "recibio_nombre": entrega["recibio_nombre"],
                    "motivo_fallo": entrega["motivo_fallo"],
                    "comentario": entrega["comentario"],
                    "reprogramado_para": entrega["reprogramado_para"],
                    "firma_url": (
                        f"/api/entregas/{entrega['id']}/evidencia/firma"
                        if entrega["firma_url"] else None
                    ),
                    "foto_url": (
                        f"/api/entregas/{entrega['id']}/evidencia/foto"
                        if entrega["foto_url"] else None
                    ),
                    "registrado_en": entrega["registrado_en"],
                }
            detalle_paradas.append(
                {
                    "id": p["id"],
                    "secuencia": p["secuencia"],
                    "estado": p["estado"],
                    "pedido_id": p["pedido_id"],
                    "pedido_folio": p["pedido_folio"],
                    "cliente_id": p["cliente_id"],
                    "cliente": p["cliente"],
                    "cliente_codigo": p["cliente_codigo"],
                    "tipo_cliente": p["tipo_cliente"],
                    "direccion": p["direccion"],
                    "telefono": p["telefono"],
                    "latitud": p["latitud"],
                    "longitud": p["longitud"],
                    "distancia_km": p["distancia_km"],
                    "eta_min": p["eta_min"],
                    "bultos": bultos.get(p["id"], []),
                    "entrega": entrega_out,
                }
            )

        ruta["paradas"] = detalle_paradas
        return ruta

    def reporte_entregas(
        self, desde: date | None = None, hasta: date | None = None
    ) -> list[dict]:
        with self.cursor() as cur:
            cur.execute(
                """
                SELECT r.folio AS ruta,
                       r.fecha,
                       c.nombre AS cliente,
                       c.zona,
                       p.folio AS pedido,
                       e.resultado,
                       e.recibio_nombre,
                       e.motivo_fallo,
                       e.reprogramado_para,
                       e.registrado_en
                FROM operaciones.entregas e
                JOIN operaciones.ruta_paradas rp ON rp.id = e.ruta_parada_id
                JOIN operaciones.rutas r ON r.id = rp.ruta_id
                JOIN operaciones.clientes c ON c.id = rp.cliente_id
                JOIN operaciones.pedidos p ON p.id = rp.pedido_id
                WHERE (%s::date IS NULL OR e.registrado_en::date >= %s::date)
                  AND (%s::date IS NULL OR e.registrado_en::date <= %s::date)
                ORDER BY e.registrado_en DESC
                """,
                (desde, desde, hasta, hasta),
            )
            return list(cur.fetchall())

    def datos_evidencia(self, entrega_id: int) -> dict | None:
        with self.cursor() as cur:
            cur.execute(
                "SELECT firma_url, foto_url FROM operaciones.entregas WHERE id = %s",
                (entrega_id,),
            )
            return cur.fetchone()

    # ------------------------------------------------------------------
    # Despacho
    # ------------------------------------------------------------------
    def despachar(self, ruta_id: int, guias: list[str], usuario: UsuarioSesion) -> dict:
        escaneadas = {g.strip().upper() for g in guias if g and g.strip()}
        with self.cursor() as cur:
            cur.execute(
                "SELECT id, folio, estado FROM operaciones.rutas WHERE id = %s FOR UPDATE",
                (ruta_id,),
            )
            ruta = cur.fetchone()
            if ruta is None:
                return {"ok": False, "codigo": 404, "mensaje": "La ruta no existe."}
            if ruta["estado"] != "PLANIFICADA":
                return {
                    "ok": False, "codigo": 409,
                    "mensaje": f"La ruta {ruta['folio']} está en estado {ruta['estado']} "
                               "y no puede despacharse.",
                }

            cur.execute(
                """
                SELECT b.guia
                FROM operaciones.ruta_bultos rb
                JOIN operaciones.bultos b ON b.id = rb.bulto_id
                JOIN operaciones.ruta_paradas rp ON rp.id = rb.ruta_parada_id
                WHERE rp.ruta_id = %s
                ORDER BY b.guia
                """,
                (ruta_id,),
            )
            esperadas = {f["guia"] for f in cur.fetchall()}
            faltantes = sorted(esperadas - escaneadas)
            ajenas = sorted(escaneadas - esperadas)

            if faltantes or ajenas:
                registrar_bitacora(
                    cur, usuario, "DESPACHO_RECHAZADO", entidad="ruta",
                    entidad_id=ruta_id,
                    detalle={"faltantes": faltantes, "ajenas": ajenas},
                )
                return {
                    "ok": False, "codigo": 409,
                    "mensaje": "El escaneo no coincide con los bultos de la ruta.",
                    "faltantes": faltantes, "ajenas": ajenas,
                }

            cur.execute(
                """
                UPDATE operaciones.rutas
                SET estado = 'EN_RUTA', salida_en = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (ruta_id,),
            )
            cur.execute(
                """
                UPDATE operaciones.pedidos SET estado = 'EN_RUTA'
                WHERE id IN (
                    SELECT pedido_id FROM operaciones.ruta_paradas WHERE ruta_id = %s
                )
                """,
                (ruta_id,),
            )
            cur.execute(
                """
                UPDATE operaciones.bultos SET estado = 'EN_RUTA'
                WHERE id IN (
                    SELECT rb.bulto_id
                    FROM operaciones.ruta_bultos rb
                    JOIN operaciones.ruta_paradas rp ON rp.id = rb.ruta_parada_id
                    WHERE rp.ruta_id = %s
                )
                """,
                (ruta_id,),
            )
            cur.execute(
                """
                INSERT INTO operaciones.eventos_rastreo
                    (bulto_id, ruta_id, estado, descripcion, ubicacion, usuario_id)
                SELECT rb.bulto_id, %s, 'EN_RUTA',
                       'Unidad despachada del andén · escaneo completo',
                       'CEDIS · Andén de salida', %s
                FROM operaciones.ruta_bultos rb
                JOIN operaciones.ruta_paradas rp ON rp.id = rb.ruta_parada_id
                WHERE rp.ruta_id = %s
                """,
                (ruta_id, usuario.id, ruta_id),
            )
            registrar_bitacora(
                cur, usuario, "RUTA_DESPACHADA", entidad="ruta",
                entidad_id=ruta_id,
                detalle={"folio": ruta["folio"], "bultos": len(esperadas)},
            )
            return {
                "ok": True, "codigo": 200,
                "mensaje": f"Ruta {ruta['folio']} despachada. "
                           f"{len(esperadas)} bultos validados.",
                "total_bultos": len(esperadas),
            }

    # ------------------------------------------------------------------
    # Entrega / evidencia
    # ------------------------------------------------------------------
    def registrar_entrega(
        self,
        ruta_id: int,
        parada_id: int,
        *,
        resultado: str,
        recibio_nombre: str | None,
        firma_url: str | None,
        foto_url: str | None,
        motivo_fallo: str | None,
        comentario: str | None,
        reprogramado_para: date | None,
        usuario: UsuarioSesion,
    ) -> dict:
        with self.cursor() as cur:
            cur.execute(
                "SELECT id, folio, estado FROM operaciones.rutas WHERE id = %s FOR UPDATE",
                (ruta_id,),
            )
            ruta = cur.fetchone()
            if ruta is None:
                return {"ok": False, "codigo": 404, "mensaje": "La ruta no existe."}
            if ruta["estado"] != "EN_RUTA":
                return {
                    "ok": False, "codigo": 409,
                    "mensaje": f"La ruta {ruta['folio']} debe estar EN_RUTA para "
                               "registrar entregas.",
                }

            cur.execute(
                """
                SELECT rp.id, rp.estado, rp.pedido_id, rp.cliente_id,
                       p.folio AS pedido_folio
                FROM operaciones.ruta_paradas rp
                JOIN operaciones.pedidos p ON p.id = rp.pedido_id
                WHERE rp.id = %s AND rp.ruta_id = %s
                FOR UPDATE OF rp
                """,
                (parada_id, ruta_id),
            )
            parada = cur.fetchone()
            if parada is None:
                return {
                    "ok": False, "codigo": 404,
                    "mensaje": "La parada no pertenece a la ruta indicada.",
                }
            if parada["estado"] != "PENDIENTE":
                return {
                    "ok": False, "codigo": 409,
                    "mensaje": "Esta parada ya tiene un resultado registrado.",
                }

            cur.execute(
                """
                SELECT b.id, b.guia
                FROM operaciones.ruta_bultos rb
                JOIN operaciones.bultos b ON b.id = rb.bulto_id
                WHERE rb.ruta_parada_id = %s
                ORDER BY b.guia
                """,
                (parada_id,),
            )
            bultos = list(cur.fetchall())
            bulto_ids = [b["id"] for b in bultos]

            cur.execute(
                """
                INSERT INTO operaciones.entregas
                    (ruta_parada_id, resultado, recibio_nombre, firma_url,
                     foto_url, motivo_fallo, comentario, reprogramado_para,
                     registrado_por)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    parada_id, resultado, recibio_nombre, firma_url, foto_url,
                    motivo_fallo, comentario, reprogramado_para, usuario.id,
                ),
            )
            cur.execute(
                "UPDATE operaciones.ruta_paradas SET estado = %s WHERE id = %s",
                (resultado, parada_id),
            )

            if resultado == "ENTREGADO":
                cur.execute(
                    "UPDATE operaciones.pedidos SET estado = 'ENTREGADO' WHERE id = %s",
                    (parada["pedido_id"],),
                )
                cur.execute(
                    "UPDATE operaciones.bultos SET estado = 'ENTREGADO' WHERE id = ANY(%s)",
                    (bulto_ids,),
                )
                descripcion = (
                    f"Entrega confirmada · recibió {recibio_nombre or 'el cliente'}"
                )
                cur.executemany(
                    """
                    INSERT INTO operaciones.eventos_rastreo
                        (bulto_id, ruta_id, estado, descripcion, ubicacion, usuario_id)
                    VALUES (%s, %s, 'ENTREGADO', %s, 'Domicilio del cliente', %s)
                    """,
                    [(bid, ruta_id, descripcion, usuario.id) for bid in bulto_ids],
                )
                accion = "ENTREGA_REGISTRADA"
            else:
                cur.execute(
                    """
                    UPDATE operaciones.pedidos
                    SET estado = CASE WHEN %s::date IS NULL THEN 'FALLIDO'
                                      ELSE 'REPROGRAMADO' END
                    WHERE id = %s
                    """,
                    (reprogramado_para, parada["pedido_id"]),
                )
                cur.execute(
                    "UPDATE operaciones.bultos SET estado = 'DEVUELTO' WHERE id = ANY(%s)",
                    (bulto_ids,),
                )
                descripcion_fallo = f"Intento de entrega fallido · {motivo_fallo}"
                cur.executemany(
                    """
                    INSERT INTO operaciones.eventos_rastreo
                        (bulto_id, ruta_id, estado, descripcion, ubicacion, usuario_id)
                    VALUES (%s, %s, 'FALLIDO', %s, 'Domicilio del cliente', %s)
                    """,
                    [(bid, ruta_id, descripcion_fallo, usuario.id) for bid in bulto_ids],
                )
                cur.executemany(
                    """
                    INSERT INTO operaciones.eventos_rastreo
                        (bulto_id, ruta_id, estado, descripcion, ubicacion, usuario_id)
                    VALUES (%s, %s, 'DEVUELTO',
                            'Mercancía devuelta a la zona de devoluciones',
                            'CEDIS · Devoluciones', %s)
                    """,
                    [(bid, ruta_id, usuario.id) for bid in bulto_ids],
                )
                if reprogramado_para:
                    cur.executemany(
                        """
                        INSERT INTO operaciones.eventos_rastreo
                            (bulto_id, ruta_id, estado, descripcion, ubicacion, usuario_id)
                        VALUES (%s, %s, 'REPROGRAMADO',
                                %s, 'CEDIS', %s)
                        """,
                        [
                            (
                                bid, ruta_id,
                                f"Entrega reprogramada para {reprogramado_para:%d/%m/%Y}",
                                usuario.id,
                            )
                            for bid in bulto_ids
                        ],
                    )
                accion = "ENTREGA_FALLIDA"

            cur.execute(
                """
                SELECT COUNT(*)::int AS pendientes
                FROM operaciones.ruta_paradas
                WHERE ruta_id = %s AND estado = 'PENDIENTE'
                """,
                (ruta_id,),
            )
            pendientes = cur.fetchone()["pendientes"]
            if pendientes == 0:
                cur.execute(
                    """
                    UPDATE operaciones.rutas
                    SET estado = 'COMPLETADA', cierre_en = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    (ruta_id,),
                )

            registrar_bitacora(
                cur, usuario, accion, entidad="ruta_parada",
                entidad_id=parada_id,
                detalle={
                    "ruta": ruta["folio"],
                    "pedido": parada["pedido_folio"],
                    "resultado": resultado,
                    "motivo_fallo": motivo_fallo,
                    "reprogramado_para": (
                        reprogramado_para.isoformat() if reprogramado_para else None
                    ),
                    "bultos": len(bulto_ids),
                },
            )

        return {
            "ok": True, "codigo": 200,
            "mensaje": (
                f"Entrega registrada para {parada['pedido_folio']}."
                if resultado == "ENTREGADO"
                else f"Entrega fallida registrada para {parada['pedido_folio']}."
            ),
            "ruta_id": ruta_id,
        }
