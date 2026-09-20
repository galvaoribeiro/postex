"""Contrato de geracao de imagem.

Separado do `AIProvider` de texto: a aplicacao nunca importa o SDK do
fornecedor fora de `app/ai/providers/`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True, slots=True)
class ImageReference:
    """Bytes da foto de produto usada para condicionar o still."""

    data: bytes
    mime_type: str
    filename: str


@dataclass(frozen=True, slots=True)
class ImagePrompt:
    """Pedido de still comercial, ja com restricoes de seguranca."""

    prompt: str
    negative_prompt: str = ""
    size: str = "1024x1792"
    seed: int = 0
    references: tuple[ImageReference, ...] = ()


@dataclass(frozen=True, slots=True)
class GeneratedImage:
    data: bytes
    mime_type: str
    width: int
    height: int
    provider: str
    model: str
    prompt: str
    latency_ms: int
    used_reference: bool = False

    def metadata(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "model": self.model,
            "width": self.width,
            "height": self.height,
            "latency_ms": self.latency_ms,
            "mime_type": self.mime_type,
            "used_reference": self.used_reference,
        }


class ImageProvider(ABC):
    name: ClassVar[str] = "abstract"

    @abstractmethod
    async def generate(self, request: ImagePrompt) -> GeneratedImage:
        """Devolve bytes de uma imagem. Erros viram `AIProviderError`."""

    @property
    def default_model(self) -> str:
        return "unknown"
