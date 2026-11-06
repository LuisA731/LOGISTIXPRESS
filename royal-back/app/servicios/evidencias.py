"""Guardado y resolución de evidencias de entrega (firma y fotografía)."""
from __future__ import annotations

import base64
import binascii
import re
import secrets
from pathlib import Path

from ..config import ajustes

_EXTENSIONES = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
}
_FIRMAS = {
    "png": b"\x89PNG\r\n\x1a\n",
    "jpg": b"\xff\xd8\xff",
}


class ErrorEvidencia(ValueError):
    pass


def _sanitizar(texto: str) -> str:
    limpio = re.sub(r"[^A-Za-z0-9._-]+", "_", texto)
    return limpio.strip("._") or "ruta"


class ServicioEvidencias:
    def __init__(self, raiz: Path | None = None, max_mb: float | None = None):
        self._raiz = (raiz or ajustes.directorio_evidencias).resolve()
        self._max_bytes = int((max_mb or ajustes.max_evidencia_mb) * 1024 * 1024)

    @property
    def raiz(self) -> Path:
        return self._raiz

    def guardar(
        self, *, ruta_folio: str, parada_id: int, tipo: str, data_url: str | None
    ) -> str | None:
        if not data_url:
            return None
        try:
            cabecera, contenido = data_url.split(",", 1)
            if not cabecera.startswith("data:") or ";base64" not in cabecera:
                raise ErrorEvidencia("La evidencia no es una imagen base64 válida.")
            mime = cabecera[5:].split(";", 1)[0].lower()
            if mime not in _EXTENSIONES:
                raise ErrorEvidencia("Solo se aceptan imágenes PNG o JPG.")
            crudo = base64.b64decode(contenido, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise ErrorEvidencia("No se pudo decodificar la imagen de evidencia.") from exc

        if not crudo:
            raise ErrorEvidencia("La imagen de evidencia está vacía.")
        if len(crudo) > self._max_bytes:
            raise ErrorEvidencia(
                f"La evidencia supera el límite de {self._max_bytes / (1024 * 1024):.0f} MB."
            )
        extension = _EXTENSIONES[mime]
        if not crudo.startswith(_FIRMAS[extension]):
            raise ErrorEvidencia("El archivo no corresponde al formato de imagen declarado.")

        carpeta = self._raiz / _sanitizar(ruta_folio) / str(parada_id)
        carpeta.mkdir(parents=True, exist_ok=True)
        nombre = f"{_sanitizar(tipo)}-{secrets.token_hex(6)}.{extension}"
        destino = carpeta / nombre
        destino.write_bytes(crudo)
        return str(destino.relative_to(self._raiz))

    def resolver(self, ruta_relativa: str) -> Path | None:
        try:
            destino = (self._raiz / ruta_relativa).resolve()
            destino.relative_to(self._raiz)
        except (ValueError, OSError):
            return None
        return destino if destino.is_file() else None

    def eliminar(self, ruta_relativa: str | None) -> None:
        if not ruta_relativa:
            return
        destino = self.resolver(ruta_relativa)
        if destino is not None:
            try:
                destino.unlink()
            except OSError:
                pass
