"""Rutas de reparto, despacho, entregas y mapas."""
from __future__ import annotations

from datetime import date
from functools import lru_cache

from fastapi import APIRouter, Depends, Query, Response

from ..config import ajustes
from ..dependencias import obtener_bd
from ..modelos.esquemas import (
    DespachoIn,
    DespachoOut,
    EntregaIn,
    EntregaRegistradaOut,
    PlanGeneradoOut,
    RutaDetalleOut,
    RutaResumenOut,
)
from ..repositorios.logistica import RepositorioRutas
from ..seguridad import UsuarioSesion, requiere_roles, usuario_actual
from ..servicios.evidencias import ServicioEvidencias
from ..servicios.renderizador import RenderizadorRutas
from ..servicios.servicio_rutas import ServicioRutas

router = APIRouter(prefix="/rutas", tags=["Rutas y reparto"])


@lru_cache
def _renderizador() -> RenderizadorRutas:
    return RenderizadorRutas()


@lru_cache
def _evidencias() -> ServicioEvidencias:
    return ServicioEvidencias(ajustes.directorio_evidencias, ajustes.max_evidencia_mb)


def _servicio(usuario: UsuarioSesion) -> ServicioRutas:
    return ServicioRutas(
        repo=RepositorioRutas(obtener_bd(), usuario.rol_bd),
        renderizador=_renderizador(),
        evidencias=_evidencias(),
        velocidad_kmh=ajustes.velocidad_kmh,
        minutos_por_entrega=ajustes.minutos_por_entrega,
    )


@router.get("", response_model=list[RutaResumenOut], summary="Listar rutas")
def listar(
    fecha: date | None = Query(default=None, description="Filtra por fecha del plan"),
    estado: str | None = Query(default=None, description="PLANIFICADA, EN_RUTA, COMPLETADA o CANCELADA"),
    limite: int = Query(default=100, ge=1, le=300),
    usuario: UsuarioSesion = Depends(usuario_actual),
) -> list[dict]:
    return _servicio(usuario).listar(fecha=fecha, estado=estado)


@router.post("/generar", response_model=PlanGeneradoOut, summary="Generar plan del día")
def generar(
    replanificar: bool = Query(
        default=False,
        description="Cancela las rutas PLANIFICADAS del día y vuelve a consolidar.",
    ),
    fecha: date | None = Query(default=None),
    usuario: UsuarioSesion = Depends(requiere_roles("admin", "operador")),
) -> dict:
    return _servicio(usuario).generar_plan(
        usuario, fecha=fecha, replanificar=replanificar
    )


@router.get("/{ruta_id}", response_model=RutaDetalleOut, summary="Detalle de una ruta")
def detalle(
    ruta_id: int,
    usuario: UsuarioSesion = Depends(usuario_actual),
) -> dict:
    return _servicio(usuario).detalle(ruta_id)


@router.get(
    "/{ruta_id}/mapa",
    summary="Mapa PNG de la ruta",
    response_class=Response,
    responses={200: {"content": {"image/png": {}}}},
)
def mapa(
    ruta_id: int,
    usuario: UsuarioSesion = Depends(usuario_actual),
) -> Response:
    png = _servicio(usuario).mapa_png(ruta_id)
    return Response(
        content=png,
        media_type="image/png",
        headers={"Cache-Control": "private, max-age=60"},
    )


@router.post(
    "/{ruta_id}/despachar",
    response_model=DespachoOut,
    summary="Validar escaneo de bultos y despachar",
)
def despachar(
    ruta_id: int,
    datos: DespachoIn,
    usuario: UsuarioSesion = Depends(requiere_roles("admin", "operador")),
) -> dict:
    resultado = _servicio(usuario).despachar(ruta_id, datos.guias, usuario)
    return {
        "estado": "EN_RUTA",
        "mensaje": resultado["mensaje"],
        "total_bultos": resultado["total_bultos"],
        "faltantes": [],
        "ajenas": [],
    }


@router.post(
    "/{ruta_id}/paradas/{parada_id}/entrega",
    response_model=EntregaRegistradaOut,
    summary="Registrar entrega o intento fallido con evidencia",
)
def registrar_entrega(
    ruta_id: int,
    parada_id: int,
    datos: EntregaIn,
    usuario: UsuarioSesion = Depends(requiere_roles("admin", "operador")),
) -> dict:
    return _servicio(usuario).registrar_entrega(ruta_id, parada_id, datos, usuario)

