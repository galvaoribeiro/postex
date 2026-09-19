"""Endpoints do dashboard e do calendario."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Query

from app.core.deps import CurrentBusiness, DbSession
from app.schemas.dashboard import CalendarRead, DashboardRead
from app.services.dashboard_service import DashboardService

router = APIRouter(tags=["dashboard"])


@router.get(
    "/dashboard",
    response_model=DashboardRead,
    summary="Responde 'o que voce deve postar hoje?'",
)
async def get_dashboard(business: CurrentBusiness, session: DbSession) -> DashboardRead:
    return await DashboardService(session).build(business)


@router.get("/calendar", response_model=CalendarRead)
async def get_calendar(
    business: CurrentBusiness,
    session: DbSession,
    year: int | None = Query(default=None, ge=2020, le=2100),
    month: int | None = Query(default=None, ge=1, le=12),
) -> CalendarRead:
    today = date.today()
    return await DashboardService(session).calendar(
        business.id, year=year or today.year, month=month or today.month
    )
