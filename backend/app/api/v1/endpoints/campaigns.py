"""Endpoints de campanhas: produto -> destino -> saidas."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Query, status

from app.core.deps import CurrentBusiness, CurrentUser, DbSession
from app.models.campaign import Campaign
from app.models.enums import (
    CampaignDestination,
    CampaignStatus,
    ContentObjective,
)
from app.schemas.asset import AssetRead
from app.schemas.campaign import (
    CampaignGenerateAccepted,
    CampaignGenerateRequest,
    CampaignRead,
    CampaignRegenerateRequest,
    CampaignStatusUpdate,
    CampaignSummary,
    DestinationRead,
)
from app.schemas.catalog import ProductRead
from app.schemas.common import Page
from app.schemas.content import ContentAssetRead, ContentRead, CreationQuestion
from app.services.ai_service import AIService
from app.services.asset_service import AssetService
from app.services.campaign_policy import DEFAULT_OUTPUTS, DESTINATION_LABELS
from app.services.campaign_service import CampaignService
from app.services.content_service import ContentService
from app.services.creation_questions import list_creation_questions, resolve_creation_item
from app.workers.dispatcher import schedule_ai_job

router = APIRouter(prefix="/campaigns", tags=["campaigns"])

DESTINATION_COPY = {
    CampaignDestination.INSTAGRAM: "Imagem comercial e legenda prontas para o feed.",
    CampaignDestination.TIKTOK: "Video vertical, roteiro e legenda nativos do TikTok.",
    CampaignDestination.TIKTOK_SHOP: "Video comercial com produto visivel e CTA de compra.",
}


def _content_to_read(content, assets: AssetService) -> ContentRead:
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
    return data.model_copy(
        update={
            "assets": linked,
            "allowed_transitions": ContentService.allowed_transitions(content),
        }
    )


def _to_read(campaign: Campaign, assets: AssetService) -> CampaignRead:
    data = CampaignRead.model_validate(campaign)
    product = ProductRead.model_validate(campaign.product) if campaign.product else None
    model = None
    if campaign.model is not None:
        model = AssetRead.model_validate(campaign.model).model_copy(
            update={"url": assets.signed_url(campaign.model)}
        )
    contents = [_content_to_read(item, assets) for item in campaign.contents]
    return data.model_copy(
        update={
            "product": product,
            "model": model,
            "contents": contents,
            "allowed_transitions": CampaignService.allowed_transitions(campaign),
        }
    )


def _to_summary(campaign: Campaign) -> CampaignSummary:
    return CampaignSummary(
        id=campaign.id,
        title=campaign.title,
        destination=campaign.destination,
        outputs_requested=list(campaign.outputs_requested or []),
        failed_outputs=list(campaign.failed_outputs or []),
        status=campaign.status,
        product_id=campaign.product_id,
        product_name=campaign.product.name if campaign.product else None,
        job_id=campaign.job_id,
        created_at=campaign.created_at,
        updated_at=campaign.updated_at,
    )


@router.get("/destinations", response_model=list[DestinationRead])
async def list_destinations(user: CurrentUser) -> list[DestinationRead]:
    return [
        DestinationRead(
            destination=item,
            label=DESTINATION_LABELS[item],
            default_outputs=list(DEFAULT_OUTPUTS[item]),
            description=DESTINATION_COPY[item],
        )
        for item in CampaignDestination
    ]


@router.get(
    "/generate/questions",
    response_model=list[CreationQuestion],
    summary="Perguntas comerciais antes de gerar a campanha",
)
async def list_generate_questions(
    business: CurrentBusiness,
    session: DbSession,
    product_id: uuid.UUID = Query(...),
    destination: CampaignDestination = Query(...),
) -> list[CreationQuestion]:
    product, _service = await resolve_creation_item(
        session,
        business.id,
        objective=ContentObjective.SELL,
        product_id=product_id,
        service_id=None,
    )
    return await list_creation_questions(
        session,
        business,
        objective=ContentObjective.SELL,
        product=product,
        service=None,
        destination=destination,
    )


@router.post(
    "/generate",
    response_model=CampaignGenerateAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Gera campanha a partir de um produto",
)
async def generate_campaign(
    payload: CampaignGenerateRequest,
    business: CurrentBusiness,
    user: CurrentUser,
    session: DbSession,
    background: BackgroundTasks,
) -> CampaignGenerateAccepted:
    job, campaign_id = await AIService(
        session, business=business, user_id=user.id
    ).request_campaign_generation(payload)
    schedule_ai_job(job.id, background)
    return CampaignGenerateAccepted(
        job_id=job.id,
        campaign_id=campaign_id,
        status=job.status.value,
        kind=job.kind.value,
    )


@router.get("", response_model=Page[CampaignSummary])
async def list_campaigns(
    business: CurrentBusiness,
    session: DbSession,
    campaign_status: list[CampaignStatus] | None = Query(default=None, alias="status"),
    destination: list[CampaignDestination] | None = Query(default=None),
    product_id: uuid.UUID | None = Query(default=None),
    search: str | None = Query(default=None, max_length=120),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> Page[CampaignSummary]:
    service = CampaignService(session)
    items, total = await service.list(
        business.id,
        statuses=campaign_status or (),
        destinations=destination or (),
        product_id=product_id,
        search=search,
        limit=limit,
        offset=offset,
    )
    return Page(
        items=[_to_summary(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{campaign_id}", response_model=CampaignRead)
async def get_campaign(
    campaign_id: uuid.UUID, business: CurrentBusiness, session: DbSession
) -> CampaignRead:
    campaign = await CampaignService(session).get(business.id, campaign_id)
    return _to_read(campaign, AssetService(session))


@router.post(
    "/{campaign_id}/regenerate",
    response_model=CampaignGenerateAccepted,
    status_code=status.HTTP_202_ACCEPTED,
)
async def regenerate_campaign(
    campaign_id: uuid.UUID,
    payload: CampaignRegenerateRequest,
    business: CurrentBusiness,
    user: CurrentUser,
    session: DbSession,
    background: BackgroundTasks,
) -> CampaignGenerateAccepted:
    job = await AIService(
        session, business=business, user_id=user.id
    ).request_campaign_regeneration(campaign_id, payload)
    schedule_ai_job(job.id, background)
    return CampaignGenerateAccepted(
        job_id=job.id,
        campaign_id=campaign_id,
        status=job.status.value,
        kind=job.kind.value,
    )


@router.post("/{campaign_id}/status", response_model=CampaignRead)
async def change_campaign_status(
    campaign_id: uuid.UUID,
    payload: CampaignStatusUpdate,
    business: CurrentBusiness,
    session: DbSession,
) -> CampaignRead:
    service = CampaignService(session)
    campaign = await service.get(business.id, campaign_id)
    await service.change_status(campaign, payload.status, reason=payload.reason)
    if payload.status.value == "APPROVED" and campaign.contents:
        contents = ContentService(session)
        from app.models.enums import ContentStatus

        for item in campaign.contents:
            detailed = await contents.get(business.id, item.id)
            if detailed.status.value in {"DRAFT", "REVIEW"}:
                try:
                    await contents.change_status(detailed, ContentStatus.APPROVED)
                except Exception:  # noqa: BLE001
                    pass
    return _to_read(await service.get(business.id, campaign_id), AssetService(session))


@router.post("/{campaign_id}/approve", response_model=CampaignRead)
async def approve_campaign(
    campaign_id: uuid.UUID, business: CurrentBusiness, session: DbSession
) -> CampaignRead:
    return await change_campaign_status(
        campaign_id,
        CampaignStatusUpdate(status=CampaignStatus.APPROVED),
        business,
        session,
    )
