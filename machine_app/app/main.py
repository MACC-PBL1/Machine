import logging
from fastapi import FastAPI
from microservice_chassis.db import Base, engine
from app.routers import main_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger("machine-service")

# FastAPI app
app = FastAPI(
    title="Machine Service",
    description="Microservice for manufacturing machine pieces",
    version="1.0.0",
)

# Startup / shutdown events
@app.on_event("startup")
async def on_startup():
    logger.info("Starting Machine Service")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.on_event("shutdown")
async def on_shutdown():
    logger.info("Shutting down Machine Service")
    await engine.dispose()

app.include_router(main_router.router)
