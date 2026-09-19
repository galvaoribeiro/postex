"""Endpoints de `Content`: a entidade central do produto."""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, BackgroundTasks, Query, status

from app.core.deps import CurrentBusiness, CurrentUser, DbSession
from app.models.content import Content
from app.models.enums import ContentFormat, ContentObjective, ContentStatus, RegenerationScope
from app.schemas.asset import AssetRead
from app.schemas.common import MessageResponse, Page
from app.schemas.content import (
    ContentActionResponse,
    ContentAssetLinkRequest,
    ContentAssetRead,
    ContentChangeFormatRequest,
    ContentDuplicateRequest,
    ContentFromIdeaRequest,
    ContentGenerateRequest,
    ContentManualCreate,
    ContentRead,
    ContentRegenerateRequest,
    ContentScheduleRequest,
    ContentStatusUpdate,
    ContentSummary,
    ContentUpdate,
    ContentVersionRead,
    CreationQuestion,
)
from app.schemas.job import JobAccepted
from app.services.ai_service import AIService
from app.services.asset_service import AssetService
from app.services.content_service import ContentService
from app.services.creation_questions import list_creation_questions, resolve_creation_item
from app.workers.dispatcher import schedule_ai_job

router = APIRouter(prefix="/contents", tags=["contents"])


def _to_read(content: Content, assets: AssetService) -> ContentRead:
    data = ContentRead.model_validate(content)
    linked = [
        ContentAssetRead(
            asset=AssetRead.model_validate(link.asset).model_copy(
                update={"url": assets.signed_url(link.asset)}
            ),
            role=link.role,
            position=link.position,
        )
        for link in content.asset_links
        if link.asset is not None
    ]
    presenter = (content.generation_context or {}).get("presenter") or {}
    return data.model_copy(
        update={
            "assets": linked,
            "presenter_name": presenter.get("display_name"),
            "allowed_transitions": ContentService.allowed_transitions(content),
        }
    )


# ------------------------------------------------------------------- criacao --


@router.post(
    "/from-idea",
    response_model=JobAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Etapa 3 e 4: transforma uma ideia escolhida em Content",
)
async def create_from_idea(
    payload: ContentFromIdeaRequest,
    business: CurrentBusiness,
    user: CurrentUser,
    session: DbSession,
    background: BackgroundTasks,
) -> JobAccepted:
    job = await AIService(session, business=business, user_id=user.id).request_production(payload)
    schedule_ai_job(job.id, background)
    return JobAccepted(job_id=job.id, status=job.status, kind=job.kind)


@router.get(
    "/generate/questions",
    response_model=list[CreationQuestion],
    summary="Perguntas que faltam antes de gerar (no maximo 3)",
)
async def list_generate_questions(
    business: CurrentBusiness,
    session: DbSession,
    objective: ContentObjective = Query(...),
    product_id: uuid.UUID | None = Query(default=None),
    service_id: uuid.UUID | None = Query(default=None),
) -> list[CreationQuestion]:
    product, service = await resolve_creation_item(
        session,
        business.id,
        objective=objective,
        product_id=product_id,
        service_id=service_id,
    )
    return await list_creation_questions(
        session, business, objective=objective, product=product, service=service
    )


@router.post(
    "/generate",
    response_model=JobAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Cria conteudo em um passo (ideia + producao no mesmo job)",
)
async def generate_content(
    payload: ContentGenerateRequest,
    business: CurrentBusiness,
    user: CurrentUser,
    session: DbSession,
    background: BackgroundTasks,
) -> JobAccepted:
    job = await AIService(session, business=business, user_id=user.id).request_content_creation(
        payload
    )
    schedule_ai_job(job.id, background)
    return JobAccepted(job_id=job.id, status=job.status, kind=job.kind)


@router.post("", response_model=ContentRead, status_code=status.HTTP_201_CREATED)
async def create_manual(
    payload: ContentManualCreate, business: CurrentBusiness, session: DbSession
) -> ContentRead:
    """Cria um conteudo do zero, sem passar pela IA."""
    service = ContentService(session)
    content = await service.create_manual(business.id, payload)
    return _to_read(await service.get(business.id, content.id), AssetService(session))


# ------------------------------------------------------------------- leitura --


@router.get("", response_model=Page[ContentSummary])
async def list_contents(
    business: CurrentBusiness,
    session: DbSession,
    content_status: list[ContentStatus] | None = Query(default=None, alias="status"),
    content_format: list[ContentFormat] | None = Query(default=None, alias="format"),
    category: str | None = Query(default=None),
    search: str | None = Query(default=None, max_length=120),
    planned_from: date | None = Query(default=None),
    planned_to: date | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> Page[ContentSummary]:
    items, total = await ContentService(session).list(
        business.id,
        statuses=content_status or (),
        formats=content_format or (),
        category=category,
        search=search,
        planned_from=planned_from,
        planned_to=planned_to,
        limit=limit,
        offset=offset,
    )
    return Page[ContentSummary](
        items=[ContentSummary.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{content_id}", response_model=ContentRead)
async def get_content(
    content_id: uuid.UUID, business: CurrentBusiness, session: DbSession
) -> ContentRead:
    content = await ContentService(session).get(business.id, content_id)
    return _to_read(content, AssetService(session))


@router.get("/{content_id}/versions", response_model=list[ContentVersionRead])
async def list_versions(
    content_id: uuid.UUID, business: CurrentBusiness, session: DbSession
) -> list[ContentVersionRead]:
    service = ContentService(session)
    content = await service.get(business.id, content_id)
    versions = await service.list_versions(content)
    return [ContentVersionRead.model_validate(version) for version in versions]


# -------------------------------------------------------------------- edicao --


@router.patch("/{content_id}", response_model=ContentRead)
async def update_content(
    content_id: uuid.UUID,
    payload: ContentUpdate,
    business: CurrentBusiness,
    session: DbSession,
) -> ContentRead:
    service = ContentService(session)
    content = await service.get(business.id, content_id)
    updated = await service.update(content, payload)
    return _to_read(updated, AssetService(session))


@router.post(
    "/{content_id}/regenerate",
    response_model=JobAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Regenera o conteudo inteiro ou apenas uma parte",
)
async def regenerate_content(
    content_id: uuid.UUID,
    payload: ContentRegenerateRequest,
    business: CurrentBusiness,
    user: CurrentUser,
    session: DbSession,
    background: BackgroundTasks,
) -> JobAccepted:
    job = await AIService(session, business=business, user_id=user.id).request_regeneration(
        content_id, payload
    )
    schedule_ai_job(job.id, background)
    return JobAccepted(job_id=job.id, status=job.status, kind=job.kind)


@router.post("/{content_id}/change-format", response_model=ContentActionResponse)
async def change_format(
    content_id: uuid.UUID,
    payload: ContentChangeFormatRequest,
    business: CurrentBusiness,
    user: CurrentUser,
    session: DbSession,
    background: BackgroundTasks,
) -> ContentActionResponse:
    """Troca o formato e, por padrao, reescreve o conteudo no novo formato.

    A troca em si e sincrona (o payload antigo nao vale no formato novo); a
    reescrita vai para a fila porque depende da IA.
    """
    service = ContentService(session)
    content = await service.get(business.id, content_id)
    content = await service.change_format(content, payload.format, reset_payload=True)

    job_id = None
    if payload.regenerate:
        job = await AIService(session, business=business, user_id=user.id).request_regeneration(
            content.id,
            ContentRegenerateRequest(
                scope=RegenerationScope.FULL, instruction=payload.instruction
            ),
        )
        schedule_ai_job(job.id, background)
        job_id = job.id

    refreshed = await service.get(business.id, content.id)
    return ContentActionResponse(
        content=_to_read(refreshed, AssetService(session)), job_id=job_id
    )


@router.post("/{content_id}/duplicate", response_model=ContentRead, status_code=status.HTTP_201_CREATED)
async def duplicate_content(
    content_id: uuid.UUID,
    payload: ContentDuplicateRequest,
    business: CurrentBusiness,
    session: DbSession,
) -> ContentRead:
    service = ContentService(session)
    content = await service.get(business.id, content_id)
    copy = await service.duplicate(content, title=payload.title)
    return _to_read(await service.get(business.id, copy.id), AssetService(session))


@router.post("/{content_id}/versions/{version}/restore", response_model=ContentRead)
async def restore_version(
    content_id: uuid.UUID,
    version: int,
    business: CurrentBusiness,
    session: DbSession,
) -> ContentRead:
    service = ContentService(session)
    content = await service.get(business.id, content_id)
    restored = await service.restore_version(content, version)
    return _to_read(restored, AssetService(session))


# ---------------------------------------------------------------- transicoes --


@router.post("/{content_id}/status", response_model=ContentRead)
async def change_status(
    content_id: uuid.UUID,
    payload: ContentStatusUpdate,
    business: CurrentBusiness,
    session: DbSession,
) -> ContentRead:
    service = ContentService(session)
    content = await service.get(business.id, content_id)
    updated = await service.change_status(
        content, payload.status, planned_date=payload.planned_date, reason=payload.reason
    )
    return _to_read(updated, AssetService(session))


@router.post("/{content_id}/approve", response_model=ContentRead)
async def approve_content(
    content_id: uuid.UUID, business: CurrentBusiness, session: DbSession
) -> ContentRead:
    service = ContentService(session)
    content = await service.get(business.id, content_id)
    updated = await service.change_status(content, ContentStatus.APPROVED)
    return _to_read(updated, AssetService(session))


@router.post("/{content_id}/reject", response_model=ContentRead)
async def reject_content(
    content_id: uuid.UUID, business: CurrentBusiness, session: DbSession
) -> ContentRead:
    service = ContentService(session)
    content = await service.get(business.id, content_id)
    updated = await service.change_status(content, ContentStatus.REJECTED)
    return _to_read(updated, AssetService(session))


@router.post("/{content_id}/archive", response_model=ContentRead)
async def archive_content(
    content_id: uuid.UUID, business: CurrentBusiness, session: DbSession
) -> ContentRead:
    service = ContentService(session)
    content = await service.get(business.id, content_id)
    updated = await service.change_status(content, ContentStatus.ARCHIVED)
    return _to_read(updated, AssetService(session))


@router.post("/{content_id}/schedule", response_model=ContentRead)
async def schedule_content(
    content_id: uuid.UUID,
    payload: ContentScheduleRequest,
    business: CurrentBusiness,
    session: DbSession,
) -> ContentRead:
    """Define a data planejada.

    A publicacao automatica no Instagram ainda nao existe: aqui o conteudo e
    organizado no calendario e, se estiver aprovado, passa a SCHEDULED.
    """
    service = ContentService(session)
    content = await service.get(business.id, content_id)
    updated = await service.schedule(content, payload.planned_date)
    return _to_read(updated, AssetService(session))


@router.delete("/{content_id}", response_model=MessageResponse)
async def delete_content(
    content_id: uuid.UUID, business: CurrentBusiness, session: DbSession
) -> MessageResponse:
    service = ContentService(session)
    content = await service.get(business.id, content_id)
    await service.delete(content)
    return MessageResponse(message="Conteudo excluido.")


# -------------------------------------------------------------------- assets --


@router.post("/{content_id}/assets", response_model=ContentRead)
async def link_asset(
    content_id: uuid.UUID,
    payload: ContentAssetLinkRequest,
    business: CurrentBusiness,
    session: DbSession,
) -> ContentRead:
    service = ContentService(session)
    content = await service.get(business.id, content_id)
    updated = await service.link_asset(
        content, payload.asset_id, role=payload.role, position=payload.position
    )
    return _to_read(updated, AssetService(session))


@router.delete("/{content_id}/assets/{asset_id}", response_model=ContentRead)
async def unlink_asset(
    content_id: uuid.UUID,
    asset_id: uuid.UUID,
    business: CurrentBusiness,
    session: DbSession,
) -> ContentRead:
    service = ContentService(session)
    content = await service.get(business.id, content_id)
    updated = await service.unlink_asset(content, asset_id)
    return _to_read(updated, AssetService(session))
