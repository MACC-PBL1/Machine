from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from microservice_chassis.db import BaseModel

class Piece(BaseModel):
    __tablename__ = "piece"

    STATUS_CREATED = "Created"
    STATUS_CANCELLED = "Cancelled"
    STATUS_QUEUED = "Queued"
    STATUS_MANUFACTURING = "Manufacturing"
    STATUS_MANUFACTURED = "Manufactured"

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, nullable=False)
    manufacturing_date = Column(DateTime(timezone=True), server_default=None)
    status = Column(String(256), default=STATUS_QUEUED)
