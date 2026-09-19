"""Negocio do usuario: a raiz de agregacao de todo o conteudo.

Todo dado do produto (produtos, servicos, assets, ideias, conteudos) pertence a
um Business, e todo Business pertence a um User. Esse encadeamento e o que
garante o isolamento entre contas.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, JSONType, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.asset import Asset
    from app.models.catalog import Product, Service
    from app.models.content import Content, ContentIdea
    from app.models.user import User


def default_content_preferences() -> dict[str, Any]:
    """Preferencias editoriais iniciais, editaveis pelo usuario."""
    return {
        "preferred_formats": ["REEL", "CAROUSEL", "IMAGE_POST"],
        "preferred_categories": [],
        "avoided_categories": [],
        "posts_per_week": 3,
        "language": "pt-BR",
        "emoji_usage": "moderado",
        "forbidden_topics": [],
        "extra_guidelines": "",
        "default_cta": "",
        "whatsapp": "",
    }


class Business(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "businesses"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    segment: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    target_audience: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(String(180))
    brand_voice: Mapped[str | None] = mapped_column(Text)
    additional_info: Mapped[str | None] = mapped_column(Text)
    instagram_handle: Mapped[str | None] = mapped_column(String(80))
    website: Mapped[str | None] = mapped_column(String(255))

    differentiators: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)
    objectives: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)
    content_preferences: Mapped[dict[str, Any]] = mapped_column(
        JSONType,
        default=default_content_preferences,
        nullable=False,
    )

    owner: Mapped["User"] = relationship(back_populates="businesses")
    products: Mapped[list["Product"]] = relationship(
        back_populates="business", cascade="all, delete-orphan"
    )
    services: Mapped[list["Service"]] = relationship(
        back_populates="business", cascade="all, delete-orphan"
    )
    assets: Mapped[list["Asset"]] = relationship(
        back_populates="business", cascade="all, delete-orphan"
    )
    content_ideas: Mapped[list["ContentIdea"]] = relationship(
        back_populates="business", cascade="all, delete-orphan"
    )
    contents: Mapped[list["Content"]] = relationship(
        back_populates="business", cascade="all, delete-orphan"
    )

    @property
    def completeness_score(self) -> int:
        """Quao completo esta o contexto do negocio, de 0 a 100.

        O Motor de Conteudo depende desses campos para fugir do generico, por
        isso o dashboard mostra esse indicador como um convite a completar.
        """
        checks = [
            bool(self.name),
            bool(self.segment),
            bool(self.description and len(self.description) >= 40),
            bool(self.target_audience),
            bool(self.location),
            bool(self.brand_voice),
            bool(self.differentiators),
            bool(self.objectives),
        ]
        return round(100 * sum(checks) / len(checks))
