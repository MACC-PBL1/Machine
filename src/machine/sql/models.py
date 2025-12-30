from chassis.sql import BaseModel
from datetime import datetime
from sqlalchemy import (
    DateTime,
    Integer, 
    String, 
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column
)

class MachineTaskModel(BaseModel):
    __tablename__ = "machine_task"

    STATUS_QUEUED = "QUEUED"
    STATUS_WORKING = "WORKING"
    STATUS_DONE = "DONE"
    STATUS_FAILED = "FAILED"
    STATUS_CANCELLED = "CANCELLED"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    piece_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    piece_type: Mapped[str] = mapped_column(
        String(1), 
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=STATUS_QUEUED,
        index=True,
    )

    queued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
