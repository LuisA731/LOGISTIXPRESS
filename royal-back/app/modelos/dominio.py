"""Dominio de reparto: pedidos, bultos, flota y plan de rutas.

Las coordenadas son geográficas reales (latitud/longitud) de la semilla. La
distancia se calcula con Haversine, suficiente para el PoC sin depender de un
servicio de ruteo externo.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum

from ..config import DEPOSITO_LAT, DEPOSITO_LON


class Zona(str, Enum):
    NORTE = "NORTE"
    SUR = "SUR"
    ORIENTE = "ORIENTE"
    PONIENTE = "PONIENTE"


TIPO_PRIORIDAD = {
    "MAYORISTA": 0,
    "HOSPITAL": 1,
    "FARMACIA": 2,
    "CORPORATIVO": 3,
    "RESTAURANTE": 4,
    "MINORISTA": 5,
}


@dataclass(frozen=True)
class PuntoGeo:
    latitud: float
    longitud: float


DEPOSITO = PuntoGeo(DEPOSITO_LAT, DEPOSITO_LON)


def distancia_km(a: PuntoGeo, b: PuntoGeo) -> float:
    """Distancia ortodrómica (Haversine) en kilómetros."""
    radio_tierra = 6371.0088
    lat1, lon1 = math.radians(a.latitud), math.radians(a.longitud)
    lat2, lon2 = math.radians(b.latitud), math.radians(b.longitud)
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    return 2 * radio_tierra * math.asin(math.sqrt(h))


@dataclass
class BultoPlan:
    id: int
    guia: str
    descripcion: str
    peso_kg: float
    volumen_m3: float


@dataclass
class ClientePlan:
    id: int
    codigo: str
    nombre: str
    tipo_cliente: str
    zona: Zona
    direccion: str
    telefono: str | None
    punto: PuntoGeo


@dataclass
class PedidoPlan:
    id: int
    folio: str
    cliente: ClientePlan
    prioridad: str
    peso_kg: float
    volumen_m3: float
    bultos: list[BultoPlan] = field(default_factory=list)

    @property
    def es_prioritario(self) -> bool:
        return self.prioridad == "ALTA"

    @property
    def tipo_cliente(self) -> str:
        return self.cliente.tipo_cliente

    @property
    def zona(self) -> Zona:
        return self.cliente.zona


@dataclass
class ParadaPlan:
    pedido: PedidoPlan
    secuencia: int = 0
    distancia_km: float = 0.0
    eta_min: float = 0.0


@dataclass
class VehiculoPlan:
    id: int
    placas: str
    modelo: str
    capacidad_kg: float
    capacidad_m3: float


@dataclass
class ConductorPlan:
    id: int
    nombre: str
    telefono: str | None = None
    licencia: str | None = None


@dataclass
class MetricasRuta:
    distancia_km: float
    distancia_base_km: float
    eta_min: float

    @property
    def ahorro_pct(self) -> float:
        if self.distancia_base_km <= 0:
            return 0.0
        return round((1 - self.distancia_km / self.distancia_base_km) * 100, 2)


@dataclass
class ViajePlan:
    zona: Zona
    vehiculo: VehiculoPlan
    conductor: ConductorPlan
    paradas: list[ParadaPlan] = field(default_factory=list)
    folio: str = ""
    metricas: MetricasRuta | None = None

    @property
    def peso_total_kg(self) -> float:
        return round(sum(p.pedido.peso_kg for p in self.paradas), 3)

    @property
    def volumen_total_m3(self) -> float:
        return round(sum(p.pedido.volumen_m3 for p in self.paradas), 4)

    @property
    def total_bultos(self) -> int:
        return sum(len(p.pedido.bultos) for p in self.paradas)

    @property
    def tipo_principal(self) -> str:
        if not self.paradas:
            return "MIXTO"
        conteo: dict[str, int] = {}
        for p in self.paradas:
            conteo[p.pedido.tipo_cliente] = conteo.get(p.pedido.tipo_cliente, 0) + 1
        return max(conteo, key=conteo.get)

    def cabe(self, pedido: PedidoPlan) -> bool:
        return (
            self.peso_total_kg + pedido.peso_kg <= self.vehiculo.capacidad_kg
            and self.volumen_total_m3 + pedido.volumen_m3 <= self.vehiculo.capacidad_m3
        )


@dataclass
class PlanRutas:
    fecha: date
    generado_en: datetime
    viajes: list[ViajePlan]
    total_pedidos: int
    total_bultos: int

    @property
    def distancia_total_km(self) -> float:
        return round(
            sum(v.metricas.distancia_km for v in self.viajes if v.metricas), 2
        )

    @property
    def distancia_base_total_km(self) -> float:
        return round(
            sum(v.metricas.distancia_base_km for v in self.viajes if v.metricas), 2
        )

    @property
    def ahorro_global_pct(self) -> float:
        base = self.distancia_base_total_km
        if base <= 0:
            return 0.0
        return round((1 - self.distancia_total_km / base) * 100, 2)


class ErrorPlanificacion(Exception):
    """Error de negocio al armar el plan (sin viajes posibles, etc.)."""
