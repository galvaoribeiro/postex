"""Repositorios: o unico lugar que monta queries.

O ponto central de seguranca esta em `BusinessScopedRepository`: metodos de
leitura e escrita exigem `business_id` na assinatura. O isolamento entre contas
nao depende de o endpoint lembrar de filtrar - nao ha como consultar sem dizer
de qual negocio.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any, Generic, TypeVar

from sqlalchemy import Select, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, instance: ModelT) -> ModelT:
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def delete(self, instance: ModelT) -> None:
        await self.session.delete(instance)
        await self.session.flush()

    async def flush(self) -> None:
        await self.session.flush()

    async def refresh(self, instance: ModelT, attributes: list[str] | None = None) -> None:
        await self.session.refresh(instance, attribute_names=attributes)


class BusinessScopedRepository(BaseRepository[ModelT]):
    """Repositorio de entidades que pertencem a um negocio."""

    async def get_for_business(
        self, business_id: uuid.UUID, entity_id: uuid.UUID
    ) -> ModelT | None:
        statement = select(self.model).where(
            self.model.id == entity_id,  # type: ignore[attr-defined]
            self.model.business_id == business_id,  # type: ignore[attr-defined]
        )
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def list_for_business(
        self,
        business_id: uuid.UUID,
        *,
        limit: int | None = None,
        offset: int = 0,
        order_by: Any = None,
        filters: Sequence[Any] = (),
    ) -> Sequence[ModelT]:
        statement = self._scoped_select(business_id, filters)
        statement = statement.order_by(order_by if order_by is not None else self._default_order())
        if offset:
            statement = statement.offset(offset)
        if limit is not None:
            statement = statement.limit(limit)
        return (await self.session.execute(statement)).scalars().all()

    async def count_for_business(
        self, business_id: uuid.UUID, *, filters: Sequence[Any] = ()
    ) -> int:
        statement = select(func.count()).select_from(self.model).where(
            self.model.business_id == business_id  # type: ignore[attr-defined]
        )
        for condition in filters:
            statement = statement.where(condition)
        return int((await self.session.execute(statement)).scalar() or 0)

    async def delete_for_business(self, business_id: uuid.UUID, entity_id: uuid.UUID) -> int:
        statement = delete(self.model).where(
            self.model.id == entity_id,  # type: ignore[attr-defined]
            self.model.business_id == business_id,  # type: ignore[attr-defined]
        )
        result = await self.session.execute(statement)
        await self.session.flush()
        return result.rowcount or 0

    def _scoped_select(self, business_id: uuid.UUID, filters: Sequence[Any] = ()) -> Select[Any]:
        statement = select(self.model).where(
            self.model.business_id == business_id  # type: ignore[attr-defined]
        )
        for condition in filters:
            statement = statement.where(condition)
        return statement

    def _default_order(self) -> Any:
        return self.model.created_at.desc()  # type: ignore[attr-defined]
