"""Repositorios de ideias, conteudos e versoes."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import date

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import selectinload

from app.models.content import Content, ContentAsset, ContentIdea, ContentVersion
from app.models.enums import ContentFormat, ContentStatus, IdeaStatus
from app.repositories.base import BaseRepository, BusinessScopedRepository


class ContentIdeaRepository(BusinessScopedRepository[ContentIdea]):
    model = ContentIdea

    async def list_filtered(
        self,
        business_id: uuid.UUID,
        *,
        status: IdeaStatus | None = None,
        category: str | None = None,
        suggested_format: ContentFormat | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> Sequence[ContentIdea]:
        filters = []
        if status is not None:
            filters.append(ContentIdea.status == status)
        if category is not None:
            filters.append(ContentIdea.category == category)
        if suggested_format is not None:
            filters.append(ContentIdea.suggested_format == suggested_format)
        return await self.list_for_business(
            business_id,
            filters=filters,
            limit=limit,
            offset=offset,
            order_by=ContentIdea.created_at.desc(),
        )

    async def count_available(self, business_id: uuid.UUID) -> int:
        return await self.count_for_business(
            business_id, filters=(ContentIdea.status == IdeaStatus.AVAILABLE,)
        )

    async def list_by_job(self, business_id: uuid.UUID, job_id: uuid.UUID) -> Sequence[ContentIdea]:
        statement = (
            select(ContentIdea)
            .where(ContentIdea.business_id == business_id, ContentIdea.job_id == job_id)
            .order_by(ContentIdea.relevance_score.desc(), ContentIdea.created_at.asc())
        )
        return (await self.session.execute(statement)).scalars().all()


class ContentRepository(BusinessScopedRepository[Content]):
    model = Content

    def _with_relations(self, statement: Select[tuple[Content]]) -> Select[tuple[Content]]:
        return statement.options(
            selectinload(Content.asset_links).selectinload(ContentAsset.asset),
            selectinload(Content.idea),
        )

    async def get_detailed(
        self, business_id: uuid.UUID, content_id: uuid.UUID
    ) -> Content | None:
        statement = self._with_relations(
            select(Content).where(
                Content.id == content_id,
                Content.business_id == business_id,
            )
        )
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def list_filtered(
        self,
        business_id: uuid.UUID,
        *,
        statuses: Sequence[ContentStatus] = (),
        formats: Sequence[ContentFormat] = (),
        category: str | None = None,
        search: str | None = None,
        planned_from: date | None = None,
        planned_to: date | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> Sequence[Content]:
        statement = self._with_relations(
            select(Content).where(Content.business_id == business_id)
        )
        if statuses:
            statement = statement.where(Content.status.in_(list(statuses)))
        if formats:
            statement = statement.where(Content.format.in_(list(formats)))
        if category:
            statement = statement.where(Content.category == category)
        if search:
            pattern = f"%{search.strip().lower()}%"
            statement = statement.where(
                or_(
                    func.lower(Content.title).like(pattern),
                    func.lower(Content.caption).like(pattern),
                )
            )
        if planned_from:
            statement = statement.where(Content.planned_date >= planned_from)
        if planned_to:
            statement = statement.where(Content.planned_date <= planned_to)

        statement = statement.order_by(Content.updated_at.desc())
        if offset:
            statement = statement.offset(offset)
        if limit is not None:
            statement = statement.limit(limit)
        return (await self.session.execute(statement)).scalars().all()

    async def count_filtered(
        self,
        business_id: uuid.UUID,
        *,
        statuses: Sequence[ContentStatus] = (),
        formats: Sequence[ContentFormat] = (),
        category: str | None = None,
        search: str | None = None,
    ) -> int:
        statement = select(func.count()).select_from(Content).where(
            Content.business_id == business_id
        )
        if statuses:
            statement = statement.where(Content.status.in_(list(statuses)))
        if formats:
            statement = statement.where(Content.format.in_(list(formats)))
        if category:
            statement = statement.where(Content.category == category)
        if search:
            pattern = f"%{search.strip().lower()}%"
            statement = statement.where(func.lower(Content.title).like(pattern))
        return int((await self.session.execute(statement)).scalar() or 0)

    async def counts_by_status(self, business_id: uuid.UUID) -> dict[str, int]:
        statement = (
            select(Content.status, func.count())
            .where(Content.business_id == business_id)
            .group_by(Content.status)
        )
        rows = (await self.session.execute(statement)).all()
        return {status.value: count for status, count in rows}

    async def counts_by_format(self, business_id: uuid.UUID) -> dict[str, int]:
        statement = (
            select(Content.format, func.count())
            .where(Content.business_id == business_id)
            .group_by(Content.format)
        )
        rows = (await self.session.execute(statement)).all()
        return {content_format.value: count for content_format, count in rows}

    async def recent_titles(self, business_id: uuid.UUID, *, limit: int = 12) -> list[str]:
        statement = (
            select(Content.title)
            .where(Content.business_id == business_id)
            .order_by(Content.created_at.desc())
            .limit(limit)
        )
        return list((await self.session.execute(statement)).scalars().all())

    async def list_recent(self, business_id: uuid.UUID, *, limit: int = 12) -> Sequence[Content]:
        statement = (
            self._with_relations(select(Content).where(Content.business_id == business_id))
            .order_by(Content.created_at.desc())
            .limit(limit)
        )
        return (await self.session.execute(statement)).scalars().all()

    async def list_calendar(
        self, business_id: uuid.UUID, *, start: date, end: date
    ) -> Sequence[Content]:
        statement = (
            self._with_relations(
                select(Content).where(
                    Content.business_id == business_id,
                    Content.planned_date.is_not(None),
                    Content.planned_date >= start,
                    Content.planned_date <= end,
                )
            )
            .order_by(Content.planned_date.asc())
        )
        return (await self.session.execute(statement)).scalars().all()

    async def list_upcoming(
        self, business_id: uuid.UUID, *, reference: date, limit: int = 5
    ) -> Sequence[Content]:
        statement = (
            self._with_relations(
                select(Content).where(
                    Content.business_id == business_id,
                    Content.planned_date.is_not(None),
                    Content.planned_date >= reference,
                    Content.status.in_(
                        [
                            ContentStatus.APPROVED,
                            ContentStatus.SCHEDULED,
                            ContentStatus.DRAFT,
                            ContentStatus.REVIEW,
                        ]
                    ),
                )
            )
            .order_by(Content.planned_date.asc())
            .limit(limit)
        )
        return (await self.session.execute(statement)).scalars().all()

    async def count_created_since(self, business_id: uuid.UUID, *, since: date) -> int:
        statement = (
            select(func.count())
            .select_from(Content)
            .where(Content.business_id == business_id, func.date(Content.created_at) >= since)
        )
        return int((await self.session.execute(statement)).scalar() or 0)


class ContentVersionRepository(BaseRepository[ContentVersion]):
    model = ContentVersion

    async def list_for_content(self, content_id: uuid.UUID) -> Sequence[ContentVersion]:
        statement = (
            select(ContentVersion)
            .where(ContentVersion.content_id == content_id)
            .order_by(ContentVersion.version.desc())
        )
        return (await self.session.execute(statement)).scalars().all()

    async def get_version(
        self, content_id: uuid.UUID, version: int
    ) -> ContentVersion | None:
        statement = select(ContentVersion).where(
            ContentVersion.content_id == content_id,
            ContentVersion.version == version,
        )
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def next_version_number(self, content_id: uuid.UUID) -> int:
        statement = select(func.max(ContentVersion.version)).where(
            ContentVersion.content_id == content_id
        )
        current = (await self.session.execute(statement)).scalar()
        return int(current or 0) + 1
