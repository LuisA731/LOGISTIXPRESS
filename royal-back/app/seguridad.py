"""Autenticación, tokens HMAC y utilidades de contraseña (solo stdlib)."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import ajustes

ROLES = ("admin", "operador", "auditor")
ROL_BD = {
    "admin": "rol_admin",
    "operador": "rol_operador",
    "auditor": "rol_auditor",
}
NOMBRE_ROL = {
    "admin": "Administrador",
    "operador": "Operador",
    "auditor": "Auditor",
}

_portador = HTTPBearer(auto_error=False, description="Token Bearer emitido por /api/auth/login")


@dataclass(frozen=True)
class UsuarioSesion:
    id: int
    nombre: str
    usuario: str
    rol: str
    correo: str | None = None

    @property
    def rol_bd(self) -> str:
        return ROL_BD[self.rol]


def hash_password(password: str, iteraciones: int = 200_000) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iteraciones)
    return "pbkdf2_sha256${}${}${}".format(
        iteraciones,
        base64.b64encode(salt).decode("ascii"),
        base64.b64encode(digest).decode("ascii"),
    )


def verificar_password(password: str, almacenado: str) -> bool:
    try:
        algoritmo, iteraciones, salt_b64, hash_b64 = almacenado.split("$", 3)
        if algoritmo != "pbkdf2_sha256":
            return False
        salt = base64.b64decode(salt_b64)
        esperado = base64.b64decode(hash_b64)
        calculado = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, int(iteraciones)
        )
        return hmac.compare_digest(esperado, calculado)
    except (ValueError, TypeError):
        return False


def _b64url(datos: bytes) -> str:
    return base64.urlsafe_b64encode(datos).rstrip(b"=").decode("ascii")


def _b64url_decodificar(texto: str) -> bytes:
    return base64.urlsafe_b64decode(texto + "=" * (-len(texto) % 4))


def crear_token(usuario: UsuarioSesion, horas: int | None = None) -> str:
    ahora = int(time.time())
    payload = {
        "sub": usuario.id,
        "nombre": usuario.nombre,
        "usuario": usuario.usuario,
        "correo": usuario.correo,
        "rol": usuario.rol,
        "iat": ahora,
        "exp": ahora + int((horas or ajustes.token_horas) * 3600),
    }
    cuerpo = _b64url(json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode())
    firma = hmac.new(ajustes.secreto.encode(), cuerpo.encode(), hashlib.sha256).digest()
    return f"{cuerpo}.{_b64url(firma)}"


def leer_token(token: str) -> UsuarioSesion:
    try:
        cuerpo, firma = token.split(".", 1)
        esperada = hmac.new(
            ajustes.secreto.encode(), cuerpo.encode(), hashlib.sha256
        ).digest()
        if not hmac.compare_digest(esperada, _b64url_decodificar(firma)):
            raise ValueError("firma inválida")
        payload = json.loads(_b64url_decodificar(cuerpo))
        if int(payload.get("exp", 0)) < int(time.time()):
            raise ValueError("token expirado")
        rol = payload.get("rol")
        if rol not in ROLES:
            raise ValueError("rol inválido")
        return UsuarioSesion(
            id=int(payload["sub"]),
            nombre=payload.get("nombre", ""),
            usuario=payload.get("usuario", ""),
            correo=payload.get("correo"),
            rol=rol,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesión inválida o expirada. Vuelve a iniciar sesión.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def usuario_actual(
    credenciales: HTTPAuthorizationCredentials | None = Depends(_portador),
) -> UsuarioSesion:
    if credenciales is None or credenciales.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Se requiere iniciar sesión.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return leer_token(credenciales.credentials)


def requiere_roles(*roles: str):
    def dependencia(usuario: UsuarioSesion = Depends(usuario_actual)) -> UsuarioSesion:
        if usuario.rol not in roles:
            nombres = ", ".join(NOMBRE_ROL[r] for r in roles)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Tu rol {NOMBRE_ROL[usuario.rol]} no tiene acceso. Requiere: {nombres}.",
            )
        return usuario

    return dependencia


def ahora_utc() -> datetime:
    return datetime.now(timezone.utc)
