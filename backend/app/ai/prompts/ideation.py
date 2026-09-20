"""Etapa 2 do pipeline: prompt de ideacao."""

from __future__ import annotations

from app.ai.context_builder import BusinessContext
from app.ai.prompts.system import base_system_prompt
from app.ai.taxonomy import ContentCategory
from app.ai.types import Prompt
from app.models.enums import ContentFormat

IDEATION_SYSTEM_EXTRA = """\
NESTA ETAPA voce NAO escreve o conteudo final. Voce identifica oportunidades de \
comunicacao e descreve cada uma como uma ideia executavel: o que mostrar, por \
que funciona para este negocio e que resultado deve gerar.

Cada ideia precisa ser suficientemente concreta para que outra pessoa consiga \
produzi-la sem perguntar nada."""


def _format_catalog_reminder(context: BusinessContext) -> str:
    if context.has_catalog:
        return ""
    return (
        "\nATENCAO: este negocio ainda nao cadastrou produtos nem servicos. "
        "Baseie as ideias no segmento, no publico-alvo, nos diferenciais e na "
        "localizacao, e prefira pilares que nao dependam de um item especifico "
        "do catalogo."
    )


def build_ideation_prompt(
    context: BusinessContext,
    *,
    categories: list[ContentCategory],
    format_hint: ContentFormat | None = None,
    extra_instruction: str | None = None,
    seed: int = 0,
) -> Prompt:
    """Monta o prompt de ideacao com um pilar editorial atribuido por ideia.

    Atribuir o pilar antecipadamente (em vez de pedir "gere N ideias variadas")
    e o que garante diversidade real: sem isso o modelo tende a devolver
    variacoes do mesmo angulo.
    """
    briefing_lines = []
    for index, category in enumerate(categories, start=1):
        briefing_lines.append(
            f"{index}. Pilar `{category.key}` ({category.label})\n"
            f"   - proposito do pilar: {category.objective}\n"
            f"   - como executar: {category.prompt_hint}\n"
            f"   - formatos recomendados: "
            f"{', '.join(f.value for f in category.recommended_formats) or 'qualquer'}"
        )

    format_block = ""
    if format_hint is not None:
        format_block = (
            f"\nRESTRICAO DE FORMATO: todas as ideias devem ser pensadas para "
            f"{format_hint.value}, independentemente dos formatos recomendados "
            f"de cada pilar."
        )

    instruction_block = ""
    if extra_instruction:
        instruction_block = f"\nPEDIDO ADICIONAL DO USUARIO: {extra_instruction.strip()}"

    user = f"""\
{context.to_prompt_block()}

## TAREFA

Gere exatamente {len(categories)} ideias de conteudo comercial, uma para \
cada pilar abaixo, na mesma ordem:

{chr(10).join(briefing_lines)}
{format_block}{instruction_block}{_format_catalog_reminder(context)}

Para cada ideia preencha:
- `title`: titulo interno curto, especifico o suficiente para ser reconhecido \
em uma lista
- `concept`: o que o conteudo mostra, em 2 a 4 frases
- `objective`: o resultado pretendido para o negocio
- `category`: a chave exata do pilar atribuido
- `suggested_format`: um de REEL, IMAGE_POST, CAROUSEL, STORY
- `rationale`: por que esta ideia funciona para ESTE negocio, citando dados do \
contexto
- `hook_suggestion`: a primeira frase do conteudo
- `audience_note`: que recorte do publico-alvo esta ideia atinge
- `relevance_score`: de 1 a 10, o quanto ela deve ser priorizada agora
- `referenced_products` e `referenced_services`: nomes exatos citados, ou listas \
vazias
"""

    return Prompt(
        name="ideation",
        system=base_system_prompt(IDEATION_SYSTEM_EXTRA),
        user=user,
        hints=context.to_hints(
            categories=tuple(category.key for category in categories),
            content_format=format_hint.value if format_hint else None,
            instruction=extra_instruction,
            seed=seed,
        ),
    )
