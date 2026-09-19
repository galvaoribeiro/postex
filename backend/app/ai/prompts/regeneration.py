"""Prompts de regeneracao total ou parcial de um conteudo.

A regeneracao preserva o contexto original: o prompt sempre carrega o contexto
do negocio e o conteudo atual completo, e pede a reescrita apenas do escopo
solicitado. E isso que permite pedidos como "mantenha a ideia, mas deixe o
roteiro mais curto" sem perder o resto do trabalho.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.ai.context_builder import BusinessContext
from app.ai.inputs import ContentSnapshot
from app.ai.prompts.system import base_system_prompt
from app.ai.schemas import (
    AIModel,
    CaptionPatch,
    ConceptPatch,
    CtaPatch,
    HashtagsPatch,
    HookPatch,
    TitlePatch,
)
from app.ai.types import Prompt
from app.core.exceptions import ValidationError
from app.models.enums import RegenerationScope

if TYPE_CHECKING:
    # Importacao adiada: `production.base` monta seus prompts a partir deste
    # modulo, e um import direto fecharia o ciclo.
    from app.ai.production.base import FormatStrategy

REGENERATION_SYSTEM_EXTRA = """\
NESTA ETAPA voce esta revisando um conteudo que ja existe. Duas regras valem \
acima de tudo:

1. Reescreva SOMENTE o escopo solicitado. O resto do conteudo permanece como \
esta e nao deve ser devolvido.
2. Mantenha a ideia, o pilar editorial e o publico da versao atual, a menos que \
a instrucao do usuario peca explicitamente o contrario."""

#: O que cada escopo pede de volta, em linguagem de instrucao.
_SCOPE_INSTRUCTIONS: dict[RegenerationScope, str] = {
    RegenerationScope.TITLE: "Reescreva apenas o titulo interno do conteudo.",
    RegenerationScope.CONCEPT: (
        "Reescreva apenas o conceito e o objetivo, mantendo o mesmo assunto."
    ),
    RegenerationScope.HOOK: (
        "Reescreva apenas o gancho de abertura. Ele precisa continuar coerente "
        "com o restante do roteiro, que nao muda."
    ),
    RegenerationScope.CAPTION: (
        "Reescreva apenas a legenda. Mantenha o CTA atual funcionando no final."
    ),
    RegenerationScope.HASHTAGS: (
        "Refaca apenas a lista de hashtags, de 8 a 15 itens, sem o caractere '#'. "
        "Combine hashtags de nicho, de intencao de compra e de busca local."
    ),
    RegenerationScope.CTA: "Reescreva apenas a chamada para acao.",
}

_PATCH_MODELS: dict[RegenerationScope, type[AIModel]] = {
    RegenerationScope.TITLE: TitlePatch,
    RegenerationScope.CONCEPT: ConceptPatch,
    RegenerationScope.HOOK: HookPatch,
    RegenerationScope.CAPTION: CaptionPatch,
    RegenerationScope.HASHTAGS: HashtagsPatch,
    RegenerationScope.CTA: CtaPatch,
}


def output_model_for_scope(
    scope: RegenerationScope, strategy: "FormatStrategy"
) -> type[AIModel]:
    """Schema que a IA deve devolver para o escopo pedido."""
    if scope is RegenerationScope.FULL:
        return strategy.production_model
    if scope is RegenerationScope.BODY:
        return strategy.payload_model
    model = _PATCH_MODELS.get(scope)
    if model is None:  # pragma: no cover - protegido pelo enum
        raise ValidationError(f"Escopo de regeneracao nao suportado: {scope.value}.")
    return model


def build_regeneration_prompt(
    context: BusinessContext,
    strategy: "FormatStrategy",
    snapshot: ContentSnapshot,
    *,
    scope: RegenerationScope,
    instruction: str | None = None,
    seed: int = 0,
) -> Prompt:
    if scope is RegenerationScope.FULL:
        task = (
            f"Refaca o conteudo completo no formato {strategy.label}, mantendo a "
            f"ideia original.\n\n{strategy.production_guidelines()}\n\n"
            "Devolva todos os campos, incluindo titulo, conceito, objetivo, "
            "legenda, CTA e hashtags."
        )
    elif scope is RegenerationScope.BODY:
        task = (
            f"Refaca apenas o {strategy.body_label} deste {strategy.label}. "
            "Devolva somente a estrutura do formato, sem titulo, legenda, CTA "
            f"nem hashtags.\n\n{strategy.production_guidelines()}"
        )
    else:
        task = _SCOPE_INSTRUCTIONS[scope]

    instruction_block = (
        f"\n## INSTRUCAO DO USUARIO\n{instruction.strip()}"
        if instruction
        else "\n## INSTRUCAO DO USUARIO\n(nenhuma instrucao especifica: melhore a clareza"
        " e a especificidade mantendo o sentido)"
    )

    user = f"""\
{context.to_prompt_block()}

## CONTEUDO ATUAL
{snapshot.render()}

## TAREFA
{task}
{instruction_block}
"""

    return Prompt(
        name=f"regeneration.{scope.value.lower()}",
        system=base_system_prompt(REGENERATION_SYSTEM_EXTRA),
        user=user,
        hints=context.to_hints(
            idea_title=snapshot.title,
            idea_concept=snapshot.concept,
            idea_category=snapshot.category,
            content_format=snapshot.content_format.value,
            instruction=instruction,
            seed=seed,
        ),
    )
