"""DTOs de entrada/salida de la API."""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Autenticación y usuarios
# ---------------------------------------------------------------------------
class LoginIn(BaseModel):
    usuario: str = Field(min_length=1, max_length=40)
    contrasena: str = Field(min_length=1, max_length=200)


class UsuarioOut(BaseModel):
    id: int
    nombre: str
    usuario: str
    correo: str | None = None
    rol: str
    puesto: str
    activo: bool


class TokenOut(BaseModel):
    token: str
    tipo: str = "bearer"
    usuario: UsuarioOut


class UsuarioCrearIn(BaseModel):
    nombre: str = Field(min_length=2, max_length=120)
    usuario: str = Field(min_length=3, max_length=40, pattern=r"^[a-zA-Z0-9._-]+$")
    correo: str | None = Field(default=None, max_length=160)
    contrasena: str = Field(min_length=8, max_length=200)
    rol: Literal["admin", "operador", "auditor"]
    puesto: str = Field(default="Administración", max_length=40)


class UsuarioEstadoIn(BaseModel):
    activo: bool


# ---------------------------------------------------------------------------
# Rutas y reparto
# ---------------------------------------------------------------------------
class VehiculoOut(BaseModel):
    id: int
    placas: str
    modelo: str
    capacidad_kg: float
    capacidad_m3: float
    activo: bool = True


class ConductorOut(BaseModel):
    id: int
    nombre: str
    telefono: str | None = None
    licencia: str | None = None
    activo: bool = True


class BultoOut(BaseModel):
    id: int
    guia: str
    descripcion: str
    peso_kg: float
    volumen_m3: float
    estado: str


class EntregaOut(BaseModel):
    id: int
    resultado: str
    recibio_nombre: str | None = None
    motivo_fallo: str | None = None
    comentario: str | None = None
    reprogramado_para: date | None = None
    firma_url: str | None = None
    foto_url: str | None = None
    registrado_en: datetime


class ParadaOut(BaseModel):
    id: int
    secuencia: int
    estado: str
    pedido_id: int
    pedido_folio: str
    cliente_id: int
    cliente: str
    cliente_codigo: str
    tipo_cliente: str
    direccion: str
    telefono: str | None = None
    latitud: float
    longitud: float
    distancia_km: float
    eta_min: float
    bultos: list[BultoOut] = []
    entrega: EntregaOut | None = None


class RutaResumenOut(BaseModel):
    id: int
    folio: str
    zona: str
    fecha: date
    estado: str
    vehiculo: VehiculoOut
    conductor: ConductorOut
    num_paradas: int
    num_bultos: int
    peso_total_kg: float
    volumen_total_m3: float
    tipo_principal: str | None = None
    distancia_km: float
    distancia_base_km: float
    ahorro_pct: float
    eta_min: float
    salida_en: datetime | None = None
    cierre_en: datetime | None = None
    mapa_url: str


class RutaDetalleOut(RutaResumenOut):
    paradas: list[ParadaOut] = []


class PlanGeneradoOut(BaseModel):
    generado: bool
    mensaje: str
    fecha: date | None = None
    total_pedidos: int = 0
    total_bultos: int = 0
    total_viajes: int = 0
    distancia_total_km: float = 0
    distancia_base_total_km: float = 0
    ahorro_global_pct: float = 0
    viajes: list[RutaResumenOut] = []


class DespachoIn(BaseModel):
    guias: list[str] = Field(default_factory=list, max_length=500)


class DespachoOut(BaseModel):
    estado: str
    mensaje: str
    total_bultos: int
    faltantes: list[str] = Field(default_factory=list)
    ajenas: list[str] = Field(default_factory=list)


class EntregaIn(BaseModel):
    resultado: Literal["ENTREGADO", "FALLIDO"]
    recibio_nombre: str | None = Field(default=None, max_length=150)
    firma_base64: str | None = None
    foto_base64: str | None = None
    motivo_fallo: Literal["CLIENTE_CERRADO", "DIRECCION_INCORRECTA", "RECHAZO", "OTRO"] | None = None
    comentario: str | None = Field(default=None, max_length=1000)
    reprogramado_para: date | None = None


class EntregaRegistradaOut(BaseModel):
    mensaje: str
    ruta: RutaDetalleOut


# ---------------------------------------------------------------------------
# Rastreo
# ---------------------------------------------------------------------------
class EventoRastreoOut(BaseModel):
    estado: str
    descripcion: str
    ubicacion: str | None = None
    usuario: str | None = None
    guia: str | None = None
    fecha: datetime


class RastreoOut(BaseModel):
    guia: str
    descripcion: str
    estado: str
    peso_kg: float
    volumen_m3: float
    pedido_folio: str
    pedido_estado: str
    fecha_compromiso: date | None = None
    cliente: str
    tipo_cliente: str
    zona: str
    direccion: str
    telefono: str | None = None
    ruta_folio: str | None = None
    ruta_estado: str | None = None
    eventos: list[EventoRastreoOut] = []


class RastreoRecienteOut(BaseModel):
    guia: str
    cliente: str
    estado: str
    pedido_folio: str
    fecha: datetime


# ---------------------------------------------------------------------------
# Panel, inventario, flota, auditoría
# ---------------------------------------------------------------------------
class ProductividadOut(BaseModel):
    operador: str
    tareas: int
    lineas: int


class PanelOut(BaseModel):
    rutas_hoy: int
    rutas_en_ruta: int
    pedidos_pendientes: int
    entregas_hoy: int
    fallidas_hoy: int
    bultos_en_ruta: int
    stock_bajo: int
    ocupacion_pct: float
    distancia_hoy_km: float
    pedidos_en_picking: int
    pedidos_en_empaque: int
    tareas_picking_pendientes: int
    recepciones_hoy: int
    incidencias_hoy: int
    mermas_hoy: int
    productos_estancados: int
    productividad_hoy: list[ProductividadOut] = []
    rutas_recientes: list[RutaResumenOut] = []
    eventos_recientes: list[EventoRastreoOut] = []


class ProductoOut(BaseModel):
    id: int
    sku: str
    nombre: str
    peso_kg: float
    volumen_m3: float
    stock_minimo: int


class UbicacionOut(BaseModel):
    id: int
    codigo: str
    pasillo: str
    rack: str
    nivel: int


class CatalogoOut(BaseModel):
    productos: list[ProductoOut]
    ubicaciones: list[UbicacionOut]


class StockOut(BaseModel):
    producto_id: int
    sku: str
    nombre: str
    stock_total: int
    stock_minimo: int
    bajo_minimo: bool
    numero_ubicaciones: int
    proximo_vencimiento: date | None = None


class MovimientoIn(BaseModel):
    producto_id: int
    ubicacion_id: int
    tipo: Literal["ENTRADA", "SALIDA"]
    cantidad: int = Field(gt=0, le=100000)


class MovimientoOut(BaseModel):
    id: int
    producto: str
    sku: str
    ubicacion: str
    tipo: str
    cantidad: int
    usuario: str | None = None
    fecha: datetime


class FlotaOut(BaseModel):
    vehiculos: list[VehiculoOut]
    conductores: list[ConductorOut]
    historial: list[RutaResumenOut] = []


class VehiculoCrearIn(BaseModel):
    placas: str = Field(min_length=3, max_length=20)
    modelo: str = Field(min_length=2, max_length=80)
    capacidad_kg: float = Field(gt=0)
    capacidad_m3: float = Field(gt=0)


class ConductorCrearIn(BaseModel):
    nombre: str = Field(min_length=2, max_length=120)
    telefono: str | None = Field(default=None, max_length=30)
    licencia: str = Field(min_length=3, max_length=40)


class BitacoraOut(BaseModel):
    id: int
    usuario: str
    rol: str
    accion: str
    entidad: str | None = None
    entidad_id: str | None = None
    detalle: dict = {}
    fecha: datetime


class ConteoIn(BaseModel):
    ubicacion_id: int
    producto_id: int
    cantidad_fisica: int = Field(ge=0, le=1000000)


class ConteoOut(BaseModel):
    id: int
    ubicacion: str
    producto: str
    cantidad_sistema: int
    cantidad_fisica: int
    diferencia: int
    auditor: str
    fecha: datetime


class RotacionOut(BaseModel):
    sku: str
    nombre: str
    total_salidas: int
    total_entradas: int
