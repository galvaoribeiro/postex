"""Contrato de geracao de video.

Espelha `ImageProvider`: a aplicacao nunca importa o SDK do fornecedor
fora de `app/ai/providers/`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar

from app.ai.image.base import ImageReference


@dataclass(frozen=True, slots=True)
class VideoPrompt:
    prompt: str
    negative_prompt: str = ""
    aspect_ratio: str = "9:16"
    duration_seconds: int = 8
    seed: int = 0
    generate_audio: bool = True
    references: tuple[ImageReference, ...] = ()
    end_user_id: str | None = None


@dataclass(frozen=True, slots=True)
class GeneratedVideo:
    data: bytes
    mime_type: str
    width: int
    height: int
    duration_seconds: int
    provider: str
    model: str
    prompt: str
    latency_ms: int
    thumbnail_data: bytes | None = None
    thumbnail_mime_type: str = "image/png"
    used_reference: bool = False

    def metadata(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "model": self.model,
            "width": self.width,
            "height": self.height,
            "duration_seconds": self.duration_seconds,
            "latency_ms": self.latency_ms,
            "mime_type": self.mime_type,
            "used_reference": self.used_reference,
        }


class VideoProvider(ABC):
    name: ClassVar[str] = "abstract"

    @abstractmethod
    async def generate(self, request: VideoPrompt) -> GeneratedVideo:
        """Devolve bytes de um MP4. Erros viram `AIProviderError`."""

    @property
    def default_model(self) -> str:
        return "unknown"
