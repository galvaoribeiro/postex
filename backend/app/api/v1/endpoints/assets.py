"""Endpoints da biblioteca de assets."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Query, status

from app.core.deps import CurrentBusiness, CurrentUser, DbSession
from app.models.enums import AssetKind, AssetStatus
from app.schemas.asset import (
    AssetAnalyzeResponse,
    AssetConfirmRequest,
    AssetRead,
    AssetUpdate,
    AssetUploadRequest,
    AssetUploadResponse,
)
from app.schemas.common import MessageResponse
from app.services.ai_service import AIService
from app.services.asset_service import AssetService
from app.workers.dispatcher import schedule_ai_job

router = APIRouter(prefix="/assets", tags=["assets"])


def _to_read(service: AssetService, asset) -> AssetRead:  # noqa: ANN001
    data = AssetRead.model_validate(asset)
    return data.model_copy(update={"url": service.signed_url(asset)})


@router.get("", response_model=list[AssetRead])
async def list_assets(
    business: CurrentBusiness,
    session: DbSession,
    kind: AssetKind | None = Query(default=None),
    asset_status: AssetStatus | None = Query(default=None, alias="status"),
    product_id: uuid.UUID | None = Query(default=None),
    service_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[AssetRead]:
    service = AssetService(session)
    assets = await service.list(
        business.id,
        kind=kind,
        status=asset_status,
        product_id=product_id,
        service_id=service_id,
        limit=limit,
        offset=offset,
    )
    return [_to_read(service, asset) for asset in assets]


@router.post(
    "/upload-url",
    response_model=AssetUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Solicita URL assinada para upload direto ao storage",
)
async def create_upload_url(
    payload: AssetUploadRequest, business: CurrentBusiness, session: DbSession
) -> AssetUploadResponse:
    ticket = await AssetService(session).create_upload_ticket(business.id, payload)
    return AssetUploadResponse(
        asset_id=ticket.asset.id,
        upload_url=ticket.upload.url,
        method=ticket.upload.method,
        headers=ticket.upload.headers,
        expires_in=ticket.upload.expires_in,
    )


@router.post("/{asset_id}/confirm", response_model=AssetRead)
async def confirm_upload(
    asset_id: uuid.UUID,
    payload: AssetConfirmRequest,
    business: CurrentBusiness,
    user: CurrentUser,
    session: DbSession,
    background: BackgroundTasks,
) -> AssetRead:
    service = AssetService(session)
    asset = await service.get(business.id, asset_id)
    asset = await service.confirm_upload(asset, payload)

    if payload.analyze:
        job = await AIService(session, business=business, user_id=user.id).request_asset_analysis(
            asset.id
        )
        schedule_ai_job(job.id, background)

    return _to_read(service, asset)


@router.post(
    "/{asset_id}/analyze",
    response_model=AssetAnalyzeResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Enfileira analise de visao da imagem",
)
async def analyze_asset(
    asset_id: uuid.UUID,
    business: CurrentBusiness,
    user: CurrentUser,
    session: DbSession,
    background: BackgroundTasks,
) -> AssetAnalyzeResponse:
    job = await AIService(session, business=business, user_id=user.id).request_asset_analysis(
        asset_id
    )
    schedule_ai_job(job.id, background)
    return AssetAnalyzeResponse(job_id=job.id, asset_id=asset_id)


@router.get("/{asset_id}", response_model=AssetRead)
async def get_asset(
    asset_id: uuid.UUID, business: CurrentBusiness, session: DbSession
) -> AssetRead:
    service = AssetService(session)
    return _to_read(service, await service.get(business.id, asset_id))


@router.patch("/{asset_id}", response_model=AssetRead)
async def update_asset(
    asset_id: uuid.UUID,
    payload: AssetUpdate,
    business: CurrentBusiness,
    session: DbSession,
) -> AssetRead:
    service = AssetService(session)
    asset = await service.get(business.id, asset_id)
    return _to_read(service, await service.update(business.id, asset, payload))


@router.delete("/{asset_id}", response_model=MessageResponse)
async def delete_asset(
    asset_id: uuid.UUID, business: CurrentBusiness, session: DbSession
) -> MessageResponse:
    service = AssetService(session)
    asset = await service.get(business.id, asset_id)
    await service.delete(asset)
    return MessageResponse(message="Imagem removida.")
