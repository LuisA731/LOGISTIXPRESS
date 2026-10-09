

BEGIN;

-- --------------------------------------------------------------------------
-- 1. ESQUEMAS
-- --------------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS almacen;
CREATE SCHEMA IF NOT EXISTS operaciones;
CREATE SCHEMA IF NOT EXISTS auditoria;

-- --------------------------------------------------------------------------
-- 2. TABLAS BASE
-- --------------------------------------------------------------------------


CREATE TABLE almacen.ubicaciones (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(30) UNIQUE NOT NULL,
    pasillo VARCHAR(10) NOT NULL,
    rack VARCHAR(10) NOT NULL,
    nivel INT NOT NULL,
    orden_picking INT NOT NULL 
);

CREATE TABLE almacen.productos (
    id SERIAL PRIMARY KEY,
    sku VARCHAR(50) UNIQUE NOT NULL,
    nombre VARCHAR(150) NOT NULL,
    stock_minimo INT NOT NULL DEFAULT 5
);


CREATE TABLE almacen.stock (
    id SERIAL PRIMARY KEY,
    producto_id INT NOT NULL REFERENCES almacen.productos(id),
    ubicacion_id INT NOT NULL REFERENCES almacen.ubicaciones(id),
    cantidad INT NOT NULL DEFAULT 0 CHECK (cantidad >= 0),
    CONSTRAINT uq_prod_ubic UNIQUE(producto_id, ubicacion_id)
);


CREATE TABLE almacen.movimientos (
    id SERIAL PRIMARY KEY,
    producto_id INT NOT NULL REFERENCES almacen.productos(id),
    ubicacion_id INT NOT NULL REFERENCES almacen.ubicaciones(id),
    tipo VARCHAR(10) NOT NULL CHECK (tipo IN ('ENTRADA', 'SALIDA')),
    cantidad INT NOT NULL CHECK (cantidad > 0),
    usuario_id INT NOT NULL,
    fecha TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE operaciones.empaque (
    id SERIAL PRIMARY KEY,
    codigo_etiqueta VARCHAR(100) UNIQUE NOT NULL,
    producto_id INT NOT NULL REFERENCES almacen.productos(id),
    cantidad INT NOT NULL CHECK (cantidad > 0),
    estado VARCHAR(20) DEFAULT 'PENDIENTE' CHECK (estado IN ('PENDIENTE', 'EMPAQUETADO', 'ETIQUETADO', 'RECHAZADO')),
    fecha TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE operaciones.embarques (
    id SERIAL PRIMARY KEY,
    folio VARCHAR(50) UNIQUE NOT NULL,
    conductor VARCHAR(100) NOT NULL,
    estado VARCHAR(20) DEFAULT 'EN_TRANSITO' CHECK (estado IN ('EN_TRANSITO', 'ENTREGADO', 'CANCELADO')),
    evidencia_digital_url TEXT, -- URL de fotografía/firma digital de entrega
    fecha_salida TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    fecha_entrega TIMESTAMPTZ
);


CREATE TABLE auditoria.conteos_ciclicos (
    id SERIAL PRIMARY KEY,
    ubicacion_id INT NOT NULL REFERENCES almacen.ubicaciones(id),
    producto_id INT NOT NULL REFERENCES almacen.productos(id),
    cantidad_sistema INT NOT NULL,
    cantidad_fisica INT NOT NULL,
    diferencia INT GENERATED ALWAYS AS (cantidad_fisica - cantidad_sistema) STORED,
    auditor_id INT NOT NULL,
    fecha TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- --------------------------------------------------------------------------
-- 3. TRIGGERS (AUTOMATIZACIÓN EN TIEMPO REAL)
-- --------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION almacen.fn_actualizar_stock_tiempo_real()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.tipo = 'ENTRADA' THEN
        INSERT INTO almacen.stock (producto_id, ubicacion_id, cantidad)
        VALUES (NEW.producto_id, NEW.ubicacion_id, NEW.cantidad)
        ON CONFLICT (producto_id, ubicacion_id)
        DO UPDATE SET cantidad = almacen.stock.cantidad + EXCLUDED.cantidad;
        
    ELSIF NEW.tipo = 'SALIDA' THEN
        UPDATE almacen.stock
        SET cantidad = cantidad - NEW.cantidad
        WHERE producto_id = NEW.producto_id AND ubicacion_id = NEW.ubicacion_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_actualizar_stock
AFTER INSERT ON almacen.movimientos
FOR EACH ROW EXECUTE FUNCTION almacen.fn_actualizar_stock_tiempo_real();

-- --------------------------------------------------------------------------
-- 4. VISTAS (RUTAS ÓPTIMAS Y MÉTRICAS)
-- --------------------------------------------------------------------------


CREATE VIEW operaciones.v_ruta_picking AS
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


CREATE VIEW auditoria.v_metricas_rotacion AS
SELECT 
    p.sku,
    p.nombre,
    COALESCE(SUM(m.cantidad) FILTER (WHERE m.tipo = 'SALIDA'), 0) AS total_salidas,
    COALESCE(SUM(m.cantidad) FILTER (WHERE m.tipo = 'ENTRADA'), 0) AS total_entradas
FROM almacen.productos p
LEFT JOIN almacen.movimientos m ON m.producto_id = p.id
GROUP BY p.id, p.sku, p.nombre;

-- --------------------------------------------------------------------------
-- 5. ROLES Y SEGURIDAD (ACCESO SEGÚN ROL)
-- --------------------------------------------------------------------------

DO $$ BEGIN CREATE ROLE rol_admin NOLOGIN; EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE ROLE rol_operador NOLOGIN; EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE ROLE rol_auditor NOLOGIN; EXCEPTION WHEN duplicate_object THEN NULL; END $$;


GRANT USAGE ON SCHEMA almacen, operaciones, auditoria TO rol_admin;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA almacen, operaciones, auditoria TO rol_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA almacen, operaciones, auditoria TO rol_admin;


GRANT USAGE ON SCHEMA almacen, operaciones TO rol_operador;
GRANT SELECT ON ALL TABLES IN SCHEMA almacen, operaciones TO rol_operador;
GRANT INSERT, UPDATE ON almacen.movimientos, operaciones.empaque, operaciones.embarques TO rol_operador;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA almacen, operaciones TO rol_operador;


GRANT USAGE ON SCHEMA almacen, auditoria TO rol_auditor;
GRANT SELECT ON ALL TABLES IN SCHEMA almacen TO rol_auditor;
GRANT SELECT, INSERT ON auditoria.conteos_ciclicos TO rol_auditor;
GRANT SELECT ON auditoria.v_metricas_rotacion TO rol_auditor;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA auditoria TO rol_auditor;

COMMIT;
