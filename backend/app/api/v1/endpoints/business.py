"""Endpoints do negocio."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, status

from app.core.deps import CurrentBusiness, CurrentUser, DbSession
from app.schemas.business import BusinessCreate, BusinessRead, BusinessUpdate
from app.schemas.common import MessageResponse
from app.services.business_service import BusinessService

router = APIRouter(prefix="/business", tags=["business"])


@router.post("", response_model=BusinessRead, status_code=status.HTTP_201_CREATED)
async def create_business(
    payload: BusinessCreate, user: CurrentUser, session: DbSession
) -> BusinessRead:
    business = await BusinessService(session).create(user.id, payload)
    return BusinessRead.model_validate(business)


@router.get("", response_model=list[BusinessRead])
async def list_businesses(user: CurrentUser, session: DbSession) -> list[BusinessRead]:
    businesses = await BusinessService(session).list_for_user(user.id)
    return [BusinessRead.model_validate(business) for business in businesses]


@router.get("/current", response_model=BusinessRead)
async def get_current(business: CurrentBusiness) -> BusinessRead:
    """Negocio ativo do request (principal, ou o do header `X-Business-Id`)."""
    return BusinessRead.model_validate(business)


@router.patch("/current", response_model=BusinessRead)
async def update_current(
    payload: BusinessUpdate, business: CurrentBusiness, session: DbSession
) -> BusinessRead:
    updated = await BusinessService(session).update(business, payload)
    return BusinessRead.model_validate(updated)


@router.get("/{business_id}", response_model=BusinessRead)
async def get_business(
    business_id: uuid.UUID, user: CurrentUser, session: DbSession
) -> BusinessRead:
    business = await BusinessService(session).get(user.id, business_id)
    return BusinessRead.model_validate(business)


@router.patch("/{business_id}", response_model=BusinessRead)
async def update_business(
    business_id: uuid.UUID,
    payload: BusinessUpdate,
    user: CurrentUser,
    session: DbSession,
) -> BusinessRead:
    service = BusinessService(session)
    business = await service.get(user.id, business_id)
    return BusinessRead.model_validate(await service.update(business, payload))


@router.delete("/{business_id}", response_model=MessageResponse)
async def delete_business(
    business_id: uuid.UUID, user: CurrentUser, session: DbSession
) -> MessageResponse:
    service = BusinessService(session)
    business = await service.get(user.id, business_id)
    await service.delete(business)
    return MessageResponse(message="Negocio removido junto de todo o seu conteudo.")
