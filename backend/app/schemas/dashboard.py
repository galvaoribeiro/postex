"""Schemas do dashboard e do calendario."""

from __future__ import annotations

from datetime import date

from pydantic import Field

from app.schemas.common import APIModel
from app.schemas.content import ContentIdeaRead, ContentSummary


class ContentCounters(APIModel):
    total: int
    by_status: dict[str, int]
    by_format: dict[str, int]
    created_last_30_days: int
    ideas_available: int
    assets_ready: int


class CalendarCoverage(APIModel):
    """Situacao do calendario nos proximos dias."""

    horizon_days: int
    scheduled_days: int
    coverage_percent: int
    next_gap_date: date | None
    target_posts_per_week: int


class NextAction(APIModel):
    """A resposta para 'o que voce deve fazer agora?'."""

    kind: str = Field(description="review | create")
    title: str
    description: str
    cta_label: str
    content_id: str | None = None
    idea_id: str | None = None
    href: str | None = None


class QuickCreateItem(APIModel):
    id: str
    kind: str
    name: str
    price: float | None = None


class DashboardRead(APIModel):
    business_name: str
    business_completeness: int
    next_action: NextAction
    counters: ContentCounters
    calendar: CalendarCoverage
    today: list[ContentSummary]
    upcoming: list[ContentSummary]
    in_review: list[ContentSummary]
    recent: list[ContentSummary]
    top_ideas: list[ContentIdeaRead]
    active_jobs: int
    quick_create: list[QuickCreateItem] = Field(default_factory=list)


class CalendarDay(APIModel):
    day: date
    contents: list[ContentSummary]


class CalendarRead(APIModel):
    start: date
    end: date
    days: list[CalendarDay]
    unscheduled: list[ContentSummary]
