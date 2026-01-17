from .models import Task
from chassis.sql import (
    get_element_by_id,
    get_element_statement_result,
    get_list_statement_result,
    update_elements_statement_result,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import (
    select,
    update,
)
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
) -> Task:
    existing = await get_task_by_piece(db, piece_id)
    if existing:
        return existing

    task = Task(
        piece_id=piece_id,
        piece_type=piece_type,
        status=Task.STATUS_QUEUED,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task

async def get_task_by_piece(
    db: AsyncSession,
    piece_id: int,
) -> Optional[Task]:
    return await get_element_statement_result(
        db=db,
        stmt=(
            select(Task)
                .where(Task.piece_id == piece_id)
        ),
    )

async def update_task(
    db: AsyncSession,
    task: Task,
    **updates,
) -> Optional[Task]:
    if not updates:
        return task
    
    await update_elements_statement_result(
        db=db,
        stmt=(
            update(Task)
                .where(Task.id == task.id)
                .values(**updates)
        )
    )
    return await get_element_by_id(db, Task, task.id)