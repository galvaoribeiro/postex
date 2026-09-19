"""Base declarativa, mixins e tipos compartilhados pelos models."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, TypeVar

from sqlalchemy import JSON, DateTime, Enum as SAEnum, MetaData, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# JSONB no Postgres, JSON generico em outros dialetos (facilita testes locais).
JSONType = JSONB().with_variant(JSON(), "sqlite")

# Nomes deterministicos para constraints e indices: sem isso o Alembic gera
# migracoes com nomes aleatorios que nao podem ser revertidos com seguranca.
NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

EnumT = TypeVar("EnumT", bound=Enum)


def enum_column(enum_cls: type[EnumT]) -> SAEnum:
    """Coluna de enum persistida como VARCHAR, sem CHECK constraint.

    A validacao acontece na borda (schemas Pydantic) e nos services. Manter o
    banco livre de CHECK permite adicionar novos formatos de conteudo e novos
    status sem uma migracao so para relaxar a constraint.
    """
    return SAEnum(
        enum_cls,
        native_enum=False,
        create_constraint=False,
        length=48,
        values_callable=lambda cls: [member.value for member in cls],
    )


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)

    def __repr__(self) -> str:  # pragma: no cover - conveniencia de debug
        identifier = getattr(self, "id", None)
        return f"<{type(self).__name__} id={identifier}>"


class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    #: `onupdate` roda em Python (nao no servidor) de proposito: um valor
    #: calculado pelo servidor deixa a coluna "expirada" apos o UPDATE, e lê-la
    #: de volta exigiria um round-trip ao banco fora do contexto assincrono no
    #: momento em que o Pydantic serializa a resposta (`MissingGreenlet`).
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=_utcnow,
        nullable=False,
    )


def empty_dict() -> dict[str, Any]:
    return {}


def empty_list() -> list[Any]:
    return []
