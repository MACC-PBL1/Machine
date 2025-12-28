from ..business_logic import (
    get_machine,
    Machine,
)

from ..global_vars import (
    RABBITMQ_CONFIG,
    PUBLIC_KEY,
)

from ..sql import (
    Message,
)
from ..sql.models import MachineTaskModel


from chassis.messaging import is_rabbitmq_healthy
from chassis.routers import (
    get_system_metrics,
    raise_and_log_error,
)
from chassis.security import create_jwt_verifier
from chassis.sql import (
    get_db,
    get_list,
)

from fastapi import (
    APIRouter,
    Depends,
    status,
)

from sqlalchemy.ext.asyncio import AsyncSession

import logging
import socket


logger = logging.getLogger(__name__)

Router = APIRouter(prefix="/machine", tags=["Machine"])

# ------------------------------------------------------------------------------------
# Health check
# ------------------------------------------------------------------------------------
@Router.get(
    "/health",
    summary="Health check endpoint",
    response_model=Message,
)
async def health_check():
    if not is_rabbitmq_healthy(RABBITMQ_CONFIG):
        raise_and_log_error(
            logger=logger,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message="[LOG:REST] - RabbitMQ not reachable"
        )

    container_id = socket.gethostname()
    logger.debug(f"[LOG:REST] - GET '/health' served by {container_id}")
    return {
        "detail": f"OK - Served by {container_id}",
        "system_metrics": get_system_metrics()
    }

@Router.get(
    "/health/auth",
    summary="Health check endpoint (JWT protected)",
    response_model=Message
)
async def health_check_auth(
    token_data: dict = Depends(create_jwt_verifier(lambda: PUBLIC_KEY["key"], logger))
):
    logger.debug("[LOG:REST] - GET '/health/auth' endpoint called.")

    user_id = token_data.get("sub")
    user_role = token_data.get("role")

    logger.info(f"[LOG:REST] - Valid JWT: user_id={user_id}, role={user_role}")

    return {
        "detail": f"Auth service is running. Authenticated as (id={user_id}, role={user_role})",
        "system_metrics": get_system_metrics()
    }

# ------------------------------------------------------------------
# Estado técnico de la máquina
# ------------------------------------------------------------------
@Router.get(
    "/status",
    summary="Machine technical status",
)
async def get_machine_status(machine: Machine = Depends(get_machine)):
    return {
        "status": machine.status,
        "working_piece_id": machine.working_piece,
        "queue_size": machine._queue.qsize(),
        "queued_piece_ids": await machine.list_queued_pieces(),
    }

# ------------------------------------------------------------------
# Historial de piezas ejecutadas
# ------------------------------------------------------------------
@Router.get(
    "/tasks",
    summary="List machine tasks"
)
async def list_machine_tasks(
    db: AsyncSession = Depends(get_db),
):
    return await get_list(db, MachineTaskModel)
