"""Flota: vehículos y conductores."""
from __future__ import annotations

from ..dependencias import registrar_bitacora
from ..db import BaseDatos
from ..errores import ErrorNegocio
from ..modelos.esquemas_operaciones import ConductorActualizar, VehiculoActualizar
from ..seguridad import UsuarioSesion
from .base import RepositorioBase


class RepositorioFlota(RepositorioBase):
    def __init__(self, bd: BaseDatos, rol_bd: str):
        super().__init__(bd, rol_bd)

    def vehiculos(self) -> list[dict]:
        with self.cursor() as cur:
            cur.execute(
                """
                SELECT id, placas, modelo,
                       capacidad_kg::float8 AS capacidad_kg,
                       capacidad_m3::float8 AS capacidad_m3,
                       activo
                FROM operaciones.vehiculos
                ORDER BY activo DESC, placas
                """
            )
            return list(cur.fetchall())

    def conductores(self) -> list[dict]:
        with self.cursor() as cur:
            cur.execute(
                """
                SELECT id, nombre, telefono, licencia, activo
                FROM operaciones.conductores
                ORDER BY activo DESC, nombre
                """
            )
            return list(cur.fetchall())

    def crear_vehiculo(
        self, *, placas: str, modelo: str, capacidad_kg: float, capacidad_m3: float
    ) -> dict:
        with self.cursor() as cur:
            cur.execute(
                """
                INSERT INTO operaciones.vehiculos
                    (placas, modelo, capacidad_kg, capacidad_m3)
                VALUES (upper(%s), %s, %s, %s)
                RETURNING id, placas, modelo,
                          capacidad_kg::float8 AS capacidad_kg,
                          capacidad_m3::float8 AS capacidad_m3,
                          activo
                """,
                (placas.strip(), modelo.strip(), capacidad_kg, capacidad_m3),
            )
            return cur.fetchone()

    def crear_conductor(
        self, *, nombre: str, telefono: str | None, licencia: str
    ) -> dict:
        with self.cursor() as cur:
            cur.execute(
                """
                INSERT INTO operaciones.conductores (nombre, telefono, licencia)
                VALUES (%s, %s, upper(%s))
                RETURNING id, nombre, telefono, licencia, activo
                """,
                (nombre.strip(), telefono, licencia.strip()),
            )
            return cur.fetchone()

    def actualizar_vehiculo(
        self, vehiculo_id: int, datos: VehiculoActualizar, usuario: UsuarioSesion
    ) -> dict:
        with self.cursor() as cur:
            cur.execute(
                """
                UPDATE operaciones.vehiculos
                SET modelo = COALESCE(%s, modelo),
                    capacidad_kg = COALESCE(%s, capacidad_kg),
                    capacidad_m3 = COALESCE(%s, capacidad_m3),
                    activo = COALESCE(%s, activo)
                WHERE id = %s
                RETURNING id, placas, modelo,
                          capacidad_kg::float8 AS capacidad_kg,
                          capacidad_m3::float8 AS capacidad_m3, activo
                """,
                (datos.modelo, datos.capacidad_kg, datos.capacidad_m3,
                 datos.activo, vehiculo_id),
            )
            vehiculo = cur.fetchone()
            if vehiculo is None:
                raise ErrorNegocio("El vehículo no existe.", 404)
            registrar_bitacora(
                cur, usuario, "VEHICULO_ACTUALIZADO", entidad="vehiculo",
                entidad_id=vehiculo_id,
                detalle={"placas": vehiculo["placas"], "activo": vehiculo["activo"]},
            )
            return vehiculo

    def actualizar_conductor(
        self, conductor_id: int, datos: ConductorActualizar, usuario: UsuarioSesion
    ) -> dict:
        with self.cursor() as cur:
            cur.execute(
                """
                UPDATE operaciones.conductores
                SET nombre = COALESCE(%s, nombre),
                    telefono = COALESCE(%s, telefono),
                    licencia = COALESCE(upper(%s), licencia),
                    activo = COALESCE(%s, activo)
                WHERE id = %s
                RETURNING id, nombre, telefono, licencia, activo
                """,
                (datos.nombre, datos.telefono, datos.licencia,
                 datos.activo, conductor_id),
            )
            conductor = cur.fetchone()
            if conductor is None:
                raise ErrorNegocio("El conductor no existe.", 404)
            registrar_bitacora(
                cur, usuario, "CONDUCTOR_ACTUALIZADO", entidad="conductor",
                entidad_id=conductor_id,
                detalle={"nombre": conductor["nombre"], "activo": conductor["activo"]},
            )
            return conductor
