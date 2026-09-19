"""Regras de `Content`: criacao, edicao, versionamento e transicoes de estado.

Este e o unico lugar onde o ciclo de vida de um conteudo pode mudar. Nenhum
endpoint altera status ou payload diretamente.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.content_engine import ProductionResult, RegenerationResult
from app.ai.inputs import ContentSnapshot
from app.ai.production import get_strategy
from app.core.exceptions import (
    ConflictError,
    InvalidStateTransitionError,
    NotFoundError,
    ValidationError,
)
from app.models.asset import Asset
from app.models.content import Content, ContentAsset, ContentVersion
from app.models.enums import (
    CONTENT_STATUS_TRANSITIONS,
    OPEN_CONTENT_STATUSES,
    ContentAssetRole,
    ContentFormat,
    ContentStatus,
    RegenerationScope,
    VersionAuthor,
)
from app.repositories.asset import AssetRepository
from app.repositories.content import ContentRepository, ContentVersionRepository
from app.schemas.content import ContentManualCreate, ContentUpdate

MAX_HASHTAGS = 30


class ContentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.contents = ContentRepository(session)
        self.versions = ContentVersionRepository(session)
        self.assets = AssetRepository(session)

    # -------------------------------------------------------------- consulta
    async def get(self, business_id: uuid.UUID, content_id: uuid.UUID) -> Content:
        content = await self.contents.get_detailed(business_id, content_id)
        if content is None:
            raise NotFoundError("Conteudo nao encontrado.")
        return content

    async def list(
        self,
        business_id: uuid.UUID,
        *,
        statuses: Sequence[ContentStatus] = (),
        formats: Sequence[ContentFormat] = (),
        category: str | None = None,
        search: str | None = None,
        planned_from: date | None = None,
        planned_to: date | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[Sequence[Content], int]:
        items = await self.contents.list_filtered(
            business_id,
            statuses=statuses,
            formats=formats,
            category=category,
            search=search,
            planned_from=planned_from,
            planned_to=planned_to,
            limit=limit,
            offset=offset,
        )
        total = await self.contents.count_filtered(
            business_id,
            statuses=statuses,
            formats=formats,
            category=category,
            search=search,
        )
        return items, total

    @staticmethod
    def allowed_transitions(content: Content) -> list[ContentStatus]:
        return sorted(
            CONTENT_STATUS_TRANSITIONS.get(content.status, frozenset()),
            key=lambda status: status.value,
        )

    @staticmethod
    def to_engine_snapshot(content: Content) -> ContentSnapshot:
        return ContentSnapshot(
            title=content.title,
            content_format=content.format,
            concept=content.concept,
            objective=content.objective,
            category=content.category,
            caption=content.caption,
            cta=content.cta,
            hashtags=tuple(content.hashtags or ()),
            payload=dict(content.payload or {}),
        )

    # -------------------------------------------------------------- criacao
    async def create_from_production(
        self,
        *,
        business_id: uuid.UUID,
        result: ProductionResult,
        idea_id: uuid.UUID | None = None,
        planned_date: date | None = None,
    ) -> Content:
        fields = result.fields
        content = Content(
            business_id=business_id,
            idea_id=idea_id,
            title=str(fields["title"])[:240],
            concept=fields.get("concept"),
            objective=fields.get("objective"),
            category=fields.get("category"),
            format=result.content_format,
            status=ContentStatus.DRAFT,
            caption=fields.get("caption"),
            cta=fields.get("cta"),
            hashtags=self._clean_hashtags(fields.get("hashtags")),
            payload=fields.get("payload") or {},
            planned_date=planned_date,
            current_version=1,
            generation_context={
                "context": result.context_snapshot,
                "provider": result.provider_metadata,
                "format": result.content_format.value,
            },
        )
        self.session.add(content)
        await self.session.flush()

        await self._record_version(
            content,
            author=VersionAuthor.AI,
            change_reason="Conteudo gerado pelo Motor de Conteudo",
        )
        return content

    async def create_manual(
        self, business_id: uuid.UUID, data: ContentManualCreate
    ) -> Content:
        strategy = get_strategy(data.format)
        content = Content(
            business_id=business_id,
            title=data.title,
            concept=data.concept,
            objective=data.objective,
            category=data.category,
            format=data.format,
            status=ContentStatus.DRAFT,
            caption=data.caption,
            cta=data.cta,
            hashtags=self._clean_hashtags(data.hashtags),
            payload={},
            planned_date=data.planned_date,
            current_version=1,
            generation_context={"source": "manual", "format": strategy.content_format.value},
        )
        self.session.add(content)
        await self.session.flush()
        await self._record_version(
            content, author=VersionAuthor.USER, change_reason="Criado manualmente"
        )
        return content

    async def duplicate(self, content: Content, *, title: str | None = None) -> Content:
        copy = Content(
            business_id=content.business_id,
            idea_id=content.idea_id,
            title=(title or f"{content.title} (copia)")[:240],
            concept=content.concept,
            objective=content.objective,
            category=content.category,
            format=content.format,
            status=ContentStatus.DRAFT,
            caption=content.caption,
            cta=content.cta,
            hashtags=list(content.hashtags or []),
            payload=dict(content.payload or {}),
            planned_date=None,
            current_version=1,
            generation_context={
                **(content.generation_context or {}),
                "duplicated_from": str(content.id),
            },
        )
        self.session.add(copy)
        await self.session.flush()

        for link in content.asset_links:
            self.session.add(
                ContentAsset(
                    content_id=copy.id,
                    asset_id=link.asset_id,
                    role=link.role,
                    position=link.position,
                )
            )

        await self.session.flush()
        await self._record_version(
            copy,
            author=VersionAuthor.USER,
            change_reason=f"Duplicado de {content.title}",
        )
        return copy

    # --------------------------------------------------------------- edicao
    async def update(self, content: Content, data: ContentUpdate) -> Content:
        payload = data.model_dump(exclude_unset=True)
        change_reason = payload.pop("change_reason", None) or "Editado manualmente"

        if "payload" in payload and payload["payload"] is not None:
            strategy = get_strategy(content.format)
            payload["payload"] = strategy.validate_payload(payload["payload"])
        if "hashtags" in payload and payload["hashtags"] is not None:
            payload["hashtags"] = self._clean_hashtags(payload["hashtags"])

        if not payload:
            return content

        for field, value in payload.items():
            setattr(content, field, value)

        await self.session.flush()
        await self._record_version(
            content, author=VersionAuthor.USER, change_reason=change_reason
        )
        return content

    async def apply_regeneration(
        self, content: Content, result: RegenerationResult, *, instruction: str | None
    ) -> Content:
        """Aplica o patch devolvido pela IA e versiona a mudanca."""
        patch = dict(result.patch)

        if "hashtags" in patch:
            patch["hashtags"] = self._clean_hashtags(patch["hashtags"])
        if "payload" in patch:
            strategy = get_strategy(content.format)
            patch["payload"] = strategy.validate_payload(patch["payload"])

        for field, value in patch.items():
            if field == "category" and not value:
                continue
            setattr(content, field, value)

        # Um conteudo aprovado que volta para a mesa de edicao deixa de estar
        # aprovado: o texto que foi aprovado nao existe mais.
        if content.status in {ContentStatus.APPROVED, ContentStatus.SCHEDULED}:
            content.status = ContentStatus.DRAFT

        await self.session.flush()
        await self._record_version(
            content,
            author=VersionAuthor.AI,
            change_reason=f"Regeneracao ({result.scope.value})",
            ai_instruction=instruction,
            scope=result.scope,
        )
        return content

    async def change_format(
        self, content: Content, new_format: ContentFormat, *, reset_payload: bool
    ) -> Content:
        if new_format is content.format:
            raise ConflictError("O conteudo ja esta neste formato.")

        get_strategy(new_format)  # valida que existe estrategia para o formato
        content.format = new_format
        if reset_payload:
            # O payload e especifico do formato: manter a estrutura antiga
            # produziria um conteudo invalido.
            content.payload = {}
        await self.session.flush()
        await self._record_version(
            content,
            author=VersionAuthor.USER,
            change_reason=f"Formato alterado para {new_format.value}",
        )
        return content

    # ------------------------------------------------------------- transicoes
    async def change_status(
        self,
        content: Content,
        new_status: ContentStatus,
        *,
        planned_date: date | None = None,
        reason: str | None = None,
    ) -> Content:
        allowed = CONTENT_STATUS_TRANSITIONS.get(content.status, frozenset())
        if new_status not in allowed:
            raise InvalidStateTransitionError(
                f"Nao e possivel mudar de {content.status.value} para {new_status.value}.",
                details={
                    "current": content.status.value,
                    "allowed": sorted(status.value for status in allowed),
                },
            )

        if new_status is ContentStatus.SCHEDULED:
            target_date = planned_date or content.planned_date
            if target_date is None:
                raise ValidationError("Defina a data planejada antes de agendar o conteudo.")
            content.planned_date = target_date

        if new_status is ContentStatus.PUBLISHED and content.published_at is None:
            content.published_at = datetime.now(timezone.utc)

        previous = content.status
        content.status = new_status
        if planned_date is not None:
            content.planned_date = planned_date

        await self.session.flush()
        await self._record_version(
            content,
            author=VersionAuthor.USER,
            change_reason=reason or f"Status: {previous.value} -> {new_status.value}",
        )
        return content

    async def schedule(self, content: Content, planned_date: date) -> Content:
        content.planned_date = planned_date
        if content.status is ContentStatus.APPROVED:
            content.status = ContentStatus.SCHEDULED
        await self.session.flush()
        await self._record_version(
            content,
            author=VersionAuthor.USER,
            change_reason=f"Data planejada: {planned_date.isoformat()}",
        )
        return content

    async def delete(self, content: Content) -> None:
        await self.contents.delete(content)

    # ---------------------------------------------------------------- assets
    async def link_asset(
        self,
        content: Content,
        asset_id: uuid.UUID,
        *,
        role: ContentAssetRole,
        position: int,
    ) -> Content:
        asset = await self.assets.get_for_business(content.business_id, asset_id)
        if asset is None:
            raise NotFoundError("Imagem nao encontrada.")

        for link in content.asset_links:
            if link.asset_id == asset_id and link.role is role:
                link.position = position
                await self.session.flush()
                return await self.get(content.business_id, content.id)

        self.session.add(
            ContentAsset(
                content_id=content.id, asset_id=asset.id, role=role, position=position
            )
        )
        await self.session.flush()
        return await self.get(content.business_id, content.id)

    async def unlink_asset(self, content: Content, asset_id: uuid.UUID) -> Content:
        removed = False
        for link in list(content.asset_links):
            if link.asset_id == asset_id:
                await self.session.delete(link)
                removed = True
        if not removed:
            raise NotFoundError("Esta imagem nao esta vinculada ao conteudo.")
        await self.session.flush()
        return await self.get(content.business_id, content.id)

    async def linked_assets(self, content: Content) -> list[tuple[Asset, ContentAsset]]:
        return [(link.asset, link) for link in content.asset_links if link.asset is not None]

    # -------------------------------------------------------------- versoes
    async def list_versions(self, content: Content) -> Sequence[ContentVersion]:
        return await self.versions.list_for_content(content.id)

    async def restore_version(self, content: Content, version: int) -> Content:
        target = await self.versions.get_version(content.id, version)
        if target is None:
            raise NotFoundError("Versao nao encontrada.")

        snapshot = target.snapshot
        content.title = snapshot.get("title", content.title)
        content.concept = snapshot.get("concept")
        content.objective = snapshot.get("objective")
        content.category = snapshot.get("category")
        content.caption = snapshot.get("caption")
        content.cta = snapshot.get("cta")
        content.hashtags = self._clean_hashtags(snapshot.get("hashtags"))
        content.payload = snapshot.get("payload") or {}
        if snapshot.get("format"):
            content.format = ContentFormat(snapshot["format"])

        await self.session.flush()
        await self._record_version(
            content,
            author=VersionAuthor.USER,
            change_reason=f"Restaurada a versao {version}",
        )
        return content

    async def _record_version(
        self,
        content: Content,
        *,
        author: VersionAuthor,
        change_reason: str,
        ai_instruction: str | None = None,
        scope: RegenerationScope | None = None,
    ) -> ContentVersion:
        """Grava um snapshot completo do estado atual como nova versao.

        Snapshot integral (em vez de diff) mantem o historico legivel e permite
        restaurar qualquer ponto sem reconstruir cadeias de alteracoes.
        """
        number = await self.versions.next_version_number(content.id)
        version = ContentVersion(
            content_id=content.id,
            version=number,
            snapshot=self._snapshot(content),
            author=author,
            change_reason=change_reason,
            ai_instruction=ai_instruction,
            regeneration_scope=scope,
        )
        self.session.add(version)
        content.current_version = number
        await self.session.flush()
        return version

    @staticmethod
    def _snapshot(content: Content) -> dict[str, Any]:
        return {
            "title": content.title,
            "concept": content.concept,
            "objective": content.objective,
            "category": content.category,
            "format": content.format.value,
            "status": content.status.value,
            "caption": content.caption,
            "cta": content.cta,
            "hashtags": list(content.hashtags or []),
            "payload": dict(content.payload or {}),
            "planned_date": content.planned_date.isoformat() if content.planned_date else None,
        }

    @staticmethod
    def _clean_hashtags(values: Any) -> list[str]:
        if not values:
            return []
        cleaned = [
            str(value).lstrip("#").strip().replace(" ", "")
            for value in values
            if str(value).strip()
        ]
        return list(dict.fromkeys(cleaned))[:MAX_HASHTAGS]

    @staticmethod
    def is_open(content: Content) -> bool:
        return content.status in OPEN_CONTENT_STATUSES
