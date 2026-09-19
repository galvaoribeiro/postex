"""Implementacoes concretas de `AIProvider`.

Este e o unico pacote autorizado a importar SDKs de modelos de IA.
"""

from app.ai.providers.mock_provider import MockProvider

__all__ = ["MockProvider"]
