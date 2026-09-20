"""Montagem do prompt de still.

A direcao criativa (pessoa, ambiente, roupa, look) vive num unico bloco
abaixo. O restante so injeta produto, cena da peca e o teto de seguranca.
"""

from __future__ import annotations

from app.ai.content_engine import ProductionResult
from app.ai.context_builder import BusinessContext
from app.ai.image.base import ImagePrompt
from app.models.enums import ContentFormat

# =============================================================================
# EDITE SOMENTE ESTE BLOCO
# =============================================================================
#
# Um unico lugar para descrever o still. Sempre que quiser mudar o visual,
# altere so o texto abaixo — persona, ambiente, roupa, pose, clima, camera.
#
# O que entra automaticamente no prompt final (titulo, conceito, direcao visual)
#   - regras duras de seguranca (adulta, ficticia, sem nu, sem menor)
#
# Escreva em ingles: o modelo de imagem lê este texto literalmente.

CREATIVE_BRIEF = """
Subject: Adult fictional Brazilian woman, approximately 30 years old, exceptionally attractive, tall and athletic, with a fit and naturally feminine physique, toned legs, defined waist, subtle abdominal definition, healthy proportions, long voluminous wavy hair, warm medium skin tone, defined facial features, expressive eyes and a natural confident smile. She has an elegant, approachable and sophisticated presence. She is entirely fictional and does not resemble any real person or celebrity.

Body & Pose: Full-body composition, head-to-toe visible, including both feet. Tall proportions and athletic physique clearly visible. Confident but natural upright posture, relaxed shoulders, subtle dynamic pose, as if presenting or wearing the product naturally. Realistic anatomy and proportions.

Clothing: Contemporary Brazilian fashion appropriate to the business and product being promoted. Prefer stylish short outfits, modern fitted dresses, coordinated sets, skirts, shorts, crop tops, or premium athletic wear when appropriate. For fitness-related businesses, use sophisticated gym clothing such as a fitted sports top, cropped athletic top, high-waisted shorts or leggings, and clean modern sneakers. Clothing may reveal a tasteful portion of the midriff, shoulders, arms and legs while remaining fashionable and commercially appropriate. Fully clothed; garments remain securely in place.

Environment: Create a realistic commercial environment specifically appropriate to the business segment, product, and scene provided later in the prompt. The environment must visually communicate what the business
does and why the product belongs there.
Do not default to a generic boutique, studio, showroom or lifestyle background. Adapt the location, architecture, furniture, props, surfaces, lighting and atmosphere to the actual business context.
For example, a fitness business should naturally suggest a premium gym, fitness studio or wellness environment; a fashion business should suggest a contemporary clothing boutique; a restaurant should show an appropriate restaurant environment; a beauty business should suggest a beauty salon or studio; a professional service should use an appropriate office or professional environment.
The environment should support the product and the creative concept without distracting from the main subject.

Lighting & Photography: Photorealistic high-end commercial photography, extremely high definition, realistic skin texture, natural skin details, premium fashion editorial quality, warm cinematic lighting, soft afternoon window light, subtle highlights and realistic shadows, shallow depth of field, natural bokeh, professional lens rendering, realistic fabric and material textures.

Composition: Vertical 9:16 portrait photograph, full-body framing, subject occupying most of the frame while leaving enough environmental context to communicate the business. Camera approximately at natural eye or slightly below eye level, realistic perspective, no excessive wide-angle distortion. Sharp focus on the woman, with the background naturally softened.

Visual Style: Luxury Brazilian commercial advertising, contemporary lifestyle photography, sophisticated but approachable, natural beauty, authentic Brazilian atmosphere, premium editorial aesthetic, realistic colors and materials.

Negative constraints: No text, no captions, no typography, no watermark, no invented logos, no celebrity resemblance, no distorted anatomy, no extra fingers or limbs, no cropped feet, no cropped head, no unnatural body proportions, no plastic-looking skin, no excessive retouching, no artificial pose, no nudity, no transparent clothing.
"""

# =============================================================================
# Fim do bloco editavel — daqui para baixo e montagem automatica
# =============================================================================

_HARD_SAFETY = (
    "The person is a fictional adult woman, clearly over 25 years old, "
    "with the appearance of a woman in her late twenties or thirties. "
    "Not a lookalike of any real celebrity. Garments stay on."
)

_HARD_NEGATIVE = (
    "child, underage, celebrity lookalike, extra limbs, deformed face, "
    "text overlay, watermark"
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
    seed: int,
) -> ImagePrompt:
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

    scene = _visual_from_production(production)
    prompt = "\n".join(
        [
            CREATIVE_BRIEF.strip(),
            offering_line,
            f"Scene: {scene}" if scene else "",
            f"Business: {context.name}. "
            f"Business segment: {context.segment}. "
            f"Location vibe: {context.location or 'Brazilian small business'}.",
            f" Brand: {context.name}.",
            _HARD_SAFETY,
        ]
    )
    return ImagePrompt(
        prompt=" ".join(prompt.split()),
        negative_prompt=" ".join(_HARD_NEGATIVE.split()),
        size=size_for_format(production.content_format),
        seed=seed,
    )
