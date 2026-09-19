"""Repositorio de assets."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select

from app.models.asset import Asset
from app.models.enums import AssetKind, AssetStatus
from app.repositories.base import BusinessScopedRepository


class AssetRepository(BusinessScopedRepository[Asset]):
    model = Asset

    async def list_filtered(
        self,
        business_id: uuid.UUID,
        *,
        kind: AssetKind | None = None,
        status: AssetStatus | None = None,
        product_id: uuid.UUID | None = None,
        service_id: uuid.UUID | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> Sequence[Asset]:
        filters = []
        if kind is not None:
            filters.append(Asset.kind == kind)
        if status is not None:
            filters.append(Asset.status == status)
        if product_id is not None:
            filters.append(Asset.product_id == product_id)
        if service_id is not None:
            filters.append(Asset.service_id == service_id)
        return await self.list_for_business(
            business_id, filters=filters, limit=limit, offset=offset
        )

    async def list_ready_images(
        self, business_id: uuid.UUID, *, limit: int = 20
    ) -> Sequence[Asset]:
        """Assets utilizaveis como contexto pelo Motor de Conteudo."""
        statement = (
            select(Asset)
            .where(
                Asset.business_id == business_id,
                Asset.status == AssetStatus.READY,
                Asset.mime_type.startswith("image/"),
            )
            .order_by(Asset.created_at.desc())
            .limit(limit)
        )
        return (await self.session.execute(statement)).scalars().all()

    async def list_by_ids(
        self, business_id: uuid.UUID, asset_ids: Sequence[uuid.UUID]
    ) -> Sequence[Asset]:
        if not asset_ids:
            return []
        statement = select(Asset).where(
            Asset.business_id == business_id,
            Asset.id.in_(list(asset_ids)),
        )
        return (await self.session.execute(statement)).scalars().all()

    async def count_by_status(self, business_id: uuid.UUID, status: AssetStatus) -> int:
        return await self.count_for_business(business_id, filters=(Asset.status == status,))
