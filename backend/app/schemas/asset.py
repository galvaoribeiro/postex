"""Schemas da biblioteca de assets."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import Field

from app.models.enums import AssetKind, AssetStatus
from app.schemas.common import APIModel, APIRequest


class AssetUploadRequest(APIRequest):
    filename: str = Field(min_length=1, max_length=255)
    mime_type: str = Field(min_length=3, max_length=120)
    size_bytes: int | None = Field(default=None, ge=1)
    kind: AssetKind = AssetKind.OTHER
    title: str | None = Field(default=None, max_length=180)
    alt_text: str | None = Field(default=None, max_length=500)
    tags: list[str] = Field(default_factory=list, max_length=12)
    product_id: uuid.UUID | None = None
    service_id: uuid.UUID | None = None


class AssetUploadResponse(APIModel):
    """Instrucoes para o browser enviar o arquivo direto ao storage."""

    asset_id: uuid.UUID
    upload_url: str
    method: str
    headers: dict[str, str]
    expires_in: int


class AssetConfirmRequest(APIRequest):
    size_bytes: int | None = Field(default=None, ge=1)
    width: int | None = Field(default=None, ge=1, le=20000)
    height: int | None = Field(default=None, ge=1, le=20000)
    analyze: bool = Field(
        default=False,
        description=(
            "Se verdadeiro, enfileira analise de visao. A imagem e util como "
            "contexto mesmo sem analise."
        ),
    )


class AssetUpdate(APIRequest):
    kind: AssetKind | None = None
    title: str | None = Field(default=None, max_length=180)
    alt_text: str | None = Field(default=None, max_length=500)
    tags: list[str] | None = Field(default=None, max_length=12)
    product_id: uuid.UUID | None = None
    service_id: uuid.UUID | None = None


class AssetRead(APIModel):
    id: uuid.UUID
    business_id: uuid.UUID
    product_id: uuid.UUID | None
    service_id: uuid.UUID | None
    kind: AssetKind
    status: AssetStatus
    original_filename: str
    mime_type: str
    size_bytes: int | None
    width: int | None
    height: int | None
    duration_seconds: int | None = None
    title: str | None
    alt_text: str | None
    tags: list[str]
    ai_analysis: dict | None
    created_at: datetime
    #: URL assinada de leitura, gerada a cada resposta. Curta duracao.
    url: str | None = None


class AssetAnalyzeResponse(APIModel):
    job_id: uuid.UUID
    asset_id: uuid.UUID
