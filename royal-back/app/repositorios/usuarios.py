"""Repositorio de usuarios y credenciales."""
from __future__ import annotations

from ..dependencias import registrar_bitacora
from ..db import BaseDatos
from ..errores import ErrorNegocio
from ..modelos.esquemas_operaciones import UsuarioActualizar
from ..seguridad import UsuarioSesion, hash_password
from .base import RepositorioBase


class RepositorioUsuarios(RepositorioBase):
    def __init__(self, bd: BaseDatos):
        # El login consulta credenciales antes de conocer el rol de sesión.
        super().__init__(bd, rol_bd=None)

    def buscar_por_usuario(self, usuario: str) -> dict | None:
        with self.cursor() as cur:
            cur.execute(
                """
                SELECT id, nombre, usuario, correo, password_hash, rol, puesto, activo
                FROM seguridad.usuarios
                WHERE lower(usuario) = lower(%s)
                """,
                (usuario,),
            )
            return cur.fetchone()

    def buscar_por_id(self, usuario_id: int) -> dict | None:
        with self.cursor() as cur:
            cur.execute(
                """
                SELECT id, nombre, usuario, correo, rol, puesto, activo
                FROM seguridad.usuarios WHERE id = %s
                """,
                (usuario_id,),
            )
            return cur.fetchone()

    def listar(self, rol_bd: str = "rol_admin") -> list[dict]:
        with self._bd.cursor(rol_bd) as cur:
            cur.execute(
                """
                SELECT id, nombre, usuario, correo, rol, puesto, activo, creado_en
                FROM seguridad.usuarios
                ORDER BY activo DESC, rol, nombre
                """
            )
            return list(cur.fetchall())

    def crear(
        self,
        *,
        nombre: str,
        usuario: str,
        correo: str | None,
        contrasena: str,
        rol: str,
        puesto: str = "Administración",
        rol_bd: str = "rol_admin",
    ) -> dict:
        with self._bd.cursor(rol_bd) as cur:
            cur.execute(
                """
                INSERT INTO seguridad.usuarios
                    (nombre, usuario, correo, password_hash, rol, puesto)
                VALUES (%s, lower(%s), %s, %s, %s, %s)
                RETURNING id, nombre, usuario, correo, rol, puesto, activo
                """,
                (nombre, usuario, correo, hash_password(contrasena), rol, puesto),
            )
            return cur.fetchone()

    def actualizar(
        self,
        usuario_id: int,
        datos: UsuarioActualizar,
        usuario_sesion: UsuarioSesion,
        rol_bd: str = "rol_admin",
    ) -> dict:
        with self._bd.cursor(rol_bd) as cur:
            cur.execute(
                "SELECT id, nombre, usuario, correo, rol, puesto, activo "
                "FROM seguridad.usuarios WHERE id = %s FOR UPDATE",
                (usuario_id,),
            )
            objetivo = cur.fetchone()
            if objetivo is None:
                raise ErrorNegocio("El usuario no existe.", 404)
            if objetivo["rol"] == "admin" and datos.rol not in (None, "admin"):
                cur.execute(
                    "SELECT COUNT(*)::int AS total FROM seguridad.usuarios "
                    "WHERE rol = 'admin' AND activo = TRUE"
                )
                if cur.fetchone()["total"] <= 1:
                    raise ErrorNegocio(
                        "Debe existir al menos un administrador activo.", 409
                    )
            password_hash = hash_password(datos.contrasena) if datos.contrasena else None
            cur.execute(
                """
                UPDATE seguridad.usuarios
                SET nombre = COALESCE(%s, nombre),
                    correo = COALESCE(%s, correo),
                    rol = COALESCE(%s, rol),
                    puesto = COALESCE(%s, puesto),
                    password_hash = COALESCE(%s, password_hash)
                WHERE id = %s
                RETURNING id, nombre, usuario, correo, rol, puesto, activo
                """,
                (datos.nombre, datos.correo, datos.rol, datos.puesto,
                 password_hash, usuario_id),
            )
            actualizado = cur.fetchone()
            registrar_bitacora(
                cur, usuario_sesion, "USUARIO_ACTUALIZADO", entidad="usuario",
                entidad_id=usuario_id,
                detalle={"usuario": actualizado["usuario"], "rol": actualizado["rol"]},
            )
            return actualizado

    def cambiar_estado(self, usuario_id: int, activo: bool, rol_bd: str = "rol_admin") -> dict | None:
        with self._bd.cursor(rol_bd) as cur:
            cur.execute(
                """
                UPDATE seguridad.usuarios SET activo = %s
                WHERE id = %s
                RETURNING id, nombre, usuario, correo, rol, puesto, activo
                """,
                (activo, usuario_id),
            )
            return cur.fetchone()

    def contar_admins_activos(self, rol_bd: str = "rol_admin") -> int:
        with self._bd.cursor(rol_bd) as cur:
            cur.execute(
                "SELECT COUNT(*)::int AS total FROM seguridad.usuarios "
                "WHERE rol = 'admin' AND activo = TRUE"
            )
            return cur.fetchone()["total"]
