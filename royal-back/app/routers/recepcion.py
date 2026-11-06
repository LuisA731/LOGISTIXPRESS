"""Recepción de mercancía: citas/OC, entrada de stock e incidencias."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from ..config import ajustes
from ..dependencias import obtener_bd
from ..modelos.esquemas_operaciones import (
    IncidenciaOut,
    OCIn,
    OCOut,
    RecepcionIn,
    RecepcionOut,
)
from ..repositorios.recepcion import RepositorioRecepcion
from ..seguridad import UsuarioSesion, requiere_roles, usuario_actual
from ..servicios.evidencias import ErrorEvidencia, ServicioEvidencias

router = APIRouter(prefix="/recepcion", tags=["Recepción"])


def _repo(usuario: UsuarioSesion) -> RepositorioRecepcion:
    return RepositorioRecepcion(obtener_bd(), usuario.rol_bd)


def _evidencias() -> ServicioEvidencias:
    return ServicioEvidencias(ajustes.directorio_evidencias, ajustes.max_evidencia_mb)


@router.get("/ordenes", response_model=list[OCOut], summary="Citas y órdenes de compra")
def ordenes(usuario: UsuarioSesion = Depends(usuario_actual)) -> list[dict]:
    return _repo(usuario).ordenes()


@router.get(
    "/ordenes/{orden_id}", response_model=OCOut, summary="Detalle de orden de compra"
)
def orden(
    orden_id: int,
    usuario: UsuarioSesion = Depends(usuario_actual),
) -> dict:
    orden = _repo(usuario).orden(orden_id)
    if orden is None:
        raise HTTPException(status_code=404, detail="La orden de compra no existe.")
    return orden


@router.post(
    "/ordenes", response_model=OCOut, status_code=201,
    summary="Programar orden de compra / cita",
)
def crear_orden(
    datos: OCIn,
    usuario: UsuarioSesion = Depends(requiere_roles("admin", "operador")),
) -> dict:
    return _repo(usuario).crear_orden(datos, usuario)


@router.post(
    "/ordenes/{orden_id}/cancelar",
    response_model=OCOut,
    summary="Cancelar cita/orden programada",
)
def cancelar_orden(
    orden_id: int,
    usuario: UsuarioSesion = Depends(requiere_roles("admin", "operador")),
) -> dict:
    return _repo(usuario).cancelar_orden(orden_id, usuario)


@router.get(
    "/sugerir-ubicacion",
    summary="Sugerir ubicación GENERAL para putaway",
)
def sugerir_ubicacion(
    producto_id: int,
    usuario: UsuarioSesion = Depends(usuario_actual),
) -> dict:
    ubicacion = _repo(usuario).sugerir_ubicacion(producto_id)
    if ubicacion is None:
        raise HTTPException(
            status_code=404,
            detail="No hay una ubicación GENERAL activa para recibir el producto.",
        )
    return ubicacion


@router.post(
    "/ordenes/{orden_id}/recibir",
    response_model=RecepcionOut,
    summary="Recibir mercancía y actualizar stock/lotes",
)
def recibir(
    orden_id: int,
    datos: RecepcionIn,
    usuario: UsuarioSesion = Depends(requiere_roles("admin", "operador")),
) -> dict:
    repo = _repo(usuario)
    orden = repo.orden(orden_id)
    if orden is None:
        raise HTTPException(status_code=404, detail="La orden de compra no existe.")
    evidencias = _evidencias()
    foto_url = None
    if datos.incidencia and datos.incidencia.foto_base64:
        try:
            foto_url = evidencias.guardar(
                ruta_folio=orden["folio"], parada_id=0,
                tipo="incidencia", data_url=datos.incidencia.foto_base64,
            )
        except ErrorEvidencia as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        return repo.recibir(orden_id, datos, usuario, foto_url=foto_url)
    except Exception:
        evidencias.eliminar(foto_url)
        raise


@router.get(
    "/incidencias", response_model=list[IncidenciaOut], summary="Incidencias de recepción"
)
def incidencias(
    limite: int = 100,
    usuario: UsuarioSesion = Depends(usuario_actual),
) -> list[dict]:
    return _repo(usuario).incidencias(limite)


@router.get(
    "/incidencias/{incidencia_id}/foto",
    summary="Fotografía de una incidencia de recepción",
)
def foto_incidencia(
    incidencia_id: int,
    usuario: UsuarioSesion = Depends(usuario_actual),
) -> FileResponse:
    fila = _repo(usuario).foto_incidencia(incidencia_id)
    if fila is None or not fila["foto_url"]:
        raise HTTPException(status_code=404, detail="La incidencia no tiene fotografía.")
    archivo = _evidencias().resolver(fila["foto_url"])
    if archivo is None:
        raise HTTPException(status_code=404, detail="La fotografía ya no está disponible.")
    media_type = "image/png" if archivo.suffix.lower() == ".png" else "image/jpeg"
    return FileResponse(archivo, media_type=media_type)
