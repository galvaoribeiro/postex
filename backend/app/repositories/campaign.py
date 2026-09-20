"""Repositorio de campanhas."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import Select, or_, select
from sqlalchemy.orm import selectinload

from app.models.campaign import Campaign
from app.models.content import Content, ContentAsset
from app.models.enums import CampaignDestination, CampaignStatus
from app.repositories.base import BusinessScopedRepository


class CampaignRepository(BusinessScopedRepository[Campaign]):
    model = Campaign

    def _with_relations(self, statement: Select[tuple[Campaign]]) -> Select[tuple[Campaign]]:
        return statement.options(
            selectinload(Campaign.product),
            selectinload(Campaign.contents)
            .selectinload(Content.asset_links)
            .selectinload(ContentAsset.asset),
        )

    async def get_detailed(
        self, business_id: uuid.UUID, campaign_id: uuid.UUID
    ) -> Campaign | None:
        statement = self._with_relations(
            select(Campaign).where(
                Campaign.id == campaign_id,
                Campaign.business_id == business_id,
            )
        )
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def list_filtered(
        self,
        business_id: uuid.UUID,
        *,
        statuses: Sequence[CampaignStatus] = (),
        destinations: Sequence[CampaignDestination] = (),
        product_id: uuid.UUID | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[Campaign]:
        filters = []
        if statuses:
            filters.append(Campaign.status.in_(list(statuses)))
        if destinations:
            filters.append(Campaign.destination.in_(list(destinations)))
        if product_id is not None:
            filters.append(Campaign.product_id == product_id)
        if search:
            like = f"%{search.strip()}%"
            filters.append(or_(Campaign.title.ilike(like)))
        items = await self.list_for_business(
            business_id,
            filters=filters,
            limit=limit,
            offset=offset,
            order_by=Campaign.created_at.desc(),
        )
        # Recarrega com produto para o summary da biblioteca.
        ids = [item.id for item in items]
        if not ids:
            return items
        statement = (
            select(Campaign)
            .where(Campaign.id.in_(ids))
            .options(selectinload(Campaign.product))
        )
        loaded = (await self.session.execute(statement)).scalars().unique().all()
        by_id = {item.id: item for item in loaded}
        return [by_id[item.id] for item in items if item.id in by_id]

    async def count_filtered(
        self,
        business_id: uuid.UUID,
        *,
        statuses: Sequence[CampaignStatus] = (),
        destinations: Sequence[CampaignDestination] = (),
        product_id: uuid.UUID | None = None,
        search: str | None = None,
    ) -> int:
        filters = []
        if statuses:
            filters.append(Campaign.status.in_(list(statuses)))
        if destinations:
            filters.append(Campaign.destination.in_(list(destinations)))
        if product_id is not None:
            filters.append(Campaign.product_id == product_id)
        if search:
            like = f"%{search.strip()}%"
            filters.append(Campaign.title.ilike(like))
        return await self.count_for_business(business_id, filters=filters)
