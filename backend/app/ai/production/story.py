"""Formato story: sequencia de frames, textos e interacao."""

from __future__ import annotations

from app.ai.production.base import FormatStrategy, register_strategy
from app.ai.schemas import StoryPayload, StoryProduction
from app.models.enums import ContentFormat


@register_strategy
class StoryStrategy(FormatStrategy):
    content_format = ContentFormat.STORY
    label = "Sequencia de stories"
    production_model = StoryProduction
    payload_model = StoryPayload
    body_label = "sequencia"

    def production_guidelines(self) -> str:
        return """\
Estruture a sequencia assim:

- `payload.frames`: de 3 a 6 frames em ordem. Em cada frame:
  - `visual`: o que aparece na tela, gravavel na hora com o celular.
  - `text`: o texto sobreposto, em linguagem falada e direta. Uma frase.
  - `interaction`: o recurso interativo usado - `enquete`, `caixinha de \
perguntas`, `quiz`, `link`, `sticker de contagem` ou `nenhum`. No maximo dois \
frames devem pedir interacao.
- `payload.visual_direction`: como manter coerencia visual entre os frames.

O primeiro frame precisa funcionar como interrupcao. O ultimo conduz ao CTA, \
preferencialmente com um recurso interativo ou link."""
