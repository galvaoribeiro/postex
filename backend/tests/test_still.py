"""Catalogo de apresentadoras e still mock, sem HTTP."""

from __future__ import annotations

import pytest

from app.ai.image.base import ImagePrompt
from app.ai.image.prompt import parse_size, size_for_format
from app.ai.presenters import load_presenters, pick_presenter
from app.ai.providers.mock_image_provider import MockImageProvider
from app.models.enums import ContentFormat


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
