from ..sql import create_piece
from .global_vars import (
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

logger = logging.getLogger(__name__)

@register_queue_handler(LISTENING_QUEUES["request_piece"])
async def request_piece(message: MessageType) -> None:
    #logger.info(f"EVENT: Piece requested --> Message: {message}")
    logger.info(
        f"EVENT: Piece requested → {message}",
        extra={"order_id": message.get("order_id")}
    )
    from ..business_logic import get_machine

    assert (order_id := message.get("order_id")), "'order_id' field should be present."
    assert (amount := message.get("amount")), "'amount' field should be present."

    order_id = int(order_id)
    amount = int(amount)

    machine = await get_machine()

    for piece_id in range(amount):
        async with SessionLocal() as db:
            await create_piece(db, piece_id, order_id)
            await db.commit()
        logger.info(
            f"Piece created (piece_id={piece_id}) for order {order_id}",
            extra={"order_id": order_id}
        )
        
        await machine.add_piece_to_queue(piece_id, order_id)

@register_queue_handler(
    queue=LISTENING_QUEUES["public_key"],
    exchange="public_key",
    exchange_type="fanout"
)
def public_key(message: MessageType) -> None:
    global PUBLIC_KEY
    assert (auth_base_url := ConsulClient(logger).get_service_url("auth")), (
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
    logger.info(f"EVENT: Public key updated: {message}")
