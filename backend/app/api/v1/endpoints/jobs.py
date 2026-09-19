"""Endpoints de acompanhamento dos jobs assincronos."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query

from app.core.deps import CurrentBusiness, DbSession
from app.models.enums import JobKind, JobStatus
from app.schemas.job import JobRead
from app.services.job_service import JobService

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get(
    "/{job_id}",
    response_model=JobRead,
    summary="Estado de um processamento (PENDING/PROCESSING/COMPLETED/FAILED)",
)
async def get_job(
    job_id: uuid.UUID, business: CurrentBusiness, session: DbSession
) -> JobRead:
    job = await JobService(session).get(business.id, job_id)
    return JobRead.model_validate(job)


@router.get("", response_model=list[JobRead])
async def list_jobs(
    business: CurrentBusiness,
    session: DbSession,
    kind: JobKind | None = Query(default=None),
    job_status: JobStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=20, ge=1, le=100),
) -> list[JobRead]:
    jobs = await JobService(session).list_recent(
        business.id, kind=kind, status=job_status, limit=limit
    )
    return [JobRead.model_validate(job) for job in jobs]
