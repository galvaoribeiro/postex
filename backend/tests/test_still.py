"""Still mock e montagem de prompt, sem HTTP."""

from __future__ import annotations

import base64
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.ai.content_engine import ProductionResult
from app.ai.image.base import ImagePrompt, ImageReference
from app.ai.image.prompt import build_still_prompt, parse_size, size_for_format
from app.ai.providers.flux_image_provider import FluxImageProvider
from app.ai.providers.mock_image_provider import MockImageProvider
from app.ai.providers.openai_image_provider import OpenAIImageProvider
from app.core.config import Settings
from app.core.exceptions import StorageError
from app.models.enums import AssetKind, ContentFormat
from app.services.still_service import StillService, load_reference, select_reference_asset
from app.services.storage_service import StorageService


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
    assert generated.used_reference is False
    assert generated.metadata()["used_reference"] is False


@pytest.mark.asyncio
async def test_mock_with_reference_still_returns_png() -> None:
    generated = await MockImageProvider().generate(
        ImagePrompt(
            prompt="Still comercial com foto de produto",
            size="1024x1792",
            seed=1,
            references=(
                ImageReference(data=b"foto", mime_type="image/png", filename="cafe.png"),
            ),
        )
    )
    assert generated.data[:8] == b"\x89PNG\r\n\x1a\n"
    assert generated.used_reference is True
    assert generated.metadata()["used_reference"] is True
    assert generated.metadata()["model"] == "mock-still"


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


def _production() -> ProductionResult:
    return ProductionResult(
        content_format=ContentFormat.REEL,
        fields={"title": "Cafe", "concept": "Aroma", "payload": {}},
        context_snapshot={},
    )


def test_still_prompt_uses_commercial_direction() -> None:
    request = build_still_prompt(
        context=_prompt_context(),  # type: ignore[arg-type]
        production=_production(),
        seed=1,
    )
    low = " ".join(request.prompt.split()).lower()
    assert "cafeteria aroma" in low
    assert "cafe" in low
    assert "over 25" in low
    assert "child" in request.negative_prompt.lower()
    assert "the product is the star" in low or "hero" in low
    assert "the scene represents the brand cafeteria aroma" in low
    assert "product fidelity" not in low
    assert request.references == ()
    assert low.index("cafeteria aroma") < low.index("hero:")


def test_still_prompt_puts_focused_product_before_brief() -> None:
    product = type(
        "Product",
        (),
        {
            "name": "Espresso Aroma",
            "description": "Single-origin espresso in a ceramic cup",
            "is_focus": True,
        },
    )()
    context = type(
        "Ctx",
        (),
        {
            "name": "Cafeteria Aroma",
            "segment": "cafeteria",
            "location": "Sao Paulo",
            "products": (product,),
            "services": (),
        },
    )()
    request = build_still_prompt(
        context=context,  # type: ignore[arg-type]
        production=ProductionResult(
            content_format=ContentFormat.REEL,
            fields={"title": "Cafe da manha", "concept": "Xicara na mao", "payload": {}},
            context_snapshot={},
        ),
        seed=1,
    )
    low = " ".join(request.prompt.split()).lower()
    assert low.index("espresso aroma") < low.index("hero:")
    assert "ceramic cup" in low
    assert "do not default to a gym" in low


def test_still_prompt_with_reference_puts_fidelity_before_brief() -> None:
    request = build_still_prompt(
        context=_prompt_context(),  # type: ignore[arg-type]
        production=_production(),
        seed=1,
        has_reference=True,
    )
    low = " ".join(request.prompt.split()).lower()
    assert "product fidelity" in low
    assert "restage" in low
    assert "do not replace it with an invented product" in low
    assert low.index("product fidelity") < low.index("hero:")
    assert low.index("product fidelity") < low.index("cafeteria aroma")


def _fake_asset(**kwargs: object) -> SimpleNamespace:
    defaults: dict[str, object] = {
        "id": uuid.uuid4(),
        "kind": AssetKind.OTHER,
        "mime_type": "image/jpeg",
        "original_filename": "arquivo.jpg",
        "storage_key": "key",
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_select_reference_prefers_product_photo() -> None:
    place = _fake_asset(kind=AssetKind.PLACE_PHOTO, mime_type="image/jpeg")
    photo = _fake_asset(kind=AssetKind.PRODUCT_PHOTO, mime_type="image/png")
    assert select_reference_asset([place, photo]) is photo


def test_select_reference_falls_back_to_newest_image() -> None:
    newest = _fake_asset(kind=AssetKind.OTHER, mime_type="image/jpeg")
    older = _fake_asset(kind=AssetKind.PLACE_PHOTO, mime_type="image/png")
    assert select_reference_asset([newest, older]) is newest


def test_select_reference_ignores_non_images() -> None:
    pdf = _fake_asset(kind=AssetKind.OTHER, mime_type="application/pdf")
    assert select_reference_asset([pdf]) is None


@pytest.mark.asyncio
async def test_storage_get_object_roundtrip() -> None:
    storage = StorageService()
    await storage.put_object("prod/cafe.png", b"bytes-da-foto", mime_type="image/png")
    assert await storage.get_object("prod/cafe.png") == b"bytes-da-foto"


@pytest.mark.asyncio
async def test_storage_get_object_missing_raises() -> None:
    storage = StorageService()
    with pytest.raises(StorageError):
        await storage.get_object("nao-existe")


@pytest.mark.asyncio
async def test_load_reference_attaches_storage_bytes() -> None:
    storage = StorageService()
    storage._memory["prod/1.png"] = b"hello-bytes"
    asset = _fake_asset(
        storage_key="prod/1.png",
        mime_type="image/png",
        original_filename="cafe.png",
    )
    reference = await load_reference(storage, asset)  # type: ignore[arg-type]
    assert reference is not None
    assert reference.data == b"hello-bytes"
    assert reference.filename == "cafe.png"
    assert reference.mime_type == "image/png"


@pytest.mark.asyncio
async def test_still_service_attaches_product_photo_bytes() -> None:
    storage = StorageService()
    storage._memory["k"] = b"foto-produto"
    photo = _fake_asset(
        kind=AssetKind.PRODUCT_PHOTO,
        mime_type="image/png",
        original_filename="espresso.png",
        storage_key="k",
    )
    service = StillService.__new__(StillService)
    service.assets = SimpleNamespace(
        list=AsyncMock(return_value=[photo]),
        storage=storage,
    )
    product_id = uuid.uuid4()
    reference, asset_id = await service._load_focused_reference(
        uuid.uuid4(), product_id, None
    )
    assert reference is not None
    assert reference.data == b"foto-produto"
    assert asset_id == photo.id
    service.assets.list.assert_awaited_once()


@pytest.mark.asyncio
async def test_still_service_empty_references_without_photo() -> None:
    service = StillService.__new__(StillService)
    service.assets = SimpleNamespace(
        list=AsyncMock(return_value=[]),
        storage=StorageService(),
    )
    reference, asset_id = await service._load_focused_reference(
        uuid.uuid4(), uuid.uuid4(), None
    )
    assert reference is None
    assert asset_id is None


@pytest.mark.asyncio
async def test_still_service_skips_reference_without_focused_item() -> None:
    service = StillService.__new__(StillService)
    service.assets = SimpleNamespace(list=AsyncMock())
    reference, asset_id = await service._load_focused_reference(uuid.uuid4(), None, None)
    assert reference is None
    assert asset_id is None
    service.assets.list.assert_not_called()


def _png_b64() -> str:
    return base64.b64encode(b"\x89PNG\r\n\x1a\nxxxx").decode()


class _ImageItem:
    def __init__(self) -> None:
        self.b64_json = _png_b64()
        self.url = None


class _ImageResponse:
    def __init__(self) -> None:
        self.data = [_ImageItem()]


def _openai_provider() -> tuple[OpenAIImageProvider, AsyncMock, AsyncMock]:
    provider = OpenAIImageProvider(settings=Settings(OPENAI_API_KEY="sk-test"))
    generate = AsyncMock(return_value=_ImageResponse())
    edit = AsyncMock(return_value=_ImageResponse())
    provider.client.images.generate = generate
    provider.client.images.edit = edit
    return provider, generate, edit


@pytest.mark.asyncio
async def test_openai_generate_without_reference() -> None:
    provider, generate, edit = _openai_provider()
    generated = await provider.generate(ImagePrompt(prompt="still", size="1024x1792"))
    generate.assert_awaited_once()
    edit.assert_not_called()
    assert generate.await_args.kwargs["size"] == "1024x1792"
    assert generated.used_reference is False
    assert generated.width == 1024
    assert generated.height == 1792


@pytest.mark.asyncio
async def test_openai_edit_with_reference() -> None:
    provider, generate, edit = _openai_provider()
    reference = ImageReference(data=b"foto", mime_type="image/png", filename="p.png")
    generated = await provider.generate(
        ImagePrompt(prompt="still", size="1024x1792", references=(reference,))
    )
    generate.assert_not_called()
    edit.assert_awaited_once()
    kwargs = edit.await_args.kwargs
    assert kwargs["size"] == "1024x1536"
    assert kwargs["quality"] == "medium"
    assert kwargs["output_format"] == "png"
    assert kwargs["image"][0] == "p.png"
    assert generated.used_reference is True
    assert generated.width == 1024
    assert generated.height == 1536
    assert generated.metadata()["used_reference"] is True


def _flux_provider() -> FluxImageProvider:
    return FluxImageProvider(
        settings=Settings(
            FAL_KEY="fal-test",
            FAL_IMAGE_MODEL="fal-ai/flux/dev",
            FAL_KONTEXT_MODEL="fal-ai/flux-pro/kontext",
        )
    )


def test_flux_payload_uses_image_model_without_reference() -> None:
    provider = _flux_provider()
    model, payload = provider._build_payload(ImagePrompt(prompt="hello", size="1024x1024"))
    assert model == "fal-ai/flux/dev"
    assert payload["image_size"] == {"width": 1024, "height": 1024}
    assert "aspect_ratio" not in payload
    assert "image_url" not in payload


def test_flux_payload_uses_kontext_with_reference() -> None:
    provider = _flux_provider()
    reference = ImageReference(data=b"foto", mime_type="image/png", filename="p.png")
    model, payload = provider._build_payload(
        ImagePrompt(prompt="hello", size="1024x1792", seed=7, references=(reference,))
    )
    assert model == "fal-ai/flux-pro/kontext"
    assert payload["prompt"] == "hello"
    assert payload["aspect_ratio"] == "9:16"
    assert payload["output_format"] == "png"
    assert payload["num_images"] == 1
    assert payload["guidance_scale"] == 3.5
    assert payload["seed"] == 7
    assert payload["image_url"].startswith("data:image/png;base64,")
    assert base64.b64decode(payload["image_url"].split(",", 1)[1]) == b"foto"
    assert "image_size" not in payload
