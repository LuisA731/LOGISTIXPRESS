"""Renderizado matplotlib de rutas a PNG (backend Agg, sin display)."""
from __future__ import annotations

import io
import math
import threading

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch

from ..config import DEPOSITO_NOMBRE
from ..modelos.dominio import DEPOSITO

BLOQUEO_MATPLOTLIB = threading.Lock()

_COLORES_ZONA = {
    "NORTE": "#ff7a1a",
    "SUR": "#ff4d6d",
    "ORIENTE": "#ffc145",
    "PONIENTE": "#2dd4bf",
}
_FONDO = "#111c2a"
_PANEL = "#091019"
_TEXTO = "#e8f0fa"
_MUTED = "#8ea2b8"
_BORDE = "#20425f"


class RenderizadorRutas:
    def png_de_ruta(self, ruta: dict) -> bytes:
        with BLOQUEO_MATPLOTLIB:
            fig, ax = plt.subplots(figsize=(7.4, 6.8))
            try:
                self._dibujar(fig, ax, ruta)
                buffer = io.BytesIO()
                fig.savefig(
                    buffer, format="png", dpi=150, bbox_inches="tight",
                    facecolor=fig.get_facecolor(),
                )
                return buffer.getvalue()
            finally:
                plt.close(fig)

    def _dibujar(self, fig, ax, ruta: dict) -> None:
        color = _COLORES_ZONA.get(ruta["zona"], "#ff7a1a")
        paradas = ruta.get("paradas", [])
        lat_cedis, lon_cedis = DEPOSITO.latitud, DEPOSITO.longitud
        lats = [lat_cedis] + [float(p["latitud"]) for p in paradas] + [lat_cedis]
        lons = [lon_cedis] + [float(p["longitud"]) for p in paradas] + [lon_cedis]

        fig.set_facecolor(_FONDO)
        ax.set_facecolor(_FONDO)
        ax.grid(True, color=_BORDE, linewidth=0.6, alpha=0.55)
        ax.set_axisbelow(True)

        ax.plot(lons, lats, color=color, linewidth=2.2, alpha=0.9, zorder=2)

        # Flechas de sentido en cada tramo.
        for (x0, y0), (x1, y1) in zip(zip(lons, lats), zip(lons[1:], lats[1:])):
            if (x0, y0) == (x1, y1):
                continue
            ax.add_patch(
                FancyArrowPatch(
                    (x0, y0), (x1, y1),
                    arrowstyle="-|>", mutation_scale=10,
                    color=color, alpha=0.65, linewidth=1.0, zorder=2,
                )
            )

        ax.scatter(
            lons[1:-1], lats[1:-1], s=150, color=color,
            edgecolors="white", linewidths=1.2, zorder=4,
        )
        for p in paradas:
            ax.annotate(
                str(p["secuencia"]),
                (float(p["longitud"]), float(p["latitud"])),
                textcoords="offset points", xytext=(0, 11), ha="center",
                color="white", fontsize=8.5, weight="bold", zorder=5,
            )
            if len(paradas) <= 10:
                ax.annotate(
                    p["cliente"],
                    (float(p["longitud"]), float(p["latitud"])),
                    textcoords="offset points", xytext=(0, -15), ha="center",
                    color=_MUTED, fontsize=6.5, zorder=5,
                )

        ax.scatter(
            [lon_cedis], [lat_cedis], marker="*", s=430,
            color="#ffd166", edgecolors="white", linewidths=1.1, zorder=6,
        )
        ax.annotate(
            DEPOSITO_NOMBRE,
            (lon_cedis, lat_cedis),
            textcoords="offset points", xytext=(12, -12),
            color="#ffd166", fontsize=7.5, zorder=6,
        )

        distancia = float(ruta.get("distancia_km") or 0)
        base = float(ruta.get("distancia_base_km") or 0)
        ahorro = float(ruta.get("ahorro_pct") or 0)
        eta = float(ruta.get("eta_min") or 0)
        stats = (
            f"{ruta.get('num_paradas', len(paradas))} paradas · "
            f"{ruta.get('num_bultos', 0)} bultos · "
            f"{float(ruta.get('peso_total_kg') or 0):.0f} kg · "
            f"{float(ruta.get('volumen_total_m3') or 0):.2f} m³\n"
            f"Distancia: {distancia:.1f} km "
            f"(base {base:.1f} km · ahorro {ahorro:.1f}%)\n"
            f"ETA ≈ {eta:.0f} min"
        )
        ax.text(
            0.02, 0.02, stats, transform=ax.transAxes, color=_TEXTO,
            fontsize=8, va="bottom",
            bbox=dict(
                boxstyle="round,pad=0.55", facecolor=_PANEL,
                edgecolor=color, alpha=0.96,
            ),
        )

        ax.set_title(
            f"Ruta {ruta['folio']} · Zona {ruta['zona']} · "
            f"{ruta['conductor']['nombre']} ({ruta['vehiculo']['placas']})",
            color="white", fontsize=10.5, pad=12,
        )
        ax.tick_params(colors=_MUTED, labelsize=7)
        for lado in ax.spines.values():
            lado.set_color(_BORDE)
        ax.set_xlabel("longitud", color=_MUTED, fontsize=7.5)
        ax.set_ylabel("latitud", color=_MUTED, fontsize=7.5)

        margen = 0.006
        ax.set_xlim(min(lons) - margen, max(lons) + margen)
        ax.set_ylim(min(lats) - margen, max(lats) + margen)
        lat_media = sum(lats) / len(lats)
        ax.set_aspect(1 / max(math.cos(math.radians(lat_media)), 0.2))
