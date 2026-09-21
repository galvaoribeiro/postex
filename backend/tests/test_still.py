"""Still mock e montagem de prompt, sem HTTP."""

from __future__ import annotations

import base64
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.ai.content_engine import ProductionResult
from app.ai.image.base import ImagePrompt, ImageReference
from app.ai.image.prompt import build_still_prompt, build_talent_prompt, parse_size, size_for_format
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
    assert "creative brief" in low
    assert "mirror selfie" in low
    assert "video com rosto" not in low
    assert "the scene represents the brand cafeteria aroma" not in low
    assert "attached photo" not in low
    assert request.references == ()
    assert low.index("cafeteria aroma") < low.index("creative brief")
    assert request.size == "1024x1792"
    assert len(request.prompt) < 32_000


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
    assert low.index("espresso aroma") < low.index("creative brief")
    assert "ceramic cup" in low
    assert "do not substitute a gym" in low


def test_talent_prompt_is_character_only() -> None:
    request = build_talent_prompt(seed=3)
    low = " ".join(request.prompt.split()).lower()
    assert "criando a modelo" in low
    assert "creative brief" in low
    assert "image b" not in low
    assert "campaign for" not in low
    assert request.size == "1024x1792"
    assert request.references == ()


def test_still_prompt_with_approved_model_locks_identity() -> None:
    request = build_still_prompt(
        context=_prompt_context(),  # type: ignore[arg-type]
        production=_production(),
        seed=1,
        has_reference=True,
        has_model=True,
    )
    low = " ".join(request.prompt.split()).lower()
    assert "attached image a" in low
    assert "attached photo" in low
    assert "identity lock" in low
    assert low.index("attached image a") < low.index("attached photo")


def test_still_prompt_with_reference_puts_fidelity_before_brief() -> None:
    request = build_still_prompt(
        context=_prompt_context(),  # type: ignore[arg-type]
        production=_production(),
        seed=1,
        has_reference=True,
    )
    low = " ".join(request.prompt.split()).lower()
    assert "attached photo" in low
    assert "never output a product-only" in low
    assert "restage" in low
    assert "do not copy those people" in low
    assert low.index("attached photo") < low.index("creative brief")
    assert low.index("cafeteria aroma") < low.index("creative brief")


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
    assert "image_urls" not in payload


def test_flux_payload_sends_model_and_product_references() -> None:
    provider = _flux_provider()
    model_ref = ImageReference(data=b"modelo", mime_type="image/png", filename="a.png")
    product_ref = ImageReference(data=b"produto", mime_type="image/jpeg", filename="b.jpg")
    _model, payload = provider._build_payload(
        ImagePrompt(
            prompt="hello",
            size="1024x1792",
            references=(model_ref, product_ref),
        )
    )
    assert payload["image_url"].startswith("data:image/png;base64,")
    assert base64.b64decode(payload["image_url"].split(",", 1)[1]) == b"modelo"
    assert len(payload["image_urls"]) == 2
    assert base64.b64decode(payload["image_urls"][1].split(",", 1)[1]) == b"produto"


def test_video_prompt_uses_creative_brief_and_scaled_timeline() -> None:
    from app.ai.video.prompt import build_video_prompt
    from app.models.enums import CampaignDestination

    request = build_video_prompt(
        context=_prompt_context(),  # type: ignore[arg-type]
        production=_production(),
        seed=1,
        destination=CampaignDestination.TIKTOK,
        has_reference=True,
    )
    low = " ".join(request.prompt.split()).lower()
    assert request.duration_seconds == 5
    assert request.aspect_ratio == "9:16"
    assert "creative brief" in low
    assert "video com rosto" in low
    assert "criando a modelo" not in low
    assert "image-to-video" in low
    assert "starting frame" in low
    assert "5-second performance" in low
    assert "native audio" in low
    assert "brazilian portuguese" in low or "lowercase english" in low
    assert "she speaks" in low
    assert request.generate_audio is True
    assert low.index("cafeteria aroma") < low.index("creative brief")
    assert "child" in request.negative_prompt.lower()
    assert "lip-sync" not in request.negative_prompt.lower()
    assert "silent clip" in request.negative_prompt.lower()
    assert len(request.prompt) < 32_000


def test_compress_still_for_video_shrinks_png() -> None:
    from io import BytesIO

    from PIL import Image

    from app.ai.image.base import ImageReference
    from app.ai.providers.fal_video_provider import compress_still_for_video

    raw = BytesIO()
    pixels = [(i * 3 % 256, i * 7 % 256, i * 11 % 256) for i in range(1024 * 1792)]
    image = Image.new("RGB", (1024, 1792))
    image.putdata(pixels)
    image.save(raw, format="PNG")
    original = ImageReference(data=raw.getvalue(), mime_type="image/png", filename="capa.png")
    prepared = compress_still_for_video(original)
    assert prepared.mime_type == "image/jpeg"
    assert prepared.data[:2] == b"\xff\xd8"
    assert len(prepared.data) < 400_000


def test_kling_payload_snaps_duration_and_truncates_prompt() -> None:
    from app.ai.image.base import ImageReference
    from app.ai.providers.fal_video_provider import build_fal_video_payload
    from app.ai.video.base import VideoPrompt

    request = VideoPrompt(
        prompt="x" * 4000,
        negative_prompt="blur, child",
        aspect_ratio="9:16",
        duration_seconds=4,
        seed=99,
        references=(ImageReference(data=b"img", mime_type="image/png", filename="a.png"),),
    )
    payload = build_fal_video_payload(
        "fal-ai/kling-video/v2.1/standard/image-to-video",
        request,
        "https://example.com/still.png",
    )
    assert payload["duration"] == "5"
    assert len(payload["prompt"]) == 2500
    assert payload["image_url"] == "https://example.com/still.png"
    assert "seed" not in payload
    assert "aspect_ratio" not in payload
    assert "child" in payload["negative_prompt"]
    assert "start_image_url" not in payload


def test_kling_v3_can_disable_audio() -> None:
    from app.ai.providers.fal_video_provider import build_fal_video_payload
    from app.ai.video.base import VideoPrompt

    payload = build_fal_video_payload(
        "fal-ai/kling-video/v3/standard/image-to-video",
        VideoPrompt(prompt="move", duration_seconds=5, generate_audio=False),
        "https://example.com/still.png",
    )
    assert payload["generate_audio"] is False


def test_kling_v3_payload_uses_start_image_url() -> None:
    from app.ai.providers.fal_video_provider import build_fal_video_payload
    from app.ai.video.base import VideoPrompt

    payload = build_fal_video_payload(
        "fal-ai/kling-video/v3/standard/image-to-video",
        VideoPrompt(prompt="move", duration_seconds=5, negative_prompt="blur"),
        "https://example.com/still.png",
    )
    assert payload["start_image_url"] == "https://example.com/still.png"
    assert "image_url" not in payload
    assert payload["duration"] == "5"
    assert payload["generate_audio"] is True
    assert payload["negative_prompt"] == "blur"


def test_veo_payload_uses_seconds_suffix() -> None:
    from app.ai.providers.fal_video_provider import build_fal_video_payload
    from app.ai.video.base import VideoPrompt

    payload = build_fal_video_payload(
        "fal-ai/veo3.1/image-to-video",
        VideoPrompt(prompt="move", duration_seconds=5, seed=2),
        "https://example.com/still.png",
    )
    assert payload["image_url"] == "https://example.com/still.png"
    assert payload["duration"] == "4s"
    assert payload["aspect_ratio"] == "9:16"
    assert payload["resolution"] == "720p"
    assert payload["generate_audio"] is True
    assert payload["seed"] == 2


def test_seedance_payload_uses_official_i2v_schema() -> None:
    from app.ai.providers.fal_video_provider import build_fal_video_payload
    from app.ai.video.base import VideoPrompt

    payload = build_fal_video_payload(
        "bytedance/seedance-2.5/image-to-video",
        VideoPrompt(
            prompt="move",
            duration_seconds=12,
            aspect_ratio="9:16",
            seed=3,
            negative_prompt="speech",
            end_user_id="biz-1",
        ),
        "https://example.com/still.png",
    )
    assert payload["duration"] == "12"
    assert payload["aspect_ratio"] == "auto"
    assert payload["resolution"] == "720p"
    assert payload["generate_audio"] is True
    assert payload["seed"] == 3
    assert payload["end_user_id"] == "biz-1"
    assert "negative_prompt" not in payload


def test_normalize_seedance_bare_model_to_image_to_video() -> None:
    from app.ai.providers.fal_video_provider import normalize_fal_video_model

    assert (
        normalize_fal_video_model("bytedance/seedance-2.5")
        == "bytedance/seedance-2.5/image-to-video"
    )
    assert (
        normalize_fal_video_model("bytedance/seedance-2.5/image-to-video")
        == "bytedance/seedance-2.5/image-to-video"
    )
