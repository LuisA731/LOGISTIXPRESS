"""Consolidación de pedidos en viajes y cálculo de métricas."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timezone

from ..modelos.dominio import (
    DEPOSITO,
    TIPO_PRIORIDAD,
    ConductorPlan,
    ErrorPlanificacion,
    MetricasRuta,
    ParadaPlan,
    PedidoPlan,
    PlanRutas,
    PuntoGeo,
    VehiculoPlan,
    ViajePlan,
    Zona,
    distancia_km,
)
from .optimizador import distancia_ruta, mejorar_dos_opt


class PlanificadorRutas:
    def __init__(
        self,
        vehiculos: list[VehiculoPlan],
        conductores: list[ConductorPlan],
        *,
        deposito: PuntoGeo = DEPOSITO,
        velocidad_kmh: float = 32.0,
        minutos_por_entrega: float = 8.0,
    ):
        if not vehiculos:
            raise ValueError("La flota no tiene vehículos activos")
        if not conductores:
            raise ValueError("No hay conductores activos")
        if velocidad_kmh <= 0:
            raise ValueError("La velocidad debe ser mayor que cero")
        self._vehiculos = sorted(vehiculos, key=lambda v: v.capacidad_kg)
        self._conductores = conductores
        self._deposito = deposito
        self._velocidad = velocidad_kmh
        self._min_entrega = minutos_por_entrega
        self._indice_vehiculo = 0
        self._indice_conductor = 0

    def planificar(self, pedidos: list[PedidoPlan], fecha: date | None = None) -> PlanRutas:
        if not pedidos:
            raise ErrorPlanificacion("No hay pedidos listos para planificar.")
        fecha = fecha or date.today()
        por_zona: dict[Zona, list[PedidoPlan]] = defaultdict(list)
        for pedido in pedidos:
            por_zona[pedido.zona].append(pedido)

        viajes: list[ViajePlan] = []
        for zona in Zona:
            pedidos_zona = por_zona.get(zona, [])
            if not pedidos_zona:
                continue
            pedidos_zona.sort(
                key=lambda p: (
                    TIPO_PRIORIDAD.get(p.tipo_cliente, 99),
                    not p.es_prioritario,
                    -p.peso_kg,
                    p.folio,
                )
            )
            viajes.extend(self._empaquetar(zona, pedidos_zona))

        for viaje in viajes:
            self._optimizar(viaje)

        return PlanRutas(
            fecha=fecha,
            generado_en=datetime.now(timezone.utc),
            viajes=viajes,
            total_pedidos=len(pedidos),
            total_bultos=sum(len(p.bultos) for p in pedidos),
        )

    def _empaquetar(self, zona: Zona, pedidos: list[PedidoPlan]) -> list[ViajePlan]:
        abiertos: list[ViajePlan] = []
        for pedido in pedidos:
            destino = next((v for v in abiertos if v.cabe(pedido)), None)
            if destino is None:
                vehiculo = self._elegir_vehiculo(pedido)
                conductor = self._siguiente_conductor()
                destino = ViajePlan(zona=zona, vehiculo=vehiculo, conductor=conductor)
                abiertos.append(destino)
            destino.paradas.append(ParadaPlan(pedido=pedido))
        return abiertos

    def _elegir_vehiculo(self, pedido: PedidoPlan) -> VehiculoPlan:
        for offset in range(len(self._vehiculos)):
            indice = (self._indice_vehiculo + offset) % len(self._vehiculos)
            vehiculo = self._vehiculos[indice]
            if (
                pedido.peso_kg <= vehiculo.capacidad_kg
                and pedido.volumen_m3 <= vehiculo.capacidad_m3
            ):
                self._indice_vehiculo = (indice + 1) % len(self._vehiculos)
                return vehiculo
        raise ErrorPlanificacion(
            f"El pedido {pedido.folio} ({pedido.peso_kg:.1f} kg · "
            f"{pedido.volumen_m3:.2f} m³) excede la capacidad de toda la flota."
        )

    def _siguiente_conductor(self) -> ConductorPlan:
        conductor = self._conductores[self._indice_conductor % len(self._conductores)]
        self._indice_conductor += 1
        return conductor

    def _optimizar(self, viaje: ViajePlan) -> None:
        orden_base = list(viaje.paradas)
        optimizadas = mejorar_dos_opt(orden_base, self._deposito)

        acumulado = 0.0
        anterior = self._deposito
        for secuencia, parada in enumerate(optimizadas, start=1):
            punto = parada.pedido.cliente.punto
            tramo = distancia_km(anterior, punto)
            acumulado += tramo
            parada.secuencia = secuencia
            parada.distancia_km = round(tramo, 2)
            parada.eta_min = round(
                acumulado / self._velocidad * 60 + (secuencia - 1) * self._min_entrega,
                1,
            )
            anterior = punto

        distancia = distancia_ruta(self._deposito, optimizadas)
        distancia_base = distancia_ruta(self._deposito, orden_base)
        viaje.paradas = optimizadas
        viaje.metricas = MetricasRuta(
            distancia_km=round(distancia, 2),
            distancia_base_km=round(distancia_base, 2),
            eta_min=round(
                distancia / self._velocidad * 60
                + len(optimizadas) * self._min_entrega,
                1,
            ),
        )
