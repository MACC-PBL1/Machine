from ..business_logic import get_machine
from .global_vars import LISTENING_QUEUES
from chassis.messaging import (
    MessageType,
    register_queue_handler
)

@register_queue_handler(LISTENING_QUEUES["request_piece"])
async def request_piece(message: MessageType) -> None:
    assert (order_id := message.get("order_id")), "'order_id' field should be present."
    assert (amount := message.get("amount")), "'amount' field should be present."

    order_id = int(order_id)
    amount = int(amount)

    machine = await get_machine()

    for piece_id in range(amount):
        await machine.add_piece_to_queue(piece_id, order_id)

@register_queue_handler(LISTENING_QUEUES["public_key"])
async def public_key(message: MessageType) -> None:
    pass