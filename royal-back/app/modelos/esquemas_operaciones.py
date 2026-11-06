"""DTOs de maestros, recepción y preparación de pedidos."""
from __future__ import annotations

from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel, Field

TipoCliente = Literal["MINORISTA", "MAYORISTA", "FARMACIA", "RESTAURANTE", "CORPORATIVO", "HOSPITAL"]
Zona = Literal["NORTE", "SUR", "ORIENTE", "PONIENTE"]
TipoZona = Literal["GENERAL", "DEVOLUCIONES", "DANADOS", "BLOQUEADO", "RESERVADO"]
Condicion = Literal["BUENO", "DANADO", "INCOMPLETO"]
Prioridad = Literal["NORMAL", "ALTA"]
Rol = Literal["admin", "operador", "auditor"]


# ---------------------------------------------------------------------------
# Maestros
# ---------------------------------------------------------------------------
class ClienteIn(BaseModel):
    codigo: str = Field(min_length=2, max_length=30)
    nombre: str = Field(min_length=2, max_length=150)
    tipo_cliente: TipoCliente
    zona: Zona
    direccion: str = Field(min_length=3)
    colonia: str | None = Field(default=None, max_length=100)
    telefono: str | None = Field(default=None, max_length=30)
    contacto: str | None = Field(default=None, max_length=120)
    latitud: float = Field(ge=-90, le=90)
    longitud: float = Field(ge=-180, le=180)


class ClienteActualizar(BaseModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=150)
    tipo_cliente: TipoCliente | None = None
    zona: Zona | None = None
    direccion: str | None = Field(default=None, min_length=3)
    colonia: str | None = Field(default=None, max_length=100)
    telefono: str | None = Field(default=None, max_length=30)
    contacto: str | None = Field(default=None, max_length=120)
    latitud: float | None = Field(default=None, ge=-90, le=90)
    longitud: float | None = Field(default=None, ge=-180, le=180)
    activo: bool | None = None


class ClienteOut(BaseModel):
    id: int
    codigo: str
    nombre: str
    tipo_cliente: str
    zona: str
    direccion: str
    colonia: str | None = None
    telefono: str | None = None
    contacto: str | None = None
    latitud: float
    longitud: float
    activo: bool


class ProductoIn(BaseModel):
    sku: str = Field(min_length=2, max_length=50)
    nombre: str = Field(min_length=2, max_length=150)
    stock_minimo: int = Field(default=5, ge=0)
    peso_kg: float = Field(gt=0)
    volumen_m3: float = Field(gt=0)


class ProductoActualizar(BaseModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=150)
    stock_minimo: int | None = Field(default=None, ge=0)
    peso_kg: float | None = Field(default=None, gt=0)
    volumen_m3: float | None = Field(default=None, gt=0)
    activo: bool | None = None


class ProductoMaestroOut(BaseModel):
    id: int
    sku: str
    nombre: str
    stock_minimo: int
    peso_kg: float
    volumen_m3: float
    activo: bool
    stock_total: int = 0


class UbicacionIn(BaseModel):
    codigo: str = Field(min_length=2, max_length=30)
    pasillo: str = Field(min_length=1, max_length=10)
    rack: str = Field(min_length=1, max_length=10)
    nivel: int = Field(ge=1, le=99)
    orden_picking: int = Field(ge=0)
    tipo_zona: TipoZona = "GENERAL"


class UbicacionActualizar(BaseModel):
    pasillo: str | None = Field(default=None, min_length=1, max_length=10)
    rack: str | None = Field(default=None, min_length=1, max_length=10)
    nivel: int | None = Field(default=None, ge=1, le=99)
    orden_picking: int | None = Field(default=None, ge=0)
    tipo_zona: TipoZona | None = None
    activo: bool | None = None


class UbicacionMaestroOut(BaseModel):
    id: int
    codigo: str
    pasillo: str
    rack: str
    nivel: int
    orden_picking: int
    tipo_zona: str
    activo: bool
    stock_total: int = 0


class LoteIn(BaseModel):
    producto_id: int
    ubicacion_id: int
    lote: str = Field(min_length=1, max_length=50)
    caducidad: date | None = None
    cantidad: int = Field(default=0, ge=0)
    condicion: Condicion = "BUENO"


class LoteActualizar(BaseModel):
    ubicacion_id: int | None = None
    caducidad: date | None = None
    cantidad: int | None = Field(default=None, ge=0)
    condicion: Condicion | None = None


class LoteOut(BaseModel):
    id: int
    producto_id: int
    producto: str
    sku: str
    ubicacion: str
    lote: str
    caducidad: date | None = None
    cantidad: int
    condicion: str


class ProveedorIn(BaseModel):
    codigo: str = Field(min_length=2, max_length=30)
    nombre: str = Field(min_length=2, max_length=150)
    contacto: str | None = Field(default=None, max_length=120)
    telefono: str | None = Field(default=None, max_length=30)
    correo: str | None = Field(default=None, max_length=160)


class ProveedorActualizar(BaseModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=150)
    contacto: str | None = Field(default=None, max_length=120)
    telefono: str | None = Field(default=None, max_length=30)
    correo: str | None = Field(default=None, max_length=160)
    activo: bool | None = None


class ProveedorOut(BaseModel):
    id: int
    codigo: str
    nombre: str
    contacto: str | None = None
    telefono: str | None = None
    correo: str | None = None
    activo: bool


# ---------------------------------------------------------------------------
# Pedidos
# ---------------------------------------------------------------------------
class PedidoLineaIn(BaseModel):
    producto_id: int
    cantidad: int = Field(gt=0, le=100000)


class PedidoIn(BaseModel):
    cliente_id: int
    prioridad: Prioridad = "NORMAL"
    fecha_compromiso: date | None = None
    observaciones: str | None = Field(default=None, max_length=1000)
    lineas: list[PedidoLineaIn] = Field(min_length=1)


class PedidoActualizar(BaseModel):
    cliente_id: int | None = None
    prioridad: Prioridad | None = None
    fecha_compromiso: date | None = None
    observaciones: str | None = Field(default=None, max_length=1000)
    lineas: list[PedidoLineaIn] | None = None


class PedidoLineaOut(BaseModel):
    id: int
    producto_id: int
    producto: str
    sku: str
    cantidad: int
    peso_kg: float
    volumen_m3: float


class PedidoResumenOut(BaseModel):
    id: int
    folio: str
    cliente_id: int
    cliente: str
    cliente_codigo: str
    estado: str
    prioridad: str
    fecha_pedido: date
    fecha_compromiso: date | None = None
    peso_kg: float
    volumen_m3: float
    num_lineas: int
    num_bultos: int
    observaciones: str | None = None


class PedidoDetalleOut(PedidoResumenOut):
    lineas: list[PedidoLineaOut] = []


# ---------------------------------------------------------------------------
# Recepción
# ---------------------------------------------------------------------------
class OCLineaIn(BaseModel):
    producto_id: int
    cantidad_solicitada: int = Field(gt=0, le=100000)


class OCIn(BaseModel):
    proveedor_id: int
    fecha_esperada: date
    hora_estimada: time | None = None
    anden: str | None = Field(default=None, max_length=20)
    observaciones: str | None = Field(default=None, max_length=1000)
    lineas: list[OCLineaIn] = Field(min_length=1)


class OCLineaOut(BaseModel):
    id: int
    producto_id: int
    producto: str
    sku: str
    cantidad_solicitada: int
    cantidad_recibida: int


class OCOut(BaseModel):
    id: int
    folio: str
    proveedor: str
    proveedor_id: int
    estado: str
    fecha_esperada: date
    hora_estimada: time | None = None
    anden: str | None = None
    observaciones: str | None = None
    total_solicitado: int
    total_recibido: int
    lineas: list[OCLineaOut] = []


class RecepcionLineaIn(BaseModel):
    linea_id: int
    cantidad_recibida: int = Field(gt=0, le=100000)
    lote: str | None = Field(default=None, max_length=50)
    caducidad: date | None = None
    condicion: Condicion = "BUENO"
    ubicacion_id: int


class IncidenciaRecepcionIn(BaseModel):
    descripcion: str = Field(min_length=3, max_length=500)
    producto_id: int | None = None
    comentario: str | None = Field(default=None, max_length=1000)
    foto_base64: str | None = None


class RecepcionIn(BaseModel):
    observaciones: str | None = Field(default=None, max_length=1000)
    lineas: list[RecepcionLineaIn] = Field(min_length=1)
    incidencia: IncidenciaRecepcionIn | None = None


class RecepcionLineaOut(BaseModel):
    producto: str
    sku: str
    ubicacion: str
    lote: str | None = None
    caducidad: date | None = None
    condicion: str
    cantidad_recibida: int


class RecepcionOut(BaseModel):
    id: int
    orden_folio: str
    proveedor: str
    recibido_por: str
    fecha: datetime
    observaciones: str | None = None
    lineas: list[RecepcionLineaOut] = []


class IncidenciaOut(BaseModel):
    id: int
    orden_folio: str
    proveedor: str
    producto: str | None = None
    descripcion: str
    foto_url: str | None = None
    responsable: str | None = None
    comentario: str | None = None
    fecha: datetime


# ---------------------------------------------------------------------------
# Picking / packing
# ---------------------------------------------------------------------------
class PickingTareaOut(BaseModel):
    id: int
    pedido_id: int
    producto: str
    sku: str
    ubicacion: str
    cantidad: int
    cantidad_picada: int
    estado: str
    orden: int


class ConfirmarTareaIn(BaseModel):
    sku: str | None = Field(default=None, max_length=50)
    ubicacion: str | None = Field(default=None, max_length=30)


class BultoOut(BaseModel):
    id: int
    guia: str
    descripcion: str
    peso_kg: float
    volumen_m3: float
    estado: str


class EmpaqueOut(BaseModel):
    id: int
    folio: str
    estado: str
    peso_kg: float
    volumen_m3: float
    validado_por: str | None = None
    creado_en: datetime
    bultos: list[BultoOut] = []


class PickingPedidoOut(BaseModel):
    id: int
    folio: str
    cliente: str
    cliente_codigo: str
    direccion: str
    telefono: str | None = None
    estado: str
    prioridad: str
    fecha_compromiso: date | None = None
    peso_kg: float
    volumen_m3: float
    lineas: list[PedidoLineaOut] = []
    tareas: list[PickingTareaOut] = []
    bultos: list[BultoOut] = []
    empaque: EmpaqueOut | None = None


class OlaOut(BaseModel):
    id: int
    folio: str
    fecha: date
    estado: str
    pedidos: int
    tareas: int
    mensaje: str


# ---------------------------------------------------------------------------
# Inventario extendido / flota / usuarios
# ---------------------------------------------------------------------------
class TrasladoIn(BaseModel):
    producto_id: int
    cantidad: int = Field(gt=0, le=100000)
    ubicacion_origen_id: int
    ubicacion_destino_id: int
    comentario: str | None = Field(default=None, max_length=500)


class TrasladoOut(BaseModel):
    id: int
    producto: str
    cantidad: int
    origen: str
    destino: str
    usuario: str | None = None
    comentario: str | None = None
    fecha: datetime


class VehiculoActualizar(BaseModel):
    modelo: str | None = Field(default=None, min_length=2, max_length=80)
    capacidad_kg: float | None = Field(default=None, gt=0)
    capacidad_m3: float | None = Field(default=None, gt=0)
    activo: bool | None = None


class ConductorActualizar(BaseModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=120)
    telefono: str | None = Field(default=None, max_length=30)
    licencia: str | None = Field(default=None, min_length=3, max_length=40)
    activo: bool | None = None


class UsuarioActualizar(BaseModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=120)
    correo: str | None = Field(default=None, max_length=160)
    rol: Rol | None = None
    puesto: str | None = Field(default=None, max_length=40)
    contrasena: str | None = Field(default=None, min_length=8, max_length=200)
