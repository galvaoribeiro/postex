"""Catalogo interno de apresentadoras.

Nao ha CRUD nem tela: o motor escolhe uma personagem ficticia adulta de forma
automatica. O YAML e a unica fonte; para acrescentar alguem, edite o arquivo.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

from app.core.exceptions import ValidationError

CATALOG_PATH = Path(__file__).parent / "config" / "presenters.yaml"


@dataclass(frozen=True, slots=True)
class Presenter:
    id: str
    display_name: str
    age_range: str
    gender: str
    adult_confirmed: bool
    style: str
    personality: str
    clothing_style: str
    appearance: str
    visual_prompt: str
    negative_prompt: str
    accent: str

    def as_dict(self) -> dict[str, str]:
        return {
            "id": self.id,
            "display_name": self.display_name,
            "age_range": self.age_range,
            "style": self.style,
        }


def _clean(value: object) -> str:
    return " ".join(str(value or "").split()).strip()


@lru_cache
def load_presenters() -> tuple[Presenter, ...]:
    raw = yaml.safe_load(CATALOG_PATH.read_text(encoding="utf-8")) or {}
    items = raw.get("presenters") or []
    presenters: list[Presenter] = []
    for item in items:
        presenter = Presenter(
            id=str(item["id"]),
            display_name=str(item["display_name"]),
            age_range=str(item["age_range"]),
            gender=str(item.get("gender") or "feminine"),
            adult_confirmed=bool(item.get("adult_confirmed")),
            style=_clean(item.get("style")),
            personality=_clean(item.get("personality")),
            clothing_style=_clean(item.get("clothing_style")),
            appearance=_clean(item.get("appearance")),
            visual_prompt=_clean(item.get("visual_prompt")),
            negative_prompt=_clean(item.get("negative_prompt")),
            accent=str(item.get("accent") or "#7c3aed"),
        )
        if not presenter.adult_confirmed:
            raise ValidationError(
                f"Apresentadora '{presenter.id}' precisa ser explicitamente adulta.",
                details={"presenter_id": presenter.id},
            )
        presenters.append(presenter)
    if not presenters:
        raise ValidationError("Catalogo de apresentadoras vazio.")
    return tuple(presenters)


def get_presenter(presenter_id: str) -> Presenter:
    for presenter in load_presenters():
        if presenter.id == presenter_id:
            return presenter
    raise ValidationError(
        "Apresentadora nao encontrada.", details={"presenter_id": presenter_id}
    )


def pick_presenter(seed: int, *, segment: str | None = None) -> Presenter:
    """Escolha automatica, deterministica por seed.

    O segmento so enviesa o conjunto, nunca expoe um seletor ao usuario.
    """
    catalog = list(load_presenters())
    lowered = (segment or "").lower()
    if any(token in lowered for token in ("luxo", "luxury", "beleza", "beauty", "estetica")):
        preferred = [item for item in catalog if item.style in {"luxury", "fashion"}]
        if preferred:
            catalog = preferred
    elif any(token in lowered for token in ("moda", "fashion", "boutique", "roupa")):
        preferred = [item for item in catalog if item.style in {"fashion", "ugc"}]
        if preferred:
            catalog = preferred
    rng = random.Random(seed)
    return rng.choice(catalog)


def reset_presenter_cache() -> None:
    load_presenters.cache_clear()
