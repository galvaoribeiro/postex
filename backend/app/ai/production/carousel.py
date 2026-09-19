"""Formato carrossel: capa, estrutura dos slides, legenda e CTA."""

from __future__ import annotations

from app.ai.production.base import FormatStrategy, register_strategy
from app.ai.schemas import CarouselPayload, CarouselProduction
from app.models.enums import ContentFormat


@register_strategy
class CarouselStrategy(FormatStrategy):
    content_format = ContentFormat.CAROUSEL
    label = "Carrossel"
    production_model = CarouselProduction
    payload_model = CarouselPayload
    body_label = "slides"

    def production_guidelines(self) -> str:
        return """\
Estruture o carrossel assim:

- `payload.cover_title`: o titulo do primeiro slide. E o unico texto que a \
maioria vai ler, portanto precisa entregar a promessa completa.
- `payload.slides`: de 5 a 9 slides em ordem, incluindo a capa como slide 1 e \
o slide de CTA como ultimo. Em cada slide:
  - `title`: titulo do slide, curto.
  - `body`: o conteudo do slide. Uma ideia por slide, no maximo 3 linhas.
  - `on_image_text`: o texto exato que sera aplicado na arte.
- `payload.visual_direction`: padrao visual do conjunto - paleta, tipografia, \
uso de fotos ou fundo solido, e o elemento que repete em todos os slides.

Cada slide deve criar motivo para deslizar para o proximo. Nao encerre o \
assunto no slide 2."""
