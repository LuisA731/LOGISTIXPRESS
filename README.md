# Royal Express

**Royal Express** es el sistema de gestión de almacén y reparto desarrollado para **LogistiXpress**. Cubre el ciclo operativo del CEDIS: maestros, recepción, putaway, picking, empaque, control de calidad, rutas, despacho, entregas, rastreo, inventario, auditoría y reportes.

El panel y la API corren en loopback; PostgreSQL conserva el estado operativo.

## Funcionalidades

- CRUD de clientes, productos, ubicaciones, lotes, proveedores y pedidos.
- Recepción con citas/OC, lote, caducidad, condición, ubicación sugerida e incidencias con foto.
- Picking por pasillo, validación de SKU/ubicación, empaque, guías, etiquetas y aprobación de QC.
- Consolidación de rutas por zona, tipo de cliente y capacidad; mapa PNG y métricas de ahorro/ETA.
- Despacho con validación de escaneo, entrega con firma/foto y gestión de entregas fallidas.
- Rastreo por guía, inventario en vivo, traslados internos y zonas especiales.
- Conteos cíclicos, bitácora, panel gerencial y reportes PDF/XLSX.
- Tres roles: `admin`, `operador`, `auditor`; `puesto` descriptivo por usuario.

## Stack

- **Backend:** Python 3.12, FastAPI, psycopg 3, matplotlib, openpyxl.
- **Base de datos:** PostgreSQL 16 con roles y `SET LOCAL ROLE`.
- **Frontend:** SPA HTML/CSS/JS sin CDN.
- **Despliegue:** imagen OCI con Docker Compose; API y PostgreSQL publicados en `127.0.0.1`.

## Inicio rápido en Linux

Requisitos: Docker Engine con el plugin Compose, puertos `8000` y `5432` libres.

```bash
git clone https://github.com/DIAFOC/Royal-Express-.git
cd Royal-Express-
sudo docker compose down -v
sudo docker compose up --build
```

Abre `http://127.0.0.1:8000`.

> `down -v` es para la primera ejecución o cuando cambia el esquema: elimina el volumen de PostgreSQL. En ejecuciones normales use `sudo docker compose down` y luego `up`.

Cuentas iniciales:

| Rol | Usuario | Contraseña |
|---|---|---|
| Administración | `admin` | `admin123` |
| Operación | `operador` | `operador123` |
| Auditoría | `auditor` | `auditor123` |

Para ver logs:

```bash
sudo docker compose logs -f api
sudo docker compose logs -f db
```

## Inicio rápido en Windows

1. Instala **Docker Desktop** y habilita el backend **WSL 2**.
2. Abre PowerShell en la carpeta donde quieras clonar el proyecto.
3. Ejecuta:

```powershell
git clone https://github.com/DIAFOC/Royal-Express-.git
cd Royal-Express-
docker compose down -v
docker compose up --build
```

Abre `http://127.0.0.1:8000`.

> Si usas WSL 2 directamente, sigue los comandos de Linux dentro de la distribución. Docker Desktop publica el puerto en `127.0.0.1` del host.

## Desarrollo local

Requisitos: Python 3.12+, PostgreSQL 16 o Podman/Docker.

```bash
cd Royal-Express-/royal-back
./scripts/setup_project.sh
./scripts/db.sh setup
./scripts/run_api.sh
```

Si usas Docker en lugar de Podman:

```bash
PODMAN=docker ./scripts/db.sh setup
```

La API y el panel quedan en `http://127.0.0.1:8000`; la documentación interactiva en `http://127.0.0.1:8000/docs`.

## Bruno

La colección está en `bruno/Royal Express`.

1. Abre Bruno → **Open Collection** → `bruno/Royal Express`.
2. Selecciona el entorno **Dev**.
3. Ejecuta `Auth/Login`; el script guarda el token en `{{token}}`.
4. Prueba `Rutas/Generar plan`, `Rastreo/Consultar guía`, `Maestros/Clientes`, `Recepción/Ordenes de compra` y `Picking/Pedidos`.
5. Para flujos de escritura, ajusta los IDs del entorno (`rutaId`, `pedidoId`, `tareaId`) a los valores devueltos por la API.

## Documentación

- [`Manual_de_Usuario_Royal_Express.pdf`](Manual_de_Usuario_Royal_Express.pdf) — operación del panel, flujos, estados, snippets y solución de problemas.
- [`Memoria_Tecnica_Royal_Express.pdf`](Memoria_Tecnica_Royal_Express.pdf) — arquitectura, modelo de datos, MVC, algoritmos, seguridad, despliegue y validación.
- API interactiva: `http://127.0.0.1:8000/docs`.

## Estructura

```text
royal-back/       API FastAPI, repositorios, servicios, DDL, semilla y pruebas
royal-front/      dashboard SPA
bruno/            colección de peticiones
docs/             validación y fuentes de los PDF
compose.yaml      PostgreSQL + API/dashboard
```

## Pruebas

```bash
cd royal-back
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q
python scripts/validar_e2e.py
```

`validar_e2e.py` levanta un PostgreSQL embebido temporal y valida login, RBAC, maestros, recepción, picking, empaque, QC, rutas, entregas, rastreo, inventario, auditoría y reportes.

## Licencia

GNU General Public License v3.0. Consulta `LICENSE`.
