"""Montagem do prompt de still.

O texto descreve personagem + produto + cena. O teto de seguranca (adulta,
ficticia, sem nu, sem menor, sem celebridade) vale em qualquer tom. O tom
ousado so troca roupa e enquadramento.
"""

from __future__ import annotations

from app.ai.content_engine import ProductionResult
from app.ai.context_builder import BusinessContext
from app.ai.image.base import ImagePrompt
from app.ai.presenters import Presenter
from app.models.enums import ContentFormat, VisualTone

_HARD_SAFETY = (
    "The person is a fictional adult woman, clearly over 25 years old, "
    "with the appearance of a woman in her late twenties or thirties. "
    "Not a lookalike of any real celebrity. Garments stay on."
)

_COMMERCIAL_LOOK = (
    "Fully clothed commercial fashion photography. Everyday boutique styling, "
    "tasteful and suitable for a brand feed."
)

_DARING_LOOK = (
    "Tasteful adult campaign photography: lingerie or beachwear (bikini), "
    "editorial fashion lighting. Skin may show on shoulders, waist, legs and "
    "tasteful cleavage. Garments stay on. Fashion editorial, campaign still."
)

_HARD_NEGATIVE = (
    "child, underage, celebrity lookalike, extra limbs, deformed face, "
    "text overlay, watermark"
)

_DARING_NEGATIVE = "adult-film, see-through exposing too much"


def size_for_format(content_format: ContentFormat) -> str:
    if content_format in {ContentFormat.REEL, ContentFormat.STORY}:
        return "1024x1792"
    return "1024x1024"


def parse_size(size: str) -> tuple[int, int]:
    width_s, height_s = size.lower().split("x", 1)
    return int(width_s), int(height_s)


def parse_visual_tone(value: object) -> VisualTone:
    if isinstance(value, VisualTone):
        return value
    if isinstance(value, str):
        try:
            return VisualTone(value.upper())
        except ValueError:
            return VisualTone.COMMERCIAL
    return VisualTone.COMMERCIAL


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
    visual_tone: VisualTone | str = VisualTone.COMMERCIAL,
) -> ImagePrompt:
    tone = parse_visual_tone(visual_tone)
    focused = next((item for item in context.products if item.is_focus), None)
    focused_service = next((item for item in context.services if item.is_focus), None)
    offering = focused or focused_service
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

    if tone is VisualTone.DARING:
        clothing_line = (
            "Clothing: adult campaign lingerie or swimsuit; garments remain on; "
            "editorial body-positive framing, fashion campaign."
        )
        look = _DARING_LOOK
        negative = f"{presenter.negative_prompt}, {_HARD_NEGATIVE}, {_DARING_NEGATIVE}"
        visual = (
            presenter.visual_prompt.replace("fully clothed", "campaign styling")
            .replace("Fully clothed", "campaign styling")
        )
    else:
        clothing_line = f"Clothing: {presenter.clothing_style}"
        look = _COMMERCIAL_LOOK
        negative = f"{presenter.negative_prompt}, {_HARD_NEGATIVE}"
        visual = presenter.visual_prompt

    scene = _visual_from_production(production)
    prompt = "\n".join(
        [
            visual,
            f"Appearance: {presenter.appearance}",
            clothing_line,
            offering_line,
            f"Scene: {scene}" if scene else "",
            f"Location vibe: {context.location or 'Brazilian small business'}."
            f" Brand: {context.name}.",
            "Vertical 9:16 still, photorealistic, high-end commercial lighting, "
            "shallow depth of field, no text overlay, no watermark, no logo invented.",
            _HARD_SAFETY,
            look,
        ]
    )
    return ImagePrompt(
        prompt=" ".join(prompt.split()),
        negative_prompt=" ".join(negative.split()),
        size=size_for_format(production.content_format),
        seed=seed,
        presenter_id=presenter.id,
    )
