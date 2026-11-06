"""Descarga de evidencias digitales de entrega."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from ..config import ajustes
from ..dependencias import obtener_bd
from ..repositorios.logistica import RepositorioRutas
from ..seguridad import UsuarioSesion, usuario_actual
from ..servicios.evidencias import ServicioEvidencias
from ..servicios.servicio_rutas import ServicioRutas
from ..servicios.renderizador import RenderizadorRutas

router = APIRouter(prefix="/entregas", tags=["Entregas"])


@router.get(
    "/{entrega_id}/evidencia/{tipo}",
    summary="Descargar firma o fotografía de una entrega",
)
def evidencia(
    entrega_id: int,
    tipo: str,
    usuario: UsuarioSesion = Depends(usuario_actual),
) -> FileResponse:
    servicio = ServicioRutas(
        repo=RepositorioRutas(obtener_bd(), usuario.rol_bd),
        renderizador=RenderizadorRutas(),
        evidencias=ServicioEvidencias(ajustes.directorio_evidencias, ajustes.max_evidencia_mb),
    )
    archivo, media_type = servicio.evidencia(entrega_id, tipo)
    return FileResponse(archivo, media_type=media_type, filename=archivo.name)
