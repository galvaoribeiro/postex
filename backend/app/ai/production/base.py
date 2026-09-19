"""Estrategias de producao por formato.

Cada formato de conteudo e uma `FormatStrategy`: define o schema de saida, as
diretrizes de producao e como o resultado da IA vira campos de `Content`.
Acrescentar um formato novo significa criar um modulo aqui, registra-lo e
adicionar o valor em `ContentFormat` - nenhuma outra camada muda.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

from pydantic import ValidationError as PydanticValidationError

from app.ai.context_builder import BusinessContext
from app.ai.inputs import IdeaInput
from app.ai.prompts.system import base_system_prompt
from app.ai.schemas import AIModel, ProducedContentBase
from app.ai.taxonomy import get_taxonomy
from app.ai.types import Prompt
from app.core.exceptions import ValidationError
from app.models.enums import ContentFormat

PRODUCTION_SYSTEM_EXTRA = """\
NESTA ETAPA voce escreve o conteudo final, pronto para produzir e publicar. \
Nao devolva sugestoes nem alternativas: devolva a versao definitiva.

A legenda deve funcionar sozinha, com a primeira linha capaz de interromper a \
rolagem. Hashtags devem ser especificas do nicho e da regiao, misturando alcance \
amplo e busca local - nunca uma lista generica de hashtags populares."""


class FormatStrategy(ABC):
    """Contrato de um formato de conteudo."""

    content_format: ClassVar[ContentFormat]
    label: ClassVar[str]
    production_model: ClassVar[type[ProducedContentBase]]
    payload_model: ClassVar[type[AIModel]]
    #: Nome legivel da parte "corpo" do formato, usado nas mensagens de
    #: regeneracao parcial ("regenerar apenas o roteiro", "apenas os slides").
    body_label: ClassVar[str]

    # ------------------------------------------------------------ diretrizes
    @abstractmethod
    def production_guidelines(self) -> str:
        """Instrucoes especificas do formato para a etapa de producao."""

    # --------------------------------------------------------------- prompts
    def build_production_prompt(
        self,
        context: BusinessContext,
        idea: IdeaInput,
        *,
        instruction: str | None = None,
        seed: int = 0,
    ) -> Prompt:
        category = get_taxonomy().find(idea.category)
        pillar_block = ""
        if category is not None:
            pillar_block = (
                f"\n## PILAR EDITORIAL\n{category.label}: {category.objective}\n"
                f"Como executar: {category.prompt_hint}"
            )

        instruction_block = ""
        if instruction:
            instruction_block = (
                f"\n## AJUSTE PEDIDO PELO USUARIO\n{instruction.strip()}\n"
                "Aplique este ajuste sem abandonar a ideia original."
            )

        user = f"""\
{context.to_prompt_block()}
{pillar_block}

## IDEIA APROVADA
{idea.render()}

## TAREFA
Produza o conteudo final no formato {self.label} ({self.content_format.value}).

{self.production_guidelines()}

Preencha tambem:
- `title`: titulo interno do conteudo
- `concept`: o conceito em uma ou duas frases
- `objective`: o resultado pretendido
- `caption`: legenda completa pronta para publicar, com quebras de linha reais
- `cta`: chamada para acao explicita e unica
- `hashtags`: de 8 a 15 hashtags sem o caractere '#'
{instruction_block}
"""

        return Prompt(
            name=f"production.{self.content_format.value.lower()}",
            system=base_system_prompt(PRODUCTION_SYSTEM_EXTRA),
            user=user,
            hints=context.to_hints(
                idea_title=idea.title,
                idea_concept=idea.concept,
                idea_category=idea.category,
                content_format=self.content_format.value,
                instruction=instruction,
                seed=seed,
            ),
        )

    # ----------------------------------------------------------- persistencia
    def to_content_fields(self, produced: ProducedContentBase) -> dict:
        """Converte a saida da IA nos campos de `Content`."""
        payload = getattr(produced, "payload")
        return {
            "title": produced.title,
            "concept": produced.concept,
            "objective": produced.objective,
            "caption": produced.caption,
            "cta": produced.cta,
            "hashtags": [tag.lstrip("#").strip() for tag in produced.hashtags if tag.strip()],
            "payload": payload.model_dump(mode="json"),
        }

    def validate_payload(self, payload: dict) -> dict:
        """Garante que um payload editado manualmente continua valido."""
        try:
            return self.payload_model.model_validate(payload).model_dump(mode="json")
        except PydanticValidationError as exc:
            # Traduzido para a excecao de dominio: e o unico tipo que os
            # handlers da API sabem converter em 422 com corpo estruturado.
            raise ValidationError(
                f"Estrutura invalida para o formato {self.label}.",
                details={
                    "format": self.content_format.value,
                    "errors": exc.errors(include_url=False),
                },
            ) from exc

    def describe(self) -> dict:
        return {
            "format": self.content_format.value,
            "label": self.label,
            "body_label": self.body_label,
            "payload_schema": self.payload_model.model_json_schema(),
        }


_STRATEGIES: dict[ContentFormat, FormatStrategy] = {}


def register_strategy(cls: type[FormatStrategy]) -> type[FormatStrategy]:
    _STRATEGIES[cls.content_format] = cls()
    return cls


def get_strategy(content_format: ContentFormat) -> FormatStrategy:
    strategy = _STRATEGIES.get(content_format)
    if strategy is None:
        raise ValidationError(
            f"Formato de conteudo sem estrategia de producao: {content_format.value}.",
            details={"available": [f.value for f in _STRATEGIES]},
        )
    return strategy


def all_strategies() -> tuple[FormatStrategy, ...]:
    return tuple(_STRATEGIES[fmt] for fmt in ContentFormat if fmt in _STRATEGIES)
