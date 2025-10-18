# machine/routes.py
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from microservice_chassis.db import get_session
from microservice_chassis.utils import raise_and_log_error
from app.business_logic.async_machine import Machine
from app.sql.models import Piece as PieceModel
from app.sql.schemas import Piece, PieceCreate, MachineStatusResponse, Message

router = APIRouter(prefix="/machine", tags=["Machine"])

# -----------------------------
# Health check
# -----------------------------
@router.get("/", summary="Health check endpoint", response_model=Message)
async def health_check():
    return {"detail": "OK"}

# -----------------------------
# Machine status
# -----------------------------
@router.get("/status", summary="Retrieve machine status", response_model=MachineStatusResponse)
async def machine_status(machine: Machine = Depends(Machine.create)):
    queue = await machine.list_queued_pieces()
    working_piece_id = machine.working_piece["id"] if machine.working_piece else None
    return MachineStatusResponse(
        status=machine.status,
        working_piece=working_piece_id,
        queue=queue
    )

# -----------------------------
# Pieces endpoints
# -----------------------------
@router.get("/piece", response_model=List[Piece], summary="Retrieve piece list")
async def get_piece_list(db: AsyncSession = Depends(get_session)):
    from app.sql.models import Piece as PieceModel
    from microservice_chassis.db import get_list
    return await get_list(db, PieceModel)

@router.get("/piece/{piece_id}", response_model=Piece, summary="Retrieve single piece by id")
async def get_piece(piece_id: int, db: AsyncSession = Depends(get_session)):
    from app.sql.models import Piece as PieceModel
    from microservice_chassis.db import get_element_by_id
    piece = await get_element_by_id(db, PieceModel, piece_id)
    if not piece:
        raise HTTPException(status_code=404, detail=f"Piece {piece_id} not found")
    return piece.as_dict()

@router.post("/requestPiece", response_model=Piece, status_code=status.HTTP_201_CREATED)
async def request_piece_manufacturing(
    piece_schema: PieceCreate,
    machine: Machine = Depends(Machine.create),
    db: AsyncSession = Depends(get_session)
):
    from app.sql.models import Piece as PieceModel
    new_piece = PieceModel(status=PieceModel.STATUS_QUEUED, orderId=piece_schema.order)
    db.add(new_piece)
    await db.commit()
    await db.refresh(new_piece)
    await Machine.add_piece_to_queue(new_piece)
    return new_piece
