# machine/dependencies.py
from microservice_chassis.db import get_session
from app.business_logic.async_machine import Machine
from sqlalchemy.ext.asyncio import AsyncSession

async def get_db() -> AsyncSession:
    async for session in get_session():
        yield session

async def get_machine() -> Machine:
    """Singleton pattern for machine instance."""
    if not hasattr(get_machine, "_instance"):
        from microservice_chassis.db import AsyncSessionLocal
        get_machine._instance = await Machine.create(AsyncSessionLocal)
    return get_machine._instance
