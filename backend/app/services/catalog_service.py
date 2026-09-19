"""CRUD de produtos e servicos."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.catalog import Product, Service
from app.repositories.catalog import ProductRepository, ServiceRepository
from app.schemas.catalog import (
    ProductCreate,
    ProductUpdate,
    ServiceCreate,
    ServiceUpdate,
)


def _clean_list(values: list[str] | None) -> list[str]:
    if not values:
        return []
    cleaned = [value.strip() for value in values if value and value.strip()]
    return list(dict.fromkeys(cleaned))


class ProductService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.products = ProductRepository(session)

    async def list(self, business_id: uuid.UUID, *, only_active: bool = False) -> Sequence[Product]:
        if only_active:
            return await self.products.list_active(business_id)
        return await self.products.list_all(business_id)

    async def get(self, business_id: uuid.UUID, product_id: uuid.UUID) -> Product:
        product = await self.products.get_for_business(business_id, product_id)
        if product is None:
            raise NotFoundError("Produto nao encontrado.")
        return product

    async def create(self, business_id: uuid.UUID, data: ProductCreate) -> Product:
        return await self.products.add(
            Product(
                business_id=business_id,
                name=data.name,
                description=data.description,
                category=data.category,
                price=data.price,
                currency=data.currency.upper(),
                highlights=_clean_list(data.highlights),
                is_active=data.is_active,
            )
        )

    async def update(self, product: Product, data: ProductUpdate) -> Product:
        payload = data.model_dump(exclude_unset=True)
        if "highlights" in payload and payload["highlights"] is not None:
            payload["highlights"] = _clean_list(payload["highlights"])
        if payload.get("currency"):
            payload["currency"] = payload["currency"].upper()
        for field, value in payload.items():
            setattr(product, field, value)
        await self.session.flush()
        return product

    async def delete(self, product: Product) -> None:
        await self.products.delete(product)


class ServiceCatalogService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.services = ServiceRepository(session)

    async def list(self, business_id: uuid.UUID, *, only_active: bool = False) -> Sequence[Service]:
        if only_active:
            return await self.services.list_active(business_id)
        return await self.services.list_all(business_id)

    async def get(self, business_id: uuid.UUID, service_id: uuid.UUID) -> Service:
        service = await self.services.get_for_business(business_id, service_id)
        if service is None:
            raise NotFoundError("Servico nao encontrado.")
        return service

    async def create(self, business_id: uuid.UUID, data: ServiceCreate) -> Service:
        return await self.services.add(
            Service(
                business_id=business_id,
                name=data.name,
                description=data.description,
                category=data.category,
                price=data.price,
                currency=data.currency.upper(),
                duration_minutes=data.duration_minutes,
                deliverables=_clean_list(data.deliverables),
                is_active=data.is_active,
            )
        )

    async def update(self, service: Service, data: ServiceUpdate) -> Service:
        payload = data.model_dump(exclude_unset=True)
        if "deliverables" in payload and payload["deliverables"] is not None:
            payload["deliverables"] = _clean_list(payload["deliverables"])
        if payload.get("currency"):
            payload["currency"] = payload["currency"].upper()
        for field, value in payload.items():
            setattr(service, field, value)
        await self.session.flush()
        return service

    async def delete(self, service: Service) -> None:
        await self.services.delete(service)
