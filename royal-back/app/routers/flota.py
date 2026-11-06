"""Control de flota: vehículos, conductores e historial."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from psycopg import errors as pg_errors

from ..dependencias import obtener_bd, registrar_bitacora_segura
from ..modelos.esquemas import (
    ConductorCrearIn,
    ConductorOut,
    FlotaOut,
    VehiculoCrearIn,
    VehiculoOut,
)
from ..modelos.esquemas_operaciones import ConductorActualizar, VehiculoActualizar
from ..repositorios.flota import RepositorioFlota
from ..repositorios.logistica import RepositorioRutas
from ..seguridad import UsuarioSesion, requiere_roles, usuario_actual

router = APIRouter(prefix="/flota", tags=["Flota"])


@router.get("", response_model=FlotaOut, summary="Flota e historial de rutas")
def flota(usuario: UsuarioSesion = Depends(usuario_actual)) -> dict:
    bd = obtener_bd()
    repo = RepositorioFlota(bd, usuario.rol_bd)
    historial = RepositorioRutas(bd, usuario.rol_bd).listar_rutas(limite=30)
    return {
        "vehiculos": repo.vehiculos(),
        "conductores": repo.conductores(),
        "historial": historial,
    }


@router.post(
    "/vehiculos",
    response_model=VehiculoOut,
    status_code=201,
    summary="Registrar vehículo",
)
def crear_vehiculo(
    datos: VehiculoCrearIn,
    usuario: UsuarioSesion = Depends(requiere_roles("admin")),
) -> dict:
    try:
        vehiculo = RepositorioFlota(obtener_bd(), usuario.rol_bd).crear_vehiculo(
            placas=datos.placas,
            modelo=datos.modelo,
            capacidad_kg=datos.capacidad_kg,
            capacidad_m3=datos.capacidad_m3,
        )
    except pg_errors.UniqueViolation as exc:
        raise HTTPException(
            status_code=409, detail="Ya existe un vehículo con esas placas."
        ) from exc
    registrar_bitacora_segura(
        obtener_bd(), usuario, "VEHICULO_CREADO", entidad="vehiculo",
        entidad_id=vehiculo["id"], detalle={"placas": vehiculo["placas"]},
    )
    return vehiculo


@router.patch(
    "/vehiculos/{vehiculo_id}",
    response_model=VehiculoOut,
    summary="Actualizar / desactivar vehículo",
)
def actualizar_vehiculo(
    vehiculo_id: int,
    datos: VehiculoActualizar,
    usuario: UsuarioSesion = Depends(requiere_roles("admin")),
) -> dict:
    return RepositorioFlota(obtener_bd(), usuario.rol_bd).actualizar_vehiculo(
        vehiculo_id, datos, usuario
    )


@router.patch(
    "/conductores/{conductor_id}",
    response_model=ConductorOut,
    summary="Actualizar / desactivar conductor",
)
def actualizar_conductor(
    conductor_id: int,
    datos: ConductorActualizar,
    usuario: UsuarioSesion = Depends(requiere_roles("admin")),
) -> dict:
    try:
        return RepositorioFlota(obtener_bd(), usuario.rol_bd).actualizar_conductor(
            conductor_id, datos, usuario
        )
    except pg_errors.UniqueViolation as exc:
        raise HTTPException(
            status_code=409, detail="Ya existe un conductor con esa licencia."
        ) from exc


@router.post(
    "/conductores",
    response_model=ConductorOut,
    status_code=201,
    summary="Registrar conductor",
)
def crear_conductor(
    datos: ConductorCrearIn,
    usuario: UsuarioSesion = Depends(requiere_roles("admin")),
) -> dict:
    try:
        conductor = RepositorioFlota(obtener_bd(), usuario.rol_bd).crear_conductor(
            nombre=datos.nombre,
            telefono=datos.telefono,
            licencia=datos.licencia,
        )
    except pg_errors.UniqueViolation as exc:
        raise HTTPException(
            status_code=409, detail="Ya existe un conductor con esa licencia."
        ) from exc
    registrar_bitacora_segura(
        obtener_bd(), usuario, "CONDUCTOR_CREADO", entidad="conductor",
        entidad_id=conductor["id"], detalle={"nombre": conductor["nombre"]},
    )
    return conductor
