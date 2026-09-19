"""Catalogo do negocio: produtos e servicos.

Produtos e servicos sao tabelas separadas (e nao uma tabela `offering` com um
discriminador) porque possuem atributos realmente distintos e porque o Motor de
Conteudo os usa de formas diferentes na ideacao.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, JSONType, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.asset import Asset
    from app.models.business import Business


class Product(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "products"

    business_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(120))
    price: Mapped[float | None] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), default="BRL", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    #: Atributos livres que enriquecem o contexto da IA (ex.: materiais, tamanhos).
    highlights: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)

    business: Mapped["Business"] = relationship(back_populates="products")
    assets: Mapped[list["Asset"]] = relationship(back_populates="product")


class Service(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "services"

    business_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(120))
    price: Mapped[float | None] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), default="BRL", nullable=False)
    duration_minutes: Mapped[int | None] = mapped_column()
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    #: O que o cliente recebe. Alimenta conteudos de prova social e objecoes.
    deliverables: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)

    business: Mapped["Business"] = relationship(back_populates="services")
    assets: Mapped[list["Asset"]] = relationship(back_populates="service")
