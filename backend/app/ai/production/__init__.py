"""Registro das estrategias de producao.

Os modulos sao importados aqui apenas pelo efeito colateral de registro; sem
essa importacao o registry fica vazio.
"""

from app.ai.production import carousel, image_post, reel, story  # noqa: F401
from app.ai.production.base import (
    FormatStrategy,
    all_strategies,
    get_strategy,
    register_strategy,
)

__all__ = [
    "FormatStrategy",
    "all_strategies",
    "get_strategy",
    "register_strategy",
]
