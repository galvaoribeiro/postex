"""Montagem do prompt de imagem comercial.

Produto, marca e cena da peca entram no comeco (Flux atende sobretudo o
inicio do texto). A direcao visual e derivada do negocio e do destino —
nao ha persona fixa.
"""

from __future__ import annotations

from app.ai.content_engine import ProductionResult
from app.ai.context_builder import BusinessContext
from app.ai.image.base import ImagePrompt
from app.ai.prompts.platforms import still_aspect
from app.models.enums import CampaignDestination, ContentFormat

_HARD_SAFETY = (
    "If a person appears, they must be a fictional adult clearly over 25 years old. "
    "Not a lookalike of any real celebrity. Fully clothed; garments stay on."
)

_HARD_NEGATIVE = (
    "child, underage, celebrity lookalike, extra limbs, deformed face, "
    "text overlay, watermark, logo invention, unreadable labels"
)

_REFERENCE_FIDELITY = (
    "PRODUCT FIDELITY: Keep the product from the reference photo identical — "
    "same shape, color, packaging and labels. Do not replace it with an invented "
    "product. Restage that same product in a new commercial photograph. This is a "
    "restage, not a background edit."
)

_COMMERCIAL_DIRECTION = """
Hero: the real product is the star of the frame. Show it clearly, honestly and
desirably. Lighting should sell material, color and texture.

Environment: match architecture, furniture, props and atmosphere to THIS business
and product. A cafe looks like a cafe; a boutique like a boutique. Do not default
to a gym, generic studio or stock lifestyle set unless that is this business.

People (optional): only include a person if it helps sell the product in use.
Any person is a fictional adult over 25, dressed as a real customer of this
business would dress. Natural pose, realistic anatomy, no celebrity resemblance.

Photography: photorealistic high-end commercial advertising, sharp product focus,
natural color, premium but approachable Brazilian commercial look.

Negative constraints: no text, captions, typography, watermark or invented logos.
No distorted anatomy, extra fingers, cropped product, plastic skin or nudity.
"""


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
    for key in ("hook", "visual_direction", "headline", "cover_title", "on_screen_text"):
        value = payload.get(key)
        if value:
            bits.append(str(value))
    scenes = payload.get("scenes") or payload.get("frames") or payload.get("slides") or []
    if scenes and isinstance(scenes[0], dict):
        visual = scenes[0].get("visual") or scenes[0].get("body") or scenes[0].get("title")
        if visual:
            bits.append(str(visual))
    return " ".join(bits)[:900]


def _join_prompt(*parts: str) -> str:
    return "\n\n".join(part.strip() for part in parts if part and part.strip())


def build_still_prompt(
    *,
    context: BusinessContext,
    production: ProductionResult,
    seed: int,
    has_reference: bool = False,
    destination: CampaignDestination | None = None,
) -> ImagePrompt:
    focused = next((item for item in context.products if item.is_focus), None)
    focused_service = next((item for item in context.services if item.is_focus), None)
    offering = focused or focused_service
    location = context.location or "Brazilian small business"
    dest_label = destination.value.replace("_", " ").title() if destination else "Instagram"
    if offering:
        offering_line = (
            f"Product in frame: '{offering.name}'. "
            f"{offering.description or ''} "
            "Show the real product honestly; do not invent labels or claims."
        )
    else:
        offering_line = (
            f"The scene represents the brand {context.name} ({context.segment}). "
            "No invented product packaging."
        )

    scene = _visual_from_production(production)
    commercial = _join_prompt(
        (
            f"COMMERCIAL PHOTO for {dest_label}: photorealistic advertisement for "
            f"{context.name}, a {context.segment} in {location}."
        ),
        offering_line,
        f"Scene: {scene}" if scene else "",
        (
            "The product, props and background MUST match this business. "
            "Do not substitute a gym, boutique, studio or generic lifestyle set "
            "unless that is this business."
        ),
    )
    size = (
        still_aspect(destination, production.content_format)
        if destination is not None
        else size_for_format(production.content_format)
    )
    prompt = _join_prompt(
        _REFERENCE_FIDELITY if has_reference else "",
        commercial,
        _COMMERCIAL_DIRECTION.strip(),
        _HARD_SAFETY,
    )
    return ImagePrompt(
        prompt=prompt,
        negative_prompt=" ".join(_HARD_NEGATIVE.split()),
        size=size,
        seed=seed,
    )
