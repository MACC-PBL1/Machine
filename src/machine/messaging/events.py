from ..global_vars import (
    PUBLIC_KEY,
    LISTENING_QUEUES
)
from chassis.messaging import (
    MessageType,
    register_queue_handler
)
from chassis.sql import SessionLocal
from chassis.consul import ConsulClient 
import requests
import logging
from ..sql import mark_task_cancelled

logger = logging.getLogger(__name__)



@register_queue_handler(LISTENING_QUEUES["piece_created"])
async def on_piece_created(message: MessageType) -> None:
    from ..business_logic import get_machine

    assert (piece_id := message.get("piece_id")) is not None, "'piece_id' field should be present."

    piece_id = int(piece_id)

    machine = await get_machine()

    await machine.add_piece_to_queue(piece_id=piece_id)

@register_queue_handler(LISTENING_QUEUES["machine_cancel_piece"])
async def on_machine_cancel_piece(message: MessageType) -> None:
    """
    Cancels a technical task by piece_id.
    Best-effort: WORKING tasks may finish.
    """
    assert (piece_id := message.get("piece_id")) is not None, "'piece_id' is required"
    piece_id = int(piece_id)

    logger.warning(
        "[EVENT:MACHINE:CANCEL_PIECE] - piece_id=%s",
        piece_id,
    )

    async with SessionLocal() as db:
        task = await mark_task_cancelled(db, piece_id)

    if task:
        logger.info(
            "[EVENT:MACHINE:CANCELLED] - piece_id=%s status=%s",
            piece_id,
            task.status,
        )
    else:
        logger.info(
            "[EVENT:MACHINE:CANCEL_SKIPPED] - No task found for piece_id=%s",
            piece_id,
        )


@register_queue_handler(
    queue=LISTENING_QUEUES["public_key"],
    exchange="public_key",
    exchange_type="fanout"
)
def public_key(message: MessageType) -> None:
    global PUBLIC_KEY
    assert (auth_base_url := ConsulClient(logger).get_service_url("auth")) is not None, (
        "The 'auth' service should be accesible"
    )
    assert "public_key" in message, "'public_key' field should be present."
    assert message["public_key"] == "AVAILABLE", (
        f"'public_key' value is '{message['public_key']}', expected 'AVAILABLE'"
    )
    response = requests.get(f"{auth_base_url}/auth/key", timeout=5)
    assert response.status_code == 200, (
        f"Public key request returned '{response.status_code}', should return '200'"
    )
    data: dict = response.json()
    new_key = data.get("public_key")
    assert new_key is not None, (
        "Auth response did not contain expected 'public_key' field."
    )
    PUBLIC_KEY["key"] = str(new_key)
    logger.info(
        "[EVENT:PUBLIC_KEY:UPDATED] - Public key updated: "
        f"key={PUBLIC_KEY["key"]}"
    )