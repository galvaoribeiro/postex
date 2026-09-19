"""Endpoints das ideias geradas pelo Motor de Conteudo."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Query, status

from app.core.deps import CurrentBusiness, CurrentUser, DbSession
from app.models.enums import ContentFormat, IdeaStatus
from app.schemas.common import MessageResponse
from app.schemas.content import ContentIdeaRead, IdeaGenerateRequest, IdeaStatusUpdate
from app.schemas.job import JobAccepted
from app.services.ai_service import AIService
from app.services.idea_service import IdeaService
from app.workers.dispatcher import schedule_ai_job

router = APIRouter(prefix="/content-ideas", tags=["content-ideas"])


@router.post(
    "/generate",
    response_model=JobAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Roda o Motor de Conteudo e gera novas ideias",
)
async def generate_ideas(
    payload: IdeaGenerateRequest,
    business: CurrentBusiness,
    user: CurrentUser,
    session: DbSession,
    background: BackgroundTasks,
) -> JobAccepted:
    """Cria um job e devolve imediatamente.

    A ideacao pode levar dezenas de segundos; a interface acompanha o andamento
    em `GET /api/v1/jobs/{job_id}`.
    """
    job = await AIService(session, business=business, user_id=user.id).request_ideation(payload)
    schedule_ai_job(job.id, background)
    return JobAccepted(job_id=job.id, status=job.status, kind=job.kind)


@router.get("", response_model=list[ContentIdeaRead])
async def list_ideas(
    business: CurrentBusiness,
    session: DbSession,
    idea_status: IdeaStatus | None = Query(default=None, alias="status"),
    category: str | None = Query(default=None),
    suggested_format: ContentFormat | None = Query(default=None, alias="format"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[ContentIdeaRead]:
    ideas = await IdeaService(session).list(
        business.id,
        status=idea_status,
        category=category,
        suggested_format=suggested_format,
        limit=limit,
        offset=offset,
    )
    return [ContentIdeaRead.model_validate(idea) for idea in ideas]


@router.get("/{idea_id}", response_model=ContentIdeaRead)
async def get_idea(
    idea_id: uuid.UUID, business: CurrentBusiness, session: DbSession
) -> ContentIdeaRead:
    idea = await IdeaService(session).get(business.id, idea_id)
    return ContentIdeaRead.model_validate(idea)


@router.patch("/{idea_id}", response_model=ContentIdeaRead)
async def update_idea_status(
    idea_id: uuid.UUID,
    payload: IdeaStatusUpdate,
    business: CurrentBusiness,
    session: DbSession,
) -> ContentIdeaRead:
    service = IdeaService(session)
    idea = await service.get(business.id, idea_id)
    return ContentIdeaRead.model_validate(await service.set_status(idea, payload.status))


@router.delete("/{idea_id}", response_model=MessageResponse)
async def delete_idea(
    idea_id: uuid.UUID, business: CurrentBusiness, session: DbSession
) -> MessageResponse:
    service = IdeaService(session)
    idea = await service.get(business.id, idea_id)
    await service.delete(idea)
    return MessageResponse(message="Ideia removida.")
