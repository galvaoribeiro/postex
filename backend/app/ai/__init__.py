"""Camada de IA do Motor de Conteudo.

Fronteira clara: o resto da aplicacao importa deste pacote (`ContentEngine`,
`ContextBuilder`, `get_ai_provider`) e nunca um SDK de modelo.
"""

from app.ai.content_engine import (
    AssetAnalysisResult,
    ContentEngine,
    IdeationResult,
    ProductionResult,
    RegenerationResult,
)
from app.ai.context_builder import BusinessContext, ContextBuilder
from app.ai.inputs import ContentSnapshot, IdeaInput
from app.ai.production import all_strategies, get_strategy
from app.ai.registry import get_ai_provider
from app.ai.taxonomy import get_taxonomy

__all__ = [
    "AssetAnalysisResult",
    "BusinessContext",
    "ContentEngine",
    "ContentSnapshot",
    "ContextBuilder",
    "IdeaInput",
    "IdeationResult",
    "ProductionResult",
    "RegenerationResult",
    "all_strategies",
    "get_ai_provider",
    "get_strategy",
    "get_taxonomy",
]
