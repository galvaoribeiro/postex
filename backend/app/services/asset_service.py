"""Biblioteca de assets: upload assinado, metadados e vinculos."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.core.logging import get_logger
from app.models.asset import Asset
from app.models.enums import AssetKind, AssetStatus
from app.repositories.asset import AssetRepository
from app.repositories.catalog import ProductRepository, ServiceRepository
from app.schemas.asset import AssetConfirmRequest, AssetUpdate, AssetUploadRequest
from app.services.storage_service import PresignedUpload, StorageService, get_storage_service

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class AssetUploadTicket:
    asset: Asset
    upload: PresignedUpload


class AssetService:
    def __init__(self, session: AsyncSession, storage: StorageService | None = None) -> None:
        self.session = session
        self.storage = storage or get_storage_service()
        self.assets = AssetRepository(session)
        self.products = ProductRepository(session)
        self.services = ServiceRepository(session)

    # -------------------------------------------------------------- consulta
    async def get(self, business_id: uuid.UUID, asset_id: uuid.UUID) -> Asset:
        asset = await self.assets.get_for_business(business_id, asset_id)
        if asset is None:
            raise NotFoundError("Imagem nao encontrada.")
        return asset

    async def list(
        self,
        business_id: uuid.UUID,
        *,
        kind: AssetKind | None = None,
        status: AssetStatus | None = None,
        product_id: uuid.UUID | None = None,
        service_id: uuid.UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[Asset]:
        return await self.assets.list_filtered(
            business_id,
            kind=kind,
            status=status,
            product_id=product_id,
            service_id=service_id,
            limit=limit,
            offset=offset,
        )

    def signed_url(self, asset: Asset) -> str | None:
        """URL de leitura para a interface. `None` se o upload nao terminou."""
        if asset.status is not AssetStatus.READY:
            return None
        return self.storage.create_presigned_download(asset.storage_key)

    # ---------------------------------------------------------------- upload
    async def create_upload_ticket(
        self, business_id: uuid.UUID, data: AssetUploadRequest
    ) -> AssetUploadTicket:
        """Cria o metadado em `PENDING_UPLOAD` e devolve a URL assinada.

        O arquivo vai do browser direto para o storage: a API nunca recebe o
        binario, o que evita limites de payload e mantem o backend leve.
        """
        mime_type = self.storage.validate_upload(
            filename=data.filename,
            mime_type=data.mime_type,
            size_bytes=data.size_bytes,
        )
        await self._validate_links(business_id, data.product_id, data.service_id)

        storage_key = self.storage.build_key(business_id, data.filename)
        asset = await self.assets.add(
            Asset(
                business_id=business_id,
                product_id=data.product_id,
                service_id=data.service_id,
                kind=data.kind,
                status=AssetStatus.PENDING_UPLOAD,
                storage_key=storage_key,
                original_filename=data.filename[:255],
                mime_type=mime_type,
                size_bytes=data.size_bytes,
                title=data.title,
                alt_text=data.alt_text,
                tags=[tag.strip() for tag in data.tags if tag.strip()],
            )
        )

        upload = self.storage.create_presigned_upload(
            storage_key=storage_key, mime_type=mime_type
        )
        return AssetUploadTicket(asset=asset, upload=upload)

    async def confirm_upload(self, asset: Asset, data: AssetConfirmRequest) -> Asset:
        """Confirma que o objeto chegou ao bucket antes de marcar como pronto."""
        head = await self.storage.head_object(asset.storage_key)
        if head is None:
            asset.status = AssetStatus.FAILED
            await self.session.flush()
            raise ValidationError(
                "O arquivo nao foi encontrado no storage. Refaca o upload.",
                details={"asset_id": str(asset.id)},
            )

        asset.status = AssetStatus.READY
        asset.size_bytes = data.size_bytes or head.get("ContentLength") or asset.size_bytes
        if data.width:
            asset.width = data.width
        if data.height:
            asset.height = data.height
        await self.session.flush()
        return asset

    # ------------------------------------------------------------- metadados
    async def update(self, business_id: uuid.UUID, asset: Asset, data: AssetUpdate) -> Asset:
        payload = data.model_dump(exclude_unset=True)
        await self._validate_links(
            business_id,
            payload.get("product_id", asset.product_id),
            payload.get("service_id", asset.service_id),
        )
        if "tags" in payload and payload["tags"] is not None:
            payload["tags"] = [tag.strip() for tag in payload["tags"] if tag.strip()]
        for field, value in payload.items():
            setattr(asset, field, value)
        await self.session.flush()
        return asset

    async def set_analysis(self, asset: Asset, analysis: dict) -> Asset:
        asset.ai_analysis = analysis
        await self.session.flush()
        return asset

    async def delete(self, asset: Asset) -> None:
        storage_key = asset.storage_key
        await self.assets.delete(asset)
        # O objeto sai depois do metadado: se a remocao no storage falhar,
        # sobra um arquivo orfao (limpavel por lifecycle) e nao um registro
        # apontando para um arquivo que nao existe mais.
        await self.storage.delete_object(storage_key)

    # ------------------------------------------------------------- validacao
    async def _validate_links(
        self,
        business_id: uuid.UUID,
        product_id: uuid.UUID | None,
        service_id: uuid.UUID | None,
    ) -> None:
        if product_id and service_id:
            raise ValidationError("Uma imagem pode ser vinculada a um produto ou a um servico, nao a ambos.")
        if product_id and await self.products.get_for_business(business_id, product_id) is None:
            raise NotFoundError("Produto informado nao encontrado.")
        if service_id and await self.services.get_for_business(business_id, service_id) is None:
            raise NotFoundError("Servico informado nao encontrado.")
