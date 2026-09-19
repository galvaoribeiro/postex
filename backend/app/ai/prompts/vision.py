"""Prompt de analise de imagem.

A analise existe para enriquecer o contexto do negocio, nao para disparar
conteudo: o resultado e gravado em `Asset.ai_analysis` e passa a compor o
contexto das proximas ideacoes se o usuario quiser usa-lo.
"""

from __future__ import annotations

from app.ai.context_builder import BusinessContext
from app.ai.prompts.system import OUTPUT_CONTRACT
from app.ai.types import ImageRef, Prompt

VISION_SYSTEM = f"""\
Voce analisa imagens de pequenos negocios para alimentar o planejamento de \
conteudo do Instagram.

Descreva apenas o que realmente esta visivel na imagem. Nao suponha marcas, \
precos, materiais ou informacoes que nao possam ser observados. Se a imagem \
estiver ruim ou ambigua, diga isso em `quality_notes` em vez de preencher os \
outros campos com suposicoes.

{OUTPUT_CONTRACT}"""


def build_asset_analysis_prompt(
    context: BusinessContext,
    image: ImageRef,
    *,
    asset_kind: str,
    linked_to: str | None = None,
) -> Prompt:
    link_block = f"\nEsta imagem esta vinculada a: {linked_to}" if linked_to else ""

    user = f"""\
## NEGOCIO
Nome: {context.name}
Segmento: {context.segment}
Publico-alvo: {context.target_audience or "nao informado"}

## IMAGEM
Tipo declarado pelo usuario: {asset_kind}{link_block}

## TAREFA
Analise a imagem e preencha:
- `summary`: o que a imagem mostra, objetivamente
- `detected_elements`: elementos relevantes visiveis
- `dominant_colors`: cores predominantes, com nomes em portugues
- `mood`: o clima transmitido
- `suggested_alt_text`: texto alternativo acessivel, em uma frase
- `content_opportunities`: conteudos que ESTA imagem especifica viabiliza para \
este negocio
- `quality_notes`: limitacoes tecnicas relevantes (iluminacao, foco, \
enquadramento, ruido de fundo)
"""

    return Prompt(
        name="vision.asset_analysis",
        system=VISION_SYSTEM,
        user=user,
        images=(image,),
        hints=context.to_hints(image_labels=(image.label or asset_kind,)),
    )
