from .async_machine import Machine
from chassis.sql import SessionLocal
from typing import Optional
import logging

logger = logging.getLogger(__name__)

MY_MACHINE: Optional[Machine] = None

async def get_machine():
    """Returns the machine object (creates it the first time its executed)."""
    logger.debug("[LOG:DEPENDENCY] - Getting machine")
    global MY_MACHINE
    if MY_MACHINE is None:
        MY_MACHINE = await Machine.create(SessionLocal)
    return MY_MACHINE