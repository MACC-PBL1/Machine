import os
from ..business_logic import get_machine
from ..sql import create_piece
from .global_vars import (
    LISTENING_QUEUES, 
    PUBLIC_KEY_PATH
)
from chassis.messaging import (
    MessageType,
    register_queue_handler
)
from chassis.sql import SessionLocal
import logging

logger = logging.getLogger(__name__)

PUBLIC_KEY = None

@register_queue_handler(LISTENING_QUEUES["request_piece"])
async def request_piece(message: MessageType) -> None:
    assert (order_id := message.get("order_id")), "'order_id' field should be present."
    assert (amount := message.get("amount")), "'amount' field should be present."

    order_id = int(order_id)
    amount = int(amount)

    machine = await get_machine()

    for piece_id in range(amount):
        async with SessionLocal() as db:
            create_piece(db, piece_id, order_id)
        await machine.add_piece_to_queue(piece_id, order_id)

@register_queue_handler(LISTENING_QUEUES["public_key"])
async def public_key(message: MessageType) -> None:
    global PUBLIC_KEY
    
    assert (data := message.get("data")), "'data' field should be present."
    assert (new_public_key := data.get("public_key")), "'public_key' field should be present."
    
    logger.info("Received event 'client.client_public_key_queue': %s", message)
    
    PUBLIC_KEY = new_public_key
    
    os.makedirs(os.path.dirname(PUBLIC_KEY_PATH), exist_ok=True)
    with open(PUBLIC_KEY_PATH, "w") as f:
        f.write(new_public_key)