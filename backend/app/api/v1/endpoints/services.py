"""Endpoints de servicos."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query, status

from app.core.deps import CurrentBusiness, DbSession
from app.schemas.catalog import ServiceCreate, ServiceRead, ServiceUpdate
from app.schemas.common import MessageResponse
from app.services.catalog_service import ServiceCatalogService

router = APIRouter(prefix="/services", tags=["services"])


@router.get("", response_model=list[ServiceRead])
async def list_services(
    business: CurrentBusiness,
    session: DbSession,
    only_active: bool = Query(default=False),
) -> list[ServiceRead]:
    services = await ServiceCatalogService(session).list(business.id, only_active=only_active)
    return [ServiceRead.model_validate(service) for service in services]


@router.post("", response_model=ServiceRead, status_code=status.HTTP_201_CREATED)
async def create_service(
    payload: ServiceCreate, business: CurrentBusiness, session: DbSession
) -> ServiceRead:
    service = await ServiceCatalogService(session).create(business.id, payload)
    return ServiceRead.model_validate(service)


@router.get("/{service_id}", response_model=ServiceRead)
async def get_service(
    service_id: uuid.UUID, business: CurrentBusiness, session: DbSession
) -> ServiceRead:
    service = await ServiceCatalogService(session).get(business.id, service_id)
    return ServiceRead.model_validate(service)


@router.patch("/{service_id}", response_model=ServiceRead)
async def update_service(
    service_id: uuid.UUID,
    payload: ServiceUpdate,
    business: CurrentBusiness,
    session: DbSession,
) -> ServiceRead:
    catalog = ServiceCatalogService(session)
    service = await catalog.get(business.id, service_id)
    return ServiceRead.model_validate(await catalog.update(service, payload))


@router.delete("/{service_id}", response_model=MessageResponse)
async def delete_service(
    service_id: uuid.UUID, business: CurrentBusiness, session: DbSession
) -> MessageResponse:
    catalog = ServiceCatalogService(session)
    service = await catalog.get(business.id, service_id)
    await catalog.delete(service)
    return MessageResponse(message="Servico removido.")
