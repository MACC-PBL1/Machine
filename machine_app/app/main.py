import logging
import os
from fastapi import FastAPI
from contextlib import asynccontextmanager
from microservice_chassis.db import Base, engine
from app.routers import main_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger("machine-service")

# App Lifespan #####################################################################################
@asynccontextmanager
async def lifespan(__app: FastAPI):
    """Lifespan context manager."""
    try:
        logger.info("Starting up")
        try:
            logger.info("Creating database tables")
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

        except Exception as e:
            logger.error(
                f"Could not create tables at startup: {e} ",
                exc_info=True
            )
        yield
    finally:
        logger.info("Shutting down database")
        await engine.dispose()

# OpenAPI Documentation ############################################################################
APP_VERSION = os.getenv("APP_VERSION", "2.0.0")
logger.info("Running app version %s", APP_VERSION)
DESCRIPTION = """
Monolithic manufacturing machine application.
"""

tag_metadata = [
    {
        "name": "Machine",
        "description": "Endpoints related to machines",
    },
    {
        "name": "Piece",
        "description": "Endpoints piece information.",
    },
]

app = FastAPI(
    redoc_url=None,
    title="FastAPI - Monolithic app",
    description=DESCRIPTION,
    version=APP_VERSION,
    servers=[{"url": "/", "description": "Development"}],
    license_info={
        "name": "MIT License",
        "url": "https://choosealicense.com/licenses/mit/",
    },
    openapi_tags=tag_metadata,
    lifespan=lifespan,
)



# # FastAPI app
# app = FastAPI(
#     title="Machine Service",
#     description="Microservice for manufacturing machine pieces",
#     version="1.0.0",
# )

# # Startup / shutdown events
# @app.on_event("startup")
# async def on_startup():
#     logger.info("Starting Machine Service")
#     try:
#         async with engine.begin() as conn:
#             await conn.run_sync(Base.metadata.create_all)
#     except:
#         print("Error ")

# @app.on_event("shutdown")
# async def on_shutdown():
#     logger.info("Shutting down Machine Service")
#     await engine.dispose()

app.include_router(main_router.router)
