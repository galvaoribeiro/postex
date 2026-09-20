"""Gera o video da campanha e vincula ao Content."""

from __future__ import annotations

import uuid
from dataclasses import replace

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.ai.content_engine import ProductionResult
from app.ai.context_builder import BusinessContext
from app.ai.image.base import ImageReference
from app.ai.video.prompt import build_video_prompt
from app.ai.video.registry import get_video_provider
from app.core.logging import get_logger
from app.models.asset import Asset
from app.models.business import Business
from app.models.content import Content
from app.models.enums import (
    AssetKind,
    AssetStatus,
    CampaignDestination,
    ContentAssetRole,
)
from app.services.asset_service import AssetService
from app.services.content_service import ContentService
from app.services.still_service import load_reference, select_reference_asset

logger = get_logger(__name__)


class VideoService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.assets = AssetService(session)
        self.contents = ContentService(session)

    async def attach_video(
        self,
        *,
        business: Business,
        content: Content,
        context: BusinessContext,
        production: ProductionResult,
        seed: int,
        destination: CampaignDestination,
        product_id: uuid.UUID | None = None,
        replace_existing: bool = False,
    ) -> tuple[Asset, dict[str, object]]:
        content = await self.contents.get(business.id, content.id)
        reference, reference_asset_id = await self._load_focused_reference(
            business.id, product_id
        )
        request = build_video_prompt(
            context=context,
            production=production,
            seed=seed,
            destination=destination,
            has_reference=reference is not None,
        )
        if reference is not None:
            request = replace(request, references=(reference,))
        generated = await get_video_provider().generate(request)

        asset = await self.assets.create_generated(
            business.id,
            data=generated.data,
            mime_type=generated.mime_type,
            filename=f"video-{content.id}.mp4",
            kind=AssetKind.VIDEO_GENERATED,
            title=f"{content.title} · video",
            alt_text=f"Video gerado para {content.title}.",
            width=generated.width,
            height=generated.height,
            duration_seconds=generated.duration_seconds,
            product_id=product_id,
            tags=["ai-generated", "video"],
        )
        if replace_existing:
            await self.contents.replace_role_asset(
                content, asset.id, role=ContentAssetRole.PRIMARY_VIDEO, position=0
            )
        else:
            await self.contents.link_asset(
                content, asset.id, role=ContentAssetRole.PRIMARY_VIDEO, position=0
            )

        if generated.thumbnail_data:
            thumb = await self.assets.create_generated(
                business.id,
                data=generated.thumbnail_data,
                mime_type=generated.thumbnail_mime_type,
                filename=f"thumb-{content.id}.png",
                kind=AssetKind.THUMBNAIL,
                title=f"{content.title} · thumbnail",
                width=generated.width,
                height=generated.height,
                product_id=product_id,
                tags=["ai-generated", "thumbnail"],
            )
            await self.contents.link_asset(
                content, thumb.id, role=ContentAssetRole.THUMBNAIL, position=1
            )

        video_meta = dict(generated.metadata())
        if reference_asset_id is not None:
            video_meta["reference_asset_id"] = str(reference_asset_id)
        meta: dict[str, object] = {"video": video_meta}
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
    ) -> tuple[ImageReference | None, uuid.UUID | None]:
        if product_id is None:
            return None, None
        candidates = await self.assets.list(
            business_id,
            status=AssetStatus.READY,
            product_id=product_id,
        )
        chosen = select_reference_asset(candidates)
        if chosen is None:
            return None, None
        reference = await load_reference(self.assets.storage, chosen)
        if reference is None:
            return None, None
        return reference, chosen.id
