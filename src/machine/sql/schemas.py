from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class Message(BaseModel):
    detail: str = "Operation successful"

class PieceBase(BaseModel):
    id: int
    manufacturing_date: Optional[datetime]
    status: str = "Queued"

class Piece(PieceBase):
    order_id: Optional[int]

    class Config:
        from_attributes = True

class PieceCreate(BaseModel):
    order: Optional[int]

class MachineStatusResponse(BaseModel):
    status: str
    order_id: Optional[int]
    working_piece: Optional[int]
    queue: List[int]
