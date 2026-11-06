#!/usr/bin/env python3
"""Validación end-to-end con un PostgreSQL embebido.

Uso:
    cd royal-back
    source .venv/bin/activate
    pip install -r requirements-dev.txt
    python scripts/validar_e2e.py

El script levanta PostgreSQL 18 en un directorio temporal, carga el esquema y
la semilla, ejecuta los flujos principales con el TestClient de FastAPI y
limpia todo al terminar. No toca la base de datos de desarrollo.
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
os.chdir(RAIZ)
sys.path.insert(0, str(RAIZ))

RUNTIME = Path(tempfile.mkdtemp(prefix="royal-e2e-runtime-"))
RUNTIME.chmod(0o700)
os.environ.setdefault("XDG_RUNTIME_DIR", str(RUNTIME))

import embedded_postgres.postgres_server as ps  # noqa: E402

# El directorio de runtime debe ser escribible (en sandbox /run/user no lo es).
ps.PostgresServer.runtime_path = RUNTIME
ps.PostgresServer.lock_path = RUNTIME / ".lockfile"
ps.PostgresServer._lock = ps.PostgresServer.fasteners.InterProcessLock(
    ps.PostgresServer.lock_path
)

# En entornos sin soporte de sockets UNIX (contenedores/Sandbox) se usa TCP
# en loopback. PostgreSQL se inicia en 127.0.0.1 y sin socket UNIX.
ps.platform.system = lambda: "Windows"
_original_running = ps.PostgresServer.ensure_postgres_running


def _sin_socket(self):
    with (self.pgdata / "postgresql.conf").open("a", encoding="utf-8") as fh:
        fh.write("\nunix_socket_directories = ''\n")
    return _original_running(self)


ps.PostgresServer.ensure_postgres_running = _sin_socket

PNG = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def login(client, usuario: str, contrasena: str) -> str:
    respuesta = client.post(
        "/api/auth/login", json={"usuario": usuario, "contrasena": contrasena}
    )
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()["token"]


def main() -> None:
    pgdata = Path(tempfile.mkdtemp(prefix="royal-e2e-pg-"))
    evidencias = Path(tempfile.mkdtemp(prefix="royal-e2e-ev-"))
    servidor = ps.get_server(pgdata, cleanup_mode="delete")
    try:
        servidor.psql("CREATE DATABASE logistixpress;")
        dsn = servidor.get_uri(database="logistixpress")
        os.environ["LOGISTIXPRESS_DSN"] = dsn
        os.environ["ROYAL_EVIDENCIAS_DIR"] = str(evidencias)
        os.environ["ROYAL_SECRETO"] = "e2e-secret"
        os.environ.setdefault("MPLCONFIGDIR", "/tmp/mpl")

        import psycopg
        from fastapi.testclient import TestClient

        with psycopg.connect(dsn, autocommit=True) as conexion:
            conexion.execute((RAIZ / "db/01_esquema.sql").read_text(encoding="utf-8"))
            conexion.execute((RAIZ / "db/02_semilla.sql").read_text(encoding="utf-8"))

        from app.main import app

        with TestClient(app) as client:
            assert client.get("/").status_code == 200
            assert client.get("/api/salud").json()["base_datos"] is True

            admin = login(client, "admin", "admin123")
            operador = login(client, "operador", "operador123")
            auditor = login(client, "auditor", "auditor123")

            panel = client.get("/api/panel/resumen", headers=auth(admin))
            assert panel.status_code == 200, panel.text
            print(
                f"Panel: {panel.json()['rutas_hoy']} rutas hoy · "
                f"{panel.json()['pedidos_pendientes']} pedidos pendientes"
            )

            assert client.post("/api/rutas/generar", headers=auth(auditor)).status_code == 403

            generado = client.post(
                "/api/rutas/generar?replanificar=true", headers=auth(operador)
            )
            assert generado.status_code == 200, generado.text
            plan = generado.json()
            assert plan["generado"] is True
            print(
                f"Plan: {plan['total_viajes']} viajes · {plan['total_pedidos']} pedidos · "
                f"{plan['total_bultos']} bultos · {plan['ahorro_global_pct']}% ahorro"
            )

            rutas = client.get("/api/rutas", headers=auth(operador)).json()
            ruta = next(r for r in rutas if r["estado"] == "PLANIFICADA")
            detalle = client.get(f"/api/rutas/{ruta['id']}", headers=auth(operador)).json()
            esperadas = [b["guia"] for p in detalle["paradas"] for b in p["bultos"]]

            mapa = client.get(f"/api/rutas/{ruta['id']}/mapa", headers=auth(admin))
            assert mapa.status_code == 200 and mapa.content.startswith(b"\x89PNG")
            print(f"Mapa: {len(mapa.content)} bytes")

            rechazo = client.post(
                f"/api/rutas/{ruta['id']}/despachar",
                headers=auth(operador),
                json={"guias": esperadas[:-1]},
            )
            assert rechazo.status_code == 409 and rechazo.json().get("faltantes")

            despacho = client.post(
                f"/api/rutas/{ruta['id']}/despachar",
                headers=auth(operador),
                json={"guias": esperadas},
            )
            assert despacho.status_code == 200, despacho.text
            print(f"Despacho: {despacho.json()['mensaje']}")

            detalle = client.get(f"/api/rutas/{ruta['id']}", headers=auth(operador)).json()
            parada = detalle["paradas"][0]
            guia = parada["bultos"][0]["guia"]
            entrega = client.post(
                f"/api/rutas/{ruta['id']}/paradas/{parada['id']}/entrega",
                headers=auth(operador),
                json={
                    "resultado": "ENTREGADO",
                    "recibio_nombre": "Sofía Treviño",
                    "firma_base64": PNG,
                    "foto_base64": None,
                    "motivo_fallo": None,
                    "comentario": "Entrega end-to-end",
                    "reprogramado_para": None,
                },
            )
            assert entrega.status_code == 200, entrega.text
            ruta_actual = entrega.json()["ruta"]
            parada_actual = next(p for p in ruta_actual["paradas"] if p["id"] == parada["id"])
            firma_url = parada_actual["entrega"]["firma_url"]
            evidencia = client.get(firma_url, headers=auth(auditor))
            assert evidencia.status_code == 200 and evidencia.content.startswith(b"\x89PNG")
            print(f"Entrega: {entrega.json()['mensaje']} · firma {len(evidencia.content)} bytes")

            rastreo = client.get(f"/api/rastreo/{guia}", headers=auth(auditor))
            assert rastreo.status_code == 200
            assert rastreo.json()["estado"] == "ENTREGADO"
            print(
                f"Rastreo: {rastreo.json()['guia']} · {rastreo.json()['estado']} · "
                f"{len(rastreo.json()['eventos'])} eventos"
            )

            assert client.get("/api/inventario/stock", headers=auth(auditor)).status_code == 200
            assert client.get("/api/usuarios", headers=auth(auditor)).status_code == 403
            assert client.get("/api/usuarios", headers=auth(admin)).status_code == 200
            assert client.get("/api/auditoria/bitacora", headers=auth(auditor)).status_code == 200

            stock_previo = next(
                item["stock_total"] for item in client.get(
                    "/api/inventario/stock", headers=auth(operador)
                ).json() if item["producto_id"] == 1
            )
            movimiento = client.post(
                "/api/inventario/movimientos",
                headers=auth(operador),
                json={"producto_id": 1, "ubicacion_id": 1, "tipo": "ENTRADA", "cantidad": 5},
            )
            assert movimiento.status_code == 200, movimiento.text
            movimiento_id = movimiento.json()["id"]
            stock_nuevo = next(
                item["stock_total"] for item in client.get(
                    "/api/inventario/stock", headers=auth(operador)
                ).json() if item["producto_id"] == 1
            )
            assert stock_nuevo == stock_previo + 5, (stock_previo, stock_nuevo)
            movimientos = client.get(
                "/api/inventario/movimientos?limite=10", headers=auth(operador)
            ).json()
            assert any(item["id"] == movimiento_id for item in movimientos)
            assert client.post(
                "/api/inventario/movimientos",
                headers=auth(auditor),
                json={"producto_id": 1, "ubicacion_id": 1, "tipo": "ENTRADA", "cantidad": 1},
            ).status_code == 403
            conteo = client.post(
                "/api/auditoria/conteos",
                headers=auth(auditor),
                json={"producto_id": 1, "ubicacion_id": 1, "cantidad_fisica": 100},
            )
            assert conteo.status_code == 201, conteo.text
            print(
                f"Inventario y conteo cíclico OK · stock {stock_previo}→{stock_nuevo} "
                f"· movimiento #{movimiento_id} visible en el historial"
            )

            pdf = client.get(
                "/api/reportes/exportar?tipo=rutas&formato=pdf", headers=auth(admin)
            )
            xlsx = client.get(
                "/api/reportes/exportar?tipo=inventario&formato=xlsx",
                headers=auth(auditor),
            )
            pdf_movimientos = client.get(
                "/api/reportes/exportar?tipo=movimientos&formato=pdf",
                headers=auth(auditor),
            )
            assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
            assert xlsx.status_code == 200 and xlsx.content.startswith(b"PK")
            assert pdf_movimientos.status_code == 200
            assert pdf_movimientos.content.startswith(b"%PDF")
            print(
                f"Reportes: rutas PDF {len(pdf.content)} bytes · inventario XLSX "
                f"{len(xlsx.content)} bytes · movimientos PDF {len(pdf_movimientos.content)} bytes"
            )

            # ================================================================
            # CRUD de maestros, recepción, picking/packing y QC
            # ================================================================
            hoy = date.today()
            caducidad = (hoy + timedelta(days=220)).isoformat()

            cliente = client.post(
                "/api/maestros/clientes",
                headers=auth(operador),
                json={
                    "codigo": "CD-E2E-001", "nombre": "Cliente E2E",
                    "tipo_cliente": "MINORISTA", "zona": "NORTE",
                    "direccion": "Calle E2E 100", "colonia": "Centro",
                    "telefono": "81 0000 0000", "contacto": "Prueba E2E",
                    "latitud": 25.72, "longitud": -100.30,
                },
            )
            assert cliente.status_code == 201, cliente.text
            cliente = cliente.json()
            actualizado = client.patch(
                f"/api/maestros/clientes/{cliente['id']}",
                headers=auth(operador), json={"nombre": "Cliente E2E Actualizado"},
            )
            assert actualizado.status_code == 200
            assert actualizado.json()["nombre"] == "Cliente E2E Actualizado"

            assert client.post(
                "/api/maestros/productos",
                headers=auth(operador),
                json={"sku": "NO-PERM", "nombre": "No permitido", "peso_kg": 1,
                      "volumen_m3": 0.01},
            ).status_code == 403
            producto = client.post(
                "/api/maestros/productos",
                headers=auth(admin),
                json={"sku": "E2E-01", "nombre": "Producto E2E", "stock_minimo": 4,
                      "peso_kg": 3.5, "volumen_m3": 0.02},
            )
            assert producto.status_code == 201, producto.text
            producto = producto.json()
            assert client.patch(
                f"/api/maestros/productos/{producto['id']}",
                headers=auth(admin), json={"nombre": "Producto E2E editado", "stock_minimo": 6},
            ).status_code == 200

            ubicacion = client.post(
                "/api/maestros/ubicaciones",
                headers=auth(admin),
                json={"codigo": "E2E-01-1", "pasillo": "E", "rack": "01",
                      "nivel": 1, "orden_picking": 999, "tipo_zona": "GENERAL"},
            )
            assert ubicacion.status_code == 201, ubicacion.text
            ubicacion = ubicacion.json()
            assert client.patch(
                f"/api/maestros/ubicaciones/{ubicacion['id']}",
                headers=auth(admin), json={"orden_picking": 998},
            ).status_code == 200

            proveedor = client.post(
                "/api/maestros/proveedores",
                headers=auth(operador),
                json={"codigo": "PROV-E2E", "nombre": "Proveedor E2E",
                      "contacto": "Compras", "telefono": "81 1111 1111",
                      "correo": "compras@e2e.mx"},
            )
            assert proveedor.status_code == 201, proveedor.text
            proveedor = proveedor.json()
            assert client.patch(
                f"/api/maestros/proveedores/{proveedor['id']}",
                headers=auth(operador), json={"contacto": "Compras E2E"},
            ).status_code == 200

            lote = client.post(
                "/api/maestros/lotes",
                headers=auth(operador),
                json={"producto_id": 2, "ubicacion_id": 3, "lote": "ACE-E2E-LOTE",
                      "caducidad": caducidad, "cantidad": 5, "condicion": "BUENO"},
            )
            assert lote.status_code == 201, lote.text

            pedido = client.post(
                "/api/maestros/pedidos",
                headers=auth(operador),
                json={
                    "cliente_id": cliente["id"], "prioridad": "ALTA",
                    "fecha_compromiso": (hoy + timedelta(days=2)).isoformat(),
                    "observaciones": "Pedido E2E de picking",
                    "lineas": [
                        {"producto_id": 2, "cantidad": 1},
                        {"producto_id": 5, "cantidad": 1},
                    ],
                },
            )
            assert pedido.status_code == 201, pedido.text
            pedido = pedido.json()
            assert pedido["estado"] == "BORRADOR" and len(pedido["lineas"]) == 2
            print(f"CRUD maestros OK · cliente {cliente['id']} · pedido {pedido['folio']}")

            # Recepción con lote y actualización de stock.
            oc = client.post(
                "/api/recepcion/ordenes",
                headers=auth(operador),
                json={
                    "proveedor_id": proveedor["id"], "fecha_esperada": hoy.isoformat(),
                    "hora_estimada": "14:00", "anden": "T-1",
                    "observaciones": "OC E2E",
                    "lineas": [{"producto_id": 2, "cantidad_solicitada": 10}],
                },
            )
            assert oc.status_code == 201, oc.text
            oc = oc.json()
            sugerida = client.get(
                "/api/recepcion/sugerir-ubicacion?producto_id=2", headers=auth(operador)
            )
            assert sugerida.status_code == 200, sugerida.text
            sugerida = sugerida.json()
            stock_antes = next(
                item["stock_total"] for item in client.get(
                    "/api/inventario/stock", headers=auth(operador)
                ).json() if item["producto_id"] == 2
            )
            recepcion = client.post(
                f"/api/recepcion/ordenes/{oc['id']}/recibir",
                headers=auth(operador),
                json={
                    "observaciones": "Recepción E2E",
                    "lineas": [{
                        "linea_id": oc["lineas"][0]["id"], "cantidad_recibida": 10,
                        "lote": "ACE-E2E-01", "caducidad": caducidad,
                        "condicion": "BUENO", "ubicacion_id": sugerida["id"],
                    }],
                },
            )
            assert recepcion.status_code == 200, recepcion.text
            stock_despues = next(
                item["stock_total"] for item in client.get(
                    "/api/inventario/stock", headers=auth(operador)
                ).json() if item["producto_id"] == 2
            )
            assert stock_despues == stock_antes + 10, (stock_antes, stock_despues)
            oc_recibida = client.get(
                f"/api/recepcion/ordenes/{oc['id']}", headers=auth(admin)
            ).json()
            assert oc_recibida["estado"] == "RECIBIDA"
            assert oc_recibida["total_recibido"] == 10
            assert any(
                item["lote"] == "ACE-E2E-01" for item in client.get(
                    "/api/maestros/lotes", headers=auth(admin)
                ).json()
            )
            print(
                f"Recepción OK · {oc['folio']} · stock producto 2 {stock_antes}→{stock_despues}"
            )

            # Recepción con daño, incidencia y fotografía.
            oc_danada = client.post(
                "/api/recepcion/ordenes",
                headers=auth(operador),
                json={
                    "proveedor_id": proveedor["id"], "fecha_esperada": hoy.isoformat(),
                    "hora_estimada": "15:00", "anden": "T-2",
                    "lineas": [{"producto_id": 4, "cantidad_solicitada": 5}],
                },
            )
            assert oc_danada.status_code == 201, oc_danada.text
            oc_danada = oc_danada.json()
            ubicaciones_maestras = client.get(
                "/api/maestros/ubicaciones", headers=auth(admin)
            ).json()
            ubicacion_danados = next(
                u for u in ubicaciones_maestras if u["tipo_zona"] == "DANADOS"
            )
            recepcion_danada = client.post(
                f"/api/recepcion/ordenes/{oc_danada['id']}/recibir",
                headers=auth(operador),
                json={
                    "lineas": [{
                        "linea_id": oc_danada["lineas"][0]["id"],
                        "cantidad_recibida": 5, "lote": "AGU-E2E-DAN",
                        "caducidad": caducidad, "condicion": "DANADO",
                        "ubicacion_id": ubicacion_danados["id"],
                    }],
                    "incidencia": {
                        "descripcion": "Caja rota E2E", "producto_id": 4,
                        "comentario": "Evidencia de recepción", "foto_base64": PNG,
                    },
                },
            )
            assert recepcion_danada.status_code == 200, recepcion_danada.text
            assert oc_danada["id"] != oc["id"]
            incidencias = client.get(
                "/api/recepcion/incidencias", headers=auth(auditor)
            ).json()
            incidencia = next(
                item for item in incidencias if item["orden_folio"] == oc_danada["folio"]
            )
            assert incidencia["foto_url"]
            foto = client.get(incidencia["foto_url"], headers=auth(auditor))
            assert foto.status_code == 200 and foto.content.startswith(b"\x89PNG")
            assert client.post(
                "/api/recepcion/ordenes",
                headers=auth(auditor),
                json={"proveedor_id": proveedor["id"], "fecha_esperada": hoy.isoformat(),
                      "lineas": [{"producto_id": 2, "cantidad_solicitada": 1}]},
            ).status_code == 403
            print(f"Incidencia de recepción OK · {incidencia['foto_url']}")

            # Ola de picking multi-pedido: incluye el pedido E2E y el pedido semilla BORRADOR.
            ola = client.post("/api/picking/generar", headers=auth(operador), json={})
            assert ola.status_code == 200, ola.text
            ola = ola.json()
            assert ola["pedidos"] >= 2 and ola["tareas"] >= 4, ola
            assert client.post(
                "/api/picking/generar", headers=auth(auditor), json={}
            ).status_code == 403
            picking_pedidos = client.get(
                "/api/picking/pedidos", headers=auth(operador)
            ).json()
            mi_pedido = next(p for p in picking_pedidos if p["id"] == pedido["id"])
            assert mi_pedido["estado"] == "EN_PICKING"
            tareas = mi_pedido["tareas"]
            assert len(tareas) == 2
            error_sku = client.post(
                f"/api/picking/tareas/{tareas[0]['id']}/confirmar",
                headers=auth(operador), json={"sku": "SKU-INCORRECTO"},
            )
            assert error_sku.status_code == 409, error_sku.text
            for tarea in tareas:
                confirmada = client.post(
                    f"/api/picking/tareas/{tarea['id']}/confirmar",
                    headers=auth(operador),
                    json={"sku": tarea["sku"], "ubicacion": tarea["ubicacion"]},
                )
                assert confirmada.status_code == 200, confirmada.text
            mi_pedido = client.get(
                f"/api/picking/pedidos/{pedido['id']}", headers=auth(operador)
            ).json()
            assert mi_pedido["estado"] == "PICKING_COMPLETO", mi_pedido
            assert client.post(
                f"/api/picking/tareas/{tareas[0]['id']}/confirmar",
                headers=auth(auditor), json={},
            ).status_code == 403
            empaque = client.post(
                f"/api/picking/pedidos/{pedido['id']}/empacar", headers=auth(operador)
            )
            assert empaque.status_code == 200, empaque.text
            empaque = empaque.json()
            assert empaque["estado"] == "EMPACADO" and len(empaque["bultos"]) == 2
            assert empaque["empaque"]["estado"] == "EN_PROCESO"
            panel_empaque = client.get(
                "/api/panel/resumen", headers=auth(admin)
            ).json()
            assert panel_empaque["pedidos_en_empaque"] >= 1
            aprobado = client.post(
                f"/api/picking/pedidos/{pedido['id']}/aprobar", headers=auth(operador)
            )
            assert aprobado.status_code == 200, aprobado.text
            aprobado = aprobado.json()
            assert aprobado["estado"] == "LISTO", aprobado
            assert aprobado["empaque"]["estado"] == "VALIDADO"
            assert len(aprobado["bultos"]) == 2
            print(
                f"Picking/empaque/QC OK · ola {ola['folio']} · "
                f"pedido {pedido['folio']} · bultos {len(aprobado['bultos'])}"
            )

            # El pedido recién empacado debe entrar al plan de rutas.
            nuevo_plan = client.post(
                "/api/rutas/generar?replanificar=false", headers=auth(admin)
            )
            assert nuevo_plan.status_code == 200, nuevo_plan.text
            nuevo_plan = nuevo_plan.json()
            assert nuevo_plan["generado"] is True
            assert nuevo_plan["total_pedidos"] == 1, nuevo_plan
            detalle_nuevo = client.get(
                f"/api/rutas/{nuevo_plan['viajes'][0]['id']}", headers=auth(admin)
            ).json()
            assert any(
                parada["pedido_folio"] == pedido["folio"]
                for parada in detalle_nuevo["paradas"]
            )
            print(f"Pedido empacado enviado a ruta · {detalle_nuevo['folio']}")

            # Traslado interno: origen → destino, sin cambiar el stock total.
            stock_antes_traslado = next(
                item["stock_total"] for item in client.get(
                    "/api/inventario/stock", headers=auth(operador)
                ).json() if item["producto_id"] == 2
            )
            traslado = client.post(
                "/api/inventario/traslados",
                headers=auth(operador),
                json={"producto_id": 2, "cantidad": 1, "ubicacion_origen_id": 3,
                      "ubicacion_destino_id": ubicacion["id"],
                      "comentario": "Traslado E2E"},
            )
            assert traslado.status_code == 201, traslado.text
            stock_despues_traslado = next(
                item["stock_total"] for item in client.get(
                    "/api/inventario/stock", headers=auth(operador)
                ).json() if item["producto_id"] == 2
            )
            assert stock_despues_traslado == stock_antes_traslado
            assert client.get(
                "/api/inventario/traslados", headers=auth(admin)
            ).json()
            assert client.post(
                "/api/inventario/traslados",
                headers=auth(operador),
                json={"producto_id": 2, "cantidad": 5000,
                      "ubicacion_origen_id": 3, "ubicacion_destino_id": ubicacion["id"]},
            ).status_code == 409
            print(f"Traslado interno OK · stock total {stock_antes_traslado}→{stock_despues_traslado}")

            # Edición de flota y usuarios.
            vehiculo = client.patch(
                "/api/flota/vehiculos/1", headers=auth(admin),
                json={"modelo": "Nissan NP300 · E2E", "capacidad_kg": 1250,
                      "activo": True},
            )
            assert vehiculo.status_code == 200, vehiculo.text
            conductor = client.patch(
                "/api/flota/conductores/1", headers=auth(admin),
                json={"telefono": "81 9999 0000", "activo": True},
            )
            assert conductor.status_code == 200, conductor.text
            usuario_qa = client.post(
                "/api/usuarios", headers=auth(admin),
                json={"nombre": "QA Auditor", "usuario": "qa.auditor",
                      "correo": "qa.auditor@logistixpress.mx",
                      "contrasena": "qa123456", "rol": "auditor"},
            )
            assert usuario_qa.status_code == 201, usuario_qa.text
            usuario_qa = usuario_qa.json()
            editado = client.patch(
                f"/api/usuarios/{usuario_qa['id']}", headers=auth(admin),
                json={"nombre": "QA Auditor Editado", "correo": "qa.editado@logistixpress.mx"},
            )
            assert editado.status_code == 200 and editado.json()["nombre"] == "QA Auditor Editado"
            assert client.patch(
                f"/api/usuarios/{usuario_qa['id']}", headers=auth(operador),
                json={"nombre": "No permitido"},
            ).status_code == 403
            print("Edición de flota/usuarios OK")

            # Panel final con métricas de almacén.
            panel_final = client.get("/api/panel/resumen", headers=auth(admin)).json()
            assert panel_final["pedidos_en_picking"] >= 1
            assert panel_final["tareas_picking_pendientes"] >= 1
            assert panel_final["recepciones_hoy"] >= 2
            assert panel_final["incidencias_hoy"] >= 1
            assert panel_final["mermas_hoy"] > 0
            assert panel_final["productividad_hoy"], panel_final
            assert client.get("/api/recepcion/ordenes", headers=auth(auditor)).status_code == 200
            assert client.get("/api/picking/pedidos", headers=auth(auditor)).status_code == 200
            print(
                "Panel extendido OK · picking "
                f"{panel_final['pedidos_en_picking']} · empaque "
                f"{panel_final['pedidos_en_empaque']} · mermas {panel_final['mermas_hoy']} "
                f"· productividad {len(panel_final['productividad_hoy'])}"
            )

            print(
                "\nE2E OK: login, RBAC, plan, mapa, despacho, entrega, rastreo, "
                "inventario, auditoría, reportes, CRUD de maestros, recepción, "
                "picking/packing/QC y traslados."
            )
    finally:
        servidor.cleanup()
        shutil.rmtree(evidencias, ignore_errors=True)
        shutil.rmtree(RUNTIME, ignore_errors=True)


if __name__ == "__main__":
    main()
