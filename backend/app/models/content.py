"""Entidades do nucleo do produto: ideias, conteudos, versoes e vinculos.

`Content` e a entidade central. Os campos comuns a todos os formatos sao
colunas; o que varia por formato (cenas de um Reel, slides de um carrossel,
frames de um story) vive em `Content.payload`, validado por schemas Pydantic
especificos. Isso permite acrescentar formatos sem alterar o schema do banco.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, JSONType, TimestampMixin, UUIDPrimaryKeyMixin, enum_column
from app.models.enums import (
    ContentAssetRole,
    ContentFormat,
    ContentStatus,
    IdeaStatus,
    RegenerationScope,
    VersionAuthor,
)

if TYPE_CHECKING:
    from app.models.asset import Asset
    from app.models.business import Business
    from app.models.campaign import Campaign
    from app.models.catalog import Product


class ContentIdea(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Oportunidade de comunicacao identificada pelo Motor de Conteudo.

    Uma ideia e barata: o usuario pode gerar varias e descartar as que nao
    fizerem sentido. Apenas as escolhidas viram `Content`.
    """

    __tablename__ = "content_ideas"

    business_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    title: Mapped[str] = mapped_column(String(240), nullable=False)
    concept: Mapped[str] = mapped_column(Text, nullable=False)
    objective: Mapped[str] = mapped_column(Text, nullable=False)

    #: Chave da taxonomia editorial (ver `app/ai/config/content_taxonomy.yaml`).
    category: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    suggested_format: Mapped[ContentFormat] = mapped_column(
        enum_column(ContentFormat), nullable=False
    )

    rationale: Mapped[str | None] = mapped_column(Text)
    hook_suggestion: Mapped[str | None] = mapped_column(Text)
    audience_note: Mapped[str | None] = mapped_column(Text)
    relevance_score: Mapped[int] = mapped_column(Integer, default=5, nullable=False)

    referenced_products: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)
    referenced_services: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)
    referenced_asset_ids: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)

    status: Mapped[IdeaStatus] = mapped_column(
        enum_column(IdeaStatus), default=IdeaStatus.AVAILABLE, index=True, nullable=False
    )

    #: Contexto exato que o Motor usou. Serve de auditoria e permite regenerar
    #: mantendo a intencao original mesmo que o negocio mude depois.
    context_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSONType, default=dict, nullable=False
    )
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("jobs.id", ondelete="SET NULL")
    )

    business: Mapped["Business"] = relationship(back_populates="content_ideas")
    contents: Mapped[list["Content"]] = relationship(back_populates="idea")


class Content(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "contents"

    business_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    idea_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("content_ideas.id", ondelete="SET NULL"),
        index=True,
    )
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="SET NULL"),
        index=True,
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("products.id", ondelete="SET NULL"),
        index=True,
    )

    title: Mapped[str] = mapped_column(String(240), nullable=False)
    concept: Mapped[str | None] = mapped_column(Text)
    objective: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(64), index=True)

    format: Mapped[ContentFormat] = mapped_column(
        enum_column(ContentFormat), index=True, nullable=False
    )
    status: Mapped[ContentStatus] = mapped_column(
        enum_column(ContentStatus), default=ContentStatus.DRAFT, index=True, nullable=False
    )

    caption: Mapped[str | None] = mapped_column(Text)
    cta: Mapped[str | None] = mapped_column(Text)
    hashtags: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)

    #: Estrutura especifica do formato (hook + cenas, slides, frames, ...).
    payload: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict, nullable=False)

    planned_date: Mapped[date | None] = mapped_column(Date, index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    current_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    #: Snapshot do contexto e dos parametros usados na geracao.
    generation_context: Mapped[dict[str, Any]] = mapped_column(
        JSONType, default=dict, nullable=False
    )

    business: Mapped["Business"] = relationship(back_populates="contents")
    idea: Mapped["ContentIdea | None"] = relationship(back_populates="contents")
    campaign: Mapped["Campaign | None"] = relationship(back_populates="contents")
    product: Mapped["Product | None"] = relationship()
    versions: Mapped[list["ContentVersion"]] = relationship(
        back_populates="content",
        cascade="all, delete-orphan",
        order_by="ContentVersion.version",
    )
    asset_links: Mapped[list["ContentAsset"]] = relationship(
        back_populates="content",
        cascade="all, delete-orphan",
        order_by="ContentAsset.position",
    )


class ContentVersion(UUIDPrimaryKeyMixin, Base):
    """Snapshot imutavel de um `Content` em um ponto do tempo.

    Guardar o conteudo inteiro (e nao um diff) mantem o historico simples de
    ler e permite restaurar qualquer versao sem reconstruir cadeias de patches.
    """

    __tablename__ = "content_versions"
    __table_args__ = (UniqueConstraint("content_id", "version"),)

    content_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("contents.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False)

    author: Mapped[VersionAuthor] = mapped_column(
        enum_column(VersionAuthor), default=VersionAuthor.USER, nullable=False
    )
    change_reason: Mapped[str | None] = mapped_column(Text)
    ai_instruction: Mapped[str | None] = mapped_column(Text)
    regeneration_scope: Mapped[RegenerationScope | None] = mapped_column(
        enum_column(RegenerationScope)
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    content: Mapped["Content"] = relationship(back_populates="versions")


class ContentAsset(UUIDPrimaryKeyMixin, Base):
    """Vinculo entre um `Content` e um `Asset`, com papel e ordem."""

    __tablename__ = "content_assets"
    __table_args__ = (UniqueConstraint("content_id", "asset_id", "role"),)

    content_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("contents.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("assets.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    role: Mapped[ContentAssetRole] = mapped_column(
        enum_column(ContentAssetRole), default=ContentAssetRole.REFERENCE, nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    content: Mapped["Content"] = relationship(back_populates="asset_links")
    asset: Mapped["Asset"] = relationship(back_populates="content_links")
