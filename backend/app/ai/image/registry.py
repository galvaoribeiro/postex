"""Selecao do provedor de still em tempo de execucao."""

from __future__ import annotations

from app.ai.image.base import ImageProvider
from app.ai.providers.mock_image_provider import MockImageProvider
from app.core.config import AIProviderName, settings
from app.core.exceptions import AIProviderError
from app.core.logging import get_logger

logger = get_logger(__name__)

_CACHE: dict[str, ImageProvider] = {}


def _build(name: AIProviderName) -> ImageProvider:
    if name is AIProviderName.MOCK:
        return MockImageProvider()
    if name is AIProviderName.OPENAI:
        from app.ai.providers.openai_image_provider import OpenAIImageProvider

        return OpenAIImageProvider()
    raise AIProviderError(f"Provedor de imagem desconhecido: {name}.")


def get_image_provider(name: AIProviderName | None = None) -> ImageProvider:
    resolved = name or settings.image_provider_name
    cached = _CACHE.get(resolved.value)
    if cached is not None:
        return cached
    provider = _build(resolved)
    _CACHE[resolved.value] = provider
    logger.info(
        "image_provider_selected", provider=provider.name, model=provider.default_model
    )
    return provider


def reset_image_provider_cache() -> None:
    _CACHE.clear()
