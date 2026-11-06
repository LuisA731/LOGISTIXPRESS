"""Bitácora, conteos cíclicos y rotación."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query

from ..dependencias import obtener_bd
from ..modelos.esquemas import BitacoraOut, ConteoIn, ConteoOut, RotacionOut
from ..repositorios.auditoria import RepositorioAuditoria
from ..seguridad import UsuarioSesion, requiere_roles

router = APIRouter(prefix="/auditoria", tags=["Auditoría"])


@router.get(
    "/bitacora",
    response_model=list[BitacoraOut],
    summary="Registro de actividades",
)
def bitacora(
    limite: int = Query(default=120, ge=1, le=500),
    accion: str | None = Query(default=None),
    desde: date | None = Query(default=None),
    hasta: date | None = Query(default=None),
    usuario: UsuarioSesion = Depends(requiere_roles("admin", "auditor")),
) -> list[dict]:
    return RepositorioAuditoria(obtener_bd(), usuario.rol_bd).bitacora(
        limite=limite, accion=accion, desde=desde, hasta=hasta
    )


@router.get(
    "/conteos",
    response_model=list[ConteoOut],
    summary="Conteos cíclicos registrados",
)
def conteos(
    limite: int = Query(default=80, ge=1, le=300),
    usuario: UsuarioSesion = Depends(requiere_roles("admin", "auditor")),
) -> list[dict]:
    return RepositorioAuditoria(obtener_bd(), usuario.rol_bd).conteos(limite)


@router.post(
    "/conteos",
    response_model=ConteoOut,
    status_code=201,
    summary="Registrar conteo cíclico",
)
def registrar_conteo(
    datos: ConteoIn,
    usuario: UsuarioSesion = Depends(requiere_roles("admin", "auditor")),
) -> dict:
    return RepositorioAuditoria(obtener_bd(), usuario.rol_bd).registrar_conteo(
        ubicacion_id=datos.ubicacion_id,
        producto_id=datos.producto_id,
        cantidad_fisica=datos.cantidad_fisica,
        usuario=usuario,
    )


@router.get(
    "/rotacion",
    response_model=list[RotacionOut],
    summary="Métricas de rotación",
)
def rotacion(
    limite: int = Query(default=80, ge=1, le=300),
    usuario: UsuarioSesion = Depends(requiere_roles("admin", "auditor")),
) -> list[dict]:
    return RepositorioAuditoria(obtener_bd(), usuario.rol_bd).rotacion(limite)
