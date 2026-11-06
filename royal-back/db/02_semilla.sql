-- ============================================================================
-- LogistiXpress · Semilla de demostración
-- Reinicia los datos del PoC y crea un día operativo reproducible:
--   · 14 pedidos (9 pendientes de ruta, 2 en ruta, 3 con historial)
--   · 1 ruta histórica completada con una entrega fallida
--   · 1 ruta planificada para despachar desde el dashboard
-- Credenciales demo: admin/admin123 · operador/operador123 · auditor/auditor123
-- ============================================================================
BEGIN;

TRUNCATE seguridad.bitacora,
         seguridad.usuarios,
         auditoria.conteos_ciclicos,
         operaciones.eventos_rastreo,
         operaciones.entregas,
         operaciones.ruta_bultos,
         operaciones.ruta_paradas,
         operaciones.rutas,
         operaciones.bultos,
         operaciones.empaques,
         operaciones.picking_tareas,
         operaciones.picking_olas,
         operaciones.pedido_detalle,
         operaciones.pedidos,
         operaciones.incidencias_recepcion,
         operaciones.recepcion_lineas,
         operaciones.recepciones,
         operaciones.orden_compra_lineas,
         operaciones.ordenes_compra,
         operaciones.proveedores,
         operaciones.clientes,
         operaciones.conductores,
         operaciones.vehiculos,
         almacen.traslados,
         almacen.movimientos,
         almacen.lotes,
         almacen.stock,
         almacen.productos,
         almacen.ubicaciones
RESTART IDENTITY CASCADE;

ALTER SEQUENCE operaciones.folio_ruta_seq RESTART WITH 1000;
ALTER SEQUENCE operaciones.folio_pedido_seq RESTART WITH 1000;
ALTER SEQUENCE operaciones.folio_oc_seq RESTART WITH 1000;
ALTER SEQUENCE operaciones.folio_ola_seq RESTART WITH 1000;
ALTER SEQUENCE operaciones.folio_empaque_seq RESTART WITH 5000;
ALTER SEQUENCE operaciones.folio_guia_seq RESTART WITH 10000;

-- ----------------------------------------------------------------------------
-- USUARIOS DEMO
-- ----------------------------------------------------------------------------
INSERT INTO seguridad.usuarios (nombre, usuario, correo, password_hash, rol, puesto) VALUES
('Omar Morales',  'admin',    'admin@logistixpress.mx',
 'pbkdf2_sha256$200000$YzssDtqPNIFXtctCYRFuqg==$lzWsZyjxrT7tyB+z9rhCPdsfLyuyjlZfBOxbDDZQ44k=', 'admin', 'Dirección'),
('Laura Salinas', 'operador', 'operador@logistixpress.mx',
 'pbkdf2_sha256$200000$xJgiPtJ78U4+PDCrI5zesw==$trIYJRpsI2pHQqho1SmsgWh8K5Hpe1Bj3Sa9JY/G4yo=', 'operador', 'Supervisor'),
('Andrés Garza',  'auditor',  'auditor@logistixpress.mx',
 'pbkdf2_sha256$200000$SMUwrLUoiBJzOEeV+yIa2g==$mKyWlB+VxZw7SvEqwLSjPvIpE7uy5VUb9DVQJQrhux8=', 'auditor', 'Auditoría');

-- ----------------------------------------------------------------------------
-- ALMACÉN
-- ----------------------------------------------------------------------------
INSERT INTO almacen.ubicaciones (codigo, pasillo, rack, nivel, orden_picking, tipo_zona) VALUES
('A-01-1', 'A', '01', 1, 10, 'GENERAL'),
('A-01-2', 'A', '01', 2, 20, 'GENERAL'),
('A-02-1', 'A', '02', 1, 30, 'GENERAL'),
('B-01-1', 'B', '01', 1, 40, 'GENERAL'),
('B-01-2', 'B', '01', 2, 50, 'GENERAL'),
('B-02-1', 'B', '02', 1, 60, 'GENERAL'),
('C-01-1', 'C', '01', 1, 70, 'GENERAL'),
('C-01-2', 'C', '01', 2, 80, 'GENERAL'),
('C-02-1', 'C', '02', 1, 90, 'GENERAL'),
('D-01-1', 'D', '01', 1, 100, 'GENERAL'),
('D-01-2', 'D', '01', 2, 110, 'GENERAL'),
('D-02-1', 'D', '02', 1, 120, 'GENERAL'),
('DEV-01-1', 'DEV', '01', 1, 130, 'DEVOLUCIONES'),
('DAN-01-1', 'DAN', '01', 1, 140, 'DANADOS'),
('BLO-01-1', 'BLO', '01', 1, 150, 'BLOQUEADO'),
('RES-01-1', 'RES', '01', 1, 160, 'RESERVADO');

INSERT INTO almacen.productos (sku, nombre, stock_minimo, peso_kg, volumen_m3) VALUES
('HAR-25', 'Harina de trigo 25 kg',            10, 25.000, 0.0600),
('ACE-12', 'Aceite vegetal 12 L',                8, 11.500, 0.0140),
('AZU-25', 'Azúcar estándar 25 kg',             12, 25.200, 0.0500),
('AGU-12', 'Agua purificada 12 piezas',         15, 12.500, 0.0120),
('CAF-20', 'Café molido caja 20 piezas',         6, 20.400, 0.0300),
('LEC-12', 'Leche en polvo caja 12 piezas',      8, 15.000, 0.0250),
('DET-10', 'Detergente 10 kg',                  10, 10.200, 0.0200),
('PAN-CJ', 'Pañales caja 40 piezas',             5,  8.000, 0.0800);

INSERT INTO almacen.stock (producto_id, ubicacion_id, cantidad) VALUES
(1, 1, 120), (1, 2,  80), (2, 3, 150), (2, 4,  60),
(3, 5, 110), (3, 6,  70), (4, 7, 200), (4, 8, 140),
(5, 9,  45), (5,10,  35), (6, 11, 90), (6,12,  55),
(7, 2,  65), (8, 4,   2), (8, 6,   0), (7, 8,  25);

INSERT INTO almacen.lotes (producto_id, ubicacion_id, lote, caducidad, cantidad, condicion) VALUES
(1, 1, 'HAR-2026-07', CURRENT_DATE + 120, 120, 'BUENO'),
(2, 3, 'ACE-2026-09', CURRENT_DATE + 240, 150, 'BUENO'),
(3, 5, 'AZU-2026-05', CURRENT_DATE + 300, 110, 'BUENO'),
(4, 7, 'AGU-2026-10', CURRENT_DATE +  45, 200, 'BUENO'),
(5, 9, 'CAF-2026-08', CURRENT_DATE +  75,  45, 'BUENO'),
(6,11, 'LEC-2026-04', CURRENT_DATE +  30,  90, 'BUENO'),
(7, 2, 'DET-2026-01', CURRENT_DATE + 500,  65, 'BUENO'),
(8, 4, 'PAN-2026-02', CURRENT_DATE + 180,   2, 'BUENO');

INSERT INTO almacen.movimientos (producto_id, ubicacion_id, tipo, cantidad, usuario_id, fecha) VALUES
(1, 1, 'ENTRADA', 20, 2, CURRENT_TIMESTAMP - INTERVAL '3 days'),
(2, 3, 'SALIDA',  12, 2, CURRENT_TIMESTAMP - INTERVAL '2 days'),
(4, 7, 'SALIDA',  30, 2, CURRENT_TIMESTAMP - INTERVAL '1 day'),
(6,11, 'ENTRADA', 15, 2, CURRENT_TIMESTAMP - INTERVAL '6 hours'),
(3, 5, 'SALIDA',   4, 2, CURRENT_TIMESTAMP - INTERVAL '2 hours');

-- ----------------------------------------------------------------------------
-- CLIENTES, FLOTA
-- ----------------------------------------------------------------------------
INSERT INTO operaciones.clientes
(codigo, nombre, tipo_cliente, zona, direccion, colonia, telefono, contacto, latitud, longitud) VALUES
('CD-001', 'Distribuidora del Norte',   'MAYORISTA',   'NORTE',    'Av. Lincoln 2100',          'Residencial Norte', '81 1100 2201', 'Sofía Treviño',   25.742100, -100.311800),
('CD-002', 'Farmacia San Rafael',       'FARMACIA',    'NORTE',    'Calle Hidalgo 845',         'Centro Norte',      '81 1100 2202', 'Rafael Cantú',    25.769000, -100.294000),
('CD-003', 'Restaurante El Roble',      'RESTAURANTE', 'NORTE',    'Prol. Constitución 320',    'Anáhuac Norte',     '81 1100 2203', 'Mónica Elizondo', 25.724000, -100.282000),
('CD-004', 'Tienda La Esquina',         'MINORISTA',   'SUR',      'Calle Colón 410',           'Centro Sur',        '81 1100 2204', 'Jorge Villarreal',25.630500, -100.305000),
('CD-005', 'Abarrotes Don Chuy',        'MINORISTA',   'SUR',      'Av. Garza Sada 1780',       'Independencia',     '81 1100 2205', 'Jesús Martínez',  25.648000, -100.323000),
('CD-006', 'Hospital Santa Lucía',      'HOSPITAL',    'SUR',      'Calle Magnolia 120',        'La Estanzuela',     '81 1100 2206', 'Dra. Lucía Ríos', 25.611000, -100.290000),
('CD-007', 'Supermercados del Este',    'MAYORISTA',   'ORIENTE',  'Av. Miguel Alemán 3050',    'Apodaca Centro',    '81 1100 2207', 'Arturo Benavides',25.690000, -100.230000),
('CD-008', 'Ferretería El Tornillo',    'MINORISTA',   'ORIENTE',  'Calle del Álamo 760',       'Jardines de Apodaca','81 1100 2208','Elena Garza',     25.705000, -100.205000),
('CD-009', 'Café Central',              'RESTAURANTE', 'ORIENTE',  'Blvd. Aeropuerto 500',      'Centro Apodaca',    '81 1100 2209', 'Patricia Luna',   25.666000, -100.242000),
('CD-010', 'Clínica del Valle',         'HOSPITAL',    'ORIENTE',  'Av. Concordia 940',         'Hacienda El Valle', '81 1100 2210', 'Dr. Mario Peña',  25.720000, -100.220000),
('CD-011', 'Papelería Central',         'CORPORATIVO', 'PONIENTE', 'Calzada del Valle 1500',    'Del Valle',         '81 1100 2211', 'Karla Villarreal',25.680000, -100.390000),
('CD-012', 'Distribuidora Poniente',    'MAYORISTA',   'PONIENTE', 'Av. Revolución 2200',       'San Jerónimo',      '81 1100 2212', 'Eduardo Sáenz',   25.700000, -100.380000),
('CD-013', 'Tienda Verde',              'MINORISTA',   'PONIENTE', 'Calle Cumbres 510',         'Cumbres Poniente',  '81 1100 2213', 'Ana Cecilia Ruiz',25.660000, -100.370000),
('CD-014', 'Comedor Industrial',        'RESTAURANTE', 'PONIENTE', 'Av. Las Palmas 1080',       'Las Palmas',        '81 1100 2214', 'Raúl Chapa',      25.715000, -100.398000);

INSERT INTO operaciones.proveedores (codigo, nombre, contacto, telefono, correo) VALUES
('PROV-001', 'Lácteos del Norte', 'Sofía Cantú', '81 3000 4101', 'compras@lacteosnorte.mx'),
('PROV-002', 'Abarrotes del Golfo', 'Héctor Salinas', '81 3000 4102', 'ventas@abarrotesgolfo.mx'),
('PROV-003', 'Cuidado Personal MX', 'Diana Elizondo', '81 3000 4103', 'cuenta@cuidadopersonal.mx');

INSERT INTO operaciones.ordenes_compra
(folio, proveedor_id, estado, fecha_esperada, hora_estimada, anden, observaciones, creado_por)
VALUES
('OC-0001', 1, 'PROGRAMADA', CURRENT_DATE, '09:30', 'A-1', 'Descarga prioritaria de perecederos.', 2),
('OC-0002', 2, 'PROGRAMADA', CURRENT_DATE, '11:00', 'A-2', 'Revisar tarimas completas.', 2),
('OC-0003', 3, 'CON_INCIDENCIA', CURRENT_DATE - 1, '10:00', 'B-1', 'Recepción con caja dañada.', 2);

INSERT INTO operaciones.orden_compra_lineas
(orden_compra_id, producto_id, cantidad_solicitada, cantidad_recibida)
SELECT id, 1, 40, 0 FROM operaciones.ordenes_compra WHERE folio = 'OC-0001'
UNION ALL
SELECT id, 2, 20, 0 FROM operaciones.ordenes_compra WHERE folio = 'OC-0001'
UNION ALL
SELECT id, 4, 60, 0 FROM operaciones.ordenes_compra WHERE folio = 'OC-0002'
UNION ALL
SELECT id, 8, 15, 0 FROM operaciones.ordenes_compra WHERE folio = 'OC-0002'
UNION ALL
SELECT id, 7, 20, 20 FROM operaciones.ordenes_compra WHERE folio = 'OC-0003';

INSERT INTO operaciones.recepciones (orden_compra_id, recibido_por, observaciones, fecha)
SELECT id, 2, 'Recepción de demostración con incidencia.', CURRENT_TIMESTAMP - INTERVAL '1 day'
FROM operaciones.ordenes_compra WHERE folio = 'OC-0003';

INSERT INTO operaciones.recepcion_lineas
(recepcion_id, orden_compra_linea_id, producto_id, ubicacion_id,
 lote, caducidad, condicion, cantidad_recibida)
SELECT r.id, ocl.id, 7, 14, 'DET-2026-R1', CURRENT_DATE + 400, 'DANADO', 20
FROM operaciones.recepciones r
JOIN operaciones.ordenes_compra oc ON oc.id = r.orden_compra_id
JOIN operaciones.orden_compra_lineas ocl ON ocl.orden_compra_id = oc.id
WHERE oc.folio = 'OC-0003' AND ocl.producto_id = 7;

INSERT INTO operaciones.incidencias_recepcion
(recepcion_id, producto_id, descripcion, responsable, comentario, fecha)
SELECT r.id, 7, 'Caja rota en la descarga', 'Laura Salinas',
       'Se recibió una caja dañada; se resguarda en zona de dañados.',
       CURRENT_TIMESTAMP - INTERVAL '1 day'
FROM operaciones.recepciones r
JOIN operaciones.ordenes_compra oc ON oc.id = r.orden_compra_id
WHERE oc.folio = 'OC-0003';

INSERT INTO almacen.lotes
(producto_id, ubicacion_id, lote, caducidad, cantidad, condicion)
VALUES (7, 14, 'DET-2026-R1', CURRENT_DATE + 400, 20, 'DANADO');

INSERT INTO almacen.movimientos
(producto_id, ubicacion_id, tipo, cantidad, usuario_id, fecha)
VALUES (7, 14, 'ENTRADA', 20, 2, CURRENT_TIMESTAMP - INTERVAL '1 day');

UPDATE operaciones.ordenes_compra
SET recibido_en = CURRENT_TIMESTAMP - INTERVAL '1 day'
WHERE folio = 'OC-0003';

INSERT INTO operaciones.vehiculos (placas, modelo, capacidad_kg, capacidad_m3) VALUES
('LX-4821', 'Nissan NP300 · caja seca',      1200.00, 8.000),
('LX-7390', 'Isuzu ELF · caja seca',          900.00, 6.000),
('LX-9054', 'Ford Transit · caja seca',       640.00, 4.500),
('LX-1122', 'Mercedes Sprinter · caja seca', 1500.00, 10.000);

INSERT INTO operaciones.conductores (nombre, telefono, licencia) VALUES
('R. Aguilar',    '81 2100 3301', 'LIC-AGU-8812'),
('M. Salinas',    '81 2100 3302', 'LIC-SAL-4471'),
('J. Orozco',     '81 2100 3303', 'LIC-ORO-2290'),
('C. Treviño',    '81 2100 3304', 'LIC-TRE-6634');

-- ----------------------------------------------------------------------------
-- PEDIDOS Y BULTOS
-- Los pedidos 1-3 forman el historial, 7-8 la ruta planificada y el resto
-- queda LISTO para que el dashboard genere el plan del día.
-- ----------------------------------------------------------------------------
DO $$
DECLARE
    i        INT;
    j        INT;
    v_pedido INT;
    v_prod   INT;
    v_cant   INT;
    v_bulto  INT;
    v_peso_u NUMERIC;
    v_vol_u  NUMERIC;
    v_nombre VARCHAR;
    v_peso   NUMERIC;
    v_vol    NUMERIC;
    v_total_peso NUMERIC;
    v_total_vol  NUMERIC;
BEGIN
    FOR i IN 1..14 LOOP
        INSERT INTO operaciones.pedidos
            (folio, cliente_id, estado, prioridad, fecha_pedido, fecha_compromiso, observaciones)
        VALUES
            (format('PED-2026-%s', lpad(i::text, 4, '0')),
             i,
             'LISTO',
             CASE WHEN i IN (2, 7, 12) THEN 'ALTA' ELSE 'NORMAL' END,
             CURRENT_DATE - (i % 4),
             CURRENT_DATE + 1 + (i % 3),
             CASE WHEN i % 5 = 0 THEN 'Manejar con cuidado · producto frágil' ELSE NULL END)
        RETURNING id INTO v_pedido;

        v_total_peso := 0;
        v_total_vol  := 0;

        FOR j IN 1..(2 + (i % 2)) LOOP
            v_prod   := ((i * 2 + j) % 8) + 1;
            v_cant   := 1 + ((i + j) % 3);
            v_peso_u := (SELECT peso_kg FROM almacen.productos WHERE id = v_prod);
            v_vol_u  := (SELECT volumen_m3 FROM almacen.productos WHERE id = v_prod);
            v_nombre := (SELECT nombre FROM almacen.productos WHERE id = v_prod);
            v_peso   := round(v_peso_u * v_cant, 3);
            v_vol    := round(v_vol_u * v_cant, 4);

            INSERT INTO operaciones.bultos
                (guia, pedido_id, descripcion, peso_kg, volumen_m3, estado, creado_en)
            VALUES
                (format('LX-%s', lpad((i * 10 + j)::text, 5, '0')),
                 v_pedido,
                 format('%s · %s pieza(s)', v_nombre, v_cant),
                 v_peso, v_vol, 'EN_BODEGA',
                 CURRENT_TIMESTAMP - INTERVAL '1 day')
            RETURNING id INTO v_bulto;

            INSERT INTO operaciones.pedido_detalle (pedido_id, producto_id, cantidad)
            VALUES (v_pedido, v_prod, v_cant);

            INSERT INTO operaciones.eventos_rastreo
                (bulto_id, estado, descripcion, ubicacion, fecha)
            VALUES
                (v_bulto, 'RECIBIDO', 'Mercancía recibida y validada en CEDIS',
                 'Andén 1', CURRENT_TIMESTAMP - INTERVAL '1 day'),
                (v_bulto, 'ETIQUETADO', 'Bulto etiquetado y listo para consolidación',
                 'Zona de empaque', CURRENT_TIMESTAMP - INTERVAL '20 hours');

            v_total_peso := v_total_peso + v_peso;
            v_total_vol  := v_total_vol + v_vol;
        END LOOP;

        UPDATE operaciones.pedidos
        SET peso_kg = round(v_total_peso, 3),
            volumen_m3 = round(v_total_vol, 4)
        WHERE id = v_pedido;
    END LOOP;
END;
$$;

-- Pedido demo en BORRADOR para demostrar picking, packing y QC desde la UI.
INSERT INTO operaciones.pedidos
(folio, cliente_id, estado, prioridad, fecha_pedido, fecha_compromiso,
 peso_kg, volumen_m3, observaciones)
VALUES
('PED-2026-0015', 2, 'BORRADOR', 'ALTA', CURRENT_DATE, CURRENT_DATE + 2,
 75.300, 0.1020, 'Pedido de demostración para picking y empaque.');

INSERT INTO operaciones.pedido_detalle (pedido_id, producto_id, cantidad)
VALUES
((SELECT id FROM operaciones.pedidos WHERE folio = 'PED-2026-0015'), 2, 3),
((SELECT id FROM operaciones.pedidos WHERE folio = 'PED-2026-0015'), 5, 2);

-- ----------------------------------------------------------------------------
-- HISTORIAL: ruta de ayer con 2 entregas y 1 intento fallido
-- ----------------------------------------------------------------------------
UPDATE operaciones.pedidos SET estado = 'ENTREGADO'    WHERE id IN (1, 2);
UPDATE operaciones.pedidos SET estado = 'REPROGRAMADO' WHERE id = 3;
UPDATE operaciones.bultos  SET estado = 'ENTREGADO'    WHERE pedido_id IN (1, 2);
UPDATE operaciones.bultos  SET estado = 'DEVUELTO'     WHERE pedido_id = 3;

INSERT INTO operaciones.rutas
(folio, zona, fecha, vehiculo_id, conductor_id, estado, distancia_km,
 distancia_base_km, ahorro_pct, eta_min, generada_por, generada_en,
 salida_en, cierre_en)
VALUES
('R-HIST-001', 'NORTE', CURRENT_DATE - 1, 1, 1, 'COMPLETADA', 34.80,
 42.50, 18.12, 97.0, 1, CURRENT_TIMESTAMP - INTERVAL '1 day 5 hours',
 CURRENT_TIMESTAMP - INTERVAL '1 day 4 hours', CURRENT_TIMESTAMP - INTERVAL '1 day');

INSERT INTO operaciones.ruta_paradas
(ruta_id, pedido_id, cliente_id, secuencia, latitud, longitud, distancia_km, eta_min, estado)
SELECT r.id, p.id, c.id,
       ROW_NUMBER() OVER (ORDER BY p.id),
       c.latitud, c.longitud,
       CASE p.id WHEN 1 THEN 8.20 WHEN 2 THEN 11.30 ELSE 15.30 END,
       CASE p.id WHEN 1 THEN 28.0 WHEN 2 THEN 52.0 ELSE 79.0 END,
       CASE p.id WHEN 1 THEN 'ENTREGADO' WHEN 2 THEN 'ENTREGADO' ELSE 'FALLIDO' END
FROM operaciones.rutas r
JOIN operaciones.pedidos p ON p.id IN (1, 2, 3)
JOIN operaciones.clientes c ON c.id = p.cliente_id
WHERE r.folio = 'R-HIST-001';

INSERT INTO operaciones.ruta_bultos (ruta_parada_id, bulto_id)
SELECT rp.id, b.id
FROM operaciones.ruta_paradas rp
JOIN operaciones.rutas r ON r.id = rp.ruta_id AND r.folio = 'R-HIST-001'
JOIN operaciones.bultos b ON b.pedido_id = rp.pedido_id;

INSERT INTO operaciones.entregas
(ruta_parada_id, resultado, recibio_nombre, motivo_fallo, comentario,
 reprogramado_para, registrado_por, registrado_en)
SELECT rp.id, 'ENTREGADO', 'Sofía Treviño', NULL, 'Entrega completa en recepción.',
       NULL, 2, CURRENT_TIMESTAMP - INTERVAL '1 day 2 hours'
FROM operaciones.ruta_paradas rp
JOIN operaciones.rutas r ON r.id = rp.ruta_id AND r.folio = 'R-HIST-001'
WHERE rp.pedido_id = 1;

INSERT INTO operaciones.entregas
(ruta_parada_id, resultado, recibio_nombre, motivo_fallo, comentario,
 reprogramado_para, registrado_por, registrado_en)
SELECT rp.id, 'ENTREGADO', 'Rafael Cantú', NULL, 'Recibido por el encargado de turno.',
       NULL, 2, CURRENT_TIMESTAMP - INTERVAL '1 day 1 hour 30 minutes'
FROM operaciones.ruta_paradas rp
JOIN operaciones.rutas r ON r.id = rp.ruta_id AND r.folio = 'R-HIST-001'
WHERE rp.pedido_id = 2;

INSERT INTO operaciones.entregas
(ruta_parada_id, resultado, recibio_nombre, motivo_fallo, comentario,
 reprogramado_para, registrado_por, registrado_en)
SELECT rp.id, 'FALLIDO', NULL, 'CLIENTE_CERRADO',
       'El negocio estaba cerrado al momento del intento. Se devuelve a bodega.',
       CURRENT_DATE + 1, 2, CURRENT_TIMESTAMP - INTERVAL '1 day 1 hour'
FROM operaciones.ruta_paradas rp
JOIN operaciones.rutas r ON r.id = rp.ruta_id AND r.folio = 'R-HIST-001'
WHERE rp.pedido_id = 3;

-- Línea de tiempo histórica por bulto.
INSERT INTO operaciones.eventos_rastreo (bulto_id, ruta_id, estado, descripcion, ubicacion, usuario_id, fecha)
SELECT b.id, r.id, 'ASIGNADO', 'Bulto asignado a la ruta R-HIST-001', 'CEDIS · Andén 1', 2,
       CURRENT_TIMESTAMP - INTERVAL '1 day 5 hours'
FROM operaciones.bultos b
JOIN operaciones.rutas r ON r.folio = 'R-HIST-001'
WHERE b.pedido_id IN (1, 2, 3);

INSERT INTO operaciones.eventos_rastreo (bulto_id, ruta_id, estado, descripcion, ubicacion, usuario_id, fecha)
SELECT b.id, r.id, 'EN_RUTA', 'Unidad despachada del andén', 'Ruta Norte', 2,
       CURRENT_TIMESTAMP - INTERVAL '1 day 4 hours'
FROM operaciones.bultos b
JOIN operaciones.rutas r ON r.folio = 'R-HIST-001'
WHERE b.pedido_id IN (1, 2, 3);

INSERT INTO operaciones.eventos_rastreo (bulto_id, ruta_id, estado, descripcion, ubicacion, usuario_id, fecha)
SELECT b.id, r.id, 'ENTREGADO', 'Entrega confirmada con evidencia digital', 'Domicilio del cliente', 2,
       CURRENT_TIMESTAMP - INTERVAL '1 day 2 hours'
FROM operaciones.bultos b
JOIN operaciones.rutas r ON r.folio = 'R-HIST-001'
WHERE b.pedido_id IN (1, 2);

INSERT INTO operaciones.eventos_rastreo (bulto_id, ruta_id, estado, descripcion, ubicacion, usuario_id, fecha)
SELECT b.id, r.id, 'FALLIDO', 'Intento de entrega fallido: cliente cerrado', 'Domicilio del cliente', 2,
       CURRENT_TIMESTAMP - INTERVAL '1 day 1 hour'
FROM operaciones.bultos b
JOIN operaciones.rutas r ON r.folio = 'R-HIST-001'
WHERE b.pedido_id = 3;

INSERT INTO operaciones.eventos_rastreo (bulto_id, ruta_id, estado, descripcion, ubicacion, usuario_id, fecha)
SELECT b.id, r.id, 'DEVUELTO', 'Mercancía recibida nuevamente en bodega', 'CEDIS · Zona devoluciones', 2,
       CURRENT_TIMESTAMP - INTERVAL '23 hours'
FROM operaciones.bultos b
JOIN operaciones.rutas r ON r.folio = 'R-HIST-001'
WHERE b.pedido_id = 3;

INSERT INTO operaciones.eventos_rastreo (bulto_id, ruta_id, estado, descripcion, ubicacion, usuario_id, fecha)
SELECT b.id, r.id, 'REPROGRAMADO', 'Entrega reprogramada para el día siguiente', 'CEDIS', 2,
       CURRENT_TIMESTAMP - INTERVAL '22 hours'
FROM operaciones.bultos b
JOIN operaciones.rutas r ON r.folio = 'R-HIST-001'
WHERE b.pedido_id = 3;

-- ----------------------------------------------------------------------------
-- RUTA DE HOY: planificada y pendiente de escaneo en andén
-- ----------------------------------------------------------------------------
UPDATE operaciones.pedidos SET estado = 'ASIGNADO' WHERE id IN (7, 8);
UPDATE operaciones.bultos  SET estado = 'ASIGNADO' WHERE pedido_id IN (7, 8);

INSERT INTO operaciones.rutas
(folio, zona, fecha, vehiculo_id, conductor_id, estado, distancia_km,
 distancia_base_km, ahorro_pct, eta_min, generada_por, generada_en)
VALUES
('R-HOY-001', 'ORIENTE', CURRENT_DATE, 2, 2, 'PLANIFICADA', 27.60,
 31.40, 12.10, 84.0, 2, CURRENT_TIMESTAMP - INTERVAL '2 hours');

INSERT INTO operaciones.ruta_paradas
(ruta_id, pedido_id, cliente_id, secuencia, latitud, longitud, distancia_km, eta_min, estado)
SELECT r.id, p.id, c.id,
       ROW_NUMBER() OVER (ORDER BY p.id),
       c.latitud, c.longitud,
       CASE p.id WHEN 7 THEN 9.40 ELSE 12.70 END,
       CASE p.id WHEN 7 THEN 33.0 ELSE 58.0 END,
       'PENDIENTE'
FROM operaciones.rutas r
JOIN operaciones.pedidos p ON p.id IN (7, 8)
JOIN operaciones.clientes c ON c.id = p.cliente_id
WHERE r.folio = 'R-HOY-001';

INSERT INTO operaciones.ruta_bultos (ruta_parada_id, bulto_id)
SELECT rp.id, b.id
FROM operaciones.ruta_paradas rp
JOIN operaciones.rutas r ON r.id = rp.ruta_id AND r.folio = 'R-HOY-001'
JOIN operaciones.bultos b ON b.pedido_id = rp.pedido_id;

INSERT INTO operaciones.eventos_rastreo (bulto_id, ruta_id, estado, descripcion, ubicacion, usuario_id, fecha)
SELECT b.id, r.id, 'ASIGNADO', 'Bulto asignado a la ruta R-HOY-001', 'CEDIS · Andén 2', 2,
       CURRENT_TIMESTAMP - INTERVAL '2 hours'
FROM operaciones.bultos b
JOIN operaciones.rutas r ON r.folio = 'R-HOY-001'
WHERE b.pedido_id IN (7, 8);

-- ----------------------------------------------------------------------------
-- BITÁCORA DEMO
-- ----------------------------------------------------------------------------
INSERT INTO seguridad.bitacora (usuario_id, usuario_nombre, rol, accion, entidad, entidad_id, detalle, fecha) VALUES
(1, 'Omar Morales', 'admin', 'RUTA_PLANIFICADA', 'ruta',
 (SELECT id::text FROM operaciones.rutas WHERE folio = 'R-HIST-001'),
 jsonb_build_object('folio', 'R-HIST-001', 'zona', 'NORTE', 'origen', 'semilla'),
 CURRENT_TIMESTAMP - INTERVAL '1 day 5 hours'),
(2, 'Laura Salinas', 'operador', 'ENTREGA_REGISTRADA', 'ruta_parada',
 (SELECT rp.id::text FROM operaciones.ruta_paradas rp JOIN operaciones.rutas r ON r.id = rp.ruta_id
  WHERE r.folio = 'R-HIST-001' AND rp.pedido_id = 1),
 jsonb_build_object('resultado', 'ENTREGADO', 'cliente', 'Distribuidora del Norte'),
 CURRENT_TIMESTAMP - INTERVAL '1 day 2 hours'),
(2, 'Laura Salinas', 'operador', 'ENTREGA_FALLIDA', 'ruta_parada',
 (SELECT rp.id::text FROM operaciones.ruta_paradas rp JOIN operaciones.rutas r ON r.id = rp.ruta_id
  WHERE r.folio = 'R-HIST-001' AND rp.pedido_id = 3),
 jsonb_build_object('motivo', 'CLIENTE_CERRADO', 'reprogramado_para', CURRENT_DATE + 1),
 CURRENT_TIMESTAMP - INTERVAL '1 day 1 hour'),
(2, 'Laura Salinas', 'operador', 'RUTA_PLANIFICADA', 'ruta',
 (SELECT id::text FROM operaciones.rutas WHERE folio = 'R-HOY-001'),
 jsonb_build_object('folio', 'R-HOY-001', 'zona', 'ORIENTE', 'origen', 'semilla'),
 CURRENT_TIMESTAMP - INTERVAL '2 hours');

COMMIT;
