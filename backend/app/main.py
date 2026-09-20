"""Aplicacao FastAPI."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import dispose_engine
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.services.storage_service import get_storage_service

logger = get_logger(__name__)

DESCRIPTION = """\
API do **POSTEX**: transforme produtos em conteudo que vende.

O fluxo do produto e:

`Negocio -> Produto + foto -> Destino (Instagram / TikTok / TikTok Shop) ->
Campanha (imagem, video, copy) -> Revisao -> Exportacao`

Operacoes de IA respondem `202 Accepted` com um `job_id`; acompanhe em
`GET /api/v1/jobs/{job_id}`.
"""


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    settings.validate_runtime()

    logger.info(
        "application_starting",
        environment=settings.ENVIRONMENT.value,
        ai_provider=settings.AI_PROVIDER.value,
        ai_execution_mode=settings.AI_EXECUTION_MODE.value,
    )
    # Idempotente e tolerante a falha: storage indisponivel no boot nao deve
    # impedir a API de subir, apenas os endpoints de asset falharao.
    await get_storage_service().ensure_bucket()

    yield

    await dispose_engine()
    logger.info("application_stopped")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description=DESCRIPTION,
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    # Necessario para que o browser envie os cookies httpOnly de sessao.
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Business-Id"],
)

register_exception_handlers(app)
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["infra"], summary="Liveness probe")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "environment": settings.ENVIRONMENT.value,
        "ai_provider": settings.AI_PROVIDER.value,
    }
