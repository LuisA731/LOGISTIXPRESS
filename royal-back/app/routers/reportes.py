"""Exportación de reportes PDF y XLSX."""
from __future__ import annotations

from datetime import date, datetime
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from ..dependencias import obtener_bd
from ..repositorios.auditoria import RepositorioAuditoria
from ..repositorios.inventario import RepositorioInventario
from ..repositorios.logistica import RepositorioRutas
from ..repositorios.usuarios import RepositorioUsuarios
from ..seguridad import UsuarioSesion, usuario_actual
from ..servicios.reportes import GeneradorReportes

router = APIRouter(prefix="/reportes", tags=["Reportes"])

_PERMISOS = {
    "inventario": {"admin", "operador", "auditor"},
    "movimientos": {"admin", "operador", "auditor"},
    "rutas": {"admin", "operador"},
    "entregas": {"admin", "operador"},
    "auditoria": {"admin", "auditor"},
    "rotacion": {"admin", "auditor"},
    "usuarios": {"admin"},
}


def _texto(valor) -> str:
    if valor is None:
        return ""
    if isinstance(valor, datetime):
        return valor.strftime("%d/%m/%Y %H:%M")
    if isinstance(valor, date):
        return valor.strftime("%d/%m/%Y")
    return str(valor)


@router.get(
    "/exportar",
    summary="Exportar reporte en PDF o XLSX",
    response_class=Response,
)
def exportar(
    tipo: str = Query(description="inventario, movimientos, rutas, entregas, auditoria, rotacion, usuarios"),
    formato: str = Query(default="pdf", pattern="^(pdf|xlsx)$"),
    desde: date | None = Query(default=None),
    hasta: date | None = Query(default=None),
    usuario: UsuarioSesion = Depends(usuario_actual),
) -> Response:
    tipo = tipo.lower().strip()
    if tipo not in _PERMISOS:
        raise HTTPException(status_code=404, detail="Tipo de reporte desconocido.")
    if usuario.rol not in _PERMISOS[tipo]:
        raise HTTPException(
            status_code=403,
            detail="Tu rol no tiene permiso para exportar este reporte.",
        )
    if desde and hasta and desde > hasta:
        raise HTTPException(
            status_code=400, detail="La fecha inicial no puede ser mayor que la final."
        )

    bd = obtener_bd()
    titulo = ""
    subtitulo = ""
    columnas: list[str] = []
    filas: list[list] = []

    if tipo == "inventario":
        titulo = "Inventario por producto"
        subtitulo = "Existencias, mínimo y número de ubicaciones"
        columnas = ["SKU", "Producto", "Stock", "Mínimo", "Ubicaciones", "Próximo vencimiento"]
        for fila in RepositorioInventario(bd, usuario.rol_bd).stock():
            filas.append([
                fila["sku"], fila["nombre"], fila["stock_total"], fila["stock_minimo"],
                fila["numero_ubicaciones"], _texto(fila["proximo_vencimiento"]),
            ])

    elif tipo == "movimientos":
        titulo = "Historial de movimientos por producto"
        subtitulo = "Entradas y salidas de almacén con usuario responsable"
        columnas = ["Fecha", "Producto", "SKU", "Ubicación", "Tipo", "Cantidad", "Usuario"]
        for movimiento in RepositorioInventario(bd, usuario.rol_bd).movimientos(5000):
            fecha_movimiento = movimiento["fecha"].date()
            if desde and fecha_movimiento < desde:
                continue
            if hasta and fecha_movimiento > hasta:
                continue
            filas.append([
                _texto(movimiento["fecha"]), movimiento["producto"], movimiento["sku"],
                movimiento["ubicacion"], movimiento["tipo"], movimiento["cantidad"],
                movimiento["usuario"] or "",
            ])

    elif tipo == "rutas":
        titulo = "Rutas y desempeño de reparto"
        subtitulo = "Planificación, distancia y ahorro contra el orden de carga"
        columnas = [
            "Folio", "Fecha", "Zona", "Estado", "Vehículo", "Conductor",
            "Paradas", "Bultos", "Peso kg", "Distancia km", "Ahorro %", "ETA min",
        ]
        for r in RepositorioRutas(bd, usuario.rol_bd).listar_rutas(limite=300):
            if desde and r["fecha"] < desde:
                continue
            if hasta and r["fecha"] > hasta:
                continue
            filas.append([
                r["folio"], _texto(r["fecha"]), r["zona"], r["estado"],
                r["vehiculo"]["placas"], r["conductor"]["nombre"], r["num_paradas"],
                r["num_bultos"], f"{r['peso_total_kg']:.1f}",
                f"{r['distancia_km']:.1f}", f"{r['ahorro_pct']:.1f}",
                f"{r['eta_min']:.0f}",
            ])
        subtitulo += " · todas las rutas" if not desde and not hasta else " · periodo filtrado"

    elif tipo == "entregas":
        titulo = "Entregas y evidencias"
        subtitulo = "Resultados, motivo de falla y reprogramación"
        columnas = [
            "Ruta", "Fecha", "Cliente", "Zona", "Pedido", "Resultado",
            "Recibió", "Motivo falla", "Reprogramada", "Registrada",
        ]
        for e in RepositorioRutas(bd, usuario.rol_bd).reporte_entregas(desde, hasta):
            filas.append([
                e["ruta"], _texto(e["fecha"]), e["cliente"], e["zona"], e["pedido"],
                e["resultado"], e["recibio_nombre"] or "", e["motivo_fallo"] or "",
                _texto(e["reprogramado_para"]), _texto(e["registrado_en"]),
            ])

    elif tipo == "auditoria":
        titulo = "Bitácora de actividades"
        subtitulo = "Acciones registradas por usuario y rol"
        columnas = ["Fecha", "Usuario", "Rol", "Acción", "Entidad", "ID", "Detalle"]
        for b in RepositorioAuditoria(bd, usuario.rol_bd).bitacora(
            limite=500, desde=desde, hasta=hasta
        ):
            detalle = b["detalle"] or {}
            filas.append([
                _texto(b["fecha"]), b["usuario"], b["rol"], b["accion"],
                b["entidad"] or "", b["entidad_id"] or "",
                "; ".join(f"{k}: {v}" for k, v in detalle.items())[:180],
            ])

    elif tipo == "rotacion":
        titulo = "Métricas de rotación"
        subtitulo = "Entradas y salidas acumuladas por producto"
        columnas = ["SKU", "Producto", "Total salidas", "Total entradas"]
        for r in RepositorioAuditoria(bd, usuario.rol_bd).rotacion(300):
            filas.append([r["sku"], r["nombre"], r["total_salidas"], r["total_entradas"]])

    elif tipo == "usuarios":
        titulo = "Usuarios del sistema"
        subtitulo = "Cuentas, rol y estado"
        columnas = ["Nombre", "Usuario", "Correo", "Rol", "Activo"]
        for u in RepositorioUsuarios(bd).listar(usuario.rol_bd):
            filas.append([
                u["nombre"], u["usuario"], u["correo"] or "", u["rol"],
                "Sí" if u["activo"] else "No",
            ])

    generador = GeneradorReportes()
    if formato == "pdf":
        contenido = generador.pdf(
            titulo=titulo, subtitulo=subtitulo, columnas=columnas,
            filas=filas, usuario=usuario.nombre, rol=usuario.rol,
        )
        media_type = "application/pdf"
    else:
        contenido = generador.xlsx(titulo=titulo, columnas=columnas, filas=filas)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    nombre = f"reporte_{tipo}_{date.today():%Y%m%d}.{formato}"
    return Response(
        content=contenido,
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename={nombre}; "
                                   f"filename*=UTF-8''{quote(nombre)}",
        },
    )
