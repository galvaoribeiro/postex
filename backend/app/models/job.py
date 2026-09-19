"""Job: unidade de trabalho assincrona observavel pela interface.

Existe para que o frontend tenha uma fonte de verdade sobre o andamento das
operacoes de IA (PENDING -> PROCESSING -> COMPLETED/FAILED) sem depender do
backend do Celery e sem perder o resultado quando o usuario recarrega a pagina.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, JSONType, TimestampMixin, UUIDPrimaryKeyMixin, enum_column
from app.models.enums import JobKind, JobStatus

if TYPE_CHECKING:
    from app.models.business import Business
    from app.models.user import User


class Job(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "jobs"

    business_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    kind: Mapped[JobKind] = mapped_column(enum_column(JobKind), nullable=False)
    status: Mapped[JobStatus] = mapped_column(
        enum_column(JobStatus), default=JobStatus.PENDING, index=True, nullable=False
    )
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    #: Etapa visivel do job unico de criacao (`ideia` / `roteiro` / `finalizando`).
    stage: Mapped[str | None] = mapped_column(String(32))

    payload: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict, nullable=False)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONType)
    error_message: Mapped[str | None] = mapped_column(Text)

    provider: Mapped[str | None] = mapped_column(String(40))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    business: Mapped["Business"] = relationship()
    user: Mapped["User"] = relationship()

    @property
    def duration_seconds(self) -> float | None:
        if not self.started_at or not self.finished_at:
            return None
        return (self.finished_at - self.started_at).total_seconds()
