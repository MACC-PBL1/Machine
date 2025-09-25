# -*- coding: utf-8 -*-
"""Classes for Request/Response schema definitions."""
# pylint: disable=too-few-public-methods
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict  # pylint: disable=no-name-in-module



class Message(BaseModel):
    """Respuesta genérica de éxito/error."""
    detail: str = Field(example="Cliente creado correctamente")


class ClientBase(BaseModel):
    """Campos comunes de un cliente."""
    name: str = Field(..., example="Juan Pérez")
    email: str = Field(..., example="juan@example.com")
    phone: Optional[str] = Field(None, example="+34 600 123 456")


class ClientCreate(ClientBase):
    """Schema para crear cliente (entrada POST)."""
    pass


class ClientUpdate(BaseModel):
    """Schema para actualizar datos de cliente (entrada PUT/PATCH)."""
    name: Optional[str] = Field(None, example="Juan Actualizado")
    phone: Optional[str] = Field(None, example="+34 700 123 456")


class ClientOut(ClientBase):
    """Respuesta al consultar cliente (salida GET)."""
    id: int = Field(..., example=1)

    class Config:
        from_attributes = True  # equivale a orm_mode=True

