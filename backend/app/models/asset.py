"""Asset: metadados de um arquivo guardado no object storage.

O binario nunca entra no Postgres. Aqui ficam apenas a chave no bucket, os
metadados tecnicos e o resultado opcional da analise por visao computacional.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, JSONType, TimestampMixin, UUIDPrimaryKeyMixin, enum_column
from app.models.enums import AssetKind, AssetStatus

if TYPE_CHECKING:
    from app.models.business import Business
    from app.models.catalog import Product, Service
    from app.models.content import ContentAsset


class Asset(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "assets"

    business_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("products.id", ondelete="SET NULL"),
        index=True,
    )
    service_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("services.id", ondelete="SET NULL"),
        index=True,
    )

    kind: Mapped[AssetKind] = mapped_column(
        enum_column(AssetKind), default=AssetKind.OTHER, nullable=False
    )
    status: Mapped[AssetStatus] = mapped_column(
        enum_column(AssetStatus), default=AssetStatus.PENDING_UPLOAD, nullable=False
    )

    storage_key: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(120), nullable=False)
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    duration_seconds: Mapped[int | None] = mapped_column(Integer)

    title: Mapped[str | None] = mapped_column(String(180))
    alt_text: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)

    #: Resultado da analise de visao, quando executada. `None` significa apenas
    #: "nao analisado" - a imagem continua utilizavel como contexto.
    ai_analysis: Mapped[dict[str, Any] | None] = mapped_column(JSONType)

    business: Mapped["Business"] = relationship(back_populates="assets")
    product: Mapped["Product | None"] = relationship(back_populates="assets")
    service: Mapped["Service | None"] = relationship(back_populates="assets")
    content_links: Mapped[list["ContentAsset"]] = relationship(
        back_populates="asset", cascade="all, delete-orphan"
    )

    @property
    def is_image(self) -> bool:
        return self.mime_type.startswith("image/")

    @property
    def is_video(self) -> bool:
        return self.mime_type.startswith("video/")
