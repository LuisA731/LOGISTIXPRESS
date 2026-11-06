import pytest
from fastapi import HTTPException

from app.seguridad import (
    UsuarioSesion,
    crear_token,
    hash_password,
    leer_token,
    verificar_password,
)


def test_password_roundtrip():
    almacenado = hash_password("secreto-123")
    assert verificar_password("secreto-123", almacenado)
    assert not verificar_password("otro", almacenado)
    assert not verificar_password("secreto-123", "hash-invalido")


def test_token_roundtrip_y_manipulacion():
    usuario = UsuarioSesion(7, "Ana", "ana", "operador", "ana@example.com")
    token = crear_token(usuario)
    leido = leer_token(token)
    assert leido.id == 7
    assert leido.rol == "operador"
    assert leido.rol_bd == "rol_operador"

    with pytest.raises(HTTPException) as exc:
        leer_token(token[:-2] + "xx")
    assert exc.value.status_code == 401
