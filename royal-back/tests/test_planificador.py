from datetime import date

import pytest

from app.modelos.dominio import (
    DEPOSITO,
    BultoPlan,
    ClientePlan,
    ConductorPlan,
    ErrorPlanificacion,
    ParadaPlan,
    PedidoPlan,
    PuntoGeo,
    VehiculoPlan,
    Zona,
)
from app.servicios.optimizador import distancia_ruta, mejorar_dos_opt
from app.servicios.planificador import PlanificadorRutas


def cliente(nombre: str, zona: Zona, lat: float, lon: float) -> ClientePlan:
    return ClientePlan(
        id=hash(nombre) % 10000,
        codigo=nombre,
        nombre=nombre,
        tipo_cliente="MINORISTA",
        zona=zona,
        direccion="Calle de prueba",
        telefono=None,
        punto=PuntoGeo(lat, lon),
    )


def pedido(nombre: str, zona: Zona, lat: float, lon: float, peso: float, vol: float, bultos=2):
    return PedidoPlan(
        id=hash(nombre) % 10000,
        folio=nombre,
        cliente=cliente(nombre, zona, lat, lon),
        prioridad="NORMAL",
        peso_kg=peso,
        volumen_m3=vol,
        bultos=[
            BultoPlan(i, f"LX-{nombre}-{i}", "Caja", peso / bultos, vol / bultos)
            for i in range(bultos)
        ],
    )


def planificador(capacidad_kg=500, capacidad_m3=5, conductores=2):
    return PlanificadorRutas(
        [VehiculoPlan(1, "LX-0001", "Van", capacidad_kg, capacidad_m3)],
        [ConductorPlan(i, f"Conductor {i}") for i in range(1, conductores + 1)],
        velocidad_kmh=30,
        minutos_por_entrega=5,
    )


def test_optimizador_conserva_paradas_y_no_empeora():
    pedidos = [
        pedido("P1", Zona.NORTE, 25.70, -100.30, 10, 0.1),
        pedido("P2", Zona.NORTE, 25.75, -100.25, 10, 0.1),
        pedido("P3", Zona.NORTE, 25.65, -100.35, 10, 0.1),
        pedido("P4", Zona.NORTE, 25.80, -100.20, 10, 0.1),
    ]
    paradas = [ParadaPlan(p) for p in pedidos]
    orden = mejorar_dos_opt(paradas)
    assert {p.pedido.folio for p in orden} == {"P1", "P2", "P3", "P4"}
    assert distancia_ruta(DEPOSITO, orden) <= distancia_ruta(DEPOSITO, paradas) + 1e-6


def test_planificador_consolida_por_zona_y_capacidad():
    p = planificador(capacidad_kg=250, capacidad_m3=5)
    pedidos = [
        pedido("N1", Zona.NORTE, 25.72, -100.30, 100, 0.5),
        pedido("N2", Zona.NORTE, 25.76, -100.28, 100, 0.5),
        pedido("N3", Zona.NORTE, 25.80, -100.26, 100, 0.5),
        pedido("S1", Zona.SUR, 25.62, -100.32, 80, 0.4),
    ]
    plan = p.planificar(pedidos, date(2026, 11, 5))
    assert plan.total_pedidos == 4
    assert plan.total_bultos == 8
    assert all(v.zona in {Zona.NORTE, Zona.SUR} for v in plan.viajes)
    for viaje in plan.viajes:
        assert viaje.peso_total_kg <= viaje.vehiculo.capacidad_kg
        assert viaje.volumen_total_m3 <= viaje.vehiculo.capacidad_m3
        assert [p.secuencia for p in viaje.paradas] == list(range(1, len(viaje.paradas) + 1))
        assert viaje.metricas is not None
        assert viaje.metricas.distancia_km > 0
    # Los 3 pedidos del norte no caben en un vehículo de 250 kg.
    viajes_norte = [v for v in plan.viajes if v.zona == Zona.NORTE]
    assert len(viajes_norte) == 2


def test_planificador_falla_si_un_pedido_excede_la_flota():
    p = planificador(capacidad_kg=100)
    with pytest.raises(ErrorPlanificacion):
        p.planificar([pedido("GIGANTE", Zona.NORTE, 25.7, -100.3, 500, 1, bultos=1)])


def test_prioriza_tipo_de_cliente_y_asigna_conductores():
    p = planificador(capacidad_kg=15, capacidad_m3=1)
    pedidos = [
        pedido("M1", Zona.NORTE, 25.70, -100.30, 10, 0.1),
        pedido("M2", Zona.NORTE, 25.71, -100.31, 10, 0.1),
    ]
    pedidos[0].cliente.tipo_cliente = "MINORISTA"
    pedidos[1].cliente.tipo_cliente = "MAYORISTA"
    plan = p.planificar(pedidos)
    assert len(plan.viajes) == 2
    assert plan.viajes[0].paradas[0].pedido.folio == "M2"
    assert plan.viajes[0].conductor.nombre.startswith("Conductor")
    assert plan.viajes[1].conductor.nombre != plan.viajes[0].conductor.nombre
