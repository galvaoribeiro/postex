"""Montagem do prompt de still.

O texto descreve personagem + produto + cena. Restricoes de seguranca (adulta,
ficticia, vestida, sem celebridade) vao sempre no prompt, nao so no negativo.
"""

from __future__ import annotations

from app.ai.content_engine import ProductionResult
from app.ai.context_builder import BusinessContext
from app.ai.image.base import ImagePrompt
from app.ai.presenters import Presenter
from app.models.enums import ContentFormat

_SAFETY = (
    "The person is a fictional adult woman, clearly over 25 years old. "
    "Fully clothed commercial fashion photography. No nudity, no sexual content, "
    "no children, no teen appearance, not a lookalike of any real celebrity."
)


def size_for_format(content_format: ContentFormat) -> str:
    if content_format in {ContentFormat.REEL, ContentFormat.STORY}:
        return "1024x1792"
    return "1024x1024"


def parse_size(size: str) -> tuple[int, int]:
    width_s, height_s = size.lower().split("x", 1)
    return int(width_s), int(height_s)


def _visual_from_production(production: ProductionResult) -> str:
    payload = production.fields.get("payload") or {}
    bits: list[str] = []
    for key in ("title", "concept"):
        value = production.fields.get(key)
        if value:
            bits.append(str(value))
    for key in ("hook", "visual_direction", "headline", "cover_title", "on_image_text"):
        value = payload.get(key)
        if value:
            bits.append(str(value))
    scenes = payload.get("scenes") or payload.get("frames") or payload.get("slides") or []
    if scenes and isinstance(scenes[0], dict):
        visual = scenes[0].get("visual") or scenes[0].get("body") or scenes[0].get("title")
        if visual:
            bits.append(str(visual))
    return " ".join(bits)[:900]


def build_still_prompt(
    *,
    context: BusinessContext,
    production: ProductionResult,
    presenter: Presenter,
    seed: int,
) -> ImagePrompt:
    focused = next((item for item in context.products if item.is_focus), None)
    focused_service = next((item for item in context.services if item.is_focus), None)
    offering = focused or focused_service
    offering_line = ""
    if offering:
        offering_line = (
            f"The commercial subject is '{offering.name}'. "
            f"{offering.description or ''} "
            "Show the real product/service honestly; do not invent labels or claims."
        )
    else:
        offering_line = (
            f"The scene represents the brand {context.name} ({context.segment}). "
            "No invented product packaging."
        )

    scene = _visual_from_production(production)
    prompt = "\n".join(
        [
            presenter.visual_prompt,
            f"Appearance: {presenter.appearance}",
            f"Clothing: {presenter.clothing_style}",
            offering_line,
            f"Scene: {scene}" if scene else "",
            f"Location vibe: {context.location or 'Brazilian small business'}."
            f" Brand: {context.name}.",
            "Vertical 9:16 Instagram still, photorealistic, high-end commercial lighting, "
            "shallow depth of field, no text overlay, no watermark, no logo invented.",
            _SAFETY,
        ]
    )
    return ImagePrompt(
        prompt=" ".join(prompt.split()),
        negative_prompt=presenter.negative_prompt,
        size=size_for_format(production.content_format),
        seed=seed,
        presenter_id=presenter.id,
    )
