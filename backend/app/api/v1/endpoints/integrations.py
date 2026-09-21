"""Geracao independente do still modelo + produto."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, status

from app.core.deps import CurrentBusiness, CurrentUser, DbSession
from app.schemas.campaign import IntegrationGenerateRequest
from app.schemas.job import JobAccepted
from app.services.ai_service import AIService
from app.workers.dispatcher import schedule_ai_job

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.post(
    "/generate",
    response_model=JobAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Gera o still da modelo com o produto e grava na biblioteca",
)
async def generate_integration(
    payload: IntegrationGenerateRequest,
    business: CurrentBusiness,
    user: CurrentUser,
    session: DbSession,
    background: BackgroundTasks,
) -> JobAccepted:
    job = await AIService(
        session, business=business, user_id=user.id
    ).request_integration_generation(payload)
    schedule_ai_job(job.id, background)
    return JobAccepted(job_id=job.id, status=job.status, kind=job.kind)
