from datetime import datetime
from pydantic import BaseModel
from typing import (
    Optional, 
    List,
    Tuple,
)

class Message(BaseModel):
    detail: str
    system_metrics: dict

class MachineTask(BaseModel):
    piece_id: int
    status: str
    queued_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime]

    class Config:
        from_attributes = True


class MachineStatusResponse(BaseModel):
    status: str
    working_piece: Optional[int]
    queue: List[int]