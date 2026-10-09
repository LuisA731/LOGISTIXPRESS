# Royal Press - Frontend Dashboard

Frontend del dashboard de Royal Press con HTML5, CSS3, JavaScript, Bootstrap, Bootstrap Icons y Chart.js.

## Funciones del prototipo
- Navegación funcional: Inicio, Cuentas, Movimientos, Clientes, Reportes y Configuración.
- Perfil accesible desde sidebar y barra superior.
- Notificaciones clicables.
- Buscador con respuesta al presionar Enter.
- Botones de alta, detalle, reportes y guardado con feedback.
- Gráficas interactivas.
- Diseño responsive.
- Pestaña **Exportar PDF**: elige tipo de reporte y periodo, y descarga el PDF generado por el backend.

## Ejecución
Abrir la carpeta en VS Code y usar **Open with Live Server** sobre `index.html`.

Los datos son de demostración y posteriormente pueden sustituirse por datos reales de Spring Boot/MySQL usando `fetch()`.

## Backend (FastAPI)
Ajusta `API_BASE` al inicio de `app.js`. El frontend espera:

`GET {API_BASE}/reportes/pdf?tipo=<reporte>&rol=admin|operador|auditor[&desde=YYYY-MM-DD&hasta=YYYY-MM-DD]`

- Responde `application/pdf`; `403` si el rol no puede ver ese reporte.
- Habilita CORS (`CORSMiddleware`) para el origen de Live Server.
- `desde` y `hasta` solo se envían en reportes con fecha.
- El rol del selector es solo de interfaz: el backend debe validarlo (idealmente con el token de sesión) y puede usar `SET ROLE rol_admin|rol_operador|rol_auditor` para que PostgreSQL aplique los GRANT.

## Reportes por rol (base logistixpress)
| tipo | Origen | Fechas | admin | operador | auditor |
|---|---|---|---|---|---|
| inventario | almacen.stock + productos + ubicaciones | no | ✔ | ✔ | ✔ |
| stock_bajo | almacen.stock vs productos.stock_minimo | no | ✔ | ✔ | ✔ |
| movimientos | almacen.movimientos | sí | ✔ | ✔ | ✔ |
| ruta_picking | operaciones.v_ruta_picking | no | ✔ | ✔ | ✖ |
| empaque | operaciones.empaque | sí | ✔ | ✔ | ✖ |
| embarques | operaciones.embarques | sí | ✔ | ✔ | ✖ |
| conteos | auditoria.conteos_ciclicos | sí | ✔ | ✖ | ✔ |
| rotacion | auditoria.v_metricas_rotacion | no | ✔ | ✖ | ✔ |
