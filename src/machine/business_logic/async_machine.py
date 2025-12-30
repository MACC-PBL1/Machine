from __future__ import annotations

import os
import asyncio
import logging
from random import randint
from typing import Optional

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from chassis.messaging import RabbitMQPublisher

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

logger = logging.getLogger(__name__)


class Machine:
    STATUS_IDLE = "IDLE"
    STATUS_WORKING = "WORKING"

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory
        self._queue: asyncio.Queue[int] = asyncio.Queue()
        self._stop = False

        self.machine_type = os.getenv("MACHINE_TYPE")  # "A" | "B"
        if self.machine_type not in ("A", "B"):
            raise RuntimeError("MACHINE_TYPE must be 'A' or 'B'")

        self.working_piece: Optional[int] = None
        self.status = self.STATUS_IDLE

    @classmethod
    async def create(
        cls,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> "Machine":
        logger.info(
            "[LOG:MACHINE-%s] - Machine initialized",
            os.getenv("MACHINE_TYPE"),
        )
        self = cls(session_factory)
        asyncio.create_task(self._manufacturing_coroutine())
        return self

    # =========================================================
    # WORKER PRINCIPAL
    # =========================================================
    async def _manufacturing_coroutine(self) -> None:
        logger.debug(
            "[LOG:MACHINE-%s] - Manufacturing coroutine started",
            self.machine_type,
        )

        while not self._stop:
            piece_id = await self._queue.get()

            try:
                # 1) Revalidar estado en BD ANTES de ejecutar
                async with self._session_factory() as db:
                    task = await get_task_by_piece(db, piece_id)

                if task is None:
                    logger.warning(
                        "[MACHINE-%s] - No task found, skipping piece_id=%s",
                        self.machine_type,
                        piece_id,
                    )
                    continue

                # Solo ejecutar si está QUEUED y es de mi tipo
                if (
                    task.status != MachineTaskModel.STATUS_QUEUED
                    or task.piece_type != self.machine_type
                ):
                    logger.info(
                        "[MACHINE-%s] - Skipping piece_id=%s status=%s type=%s",
                        self.machine_type,
                        piece_id,
                        task.status,
                        task.piece_type,
                    )
                    continue

                # 2) Ejecutar
                await self._execute_piece(piece_id)

            except Exception as e:
                logger.error(
                    "[MACHINE-%s] - Error executing piece_id=%s: %s",
                    self.machine_type,
                    piece_id,
                    e,
                    exc_info=True,
                )
            finally:
                self._queue.task_done()

    # =========================================================
    # EJECUCIÓN TÉCNICA
    # =========================================================
    async def _execute_piece(self, piece_id: int) -> None:
        logger.info(
            "[MACHINE-%s] - Executing piece_id=%s",
            self.machine_type,
            piece_id,
        )

        self.status = self.STATUS_WORKING
        self.working_piece = piece_id

        async with self._session_factory() as db:
            await mark_task_working(db, piece_id)
            await db.commit()

        # Simulación de trabajo
        await asyncio.sleep(randint(5, 20))

        async with self._session_factory() as db:
            await mark_task_done(db, piece_id)
            await db.commit()

        self._publish_piece_executed(piece_id)

        self.working_piece = None
        self.status = self.STATUS_IDLE

    # =========================================================
    # API PÚBLICA
    # =========================================================
    async def add_piece_to_queue(
        self,
        piece_id: int,
        piece_type: str,
    ) -> None:
        if piece_type != self.machine_type:
            logger.warning(
                "[MACHINE-%s] - Ignoring piece_id=%s of type=%s",
                self.machine_type,
                piece_id,
                piece_type,
            )
            return

        async with self._session_factory() as db:
            await create_task(
                db=db,
                piece_id=piece_id,
                piece_type=piece_type,
            )
            await db.commit()

        await self._queue.put(piece_id)

    async def list_queued_pieces(self):
        return list(self._queue._queue)

    # =========================================================
    # EVENTOS
    # =========================================================
    def _publish_piece_executed(self, piece_id: int) -> None:
        with RabbitMQPublisher(
            queue=PUBLISHING_QUEUES["piece_executed"],
            rabbitmq_config=RABBITMQ_CONFIG,
        ) as publisher:
            publisher.publish({
                "piece_id": piece_id,
                "piece_type": self.machine_type,
            })

        logger.info(
            "[EVENT:MACHINE-%s:PIECE_EXECUTED] - piece_id=%s",
            self.machine_type,
            piece_id,
        )
