"""Inventario: existencias, catálogo y movimientos."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg import errors as pg_errors

from ..dependencias import obtener_bd
from ..modelos.esquemas import (
    CatalogoOut,
    MovimientoIn,
    MovimientoOut,
    StockOut,
)
from ..modelos.esquemas_operaciones import TrasladoIn, TrasladoOut
from ..repositorios.inventario import RepositorioInventario
from ..seguridad import UsuarioSesion, requiere_roles, usuario_actual

router = APIRouter(prefix="/inventario", tags=["Inventario"])


@router.get("/stock", response_model=list[StockOut], summary="Existencias por producto")
def stock(usuario: UsuarioSesion = Depends(usuario_actual)) -> list[dict]:
    return RepositorioInventario(obtener_bd(), usuario.rol_bd).stock()


@router.get("/catalogo", response_model=CatalogoOut, summary="Productos y ubicaciones")
def catalogo(usuario: UsuarioSesion = Depends(usuario_actual)) -> dict:
    return RepositorioInventario(obtener_bd(), usuario.rol_bd).catalogo()


@router.get("/movimientos", response_model=list[MovimientoOut], summary="Movimientos recientes")
def movimientos(
    limite: int = Query(default=80, ge=1, le=300),
    usuario: UsuarioSesion = Depends(usuario_actual),
) -> list[dict]:
    return RepositorioInventario(obtener_bd(), usuario.rol_bd).movimientos(limite)


@router.get("/traslados", response_model=list[TrasladoOut], summary="Traslados internos")
def traslados(
    limite: int = Query(default=80, ge=1, le=300),
    usuario: UsuarioSesion = Depends(usuario_actual),
) -> list[dict]:
    return RepositorioInventario(obtener_bd(), usuario.rol_bd).traslados(limite)


@router.post(
    "/traslados",
    response_model=TrasladoOut,
    status_code=201,
    summary="Mover mercancía entre ubicaciones (origen → destino)",
)
def registrar_traslado(
    datos: TrasladoIn,
    usuario: UsuarioSesion = Depends(requiere_roles("admin", "operador")),
) -> dict:
    try:
        return RepositorioInventario(obtener_bd(), usuario.rol_bd).registrar_traslado(
            producto_id=datos.producto_id,
            cantidad=datos.cantidad,
            ubicacion_origen_id=datos.ubicacion_origen_id,
            ubicacion_destino_id=datos.ubicacion_destino_id,
            comentario=datos.comentario,
            usuario=usuario,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post(
    "/movimientos",
    response_model=MovimientoOut,
    summary="Registrar entrada o salida de almacén",
)
def registrar_movimiento(
    datos: MovimientoIn,
    usuario: UsuarioSesion = Depends(requiere_roles("admin", "operador")),
) -> dict:
    try:
        return RepositorioInventario(obtener_bd(), usuario.rol_bd).registrar_movimiento(
            producto_id=datos.producto_id,
            ubicacion_id=datos.ubicacion_id,
            tipo=datos.tipo,
            cantidad=datos.cantidad,
            usuario=usuario,
        )
    except (pg_errors.RaiseException, pg_errors.CheckViolation) as exc:
        raise HTTPException(
            status_code=409,
            detail=(
                "No se pudo aplicar el movimiento. Verifica que exista stock "
                "suficiente en la ubicación seleccionada."
            ),
        ) from exc
    except pg_errors.ForeignKeyViolation as exc:
        raise HTTPException(
            status_code=400,
            detail="El producto o la ubicación seleccionada no existe.",
        ) from exc
