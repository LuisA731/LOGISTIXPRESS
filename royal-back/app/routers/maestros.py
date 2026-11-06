"""CRUD de maestros y pedidos (MVC · capa de presentación)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from psycopg import errors as pg_errors

from ..dependencias import obtener_bd
from ..modelos.esquemas_operaciones import (
    ClienteActualizar,
    ClienteIn,
    ClienteOut,
    LoteActualizar,
    LoteIn,
    LoteOut,
    PedidoActualizar,
    PedidoDetalleOut,
    PedidoIn,
    PedidoResumenOut,
    ProductoActualizar,
    ProductoIn,
    ProductoMaestroOut,
    ProveedorActualizar,
    ProveedorIn,
    ProveedorOut,
    UbicacionActualizar,
    UbicacionIn,
    UbicacionMaestroOut,
)
from ..repositorios.maestros import RepositorioMaestros
from ..seguridad import UsuarioSesion, requiere_roles, usuario_actual

router = APIRouter(prefix="/maestros", tags=["Maestros y pedidos"])


def _repo(usuario: UsuarioSesion) -> RepositorioMaestros:
    return RepositorioMaestros(obtener_bd(), usuario.rol_bd)


def _conflicto(error: pg_errors.UniqueViolation, mensaje: str) -> HTTPException:
    return HTTPException(status_code=409, detail=mensaje)


@router.get("/clientes", response_model=list[ClienteOut], summary="Listar clientes")
def clientes(usuario: UsuarioSesion = Depends(usuario_actual)) -> list[dict]:
    return _repo(usuario).clientes()


@router.post(
    "/clientes", response_model=ClienteOut, status_code=201, summary="Crear cliente"
)
def crear_cliente(
    datos: ClienteIn,
    usuario: UsuarioSesion = Depends(requiere_roles("admin", "operador")),
) -> dict:
    try:
        return _repo(usuario).crear_cliente(datos, usuario)
    except pg_errors.UniqueViolation as exc:
        raise _conflicto(exc, "Ya existe un cliente con ese código.") from exc


@router.patch(
    "/clientes/{cliente_id}",
    response_model=ClienteOut,
    summary="Actualizar cliente / baja lógica",
)
def actualizar_cliente(
    cliente_id: int,
    datos: ClienteActualizar,
    usuario: UsuarioSesion = Depends(requiere_roles("admin", "operador")),
) -> dict:
    try:
        return _repo(usuario).actualizar_cliente(cliente_id, datos, usuario)
    except pg_errors.UniqueViolation as exc:
        raise _conflicto(exc, "Ya existe un cliente con ese código.") from exc


@router.get("/productos", response_model=list[ProductoMaestroOut], summary="Listar productos")
def productos(usuario: UsuarioSesion = Depends(usuario_actual)) -> list[dict]:
    return _repo(usuario).productos()


@router.post(
    "/productos", response_model=ProductoMaestroOut, status_code=201,
    summary="Crear producto",
)
def crear_producto(
    datos: ProductoIn,
    usuario: UsuarioSesion = Depends(requiere_roles("admin")),
) -> dict:
    try:
        return _repo(usuario).crear_producto(datos, usuario)
    except pg_errors.UniqueViolation as exc:
        raise _conflicto(exc, "Ya existe un producto con ese SKU.") from exc


@router.patch(
    "/productos/{producto_id}",
    response_model=ProductoMaestroOut,
    summary="Actualizar producto / baja lógica",
)
def actualizar_producto(
    producto_id: int,
    datos: ProductoActualizar,
    usuario: UsuarioSesion = Depends(requiere_roles("admin")),
) -> dict:
    return _repo(usuario).actualizar_producto(producto_id, datos, usuario)


@router.get(
    "/ubicaciones", response_model=list[UbicacionMaestroOut], summary="Listar ubicaciones"
)
def ubicaciones(usuario: UsuarioSesion = Depends(usuario_actual)) -> list[dict]:
    return _repo(usuario).ubicaciones()


@router.post(
    "/ubicaciones", response_model=UbicacionMaestroOut, status_code=201,
    summary="Crear ubicación",
)
def crear_ubicacion(
    datos: UbicacionIn,
    usuario: UsuarioSesion = Depends(requiere_roles("admin")),
) -> dict:
    try:
        return _repo(usuario).crear_ubicacion(datos, usuario)
    except pg_errors.UniqueViolation as exc:
        raise _conflicto(exc, "Ya existe una ubicación con ese código.") from exc


@router.patch(
    "/ubicaciones/{ubicacion_id}",
    response_model=UbicacionMaestroOut,
    summary="Actualizar ubicación / baja lógica",
)
def actualizar_ubicacion(
    ubicacion_id: int,
    datos: UbicacionActualizar,
    usuario: UsuarioSesion = Depends(requiere_roles("admin")),
) -> dict:
    return _repo(usuario).actualizar_ubicacion(ubicacion_id, datos, usuario)


@router.get("/lotes", response_model=list[LoteOut], summary="Listar lotes")
def lotes(usuario: UsuarioSesion = Depends(usuario_actual)) -> list[dict]:
    return _repo(usuario).lotes()


@router.post(
    "/lotes", response_model=LoteOut, status_code=201, summary="Crear lote"
)
def crear_lote(
    datos: LoteIn,
    usuario: UsuarioSesion = Depends(requiere_roles("admin", "operador")),
) -> dict:
    try:
        return _repo(usuario).crear_lote(datos, usuario)
    except pg_errors.UniqueViolation as exc:
        raise _conflicto(exc, "Ya existe un lote con ese código para el producto.") from exc


@router.patch(
    "/lotes/{lote_id}", response_model=LoteOut, summary="Actualizar lote"
)
def actualizar_lote(
    lote_id: int,
    datos: LoteActualizar,
    usuario: UsuarioSesion = Depends(requiere_roles("admin", "operador")),
) -> dict:
    return _repo(usuario).actualizar_lote(lote_id, datos, usuario)


@router.get(
    "/proveedores", response_model=list[ProveedorOut], summary="Listar proveedores"
)
def proveedores(usuario: UsuarioSesion = Depends(usuario_actual)) -> list[dict]:
    return _repo(usuario).proveedores()


@router.post(
    "/proveedores", response_model=ProveedorOut, status_code=201,
    summary="Crear proveedor",
)
def crear_proveedor(
    datos: ProveedorIn,
    usuario: UsuarioSesion = Depends(requiere_roles("admin", "operador")),
) -> dict:
    try:
        return _repo(usuario).crear_proveedor(datos, usuario)
    except pg_errors.UniqueViolation as exc:
        raise _conflicto(exc, "Ya existe un proveedor con ese código.") from exc


@router.patch(
    "/proveedores/{proveedor_id}",
    response_model=ProveedorOut,
    summary="Actualizar proveedor / baja lógica",
)
def actualizar_proveedor(
    proveedor_id: int,
    datos: ProveedorActualizar,
    usuario: UsuarioSesion = Depends(requiere_roles("admin", "operador")),
) -> dict:
    return _repo(usuario).actualizar_proveedor(proveedor_id, datos, usuario)


@router.get(
    "/pedidos", response_model=list[PedidoResumenOut], summary="Listar pedidos"
)
def pedidos(
    limite: int = 200,
    usuario: UsuarioSesion = Depends(usuario_actual),
) -> list[dict]:
    return _repo(usuario).pedidos(limite)


@router.get(
    "/pedidos/{pedido_id}", response_model=PedidoDetalleOut, summary="Detalle del pedido"
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
    "/pedidos", response_model=PedidoDetalleOut, status_code=201,
    summary="Crear pedido BORRADOR con detalle",
)
def crear_pedido(
    datos: PedidoIn,
    usuario: UsuarioSesion = Depends(requiere_roles("admin", "operador")),
) -> dict:
    return _repo(usuario).crear_pedido(datos, usuario)


@router.patch(
    "/pedidos/{pedido_id}",
    response_model=PedidoDetalleOut,
    summary="Editar pedido BORRADOR",
)
def actualizar_pedido(
    pedido_id: int,
    datos: PedidoActualizar,
    usuario: UsuarioSesion = Depends(requiere_roles("admin", "operador")),
) -> dict:
    return _repo(usuario).actualizar_pedido(pedido_id, datos, usuario)


@router.post(
    "/pedidos/{pedido_id}/cancelar",
    response_model=PedidoDetalleOut,
    summary="Cancelar pedido BORRADOR/LISTO",
)
def cancelar_pedido(
    pedido_id: int,
    usuario: UsuarioSesion = Depends(requiere_roles("admin", "operador")),
) -> dict:
    return _repo(usuario).cancelar_pedido(pedido_id, usuario)
