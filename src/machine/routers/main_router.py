from ..business_logic import (
    get_machine, 
    Machine
)
from ..sql import (
    MachineStatusResponse,
    Piece, 
    PieceModel, 
)
from chassis.sql import (
    get_db, 
    get_list, 
    get_list_statement_result, 
    get_element_statement_result,
)
from chassis.security.jwt_utils import verify_jwt
from fastapi import (
    APIRouter, 
    Depends, 
    HTTPException,
    Request,
    status
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import (
    List, 
    Optional
)

Router = APIRouter(prefix="/machine", tags=["Machine"])

# --------------------------------------------------
# GET /machine/status
# --------------------------------------------------
@Router.get(
    "/status", 
    response_model=MachineStatusResponse, 
    summary="Estado actual de la máquina"
)
async def get_machine_status(
    request: Request,
    machine: Machine = Depends(get_machine)
):  
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )

    token = auth_header.split(" ")[1]
    try:
        verify_jwt(token, require_admin=True)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    
    queue = await machine.list_queued_pieces()
    working_piece_id = machine.working_piece["id"] if machine.working_piece else None
    order_id = machine.working_piece["order_id"] if machine.working_piece else None
    return MachineStatusResponse(
        status=machine.status, 
        order_id=order_id, 
        working_piece=working_piece_id, 
        queue=queue
    )

# --------------------------------------------------
# GET /machine/status/piece
# --------------------------------------------------
@Router.get(
    "/status/piece", 
    response_model=List[Piece], 
    summary="Lista de todas las piezas"
)
async def get_all_pieces(request: Request, db: AsyncSession = Depends(get_db)):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )

    token = auth_header.split(" ")[1]
    try:
        verify_jwt(token, require_admin=True)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    return await get_list(db, PieceModel)

# --------------------------------------------------
# GET /machine/status/piece/{order_id}
# --------------------------------------------------
@Router.get(
    "/status/piece/{order_id}", 
    response_model=List[Piece], 
    summary="Lista de piezas por order_id"
)
async def get_pieces_by_order(
    request: Request,
    order_id: int, 
    db: AsyncSession = Depends(get_db)
):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )

    token = auth_header.split(" ")[1]
    try:
        verify_jwt(token, require_admin=True)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    result = await get_list_statement_result(
        db=db,
        stmt=select(PieceModel).where(PieceModel.order_id == order_id)
    )
    return result

# --------------------------------------------------
# GET /machine/status/piece/{order_id}/{piece_id}
# --------------------------------------------------
@Router.get(
    "/status/piece/{order_id}/{piece_id}", 
    response_model=Piece, 
    summary="Información de una pieza específica"
)
async def get_piece_detail(
    request: Request,
    order_id: int, 
    piece_id: int, 
    db: AsyncSession = Depends(get_db)
):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )

    token = auth_header.split(" ")[1]
    try:
        verify_jwt(token, require_admin=True)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    piece: Optional[PieceModel] = await get_element_statement_result(
        db=db,
        stmt=select(PieceModel)
                .where(PieceModel.order_id == order_id)
                .where(PieceModel.id == piece_id)
    )

    if piece is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Piece not found for this order"
        )
    return piece.as_dict()
