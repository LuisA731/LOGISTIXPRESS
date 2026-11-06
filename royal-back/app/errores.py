"""Errores de negocio con traducción HTTP."""
from __future__ import annotations

from typing import Any


class ErrorNegocio(Exception):
    def __init__(self, mensaje: str, codigo: int = 400, extra: dict[str, Any] | None = None):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.codigo = codigo
        self.extra = extra or {}
