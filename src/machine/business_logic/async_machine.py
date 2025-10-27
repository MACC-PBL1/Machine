# -*- coding: utf-8 -*-
"""Simulation of a machine that manufactures pieces."""
from ..messaging import (
    PUBLISHING_QUEUES,
    RABBITMQ_CONFIG,
)
from ..sql import (
    get_piece,
    get_piece_list_by_order,
    get_piece_list_by_status,
    PieceModel,
    update_piece_manufacturing_date_to_now,
    update_piece_status,
)
from chassis.messaging import RabbitMQPublisher
from random import randint
from sqlalchemy.exc import (
    ProgrammingError, 
    OperationalError
)
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)
from typing import (
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
)
import asyncio
import logging

logger = logging.getLogger(__name__)
logger.debug("Machine logger set.")

MachineType = TypeVar("MachineType", bound="Machine")

class Machine:
    """Piece manufacturing machine simulator."""
    STATUS_WAITING = "Waiting"
    STATUS_CHANGING_PIECE = "Changing Piece"
    STATUS_WORKING = "Working"
    __manufacturing_queue: asyncio.Queue[Tuple[int, int]] = asyncio.Queue()
    __stop_machine = False
    working_piece = None
    status = STATUS_WAITING

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        # Session factory is injected to reduce coupling/dependencies
        self._session_factory = session_factory

    @classmethod
    async def create(
        cls: Type[MachineType], 
        session_factory: async_sessionmaker[AsyncSession],
    ) -> MachineType:
        """Machine constructor: loads manufacturing/queued pieces and starts simulation."""
        logger.info("AsyncMachine initialized")
        self = cls(session_factory)
        asyncio.create_task(self._manufacturing_coroutine())
        await self._reload_queue_from_database()
        return self

    async def _reload_queue_from_database(self):
        """Reload queue from database, to reload data when the system has been rebooted."""
        # Load the piece that was being manufactured
        async with self._session_factory() as db:
            manufacturing_piece = await Machine._get_manufacturing_piece(db)
            if manufacturing_piece is not None:
                await self.add_piece_to_queue(
                    piece_id=manufacturing_piece.id,
                    order_id=manufacturing_piece.order_id,
                )

            # Load the pieces that were in the queue
            queued_pieces = await Machine._get_queued_pieces(db)

            if queued_pieces:
                await self.add_pieces_to_queue(queued_pieces)
            await db.close()

    @staticmethod
    async def _get_manufacturing_piece(db: AsyncSession):
        """Gets the manufacturing piece from the database."""
        try:
            manufacturing_pieces = await get_piece_list_by_status(
                db,
                PieceModel.STATUS_MANUFACTURING
            )
            if manufacturing_pieces and manufacturing_pieces[0]:
                return manufacturing_pieces[0]
        except (ProgrammingError, OperationalError):
            logger.error(
                "Error getting Manufacturing Piece at startup. It may be the first execution"
            )
        return None

    @staticmethod
    async def _get_queued_pieces(db: AsyncSession):
        """Get all queued pieces from the database."""
        try:
            queued_pieces = await get_piece_list_by_status(db, PieceModel.STATUS_QUEUED)
            return queued_pieces
        except (ProgrammingError, OperationalError):
            logger.error("Error getting Queued Pieces at startup. It may be the first execution")
            return []

    async def _manufacturing_coroutine(self) -> None:
        """Coroutine that manufactures queued pieces one by one."""
        logger.debug("Entered manufacturing coroutine.")
        while not self.__stop_machine:
            if self.__manufacturing_queue.empty():
                self.status = self.STATUS_WAITING
            (piece_id, order_id) = await self.__manufacturing_queue.get()
            await self._create_piece(piece_id, order_id)
            self.__manufacturing_queue.task_done()

    async def _create_piece(
        self, 
        piece_id: int,
        order_id: int,
    ) -> None:
        """Simulates piece manufacturing."""
        # Machine and piece status updated during manufacturing
        logger.debug(f"Creating piece '{piece_id}' from order_id '{order_id}'")
        async with self._session_factory() as db:
            await self._update_working_piece(piece_id, order_id, db)
            await self._working_piece_to_manufacturing(db)  # Update Machine&piece status
            await db.close()

        await asyncio.sleep(randint(5, 20))  # Simulates time spent manufacturing

        async with self._session_factory() as db:
            await self._working_piece_to_finished(db)  # Update Machine&Piece status
            await db.close()

        self.working_piece = None

    async def _update_working_piece(
        self, 
        piece_id: int,
        order_id: int,
        db: AsyncSession
    ) -> None:
        """Loads a piece for the given id and updates the working piece."""
        logger.debug("Updating working piece to %i", piece_id)
        assert (piece := await get_piece(db, piece_id, order_id)) is not None, "Piece should exist."
        self.working_piece = piece.as_dict()

    async def _working_piece_to_manufacturing(
        self, 
        db: AsyncSession
    ) -> None:
        """Updates piece status to manufacturing."""
        assert self.working_piece is not None, "Current working piece should be set"
        self.status = Machine.STATUS_WORKING
        try:
            await update_piece_status(
                db=db, 
                piece_id=self.working_piece['id'],
                order_id=self.working_piece["order_id"],
                status=PieceModel.STATUS_MANUFACTURING
            )
        except Exception as exc:
            logger.error(f"Could not update working piece status to manufacturing: {exc}")

    async def _working_piece_to_finished(
        self, 
        db: AsyncSession
    ) -> None:
        """Updates piece status to finished and order if all pieces are finished."""
        global RABBITMQ_CONFIG
        logger.debug("Working piece finished.")
        assert self.working_piece is not None, "Current working piece should be known."
        self.status = Machine.STATUS_CHANGING_PIECE

        assert (piece := await update_piece_status(
            db=db,
            piece_id=self.working_piece['id'],
            order_id=self.working_piece["order_id"],
            status=PieceModel.STATUS_MANUFACTURED
        )), "The piece should exist in the database if it is trying to update."
        self.working_piece = piece.as_dict()

        assert (piece := await update_piece_manufacturing_date_to_now(
            db,
            piece_id=self.working_piece['id'],
            order_id=self.working_piece["order_id"],
        )), "The piece should exist in the database if it is trying to update."
        self.working_piece = piece.as_dict()

        with RabbitMQPublisher(
            queue=PUBLISHING_QUEUES["confirmation"],
            rabbitmq_config=RABBITMQ_CONFIG,
        ) as publisher:
            data = {
                "order_id": self.working_piece["order_id"],
                "piece_id": self.working_piece["piece_id"],
            }
            publisher.publish(data)
            logger.info(f"COMMAND: Confirm piece creation --> {data}")

    @staticmethod
    async def _is_order_finished(
        order_id: int, 
        db: AsyncSession
    ) -> Optional[bool]:
        """Return whether an order is finished or not."""
        order_pieces = await get_piece_list_by_order(db, order_id)
        if len(order_pieces) == 0:
            return None
        for piece in order_pieces:
            if piece.status != PieceModel.STATUS_MANUFACTURED:
                return False
        return True

    async def add_pieces_to_queue(
        self, 
        pieces: List[PieceModel]
    ) -> None:
        """Adds a list of pieces to the queue and updates their status."""
        logger.debug("Adding %i pieces to queue", len(pieces))
        for piece in pieces:
            await self.add_piece_to_queue(
                piece_id=piece.id,
                order_id=piece.order_id,
            )

    async def add_piece_to_queue(
        self, 
        piece_id: int,
        order_id: int,
    ) -> None:
        """Adds the given piece from the queue."""
        logger.debug(f"Piece '{piece_id}' from order_id '{order_id}' added to queue.")
        await self.__manufacturing_queue.put((piece_id, order_id))

    async def remove_pieces_from_queue(self, pieces):
        """Adds a list of pieces to the queue and updates their status."""
        logger.debug("Removing %i pieces from queue", len(pieces))
        for piece in pieces:
            await self.remove_piece_from_queue(piece)

    async def remove_piece_from_queue(self, piece) -> bool:
        """Removes the given piece from the queue."""
        logger.info("Removing piece %i", piece.id)
        if self.working_piece == piece.id:
            logger.warning(
                "Piece %i is being manufactured, cannot remove from queue\n\n",
                piece.id
            )
            return False

        item_list = []
        removed = False
        # Empty the list
        while not self.__manufacturing_queue.empty():
            item_list.append(self.__manufacturing_queue.get_nowait())

        # Fill the list with all items but *piece_id*
        for item in item_list:
            if item != piece.id:
                self.__manufacturing_queue.put_nowait(item)
            else:
                logging.debug("Piece %i removed from queue.", piece.id)
                removed = True

        if not removed:
            logger.warning("Piece %i not found in the queue.", piece.id)

        return removed

    async def list_queued_pieces(self):
        """Get queued piece ids as list."""
        piece_list = list(self.__manufacturing_queue.__dict__['_queue'])
        return piece_list
