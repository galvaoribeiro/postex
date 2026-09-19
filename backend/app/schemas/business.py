"""Schemas do negocio e das preferencias editoriais."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import Field

from app.models.enums import ContentFormat
from app.schemas.common import APIModel, APIRequest


class ContentPreferencesSchema(APIRequest):
    preferred_formats: list[ContentFormat] = Field(default_factory=list)
    preferred_categories: list[str] = Field(default_factory=list)
    avoided_categories: list[str] = Field(default_factory=list)
    posts_per_week: int = Field(default=3, ge=1, le=21)
    language: str = Field(default="pt-BR", max_length=12)
    emoji_usage: str = Field(default="moderado", max_length=24)
    forbidden_topics: list[str] = Field(default_factory=list, max_length=20)
    extra_guidelines: str = Field(default="", max_length=1000)
    default_cta: str = Field(default="", max_length=40)
    whatsapp: str = Field(default="", max_length=32)


class BusinessBase(APIRequest):
    name: str = Field(min_length=2, max_length=160)
    segment: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=4000)
    target_audience: str | None = Field(default=None, max_length=2000)
    location: str | None = Field(default=None, max_length=180)
    brand_voice: str | None = Field(default=None, max_length=1000)
    additional_info: str | None = Field(default=None, max_length=4000)
    instagram_handle: str | None = Field(default=None, max_length=80)
    website: str | None = Field(default=None, max_length=255)
    differentiators: list[str] = Field(default_factory=list, max_length=15)
    objectives: list[str] = Field(default_factory=list, max_length=15)


class BusinessCreate(BusinessBase):
    content_preferences: ContentPreferencesSchema | None = None


class BusinessUpdate(APIRequest):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    segment: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=4000)
    target_audience: str | None = Field(default=None, max_length=2000)
    location: str | None = Field(default=None, max_length=180)
    brand_voice: str | None = Field(default=None, max_length=1000)
    additional_info: str | None = Field(default=None, max_length=4000)
    instagram_handle: str | None = Field(default=None, max_length=80)
    website: str | None = Field(default=None, max_length=255)
    differentiators: list[str] | None = Field(default=None, max_length=15)
    objectives: list[str] | None = Field(default=None, max_length=15)
    content_preferences: ContentPreferencesSchema | None = None


class BusinessRead(APIModel):
    id: uuid.UUID
    name: str
    segment: str
    description: str | None
    target_audience: str | None
    location: str | None
    brand_voice: str | None
    additional_info: str | None
    instagram_handle: str | None
    website: str | None
    differentiators: list[str]
    objectives: list[str]
    content_preferences: dict
    completeness_score: int
    created_at: datetime
    updated_at: datetime
