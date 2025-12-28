from __future__ import annotations

from ..global_vars import (
    PUBLISHING_QUEUES,
    RABBITMQ_CONFIG,
)

from ..sql.crud import (
    create_task,
    mark_task_working,
    mark_task_done,
    get_task_by_piece,
)

from ..sql.models import MachineTaskModel

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
    STATUS_IDLE = "IDLE"
    STATUS_WORKING = "WORKING"

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory
        self._loop = asyncio.get_running_loop()
        self._queue: asyncio.Queue[int] = asyncio.Queue()
        self._stop = False

        self.working_piece: Optional[int] = None
        self.status = self.STATUS_IDLE

    @classmethod
    async def create(
        cls,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> "Machine":
        logger.info("[LOG:MACHINE] - AsyncMachine initialized")
        self = cls(session_factory)
        asyncio.create_task(self._manufacturing_coroutine())
        return self

    # WORKER PRINCIPAL
    async def _manufacturing_coroutine(self) -> None:
        logger.debug("[LOG:MACHINE] - Manufacturing coroutine started")

        while not self._stop:
            piece_id = await self._queue.get()

            try:
                # 1) Revalidar estado en BD ANTES de ejecutar
                async with self._session_factory() as db:
                    task = await get_task_by_piece(db, piece_id)

                if task is None:
                    logger.warning(
                        "[MACHINE] - No task found, skipping piece_id=%s",
                        piece_id,
                    )
                    continue

                #  SOLO se ejecuta si está QUEUED
                if task.status != MachineTaskModel.STATUS_QUEUED:
                    logger.info(
                        "[MACHINE] - Skipping task piece_id=%s status=%s",
                        piece_id,
                        task.status,
                    )
                    continue   # CANCELLED, DONE, WORKING → NO EJECUTAR

                # 2) Ejecutar
                await self._execute_piece(piece_id)

            except Exception as e:
                logger.error(
                    "[MACHINE] - Error executing piece_id=%s: %s",
                    piece_id,
                    e,
                    exc_info=True,
                )
            finally:
                #  Siempre exactamente 1 task_done por cada get()
                self._queue.task_done()

    # EJECUCIÓN TÉCNICA
    async def _execute_piece(self, piece_id: int) -> None:
        logger.debug("[MACHINE] - Executing piece_id=%s", piece_id)

        self.status = self.STATUS_WORKING
        self.working_piece = piece_id

        async with self._session_factory() as db:
            await mark_task_working(db, piece_id)
            await db.commit()

        await asyncio.sleep(randint(5, 20))

        async with self._session_factory() as db:
            await mark_task_done(db, piece_id)
            await db.commit()

        self._publish_piece_executed(piece_id)

        self.working_piece = None
        self.status = self.STATUS_IDLE

    # API PÚBLICA
    async def add_piece_to_queue(self, piece_id: int) -> None:
        # Creamos task técnica en BD (idempotente si tienes unique(piece_id))
        async with self._session_factory() as db:
            await create_task(db, piece_id)
            await db.commit()

        # Encolar
        await self._queue.put(piece_id)

    async def list_queued_pieces(self):
        # (debug) introspección interna de asyncio.Queue
        return list(self._queue._queue)


    # EVENTO
    def _publish_piece_executed(self, piece_id: int) -> None:
        with RabbitMQPublisher(
            queue=PUBLISHING_QUEUES["piece_executed"],
            rabbitmq_config=RABBITMQ_CONFIG,
        ) as publisher:
            publisher.publish({"piece_id": piece_id})

        logger.info("[EVENT:MACHINE:PIECE_EXECUTED] - piece_id=%s", piece_id)
