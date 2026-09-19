"""Tipos de transporte da camada de IA."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ImageRef:
    """Imagem oferecida ao modelo como contexto adicional.

    `url` precisa ser acessivel pelo provedor (em MinIO/S3 usamos URL assinada
    de curta duracao).
    """

    url: str
    mime_type: str
    label: str | None = None


@dataclass(frozen=True, slots=True)
class PromptHints:
    """Resumo estruturado do que foi para dentro do prompt.

    Serve a dois propositos concretos: observabilidade (logar o que a IA
    recebeu sem despejar o prompt inteiro) e permitir que o `MockProvider`
    produza respostas derivadas dos dados reais do negocio, em vez de texto
    de enchimento. Provedores reais nunca dependem deste campo para gerar.
    """

    business_name: str = ""
    segment: str = ""
    location: str | None = None
    target_audience: str | None = None
    brand_voice: str | None = None
    product_names: tuple[str, ...] = ()
    service_names: tuple[str, ...] = ()
    differentiators: tuple[str, ...] = ()
    objectives: tuple[str, ...] = ()
    categories: tuple[str, ...] = ()
    recent_titles: tuple[str, ...] = ()
    idea_title: str | None = None
    idea_concept: str | None = None
    idea_category: str | None = None
    content_format: str | None = None
    instruction: str | None = None
    image_labels: tuple[str, ...] = ()
    seed: int = 0


@dataclass(frozen=True, slots=True)
class Prompt:
    """Unidade de comunicacao com um provedor de IA.

    Nenhum texto de prompt e montado fora de `app/ai/prompts/`.
    """

    name: str
    system: str
    user: str
    images: tuple[ImageRef, ...] = ()
    temperature: float | None = None
    max_output_tokens: int | None = None
    hints: PromptHints = field(default_factory=PromptHints)

    @property
    def requires_vision(self) -> bool:
        return bool(self.images)
