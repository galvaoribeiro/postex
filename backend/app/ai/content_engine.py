"""O Motor de Conteudo.

Orquestra as quatro etapas do pipeline:

    1. Contexto    -> `ContextBuilder` (modulo separado)
    2. Ideacao     -> `generate_ideas`
    3. Selecao     -> decisao do usuario, fora do motor
    4. Producao    -> `produce`

e, alem delas, a revisao continua (`regenerate`) e a leitura de imagens
(`analyze_asset`).

O motor nao conhece HTTP, banco de dados nem fila. Recebe contexto e devolve
estruturas validadas, o que o torna testavel isoladamente e permite que cada
etapa aponte para um provedor de IA diferente no futuro.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.ai.base import AICompletion, AIProvider
from app.ai.context_builder import BusinessContext
from app.ai.inputs import ContentSnapshot, IdeaInput
from app.ai.production import get_strategy
from app.ai.prompts.ideation import build_ideation_prompt
from app.ai.prompts.regeneration import build_regeneration_prompt, output_model_for_scope
from app.ai.prompts.vision import build_asset_analysis_prompt
from app.ai.registry import get_ai_provider
from app.ai.schemas import (
    AssetAnalysis,
    CaptionPatch,
    ConceptPatch,
    CtaPatch,
    HashtagsPatch,
    HookPatch,
    IdeaBatch,
    IdeaDraft,
    ProducedContentBase,
    TitlePatch,
)
from app.ai.taxonomy import ContentCategory, get_taxonomy
from app.ai.types import ImageRef
from app.core.config import settings
from app.core.exceptions import AIResponseError, ValidationError
from app.core.logging import get_logger
from app.models.enums import ContentFormat, RegenerationScope

logger = get_logger(__name__)

MAX_IDEAS_PER_RUN = 12

#: Padroes que denunciam resposta generica. Quando aparecem, o texto e
#: registrado no log para que o prompt possa ser corrigido - o conteudo ainda e
#: entregue ao usuario, que decide se aproveita ou regenera.
_PLACEHOLDER_PATTERNS = (
    re.compile(r"lorem ipsum", re.IGNORECASE),
    re.compile(r"\[nome do (produto|servico|neg[oó]cio)\]", re.IGNORECASE),
    re.compile(r"\bseu produto\b", re.IGNORECASE),
    re.compile(r"\bsua empresa\b", re.IGNORECASE),
)


@dataclass(slots=True)
class IdeationResult:
    ideas: list[IdeaDraft]
    categories: list[str]
    context_snapshot: dict[str, Any]
    provider_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ProductionResult:
    """Campos prontos para gravar em `Content`."""

    content_format: ContentFormat
    fields: dict[str, Any]
    context_snapshot: dict[str, Any]
    provider_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RegenerationResult:
    scope: RegenerationScope
    patch: dict[str, Any]
    provider_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AssetAnalysisResult:
    analysis: dict[str, Any]
    provider_metadata: dict[str, Any] = field(default_factory=dict)


class ContentEngine:
    def __init__(self, provider: AIProvider | None = None) -> None:
        self.provider = provider or get_ai_provider()
        self.taxonomy = get_taxonomy()

    # ------------------------------------------------------- etapa 2: ideacao
    async def generate_ideas(
        self,
        context: BusinessContext,
        *,
        count: int | None = None,
        categories: list[str] | None = None,
        format_hint: ContentFormat | None = None,
        extra_instruction: str | None = None,
        seed: int = 0,
    ) -> IdeationResult:
        requested = count or settings.AI_DEFAULT_IDEA_COUNT
        if requested < 1 or requested > MAX_IDEAS_PER_RUN:
            raise ValidationError(
                f"Quantidade de ideias deve estar entre 1 e {MAX_IDEAS_PER_RUN}.",
                details={"requested": requested},
            )

        plan = self.taxonomy.plan_distribution(
            requested,
            allowed=categories or list(context.preferences.preferred_categories) or None,
            avoided=list(context.preferences.avoided_categories) or None,
            seed=seed or None,
        )

        prompt = build_ideation_prompt(
            context,
            categories=list(plan),
            format_hint=format_hint,
            extra_instruction=extra_instruction,
            seed=seed,
        )
        completion = await self.provider.generate_structured(
            prompt=prompt, output_model=IdeaBatch
        )

        ideas = self._normalize_ideas(completion.value.ideas, plan, format_hint)
        if not ideas:
            raise AIResponseError("A IA nao devolveu nenhuma ideia utilizavel.")

        self._warn_on_placeholders(
            "ideation", [idea.title + " " + idea.concept for idea in ideas]
        )

        return IdeationResult(
            ideas=ideas,
            categories=[category.key for category in plan],
            context_snapshot=context.to_snapshot(),
            provider_metadata=completion.metadata(),
        )

    def _normalize_ideas(
        self,
        drafts: list[IdeaDraft],
        plan: list[ContentCategory],
        format_hint: ContentFormat | None,
    ) -> list[IdeaDraft]:
        """Corrige desvios previsiveis do modelo sem descartar o trabalho.

        O modelo as vezes inventa uma chave de pilar ou ignora a restricao de
        formato. Em vez de falhar a operacao inteira, o motor recoloca o valor
        no dominio valido - usando o pilar que ele mesmo atribuiu a posicao.
        """
        normalized: list[IdeaDraft] = []
        seen_titles: set[str] = set()

        for index, draft in enumerate(drafts):
            fallback = plan[index] if index < len(plan) else plan[-1]
            category = self.taxonomy.find(draft.category) or fallback

            content_format = format_hint or draft.suggested_format
            if content_format not in ContentFormat:  # pragma: no cover - pydantic ja valida
                content_format = category.default_format

            title = draft.title.strip()
            if not title:
                continue
            key = title.lower()
            if key in seen_titles:
                title = f"{title} ({category.label})"
                key = title.lower()
            seen_titles.add(key)

            normalized.append(
                draft.model_copy(
                    update={
                        "title": title,
                        "category": category.key,
                        "suggested_format": content_format,
                        "relevance_score": max(1, min(10, draft.relevance_score)),
                    }
                )
            )

        return normalized

    # ------------------------------------------------------ etapa 4: producao
    async def produce(
        self,
        context: BusinessContext,
        idea: IdeaInput,
        *,
        content_format: ContentFormat,
        instruction: str | None = None,
        seed: int = 0,
    ) -> ProductionResult:
        strategy = get_strategy(content_format)
        prompt = strategy.build_production_prompt(
            context, idea, instruction=instruction, seed=seed
        )
        completion: AICompletion[ProducedContentBase] = await self.provider.generate_structured(
            prompt=prompt,
            output_model=strategy.production_model,
        )

        fields = strategy.to_content_fields(completion.value)
        fields["category"] = idea.category
        self._warn_on_placeholders(prompt.name, [str(fields.get("caption", ""))])

        return ProductionResult(
            content_format=content_format,
            fields=fields,
            context_snapshot=context.to_snapshot(),
            provider_metadata=completion.metadata(),
        )

    # ------------------------------------------------------------ regeneracao
    async def regenerate(
        self,
        context: BusinessContext,
        snapshot: ContentSnapshot,
        *,
        scope: RegenerationScope,
        instruction: str | None = None,
        seed: int = 0,
    ) -> RegenerationResult:
        strategy = get_strategy(snapshot.content_format)

        if scope is RegenerationScope.HOOK and "hook" not in strategy.payload_model.model_fields:
            raise ValidationError(
                f"O formato {strategy.label} nao possui gancho separado. "
                f"Regenere o {strategy.body_label} ou a legenda.",
                details={"format": snapshot.content_format.value},
            )

        output_model = output_model_for_scope(scope, strategy)
        prompt = build_regeneration_prompt(
            context,
            strategy,
            snapshot,
            scope=scope,
            instruction=instruction,
            seed=seed,
        )
        completion = await self.provider.generate_structured(
            prompt=prompt, output_model=output_model
        )

        patch = self._patch_from_output(completion.value, scope, snapshot, strategy)
        self._warn_on_placeholders(prompt.name, [str(value) for value in patch.values()])

        return RegenerationResult(
            scope=scope,
            patch=patch,
            provider_metadata=completion.metadata(),
        )

    def _patch_from_output(
        self,
        value: Any,
        scope: RegenerationScope,
        snapshot: ContentSnapshot,
        strategy: Any,
    ) -> dict[str, Any]:
        if scope is RegenerationScope.FULL:
            return strategy.to_content_fields(value)

        if scope is RegenerationScope.BODY:
            return {"payload": value.model_dump(mode="json")}

        if isinstance(value, TitlePatch):
            return {"title": value.title.strip()}

        if isinstance(value, ConceptPatch):
            return {"concept": value.concept.strip(), "objective": value.objective.strip()}

        if isinstance(value, HookPatch):
            payload = dict(snapshot.payload)
            payload["hook"] = value.hook.strip()
            return {"payload": strategy.validate_payload(payload)}

        if isinstance(value, CaptionPatch):
            return {"caption": value.caption.strip()}

        if isinstance(value, HashtagsPatch):
            return {
                "hashtags": [
                    tag.lstrip("#").strip() for tag in value.hashtags if tag and tag.strip()
                ]
            }

        if isinstance(value, CtaPatch):
            return {"cta": value.cta.strip()}

        raise AIResponseError(  # pragma: no cover - protegido pelo mapeamento de escopos
            "Resposta de regeneracao em formato inesperado.",
            details={"scope": scope.value},
        )

    # ------------------------------------------------------------------ visao
    async def analyze_asset(
        self,
        context: BusinessContext,
        image: ImageRef,
        *,
        asset_kind: str,
        linked_to: str | None = None,
    ) -> AssetAnalysisResult:
        if not self.provider.supports_vision:
            raise ValidationError(
                "O provedor de IA configurado nao suporta analise de imagens.",
                details={"provider": self.provider.name},
            )

        prompt = build_asset_analysis_prompt(
            context, image, asset_kind=asset_kind, linked_to=linked_to
        )
        completion = await self.provider.generate_structured(
            prompt=prompt, output_model=AssetAnalysis
        )
        return AssetAnalysisResult(
            analysis=completion.value.model_dump(mode="json"),
            provider_metadata=completion.metadata(),
        )

    # ----------------------------------------------------------- diagnosticos
    def _warn_on_placeholders(self, prompt_name: str, texts: list[str]) -> None:
        for text in texts:
            for pattern in _PLACEHOLDER_PATTERNS:
                if pattern.search(text):
                    logger.warning(
                        "ai_generic_output_detected",
                        prompt=prompt_name,
                        provider=self.provider.name,
                        pattern=pattern.pattern,
                    )
                    return
