"""Ciclo de vida das campanhas de produto."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidStateTransitionError, NotFoundError
from app.models.campaign import Campaign
from app.models.enums import (
    CAMPAIGN_STATUS_TRANSITIONS,
    CampaignDestination,
    CampaignOutput,
    CampaignStatus,
)
from app.repositories.campaign import CampaignRepository
from app.services.campaign_policy import DESTINATION_LABELS, normalize_outputs


class CampaignService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.campaigns = CampaignRepository(session)

    async def get(self, business_id: uuid.UUID, campaign_id: uuid.UUID) -> Campaign:
        campaign = await self.campaigns.get_detailed(business_id, campaign_id)
        if campaign is None:
            raise NotFoundError("Campanha nao encontrada.")
        return campaign

    async def list(
        self,
        business_id: uuid.UUID,
        *,
        statuses: Sequence[CampaignStatus] = (),
        destinations: Sequence[CampaignDestination] = (),
        product_id: uuid.UUID | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[Sequence[Campaign], int]:
        items = await self.campaigns.list_filtered(
            business_id,
            statuses=statuses,
            destinations=destinations,
            product_id=product_id,
            search=search,
            limit=limit,
            offset=offset,
        )
        total = await self.campaigns.count_filtered(
            business_id,
            statuses=statuses,
            destinations=destinations,
            product_id=product_id,
            search=search,
        )
        return items, total

    async def create(
        self,
        *,
        business_id: uuid.UUID,
        product_id: uuid.UUID,
        product_name: str,
        destination: CampaignDestination,
        outputs: list[CampaignOutput] | None,
        brief: dict,
    ) -> Campaign:
        resolved = normalize_outputs(destination, outputs)
        campaign = Campaign(
            business_id=business_id,
            product_id=product_id,
            destination=destination,
            outputs_requested=[item.value for item in resolved],
            failed_outputs=[],
            status=CampaignStatus.GENERATING,
            title=f"{product_name} · {DESTINATION_LABELS[destination]}",
            brief=brief,
            generation_context={},
        )
        self.session.add(campaign)
        await self.session.flush()
        return campaign

    async def attach_job(self, campaign: Campaign, job_id: uuid.UUID) -> Campaign:
        campaign.job_id = job_id
        await self.session.flush()
        return campaign

    async def mark_review(
        self,
        campaign: Campaign,
        *,
        title: str | None = None,
        failed_outputs: list[str] | None = None,
        generation_context: dict | None = None,
    ) -> Campaign:
        if title:
            campaign.title = title[:240]
        campaign.failed_outputs = failed_outputs or []
        campaign.status = CampaignStatus.REVIEW
        campaign.error_message = None
        if generation_context is not None:
            campaign.generation_context = generation_context
        await self.session.flush()
        return campaign

    async def mark_failed(self, campaign: Campaign, message: str) -> Campaign:
        campaign.status = CampaignStatus.FAILED
        campaign.error_message = message[:2000]
        await self.session.flush()
        return campaign

    async def change_status(
        self,
        campaign: Campaign,
        new_status: CampaignStatus,
        *,
        reason: str | None = None,
    ) -> Campaign:
        allowed = CAMPAIGN_STATUS_TRANSITIONS.get(campaign.status, frozenset())
        if new_status not in allowed:
            raise InvalidStateTransitionError(
                f"Nao e possivel mudar de {campaign.status.value} para {new_status.value}.",
                details={
                    "current": campaign.status.value,
                    "allowed": sorted(status.value for status in allowed),
                },
            )
        campaign.status = new_status
        if reason:
            brief = dict(campaign.brief or {})
            brief["last_status_reason"] = reason
            campaign.brief = brief
        await self.session.flush()
        return campaign

    @staticmethod
    def allowed_transitions(campaign: Campaign) -> list[CampaignStatus]:
        return sorted(
            CAMPAIGN_STATUS_TRANSITIONS.get(campaign.status, frozenset()),
            key=lambda status: status.value,
        )

    @staticmethod
    def outputs(campaign: Campaign) -> list[CampaignOutput]:
        result: list[CampaignOutput] = []
        for raw in campaign.outputs_requested or []:
            try:
                result.append(CampaignOutput(raw))
            except ValueError:
                continue
        return result
