"""Endpoints de produtos."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query, status

from app.core.deps import CurrentBusiness, DbSession
from app.schemas.catalog import ProductCreate, ProductRead, ProductUpdate
from app.schemas.common import MessageResponse
from app.services.catalog_service import ProductService

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=list[ProductRead])
async def list_products(
    business: CurrentBusiness,
    session: DbSession,
    only_active: bool = Query(default=False),
) -> list[ProductRead]:
    products = await ProductService(session).list(business.id, only_active=only_active)
    return [ProductRead.model_validate(product) for product in products]


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
async def create_product(
    payload: ProductCreate, business: CurrentBusiness, session: DbSession
) -> ProductRead:
    product = await ProductService(session).create(business.id, payload)
    return ProductRead.model_validate(product)


@router.get("/{product_id}", response_model=ProductRead)
async def get_product(
    product_id: uuid.UUID, business: CurrentBusiness, session: DbSession
) -> ProductRead:
    product = await ProductService(session).get(business.id, product_id)
    return ProductRead.model_validate(product)


@router.patch("/{product_id}", response_model=ProductRead)
async def update_product(
    product_id: uuid.UUID,
    payload: ProductUpdate,
    business: CurrentBusiness,
    session: DbSession,
) -> ProductRead:
    service = ProductService(session)
    product = await service.get(business.id, product_id)
    return ProductRead.model_validate(await service.update(product, payload))


@router.delete("/{product_id}", response_model=MessageResponse)
async def delete_product(
    product_id: uuid.UUID, business: CurrentBusiness, session: DbSession
) -> MessageResponse:
    service = ProductService(session)
    product = await service.get(business.id, product_id)
    await service.delete(product)
    return MessageResponse(message="Produto removido.")
