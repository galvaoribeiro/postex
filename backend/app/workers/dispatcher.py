"""Agendamento dos jobs de IA apos o commit do request.

O envio acontece em `BackgroundTasks`, ou seja, depois que a resposta HTTP foi
produzida e a transacao confirmada. Isso elimina a corrida em que o worker leria
o job antes de ele existir no banco.
"""

from __future__ import annotations

import uuid

from fastapi import BackgroundTasks

from app.core.config import AIExecutionMode, settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def schedule_ai_job(job_id: uuid.UUID, background: BackgroundTasks) -> None:
    if settings.AI_EXECUTION_MODE is AIExecutionMode.CELERY:
        background.add_task(_send_to_broker, job_id)
    else:
        background.add_task(_run_inline, job_id)


def _send_to_broker(job_id: uuid.UUID) -> None:
    from app.workers.celery_app import AI_JOB_TASK, celery_app

    try:
        celery_app.send_task(AI_JOB_TASK, args=[str(job_id)])
        logger.info("ai_job_enqueued", job_id=str(job_id))
    except Exception as exc:  # noqa: BLE001 - broker indisponivel nao pode deixar o job preso
        logger.error("ai_job_enqueue_failed", job_id=str(job_id), error=str(exc))
        _mark_enqueue_failure(job_id, str(exc))


def _mark_enqueue_failure(job_id: uuid.UUID, error: str) -> None:
    """Sem isso o job ficaria eternamente em PENDING e a interface travaria."""
    import asyncio

    from app.core.database import session_scope
    from app.services.job_service import JobService

    async def _fail() -> None:
        async with session_scope() as session:
            jobs = JobService(session)
            job = await jobs.get_unscoped(job_id)
            await jobs.fail(
                job,
                "Nao foi possivel enfileirar o processamento. Verifique se o Redis "
                "e o worker estao ativos.",
                details={"error": error},
            )

    try:
        asyncio.run(_fail())
    except Exception:  # noqa: BLE001 - best effort
        logger.exception("ai_job_failure_record_failed", job_id=str(job_id))


async def _run_inline(job_id: uuid.UUID) -> None:
    from app.workers.executor import execute_job

    await execute_job(job_id)
