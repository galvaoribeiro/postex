"""Still mock e montagem de prompt, sem HTTP."""

from __future__ import annotations

import pytest

from app.ai.image.base import ImagePrompt
from app.ai.content_engine import ProductionResult
from app.ai.image.prompt import CREATIVE_BRIEF, build_still_prompt, parse_size, size_for_format
from app.ai.providers.mock_image_provider import MockImageProvider
from app.models.enums import ContentFormat


@pytest.mark.asyncio
async def test_mock_image_provider_returns_png() -> None:
    generated = await MockImageProvider().generate(
        ImagePrompt(
            prompt="Still comercial de vestido preto com adulta ficticia",
            size="1024x1792",
            seed=1,
        )
    )
    assert generated.mime_type == "image/png"
    assert generated.data[:8] == b"\x89PNG\r\n\x1a\n"
    assert generated.provider == "mock"
    assert generated.width > 0 and generated.height > generated.width


def test_size_for_reel_is_portrait() -> None:
    assert size_for_format(ContentFormat.REEL) == "1024x1792"
    width, height = parse_size("1024x1024")
    assert width == height


def _prompt_context() -> object:
    return type(
        "Ctx",
        (),
        {
            "name": "Cafeteria Aroma",
            "segment": "cafeteria",
            "location": "Sao Paulo",
            "products": (),
            "services": (),
        },
    )()


def test_still_prompt_uses_creative_brief() -> None:
    request = build_still_prompt(
        context=_prompt_context(),  # type: ignore[arg-type]
        production=ProductionResult(
            content_format=ContentFormat.REEL,
            fields={"title": "Cafe", "concept": "Aroma", "payload": {}},
            context_snapshot={},
        ),
        seed=1,
    )
    low = request.prompt.lower()
    brief = " ".join(CREATIVE_BRIEF.split()).lower()
    assert brief in low
    assert "cafeteria aroma" in low
    assert "cafe" in low
    assert "over 25" in low
    assert "child" in request.negative_prompt.lower()
