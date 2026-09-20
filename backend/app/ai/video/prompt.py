"""Prompt de video comercial vertical, condicionado a foto do produto."""

from __future__ import annotations

from app.ai.content_engine import ProductionResult
from app.ai.context_builder import BusinessContext
from app.ai.prompts.platforms import video_duration
from app.ai.video.base import VideoPrompt
from app.models.enums import CampaignDestination

_NEGATIVE = (
    "text overlay, watermark, distorted product, extra limbs, child, "
    "celebrity lookalike, shaky unusable footage"
)


def build_video_prompt(
    *,
    context: BusinessContext,
    production: ProductionResult,
    seed: int,
    destination: CampaignDestination,
    has_reference: bool = False,
) -> VideoPrompt:
    focused = next((item for item in context.products if item.is_focus), None)
    product_name = focused.name if focused else context.name
    payload = production.fields.get("payload") or {}
    hook = payload.get("hook") or production.fields.get("title") or product_name
    visual = ""
    scenes = payload.get("scenes") or []
    if scenes and isinstance(scenes[0], dict):
        visual = str(scenes[0].get("visual") or "")
    fidelity = (
        "Keep the product from the reference image identical in shape, color and labels. "
        if has_reference
        else ""
    )
    dest = {
        CampaignDestination.INSTAGRAM: "Instagram Reels style commercial, 9:16.",
        CampaignDestination.TIKTOK: "Native TikTok commercial, fast hook, 9:16.",
        CampaignDestination.TIKTOK_SHOP: (
            "TikTok Shop product video: product hero, benefit, buy-now energy, 9:16."
        ),
    }[destination]
    prompt = (
        f"{dest} Photorealistic vertical video advertising '{product_name}' for "
        f"{context.name}, a {context.segment}. {fidelity}"
        f"Opening hook: {hook}. {visual} "
        "Smooth commercial camera, product clearly visible, no on-screen text."
    )
    return VideoPrompt(
        prompt=prompt.strip(),
        negative_prompt=_NEGATIVE,
        aspect_ratio="9:16",
        duration_seconds=video_duration(destination),
        seed=seed,
    )
