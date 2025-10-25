from chassis.sql import BaseModel
from datetime import datetime
from sqlalchemy import (
    # Column, 
    DateTime,
    Integer, 
    String, 
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column
)

class PieceModel(BaseModel):
    __tablename__ = "piece"

    STATUS_CREATED = "Created"
    STATUS_CANCELLED = "Cancelled"
    STATUS_QUEUED = "Queued"
    STATUS_MANUFACTURING = "Manufacturing"
    STATUS_MANUFACTURED = "Manufactured"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    manufacturing_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=None)
    status: Mapped[str] = mapped_column(String(256), default=STATUS_QUEUED)
