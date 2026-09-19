"""Dados do dashboard e do calendario.

O dashboard responde uma pergunta: "o que voce deve postar hoje?". Por isso ele
nao e uma colecao de graficos - ele calcula a proxima acao concreta e coloca o
resto como contexto.
"""

from __future__ import annotations

import calendar
import uuid
from collections.abc import Sequence
from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.business import Business
from app.models.content import Content
from app.models.enums import AssetStatus, ContentStatus, IdeaStatus
from app.repositories.asset import AssetRepository
from app.repositories.content import ContentIdeaRepository, ContentRepository
from app.repositories.job import JobRepository
from app.schemas.dashboard import (
    CalendarCoverage,
    CalendarDay,
    CalendarRead,
    ContentCounters,
    DashboardRead,
    NextAction,
)

COVERAGE_HORIZON_DAYS = 14
RECENT_WINDOW_DAYS = 30


class DashboardService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.contents = ContentRepository(session)
        self.ideas = ContentIdeaRepository(session)
        self.assets = AssetRepository(session)
        self.jobs = JobRepository(session)

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
        next_action = self._next_action(
            business=business,
            reference=reference,
            today_contents=today_contents,
            in_review=in_review,
            ideas_available=ideas_available,
            coverage=coverage,
        )

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

    def _next_action(
        self,
        *,
        business: Business,
        reference: date,
        today_contents: Sequence[Content],
        in_review: Sequence[Content],
        ideas_available: int,
        coverage: CalendarCoverage,
    ) -> NextAction:
        """A regra de prioridade que sustenta o dashboard.

        A ordem importa: publicar o que ja esta pronto para hoje vem antes de
        gerar coisa nova, e completar o cadastro vem antes de tudo, porque sem
        contexto o Motor entrega conteudo generico.
        """
        ready_today = [
            content
            for content in today_contents
            if content.status in {ContentStatus.APPROVED, ContentStatus.SCHEDULED}
        ]
        if ready_today:
            content = ready_today[0]
            return NextAction(
                kind="publish_today",
                title="Publique hoje",
                description=f'"{content.title}" esta aprovado e planejado para hoje.',
                cta_label="Abrir conteudo",
                content_id=str(content.id),
            )

        if business.completeness_score < 60:
            return NextAction(
                kind="setup",
                title="Complete o perfil do negocio",
                description=(
                    "Quanto mais o Motor de Conteudo souber sobre o seu negocio, "
                    "menos generico o conteudo fica. Faltam informacoes importantes."
                ),
                cta_label="Completar cadastro",
            )

        pending_review = [content for content in in_review if content.status is ContentStatus.REVIEW]
        if pending_review:
            content = pending_review[0]
            return NextAction(
                kind="review",
                title="Voce tem conteudo esperando revisao",
                description=f'"{content.title}" esta aguardando a sua aprovacao.',
                cta_label="Revisar agora",
                content_id=str(content.id),
            )

        drafts = [content for content in in_review if content.status is ContentStatus.DRAFT]
        if drafts:
            content = drafts[0]
            return NextAction(
                kind="review",
                title="Termine o rascunho que ja esta pronto",
                description=f'"{content.title}" foi gerado e ainda nao foi aprovado.',
                cta_label="Abrir editor",
                content_id=str(content.id),
            )

        if ideas_available:
            return NextAction(
                kind="pick_idea",
                title=f"Voce tem {ideas_available} ideias esperando",
                description="Escolha uma ideia e transforme em conteudo pronto para publicar.",
                cta_label="Ver ideias",
            )

        gap = coverage.next_gap_date
        gap_text = (
            f" O proximo dia sem conteudo e {gap.strftime('%d/%m')}." if gap else ""
        )
        return NextAction(
            kind="generate_ideas",
            title="Gere novas ideias",
            description=(
                f"Nao ha ideias disponiveis nem conteudo em aberto.{gap_text}"
            ),
            cta_label="Gerar ideias",
        )

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
