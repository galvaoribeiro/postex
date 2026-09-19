"""Ciclo de vida dos jobs assincronos."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.enums import JobKind, JobStatus
from app.models.job import Job
from app.repositories.job import JobRepository


class JobService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.jobs = JobRepository(session)

    async def create(
        self,
        *,
        business_id: uuid.UUID,
        user_id: uuid.UUID,
        kind: JobKind,
        payload: dict[str, Any],
        provider: str | None = None,
    ) -> Job:
        """Cria o job e confirma a transacao imediatamente.

        O commit e explicito porque o `BackgroundTasks` do FastAPI executa
        ANTES do cleanup da dependencia de sessao (`get_session`) - o inverso
        do que se poderia supor. Sem este commit, o executor (inline ou via
        Celery apos o enqueue) tentaria ler um job que ainda nao existe de
        fato no banco.
        """
        job = await self.jobs.add(
            Job(
                business_id=business_id,
                user_id=user_id,
                kind=kind,
                status=JobStatus.PENDING,
                payload=payload,
                provider=provider,
            )
        )
        await self.session.commit()
        return job

    async def get(self, business_id: uuid.UUID, job_id: uuid.UUID) -> Job:
        job = await self.jobs.get_for_business(business_id, job_id)
        if job is None:
            raise NotFoundError("Processamento nao encontrado.")
        return job

    async def get_unscoped(self, job_id: uuid.UUID) -> Job:
        """Somente para o executor, que recebe apenas o id pela fila."""
        job = await self.jobs.get_any(job_id)
        if job is None:
            raise NotFoundError("Processamento nao encontrado.")
        return job

    async def list_recent(
        self,
        business_id: uuid.UUID,
        *,
        kind: JobKind | None = None,
        status: JobStatus | None = None,
        limit: int = 20,
    ) -> Sequence[Job]:
        return await self.jobs.list_recent(business_id, kind=kind, status=status, limit=limit)

    async def count_active(self, business_id: uuid.UUID) -> int:
        return await self.jobs.count_active(business_id)

    # ------------------------------------------------------------ transicoes
    async def mark_processing(self, job: Job, *, provider: str | None = None) -> Job:
        job.status = JobStatus.PROCESSING
        job.progress = 10
        job.started_at = datetime.now(timezone.utc)
        if provider:
            job.provider = provider
        await self.session.flush()
        return job

    async def set_progress(self, job: Job, progress: int) -> Job:
        job.progress = max(0, min(99, progress))
        await self.session.flush()
        return job

    @classmethod
    async def set_stage(cls, job_id: uuid.UUID, stage: str, progress: int) -> None:
        """Persiste o stage com transacao curta, fora do handler longo de geracao.

        Sem um commit proprio o polling da interface so veria `ideia`/`roteiro`
        depois que o job inteiro terminasse.
        """
        from app.core.database import session_scope

        async with session_scope() as session:
            service = cls(session)
            job = await service.get_unscoped(job_id)
            job.stage = stage
            job.progress = max(0, min(99, progress))
            await session.flush()

    async def complete(self, job: Job, result: dict[str, Any]) -> Job:
        job.status = JobStatus.COMPLETED
        job.progress = 100
        job.result = result
        job.error_message = None
        job.finished_at = datetime.now(timezone.utc)
        await self.session.flush()
        return job

    async def fail(self, job: Job, message: str, *, details: dict[str, Any] | None = None) -> Job:
        job.status = JobStatus.FAILED
        job.error_message = message[:2000]
        job.result = details
        job.finished_at = datetime.now(timezone.utc)
        await self.session.flush()
        return job
