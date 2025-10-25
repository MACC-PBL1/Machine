# -*- coding: utf-8 -*-
"""Functions that interact with the database."""
from .models import PieceModel
from chassis.sql import (
    get_list_statement_result,
    get_element_by_id,
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

# Piece functions ##################################################################################
async def get_piece(
    db: AsyncSession, 
    piece_id: int,
    order_id: int,
) -> Optional[PieceModel]:
    """Load a piece from the database."""
    return await get_element_statement_result(
        db=db,
        stmt=select(PieceModel)
                .where(PieceModel.id == piece_id)
                .where(PieceModel.order_id == order_id)
    )

async def get_piece_list(db: AsyncSession) -> List[PieceModel]:
    """Load all the orders from the database."""
    return await get_list_statement_result(
        db=db, 
        stmt=select(PieceModel).join(PieceModel.order) # TODO: HONEK ERROREA!!
    )

async def get_piece_list_by_order(
    db: AsyncSession,
    order_id: int,
) -> List[PieceModel]:
    return await get_list_statement_result(
        db=db,
        stmt=select(PieceModel).where(PieceModel.order_id == order_id)
    )

async def get_piece_list_by_status(
    db: AsyncSession, 
    status: str
) -> List[PieceModel]:
    """Get all pieces with a given status from the database."""
    return await get_list_statement_result(
        db=db, 
        stmt=select(PieceModel).where(PieceModel.status == status)
    )

async def update_piece_status(
    db: AsyncSession, 
    piece_id: int,
    order_id: int, 
    status: str,
) -> Optional[PieceModel]:
    """Persist new piece status on the database."""
    db_piece = await get_piece(db, piece_id, order_id)
    if db_piece is not None:
        db_piece.status = status
        await db.commit()
        await db.refresh(db_piece)
    return db_piece

async def update_piece_manufacturing_date_to_now(
    db: AsyncSession, 
    piece_id: int,
    order_id: int,
) -> Optional[PieceModel]:
    """For a given piece_id, sets piece's manufacturing_date to current datetime."""
    db_piece = await get_piece(db, piece_id, order_id)
    if db_piece is not None:
        db_piece.manufacturing_date = datetime.now()
        await db.commit()
        await db.refresh(db_piece)
    return db_piece