# -*- coding: utf-8 -*-
"""Classes for Request/Response schema definitions."""
# pylint: disable=too-few-public-methods
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict  # pylint: disable=no-name-in-module



class Message(BaseModel):
    """Respuesta genérica de éxito/error."""
    detail: str = Field(example="Machinee creado correctamente")


class MachineBase(BaseModel):
    """Campos comunes de un machinee."""
    name: str = Field(..., example="Juan Pérez")
    email: str = Field(..., example="juan@example.com")
    phone: Optional[str] = Field(None, example="+34 600 123 456")


class PieceBase(BaseModel):
    """Piece base schema definition."""
    id: int = Field(
        description="Piece identifier (Primary key)",
        example="1"
    )
    manufacturing_date: Optional[datetime] = Field(
        description="Date when piece has been manufactured",
        example="2022-07-22T17:32:32.193211"
    )
    status: str = Field(
        description="Current status of the piece",
        default="Queued",
        example="Manufactured"
    )


class Piece(PieceBase):
    """Piece schema definition."""
    model_config = ConfigDict(from_attributes=True)  # ORM mode ON
    orderId: Optional[int] = Field(description="Order where the piece belongs to")

    #class Config:
    #    """ORM configuration."""
    #    orm_mode = True

class PieceCreate(BaseModel):
    order: Optional[int]


class MachineStatusResponse(BaseModel):
    """machine status schema definition."""
    status: str = Field(
        description="Machine's current status",
        default=None,
        example="Waiting"
    )
    working_piece: Optional[int] = Field(
        description="Current working piece id. None if not working piece.",
        example=1
    )
    queue: List[int] = Field(description="Queued piece ids")
