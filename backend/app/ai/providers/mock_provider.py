"""Provedor local, deterministico e sem custo.

Este provedor existe para que o produto seja utilizavel de ponta a ponta antes
de haver qualquer chave de IA configurada, e para que os testes exercitem o
pipeline inteiro sem rede.

Ele NAO devolve texto de enchimento: monta ideias, roteiros, legendas e hashtags
a partir do negocio real que veio em `Prompt.hints` (nome, segmento, produtos,
servicos, publico, localizacao, diferenciais). A saida e plausivel e especifica,
o que torna possivel avaliar a interface e o fluxo de revisao de verdade.

O que ele nao faz e raciocinar: os angulos vem de gabaritos por pilar
editorial. Para conteudo de producao, use `AI_PROVIDER=openai`.
"""

from __future__ import annotations

import asyncio
import hashlib
import random
import re
import time
import unicodedata
from typing import Any, ClassVar

from app.ai.base import AICompletion, AIProvider, OutputT
from app.ai.schemas import (
    AssetAnalysis,
    CaptionPatch,
    CarouselPayload,
    CarouselProduction,
    CarouselSlide,
    ConceptPatch,
    CtaPatch,
    HashtagsPatch,
    HookPatch,
    IdeaBatch,
    IdeaDraft,
    ImagePostPayload,
    ImagePostProduction,
    ReelPayload,
    ReelProduction,
    ReelScene,
    StoryFrame,
    StoryPayload,
    StoryProduction,
    TitlePatch,
)
from app.ai.types import Prompt, PromptHints
from app.core.exceptions import AIResponseError
from app.models.enums import ContentFormat

MOCK_LATENCY_SECONDS = 0.05


def _slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "", normalized.lower())


# Gabaritos por pilar editorial. `{subject}` recebe um produto, servico ou o
# proprio segmento; `{business}`, `{audience}` e `{location}` vem do contexto.
_CATEGORY_TEMPLATES: dict[str, dict[str, str]] = {
    "educativo": {
        "title": "3 cuidados com {subject} que quase ninguem faz",
        "concept": (
            "Conteudo ensinando tres cuidados praticos relacionados a {subject}, "
            "com o que fazer e o que evitar em cada um. Entrega valor mesmo para "
            "quem ainda nao e cliente de {business}."
        ),
        "objective": "Atrair {audience} pela utilidade e construir confianca antes da venda.",
        "hook": "Quase todo mundo erra o segundo cuidado com {subject}.",
        "cta": "Salva esse post para consultar na hora que precisar.",
    },
    "demonstracao": {
        "title": "{subject} do inicio ao resultado, sem corte",
        "concept": (
            "Demonstracao de {subject} acontecendo de verdade em {business}, do "
            "estado inicial ao resultado final, destacando o detalhe que so quem "
            "faz percebe."
        ),
        "objective": "Encurtar a distancia entre o interesse e a decisao de compra.",
        "hook": "Olha o antes e o depois de {subject}.",
        "cta": "Chama no direct para saber como funciona para o seu caso.",
    },
    "produto": {
        "title": "Por que {subject} vale o investimento",
        "concept": (
            "Apresentacao de {subject} traduzindo cada caracteristica em um "
            "beneficio concreto para {audience}, com foco no que diferencia a "
            "versao de {business}."
        ),
        "objective": "Fazer {audience} entender exatamente o que esta comprando.",
        "hook": "Nao e so o preco: e isso que muda em {subject}.",
        "cta": "Toca no link da bio para ver as opcoes disponiveis.",
    },
    "servico": {
        "title": "Como funciona {subject}, passo a passo",
        "concept": (
            "Explicacao da jornada completa de {subject} em {business}: primeiro "
            "contato, o que acontece durante e o que o cliente recebe no final."
        ),
        "objective": "Eliminar a inseguranca de quem nunca contratou esse tipo de servico.",
        "hook": "Antes de contratar {subject}, entenda o que realmente acontece.",
        "cta": "Manda uma mensagem e a gente monta o seu orcamento.",
    },
    "autoridade": {
        "title": "O erro que mais vejo quando o assunto e {subject}",
        "concept": (
            "Posicionamento tecnico sobre um erro comum relacionado a {subject}, "
            "com o criterio que {business} usa para fazer diferente."
        ),
        "objective": "Justificar por que {audience} deve confiar em {business} e nao em outro.",
        "hook": "Vou contrariar o que voce ouve por ai sobre {subject}.",
        "cta": "Comenta se voce ja passou por isso.",
    },
    "prova_social": {
        "title": "O caso de quem chegou aqui com problema em {subject}",
        "concept": (
            "Caso real estruturado em situacao inicial, o que foi feito com "
            "{subject} e resultado obtido, com espaco para o dado do cliente."
        ),
        "objective": "Transferir a confianca de quem ja comprou para quem ainda hesita.",
        "hook": "Ela chegou achando que nao tinha solucao para {subject}.",
        "cta": "Quer um resultado assim? Chama no direct.",
    },
    "bastidores": {
        "title": "Um dia de trabalho por aqui, comecando por {subject}",
        "concept": (
            "Rotina real de {business} mostrando o processo por tras de {subject}, "
            "com o trabalho manual e as decisoes que ninguem ve."
        ),
        "objective": "Humanizar {business} e criar vinculo com {audience}.",
        "hook": "Voce ve o resultado. Eu vou te mostrar as 6 da manha.",
        "cta": "Conta nos comentarios o que voce quer ver dos bastidores.",
    },
    "relacionamento": {
        "title": "Qual voce escolheria quando o assunto e {subject}?",
        "concept": (
            "Conversa direta com {audience} sobre preferencias em {subject}, "
            "convidando a responder em poucos segundos."
        ),
        "objective": "Aumentar interacao e entender melhor o que {audience} procura.",
        "hook": "Preciso da sua opiniao sobre {subject}.",
        "cta": "Responde aqui embaixo: opcao 1 ou opcao 2?",
    },
    "entretenimento": {
        "title": "Expectativa x realidade: {subject}",
        "concept": (
            "Conteudo leve contrastando a expectativa e a realidade de {subject} "
            "no dia a dia de {business}, com humor vindo do proprio contexto."
        ),
        "objective": "Ampliar alcance com conteudo compartilhavel.",
        "hook": "O que as pessoas pensam sobre {subject} x o que realmente acontece.",
        "cta": "Marca alguem que precisa ver isso.",
    },
    "objecoes": {
        "title": "\"{subject} e caro\" - vamos falar sobre isso",
        "concept": (
            "Resposta direta a objecao de preco em {subject}, abrindo o que esta "
            "incluso e comparando com o custo de escolher errado."
        ),
        "objective": "Remover o atrito que impede {audience} de comprar.",
        "hook": "Se voce achou {subject} caro, provavelmente comparou a coisa errada.",
        "cta": "Chama no direct e eu te mostro as opcoes que cabem no seu orcamento.",
    },
    "comparacao": {
        "title": "{subject}: qual opcao faz sentido para voce",
        "concept": (
            "Comparacao honesta entre as opcoes disponiveis em {subject}, "
            "reconhecendo em que situacao cada uma e a melhor escolha."
        ),
        "objective": "Ajudar {audience} a decidir e evidenciar os diferenciais de {business}.",
        "hook": "Nao existe a melhor opcao de {subject}. Existe a certa para o seu caso.",
        "cta": "Na duvida, me conta seu caso que eu indico.",
    },
    "tendencias": {
        "title": "O que esta em alta agora em {subject}",
        "concept": (
            "Leitura do momento atual de {subject}, conectando a novidade a algo "
            "concreto que {business} ja oferece."
        ),
        "objective": "Aproveitar a atencao que {audience} ja esta dando ao assunto.",
        "hook": "Todo mundo esta pedindo {subject} desse jeito agora.",
        "cta": "Salva para nao esquecer quando for escolher.",
    },
    "oferta": {
        "title": "Condicao especial em {subject}",
        "concept": (
            "Convite direto a compra de {subject}, deixando claro o que esta "
            "incluso, para quem serve e o prazo da condicao."
        ),
        "objective": "Converter quem ja acompanha {business} em venda.",
        "hook": "{subject} com condicao especial ate [INSERIR PRAZO].",
        "cta": "Garanta o seu pelo direct ou pelo link da bio.",
    },
}

_FALLBACK_TEMPLATE = _CATEGORY_TEMPLATES["produto"]


class _MockGenerator:
    """Gera as respostas a partir do contexto real recebido no prompt."""

    def __init__(self, hints: PromptHints, prompt_name: str) -> None:
        self.hints = hints
        seed_source = f"{hints.business_name}|{prompt_name}|{hints.seed}"
        digest = hashlib.sha256(seed_source.encode("utf-8")).hexdigest()
        self.rng = random.Random(int(digest[:12], 16))

    # ------------------------------------------------------------- contexto
    @property
    def business(self) -> str:
        return self.hints.business_name or "o negocio"

    @property
    def audience(self) -> str:
        return self.hints.target_audience or f"o publico de {self.hints.segment or 'nicho'}"

    @property
    def location(self) -> str | None:
        return self.hints.location

    def subjects(self) -> list[str]:
        items = list(self.hints.product_names) + list(self.hints.service_names)
        if not items:
            items = [self.hints.segment or "o servico principal"]
        return items

    def subject_for(self, index: int) -> str:
        items = self.subjects()
        return items[index % len(items)]

    def fill(self, template: str, subject: str) -> str:
        return template.format(
            subject=subject,
            business=self.business,
            audience=self.audience,
            location=self.location or "a regiao",
        )

    def template_for(self, category: str) -> dict[str, str]:
        return _CATEGORY_TEMPLATES.get(category, _FALLBACK_TEMPLATE)

    def hashtags(self, subject: str, category: str) -> list[str]:
        segment_slug = _slug(self.hints.segment) or "negocio"
        subject_slug = _slug(subject) or segment_slug
        business_slug = _slug(self.business) or "marca"
        tags = [
            segment_slug,
            subject_slug,
            f"{segment_slug}brasil",
            business_slug,
            _slug(category) or "conteudo",
            "pequenosnegocios",
            "empreendedorismo",
            "instagramparanegocios",
        ]
        if self.location:
            location_slug = _slug(self.location)
            if location_slug:
                tags.extend([location_slug, f"{segment_slug}{location_slug}"])
        for differentiator in self.hints.differentiators[:2]:
            differentiator_slug = _slug(differentiator)
            if len(differentiator_slug) >= 4:
                tags.append(differentiator_slug[:24])
        deduped = [tag for tag in dict.fromkeys(tags) if tag]
        return deduped[:12]

    def caption(self, subject: str, category: str, hook: str, cta: str) -> str:
        template = self.template_for(category)
        differentiator = (
            self.hints.differentiators[0]
            if self.hints.differentiators
            else "atendimento proximo e feito com cuidado"
        )
        location_line = f" Atendemos em {self.location}." if self.location else ""
        return (
            f"{hook}\n\n"
            f"{self.fill(template['concept'], subject)}\n\n"
            f"O que costuma fazer diferenca aqui em {self.business}: {differentiator}."
            f"{location_line}\n\n"
            f"{cta}"
        )

    # -------------------------------------------------------------- ideacao
    def idea_batch(self) -> IdeaBatch:
        categories = list(self.hints.categories) or ["produto", "educativo", "prova_social"]
        recent = {title.strip().lower() for title in self.hints.recent_titles}
        preferred_format = self.hints.content_format

        ideas: list[IdeaDraft] = []
        for index, category in enumerate(categories):
            subject = self.subject_for(index)
            template = self.template_for(category)
            title = self.fill(template["title"], subject)
            if title.strip().lower() in recent:
                title = f"{title} (novo angulo)"

            if preferred_format:
                suggested = ContentFormat(preferred_format)
            else:
                suggested = self._format_for_category(category)

            ideas.append(
                IdeaDraft(
                    title=title,
                    concept=self.fill(template["concept"], subject),
                    objective=self.fill(template["objective"], subject),
                    category=category,
                    suggested_format=suggested,
                    rationale=(
                        f"Ancorada em '{subject}', que esta cadastrado em {self.business}, "
                        f"e direcionada a {self.audience}."
                        + (f" Explora a presenca em {self.location}." if self.location else "")
                    ),
                    hook_suggestion=self.fill(template["hook"], subject),
                    audience_note=f"Recorte de {self.audience} com interesse em {subject}.",
                    relevance_score=self.rng.randint(6, 10),
                    referenced_products=(
                        [subject] if subject in self.hints.product_names else []
                    ),
                    referenced_services=(
                        [subject] if subject in self.hints.service_names else []
                    ),
                )
            )

        return IdeaBatch(ideas=ideas)

    def _format_for_category(self, category: str) -> ContentFormat:
        mapping = {
            "educativo": ContentFormat.CAROUSEL,
            "demonstracao": ContentFormat.REEL,
            "produto": ContentFormat.IMAGE_POST,
            "servico": ContentFormat.CAROUSEL,
            "autoridade": ContentFormat.REEL,
            "prova_social": ContentFormat.CAROUSEL,
            "bastidores": ContentFormat.STORY,
            "relacionamento": ContentFormat.STORY,
            "entretenimento": ContentFormat.REEL,
            "objecoes": ContentFormat.REEL,
            "comparacao": ContentFormat.CAROUSEL,
            "tendencias": ContentFormat.REEL,
            "oferta": ContentFormat.IMAGE_POST,
        }
        return mapping.get(category, ContentFormat.REEL)

    # ------------------------------------------------------------- producao
    def production_base(self) -> tuple[str, str, str, str, str, list[str], str]:
        """Campos comuns a qualquer formato: titulo, conceito, legenda, CTA..."""
        category = self.hints.idea_category or "produto"
        subject = self.subject_for(0)
        template = self.template_for(category)
        title = self.hints.idea_title or self.fill(template["title"], subject)
        concept = self.hints.idea_concept or self.fill(template["concept"], subject)
        objective = self.fill(template["objective"], subject)
        hook = self.fill(template["hook"], subject)
        cta = self.fill(template["cta"], subject)
        hashtags = self.hashtags(subject, category)
        caption = self.caption(subject, category, hook, cta)
        return title, concept, objective, hook, cta, hashtags, caption

    def reel_payload(self) -> ReelPayload:
        category = self.hints.idea_category or "produto"
        subject = self.subject_for(0)
        template = self.template_for(category)
        hook = self.fill(template["hook"], subject)
        differentiator = (
            self.hints.differentiators[0] if self.hints.differentiators else "o cuidado no processo"
        )

        scenes = [
            ReelScene(
                order=1,
                duration_seconds=4,
                visual=f"Close em {subject}, camera na mao, luz natural da janela.",
                on_screen_text=hook[:60],
                voiceover=hook,
            ),
            ReelScene(
                order=2,
                duration_seconds=7,
                visual=f"Plano medio mostrando {subject} sendo preparado em {self.business}.",
                on_screen_text="O que ninguem mostra",
                voiceover=(
                    f"A maioria olha so o resultado. O que muda de verdade em {subject} "
                    f"e {differentiator}."
                ),
            ),
            ReelScene(
                order=3,
                duration_seconds=8,
                visual=f"Detalhe do acabamento de {subject}, camera aproximando devagar.",
                on_screen_text="Olha o detalhe",
                voiceover=(
                    f"E por isso que {self.audience} percebe a diferenca no primeiro "
                    f"contato com {subject}."
                ),
            ),
            ReelScene(
                order=4,
                duration_seconds=6,
                visual=(
                    f"Plano aberto de {self.business}"
                    + (f" em {self.location}" if self.location else "")
                    + ", pessoa olhando para a camera."
                ),
                on_screen_text="Vem ver de perto",
                voiceover=self.fill(template["cta"], subject),
            ),
        ]

        return ReelPayload(
            hook=hook,
            scenes=scenes,
            total_duration_seconds=sum(scene.duration_seconds for scene in scenes),
            music_suggestion=(
                "Trilha instrumental leve, batida constante em torno de 100 bpm, "
                "volume baixo para nao competir com a narracao."
            ),
            editing_notes=(
                "Cortes secos entre as cenas, legenda queimada em todas as falas, "
                "zoom suave de 5% nos closes e ultimo frame parado por 1 segundo "
                "para fixar o CTA."
            ),
        )

    def image_post_payload(self) -> ImagePostPayload:
        category = self.hints.idea_category or "produto"
        subject = self.subject_for(0)
        template = self.template_for(category)
        return ImagePostPayload(
            headline=self.fill(template["title"], subject),
            on_image_text=self.fill(template["hook"], subject)[:70],
            body_text=self.fill(template["concept"], subject),
            visual_direction=(
                f"Foto de {subject} em fundo limpo, luz natural lateral, "
                "enquadramento quadrado com o produto ocupando dois tercos do "
                "quadro. Texto aplicado na faixa superior, com contraste alto. "
                "Evitar fundo poluido e filtro pesado."
            ),
        )

    def carousel_payload(self) -> CarouselPayload:
        category = self.hints.idea_category or "produto"
        subject = self.subject_for(0)
        template = self.template_for(category)
        cover = self.fill(template["title"], subject)
        differentiators = list(self.hints.differentiators) or [
            "processo conferido item por item",
            "atendimento direto com quem executa",
        ]

        slides = [
            CarouselSlide(
                order=1,
                title=cover,
                body=self.fill(template["hook"], subject),
                on_image_text=cover,
            ),
            CarouselSlide(
                order=2,
                title="Por que isso importa",
                body=self.fill(template["concept"], subject),
                on_image_text="Por que isso importa",
            ),
        ]
        for index, differentiator in enumerate(differentiators[:3], start=3):
            slides.append(
                CarouselSlide(
                    order=index,
                    title=f"Ponto {index - 2}",
                    body=(
                        f"{differentiator.capitalize()} - e isso aparece no resultado "
                        f"final de {subject}."
                    ),
                    on_image_text=differentiator[:48],
                )
            )
        slides.append(
            CarouselSlide(
                order=len(slides) + 1,
                title="O proximo passo",
                body=self.fill(template["cta"], subject),
                on_image_text="Chama no direct",
            )
        )

        return CarouselPayload(
            cover_title=cover,
            slides=slides,
            visual_direction=(
                "Fundo solido claro com faixa de cor da marca no rodape, tipografia "
                "sem serifa em dois pesos, numero do slide no canto superior "
                "direito e uma foto real a cada dois slides de texto."
            ),
        )

    def story_payload(self) -> StoryPayload:
        category = self.hints.idea_category or "produto"
        subject = self.subject_for(0)
        template = self.template_for(category)
        frames = [
            StoryFrame(
                order=1,
                visual=f"Video curto na vertical mostrando {subject} de perto.",
                text=self.fill(template["hook"], subject),
                interaction="nenhum",
            ),
            StoryFrame(
                order=2,
                visual=f"Bastidor de {self.business} com {subject} em uso.",
                text=self.fill(template["concept"], subject)[:120],
                interaction="enquete",
            ),
            StoryFrame(
                order=3,
                visual="Pessoa da equipe falando com a camera, plano proximo.",
                text=f"A duvida que mais aparece sobre {subject} e sempre a mesma.",
                interaction="caixinha de perguntas",
            ),
            StoryFrame(
                order=4,
                visual=f"Frame final com {subject} em destaque e o contato visivel.",
                text=self.fill(template["cta"], subject),
                interaction="link",
            ),
        ]
        return StoryPayload(
            frames=frames,
            visual_direction=(
                "Sequencia toda na vertical 9:16, mesma fonte e mesma cor de texto "
                "nos quatro frames, sticker de localizacao no primeiro frame."
            ),
        )

    def asset_analysis(self) -> AssetAnalysis:
        label = self.hints.image_labels[0] if self.hints.image_labels else "imagem do negocio"
        subject = self.subject_for(0)
        return AssetAnalysis(
            summary=(
                f"Imagem enviada como '{label}', relacionada a {subject} em "
                f"{self.business}. Analise simulada: o provedor mock nao processa "
                "pixels."
            ),
            detected_elements=[subject, "ambiente interno", "luz natural"],
            dominant_colors=["bege", "madeira", "branco"],
            mood="acolhedor e artesanal",
            suggested_alt_text=f"Foto de {subject} em {self.business}.",
            content_opportunities=[
                f"Post de produto destacando {subject}",
                f"Story de bastidores mostrando como {subject} e preparado",
            ],
            quality_notes=(
                "Nao foi possivel avaliar nitidez, enquadramento ou iluminacao: "
                "configure AI_PROVIDER=openai para analise real de imagem."
            ),
        )


class MockProvider(AIProvider):
    name: ClassVar[str] = "mock"

    @property
    def supports_vision(self) -> bool:
        # Declara suporte para que o fluxo de analise de imagem seja exercitavel
        # de ponta a ponta. O resultado e explicitamente marcado como simulado.
        return True

    @property
    def default_model(self) -> str:
        return "mock-deterministic-v1"

    async def generate_structured(
        self,
        *,
        prompt: Prompt,
        output_model: type[OutputT],
    ) -> AICompletion[OutputT]:
        started = time.perf_counter()
        await asyncio.sleep(MOCK_LATENCY_SECONDS)

        generator = _MockGenerator(prompt.hints, prompt.name)
        value = self._dispatch(generator, output_model)

        latency_ms = int((time.perf_counter() - started) * 1000)
        return AICompletion(
            value=value,
            provider=self.name,
            model=self.default_model,
            latency_ms=latency_ms,
        )

    def _dispatch(self, generator: _MockGenerator, output_model: type[OutputT]) -> OutputT:
        builders: dict[type, Any] = {
            IdeaBatch: generator.idea_batch,
            ReelPayload: generator.reel_payload,
            ImagePostPayload: generator.image_post_payload,
            CarouselPayload: generator.carousel_payload,
            StoryPayload: generator.story_payload,
            AssetAnalysis: generator.asset_analysis,
        }

        builder = builders.get(output_model)
        if builder is not None:
            return builder()  # type: ignore[return-value]

        if output_model in {
            ReelProduction,
            ImagePostProduction,
            CarouselProduction,
            StoryProduction,
        }:
            return self._build_production(generator, output_model)  # type: ignore[return-value]

        patch = self._build_patch(generator, output_model)
        if patch is not None:
            return patch  # type: ignore[return-value]

        raise AIResponseError(
            "O provedor mock nao sabe gerar este tipo de resposta.",
            details={"output_model": output_model.__name__},
        )

    def _build_production(self, generator: _MockGenerator, output_model: type) -> Any:
        title, concept, objective, _hook, cta, hashtags, caption = generator.production_base()
        payload_builders = {
            ReelProduction: generator.reel_payload,
            ImagePostProduction: generator.image_post_payload,
            CarouselProduction: generator.carousel_payload,
            StoryProduction: generator.story_payload,
        }
        return output_model(
            title=title,
            concept=concept,
            objective=objective,
            caption=caption,
            cta=cta,
            hashtags=hashtags,
            payload=payload_builders[output_model](),
        )

    def _build_patch(self, generator: _MockGenerator, output_model: type) -> Any | None:
        title, concept, objective, hook, cta, hashtags, caption = generator.production_base()
        instruction = (generator.hints.instruction or "").strip()
        suffix = f" ({instruction})" if instruction else ""

        if output_model is TitlePatch:
            return TitlePatch(title=f"{title}{suffix}")
        if output_model is ConceptPatch:
            return ConceptPatch(concept=f"{concept}{suffix}", objective=objective)
        if output_model is HookPatch:
            return HookPatch(hook=f"{hook}{suffix}")
        if output_model is CaptionPatch:
            return CaptionPatch(caption=f"{caption}{suffix}".strip())
        if output_model is HashtagsPatch:
            return HashtagsPatch(hashtags=hashtags)
        if output_model is CtaPatch:
            return CtaPatch(cta=f"{cta}{suffix}")
        return None
