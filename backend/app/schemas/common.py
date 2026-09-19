"""Tipos base dos schemas da API."""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

ItemT = TypeVar("ItemT")


class APIModel(BaseModel):
    """Base dos schemas de resposta: le direto dos models SQLAlchemy."""

    model_config = ConfigDict(from_attributes=True)


class APIRequest(BaseModel):
    """Base dos schemas de entrada: rejeita campos desconhecidos.

    Recusar `extra` evita que um campo com nome errado seja silenciosamente
    ignorado e o usuario ache que salvou algo que nao foi salvo.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class MessageResponse(BaseModel):
    message: str


class Page(BaseModel, Generic[ItemT]):
    items: list[ItemT]
    total: int
    limit: int
    offset: int

    @property
    def has_more(self) -> bool:
        return self.offset + len(self.items) < self.total


class PaginationParams(BaseModel):
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)
