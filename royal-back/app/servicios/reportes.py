"""Generación de reportes PDF y XLSX sin servicios externos."""
from __future__ import annotations

import io
from datetime import datetime

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from .renderizador import BLOQUEO_MATPLOTLIB


class GeneradorReportes:
    def pdf(
        self,
        *,
        titulo: str,
        subtitulo: str,
        columnas: list[str],
        filas: list[list],
        usuario: str,
        rol: str,
    ) -> bytes:
        with BLOQUEO_MATPLOTLIB:
            buffer = io.BytesIO()
            with PdfPages(buffer) as pdf:
                por_pagina = 24
                paginas = [filas[i:i + por_pagina] for i in range(0, len(filas), por_pagina)] or [[]]
                for indice, bloque in enumerate(paginas, start=1):
                    self._pagina(
                        pdf, titulo, subtitulo, columnas, bloque,
                        usuario, rol, indice, len(paginas),
                    )
            return buffer.getvalue()

    def _pagina(
        self,
        pdf: PdfPages,
        titulo: str,
        subtitulo: str,
        columnas: list[str],
        filas: list[list],
        usuario: str,
        rol: str,
        pagina: int,
        total_paginas: int,
    ) -> None:
        fig, ax = plt.subplots(figsize=(11, 8.5))
        fig.patch.set_facecolor("white")
        ax.axis("off")
        ax.text(
            0.02, 0.955, "LogistiXpress · Royal Express", fontsize=9,
            color="#ff6a00", weight="bold", transform=ax.transAxes,
        )
        ax.text(
            0.02, 0.915, titulo, fontsize=17, color="#0b1a2c",
            weight="bold", transform=ax.transAxes,
        )
        ax.text(
            0.02, 0.882, subtitulo, fontsize=9, color="#5b6b7c",
            transform=ax.transAxes,
        )
        ax.text(
            0.98, 0.955, f"Página {pagina}/{total_paginas}", fontsize=8,
            color="#5b6b7c", ha="right", transform=ax.transAxes,
        )
        ax.text(
            0.98, 0.925,
            f"Generado: {datetime.now():%d/%m/%Y %H:%M}\n{usuario} · {rol}",
            fontsize=7.5, color="#5b6b7c", ha="right", va="top",
            transform=ax.transAxes,
        )

        if not filas:
            ax.text(
                0.5, 0.5, "Sin registros para el periodo seleccionado.",
                fontsize=12, color="#5b6b7c", ha="center", va="center",
                transform=ax.transAxes,
            )
            pdf.savefig(fig, facecolor="white")
            plt.close(fig)
            return

        tabla = ax.table(
            cellText=filas,
            colLabels=columnas,
            cellLoc="left",
            colLoc="left",
            loc="upper center",
            bbox=[0.02, 0.06, 0.96, 0.76],
        )
        tabla.auto_set_font_size(False)
        tabla.set_fontsize(7.2)
        for (fila, columna), celda in tabla.get_celld().items():
            celda.set_edgecolor("#d7e0ea")
            celda.set_linewidth(0.5)
            if fila == 0:
                celda.set_facecolor("#0b1a2c")
                celda.get_text().set_color("white")
                celda.get_text().set_weight("bold")
            else:
                celda.set_facecolor("#f7fafd" if fila % 2 == 0 else "white")
                celda.get_text().set_color("#142433")
        pdf.savefig(fig, facecolor="white")
        plt.close(fig)

    def xlsx(
        self,
        *,
        titulo: str,
        columnas: list[str],
        filas: list[list],
    ) -> bytes:
        libro = Workbook()
        hoja = libro.active
        hoja.title = titulo[:31] or "Reporte"
        hoja.append(columnas)
        for celda in hoja[1]:
            celda.font = Font(bold=True, color="FFFFFF")
            celda.fill = PatternFill("solid", fgColor="0B1A2C")
            celda.alignment = Alignment(horizontal="center", vertical="center")
        for fila in filas:
            hoja.append(fila)
        hoja.freeze_panes = "A2"
        hoja.auto_filter.ref = hoja.dimensions
        for indice, columna in enumerate(columnas, start=1):
            letra = get_column_letter(indice)
            ancho = max(
                [len(str(columna))]
                + [len(str(fila[indice - 1])) for fila in filas if indice - 1 < len(fila)]
            )
            hoja.column_dimensions[letra].width = min(max(ancho + 2, 10), 42)
        buffer = io.BytesIO()
        libro.save(buffer)
        return buffer.getvalue()
