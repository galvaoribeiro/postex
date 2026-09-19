"""Repositorios de produtos e servicos."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from app.models.catalog import Product, Service
from app.repositories.base import BusinessScopedRepository


class ProductRepository(BusinessScopedRepository[Product]):
    model = Product

    async def list_active(self, business_id: uuid.UUID) -> Sequence[Product]:
        return await self.list_for_business(
            business_id,
            filters=(Product.is_active.is_(True),),
            order_by=Product.name.asc(),
        )

    async def list_all(self, business_id: uuid.UUID) -> Sequence[Product]:
        return await self.list_for_business(business_id, order_by=Product.name.asc())


class ServiceRepository(BusinessScopedRepository[Service]):
    model = Service

    async def list_active(self, business_id: uuid.UUID) -> Sequence[Service]:
        return await self.list_for_business(
            business_id,
            filters=(Service.is_active.is_(True),),
            order_by=Service.name.asc(),
        )

    async def list_all(self, business_id: uuid.UUID) -> Sequence[Service]:
        return await self.list_for_business(business_id, order_by=Service.name.asc())
