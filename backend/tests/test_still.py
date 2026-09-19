"""Catalogo de apresentadoras e still mock, sem HTTP."""

from __future__ import annotations

import pytest

from app.ai.image.base import ImagePrompt
from app.ai.content_engine import ProductionResult
from app.ai.image.prompt import build_still_prompt, parse_size, parse_visual_tone, size_for_format
from app.ai.presenters import load_presenters, pick_presenter
from app.ai.providers.mock_image_provider import MockImageProvider
from app.models.enums import ContentFormat, VisualTone


def test_presenters_are_adult_and_named() -> None:
    catalog = load_presenters()
    names = {item.id for item in catalog}
    assert {"lara", "camila", "bianca"} <= names
    assert all(item.adult_confirmed for item in catalog)
    for item in catalog:
        low, high = (int(part) for part in item.age_range.split("-"))
        assert low >= 25
        assert high >= low


def test_pick_presenter_is_deterministic() -> None:
    first = pick_presenter(42, segment="moda feminina")
    second = pick_presenter(42, segment="moda feminina")
    assert first.id == second.id


@pytest.mark.asyncio
async def test_mock_image_provider_returns_png() -> None:
    presenter = pick_presenter(1)
    generated = await MockImageProvider().generate(
        ImagePrompt(
            prompt="Still comercial de vestido preto com apresentadora adulta ficticia",
            size="1024x1792",
            seed=1,
            presenter_id=presenter.id,
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


def test_commercial_prompt_stays_clothed() -> None:
    presenter = pick_presenter(1)
    request = build_still_prompt(
        context=_prompt_context(),  # type: ignore[arg-type]
        production=ProductionResult(
            content_format=ContentFormat.REEL,
            fields={"title": "Cafe", "concept": "Aroma", "payload": {}},
            context_snapshot={},
        ),
        presenter=presenter,
        seed=1,
        visual_tone=VisualTone.COMMERCIAL,
    )
    low = request.prompt.lower()
    assert "over 25" in low
    assert "fully clothed" in low
    assert "lingerie" not in low
    assert "child" in request.negative_prompt.lower()


def test_daring_prompt_is_campaign_not_explicit() -> None:
    presenter = pick_presenter(1)
    request = build_still_prompt(
        context=_prompt_context(),  # type: ignore[arg-type]
        production=ProductionResult(
            content_format=ContentFormat.REEL,
            fields={"title": "Cafe", "concept": "Aroma", "payload": {}},
            context_snapshot={},
        ),
        presenter=presenter,
        seed=1,
        visual_tone=VisualTone.DARING,
    )
    low = request.prompt.lower()
    negative = request.negative_prompt.lower()
    assert "lingerie" in low or "beachwear" in low or "swimsuit" in low
    assert "garments stay on" in low or "garments remain on" in low
    assert "over 25" in low
    assert "fully clothed" not in low
    assert "child" in negative
    assert parse_visual_tone("daring") is VisualTone.DARING
