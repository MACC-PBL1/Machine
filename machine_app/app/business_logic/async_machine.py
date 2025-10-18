# machine/business_logic/machine.py
import asyncio
from random import randint
from sqlalchemy.ext.asyncio import AsyncSession
from microservice_chassis.db import get_element_by_id, get_list_statement_result
from microservice_chassis.utils import raise_and_log_error
from microservice_chassis.events import EventPublisher
from microservice_chassis.config import settings
from app.sql.models import Piece
import logging

logger = logging.getLogger(__name__)

class Machine:
    """Piece manufacturing machine simulator."""

    STATUS_WAITING = "Waiting"
    STATUS_CHANGING_PIECE = "Changing Piece"
    STATUS_WORKING = "Working"

    def __init__(self):
        self.status = self.STATUS_WAITING
        self.working_piece = None
        self._queue = asyncio.Queue()
        self._stop_machine = False
        self.publisher = EventPublisher(exchange=f"{settings.SERVICE_NAME}.events")
        self.publisher.connect()

    @classmethod
    async def create(cls, session_factory):
        self = Machine()
        self._session_factory = session_factory
        # Load queue from DB on startup
        await self._reload_queue_from_database()
        # Start manufacturing loop
        asyncio.create_task(self._manufacturing_loop())
        return self

    async def _reload_queue_from_database(self):
        async with self._session_factory() as db:
            # Add manufacturing piece first
            manufacturing_pieces = await get_list_statement_result(
                db, 
                db.select(Piece).where(Piece.status == Piece.STATUS_MANUFACTURING)
            )
            if manufacturing_pieces:
                await self.add_piece_to_queue(manufacturing_pieces[0])
            # Add queued pieces
            queued_pieces = await get_list_statement_result(
                db, 
                db.select(Piece).where(Piece.status == Piece.STATUS_QUEUED)
            )
            for piece in queued_pieces:
                await self.add_piece_to_queue(piece)

    async def _manufacturing_loop(self):
        while not self._stop_machine:
            if self._queue.empty():
                self.status = self.STATUS_WAITING
            piece = await self._queue.get()
            await self._process_piece(piece)
            self._queue.task_done()

    async def _process_piece(self, piece: Piece):
        async with self._session_factory() as db:
            self.working_piece = (await get_element_by_id(db, Piece, piece.id)).as_dict()
            await self._update_piece_status(db, self.working_piece["id"], Piece.STATUS_MANUFACTURING)

        self.status = self.STATUS_WORKING
        self.publisher.publish("piece.started", {"piece_id": piece.id})

        await asyncio.sleep(randint(5, 20))  # simulate manufacturing

        async with self._session_factory() as db:
            await self._update_piece_status(db, self.working_piece["id"], Piece.STATUS_MANUFACTURED)
            self.working_piece["manufacturing_date"] = db.func.now() if hasattr(db, "func") else None

        self.publisher.publish("piece.finished", {"piece_id": piece.id})
        self.status = self.STATUS_CHANGING_PIECE
        self.working_piece = None

    async def add_piece_to_queue(self, piece: Piece):
        await self._queue.put(piece)

    async def list_queued_pieces(self):
        return [p.id for p in list(self._queue._queue)]

    async def _update_piece_status(self, db: AsyncSession, piece_id: int, status: str):
        piece = await get_element_by_id(db, Piece, piece_id)
        if not piece:
            raise_and_log_error(404, f"Piece {piece_id} not found")
        piece.status = status
        await db.commit()
        await db.refresh(piece)
