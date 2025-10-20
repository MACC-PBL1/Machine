import asyncio
from random import randint
from sqlalchemy.ext.asyncio import AsyncSession
from microservice_chassis.db import get_element_by_id, get_list_statement_result
from microservice_chassis.utils import raise_and_log_error
from microservice_chassis.events import EventPublisher, EventSubscriber
from microservice_chassis.config import settings
from microservice_chassis.utils import time_utils
from app.sql.models import Piece
import logging

logger = logging.getLogger(__name__)

class Machine:
    STATUS_WAITING = "Waiting"
    STATUS_CHANGING_PIECE = "Changing Piece"
    STATUS_WORKING = "Working"

    def __init__(self):
        self.status = self.STATUS_WAITING
        self.working_piece = None
        self._queue = asyncio.Queue()
        self._stop_machine = False
        self.publisher = EventPublisher(exchange=f"{settings.SERVICE_NAME}.events")
        self.subscriber = EventSubscriber(exchange=f"{settings.SERVICE_NAME}.events")

    @classmethod
    async def create(cls, session_factory):
        self = Machine()
        self._session_factory = session_factory
        self.publisher.connect()
        await self._reload_queue_from_database()
        asyncio.create_task(self._manufacturing_loop())
        asyncio.create_task(self._listen_to_requests())
        return self

    async def _listen_to_requests(self):
        async for event in self.subscriber.listen("machine.request_piece"):
            order_id = event.get("order_id")
            amount = event.get("piece_amount", 1)
            logger.info(f"Recibida solicitud para fabricar {amount} piezas del pedido {order_id}")
            async with self._session_factory() as db:
                for _ in range(amount):
                    new_piece = Piece(order_id=order_id, status=Piece.STATUS_QUEUED)
                    db.add(new_piece)
                    await db.commit()
                    await db.refresh(new_piece)
                    await self.add_piece_to_queue(new_piece)

    async def _reload_queue_from_database(self):
        async with self._session_factory() as db:
            manufacturing = await get_list_statement_result(
                db, db.select(Piece).where(Piece.status == Piece.STATUS_MANUFACTURING)
            )
            for p in manufacturing:
                await self.add_piece_to_queue(p)
            queued = await get_list_statement_result(
                db, db.select(Piece).where(Piece.status == Piece.STATUS_QUEUED)
            )
            for p in queued:
                await self.add_piece_to_queue(p)

    async def _manufacturing_loop(self):
        while not self._stop_machine:
            if self._queue.empty():
                self.status = self.STATUS_WAITING
                await asyncio.sleep(1)
                continue
            piece = await self._queue.get()
            await self._process_piece(piece)
            self._queue.task_done()

    async def _process_piece(self, piece: Piece):
        async with self._session_factory() as db:
            piece_db = await get_element_by_id(db, Piece, piece.id)
            await self._update_piece_status(db, piece_db.id, Piece.STATUS_MANUFACTURING)
            self.working_piece = piece_db.as_dict()

        self.status = self.STATUS_WORKING
        await asyncio.sleep(randint(5, 20))  # simulación

        async with self._session_factory() as db:
            await self._update_piece_status(db, piece_db.id, Piece.STATUS_MANUFACTURED)
        
        self.publisher.publish(
            "machine.confirmation_piece",
            {"order_id": piece_db.order_id, "piece_id": piece_db.id}
        )
        self.working_piece = None
        self.status = self.STATUS_CHANGING_PIECE

    async def add_piece_to_queue(self, piece: Piece):
        await self._queue.put(piece)

    async def list_queued_pieces(self):
        return [p.id for p in list(self._queue._queue)]

    async def _update_piece_status(self, db: AsyncSession, piece_id: int, status: str):
        piece = await get_element_by_id(db, Piece, piece_id)
        if not piece:
            raise_and_log_error(404, f"Piece {piece_id} not found")
        piece.manufacturing_date = time_utils.utcnow()
        piece.status = status
        await db.commit()
        await db.refresh(piece)
