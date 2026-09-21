"""Prompt de video: continua a selfie no espelho a partir do still."""

from __future__ import annotations

from app.ai.content_engine import ProductionResult
from app.ai.context_builder import BusinessContext
from app.ai.prompts.creative import (
    HARD_SAFETY,
    VIDEO_NEGATIVE,
    campaign_header,
    spoken_intent,
    video_creative_block,
)
from app.ai.prompts.platforms import video_duration
from app.ai.video.base import VideoPrompt
from app.core.config import settings
from app.models.enums import CampaignDestination


def _speech_language(model: str) -> str:
    """Kling so sintetiza ingles/chines; Veo e Seedance seguem o prompt."""
    return "en" if "kling" in (model or "").lower() else "pt"


def _join_prompt(*parts: str) -> str:
    return "\n\n".join(part.strip() for part in parts if part and part.strip())


def build_video_prompt(
    *,
    context: BusinessContext,
    production: ProductionResult,
    seed: int,
    destination: CampaignDestination,
    has_reference: bool = False,
) -> VideoPrompt:
    duration = video_duration(destination)
    prompt = _join_prompt(
        campaign_header(
            context=context,
            production=production,
            destination=destination,
            duration_seconds=duration,
        ),
        video_creative_block(
            duration_seconds=duration,
            has_reference=has_reference,
            spoken_intent=spoken_intent(production),
            speech_language=_speech_language(settings.FAL_VIDEO_MODEL),
        ),
        HARD_SAFETY,
    )
    return VideoPrompt(
        prompt=prompt.strip(),
        negative_prompt=" ".join(VIDEO_NEGATIVE.split()),
        aspect_ratio="9:16",
        duration_seconds=duration,
        seed=seed,
        generate_audio=settings.FAL_VIDEO_GENERATE_AUDIO,
        end_user_id=(
            str(context.business_id) if getattr(context, "business_id", None) else None
        ),
    )
