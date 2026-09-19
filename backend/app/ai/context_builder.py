"""Etapa 1 do pipeline: transformar o negocio em contexto estruturado.

O `BusinessContext` e a unica fonte de verdade que o Motor de Conteudo enxerga.
Ele e serializavel (`to_snapshot`) para ficar gravado junto de cada ideia e de
cada conteudo, permitindo auditar e regenerar com o mesmo contexto original.
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.types import ImageRef, PromptHints
from app.models.asset import Asset
from app.models.business import Business
from app.models.catalog import Product, Service
from app.models.enums import AssetStatus
from app.repositories.asset import AssetRepository
from app.repositories.catalog import ProductRepository, ServiceRepository
from app.repositories.content import ContentRepository
from app.services.storage_service import StorageService, get_storage_service

MAX_CONTEXT_PRODUCTS = 25
MAX_CONTEXT_SERVICES = 25
MAX_CONTEXT_ASSETS = 12
MAX_RECENT_CONTENTS = 12


@dataclass(frozen=True, slots=True)
class ProductContext:
    name: str
    description: str | None
    category: str | None
    price: float | None
    currency: str
    highlights: tuple[str, ...]
    is_focus: bool = False

    def render(self, *, brief: bool = False) -> str:
        parts = [f"- {self.name}"]
        if self.category:
            parts.append(f"(categoria: {self.category})")
        if self.price is not None:
            parts.append(f"| preco: {self.currency} {self.price:.2f}")
        line = " ".join(parts)
        if brief:
            return line
        if self.description:
            line += f"\n    descricao: {self.description}"
        if self.highlights:
            line += f"\n    destaques: {', '.join(self.highlights)}"
        return line


@dataclass(frozen=True, slots=True)
class ServiceContext:
    name: str
    description: str | None
    category: str | None
    price: float | None
    currency: str
    duration_minutes: int | None
    deliverables: tuple[str, ...]
    is_focus: bool = False

    def render(self, *, brief: bool = False) -> str:
        parts = [f"- {self.name}"]
        if self.category:
            parts.append(f"(categoria: {self.category})")
        if self.price is not None:
            parts.append(f"| preco: {self.currency} {self.price:.2f}")
        if self.duration_minutes:
            parts.append(f"| duracao: {self.duration_minutes} min")
        line = " ".join(parts)
        if brief:
            return line
        if self.description:
            line += f"\n    descricao: {self.description}"
        if self.deliverables:
            line += f"\n    entregaveis: {', '.join(self.deliverables)}"
        return line


@dataclass(frozen=True, slots=True)
class AssetContext:
    id: str
    kind: str
    title: str | None
    alt_text: str | None
    tags: tuple[str, ...]
    linked_to: str | None
    analysis_summary: str | None
    detected_elements: tuple[str, ...]
    storage_key: str
    mime_type: str
    signed_url: str | None = None

    def render(self) -> str:
        label = self.title or self.alt_text or f"imagem {self.kind.lower()}"
        line = f"- [{self.kind}] {label}"
        if self.linked_to:
            line += f" (vinculada a: {self.linked_to})"
        if self.analysis_summary:
            line += f"\n    analise: {self.analysis_summary}"
        if self.detected_elements:
            line += f"\n    elementos: {', '.join(self.detected_elements)}"
        if self.tags:
            line += f"\n    tags: {', '.join(self.tags)}"
        return line


@dataclass(frozen=True, slots=True)
class RecentContentContext:
    title: str
    content_format: str
    category: str | None
    status: str
    created_at: str

    def render(self) -> str:
        category = f" / {self.category}" if self.category else ""
        return f"- \"{self.title}\" ({self.content_format}{category}, {self.status})"


@dataclass(frozen=True, slots=True)
class ContentPreferences:
    preferred_formats: tuple[str, ...] = ()
    preferred_categories: tuple[str, ...] = ()
    avoided_categories: tuple[str, ...] = ()
    posts_per_week: int = 3
    language: str = "pt-BR"
    emoji_usage: str = "moderado"
    forbidden_topics: tuple[str, ...] = ()
    extra_guidelines: str = ""
    default_cta: str = ""
    whatsapp: str = ""

    @classmethod
    def from_dict(cls, raw: dict | None) -> "ContentPreferences":
        raw = raw or {}
        return cls(
            preferred_formats=tuple(raw.get("preferred_formats") or ()),
            preferred_categories=tuple(raw.get("preferred_categories") or ()),
            avoided_categories=tuple(raw.get("avoided_categories") or ()),
            posts_per_week=int(raw.get("posts_per_week") or 3),
            language=str(raw.get("language") or "pt-BR"),
            emoji_usage=str(raw.get("emoji_usage") or "moderado"),
            forbidden_topics=tuple(raw.get("forbidden_topics") or ()),
            extra_guidelines=str(raw.get("extra_guidelines") or ""),
            default_cta=str(raw.get("default_cta") or ""),
            whatsapp=str(raw.get("whatsapp") or ""),
        )

    def render(self) -> str:
        lines = [
            f"- idioma: {self.language}",
            f"- uso de emojis: {self.emoji_usage}",
            f"- frequencia desejada: {self.posts_per_week} publicacoes por semana",
        ]
        if self.preferred_formats:
            lines.append(f"- formatos preferidos: {', '.join(self.preferred_formats)}")
        if self.preferred_categories:
            lines.append(f"- pilares priorizados: {', '.join(self.preferred_categories)}")
        if self.avoided_categories:
            lines.append(f"- pilares a evitar: {', '.join(self.avoided_categories)}")
        if self.forbidden_topics:
            lines.append(f"- assuntos proibidos: {', '.join(self.forbidden_topics)}")
        if self.default_cta:
            lines.append(f"- CTA padrao: {self.default_cta}")
        if self.whatsapp:
            lines.append(f"- WhatsApp: {self.whatsapp}")
        if self.extra_guidelines:
            lines.append(f"- diretrizes adicionais: {self.extra_guidelines}")
        return "\n".join(lines)


@dataclass(frozen=True, slots=True)
class BusinessContext:
    business_id: uuid.UUID
    name: str
    segment: str
    description: str | None
    target_audience: str | None
    location: str | None
    brand_voice: str | None
    additional_info: str | None
    instagram_handle: str | None
    website: str | None
    differentiators: tuple[str, ...]
    objectives: tuple[str, ...]
    completeness_score: int
    preferences: ContentPreferences
    products: tuple[ProductContext, ...] = ()
    services: tuple[ServiceContext, ...] = ()
    assets: tuple[AssetContext, ...] = ()
    recent_contents: tuple[RecentContentContext, ...] = field(default=())

    # ------------------------------------------------------------ renderizacao
    def to_prompt_block(self) -> str:
        """Bloco de contexto injetado nos prompts."""
        sections: list[str] = [
            "## NEGOCIO",
            f"Nome: {self.name}",
            f"Segmento: {self.segment}",
        ]
        if self.location:
            sections.append(f"Localizacao: {self.location}")
        if self.description:
            sections.append(f"Descricao: {self.description}")
        if self.target_audience:
            sections.append(f"Publico-alvo: {self.target_audience}")
        if self.brand_voice:
            sections.append(f"Tom de comunicacao: {self.brand_voice}")
        if self.instagram_handle:
            sections.append(f"Instagram: @{self.instagram_handle.lstrip('@')}")
        if self.differentiators:
            sections.append("Diferenciais:\n" + "\n".join(f"- {d}" for d in self.differentiators))
        if self.objectives:
            sections.append("Objetivos:\n" + "\n".join(f"- {o}" for o in self.objectives))
        if self.additional_info:
            sections.append(f"Informacoes adicionais: {self.additional_info}")

        focused_product = next((item for item in self.products if item.is_focus), None)
        focused_service = next((item for item in self.services if item.is_focus), None)
        if focused_product or focused_service:
            kind = "produto" if focused_product else "servico"
            focused = focused_product or focused_service
            assert focused is not None
            sections.append(
                f"\n## FOCO DESTE CONTEUDO\n"
                f"Este conteudo e sobre o {kind} abaixo. Priorize-o; o restante "
                f"do catalogo e so contexto.\n"
                f"{focused.render()}"
            )

        other_products = tuple(item for item in self.products if not item.is_focus)
        if other_products:
            header = (
                "\n## OUTROS PRODUTOS (contexto secundario)\n"
                if focused_product or focused_service
                else "\n## PRODUTOS CADASTRADOS\n"
            )
            brief = bool(focused_product or focused_service)
            sections.append(
                header + "\n".join(product.render(brief=brief) for product in other_products)
            )
        elif not focused_product:
            sections.append("\n## PRODUTOS CADASTRADOS\n(nenhum produto cadastrado)")

        other_services = tuple(item for item in self.services if not item.is_focus)
        if other_services:
            header = (
                "\n## OUTROS SERVICOS (contexto secundario)\n"
                if focused_product or focused_service
                else "\n## SERVICOS CADASTRADOS\n"
            )
            brief = bool(focused_product or focused_service)
            sections.append(
                header + "\n".join(service.render(brief=brief) for service in other_services)
            )
        elif not focused_service:
            sections.append("\n## SERVICOS CADASTRADOS\n(nenhum servico cadastrado)")

        if self.assets:
            sections.append(
                "\n## IMAGENS DISPONIVEIS\n"
                + "\n".join(asset.render() for asset in self.assets)
                + "\n(as imagens sao contexto adicional e nao obrigam a criacao de conteudo)"
            )

        if self.recent_contents:
            sections.append(
                "\n## CONTEUDOS RECENTES (nao repetir angulo nem titulo)\n"
                + "\n".join(content.render() for content in self.recent_contents)
            )

        sections.append("\n## PREFERENCIAS EDITORIAIS\n" + self.preferences.render())

        return "\n".join(sections)

    def to_snapshot(self) -> dict:
        data = asdict(self)
        data["business_id"] = str(self.business_id)
        # Chaves e URLs assinadas nao devem ser persistidas no snapshot.
        for asset in data.get("assets", []):
            asset.pop("signed_url", None)
        return data

    def to_hints(
        self,
        *,
        categories: tuple[str, ...] = (),
        idea_title: str | None = None,
        idea_concept: str | None = None,
        idea_category: str | None = None,
        content_format: str | None = None,
        instruction: str | None = None,
        image_labels: tuple[str, ...] = (),
        seed: int = 0,
    ) -> PromptHints:
        return PromptHints(
            business_name=self.name,
            segment=self.segment,
            location=self.location,
            target_audience=self.target_audience,
            brand_voice=self.brand_voice,
            product_names=tuple(product.name for product in self.products),
            service_names=tuple(service.name for service in self.services),
            differentiators=self.differentiators,
            objectives=self.objectives,
            categories=categories,
            recent_titles=tuple(content.title for content in self.recent_contents),
            idea_title=idea_title,
            idea_concept=idea_concept,
            idea_category=idea_category,
            content_format=content_format,
            instruction=instruction,
            image_labels=image_labels,
            seed=seed,
            focus_name=next(
                (item.name for item in (*self.products, *self.services) if item.is_focus),
                None,
            ),
        )

    def image_refs(self, *, limit: int = 4) -> tuple[ImageRef, ...]:
        """Imagens com URL assinada, prontas para provedores com visao."""
        refs = [
            ImageRef(
                url=asset.signed_url,
                mime_type=asset.mime_type,
                label=asset.title or asset.alt_text or asset.kind,
            )
            for asset in self.assets
            if asset.signed_url
        ]
        return tuple(refs[:limit])

    @property
    def has_catalog(self) -> bool:
        return bool(self.products or self.services)


class ContextBuilder:
    def __init__(self, session: AsyncSession, storage: StorageService | None = None) -> None:
        self.session = session
        self.storage = storage or get_storage_service()
        self.products = ProductRepository(session)
        self.services = ServiceRepository(session)
        self.assets = AssetRepository(session)
        self.contents = ContentRepository(session)

    async def build(
        self,
        business: Business,
        *,
        include_image_urls: bool = False,
        focus_product_id: uuid.UUID | None = None,
        focus_service_id: uuid.UUID | None = None,
    ) -> BusinessContext:
        """Monta o contexto completo do negocio.

        `include_image_urls=True` acrescenta URLs assinadas das imagens, usado
        somente quando o provedor selecionado suporta visao (gerar URL para
        todo mundo seria desperdicio e exposicao desnecessaria).

        Com `focus_product_id` / `focus_service_id`, o item vai para
        `## FOCO DESTE CONTEUDO` e seus assets sobem ao topo. Sem foco, o
        comportamento permanece o de sempre.
        """
        products = list(await self.products.list_active(business.id))
        services = list(await self.services.list_active(business.id))
        products = await self._with_focus(products, focus_product_id, self.products, business.id)
        services = await self._with_focus(services, focus_service_id, self.services, business.id)
        assets = await self._collect_assets(
            business.id,
            focus_product_id=focus_product_id,
            focus_service_id=focus_service_id,
        )
        recent = await self.contents.list_recent(business.id, limit=MAX_RECENT_CONTENTS)

        product_names = {product.id: product.name for product in products}
        service_names = {service.id: service.name for service in services}

        asset_contexts: list[AssetContext] = []
        for asset in assets:
            analysis = asset.ai_analysis or {}
            linked_to = None
            if asset.product_id and asset.product_id in product_names:
                linked_to = f"produto {product_names[asset.product_id]}"
            elif asset.service_id and asset.service_id in service_names:
                linked_to = f"servico {service_names[asset.service_id]}"

            signed_url = None
            if include_image_urls:
                signed_url = self.storage.create_presigned_download(
                    asset.storage_key, internal=True
                )

            asset_contexts.append(
                AssetContext(
                    id=str(asset.id),
                    kind=asset.kind.value,
                    title=asset.title,
                    alt_text=asset.alt_text,
                    tags=tuple(asset.tags or ()),
                    linked_to=linked_to,
                    analysis_summary=analysis.get("summary"),
                    detected_elements=tuple(analysis.get("detected_elements") or ()),
                    storage_key=asset.storage_key,
                    mime_type=asset.mime_type,
                    signed_url=signed_url,
                )
            )

        return BusinessContext(
            business_id=business.id,
            name=business.name,
            segment=business.segment,
            description=business.description,
            target_audience=business.target_audience,
            location=business.location,
            brand_voice=business.brand_voice,
            additional_info=business.additional_info,
            instagram_handle=business.instagram_handle,
            website=business.website,
            differentiators=tuple(business.differentiators or ()),
            objectives=tuple(business.objectives or ()),
            completeness_score=business.completeness_score,
            preferences=ContentPreferences.from_dict(business.content_preferences),
            products=tuple(
                self._product_context(product, focus_id=focus_product_id)
                for product in products[:MAX_CONTEXT_PRODUCTS]
            ),
            services=tuple(
                self._service_context(service, focus_id=focus_service_id)
                for service in services[:MAX_CONTEXT_SERVICES]
            ),
            assets=tuple(asset_contexts),
            recent_contents=tuple(
                RecentContentContext(
                    title=content.title,
                    content_format=content.format.value,
                    category=content.category,
                    status=content.status.value,
                    created_at=content.created_at.isoformat() if content.created_at else "",
                )
                for content in recent
            ),
        )

    @staticmethod
    async def _with_focus(
        items: list,
        focus_id: uuid.UUID | None,
        repository: ProductRepository | ServiceRepository,
        business_id: uuid.UUID,
    ) -> list:
        """Garante que o item focado venha primeiro, mesmo se estiver inativo."""
        if focus_id is None:
            return items
        focused = next((item for item in items if item.id == focus_id), None)
        if focused is None:
            focused = await repository.get_for_business(business_id, focus_id)
            if focused is None:
                return items
            return [focused, *items]
        return [focused, *[item for item in items if item.id != focus_id]]

    async def _collect_assets(
        self,
        business_id: uuid.UUID,
        *,
        focus_product_id: uuid.UUID | None,
        focus_service_id: uuid.UUID | None,
    ) -> list[Asset]:
        focused: list[Asset] = []
        if focus_product_id:
            focused = list(
                await self.assets.list_filtered(
                    business_id,
                    status=AssetStatus.READY,
                    product_id=focus_product_id,
                    limit=MAX_CONTEXT_ASSETS,
                )
            )
        elif focus_service_id:
            focused = list(
                await self.assets.list_filtered(
                    business_id,
                    status=AssetStatus.READY,
                    service_id=focus_service_id,
                    limit=MAX_CONTEXT_ASSETS,
                )
            )
        focused = [asset for asset in focused if asset.mime_type.startswith("image/")]

        others = list(await self.assets.list_ready_images(business_id, limit=MAX_CONTEXT_ASSETS))
        seen = {asset.id for asset in focused}
        merged = focused + [asset for asset in others if asset.id not in seen]
        return merged[:MAX_CONTEXT_ASSETS]

    @staticmethod
    def _product_context(product: Product, *, focus_id: uuid.UUID | None) -> ProductContext:
        return ProductContext(
            name=product.name,
            description=product.description,
            category=product.category,
            price=float(product.price) if product.price is not None else None,
            currency=product.currency,
            highlights=tuple(product.highlights or ()),
            is_focus=focus_id is not None and product.id == focus_id,
        )

    @staticmethod
    def _service_context(service: Service, *, focus_id: uuid.UUID | None) -> ServiceContext:
        return ServiceContext(
            name=service.name,
            description=service.description,
            category=service.category,
            price=float(service.price) if service.price is not None else None,
            currency=service.currency,
            duration_minutes=service.duration_minutes,
            deliverables=tuple(service.deliverables or ()),
            is_focus=focus_id is not None and service.id == focus_id,
        )
