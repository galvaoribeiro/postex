"""Contrato unico de acesso a modelos de IA.

Nenhum modulo fora de `app/ai/providers/` fala com um SDK de modelo. Toda a
aplicacao depende apenas de `AIProvider`, o que permite trocar de provedor,
usar provedores diferentes por etapa do pipeline, ou rodar tudo em modo mock
sem tocar em regra de negocio.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar, Generic, TypeVar

from pydantic import BaseModel

from app.ai.types import Prompt

OutputT = TypeVar("OutputT", bound=BaseModel)


@dataclass(frozen=True, slots=True)
class AICompletion(Generic[OutputT]):
    """Resposta validada, acompanhada dos metadados da chamada."""

    value: OutputT
    provider: str
    model: str
    latency_ms: int
    input_tokens: int | None = None
    output_tokens: int | None = None

    def metadata(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "model": self.model,
            "latency_ms": self.latency_ms,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
        }


class AIProvider(ABC):
    """Provedor de geracao estruturada."""

    name: ClassVar[str] = "abstract"

    @abstractmethod
    async def generate_structured(
        self,
        *,
        prompt: Prompt,
        output_model: type[OutputT],
    ) -> AICompletion[OutputT]:
        """Executa o prompt e devolve uma instancia validada de `output_model`.

        Implementacoes devem levantar `AIProviderError` (falha de transporte,
        quota, timeout) ou `AIResponseError` (resposta que nao satisfaz o
        schema) - nunca vazar excecoes do SDK subjacente.
        """

    @property
    def supports_vision(self) -> bool:
        """Se o provedor consegue considerar as imagens de `Prompt.images`."""
        return False

    @property
    def default_model(self) -> str:
        return "unknown"
