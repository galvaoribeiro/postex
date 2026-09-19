"""Schemas de metadados da camada de IA.

Expor a taxonomia e os formatos pela API mantem a interface sempre alinhada com
o backend: adicionar um pilar no YAML ou um formato novo aparece no frontend sem
alteracao de codigo lá.
"""

from __future__ import annotations

from typing import Any

from app.models.enums import ContentFormat
from app.schemas.common import APIModel


class CategoryRead(APIModel):
    key: str
    label: str
    description: str
    objective: str
    recommended_formats: list[ContentFormat]
    weight: int


class FormatRead(APIModel):
    format: ContentFormat
    label: str
    body_label: str
    payload_schema: dict[str, Any]


class AICapabilitiesRead(APIModel):
    provider: str
    model: str
    supports_vision: bool
    image_provider: str
    image_model: str
    execution_mode: str
    taxonomy_version: int
    default_idea_count: int
    max_ideas_per_run: int


class TaxonomyRead(APIModel):
    version: int
    categories: list[CategoryRead]
