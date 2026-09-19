"""Repositorio de jobs assincronos."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select

from app.models.enums import JobKind, JobStatus
from app.models.job import Job
from app.repositories.base import BusinessScopedRepository


class JobRepository(BusinessScopedRepository[Job]):
    model = Job

    async def get_any(self, job_id: uuid.UUID) -> Job | None:
        """Busca sem escopo de negocio.

        Uso restrito ao worker, que recebe apenas o id do job pela fila e ainda
        nao conhece o negocio. Requests HTTP devem usar `get_for_business`.
        """
        return (await self.session.execute(select(Job).where(Job.id == job_id))).scalar_one_or_none()

    async def list_recent(
        self,
        business_id: uuid.UUID,
        *,
        kind: JobKind | None = None,
        status: JobStatus | None = None,
        limit: int = 20,
    ) -> Sequence[Job]:
        filters = []
        if kind is not None:
            filters.append(Job.kind == kind)
        if status is not None:
            filters.append(Job.status == status)
        return await self.list_for_business(business_id, filters=filters, limit=limit)

    async def count_active(self, business_id: uuid.UUID) -> int:
        return await self.count_for_business(
            business_id,
            filters=(Job.status.in_([JobStatus.PENDING, JobStatus.PROCESSING]),),
        )
