"""Panel principal."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from ..dependencias import obtener_bd
from ..modelos.esquemas import PanelOut
from ..repositorios.panel import RepositorioPanel
from ..repositorios.rastreo import RepositorioRastreo
from ..repositorios.logistica import RepositorioRutas
from ..seguridad import UsuarioSesion, usuario_actual

router = APIRouter(prefix="/panel", tags=["Panel"])


@router.get("/resumen", response_model=PanelOut, summary="Indicadores del día")
def resumen(usuario: UsuarioSesion = Depends(usuario_actual)) -> PanelOut:
    bd = obtener_bd()
    repo = RepositorioPanel(bd, usuario.rol_bd)
    indicadores = repo.resumen()
    rutas = RepositorioRutas(bd, usuario.rol_bd).listar_rutas(limite=5)
    eventos = RepositorioRastreo(bd, usuario.rol_bd).eventos_recientes(limite=6)
    return PanelOut(
        **indicadores,
        productividad_hoy=repo.productividad_hoy(),
        rutas_recientes=rutas,
        eventos_recientes=eventos,
    )
