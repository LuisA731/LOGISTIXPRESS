"""Autenticación de usuarios."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ..dependencias import obtener_bd, registrar_bitacora_segura
from ..modelos.esquemas import LoginIn, TokenOut, UsuarioOut
from ..repositorios.usuarios import RepositorioUsuarios
from ..seguridad import (
    UsuarioSesion,
    crear_token,
    usuario_actual,
    verificar_password,
)

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/login", response_model=TokenOut, summary="Iniciar sesión")
def login(datos: LoginIn) -> TokenOut:
    repo = RepositorioUsuarios(obtener_bd())
    fila = repo.buscar_por_usuario(datos.usuario)
    if (
        fila is None
        or not fila["activo"]
        or not verificar_password(datos.contrasena, fila["password_hash"])
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos.",
        )
    usuario = UsuarioSesion(
        id=fila["id"],
        nombre=fila["nombre"],
        usuario=fila["usuario"],
        correo=fila["correo"],
        rol=fila["rol"],
    )
    registrar_bitacora_segura(
        obtener_bd(), usuario, "INICIO_SESION", entidad="usuario",
        entidad_id=usuario.id, detalle={"usuario": usuario.usuario},
    )
    return TokenOut(
        token=crear_token(usuario),
        usuario=UsuarioOut(
            id=fila["id"], nombre=fila["nombre"], usuario=fila["usuario"],
            correo=fila["correo"], rol=fila["rol"], puesto=fila["puesto"],
            activo=fila["activo"],
        ),
    )


@router.get("/me", response_model=UsuarioOut, summary="Perfil de la sesión actual")
def perfil(usuario: UsuarioSesion = Depends(usuario_actual)) -> UsuarioOut:
    fila = RepositorioUsuarios(obtener_bd()).buscar_por_id(usuario.id)
    if fila is None or not fila["activo"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="La cuenta ya no está activa.",
        )
    return UsuarioOut(**fila)


@router.post("/logout", summary="Cerrar sesión")
def logout(usuario: UsuarioSesion = Depends(usuario_actual)) -> dict:
    registrar_bitacora_segura(
        obtener_bd(), usuario, "CIERRE_SESION", entidad="usuario",
        entidad_id=usuario.id,
    )
    return {"mensaje": "Sesión cerrada. El token expirará automáticamente."}
