"""Picking, packing y control de calidad."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..dependencias import obtener_bd
from ..modelos.esquemas_operaciones import (
    ConfirmarTareaIn,
    OlaOut,
    PickingPedidoOut,
)
from ..repositorios.picking import RepositorioPicking
from ..seguridad import UsuarioSesion, requiere_roles, usuario_actual

router = APIRouter(prefix="/picking", tags=["Picking y packing"])


def _repo(usuario: UsuarioSesion) -> RepositorioPicking:
    return RepositorioPicking(obtener_bd(), usuario.rol_bd)


@router.get(
    "/pedidos", response_model=list[PickingPedidoOut], summary="Pedidos en picking/empaque"
)
def pedidos(
    limite: int = 100,
    usuario: UsuarioSesion = Depends(usuario_actual),
) -> list[dict]:
    return _repo(usuario).pedidos(limite)


@router.get(
    "/pedidos/{pedido_id}",
    response_model=PickingPedidoOut,
    summary="Detalle de picking/empaque del pedido",
)
def pedido(
    pedido_id: int,
    usuario: UsuarioSesion = Depends(usuario_actual),
) -> dict:
    pedido = _repo(usuario).pedido(pedido_id)
    if pedido is None:
        raise HTTPException(status_code=404, detail="El pedido no existe.")
    return pedido


@router.post(
    "/generar",
    response_model=OlaOut,
    summary="Generar ola de picking para pedidos BORRADOR",
)
def generar_ola(
    usuario: UsuarioSesion = Depends(requiere_roles("admin", "operador")),
) -> dict:
    return _repo(usuario).generar_ola(usuario)


@router.post(
    "/tareas/{tarea_id}/confirmar",
    response_model=PickingPedidoOut,
    summary="Confirmar tarea de surtido con validación de SKU/ubicación",
)
def confirmar_tarea(
    tarea_id: int,
    datos: ConfirmarTareaIn,
    usuario: UsuarioSesion = Depends(requiere_roles("admin", "operador")),
) -> dict:
    return _repo(usuario).confirmar_tarea(tarea_id, datos, usuario)


@router.post(
    "/pedidos/{pedido_id}/empacar",
    response_model=PickingPedidoOut,
    summary="Empacar pedido, generar bultos y guías",
)
def empacar(
    pedido_id: int,
    usuario: UsuarioSesion = Depends(requiere_roles("admin", "operador")),
) -> dict:
    return _repo(usuario).empacar(pedido_id, usuario)


@router.post(
    "/pedidos/{pedido_id}/aprobar",
    response_model=PickingPedidoOut,
    summary="Aprobar control de calidad y liberar pedido a ruta",
)
def aprobar(
    pedido_id: int,
    usuario: UsuarioSesion = Depends(requiere_roles("admin", "operador")),
) -> dict:
    return _repo(usuario).aprobar(pedido_id, usuario)
