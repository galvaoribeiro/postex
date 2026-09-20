"""Geracao independente da modelo (Image A)."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, status

from app.core.deps import CurrentBusiness, CurrentUser, DbSession
from app.schemas.job import JobAccepted
from app.services.ai_service import AIService
from app.workers.dispatcher import schedule_ai_job

router = APIRouter(prefix="/talents", tags=["talents"])


@router.post(
    "/generate",
    response_model=JobAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Gera uma nova modelo e grava na biblioteca de imagens",
)
async def generate_talent(
    business: CurrentBusiness,
    user: CurrentUser,
    session: DbSession,
    background: BackgroundTasks,
) -> JobAccepted:
    job = await AIService(
        session, business=business, user_id=user.id
    ).request_talent_generation()
    schedule_ai_job(job.id, background)
    return JobAccepted(job_id=job.id, status=job.status, kind=job.kind)
