# -*- coding: utf-8 -*-
"""Main file to start FastAPI application."""
import logging.config
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from app.routers import main_router
from app.sql import models
from app.sql import database

# Configure logging ################################################################################
logging.config.fileConfig(os.path.join(os.path.dirname(__file__), "logging.ini"))
logger = logging.getLogger(__name__)

# OpenAPI Documentation ############################################################################
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
logger.info("Running app version %s", APP_VERSION)
DESCRIPTION = """
Microservicio de Machinees.
"""

tag_metadata = [
    {
        "name": "Machine",
        "description": "Endpoints related to machines",
    },
]



app = FastAPI(
    title="Machine Service",
    description=DESCRIPTION,
    version=APP_VERSION,
    openapi_tags=[
        {"name": "Machine", "description": "Operaciones sobre machine"},
    ],
)

# App Lifespan #####################################################################################
@app.on_event("startup")
async def on_startup():
    """Se ejecuta al iniciar la app: crea tablas si no existen."""
    logger.info("Iniciando Machine Service")
    async with database.engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)


@app.on_event("shutdown")
async def on_shutdown():
    """Se ejecuta al cerrar la app: libera recursos."""
    logger.info("Cerrando Machine Service")
    await database.engine.dispose()


#


app.include_router(main_router.router)
