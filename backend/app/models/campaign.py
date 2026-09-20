"""Campanha: geracao multimodal a partir de um produto.

Uma campanha agrega o pedido (destino + saidas) e os artefatos gerados
(copy em `Content`, imagem e video em `Asset`). O usuario entrega o produto;
a plataforma decide o que produzir.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, JSONType, TimestampMixin, UUIDPrimaryKeyMixin, enum_column
from app.models.enums import CampaignDestination, CampaignStatus

if TYPE_CHECKING:
    from app.models.asset import Asset
    from app.models.business import Business
    from app.models.catalog import Product
    from app.models.content import Content
    from app.models.job import Job


class Campaign(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "campaigns"

    business_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("jobs.id", ondelete="SET NULL"),
        index=True,
    )
    model_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("assets.id", ondelete="SET NULL"),
        index=True,
    )

    destination: Mapped[CampaignDestination] = mapped_column(
        enum_column(CampaignDestination), index=True, nullable=False
    )
    outputs_requested: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)
    failed_outputs: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)

    status: Mapped[CampaignStatus] = mapped_column(
        enum_column(CampaignStatus),
        default=CampaignStatus.DRAFT,
        index=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    brief: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict, nullable=False)
    generation_context: Mapped[dict[str, Any]] = mapped_column(
        JSONType, default=dict, nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(Text)

    business: Mapped["Business"] = relationship(back_populates="campaigns")
    product: Mapped["Product"] = relationship()
    model: Mapped["Asset | None"] = relationship(foreign_keys=[model_asset_id])
    job: Mapped["Job | None"] = relationship()
    contents: Mapped[list["Content"]] = relationship(
        back_populates="campaign",
        cascade="all, delete-orphan",
        order_by="Content.created_at",
    )
