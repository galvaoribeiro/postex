"""Schemas das respostas estruturadas da IA.

Estes modelos sao o contrato entre a IA e a aplicacao: o provedor e obrigado a
devolver exatamente esta forma, e o que nao valida nao entra no banco. Eles
tambem geram o JSON Schema enviado ao modelo quando o provedor suporta saida
estruturada.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ContentFormat


class AIModel(BaseModel):
    """Base dos schemas de IA: rejeita campos extras inventados pelo modelo."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)


# ---------------------------------------------------------------- ideacao ----


class IdeaDraft(AIModel):
    title: str = Field(description="Titulo curto e especifico da ideia.")
    concept: str = Field(description="O que o conteudo mostra e por que funciona.")
    objective: str = Field(description="O resultado esperado com este conteudo.")
    category: str = Field(description="Chave do pilar editorial da taxonomia.")
    suggested_format: ContentFormat
    rationale: str = Field(description="Por que esta ideia faz sentido para ESTE negocio.")
    hook_suggestion: str = Field(description="Primeira frase para prender a atencao.")
    audience_note: str = Field(description="Que recorte do publico-alvo esta ideia atinge.")
    relevance_score: int = Field(ge=1, le=10)
    referenced_products: list[str] = Field(description="Nomes de produtos citados.")
    referenced_services: list[str] = Field(description="Nomes de servicos citados.")


class IdeaBatch(AIModel):
    ideas: list[IdeaDraft]


# ------------------------------------------------- payloads por formato ------


class ReelScene(AIModel):
    order: int = Field(ge=1)
    duration_seconds: int = Field(ge=1, le=60)
    visual: str = Field(description="O que a camera mostra.")
    on_screen_text: str = Field(description="Texto sobreposto na tela.")
    voiceover: str = Field(description="Narracao ou fala.")


class ReelPayload(AIModel):
    hook: str = Field(description="Gancho dos 3 primeiros segundos.")
    scenes: list[ReelScene]
    total_duration_seconds: int = Field(ge=5, le=180)
    music_suggestion: str
    editing_notes: str


class ImagePostPayload(AIModel):
    headline: str = Field(description="Titulo principal da imagem.")
    on_image_text: str = Field(description="Texto que aparece sobre a imagem.")
    body_text: str = Field(description="Desenvolvimento da mensagem.")
    visual_direction: str = Field(description="Direcao de arte: enquadramento, luz, cenario.")


class CarouselSlide(AIModel):
    order: int = Field(ge=1)
    title: str
    body: str
    on_image_text: str


class CarouselPayload(AIModel):
    cover_title: str
    slides: list[CarouselSlide]
    visual_direction: str


class StoryFrame(AIModel):
    order: int = Field(ge=1)
    visual: str
    text: str
    interaction: str = Field(
        description="Recurso interativo do frame: enquete, caixinha, link, quiz ou nenhum."
    )


class StoryPayload(AIModel):
    frames: list[StoryFrame]
    visual_direction: str


PayloadModel = ReelPayload | ImagePostPayload | CarouselPayload | StoryPayload


# ----------------------------------------------------------- producao --------


class ProducedContentBase(AIModel):
    title: str
    concept: str
    objective: str
    caption: str = Field(description="Legenda pronta para publicar.")
    cta: str = Field(description="Chamada para acao explicita.")
    hashtags: list[str] = Field(description="Hashtags sem o caractere '#'.")


class ReelProduction(ProducedContentBase):
    payload: ReelPayload


class ImagePostProduction(ProducedContentBase):
    payload: ImagePostPayload


class CarouselProduction(ProducedContentBase):
    payload: CarouselPayload


class StoryProduction(ProducedContentBase):
    payload: StoryPayload


# -------------------------------------------------------- regeneracao --------


class TitlePatch(AIModel):
    title: str


class ConceptPatch(AIModel):
    concept: str
    objective: str


class CaptionPatch(AIModel):
    caption: str


class HashtagsPatch(AIModel):
    hashtags: list[str]


class CtaPatch(AIModel):
    cta: str


class HookPatch(AIModel):
    hook: str


# ------------------------------------------------------------- visao ---------


class AssetAnalysis(AIModel):
    summary: str = Field(description="Descricao objetiva da imagem.")
    detected_elements: list[str] = Field(description="Elementos relevantes identificados.")
    dominant_colors: list[str]
    mood: str = Field(description="Clima/atmosfera transmitida.")
    suggested_alt_text: str
    content_opportunities: list[str] = Field(
        description="Ideias de conteudo que esta imagem especifica viabiliza."
    )
    quality_notes: str = Field(description="Limitacoes tecnicas relevantes para publicacao.")
