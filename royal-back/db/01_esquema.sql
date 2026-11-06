-- ============================================================================
-- LogistiXpress · Esquema operativo v2
-- Mantiene el modelo aprobado de almacén y agrega el dominio de reparto:
-- clientes, pedidos, bultos, rutas, paradas, evidencias y rastreo.
-- ============================================================================
BEGIN;

CREATE SCHEMA IF NOT EXISTS seguridad;
CREATE SCHEMA IF NOT EXISTS almacen;
CREATE SCHEMA IF NOT EXISTS operaciones;
CREATE SCHEMA IF NOT EXISTS auditoria;

-- ----------------------------------------------------------------------------
-- 1. SEGURIDAD, USUARIOS Y BITÁCORA
-- ----------------------------------------------------------------------------
CREATE TABLE seguridad.usuarios (
    id            SERIAL PRIMARY KEY,
    nombre        VARCHAR(120) NOT NULL,
    usuario       VARCHAR(40)  UNIQUE NOT NULL,
    correo        VARCHAR(160) UNIQUE,
    password_hash TEXT NOT NULL,
    rol           VARCHAR(20) NOT NULL CHECK (rol IN ('admin', 'operador', 'auditor')),
    puesto        VARCHAR(40) NOT NULL DEFAULT 'Administración'
                  CHECK (puesto IN ('Auxiliar de almacén', 'Montacarguista',
                                    'Surtidor', 'Empacador', 'Chofer',
                                    'Supervisor', 'Administración',
                                    'Dirección', 'Auditoría')),
    activo        BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en     TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE seguridad.bitacora (
    id             BIGSERIAL PRIMARY KEY,
    usuario_id     INT REFERENCES seguridad.usuarios(id),
    usuario_nombre VARCHAR(120) NOT NULL,
    rol            VARCHAR(20) NOT NULL,
    accion         VARCHAR(80) NOT NULL,
    entidad        VARCHAR(60),
    entidad_id     TEXT,
    detalle        JSONB NOT NULL DEFAULT '{}'::jsonb,
    fecha          TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_bitacora_fecha ON seguridad.bitacora (fecha DESC);
CREATE INDEX idx_bitacora_accion ON seguridad.bitacora (accion);

-- ----------------------------------------------------------------------------
-- 2. ALMACÉN (modelo aprobado + atributos físicos para consolidar viajes)
-- ----------------------------------------------------------------------------
CREATE TABLE almacen.ubicaciones (
    id            SERIAL PRIMARY KEY,
    codigo        VARCHAR(30) UNIQUE NOT NULL,
    pasillo       VARCHAR(10) NOT NULL,
    rack          VARCHAR(10) NOT NULL,
    nivel         INT NOT NULL,
    orden_picking INT NOT NULL,
    tipo_zona     VARCHAR(20) NOT NULL DEFAULT 'GENERAL'
                  CHECK (tipo_zona IN ('GENERAL', 'DEVOLUCIONES', 'DANADOS',
                                       'BLOQUEADO', 'RESERVADO')),
    activo        BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE almacen.productos (
    id           SERIAL PRIMARY KEY,
    sku          VARCHAR(50) UNIQUE NOT NULL,
    nombre       VARCHAR(150) NOT NULL,
    stock_minimo INT NOT NULL DEFAULT 5,
    peso_kg      NUMERIC(10,3) NOT NULL DEFAULT 1.000,
    volumen_m3   NUMERIC(10,4) NOT NULL DEFAULT 0.0010,
    activo       BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE almacen.stock (
    id           SERIAL PRIMARY KEY,
    producto_id  INT NOT NULL REFERENCES almacen.productos(id),
    ubicacion_id INT NOT NULL REFERENCES almacen.ubicaciones(id),
    cantidad     INT NOT NULL DEFAULT 0 CHECK (cantidad >= 0),
    CONSTRAINT uq_prod_ubic UNIQUE (producto_id, ubicacion_id)
);

CREATE TABLE almacen.lotes (
    id           SERIAL PRIMARY KEY,
    producto_id  INT NOT NULL REFERENCES almacen.productos(id),
    ubicacion_id INT NOT NULL REFERENCES almacen.ubicaciones(id),
    lote         VARCHAR(50) NOT NULL,
    caducidad    DATE,
    cantidad     INT NOT NULL CHECK (cantidad >= 0),
    condicion    VARCHAR(20) NOT NULL DEFAULT 'BUENO'
                 CHECK (condicion IN ('BUENO', 'DANADO', 'INCOMPLETO')),
    creado_en    TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (producto_id, lote)
);

CREATE TABLE almacen.movimientos (
    id           SERIAL PRIMARY KEY,
    producto_id  INT NOT NULL REFERENCES almacen.productos(id),
    ubicacion_id INT NOT NULL REFERENCES almacen.ubicaciones(id),
    tipo         VARCHAR(10) NOT NULL CHECK (tipo IN ('ENTRADA', 'SALIDA')),
    cantidad     INT NOT NULL CHECK (cantidad > 0),
    usuario_id   INT REFERENCES seguridad.usuarios(id),
    fecha        TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_movimientos_fecha ON almacen.movimientos (fecha DESC);
CREATE INDEX idx_stock_producto ON almacen.stock (producto_id);

CREATE TABLE almacen.traslados (
    id                  SERIAL PRIMARY KEY,
    producto_id         INT NOT NULL REFERENCES almacen.productos(id),
    cantidad            INT NOT NULL CHECK (cantidad > 0),
    ubicacion_origen_id INT NOT NULL REFERENCES almacen.ubicaciones(id),
    ubicacion_destino_id INT NOT NULL REFERENCES almacen.ubicaciones(id),
    usuario_id          INT REFERENCES seguridad.usuarios(id),
    comentario          TEXT,
    fecha               TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (ubicacion_origen_id <> ubicacion_destino_id)
);

-- ----------------------------------------------------------------------------
-- 3. CLIENTES, PEDIDOS, BULTOS Y FLOTA
-- ----------------------------------------------------------------------------
CREATE TABLE operaciones.clientes (
    id           SERIAL PRIMARY KEY,
    codigo       VARCHAR(30) UNIQUE NOT NULL,
    nombre       VARCHAR(150) NOT NULL,
    tipo_cliente VARCHAR(20) NOT NULL
                 CHECK (tipo_cliente IN ('MINORISTA', 'MAYORISTA', 'FARMACIA',
                                         'RESTAURANTE', 'CORPORATIVO', 'HOSPITAL')),
    zona         VARCHAR(20) NOT NULL
                 CHECK (zona IN ('NORTE', 'SUR', 'ORIENTE', 'PONIENTE')),
    direccion    TEXT NOT NULL,
    colonia      VARCHAR(100),
    telefono     VARCHAR(30),
    contacto     VARCHAR(120),
    latitud      NUMERIC(9,6) NOT NULL,
    longitud     NUMERIC(9,6) NOT NULL,
    activo       BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE operaciones.proveedores (
    id        SERIAL PRIMARY KEY,
    codigo    VARCHAR(30) UNIQUE NOT NULL,
    nombre    VARCHAR(150) NOT NULL,
    contacto  VARCHAR(120),
    telefono  VARCHAR(30),
    correo    VARCHAR(160),
    activo    BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE SEQUENCE operaciones.folio_oc_seq AS INTEGER START WITH 1000;

CREATE TABLE operaciones.ordenes_compra (
    id             SERIAL PRIMARY KEY,
    folio          VARCHAR(40) UNIQUE NOT NULL,
    proveedor_id   INT NOT NULL REFERENCES operaciones.proveedores(id),
    estado         VARCHAR(20) NOT NULL DEFAULT 'PROGRAMADA'
                   CHECK (estado IN ('PROGRAMADA', 'EN_RECEPCION', 'RECIBIDA',
                                     'CON_INCIDENCIA', 'CANCELADA')),
    fecha_esperada DATE NOT NULL DEFAULT CURRENT_DATE,
    hora_estimada  TIME,
    anden          VARCHAR(20),
    observaciones  TEXT,
    creado_por     INT REFERENCES seguridad.usuarios(id),
    creado_en      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    recibido_en    TIMESTAMPTZ
);

CREATE INDEX idx_ordenes_compra_fecha ON operaciones.ordenes_compra (fecha_esperada, hora_estimada);

CREATE TABLE operaciones.orden_compra_lineas (
    id                 SERIAL PRIMARY KEY,
    orden_compra_id    INT NOT NULL REFERENCES operaciones.ordenes_compra(id) ON DELETE CASCADE,
    producto_id        INT NOT NULL REFERENCES almacen.productos(id),
    cantidad_solicitada INT NOT NULL CHECK (cantidad_solicitada > 0),
    cantidad_recibida  INT NOT NULL DEFAULT 0 CHECK (cantidad_recibida >= 0),
    UNIQUE (orden_compra_id, producto_id)
);

CREATE TABLE operaciones.recepciones (
    id              SERIAL PRIMARY KEY,
    orden_compra_id INT NOT NULL REFERENCES operaciones.ordenes_compra(id),
    recibido_por    INT REFERENCES seguridad.usuarios(id),
    observaciones   TEXT,
    fecha           TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE operaciones.recepcion_lineas (
    id                   SERIAL PRIMARY KEY,
    recepcion_id         INT NOT NULL REFERENCES operaciones.recepciones(id) ON DELETE CASCADE,
    orden_compra_linea_id INT NOT NULL REFERENCES operaciones.orden_compra_lineas(id),
    producto_id          INT NOT NULL REFERENCES almacen.productos(id),
    ubicacion_id         INT NOT NULL REFERENCES almacen.ubicaciones(id),
    lote                 VARCHAR(50),
    caducidad            DATE,
    condicion            VARCHAR(20) NOT NULL DEFAULT 'BUENO'
                         CHECK (condicion IN ('BUENO', 'DANADO', 'INCOMPLETO')),
    cantidad_recibida    INT NOT NULL CHECK (cantidad_recibida > 0)
);

CREATE TABLE operaciones.incidencias_recepcion (
    id           SERIAL PRIMARY KEY,
    recepcion_id INT NOT NULL REFERENCES operaciones.recepciones(id) ON DELETE CASCADE,
    producto_id  INT REFERENCES almacen.productos(id),
    descripcion  TEXT NOT NULL,
    foto_url     TEXT,
    responsable  VARCHAR(120),
    comentario   TEXT,
    fecha        TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE operaciones.pedidos (
    id               SERIAL PRIMARY KEY,
    folio            VARCHAR(40) UNIQUE NOT NULL,
    cliente_id       INT NOT NULL REFERENCES operaciones.clientes(id),
    estado           VARCHAR(20) NOT NULL DEFAULT 'BORRADOR'
                     CHECK (estado IN ('BORRADOR', 'EN_PICKING', 'PICKING_COMPLETO',
                                       'EMPACADO', 'LISTO', 'ASIGNADO', 'EN_RUTA',
                                       'ENTREGADO', 'FALLIDO', 'REPROGRAMADO', 'CANCELADO')),
    prioridad        VARCHAR(10) NOT NULL DEFAULT 'NORMAL' CHECK (prioridad IN ('NORMAL', 'ALTA')),
    fecha_pedido     DATE NOT NULL DEFAULT CURRENT_DATE,
    fecha_compromiso DATE,
    peso_kg          NUMERIC(12,3) NOT NULL DEFAULT 0,
    volumen_m3       NUMERIC(12,4) NOT NULL DEFAULT 0,
    observaciones    TEXT,
    creado_en        TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_pedidos_estado ON operaciones.pedidos (estado);
CREATE INDEX idx_pedidos_cliente ON operaciones.pedidos (cliente_id);
CREATE SEQUENCE operaciones.folio_pedido_seq AS INTEGER START WITH 1000;

CREATE TABLE operaciones.pedido_detalle (
    id          SERIAL PRIMARY KEY,
    pedido_id   INT NOT NULL REFERENCES operaciones.pedidos(id) ON DELETE CASCADE,
    producto_id INT NOT NULL REFERENCES almacen.productos(id),
    cantidad    INT NOT NULL CHECK (cantidad > 0)
);

CREATE SEQUENCE operaciones.folio_ola_seq AS INTEGER START WITH 1000;
CREATE SEQUENCE operaciones.folio_empaque_seq AS INTEGER START WITH 5000;
CREATE SEQUENCE operaciones.folio_guia_seq AS INTEGER START WITH 10000;

CREATE TABLE operaciones.picking_olas (
    id         SERIAL PRIMARY KEY,
    folio      VARCHAR(40) UNIQUE NOT NULL,
    fecha      DATE NOT NULL DEFAULT CURRENT_DATE,
    estado     VARCHAR(20) NOT NULL DEFAULT 'ABIERTA'
               CHECK (estado IN ('ABIERTA', 'EN_PROCESO', 'COMPLETADA', 'CANCELADA')),
    creado_por INT REFERENCES seguridad.usuarios(id),
    creado_en  TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE operaciones.picking_tareas (
    id             SERIAL PRIMARY KEY,
    ola_id         INT NOT NULL REFERENCES operaciones.picking_olas(id) ON DELETE CASCADE,
    pedido_id      INT NOT NULL REFERENCES operaciones.pedidos(id) ON DELETE CASCADE,
    producto_id    INT NOT NULL REFERENCES almacen.productos(id),
    ubicacion_id   INT NOT NULL REFERENCES almacen.ubicaciones(id),
    cantidad       INT NOT NULL CHECK (cantidad > 0),
    cantidad_picada INT NOT NULL DEFAULT 0 CHECK (cantidad_picada >= 0),
    estado         VARCHAR(20) NOT NULL DEFAULT 'PENDIENTE'
                   CHECK (estado IN ('PENDIENTE', 'PICKEADO', 'FALTANTE')),
    orden          INT NOT NULL DEFAULT 1,
    completado_por INT REFERENCES seguridad.usuarios(id),
    completado_en  TIMESTAMPTZ,
    UNIQUE (ola_id, pedido_id, producto_id)
);

CREATE INDEX idx_picking_tareas_ola ON operaciones.picking_tareas (ola_id);
CREATE INDEX idx_picking_tareas_estado ON operaciones.picking_tareas (estado);

CREATE TABLE operaciones.empaques (
    id          SERIAL PRIMARY KEY,
    folio       VARCHAR(40) UNIQUE NOT NULL,
    pedido_id   INT NOT NULL REFERENCES operaciones.pedidos(id),
    estado      VARCHAR(20) NOT NULL DEFAULT 'EN_PROCESO'
                CHECK (estado IN ('EN_PROCESO', 'VALIDADO', 'RECHAZADO')),
    peso_kg     NUMERIC(12,3) NOT NULL DEFAULT 0,
    volumen_m3  NUMERIC(12,4) NOT NULL DEFAULT 0,
    usuario_id  INT REFERENCES seguridad.usuarios(id),
    validado_por INT REFERENCES seguridad.usuarios(id),
    comentario  TEXT,
    creado_en   TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    validado_en TIMESTAMPTZ
);

CREATE TABLE operaciones.bultos (
    id          SERIAL PRIMARY KEY,
    guia        VARCHAR(40) UNIQUE NOT NULL,
    pedido_id   INT NOT NULL REFERENCES operaciones.pedidos(id) ON DELETE CASCADE,
    empaque_id  INT REFERENCES operaciones.empaques(id),
    descripcion VARCHAR(200) NOT NULL,
    peso_kg     NUMERIC(12,3) NOT NULL CHECK (peso_kg > 0),
    volumen_m3  NUMERIC(12,4) NOT NULL CHECK (volumen_m3 > 0),
    estado      VARCHAR(20) NOT NULL DEFAULT 'EN_BODEGA'
                CHECK (estado IN ('EN_BODEGA', 'ASIGNADO', 'EN_RUTA',
                                  'ENTREGADO', 'FALLIDO', 'DEVUELTO')),
    creado_en   TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_bultos_pedido ON operaciones.bultos (pedido_id);
CREATE INDEX idx_bultos_estado ON operaciones.bultos (estado);

CREATE TABLE operaciones.conductores (
    id       SERIAL PRIMARY KEY,
    nombre   VARCHAR(120) NOT NULL,
    telefono VARCHAR(30),
    licencia VARCHAR(40) UNIQUE NOT NULL,
    activo   BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE operaciones.vehiculos (
    id            SERIAL PRIMARY KEY,
    placas        VARCHAR(20) UNIQUE NOT NULL,
    modelo        VARCHAR(80) NOT NULL,
    capacidad_kg  NUMERIC(10,2) NOT NULL CHECK (capacidad_kg > 0),
    capacidad_m3  NUMERIC(10,3) NOT NULL CHECK (capacidad_m3 > 0),
    activo        BOOLEAN NOT NULL DEFAULT TRUE
);

-- ----------------------------------------------------------------------------
-- 4. RUTAS, PARADAS, PAQUETES ASIGNADOS Y RASTREO
-- ----------------------------------------------------------------------------
CREATE SEQUENCE operaciones.folio_ruta_seq AS INTEGER START WITH 1000;

CREATE TABLE operaciones.rutas (
    id               SERIAL PRIMARY KEY,
    folio            VARCHAR(40) UNIQUE NOT NULL,
    zona             VARCHAR(20) NOT NULL
                     CHECK (zona IN ('NORTE', 'SUR', 'ORIENTE', 'PONIENTE')),
    fecha            DATE NOT NULL DEFAULT CURRENT_DATE,
    vehiculo_id      INT NOT NULL REFERENCES operaciones.vehiculos(id),
    conductor_id     INT NOT NULL REFERENCES operaciones.conductores(id),
    estado           VARCHAR(20) NOT NULL DEFAULT 'PLANIFICADA'
                     CHECK (estado IN ('PLANIFICADA', 'EN_RUTA', 'COMPLETADA', 'CANCELADA')),
    distancia_km     NUMERIC(10,2) NOT NULL DEFAULT 0,
    distancia_base_km NUMERIC(10,2) NOT NULL DEFAULT 0,
    ahorro_pct       NUMERIC(6,2) NOT NULL DEFAULT 0,
    eta_min          NUMERIC(8,1) NOT NULL DEFAULT 0,
    generada_por     INT REFERENCES seguridad.usuarios(id),
    generada_en      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    salida_en        TIMESTAMPTZ,
    cierre_en        TIMESTAMPTZ
);

CREATE INDEX idx_rutas_fecha ON operaciones.rutas (fecha DESC);
CREATE INDEX idx_rutas_estado ON operaciones.rutas (estado);

CREATE TABLE operaciones.ruta_paradas (
    id              SERIAL PRIMARY KEY,
    ruta_id         INT NOT NULL REFERENCES operaciones.rutas(id) ON DELETE CASCADE,
    pedido_id       INT NOT NULL REFERENCES operaciones.pedidos(id),
    cliente_id      INT NOT NULL REFERENCES operaciones.clientes(id),
    secuencia       INT NOT NULL CHECK (secuencia > 0),
    latitud         NUMERIC(9,6) NOT NULL,
    longitud        NUMERIC(9,6) NOT NULL,
    distancia_km    NUMERIC(10,2) NOT NULL DEFAULT 0,
    eta_min         NUMERIC(8,1) NOT NULL DEFAULT 0,
    estado          VARCHAR(20) NOT NULL DEFAULT 'PENDIENTE'
                    CHECK (estado IN ('PENDIENTE', 'ENTREGADO', 'FALLIDO')),
    UNIQUE (ruta_id, pedido_id),
    UNIQUE (ruta_id, secuencia)
);

CREATE TABLE operaciones.ruta_bultos (
    ruta_parada_id INT NOT NULL REFERENCES operaciones.ruta_paradas(id) ON DELETE CASCADE,
    bulto_id       INT NOT NULL REFERENCES operaciones.bultos(id),
    PRIMARY KEY (ruta_parada_id, bulto_id)
);

CREATE INDEX idx_ruta_bultos_bulto ON operaciones.ruta_bultos (bulto_id);

CREATE TABLE operaciones.eventos_rastreo (
    id          BIGSERIAL PRIMARY KEY,
    bulto_id    INT NOT NULL REFERENCES operaciones.bultos(id) ON DELETE CASCADE,
    ruta_id     INT REFERENCES operaciones.rutas(id) ON DELETE SET NULL,
    estado      VARCHAR(20) NOT NULL
                CHECK (estado IN ('RECIBIDO', 'ETIQUETADO', 'ASIGNADO', 'EN_RUTA',
                                  'ENTREGADO', 'FALLIDO', 'REPROGRAMADO', 'DEVUELTO',
                                  'CANCELADO')),
    descripcion VARCHAR(250) NOT NULL,
    ubicacion   VARCHAR(150),
    usuario_id  INT REFERENCES seguridad.usuarios(id),
    fecha       TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_eventos_bulto ON operaciones.eventos_rastreo (bulto_id, fecha DESC);
CREATE INDEX idx_eventos_fecha ON operaciones.eventos_rastreo (fecha DESC);

CREATE TABLE operaciones.entregas (
    id                SERIAL PRIMARY KEY,
    ruta_parada_id    INT NOT NULL UNIQUE REFERENCES operaciones.ruta_paradas(id) ON DELETE CASCADE,
    resultado         VARCHAR(20) NOT NULL CHECK (resultado IN ('ENTREGADO', 'FALLIDO')),
    recibio_nombre    VARCHAR(150),
    firma_url         TEXT,
    foto_url          TEXT,
    motivo_fallo      VARCHAR(30)
                      CHECK (motivo_fallo IN ('CLIENTE_CERRADO', 'DIRECCION_INCORRECTA',
                                              'RECHAZO', 'OTRO')),
    comentario        TEXT,
    reprogramado_para DATE,
    registrado_por    INT REFERENCES seguridad.usuarios(id),
    registrado_en     TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- 5. AUDITORÍA
-- ----------------------------------------------------------------------------
CREATE TABLE auditoria.conteos_ciclicos (
    id               SERIAL PRIMARY KEY,
    ubicacion_id     INT NOT NULL REFERENCES almacen.ubicaciones(id),
    producto_id      INT NOT NULL REFERENCES almacen.productos(id),
    cantidad_sistema INT NOT NULL,
    cantidad_fisica  INT NOT NULL,
    diferencia       INT GENERATED ALWAYS AS (cantidad_fisica - cantidad_sistema) STORED,
    auditor_id       INT NOT NULL REFERENCES seguridad.usuarios(id),
    fecha            TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- 6. TRIGGER DE INVENTARIO EN TIEMPO REAL
-- SECURITY DEFINER: el operador puede insertar movimientos sin tener UPDATE
-- directo sobre almacen.stock.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION almacen.fn_actualizar_stock_tiempo_real()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = almacen, pg_temp
AS $$
BEGIN
    IF NEW.tipo = 'ENTRADA' THEN
        INSERT INTO almacen.stock (producto_id, ubicacion_id, cantidad)
        VALUES (NEW.producto_id, NEW.ubicacion_id, NEW.cantidad)
        ON CONFLICT (producto_id, ubicacion_id)
        DO UPDATE SET cantidad = almacen.stock.cantidad + EXCLUDED.cantidad;

    ELSIF NEW.tipo = 'SALIDA' THEN
        UPDATE almacen.stock
        SET cantidad = cantidad - NEW.cantidad
        WHERE producto_id = NEW.producto_id
          AND ubicacion_id = NEW.ubicacion_id
          AND cantidad >= NEW.cantidad;

        IF NOT FOUND THEN
            RAISE EXCEPTION 'Stock insuficiente para el producto % en la ubicación %',
                NEW.producto_id, NEW.ubicacion_id;
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_actualizar_stock ON almacen.movimientos;
CREATE TRIGGER trg_actualizar_stock
AFTER INSERT ON almacen.movimientos
FOR EACH ROW EXECUTE FUNCTION almacen.fn_actualizar_stock_tiempo_real();

-- ----------------------------------------------------------------------------
-- 7. VISTAS DE APOYO (compatibilidad con el modelo aprobado + reparto)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW operaciones.v_ruta_picking AS
SELECT
    u.orden_picking,
    u.codigo AS ubicacion,
    p.sku,
    p.nombre AS producto,
    s.cantidad AS disponible
FROM almacen.stock s
JOIN almacen.ubicaciones u ON u.id = s.ubicacion_id
JOIN almacen.productos p ON p.id = s.producto_id
WHERE s.cantidad > 0
ORDER BY u.orden_picking ASC;

CREATE OR REPLACE VIEW auditoria.v_metricas_rotacion AS
SELECT
    p.sku,
    p.nombre,
    COALESCE(SUM(m.cantidad) FILTER (WHERE m.tipo = 'SALIDA'), 0) AS total_salidas,
    COALESCE(SUM(m.cantidad) FILTER (WHERE m.tipo = 'ENTRADA'), 0) AS total_entradas
FROM almacen.productos p
LEFT JOIN almacen.movimientos m ON m.producto_id = p.id
GROUP BY p.id, p.sku, p.nombre;

CREATE OR REPLACE VIEW operaciones.v_resumen_rutas AS
SELECT
    r.id,
    r.folio,
    r.zona,
    r.fecha,
    r.estado,
    v.placas,
    v.modelo,
    c.nombre AS conductor,
    COUNT(DISTINCT rp.id) AS paradas,
    COUNT(rb.bulto_id) AS bultos,
    r.distancia_km,
    r.ahorro_pct
FROM operaciones.rutas r
JOIN operaciones.vehiculos v ON v.id = r.vehiculo_id
JOIN operaciones.conductores c ON c.id = r.conductor_id
LEFT JOIN operaciones.ruta_paradas rp ON rp.ruta_id = r.id
LEFT JOIN operaciones.ruta_bultos rb ON rb.ruta_parada_id = rp.id
GROUP BY r.id, v.placas, v.modelo, c.nombre;

CREATE OR REPLACE VIEW operaciones.v_entregas_fallidas AS
SELECT
    e.id,
    r.folio AS ruta,
    cl.nombre AS cliente,
    cl.zona,
    e.motivo_fallo,
    e.comentario,
    e.reprogramado_para,
    e.registrado_en
FROM operaciones.entregas e
JOIN operaciones.ruta_paradas rp ON rp.id = e.ruta_parada_id
JOIN operaciones.rutas r ON r.id = rp.ruta_id
JOIN operaciones.clientes cl ON cl.id = rp.cliente_id
WHERE e.resultado = 'FALLIDO';

-- ----------------------------------------------------------------------------
-- 8. ROLES Y PRIVILEGIOS
-- La aplicación ejecuta SET LOCAL ROLE según el rol del token, además de
-- validar los permisos en FastAPI. Así PostgreSQL también aplica el RBAC.
-- ----------------------------------------------------------------------------
DO $$ BEGIN CREATE ROLE rol_admin NOLOGIN; EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE ROLE rol_operador NOLOGIN; EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE ROLE rol_auditor NOLOGIN; EXCEPTION WHEN duplicate_object THEN NULL; END $$;

GRANT USAGE ON SCHEMA seguridad, almacen, operaciones, auditoria TO rol_admin;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA seguridad, almacen, operaciones, auditoria TO rol_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA seguridad, almacen, operaciones, auditoria TO rol_admin;

-- Operador: lectura general y escritura operativa (sin usuarios ni borrados).
GRANT USAGE ON SCHEMA almacen, operaciones, seguridad TO rol_operador;
GRANT SELECT ON ALL TABLES IN SCHEMA almacen, operaciones TO rol_operador;
GRANT SELECT (id, nombre, usuario, rol, activo) ON seguridad.usuarios TO rol_operador;
GRANT INSERT, UPDATE ON almacen.movimientos,
                        almacen.lotes,
                        operaciones.proveedores,
                        operaciones.ordenes_compra,
                        operaciones.orden_compra_lineas,
                        operaciones.recepciones,
                        operaciones.recepcion_lineas,
                        operaciones.incidencias_recepcion,
                        operaciones.clientes,
                        operaciones.pedidos,
                        operaciones.bultos,
                        operaciones.picking_olas,
                        operaciones.picking_tareas,
                        operaciones.empaques,
                        operaciones.rutas,
                        operaciones.ruta_paradas,
                        operaciones.ruta_bultos,
                        operaciones.eventos_rastreo,
                        operaciones.entregas TO rol_operador;
GRANT INSERT, UPDATE, DELETE ON operaciones.pedido_detalle TO rol_operador;
GRANT INSERT ON almacen.traslados TO rol_operador;
GRANT INSERT ON seguridad.bitacora TO rol_operador;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA almacen, operaciones, seguridad TO rol_operador;

-- Auditor: lectura de toda la operación, bitácora y conteos; sin cambios.
GRANT USAGE ON SCHEMA almacen, operaciones, auditoria, seguridad TO rol_auditor;
GRANT SELECT ON ALL TABLES IN SCHEMA almacen, operaciones TO rol_auditor;
GRANT SELECT (id, nombre, usuario, rol, activo) ON seguridad.usuarios TO rol_auditor;
GRANT SELECT, INSERT ON auditoria.conteos_ciclicos TO rol_auditor;
GRANT SELECT ON auditoria.v_metricas_rotacion TO rol_auditor;
GRANT SELECT ON seguridad.bitacora TO rol_auditor;
GRANT INSERT ON seguridad.bitacora TO rol_auditor;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA auditoria, seguridad TO rol_auditor;

COMMIT;
