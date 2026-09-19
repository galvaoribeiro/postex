"""Gera o still de capa e vincula ao Content.

Escolhe apresentadora automaticamente, pede a imagem ao ImageProvider, grava
no storage e liga como COVER. O executor so orquestra o stage.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.ai.content_engine import ProductionResult
from app.ai.context_builder import BusinessContext
from app.ai.image.prompt import build_still_prompt, parse_visual_tone
from app.ai.image.registry import resolve_cover_provider
from app.ai.presenters import pick_presenter
from app.models.asset import Asset
from app.models.business import Business
from app.models.content import Content
from app.models.enums import ContentAssetRole, VisualTone
from app.services.asset_service import AssetService
from app.services.content_service import ContentService


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
        visual_tone: VisualTone | str = VisualTone.COMMERCIAL,
    ) -> tuple[Asset, dict[str, object]]:
        presenter = pick_presenter(seed, segment=business.segment)
        content = await self.contents.get(business.id, content.id)
        tone = parse_visual_tone(visual_tone)
        request = build_still_prompt(
            context=context,
            production=production,
            presenter=presenter,
            seed=seed,
            visual_tone=tone,
        )
        generated = await resolve_cover_provider(tone).generate(request)

        asset = await self.assets.create_generated(
            business.id,
            data=generated.data,
            mime_type=generated.mime_type,
            filename=f"capa-{presenter.id}.png",
            title=f"{presenter.display_name} · capa",
            alt_text=(
                f"Still gerado com a apresentadora {presenter.display_name}, "
                f"adulta ficticia, para {content.title}."
            ),
            width=generated.width,
            height=generated.height,
            product_id=product_id,
            service_id=service_id,
            tags=["ai-generated", "cover", presenter.id],
        )
        await self.contents.link_asset(
            content, asset.id, role=ContentAssetRole.COVER, position=0
        )

        meta: dict[str, object] = {
            "presenter": presenter.as_dict(),
            "image": generated.metadata(),
            "visual_tone": tone.value,
        }
        context_blob = dict(content.generation_context or {})
        context_blob.update(meta)
        content.generation_context = context_blob
        flag_modified(content, "generation_context")
        await self.session.flush()
        return asset, meta
