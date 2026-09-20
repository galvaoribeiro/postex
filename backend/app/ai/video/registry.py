"""Selecao do provedor de video em tempo de execucao."""

from __future__ import annotations

from app.ai.video.base import VideoProvider
from app.core.config import VideoProviderName, settings
from app.core.exceptions import AIProviderError
from app.core.logging import get_logger

logger = get_logger(__name__)

_CACHE: dict[str, VideoProvider] = {}


def _build(name: VideoProviderName) -> VideoProvider:
    if name is VideoProviderName.MOCK:
        from app.ai.providers.mock_video_provider import MockVideoProvider

        return MockVideoProvider()
    if name is VideoProviderName.FAL:
        from app.ai.providers.fal_video_provider import FalVideoProvider

        return FalVideoProvider()
    raise AIProviderError(f"Provedor de video desconhecido: {name}.")


def get_video_provider(name: VideoProviderName | None = None) -> VideoProvider:
    resolved = name or settings.video_provider_name
    cached = _CACHE.get(resolved.value)
    if cached is not None:
        return cached
    provider = _build(resolved)
    _CACHE[resolved.value] = provider
    logger.info(
        "video_provider_selected", provider=provider.name, model=provider.default_model
    )
    return provider


def reset_video_provider_cache() -> None:
    _CACHE.clear()
