"""Schemas dos jobs assincronos."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from app.models.enums import JobKind, JobStatus
from app.schemas.common import APIModel


class JobRead(APIModel):
    id: uuid.UUID
    kind: JobKind
    status: JobStatus
    progress: int
    stage: str | None = None
    provider: str | None
    result: dict[str, Any] | None
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime

    @property
    def is_finished(self) -> bool:
        return self.status in {JobStatus.COMPLETED, JobStatus.FAILED}


class JobAccepted(APIModel):
    """Resposta 202 de toda operacao de IA."""

    job_id: uuid.UUID
    status: JobStatus
    kind: JobKind
