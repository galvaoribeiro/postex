"""Repositorio de negocios.

Toda leitura exige `user_id`: e aqui que a posse do negocio e verificada, uma
unica vez, antes de qualquer outra consulta do request.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select

from app.models.business import Business
from app.repositories.base import BaseRepository


class BusinessRepository(BaseRepository[Business]):
    model = Business

    async def get_for_user(
        self, user_id: uuid.UUID, business_id: uuid.UUID
    ) -> Business | None:
        statement = select(Business).where(
            Business.id == business_id,
            Business.user_id == user_id,
        )
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def list_for_user(self, user_id: uuid.UUID) -> Sequence[Business]:
        statement = (
            select(Business)
            .where(Business.user_id == user_id)
            .order_by(Business.created_at.asc())
        )
        return (await self.session.execute(statement)).scalars().all()

    async def get_unscoped(self, business_id: uuid.UUID) -> Business | None:
        """Busca sem verificar o dono.

        Uso restrito ao executor de jobs, que recebe apenas `business_id` pela
        fila e cuja autorizacao ja foi feita no momento do request HTTP.
        """
        statement = select(Business).where(Business.id == business_id)
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def get_primary_for_user(self, user_id: uuid.UUID) -> Business | None:
        """Negocio principal: o mais antigo do usuario.

        A interface inicial trabalha com um negocio por conta, mas o modelo de
        dados ja suporta varios.
        """
        statement = (
            select(Business)
            .where(Business.user_id == user_id)
            .order_by(Business.created_at.asc())
            .limit(1)
        )
        return (await self.session.execute(statement)).scalar_one_or_none()
