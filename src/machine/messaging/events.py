from ..business_logic import get_machine
from ..global_vars import (
    MACHINE_TYPE,
    LISTENING_QUEUES,
    PUBLIC_KEY,
)
from chassis.consul import CONSUL_CLIENT 
from chassis.messaging import (
    MessageType,
    register_queue_handler
)
import requests
import logging

logger = logging.getLogger(__name__)

@register_queue_handler(
    queue=LISTENING_QUEUES[f"machine_{MACHINE_TYPE}_produce"],
    exchange="machine",
    exchange_type="topic",
    routing_key=f"machine.piece.produce.{MACHINE_TYPE}"
)
async def piece_asked(message: MessageType) -> None:
    assert (piece_id := message.get("piece_id")) is not None, "'piece_id' field should be present."
    assert (piece_type := message.get("piece_type")) is not None, "'piece_type' field should be present."

    piece_id = int(piece_id)

    logger.info(f"[EVENT:MACHINE-{MACHINE_TYPE}:PIECES_REQUESTED] - piece_id={piece_id}")

    machine = await get_machine()

    await machine.add_piece_to_queue(
        piece_id=piece_id,
        piece_type=piece_type,
    )

@register_queue_handler(
    LISTENING_QUEUES["cancel_piece"],
    exchange="machine_cancel",
    exchange_type="fanout",
)
async def cancel_piece(message: MessageType) -> None:
    assert (piece_id := message.get("piece_id")) is not None, "'piece_id' is required"

    piece_id = int(piece_id)

    machine = await get_machine()
    await machine.cancel_piece(piece_id)

@register_queue_handler(
    queue=LISTENING_QUEUES["public_key"],
    exchange="public_key",
    exchange_type="fanout"
)
def public_key(message: MessageType) -> None:
    global PUBLIC_KEY
    assert (auth_base_url := CONSUL_CLIENT.discover_service("auth")) is not None, (
        "The 'auth' service should be accesible"
    )
    assert "public_key" in message, "'public_key' field should be present."
    assert message["public_key"] == "AVAILABLE", (
        f"'public_key' value is '{message['public_key']}', expected 'AVAILABLE'"
    )
    address, port = auth_base_url
    response = requests.get(f"{address}:{port}/auth/key", timeout=5)
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