from ..global_vars import (
    MACHINE_TYPE,
    RABBITMQ_CONFIG,
)
from ..sql.crud import (
    create_task,
    get_task_by_piece,
    update_task,
)
from ..sql.models import Task
from chassis.messaging import RabbitMQPublisher
from random import randint
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)
from typing import Optional
import asyncio
import logging

logger = logging.getLogger(__name__)

class Machine:
    STATUS_IDLE = "Idle"
    STATUS_PROCESSING = "Processing"

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._queue: asyncio.Queue[int] = asyncio.Queue()
        self._session_factory = session_factory
        self._status = self.STATUS_IDLE
        self._stop = False
        self._working_piece: Optional[int] = None

    async def _manufacturing_coroutine(self) -> None:
        while not self._stop:
            piece_id = await self._queue.get()

            async with self._session_factory() as db:
                assert (task := await get_task_by_piece(db, piece_id)) is not None, "Task should exist"
                assert task.status == Task.STATUS_QUEUED, "The task should be queued"

            await self._produce_piece(piece_id)
            self._queue.task_done()

    @staticmethod
    def _notify_piece_processing(piece_id: int) -> None:
        with RabbitMQPublisher(
            queue="",
            rabbitmq_config=RABBITMQ_CONFIG,
            exchange="machine_events",
            exchange_type="topic",
            routing_key="machine.piece.producing",
            auto_delete_queue=True
        ) as publisher:
            publisher.publish({
                "piece_id": piece_id,
            })

    async def _produce_piece(self, piece_id: int) -> None:
        self._status = self.STATUS_PROCESSING
        self._working_piece = piece_id

        Machine._notify_piece_processing(piece_id)

        async with self._session_factory() as db:
            assert (task := await get_task_by_piece(db, piece_id)) is not None, "Task should exist"
            assert task.status == Task.STATUS_QUEUED, "The task should be queued"
            assert (await update_task(db, task, status=Task.STATUS_PROCESSING)) is not None, "Update should happen"

        # Simulación de trabajo
        await asyncio.sleep(randint(5, 20))

        async with self._session_factory() as db:
            assert (task := await get_task_by_piece(db, piece_id)) is not None, "Task should exist"
            assert task.status == Task.STATUS_PROCESSING, "The task should be queued"
            assert (await update_task(db, task, status=Task.STATUS_PROCESSED)) is not None, "Update should happen"

        Machine._publish_produced_piece(piece_id)

        self._working_piece = None
        self._status = self.STATUS_IDLE

    @staticmethod
    def _publish_produced_piece(piece_id: int) -> None:
        with RabbitMQPublisher(
            queue="",
            rabbitmq_config=RABBITMQ_CONFIG,
            exchange="machine_events",
            exchange_type="topic",
            routing_key="machine.piece.produced",
            auto_delete_queue=True
        ) as publisher:
            publisher.publish({
                "piece_id": piece_id,
            })

    async def add_piece_to_queue(
        self,
        piece_id: int,
        piece_type: str,
    ) -> None:
        assert piece_type == MACHINE_TYPE, "Piece should be the same type of the machine"

        async with self._session_factory() as db:
            _ = await create_task(
                db=db,
                piece_id=piece_id,
                piece_type=piece_type,
            )

        await self._queue.put(piece_id)

    @classmethod
    async def create(
        cls,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> "Machine":
        self = cls(session_factory)
        asyncio.create_task(self._manufacturing_coroutine())
        return self

    async def list_queued_pieces(self) -> list[int]:
        return list(self._queue._queue) # type: ignore