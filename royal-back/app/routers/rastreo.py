"""Rastreo de paquetes por guía."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from ..dependencias import obtener_bd
from ..modelos.esquemas import RastreoOut, RastreoRecienteOut
from ..repositorios.rastreo import RepositorioRastreo
from ..seguridad import UsuarioSesion, usuario_actual

router = APIRouter(prefix="/rastreo", tags=["Rastreo de paquetes"])


@router.get("", response_model=list[RastreoRecienteOut], summary="Paquetes con movimiento reciente")
def recientes(
    limite: int = Query(default=8, ge=1, le=50),
    usuario: UsuarioSesion = Depends(usuario_actual),
) -> list[dict]:
    return RepositorioRastreo(obtener_bd(), usuario.rol_bd).recientes(limite)


@router.get("/{guia}", response_model=RastreoOut, summary="Línea de tiempo de una guía")
def consultar(
    guia: str,
    usuario: UsuarioSesion = Depends(usuario_actual),
) -> dict:
    resultado = RepositorioRastreo(obtener_bd(), usuario.rol_bd).consultar(guia)
    if resultado is None:
        raise HTTPException(
            status_code=404,
            detail=f"No se encontró la guía {guia}. Verifica el código e intenta de nuevo.",
        )
    return resultado
