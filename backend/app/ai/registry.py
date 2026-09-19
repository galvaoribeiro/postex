"""Selecao do provedor de IA em tempo de execucao.

O provedor e resolvido por configuracao (`AI_PROVIDER`) e cacheado por nome. A
assinatura aceita um nome explicito para que seja possivel, no futuro, usar
provedores distintos por etapa do pipeline (ideacao em um modelo barato,
producao em um modelo melhor) sem mudar nada nos services.
"""

from __future__ import annotations

from app.ai.base import AIProvider
from app.ai.providers.mock_provider import MockProvider
from app.core.config import AIProviderName, settings
from app.core.exceptions import AIProviderError
from app.core.logging import get_logger

logger = get_logger(__name__)

_PROVIDER_CACHE: dict[str, AIProvider] = {}


def _build(name: AIProviderName) -> AIProvider:
    if name is AIProviderName.MOCK:
        return MockProvider()

    if name is AIProviderName.OPENAI:
        # Importacao tardia: o SDK so e carregado se o provedor for usado.
        from app.ai.providers.openai_provider import OpenAIProvider

        return OpenAIProvider()

    raise AIProviderError(f"Provedor de IA desconhecido: {name}.")


def get_ai_provider(name: AIProviderName | None = None) -> AIProvider:
    resolved = name or settings.AI_PROVIDER
    cached = _PROVIDER_CACHE.get(resolved.value)
    if cached is not None:
        return cached

    provider = _build(resolved)
    _PROVIDER_CACHE[resolved.value] = provider
    logger.info("ai_provider_selected", provider=provider.name, model=provider.default_model)
    return provider


def reset_provider_cache() -> None:
    """Usado em testes que alternam de provedor."""
    _PROVIDER_CACHE.clear()
