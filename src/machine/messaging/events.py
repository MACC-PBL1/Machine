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
import logging

logger = logging.getLogger(__name__)

@register_queue_handler(LISTENING_QUEUES["request_piece"])
async def request_piece(message: MessageType) -> None:
    logger.info(f"EVENT: Piece requested --> Message: {message}")
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
        await machine.add_piece_to_queue(piece_id, order_id)

@register_queue_handler(
    queue=LISTENING_QUEUES["public_key"],
    exchange="public_key",
    exchange_type="fanout"
)
def public_key(message: MessageType) -> None:
    logger.info(f"EVENT: Public key updated: {message}")
    global PUBLIC_KEY
    assert (public_key := message.get("public_key")) is not None, "'public_key' field should be present."
    PUBLIC_KEY["key"] = str(public_key)