"""Schemas de produtos e servicos."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import Field

from app.schemas.common import APIModel, APIRequest


class ProductCreate(APIRequest):
    name: str = Field(min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    category: str | None = Field(default=None, max_length=120)
    price: float | None = Field(default=None, ge=0, le=99_999_999)
    currency: str = Field(default="BRL", min_length=3, max_length=3)
    highlights: list[str] = Field(default_factory=list, max_length=12)
    is_active: bool = True


class ProductUpdate(APIRequest):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    category: str | None = Field(default=None, max_length=120)
    price: float | None = Field(default=None, ge=0, le=99_999_999)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    highlights: list[str] | None = Field(default=None, max_length=12)
    is_active: bool | None = None


class ProductRead(APIModel):
    id: uuid.UUID
    business_id: uuid.UUID
    name: str
    description: str | None
    category: str | None
    price: float | None
    currency: str
    highlights: list[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ServiceCreate(APIRequest):
    name: str = Field(min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    category: str | None = Field(default=None, max_length=120)
    price: float | None = Field(default=None, ge=0, le=99_999_999)
    currency: str = Field(default="BRL", min_length=3, max_length=3)
    duration_minutes: int | None = Field(default=None, ge=1, le=100_000)
    deliverables: list[str] = Field(default_factory=list, max_length=12)
    is_active: bool = True


class ServiceUpdate(APIRequest):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    category: str | None = Field(default=None, max_length=120)
    price: float | None = Field(default=None, ge=0, le=99_999_999)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    duration_minutes: int | None = Field(default=None, ge=1, le=100_000)
    deliverables: list[str] | None = Field(default=None, max_length=12)
    is_active: bool | None = None


class ServiceRead(APIModel):
    id: uuid.UUID
    business_id: uuid.UUID
    name: str
    description: str | None
    category: str | None
    price: float | None
    currency: str
    duration_minutes: int | None
    deliverables: list[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
