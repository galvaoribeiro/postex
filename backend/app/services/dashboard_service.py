"""Dados do dashboard e do calendario.

O Inicio responde: abrir um preview que espera o usuario, ou ir criar. Completude
do cadastro nao bloqueia. Cobertura e contadores continuam no schema para o
Calendario e para testes.
"""

from __future__ import annotations

import calendar
import uuid
from collections.abc import Sequence
from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.business import Business
from app.models.catalog import Product, Service
from app.models.content import Content
from app.models.enums import AssetStatus, ContentStatus, IdeaStatus
from app.repositories.asset import AssetRepository
from app.repositories.catalog import ProductRepository, ServiceRepository
from app.repositories.content import ContentIdeaRepository, ContentRepository
from app.repositories.job import JobRepository
from app.schemas.dashboard import (
    CalendarCoverage,
    CalendarDay,
    CalendarRead,
    ContentCounters,
    DashboardRead,
    NextAction,
    QuickCreateItem,
)

COVERAGE_HORIZON_DAYS = 14
RECENT_WINDOW_DAYS = 30
QUICK_CREATE_LIMIT = 8


class DashboardService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.contents = ContentRepository(session)
        self.ideas = ContentIdeaRepository(session)
        self.assets = AssetRepository(session)
        self.jobs = JobRepository(session)
        self.products = ProductRepository(session)
        self.services = ServiceRepository(session)

    async def build(self, business: Business, *, today: date | None = None) -> DashboardRead:
        reference = today or date.today()

        by_status = await self.contents.counts_by_status(business.id)
        by_format = await self.contents.counts_by_format(business.id)
        ideas_available = await self.ideas.count_available(business.id)
        assets_ready = await self.assets.count_by_status(business.id, AssetStatus.READY)
        created_recently = await self.contents.count_created_since(
            business.id, since=reference - timedelta(days=RECENT_WINDOW_DAYS)
        )
        active_jobs = await self.jobs.count_active(business.id)

        today_contents = await self.contents.list_calendar(
            business.id, start=reference, end=reference
        )
        upcoming = await self.contents.list_upcoming(
            business.id, reference=reference + timedelta(days=1), limit=5
        )
        in_review = await self.contents.list_filtered(
            business.id, statuses=[ContentStatus.REVIEW, ContentStatus.DRAFT], limit=5
        )
        recent = await self.contents.list_recent(business.id, limit=6)
        top_ideas = await self.ideas.list_filtered(
            business.id, status=IdeaStatus.AVAILABLE, limit=4
        )

        coverage = await self._coverage(business, reference)
        next_action = self._next_action(in_review=in_review)
        quick_create = await self._quick_create(business.id)

        return DashboardRead(
            business_name=business.name,
            business_completeness=business.completeness_score,
            next_action=next_action,
            counters=ContentCounters(
                total=sum(by_status.values()),
                by_status=by_status,
                by_format=by_format,
                created_last_30_days=created_recently,
                ideas_available=ideas_available,
                assets_ready=assets_ready,
            ),
            calendar=coverage,
            today=list(today_contents),  # type: ignore[arg-type]
            upcoming=list(upcoming),  # type: ignore[arg-type]
            in_review=list(in_review),  # type: ignore[arg-type]
            recent=list(recent),  # type: ignore[arg-type]
            top_ideas=list(top_ideas),  # type: ignore[arg-type]
            active_jobs=active_jobs,
            quick_create=quick_create,
        )

    async def _coverage(self, business: Business, reference: date) -> CalendarCoverage:
        end = reference + timedelta(days=COVERAGE_HORIZON_DAYS - 1)
        scheduled = await self.contents.list_calendar(business.id, start=reference, end=end)
        days_with_content = {content.planned_date for content in scheduled if content.planned_date}

        target = int((business.content_preferences or {}).get("posts_per_week") or 3)
        expected_days = max(1, round(target * COVERAGE_HORIZON_DAYS / 7))
        coverage_percent = min(100, round(100 * len(days_with_content) / expected_days))

        next_gap = None
        for offset in range(COVERAGE_HORIZON_DAYS):
            day = reference + timedelta(days=offset)
            if day not in days_with_content:
                next_gap = day
                break

        return CalendarCoverage(
            horizon_days=COVERAGE_HORIZON_DAYS,
            scheduled_days=len(days_with_content),
            coverage_percent=coverage_percent,
            next_gap_date=next_gap,
            target_posts_per_week=target,
        )

    def _next_action(self, *, in_review: Sequence[Content]) -> NextAction:
        """So dois destinos: abrir o preview ou ir criar.

        Nunca um CTA que mude status sem o usuario ver o conteudo. Completude
        do cadastro nao bloqueia a criacao.
        """
        pending = [
            content
            for content in in_review
            if content.status in {ContentStatus.DRAFT, ContentStatus.REVIEW}
        ]
        if pending:
            content = pending[0]
            return NextAction(
                kind="review",
                title="Voce tem conteudo esperando",
                description=f'"{content.title}" esta pronto para voce ver.',
                cta_label="Abrir preview",
                content_id=str(content.id),
            )

        return NextAction(
            kind="create",
            title="Criar conteudo",
            description="Escolha o que divulgar e gere um post.",
            cta_label="Criar conteudo",
            href="/criar",
        )

    async def _quick_create(self, business_id: uuid.UUID) -> list[QuickCreateItem]:
        products = await self.products.list_for_business(
            business_id,
            filters=(Product.is_active.is_(True),),
            order_by=Product.created_at.desc(),
            limit=QUICK_CREATE_LIMIT,
        )
        services = await self.services.list_for_business(
            business_id,
            filters=(Service.is_active.is_(True),),
            order_by=Service.created_at.desc(),
            limit=QUICK_CREATE_LIMIT,
        )
        items: list[tuple] = [
            *(
                (product.created_at, QuickCreateItem(
                    id=str(product.id),
                    kind="product",
                    name=product.name,
                    price=float(product.price) if product.price is not None else None,
                ))
                for product in products
            ),
            *(
                (service.created_at, QuickCreateItem(
                    id=str(service.id),
                    kind="service",
                    name=service.name,
                    price=float(service.price) if service.price is not None else None,
                ))
                for service in services
            ),
        ]
        items.sort(key=lambda pair: pair[0], reverse=True)
        return [item for _, item in items[:QUICK_CREATE_LIMIT]]

    # ------------------------------------------------------------- calendario
    async def calendar(
        self, business_id: uuid.UUID, *, year: int, month: int
    ) -> CalendarRead:
        start = date(year, month, 1)
        end = date(year, month, calendar.monthrange(year, month)[1])

        scheduled = await self.contents.list_calendar(business_id, start=start, end=end)
        grouped: dict[date, list[Content]] = {}
        for content in scheduled:
            if content.planned_date:
                grouped.setdefault(content.planned_date, []).append(content)

        days = [
            CalendarDay(
                day=start + timedelta(days=offset),
                contents=grouped.get(start + timedelta(days=offset), []),  # type: ignore[arg-type]
            )
            for offset in range((end - start).days + 1)
        ]

        unscheduled = await self.contents.list_filtered(
            business_id,
            statuses=[ContentStatus.DRAFT, ContentStatus.REVIEW, ContentStatus.APPROVED],
            limit=40,
        )
        return CalendarRead(
            start=start,
            end=end,
            days=days,
            unscheduled=[  # type: ignore[arg-type]
                content for content in unscheduled if content.planned_date is None
            ],
        )
