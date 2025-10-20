from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.sql.models import Piece as PieceModel
from app.sql.schemas import Piece, MachineStatusResponse
from microservice_chassis.db import get_session, get_list, get_list_statement_result, get_element_by_id
from app.dependencies import get_machine
from app.business_logic.async_machine import Machine

router = APIRouter(prefix="/machine", tags=["Machine"])


# --------------------------------------------------
# GET /machine/status
# --------------------------------------------------
@router.get("/status", response_model=MachineStatusResponse, summary="Estado actual de la máquina")
async def get_machine_status(machine: Machine = Depends(get_machine)):
    queue = await machine.list_queued_pieces()
    working_piece_id = machine.working_piece["id"] if machine.working_piece else None
    order_id = machine.working_piece["order_id"] if machine.working_piece else None
    return MachineStatusResponse(status=machine.status, order_id=order_id, working_piece=working_piece_id, queue=queue)



# --------------------------------------------------
# GET /machine/status/piece
# --------------------------------------------------
@router.get("/status/piece", response_model=List[Piece], summary="Lista de todas las piezas")
async def get_all_pieces(db: AsyncSession = Depends(get_session)):
    return await get_list(db, PieceModel)


# --------------------------------------------------
# GET /machine/status/piece/{order_id}
# --------------------------------------------------
@router.get("/status/piece/{order_id}", response_model=List[Piece], summary="Lista de piezas por order_id")
async def get_pieces_by_order(order_id: int, db: AsyncSession = Depends(get_session)):
    result = await get_list_statement_result(
        db,
        db.select(PieceModel).where(PieceModel.order_id == order_id)
    )
    return result


# --------------------------------------------------
# GET /machine/status/piece/{order_id}/{piece_id}
# --------------------------------------------------
@router.get("/status/piece/{order_id}/{piece_id}", response_model=Piece, summary="Información de una pieza específica")
async def get_piece_detail(order_id: int, piece_id: int, db: AsyncSession = Depends(get_session)):
    piece = await get_element_by_id(db, PieceModel, piece_id)
    if not piece or piece.order_id != order_id:
        raise HTTPException(status_code=404, detail="Piece not found for this order")
    return piece.as_dict()
