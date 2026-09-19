"""Porta de entrada das operacoes de IA.

Os endpoints nunca chamam o Motor de Conteudo diretamente. Eles pedem a este
service, que valida as precondicoes, cria um `Job` observavel e devolve. O
trabalho pesado roda fora do ciclo do request.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.registry import get_ai_provider
from app.core.exceptions import ValidationError
from app.models.business import Business
from app.models.enums import AssetStatus, JobKind, RegenerationScope
from app.models.job import Job
from app.schemas.content import (
    ContentFromIdeaRequest,
    ContentGenerateRequest,
    ContentRegenerateRequest,
    IdeaGenerateRequest,
)
from app.services.asset_service import AssetService
from app.services.content_service import ContentService
from app.services.creation_questions import persist_creation_answers, resolve_creation_item
from app.services.idea_service import IdeaService
from app.services.job_service import JobService


class AIService:
    def __init__(self, session: AsyncSession, *, business: Business, user_id: uuid.UUID) -> None:
        self.session = session
        self.business = business
        self.user_id = user_id
        self.jobs = JobService(session)
        self.ideas = IdeaService(session)
        self.contents = ContentService(session)
        self.assets = AssetService(session)

    @property
    def provider_name(self) -> str:
        return get_ai_provider().name

    async def request_ideation(self, data: IdeaGenerateRequest) -> Job:
        if not self.business.segment:
            raise ValidationError(
                "Complete o cadastro do negocio antes de gerar ideias.",
                details={"missing": ["segment"]},
            )

        return await self.jobs.create(
            business_id=self.business.id,
            user_id=self.user_id,
            kind=JobKind.IDEATION,
            provider=self.provider_name,
            payload={
                "count": data.count,
                "categories": data.categories,
                "format_hint": data.format_hint.value if data.format_hint else None,
                "instruction": data.instruction,
            },
        )

    async def request_content_creation(self, data: ContentGenerateRequest) -> Job:
        product, service = await resolve_creation_item(
            self.session,
            self.business.id,
            objective=data.objective,
            product_id=data.product_id,
            service_id=data.service_id,
        )
        instruction = await persist_creation_answers(
            self.session,
            self.business,
            product=product,
            service=service,
            objective=data.objective,
            answers=data.answers,
        )

        return await self.jobs.create(
            business_id=self.business.id,
            user_id=self.user_id,
            kind=JobKind.CONTENT_CREATION,
            provider=self.provider_name,
            payload={
                "objective": data.objective.value,
                "product_id": str(product.id) if product else None,
                "service_id": str(service.id) if service else None,
                "format": data.format.value if data.format else None,
                "instruction": instruction,
                "planned_date": data.planned_date.isoformat() if data.planned_date else None,
                "visual_tone": data.visual_tone.value,
            },
        )

    async def request_production(self, data: ContentFromIdeaRequest) -> Job:
        # Valida a posse da ideia agora, no request, para que o erro apareca
        # imediatamente em vez de virar um job que falha depois.
        idea = await self.ideas.get(self.business.id, data.idea_id)
        content_format = data.format or idea.suggested_format

        return await self.jobs.create(
            business_id=self.business.id,
            user_id=self.user_id,
            kind=JobKind.CONTENT_PRODUCTION,
            provider=self.provider_name,
            payload={
                "idea_id": str(idea.id),
                "format": content_format.value,
                "instruction": data.instruction,
                "planned_date": data.planned_date.isoformat() if data.planned_date else None,
            },
        )

    async def request_regeneration(
        self, content_id: uuid.UUID, data: ContentRegenerateRequest
    ) -> Job:
        content = await self.contents.get(self.business.id, content_id)

        if data.scope is not RegenerationScope.FULL and not content.payload:
            raise ValidationError(
                "Este conteudo ainda nao tem estrutura gerada. Regenere o conteudo completo.",
                details={"scope": data.scope.value},
            )

        return await self.jobs.create(
            business_id=self.business.id,
            user_id=self.user_id,
            kind=JobKind.CONTENT_REGENERATION,
            provider=self.provider_name,
            payload={
                "content_id": str(content.id),
                "scope": data.scope.value,
                "instruction": data.instruction,
            },
        )

    async def request_asset_analysis(self, asset_id: uuid.UUID) -> Job:
        asset = await self.assets.get(self.business.id, asset_id)

        if asset.status is not AssetStatus.READY:
            raise ValidationError("Aguarde o upload terminar antes de analisar a imagem.")
        if not asset.is_image:
            raise ValidationError("Somente imagens podem ser analisadas.")

        provider = get_ai_provider()
        if not provider.supports_vision:
            raise ValidationError(
                "O provedor de IA configurado nao suporta analise de imagens.",
                details={"provider": provider.name},
            )

        return await self.jobs.create(
            business_id=self.business.id,
            user_id=self.user_id,
            kind=JobKind.ASSET_ANALYSIS,
            provider=provider.name,
            payload={"asset_id": str(asset.id)},
        )
