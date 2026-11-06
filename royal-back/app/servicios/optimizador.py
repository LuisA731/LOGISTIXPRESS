"""Optimización TSP para el PoC: vecino más cercano + 2-opt.

No se busca precisión milimétrica. La métrica contra el orden natural de carga
se muestra en el dashboard para hacer transparente la mejora.
"""
from __future__ import annotations

from itertools import pairwise

from ..modelos.dominio import DEPOSITO, ParadaPlan, PuntoGeo, distancia_km


def distancia_ruta(deposito: PuntoGeo, paradas: list[ParadaPlan]) -> float:
    if not paradas:
        return 0.0
    puntos = [deposito, *(p.pedido.cliente.punto for p in paradas), deposito]
    return sum(distancia_km(a, b) for a, b in pairwise(puntos))


def vecino_mas_cercano(
    paradas: list[ParadaPlan], deposito: PuntoGeo = DEPOSITO
) -> list[ParadaPlan]:
    restantes = list(paradas)
    ruta: list[ParadaPlan] = []
    actual = deposito
    while restantes:
        siguiente = min(
            restantes, key=lambda p: distancia_km(actual, p.pedido.cliente.punto)
        )
        ruta.append(siguiente)
        restantes.remove(siguiente)
        actual = siguiente.pedido.cliente.punto
    return ruta


def mejorar_dos_opt(
    paradas: list[ParadaPlan],
    deposito: PuntoGeo = DEPOSITO,
    max_pasadas: int = 40,
) -> list[ParadaPlan]:
    ruta = vecino_mas_cercano(paradas, deposito)
    if len(ruta) < 4:
        return ruta

    mejor = distancia_ruta(deposito, ruta)
    for _ in range(max_pasadas):
        mejoro = False
        for i in range(len(ruta) - 1):
            for j in range(i + 2, len(ruta) + 1):
                candidata = ruta[:i] + ruta[i:j][::-1] + ruta[j:]
                distancia = distancia_ruta(deposito, candidata)
                if distancia < mejor - 1e-9:
                    ruta, mejor, mejoro = candidata, distancia, True
        if not mejoro:
            break
    return ruta
