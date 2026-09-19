"""Aplicacao Celery e a task que executa jobs de IA."""

from __future__ import annotations

import asyncio
import uuid

from celery import Celery

from app.core.config import settings
from app.core.logging import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)

celery_app = Celery(
    "motor_de_conteudo",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_max_tasks_per_child=200,
    broker_connection_retry_on_startup=True,
    result_expires=60 * 60 * 24,
)

AI_JOB_TASK = "ai.execute_job"


@celery_app.task(name=AI_JOB_TASK, bind=True, max_retries=0)
def execute_ai_job(self, job_id: str) -> None:  # noqa: ANN001 - assinatura do Celery
    """Ponte sincrona para o executor assincrono.

    `execute_job` trata os proprios erros e registra o resultado no banco, por
    isso a task nao precisa de retry do Celery: repetir aqui apenas duplicaria
    conteudo gerado.
    """
    from app.core.database import dispose_engine
    from app.workers.executor import execute_job

    logger.info("celery_job_received", job_id=job_id)

    async def _run() -> None:
        try:
            await execute_job(uuid.UUID(job_id))
        finally:
            # Cada chamada a `asyncio.run` cria um event loop novo, mas o
            # engine async do SQLAlchemy e um singleton de modulo com pool de
            # conexoes. Conexoes asyncpg ficam amarradas ao loop em que foram
            # criadas, entao sem descartar o pool aqui a proxima task tentaria
            # reusar uma conexao de um loop ja fechado (RuntimeError: Future
            # attached to a different loop). Descartar forca reconexao limpa.
            await dispose_engine()

    asyncio.run(_run())
