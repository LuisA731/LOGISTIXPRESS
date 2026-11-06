"""Base común de repositorios."""
from __future__ import annotations

from contextlib import contextmanager

from ..db import BaseDatos


class RepositorioBase:
    def __init__(self, bd: BaseDatos, rol_bd: str | None = None):
        self._bd = bd
        self._rol_bd = rol_bd

    @contextmanager
    def cursor(self):
        with self._bd.cursor(self._rol_bd) as cur:
            yield cur
