"""Administración de usuarios y roles."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from psycopg import errors as pg_errors

from ..dependencias import obtener_bd, registrar_bitacora_segura
from ..modelos.esquemas import UsuarioCrearIn, UsuarioEstadoIn, UsuarioOut
from ..modelos.esquemas_operaciones import UsuarioActualizar
from ..repositorios.usuarios import RepositorioUsuarios
from ..seguridad import UsuarioSesion, requiere_roles

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])


@router.get("", response_model=list[UsuarioOut], summary="Listar usuarios")
def listar(usuario: UsuarioSesion = Depends(requiere_roles("admin"))) -> list[dict]:
    return RepositorioUsuarios(obtener_bd()).listar(usuario.rol_bd)


@router.post(
    "", response_model=UsuarioOut, status_code=201, summary="Crear usuario"
)
def crear(
    datos: UsuarioCrearIn,
    usuario: UsuarioSesion = Depends(requiere_roles("admin")),
) -> dict:
    try:
        creado = RepositorioUsuarios(obtener_bd()).crear(
            nombre=datos.nombre,
            usuario=datos.usuario,
            correo=datos.correo,
            contrasena=datos.contrasena,
            rol=datos.rol,
            puesto=datos.puesto,
            rol_bd=usuario.rol_bd,
        )
    except pg_errors.UniqueViolation as exc:
        raise HTTPException(
            status_code=409,
            detail="Ya existe un usuario o correo con esos datos.",
        ) from exc
    registrar_bitacora_segura(
        obtener_bd(), usuario, "USUARIO_CREADO", entidad="usuario",
        entidad_id=creado["id"],
        detalle={"usuario": creado["usuario"], "rol": creado["rol"]},
    )
    return creado


@router.patch(
    "/{usuario_id}",
    response_model=UsuarioOut,
    summary="Editar nombre, correo, rol o contraseña",
)
def actualizar_usuario(
    usuario_id: int,
    datos: UsuarioActualizar,
    usuario: UsuarioSesion = Depends(requiere_roles("admin")),
) -> dict:
    try:
        return RepositorioUsuarios(obtener_bd()).actualizar(
            usuario_id, datos, usuario, usuario.rol_bd
        )
    except pg_errors.UniqueViolation as exc:
        raise HTTPException(
            status_code=409, detail="Ya existe un usuario o correo con esos datos."
        ) from exc


@router.patch(
    "/{usuario_id}/estado",
    response_model=UsuarioOut,
    summary="Activar o desactivar usuario",
)
def cambiar_estado(
    usuario_id: int,
    datos: UsuarioEstadoIn,
    usuario: UsuarioSesion = Depends(requiere_roles("admin")),
) -> dict:
    if usuario_id == usuario.id and not datos.activo:
        raise HTTPException(
            status_code=409, detail="No puedes desactivar tu propia cuenta."
        )
    repo = RepositorioUsuarios(obtener_bd())
    objetivo = repo.buscar_por_id(usuario_id)
    if objetivo is None:
        raise HTTPException(status_code=404, detail="El usuario no existe.")
    if (
        objetivo["rol"] == "admin"
        and objetivo["activo"]
        and not datos.activo
        and repo.contar_admins_activos(usuario.rol_bd) <= 1
    ):
        raise HTTPException(
            status_code=409,
            detail="Debe existir al menos un administrador activo.",
        )
    actualizado = repo.cambiar_estado(usuario_id, datos.activo, usuario.rol_bd)
    registrar_bitacora_segura(
        obtener_bd(), usuario,
        "USUARIO_ACTIVADO" if datos.activo else "USUARIO_DESACTIVADO",
        entidad="usuario", entidad_id=usuario_id,
        detalle={"usuario": objetivo["usuario"]},
    )
    return actualizado
