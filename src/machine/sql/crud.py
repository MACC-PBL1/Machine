from .models import MachineTaskModel
from chassis.sql import (
    get_list_statement_result,
    get_element_statement_result,

)
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import (
    List,
    Optional,
)
import logging

logger = logging.getLogger(__name__)



async def create_task(
    db: AsyncSession,
    piece_id: int,
    piece_type: str,
) -> MachineTaskModel:
    existing = await get_task_by_piece(db, piece_id)
    if existing:
        return existing

    task = MachineTaskModel(
        piece_id=piece_id,
        piece_type=piece_type,
        status=MachineTaskModel.STATUS_QUEUED,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task



async def get_task_by_piece(
    db: AsyncSession,
    piece_id: int,
) -> Optional[MachineTaskModel]:
    return await get_element_statement_result(
        db=db,
        stmt=select(MachineTaskModel)
        .where(MachineTaskModel.piece_id == piece_id),
    )

async def list_tasks(
    db: AsyncSession,
) -> List[MachineTaskModel]:
    return await get_list_statement_result(
        db=db,
        stmt=select(MachineTaskModel),
    )


async def list_tasks_by_status(
    db: AsyncSession,
    status: str,
) -> List[MachineTaskModel]:
    return await get_list_statement_result(
        db=db,
        stmt=select(MachineTaskModel)
        .where(MachineTaskModel.status == status),
    )

async def mark_task_working(
    db: AsyncSession,
    piece_id: int,
) -> Optional[MachineTaskModel]:
    task = await get_task_by_piece(db, piece_id)

    if task and task.status == MachineTaskModel.STATUS_QUEUED:
        task.status = MachineTaskModel.STATUS_WORKING
        task.started_at = datetime.utcnow()
        await db.commit()
        await db.refresh(task)

    return task

async def mark_task_done(
    db: AsyncSession,
    piece_id: int,
) -> Optional[MachineTaskModel]:
    task = await get_task_by_piece(db, piece_id)

    if task and task.status == MachineTaskModel.STATUS_WORKING:
        task.status = MachineTaskModel.STATUS_DONE
        task.finished_at = datetime.utcnow()
        await db.commit()
        await db.refresh(task)

    return task


async def mark_task_failed(
    db: AsyncSession,
    piece_id: int,
) -> Optional[MachineTaskModel]:
    task = await get_task_by_piece(db, piece_id)

    if task and task.status == MachineTaskModel.STATUS_WORKING:
        task.status = MachineTaskModel.STATUS_FAILED
        task.finished_at = datetime.utcnow()
        await db.commit()
        await db.refresh(task)

    return task

async def mark_task_cancelled(
    db: AsyncSession,
    piece_id: int,
) -> Optional[MachineTaskModel]:
    """
    Cancels ONLY queued tasks.
    WORKING tasks are not interrupted (best-effort).
    """
    task = await get_task_by_piece(db, piece_id)

    if task and task.status == MachineTaskModel.STATUS_QUEUED:
        task.status = MachineTaskModel.STATUS_CANCELLED
        task.finished_at = datetime.utcnow()
        await db.commit()
        await db.refresh(task)

    return task