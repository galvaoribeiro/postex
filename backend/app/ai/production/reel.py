"""Formato Reel: gancho, roteiro em cenas, texto na tela, CTA e legenda."""

from __future__ import annotations

from app.ai.production.base import FormatStrategy, register_strategy
from app.ai.schemas import ReelPayload, ReelProduction
from app.models.enums import ContentFormat


@register_strategy
class ReelStrategy(FormatStrategy):
    content_format = ContentFormat.REEL
    label = "Reel"
    production_model = ReelProduction
    payload_model = ReelPayload
    body_label = "roteiro"

    def production_guidelines(self) -> str:
        return """\
Estruture o Reel assim:

- `payload.hook`: a primeira frase, falada ou escrita, nos 3 segundos iniciais. \
Ela precisa criar tensao, contrariar uma crenca comum ou prometer um resultado \
concreto. Nada de "voce sabia que...".
- `payload.scenes`: de 3 a 6 cenas em ordem. Em cada cena:
  - `visual`: o que a camera mostra, com enquadramento e acao. Precisa ser \
gravavel com um celular no local do negocio.
  - `on_screen_text`: texto curto sobreposto, no maximo 8 palavras.
  - `voiceover`: a fala exata, escrita como se fosse dita em voz alta.
  - `duration_seconds`: duracao realista da cena.
- `payload.total_duration_seconds`: entre 15 e 60 segundos, coerente com a soma \
das cenas.
- `payload.music_suggestion`: tipo de trilha e ritmo desejados (nao invente \
nomes de musicas licenciadas especificas).
- `payload.editing_notes`: cortes, velocidade, legendas e transicoes.

A ultima cena deve conduzir naturalmente ao CTA."""
