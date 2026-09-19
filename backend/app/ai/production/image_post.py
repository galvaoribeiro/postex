"""Formato post de imagem unica: conceito, texto, legenda e CTA."""

from __future__ import annotations

from app.ai.production.base import FormatStrategy, register_strategy
from app.ai.schemas import ImagePostPayload, ImagePostProduction
from app.models.enums import ContentFormat


@register_strategy
class ImagePostStrategy(FormatStrategy):
    content_format = ContentFormat.IMAGE_POST
    label = "Post de imagem"
    production_model = ImagePostProduction
    payload_model = ImagePostPayload
    body_label = "texto"

    def production_guidelines(self) -> str:
        return """\
Estruture o post assim:

- `payload.headline`: a ideia central em uma frase, capaz de funcionar sozinha \
mesmo que a pessoa nao leia a legenda.
- `payload.on_image_text`: o texto que sera aplicado sobre a imagem. No maximo \
duas linhas curtas, porque precisa ser legivel em tela pequena.
- `payload.body_text`: o desenvolvimento da mensagem, que aparece na imagem ou \
como complemento visual.
- `payload.visual_direction`: direcao de arte pratica - enquadramento, luz, \
cenario, objetos em cena e o que evitar. Precisa ser executavel com celular.

A legenda nao deve repetir literalmente o texto da imagem: ela aprofunda o \
assunto e conduz ao CTA."""
