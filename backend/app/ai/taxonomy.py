"""Carga e consulta da taxonomia editorial definida em YAML."""

from __future__ import annotations

import random
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

from app.core.exceptions import ValidationError
from app.models.enums import ContentFormat

TAXONOMY_PATH = Path(__file__).parent / "config" / "content_taxonomy.yaml"


@dataclass(frozen=True, slots=True)
class ContentCategory:
    key: str
    label: str
    description: str
    objective: str
    recommended_formats: tuple[ContentFormat, ...]
    prompt_hint: str
    weight: int

    @property
    def default_format(self) -> ContentFormat:
        return self.recommended_formats[0] if self.recommended_formats else ContentFormat.REEL


@dataclass(frozen=True, slots=True)
class ContentTaxonomy:
    version: int
    categories: tuple[ContentCategory, ...]

    @property
    def keys(self) -> tuple[str, ...]:
        return tuple(category.key for category in self.categories)

    def get(self, key: str) -> ContentCategory:
        for category in self.categories:
            if category.key == key:
                return category
        raise ValidationError(
            f"Categoria de conteudo desconhecida: '{key}'.",
            details={"available": list(self.keys)},
        )

    def find(self, key: str) -> ContentCategory | None:
        for category in self.categories:
            if category.key == key:
                return category
        return None

    def resolve(self, keys: list[str] | None) -> tuple[ContentCategory, ...]:
        """Valida e materializa uma lista de chaves; vazio significa 'todas'."""
        if not keys:
            return self.categories
        return tuple(self.get(key) for key in dict.fromkeys(keys))

    def plan_distribution(
        self,
        count: int,
        *,
        allowed: list[str] | None = None,
        avoided: list[str] | None = None,
        seed: int | None = None,
    ) -> list[ContentCategory]:
        """Distribui `count` ideias entre os pilares respeitando os pesos.

        Evita que uma rodada de ideacao venha inteira do mesmo pilar, que e o
        principal sintoma de conteudo generico.
        """
        pool = list(self.resolve(allowed))
        if avoided:
            avoided_set = set(avoided)
            filtered = [category for category in pool if category.key not in avoided_set]
            pool = filtered or pool

        if not pool:
            pool = list(self.categories)

        rng = random.Random(seed)
        weighted = [category for category in pool for _ in range(max(1, category.weight))]

        chosen: list[ContentCategory] = []
        # Primeiro passo: variedade garantida enquanto houver pilares disponiveis.
        rotation = pool[:]
        rng.shuffle(rotation)
        for category in rotation:
            if len(chosen) >= count:
                break
            chosen.append(category)

        # Restante: sorteio ponderado.
        while len(chosen) < count:
            chosen.append(rng.choice(weighted))

        return chosen[:count]


def _load(path: Path = TAXONOMY_PATH) -> ContentTaxonomy:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))

    categories: list[ContentCategory] = []
    for item in raw.get("categories", []):
        formats = tuple(
            ContentFormat(value) for value in item.get("recommended_formats", []) or []
        )
        categories.append(
            ContentCategory(
                key=item["key"],
                label=item["label"],
                description=" ".join(item.get("description", "").split()),
                objective=" ".join(item.get("objective", "").split()),
                recommended_formats=formats,
                prompt_hint=" ".join(item.get("prompt_hint", "").split()),
                weight=int(item.get("weight", 1)),
            )
        )

    if not categories:
        raise RuntimeError(f"Taxonomia vazia em {path}")

    return ContentTaxonomy(version=int(raw.get("version", 1)), categories=tuple(categories))


@lru_cache
def get_taxonomy() -> ContentTaxonomy:
    return _load()
