"""Metadados da camada de IA consumidos pela interface."""

from __future__ import annotations

from fastapi import APIRouter

from app.ai.content_engine import MAX_IDEAS_PER_RUN
from app.ai.production import all_strategies
from app.ai.image.registry import get_image_provider
from app.ai.registry import get_ai_provider
from app.ai.taxonomy import get_taxonomy
from app.ai.video.registry import get_video_provider
from app.core.config import settings
from app.core.deps import CurrentUser
from app.schemas.ai import (
    AICapabilitiesRead,
    CategoryRead,
    FormatRead,
    TaxonomyRead,
)

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get(
    "/taxonomy",
    response_model=TaxonomyRead,
    summary="Pilares editoriais configurados em content_taxonomy.yaml",
)
async def get_taxonomy_endpoint(user: CurrentUser) -> TaxonomyRead:
    taxonomy = get_taxonomy()
    return TaxonomyRead(
        version=taxonomy.version,
        categories=[
            CategoryRead(
                key=category.key,
                label=category.label,
                description=category.description,
                objective=category.objective,
                recommended_formats=list(category.recommended_formats),
                weight=category.weight,
            )
            for category in taxonomy.categories
        ],
    )


@router.get(
    "/formats",
    response_model=list[FormatRead],
    summary="Formatos de conteudo suportados e o schema de cada payload",
)
async def list_formats(user: CurrentUser) -> list[FormatRead]:
    return [FormatRead.model_validate(strategy.describe()) for strategy in all_strategies()]


@router.get("/capabilities", response_model=AICapabilitiesRead)
async def get_capabilities(user: CurrentUser) -> AICapabilitiesRead:
    provider = get_ai_provider()
    image = get_image_provider()
    video = get_video_provider()
    return AICapabilitiesRead(
        provider=provider.name,
        model=provider.default_model,
        supports_vision=provider.supports_vision,
        image_provider=image.name,
        image_model=image.default_model,
        video_provider=video.name,
        video_model=video.default_model,
        execution_mode=settings.AI_EXECUTION_MODE.value,
        taxonomy_version=get_taxonomy().version,
        default_idea_count=settings.AI_DEFAULT_IDEA_COUNT,
        max_ideas_per_run=MAX_IDEAS_PER_RUN,
    )
