"""Gera o still de capa e vincula ao Content.

Monta o prompt, pede a imagem ao ImageProvider, grava no storage e liga
como COVER. O executor so orquestra o stage.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import replace

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.ai.content_engine import ProductionResult
from app.ai.context_builder import BusinessContext
from app.ai.image.base import ImageReference
from app.ai.image.prompt import build_still_prompt, build_talent_prompt
from app.ai.image.registry import resolve_cover_provider
from app.core.exceptions import StorageError
from app.core.logging import get_logger
from app.models.asset import Asset
from app.models.business import Business
from app.models.content import Content
from app.models.enums import AssetKind, AssetStatus, CampaignDestination, ContentAssetRole
from app.services.asset_service import AssetService
from app.services.content_service import ContentService
from app.services.storage_service import StorageService

logger = get_logger(__name__)


def select_reference_asset(candidates: Sequence[Asset]) -> Asset | None:
    """Prefere PRODUCT_PHOTO; senao a imagem mais recente do item.

    `list_filtered` ja devolve `created_at` desc, entao o primeiro de cada
    grupo e o mais recente.
    """
    images = [
        item
        for item in candidates
        if str(getattr(item, "mime_type", "")).startswith("image/")
    ]
    if not images:
        return None
    photos = [item for item in images if item.kind == AssetKind.PRODUCT_PHOTO]
    return (photos or images)[0]


async def load_reference(storage: StorageService, asset: Asset) -> ImageReference | None:
    try:
        data = await storage.get_object(asset.storage_key)
    except StorageError as exc:
        logger.warning(
            "still_reference_read_failed",
            asset_id=str(getattr(asset, "id", "") or ""),
            key=asset.storage_key,
            error=str(exc),
        )
        return None
    if not data:
        return None
    return ImageReference(
        data=data,
        mime_type=asset.mime_type or "image/png",
        filename=asset.original_filename or "product.png",
    )


class StillService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.assets = AssetService(session)
        self.contents = ContentService(session)

    async def attach_cover(
        self,
        *,
        business: Business,
        content: Content,
        context: BusinessContext,
        production: ProductionResult,
        seed: int,
        product_id: uuid.UUID | None = None,
        service_id: uuid.UUID | None = None,
        destination: CampaignDestination | None = None,
        model_asset_id: uuid.UUID | None = None,
        replace_existing: bool = False,
    ) -> tuple[Asset, dict[str, object]]:
        content = await self.contents.get(business.id, content.id)
        product_ref, product_asset_id = await self._load_focused_reference(
            business.id, product_id, service_id
        )
        model_ref, resolved_model_id = await self._load_model_reference(
            business.id, model_asset_id
        )
        request = build_still_prompt(
            context=context,
            production=production,
            seed=seed,
            has_reference=product_ref is not None,
            has_model=model_ref is not None,
            destination=destination,
        )
        references = tuple(item for item in (model_ref, product_ref) if item is not None)
        if references:
            request = replace(request, references=references)
        generated = await resolve_cover_provider().generate(request)

        asset = await self.assets.create_generated(
            business.id,
            data=generated.data,
            mime_type=generated.mime_type,
            filename=f"capa-{content.id}.png",
            title=f"{content.title} · capa",
            alt_text=f"Still gerado para {content.title}.",
            width=generated.width,
            height=generated.height,
            product_id=product_id,
            service_id=service_id,
            tags=["ai-generated", "cover"],
        )
        if replace_existing:
            await self.contents.replace_role_asset(
                content, asset.id, role=ContentAssetRole.COVER, position=0
            )
        else:
            await self.contents.link_asset(
                content, asset.id, role=ContentAssetRole.COVER, position=0
            )

        image_meta = dict(generated.metadata())
        if product_asset_id is not None:
            image_meta["reference_asset_id"] = str(product_asset_id)
        if resolved_model_id is not None:
            image_meta["model_asset_id"] = str(resolved_model_id)
        meta: dict[str, object] = {"image": image_meta}
        context_blob = dict(content.generation_context or {})
        context_blob.update(meta)
        content.generation_context = context_blob
        flag_modified(content, "generation_context")
        await self.session.flush()
        return asset, meta

    async def _load_focused_reference(
        self,
        business_id: uuid.UUID,
        product_id: uuid.UUID | None,
        service_id: uuid.UUID | None,
    ) -> tuple[ImageReference | None, uuid.UUID | None]:
        if product_id is None and service_id is None:
            return None, None
        candidates = await self.assets.list(
            business_id,
            status=AssetStatus.READY,
            product_id=product_id,
            service_id=service_id,
        )
        chosen = select_reference_asset(candidates)
        if chosen is None:
            return None, None
        reference = await load_reference(self.assets.storage, chosen)
        if reference is None:
            return None, None
        return reference, chosen.id

    async def _load_model_reference(
        self,
        business_id: uuid.UUID,
        model_asset_id: uuid.UUID | None,
    ) -> tuple[ImageReference | None, uuid.UUID | None]:
        if model_asset_id is None:
            return None, None
        asset = await self.assets.get(business_id, model_asset_id)
        if asset.kind is not AssetKind.MODEL_PHOTO or asset.status is not AssetStatus.READY:
            return None, None
        reference = await load_reference(self.assets.storage, asset)
        if reference is None:
            return None, None
        return reference, asset.id

    async def generate_talent(
        self,
        *,
        business: Business,
        seed: int,
    ) -> tuple[Asset, dict[str, object]]:
        request = build_talent_prompt(seed=seed)
        generated = await resolve_cover_provider().generate(request)
        asset = await self.assets.create_generated(
            business.id,
            data=generated.data,
            mime_type=generated.mime_type,
            filename=f"modelo-{uuid.uuid4().hex[:8]}.png",
            kind=AssetKind.MODEL_PHOTO,
            title="Modelo",
            alt_text="Modelo gerada para campanhas.",
            width=generated.width,
            height=generated.height,
            tags=["ai-generated", "model"],
        )
        return asset, {"image": dict(generated.metadata()), "asset_id": str(asset.id)}
