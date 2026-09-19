"""Entradas do Motor de Conteudo, desacopladas dos models do banco.

O motor recebe estruturas simples em vez de instancias SQLAlchemy: isso o torna
testavel isoladamente e impede que ele dispare lazy loads inesperados.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.models.enums import ContentFormat


@dataclass(frozen=True, slots=True)
class IdeaInput:
    """Ideia aprovada pelo usuario, pronta para virar conteudo."""

    title: str
    concept: str
    objective: str
    category: str
    hook_suggestion: str | None = None
    audience_note: str | None = None
    referenced_products: tuple[str, ...] = ()
    referenced_services: tuple[str, ...] = ()

    def render(self) -> str:
        lines = [
            f"Titulo: {self.title}",
            f"Conceito: {self.concept}",
            f"Objetivo: {self.objective}",
            f"Pilar editorial: {self.category}",
        ]
        if self.hook_suggestion:
            lines.append(f"Gancho sugerido na ideacao: {self.hook_suggestion}")
        if self.audience_note:
            lines.append(f"Recorte de publico: {self.audience_note}")
        if self.referenced_products:
            lines.append(f"Produtos citados: {', '.join(self.referenced_products)}")
        if self.referenced_services:
            lines.append(f"Servicos citados: {', '.join(self.referenced_services)}")
        return "\n".join(lines)


@dataclass(frozen=True, slots=True)
class ContentSnapshot:
    """Estado atual de um conteudo, usado como base para regeneracao."""

    title: str
    content_format: ContentFormat
    concept: str | None = None
    objective: str | None = None
    category: str | None = None
    caption: str | None = None
    cta: str | None = None
    hashtags: tuple[str, ...] = ()
    payload: dict[str, Any] = field(default_factory=dict)

    def render(self) -> str:
        import json

        lines = [
            f"Titulo: {self.title}",
            f"Formato: {self.content_format.value}",
        ]
        if self.concept:
            lines.append(f"Conceito: {self.concept}")
        if self.objective:
            lines.append(f"Objetivo: {self.objective}")
        if self.category:
            lines.append(f"Pilar editorial: {self.category}")
        if self.caption:
            lines.append(f"Legenda atual:\n{self.caption}")
        if self.cta:
            lines.append(f"CTA atual: {self.cta}")
        if self.hashtags:
            lines.append(f"Hashtags atuais: {', '.join(self.hashtags)}")
        if self.payload:
            lines.append(
                "Estrutura atual do formato:\n"
                + json.dumps(self.payload, ensure_ascii=False, indent=2)
            )
        return "\n".join(lines)

    def to_idea_input(self) -> IdeaInput:
        return IdeaInput(
            title=self.title,
            concept=self.concept or self.title,
            objective=self.objective or "Manter a presenca do negocio no Instagram.",
            category=self.category or "produto",
        )
