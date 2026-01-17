from chassis.sql import BaseModel
from sqlalchemy import (
    Integer, 
    String, 
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column
)

class Task(BaseModel):
    __tablename__ = "task"

    STATUS_QUEUED = "Queued"
    STATUS_PROCESSING = "Processing"
    STATUS_PROCESSED = "Processed"
    STATUS_FAILED = "Failed"
    STATUS_CANCELLED = "Cancelled"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    piece_id: Mapped[int] = mapped_column(Integer, nullable=False)
    piece_type: Mapped[str] = mapped_column(String(1), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=STATUS_QUEUED)