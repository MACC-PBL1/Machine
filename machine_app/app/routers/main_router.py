# -*- coding: utf-8 -*-
"""FastAPI router definitions for Client Service."""
import logging
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.sql import crud, schemas
from app.dependencies import get_db

logger = logging.getLogger(__name__)
router = APIRouter()

# ------------------------------------------------------------------------------------
# Health check
# ------------------------------------------------------------------------------------
@router.get(
    "/",
    summary="Health check endpoint",
    response_model=schemas.Message,
)
async def health_check():
    """Endpoint to check if the Client Service is running."""
    logger.debug("GET '/' endpoint called.")
    return {"detail": "OK"}


# ------------------------------------------------------------------------------------
# Pieces
# ------------------------------------------------------------------------------------
@router.get(
    "/piece",
    response_model=List[schemas.Piece],
    summary="retrieve piece list",
    tags=["Piece", "List"]
)
async def get_piece_list(
        db: AsyncSession = Depends(get_db)
):
    """Retrieve the list of pieces."""
    logger.debug("GET '/piece' endpoint called.")
    return await crud.get_piece_list(db)


@router.get(
    "/piece/{piece_id}",
    summary="Retrieve single piece by id",
    response_model=schemas.Piece,
    tags=['Piece']
)
async def get_single_piece(
        piece_id: int,
        db: AsyncSession = Depends(get_db)
):
    """Retrieve single piece by id"""
    logger.debug("GET '/piece/%i' endpoint called.", piece_id)
    return await crud.get_piece(db, piece_id)