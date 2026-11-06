"""Aplicación FastAPI de LogistiXpress."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from psycopg import Error as ErrorPostgres
from psycopg_pool import PoolTimeout

from .config import DIRECTORIO_FRONTEND, ajustes
from .dependencias import obtener_bd
from .errores import ErrorNegocio
from .routers import (
    auditoria,
    auth,
    entregas,
    flota,
    inventario,
    maestros,
    panel,
    picking,
    rastreo,
    recepcion,
    reportes,
    rutas,
    usuarios,
)

logger = logging.getLogger("logistixpress")


@asynccontextmanager
async def ciclo_vida(app: FastAPI):
    ajustes.directorio_evidencias.mkdir(parents=True, exist_ok=True)
    bd = obtener_bd()
    if bd.ping():
        logger.info("Conexión con PostgreSQL verificada.")
    else:
        logger.warning("PostgreSQL no disponible al iniciar; la API responderá 503.")
    try:
        yield
    finally:
        bd.cerrar()


def crear_app() -> FastAPI:
    app = FastAPI(
        title="LogistiXpress API",
        version=ajustes.version,
        description=(
            "WMS y centro de distribución Royal Express. "
            "Autenticación por token, RBAC de tres roles y módulo de rutas, "
            "despacho, evidencia digital y rastreo de paquetes."
        ),
        lifespan=ciclo_vida,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    prefijo = "/api"
    for modulo in (
        auth, panel, rutas, entregas, rastreo, recepcion, picking, inventario,
        maestros, flota, usuarios, auditoria, reportes,
    ):
        app.include_router(modulo.router, prefix=prefijo)

    @app.get("/api/salud", tags=["Salud"], summary="Estado de la API y la base")
    def salud() -> dict:
        return {
            "estado": "ok",
            "version": ajustes.version,
            "base_datos": obtener_bd().ping(),
        }

    @app.exception_handler(ErrorNegocio)
    async def manejar_error_negocio(request: Request, exc: ErrorNegocio):
        contenido = {"detail": exc.mensaje}
        contenido.update(exc.extra)
        return JSONResponse(status_code=exc.codigo, content=contenido)

    @app.exception_handler(PoolTimeout)
    async def manejar_pool_timeout(request: Request, exc: PoolTimeout):
        logger.exception("Timeout del pool de PostgreSQL")
        return JSONResponse(
            status_code=503,
            content={
                "detail": "La base de datos no respondió. "
                          "Verifica que PostgreSQL esté en ejecución."
            },
        )

    @app.exception_handler(ErrorPostgres)
    async def manejar_error_postgres(request: Request, exc: ErrorPostgres):
        logger.exception("Error de PostgreSQL")
        return JSONResponse(
            status_code=503,
            content={
                "detail": "No se pudo completar la operación contra PostgreSQL. "
                          "Revisa la conexión y los permisos del rol."
            },
        )

    if DIRECTORIO_FRONTEND.exists():
        app.mount(
            "/",
            StaticFiles(directory=str(DIRECTORIO_FRONTEND), html=True),
            name="frontend",
        )
    else:
        logger.warning("No se encontró el frontend en %s", DIRECTORIO_FRONTEND)

    return app


app = crear_app()
