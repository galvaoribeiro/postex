"""Ideias geradas pelo Motor de Conteudo."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.content_engine import IdeationResult
from app.ai.inputs import IdeaInput
from app.core.exceptions import ConflictError, NotFoundError
from app.models.content import ContentIdea
from app.models.enums import ContentFormat, IdeaStatus
from app.repositories.content import ContentIdeaRepository


class IdeaService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.ideas = ContentIdeaRepository(session)

    async def get(self, business_id: uuid.UUID, idea_id: uuid.UUID) -> ContentIdea:
        idea = await self.ideas.get_for_business(business_id, idea_id)
        if idea is None:
            raise NotFoundError("Ideia nao encontrada.")
        return idea

    async def list(
        self,
        business_id: uuid.UUID,
        *,
        status: IdeaStatus | None = None,
        category: str | None = None,
        suggested_format: ContentFormat | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[ContentIdea]:
        return await self.ideas.list_filtered(
            business_id,
            status=status,
            category=category,
            suggested_format=suggested_format,
            limit=limit,
            offset=offset,
        )

    async def count_available(self, business_id: uuid.UUID) -> int:
        return await self.ideas.count_available(business_id)

    async def persist_batch(
        self,
        business_id: uuid.UUID,
        result: IdeationResult,
        *,
        job_id: uuid.UUID | None = None,
    ) -> list[ContentIdea]:
        """Grava as ideias junto do contexto que as gerou."""
        created: list[ContentIdea] = []
        for draft in result.ideas:
            idea = ContentIdea(
                business_id=business_id,
                title=draft.title[:240],
                concept=draft.concept,
                objective=draft.objective,
                category=draft.category,
                suggested_format=draft.suggested_format,
                rationale=draft.rationale,
                hook_suggestion=draft.hook_suggestion,
                audience_note=draft.audience_note,
                relevance_score=draft.relevance_score,
                referenced_products=list(draft.referenced_products),
                referenced_services=list(draft.referenced_services),
                status=IdeaStatus.AVAILABLE,
                context_snapshot={
                    "context": result.context_snapshot,
                    "provider": result.provider_metadata,
                    "categories_planned": result.categories,
                },
                job_id=job_id,
            )
            self.session.add(idea)
            created.append(idea)

        await self.session.flush()
        return created

    async def set_status(self, idea: ContentIdea, status: IdeaStatus) -> ContentIdea:
        idea.status = status
        await self.session.flush()
        return idea

    async def mark_used(self, idea: ContentIdea) -> ContentIdea:
        return await self.set_status(idea, IdeaStatus.USED)

    async def delete(self, idea: ContentIdea) -> None:
        if idea.status is IdeaStatus.USED:
            raise ConflictError(
                "Esta ideia ja virou conteudo. Arquive o conteudo em vez de excluir a ideia."
            )
        await self.ideas.delete(idea)

    @staticmethod
    def to_engine_input(idea: ContentIdea) -> IdeaInput:
        return IdeaInput(
            title=idea.title,
            concept=idea.concept,
            objective=idea.objective,
            category=idea.category,
            hook_suggestion=idea.hook_suggestion,
            audience_note=idea.audience_note,
            referenced_products=tuple(idea.referenced_products or ()),
            referenced_services=tuple(idea.referenced_services or ()),
        )
