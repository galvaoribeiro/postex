"""Execucao dos jobs de IA.

O mesmo codigo roda no worker Celery e no modo `inline`. A diferenca entre os
dois modos esta apenas em quem chama `execute_job`.

Cada transicao de estado usa a sua propria transacao curta, para que o
`PROCESSING` fique visivel na interface enquanto a geracao acontece, e para que
uma falha na geracao nao desfaca o registro do erro.
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from app.ai.content_engine import ContentEngine
from app.ai.context_builder import ContextBuilder
from app.ai.registry import get_ai_provider
from app.ai.taxonomy import pick_pillar_for_objective
from app.ai.types import ImageRef
from app.core.database import session_scope
from app.core.exceptions import DomainError, NotFoundError
from app.core.logging import get_logger
from app.models.business import Business
from app.models.enums import (
    TERMINAL_JOB_STATUSES,
    ContentFormat,
    ContentObjective,
    JobKind,
    RegenerationScope,
)
from app.repositories.business import BusinessRepository
from app.services.asset_service import AssetService
from app.services.content_service import ContentService
from app.services.idea_service import IdeaService
from app.services.job_service import JobService
from app.services.still_service import StillService
from app.services.storage_service import get_storage_service

logger = get_logger(__name__)


async def execute_job(job_id: uuid.UUID) -> None:
    """Executa um job pelo id. Nunca levanta: o resultado vai para o registro.

    O `_claim` tambem fica dentro do `try`: uma falha ali (ex.: instabilidade
    momentanea de conexao com o banco) nao pode deixar o job preso em PENDING
    para sempre sem nenhum registro do motivo.
    """
    kind = None
    try:
        claimed = await _claim(job_id)
        if claimed is None:
            return
        kind, business_id, payload = claimed
        result = await _run_handler(kind, business_id, job_id, payload)
    except DomainError as exc:
        logger.warning(
            "ai_job_failed", job_id=str(job_id), kind=kind, reason=exc.message
        )
        await _fail(job_id, exc.message, {"code": exc.code, **exc.details})
        return
    except Exception as exc:  # noqa: BLE001 - qualquer falha precisa virar FAILED
        logger.exception("ai_job_crashed", job_id=str(job_id), kind=kind)
        await _fail(job_id, f"Falha inesperada no processamento: {exc}")
        return

    await _complete(job_id, result)
    logger.info("ai_job_completed", job_id=str(job_id), kind=kind.value)


# ------------------------------------------------------------------ estados --


async def _claim(job_id: uuid.UUID) -> tuple[JobKind, uuid.UUID, dict[str, Any]] | None:
    """Marca o job como PROCESSING e devolve o que o handler precisa.

    Devolve `None` quando o job ja foi processado, o que torna a execucao
    idempotente diante de reentrega da fila.
    """
    async with session_scope() as session:
        jobs = JobService(session)
        job = await jobs.get_unscoped(job_id)
        if job.status in TERMINAL_JOB_STATUSES:
            logger.info("ai_job_skipped", job_id=str(job_id), status=job.status.value)
            return None

        await jobs.mark_processing(job, provider=get_ai_provider().name)
        return job.kind, job.business_id, dict(job.payload or {})


async def _complete(job_id: uuid.UUID, result: dict[str, Any]) -> None:
    async with session_scope() as session:
        jobs = JobService(session)
        await jobs.complete(await jobs.get_unscoped(job_id), result)


async def _fail(job_id: uuid.UUID, message: str, details: dict[str, Any] | None = None) -> None:
    async with session_scope() as session:
        jobs = JobService(session)
        await jobs.fail(await jobs.get_unscoped(job_id), message, details=details)


# ----------------------------------------------------------------- handlers --


async def _run_handler(
    kind: JobKind,
    business_id: uuid.UUID,
    job_id: uuid.UUID,
    payload: dict[str, Any],
) -> dict[str, Any]:
    handlers = {
        JobKind.IDEATION: _handle_ideation,
        JobKind.CONTENT_PRODUCTION: _handle_production,
        JobKind.CONTENT_REGENERATION: _handle_regeneration,
        JobKind.ASSET_ANALYSIS: _handle_asset_analysis,
        JobKind.CONTENT_CREATION: _handle_content_creation,
    }
    handler = handlers[kind]

    async with session_scope() as session:
        business = await BusinessRepository(session).get_unscoped(business_id)
        if business is None:
            raise NotFoundError("Negocio do processamento nao existe mais.")
        return await handler(session, business, job_id, payload)


async def _handle_ideation(
    session: Any, business: Business, job_id: uuid.UUID, payload: dict[str, Any]
) -> dict[str, Any]:
    context = await ContextBuilder(session).build(business)
    engine = ContentEngine()

    format_hint = payload.get("format_hint")
    result = await engine.generate_ideas(
        context,
        count=payload.get("count"),
        categories=payload.get("categories") or None,
        format_hint=ContentFormat(format_hint) if format_hint else None,
        extra_instruction=payload.get("instruction"),
        seed=int(job_id.int % 1_000_000),
    )

    ideas = await IdeaService(session).persist_batch(business.id, result, job_id=job_id)
    return {
        "idea_ids": [str(idea.id) for idea in ideas],
        "count": len(ideas),
        "categories": result.categories,
        "provider": result.provider_metadata,
    }


async def _handle_production(
    session: Any, business: Business, job_id: uuid.UUID, payload: dict[str, Any]
) -> dict[str, Any]:
    idea_service = IdeaService(session)
    idea = await idea_service.get(business.id, uuid.UUID(payload["idea_id"]))
    content_format = ContentFormat(payload["format"])

    provider = get_ai_provider()
    context = await ContextBuilder(session).build(
        business, include_image_urls=provider.supports_vision
    )
    engine = ContentEngine(provider)

    result = await engine.produce(
        context,
        IdeaService.to_engine_input(idea),
        content_format=content_format,
        instruction=payload.get("instruction"),
        seed=int(job_id.int % 1_000_000),
    )

    planned_date = payload.get("planned_date")
    content = await ContentService(session).create_from_production(
        business_id=business.id,
        result=result,
        idea_id=idea.id,
        planned_date=date.fromisoformat(planned_date) if planned_date else None,
    )
    await idea_service.mark_used(idea)

    return {
        "content_id": str(content.id),
        "format": content.format.value,
        "title": content.title,
        "provider": result.provider_metadata,
    }


async def _handle_regeneration(
    session: Any, business: Business, job_id: uuid.UUID, payload: dict[str, Any]
) -> dict[str, Any]:
    content_service = ContentService(session)
    content = await content_service.get(business.id, uuid.UUID(payload["content_id"]))
    scope = RegenerationScope(payload["scope"])
    instruction = payload.get("instruction")

    context = await ContextBuilder(session).build(business)
    engine = ContentEngine()
    result = await engine.regenerate(
        context,
        ContentService.to_engine_snapshot(content),
        scope=scope,
        instruction=instruction,
        seed=int(job_id.int % 1_000_000),
    )

    await content_service.apply_regeneration(content, result, instruction=instruction)
    return {
        "content_id": str(content.id),
        "scope": scope.value,
        "version": content.current_version,
        "provider": result.provider_metadata,
    }


async def _handle_asset_analysis(
    session: Any, business: Business, job_id: uuid.UUID, payload: dict[str, Any]
) -> dict[str, Any]:
    asset_service = AssetService(session)
    asset = await asset_service.get(business.id, uuid.UUID(payload["asset_id"]))

    storage = get_storage_service()
    image = ImageRef(
        # URL interna: quem le e o provedor de IA a partir do backend.
        url=storage.create_presigned_download(asset.storage_key, internal=True),
        mime_type=asset.mime_type,
        label=asset.title or asset.original_filename,
    )

    context = await ContextBuilder(session).build(business)
    engine = ContentEngine()
    result = await engine.analyze_asset(
        context,
        image,
        asset_kind=asset.kind.value,
        linked_to=(
            f"produto {asset.product.name}"
            if asset.product
            else (f"servico {asset.service.name}" if asset.service else None)
        ),
    )

    await asset_service.set_analysis(asset, result.analysis)
    return {
        "asset_id": str(asset.id),
        "summary": result.analysis.get("summary"),
        "provider": result.provider_metadata,
    }


async def _handle_content_creation(
    session: Any, business: Business, job_id: uuid.UUID, payload: dict[str, Any]
) -> dict[str, Any]:
    objective = ContentObjective(payload["objective"])
    product_id = uuid.UUID(payload["product_id"]) if payload.get("product_id") else None
    service_id = uuid.UUID(payload["service_id"]) if payload.get("service_id") else None
    format_hint = ContentFormat(payload["format"]) if payload.get("format") else None
    instruction = payload.get("instruction")
    planned_date = payload.get("planned_date")

    provider = get_ai_provider()
    context = await ContextBuilder(session).build(
        business,
        include_image_urls=provider.supports_vision,
        focus_product_id=product_id,
        focus_service_id=service_id,
    )
    engine = ContentEngine(provider)
    pillar = pick_pillar_for_objective(
        objective,
        seed=int(job_id.int % 1_000_000),
        service_focused=service_id is not None,
    )
    stages: list[str] = []

    async def mark(stage: str, progress: int) -> None:
        stages.append(stage)
        await JobService.set_stage(job_id, stage, progress)

    await mark("ideia", 25)
    ideation = await engine.generate_ideas(
        context,
        count=1,
        categories=[pillar],
        format_hint=format_hint,
        extra_instruction=instruction,
        seed=int(job_id.int % 1_000_000),
    )
    idea_service = IdeaService(session)
    idea = (await idea_service.persist_batch(business.id, ideation, job_id=job_id))[0]

    content_format = format_hint or idea.suggested_format
    await mark("roteiro", 60)
    production = await engine.produce(
        context,
        IdeaService.to_engine_input(idea),
        content_format=content_format,
        instruction=instruction,
        seed=int(job_id.int % 1_000_000),
    )

    await mark("imagem", 78)
    content = await ContentService(session).create_from_production(
        business_id=business.id,
        result=production,
        idea_id=idea.id,
        planned_date=date.fromisoformat(planned_date) if planned_date else None,
    )
    _asset, still_meta = await StillService(session).attach_cover(
        business=business,
        content=content,
        context=context,
        production=production,
        seed=int(job_id.int % 1_000_000),
        product_id=product_id,
        service_id=service_id,
    )
    await mark("finalizando", 92)
    await idea_service.mark_used(idea)

    return {
        "content_id": str(content.id),
        "idea_id": str(idea.id),
        "format": content.format.value,
        "title": content.title,
        "stages": stages,
        "image": still_meta.get("image"),
        "provider": production.provider_metadata,
    }
