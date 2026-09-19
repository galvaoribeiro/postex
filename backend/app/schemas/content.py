"""Schemas de ideias, conteudos e versoes."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import Field, model_validator

from app.models.enums import (
    ContentAssetRole,
    ContentFormat,
    ContentObjective,
    ContentStatus,
    IdeaStatus,
    RegenerationScope,
    VersionAuthor,
    VisualTone,
)
from app.schemas.asset import AssetRead
from app.schemas.common import APIModel, APIRequest

MAX_IDEAS_PER_REQUEST = 12


# ----------------------------------------------------------------- ideias ----


class IdeaGenerateRequest(APIRequest):
    count: int = Field(default=5, ge=1, le=MAX_IDEAS_PER_REQUEST)
    categories: list[str] = Field(
        default_factory=list,
        max_length=MAX_IDEAS_PER_REQUEST,
        description="Chaves da taxonomia. Vazio deixa o motor distribuir entre os pilares.",
    )
    format_hint: ContentFormat | None = None
    instruction: str | None = Field(default=None, max_length=600)


class ContentIdeaRead(APIModel):
    id: uuid.UUID
    business_id: uuid.UUID
    title: str
    concept: str
    objective: str
    category: str
    suggested_format: ContentFormat
    rationale: str | None
    hook_suggestion: str | None
    audience_note: str | None
    relevance_score: int
    referenced_products: list[str]
    referenced_services: list[str]
    status: IdeaStatus
    job_id: uuid.UUID | None
    created_at: datetime


class IdeaStatusUpdate(APIRequest):
    status: IdeaStatus


# --------------------------------------------------------------- conteudos ---


class ContentGenerateRequest(APIRequest):
    """Pedido de criacao em um passo: produto/objetivo -> job unico -> preview."""

    product_id: uuid.UUID | None = None
    service_id: uuid.UUID | None = None
    objective: ContentObjective
    format: ContentFormat | None = Field(
        default=None, description="None deixa o motor escolher; a UI do MVP nao oferece seletor."
    )
    answers: dict[str, str] = Field(default_factory=dict)
    planned_date: date | None = None
    visual_tone: VisualTone = VisualTone.COMMERCIAL

    @model_validator(mode="after")
    def validate_item_for_objective(self) -> ContentGenerateRequest:
        if self.product_id and self.service_id:
            raise ValueError("Informe produto ou servico, nao os dois.")
        if self.objective is ContentObjective.SELL and not self.product_id and not self.service_id:
            raise ValueError("Para vender, escolha um produto ou servico.")
        return self


class QuestionOption(APIModel):
    value: str
    label: str


class CreationQuestion(APIModel):
    key: str
    question: str
    kind: str
    options: list[QuestionOption] = Field(default_factory=list)
    optional: bool = True
    persist_to: str | None = None


class ContentFromIdeaRequest(APIRequest):
    idea_id: uuid.UUID
    format: ContentFormat | None = Field(
        default=None, description="Sobrepoe o formato sugerido na ideacao."
    )
    instruction: str | None = Field(default=None, max_length=600)
    planned_date: date | None = None


class ContentManualCreate(APIRequest):
    title: str = Field(min_length=2, max_length=240)
    format: ContentFormat
    category: str | None = Field(default=None, max_length=64)
    concept: str | None = Field(default=None, max_length=2000)
    objective: str | None = Field(default=None, max_length=2000)
    caption: str | None = Field(default=None, max_length=4000)
    cta: str | None = Field(default=None, max_length=500)
    hashtags: list[str] = Field(default_factory=list, max_length=30)
    planned_date: date | None = None


class ContentUpdate(APIRequest):
    title: str | None = Field(default=None, min_length=2, max_length=240)
    concept: str | None = Field(default=None, max_length=2000)
    objective: str | None = Field(default=None, max_length=2000)
    category: str | None = Field(default=None, max_length=64)
    caption: str | None = Field(default=None, max_length=4000)
    cta: str | None = Field(default=None, max_length=500)
    hashtags: list[str] | None = Field(default=None, max_length=30)
    planned_date: date | None = None
    #: Estrutura especifica do formato. Validada contra o schema do formato.
    payload: dict[str, Any] | None = None
    change_reason: str | None = Field(default=None, max_length=300)


class ContentStatusUpdate(APIRequest):
    status: ContentStatus
    planned_date: date | None = None
    reason: str | None = Field(default=None, max_length=300)


class ContentScheduleRequest(APIRequest):
    planned_date: date


class ContentRegenerateRequest(APIRequest):
    scope: RegenerationScope = RegenerationScope.FULL
    instruction: str | None = Field(
        default=None,
        max_length=600,
        description='Ex.: "mantenha a ideia, mas deixe o roteiro mais curto".',
    )


class ContentChangeFormatRequest(APIRequest):
    format: ContentFormat
    regenerate: bool = Field(
        default=True,
        description=(
            "Se verdadeiro, a IA reescreve o conteudo no novo formato. Se falso, "
            "apenas o formato muda e o payload e reiniciado."
        ),
    )
    instruction: str | None = Field(default=None, max_length=600)


class ContentDuplicateRequest(APIRequest):
    title: str | None = Field(default=None, min_length=2, max_length=240)


class ContentAssetLinkRequest(APIRequest):
    asset_id: uuid.UUID
    role: ContentAssetRole = ContentAssetRole.REFERENCE
    position: int = Field(default=0, ge=0, le=50)


class ContentAssetRead(APIModel):
    asset: AssetRead
    role: ContentAssetRole
    position: int


class ContentRead(APIModel):
    id: uuid.UUID
    business_id: uuid.UUID
    idea_id: uuid.UUID | None
    title: str
    concept: str | None
    objective: str | None
    category: str | None
    format: ContentFormat
    status: ContentStatus
    caption: str | None
    cta: str | None
    hashtags: list[str]
    payload: dict[str, Any]
    planned_date: date | None
    published_at: datetime | None
    current_version: int
    created_at: datetime
    updated_at: datetime
    presenter_name: str | None = None
    assets: list[ContentAssetRead] = Field(default_factory=list)
    allowed_transitions: list[ContentStatus] = Field(default_factory=list)


class ContentSummary(APIModel):
    """Versao enxuta, usada em listagens, dashboard e calendario."""

    id: uuid.UUID
    title: str
    format: ContentFormat
    status: ContentStatus
    category: str | None
    planned_date: date | None
    current_version: int
    updated_at: datetime


class ContentActionResponse(APIModel):
    """Resposta de acoes que podem ou nao disparar trabalho de IA.

    `job_id` vem preenchido quando a acao enfileirou geracao; nesse caso o
    conteudo devolvido e o estado atual, ainda sem o resultado da IA.
    """

    content: ContentRead
    job_id: uuid.UUID | None = None


class ContentVersionRead(APIModel):
    id: uuid.UUID
    content_id: uuid.UUID
    version: int
    author: VersionAuthor
    change_reason: str | None
    ai_instruction: str | None
    regeneration_scope: RegenerationScope | None
    snapshot: dict[str, Any]
    created_at: datetime
