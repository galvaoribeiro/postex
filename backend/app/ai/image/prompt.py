"""Montagem do prompt de still.

A direcao criativa (pessoa, ambiente, roupa, look) vive num unico bloco
abaixo. Produto, marca e cena da peca entram ANTES desse bloco — Flux
atende sobretudo o comeco do texto (CLIP ~77 tokens, T5 ~512).
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
# O que entra sozinho, ANTES deste bloco (nao precisa repetir aqui):
#   - produto/servico em foco e nome da marca
#   - cena extraida da peca (titulo, conceito, direcao visual)
#   - regras duras de seguranca (adulta, ficticia, sem nu, sem menor)
#
# Escreva em ingles: o modelo de imagem lê este texto literalmente.
# No Flux, o começo do prompt pesa mais: evite listar academia/shorts/crop
# como default, senão esses visuais vencem o produto.

CREATIVE_BRIEF = """
Subject: Adult fictional Brazilian woman, approximately 30 years old, exceptionally attractive, tall, with a fit and naturally feminine physique, healthy proportions, long voluminous wavy hair, warm medium skin tone, defined facial features, expressive eyes and a natural confident smile. She has an elegant, approachable and sophisticated presence. She is entirely fictional and does not resemble any real person or celebrity.

Body & Pose: Full-body composition, head-to-toe visible, including both feet. Confident but natural upright posture, relaxed shoulders, subtle dynamic pose, as if presenting or using the product naturally. Realistic anatomy and proportions.

Clothing: Contemporary Brazilian fashion that matches the business and product at the start of this prompt. Dress her as a real customer or staff of THIS business would dress. Do not default to gym wear, crop tops, shorts or athletic clothing unless the business is fitness, sports or beachwear. Fully clothed; garments remain securely in place.

Environment: Match architecture, furniture, props, lighting and atmosphere to the business, product and scene at the start of this prompt. A cafe must look like a cafe; a restaurant like a restaurant; a boutique like a boutique. Do not default to a gym, generic studio, showroom or lifestyle backdrop.

Lighting & Photography: Photorealistic high-end commercial photography, extremely high definition, realistic skin texture, natural skin details, premium fashion editorial quality, warm cinematic lighting, soft afternoon window light, subtle highlights and realistic shadows, shallow depth of field, natural bokeh, professional lens rendering, realistic fabric and material textures.

Composition: Vertical 9:16 portrait photograph, full-body framing, subject occupying most of the frame while leaving enough environmental context to communicate the business. Camera approximately at natural eye or slightly below eye level, realistic perspective, no excessive wide-angle distortion. Sharp focus on the woman, with the background naturally softened.

Visual Style: Luxury Brazilian commercial advertising, contemporary lifestyle photography, sophisticated but approachable, natural beauty, authentic Brazilian atmosphere, premium editorial aesthetic, realistic colors and materials.

Negative constraints: No text, no captions, no typography, no watermark, no invented logos, no celebrity resemblance, no distorted anatomy, no extra fingers or limbs, no cropped feet, no cropped head, no unnatural body proportions, no plastic-looking skin, no excessive retouching, no artificial pose, no nudity, no transparent clothing. No gym, athletic wear or fitness studio unless the business is fitness.
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
    "text overlay, watermark, gym interior unless fitness business"
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


def _join_prompt(*parts: str) -> str:
    return "\n\n".join(part.strip() for part in parts if part and part.strip())


def build_still_prompt(
    *,
    context: BusinessContext,
    production: ProductionResult,
    seed: int,
) -> ImagePrompt:
    focused = next((item for item in context.products if item.is_focus), None)
    focused_service = next((item for item in context.services if item.is_focus), None)
    offering = focused or focused_service
    location = context.location or "Brazilian small business"
    if offering:
        offering_line = (
            f"Product in frame: '{offering.name}'. "
            f"{offering.description or ''} "
            "Show the real product/service honestly in her hands or clearly in use; "
            "do not invent labels or claims."
        )
    else:
        offering_line = (
            f"The scene represents the brand {context.name} ({context.segment}). "
            "No invented product packaging."
        )

    scene = _visual_from_production(production)
    # Flux: CLIP/T5 leem o comeco. Negocio e produto precisam vir primeiro.
    commercial = _join_prompt(
        (
            f"COMMERCIAL PHOTO: photorealistic advertisement for {context.name}, "
            f"a {context.segment} in {location}."
        ),
        offering_line,
        f"Scene: {scene}" if scene else "",
        (
            "The woman, her clothing, the props in her hands and the background "
            "MUST match this business and product. Do not substitute a gym, "
            "boutique, studio or generic lifestyle set unless that is this business."
        ),
    )
    prompt = _join_prompt(
        commercial,
        CREATIVE_BRIEF.strip(),
        _HARD_SAFETY,
    )
    return ImagePrompt(
        prompt=prompt,
        negative_prompt=" ".join(_HARD_NEGATIVE.split()),
        size=size_for_format(production.content_format),
        seed=seed,
    )
