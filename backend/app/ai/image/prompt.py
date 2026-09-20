"""Montagem do prompt de imagem comercial.

Fatos da campanha (produto, marca, destino) entram no comeco — o Flux atende
sobretudo o inicio do texto. Em seguida vem um unico CREATIVE BRIEF: selfie
no espelho + integracao inteligente do produto.
"""

from __future__ import annotations

from app.ai.content_engine import ProductionResult
from app.ai.context_builder import BusinessContext
from app.ai.image.base import ImagePrompt
from app.ai.prompts.creative import (
    CHARACTER_BRIEF,
    HARD_SAFETY,
    STILL_NEGATIVE,
    campaign_header,
    still_creative_block,
)
from app.ai.prompts.platforms import still_aspect
from app.models.enums import CampaignDestination, ContentFormat


def size_for_format(content_format: ContentFormat) -> str:
    if content_format in {ContentFormat.REEL, ContentFormat.STORY}:
        return "1024x1792"
    return "1024x1024"


def parse_size(size: str) -> tuple[int, int]:
    width_s, height_s = size.lower().split("x", 1)
    return int(width_s), int(height_s)


def _join_prompt(*parts: str) -> str:
    return "\n\n".join(part.strip() for part in parts if part and part.strip())


def build_talent_prompt(*, seed: int) -> ImagePrompt:
    """Still so da modelo, sem produto. O usuario valida antes da campanha."""
    return ImagePrompt(
        prompt=_join_prompt(CHARACTER_BRIEF, HARD_SAFETY),
        negative_prompt=" ".join(STILL_NEGATIVE.split()),
        size="1024x1792",
        seed=seed,
    )


def build_still_prompt(
    *,
    context: BusinessContext,
    production: ProductionResult,
    seed: int,
    has_reference: bool = False,
    has_model: bool = False,
    destination: CampaignDestination | None = None,
) -> ImagePrompt:
    header = campaign_header(
        context=context,
        production=production,
        destination=destination,
    )
    prompt = _join_prompt(
        header,
        still_creative_block(has_reference=has_reference, has_model=has_model),
        HARD_SAFETY,
    )
    size = (
        still_aspect(destination, production.content_format)
        if destination is not None
        else "1024x1792"
    )
    return ImagePrompt(
        prompt=prompt,
        negative_prompt=" ".join(STILL_NEGATIVE.split()),
        size=size,
        seed=seed,
    )
