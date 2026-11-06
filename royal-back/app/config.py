"""Configuración de Royal Express / LogistiXpress."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


DIRECTORIO_BACKEND = Path(__file__).resolve().parent.parent
DIRECTORIO_PROYECTO = DIRECTORIO_BACKEND.parent
DIRECTORIO_FRONTEND = Path(
    os.getenv("ROYAL_FRONTEND_DIR", str(DIRECTORIO_PROYECTO / "royal-front"))
).resolve()


def _ruta_evidencias() -> Path:
    return Path(
        os.getenv("ROYAL_EVIDENCIAS_DIR", str(DIRECTORIO_BACKEND / "data" / "evidencias"))
    ).resolve()


@dataclass(frozen=True)
class Ajustes:
    dsn: str = os.getenv(
        "LOGISTIXPRESS_DSN",
        "postgresql://postgres:postgres@127.0.0.1:5432/logistixpress",
    )
    secreto: str = os.getenv("ROYAL_SECRETO", "royal-dev-secret-cambiar-en-produccion")
    token_horas: int = int(os.getenv("ROYAL_TOKEN_HORAS", "12"))
    velocidad_kmh: float = float(os.getenv("ROYAL_VELOCIDAD_KMH", "32"))
    minutos_por_entrega: float = float(os.getenv("ROYAL_MINUTOS_ENTREGA", "8"))
    max_evidencia_mb: float = float(os.getenv("ROYAL_MAX_EVIDENCIA_MB", "6"))
    directorio_evidencias: Path = field(default_factory=_ruta_evidencias)
    version: str = "1.0.0"


ajustes = Ajustes()

DEPOSITO_LAT = float(os.getenv("ROYAL_DEPOSITO_LAT", "25.686600"))
DEPOSITO_LON = float(os.getenv("ROYAL_DEPOSITO_LON", "-100.316100"))
DEPOSITO_NOMBRE = os.getenv("ROYAL_DEPOSITO_NOMBRE", "CEDIS LogistiXpress · Andén 1")
