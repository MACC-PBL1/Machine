# -*- coding: utf-8 -*-
"""FastAPI router definitions for Machine Service."""
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.business_logic.async_machine import Machine
from app.dependencies import get_db, get_machine
from app.sql import crud
from ..sql import schemas
from app.sql.models import Piece as PieceModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/machine", tags=["Machine"])

# ------------------------------------------------------------------------------------
# Health check
# ------------------------------------------------------------------------------------
@router.get(
    "/",
    summary="Health check endpoint",
    response_model=schemas.Message,
)
async def health_check():
    """Endpoint to check if the Machine Service is running."""
    logger.debug("GET '/' endpoint called.")
    return {"detail": "OK"}

# Machine ##########################################################################################
@router.get(
    "/status",
    summary="Retrieve machine status",
    response_model=schemas.MachineStatusResponse,
    tags=['Machine']
)
async def machine_status(
        my_machine: Machine = Depends(get_machine)
):
    """Retrieve machine status"""
    logger.debug("GET '/machine/status' endpoint called.")
    working_piece_id = None
    if my_machine.working_piece is not None:
        working_piece_id = my_machine.working_piece['id']

    queue = await my_machine.list_queued_pieces()

    return schemas.MachineStatusResponse(
        status=my_machine.status,
        working_piece=working_piece_id,
        queue=queue
    )


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
async def get_single_piece(piece_id: int, db: AsyncSession = Depends(get_db)):
    piece = await crud.get_piece(db, piece_id)
    if not piece:
        raise HTTPException(status_code=404, detail=f"Piece {piece_id} not found")
    return piece.as_dict()

@router.post(
    "/requestPiece",
    response_model=schemas.Piece,
    summary="Request piece manufacturing",
    status_code=status.HTTP_201_CREATED,
    tags=["Machine"]
)
async def request_piece_manufacturing(
    piece_schema: schemas.PieceCreate,
    db: AsyncSession = Depends(get_db),
    machine: "Machine" = Depends(get_machine)
):
    try:
        db_piece = await crud.create_piece_for_order(db, piece_schema)

        await machine.add_piece_to_queue(db_piece)

        return db_piece

    except Exception as exc:
        logger.error("Error requesting piece manufacturing: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Error requesting piece manufacturing: {exc}"
        )