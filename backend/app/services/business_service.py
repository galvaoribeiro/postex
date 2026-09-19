"""Regras do negocio e das preferencias editoriais."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.taxonomy import get_taxonomy
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.business import Business, default_content_preferences
from app.repositories.business import BusinessRepository
from app.schemas.business import BusinessCreate, BusinessUpdate, ContentPreferencesSchema

#: A interface atual trabalha com um negocio por conta. O limite existe para
#: nao virar um vetor de abuso enquanto o produto nao tem planos pagos.
MAX_BUSINESSES_PER_USER = 3


class BusinessService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.businesses = BusinessRepository(session)

    async def create(self, user_id: uuid.UUID, data: BusinessCreate) -> Business:
        existing = await self.businesses.list_for_user(user_id)
        if len(existing) >= MAX_BUSINESSES_PER_USER:
            raise ConflictError(
                f"Limite de {MAX_BUSINESSES_PER_USER} negocios por conta atingido."
            )

        preferences = default_content_preferences()
        if data.content_preferences is not None:
            preferences = self._validated_preferences(data.content_preferences)

        return await self.businesses.add(
            Business(
                user_id=user_id,
                name=data.name,
                segment=data.segment,
                description=data.description,
                target_audience=data.target_audience,
                location=data.location,
                brand_voice=data.brand_voice,
                additional_info=data.additional_info,
                instagram_handle=self._normalize_handle(data.instagram_handle),
                website=data.website,
                differentiators=self._clean_list(data.differentiators),
                objectives=self._clean_list(data.objectives),
                content_preferences=preferences,
            )
        )

    async def get(self, user_id: uuid.UUID, business_id: uuid.UUID) -> Business:
        business = await self.businesses.get_for_user(user_id, business_id)
        if business is None:
            # 404 e nao 403: um usuario nao deve conseguir descobrir que um
            # negocio existe apenas porque ele pertence a outra conta.
            raise NotFoundError("Negocio nao encontrado.")
        return business

    async def list_for_user(self, user_id: uuid.UUID) -> Sequence[Business]:
        return await self.businesses.list_for_user(user_id)

    async def get_primary(self, user_id: uuid.UUID) -> Business:
        business = await self.businesses.get_primary_for_user(user_id)
        if business is None:
            raise NotFoundError("Nenhum negocio cadastrado para esta conta.")
        return business

    async def update(self, business: Business, data: BusinessUpdate) -> Business:
        payload = data.model_dump(exclude_unset=True)

        if "content_preferences" in payload:
            preferences_schema = data.content_preferences
            payload["content_preferences"] = (
                self._merge_preferences(
                    business.content_preferences,
                    self._validated_preferences(preferences_schema),
                )
                if preferences_schema is not None
                else default_content_preferences()
            )
        if "instagram_handle" in payload:
            payload["instagram_handle"] = self._normalize_handle(payload["instagram_handle"])
        for key in ("differentiators", "objectives"):
            if key in payload and payload[key] is not None:
                payload[key] = self._clean_list(payload[key])

        for field, value in payload.items():
            setattr(business, field, value)

        await self.session.flush()
        return business

    async def delete(self, business: Business) -> None:
        await self.businesses.delete(business)

    # ------------------------------------------------------------- validacao
    def _validated_preferences(self, preferences: ContentPreferencesSchema) -> dict:
        taxonomy = get_taxonomy()
        valid_keys = set(taxonomy.keys)

        unknown = [
            key
            for key in (*preferences.preferred_categories, *preferences.avoided_categories)
            if key not in valid_keys
        ]
        if unknown:
            raise ValidationError(
                "Pilares de conteudo desconhecidos nas preferencias.",
                details={"unknown": unknown, "available": sorted(valid_keys)},
            )

        overlap = set(preferences.preferred_categories) & set(preferences.avoided_categories)
        if overlap:
            raise ValidationError(
                "Um pilar nao pode estar ao mesmo tempo priorizado e evitado.",
                details={"conflicting": sorted(overlap)},
            )

        data = preferences.model_dump(mode="json")
        data["forbidden_topics"] = self._clean_list(data["forbidden_topics"])
        return data

    @staticmethod
    def _merge_preferences(existing: dict | None, incoming: dict) -> dict:
        """Preserva chaves JSON extras e nao apaga CTA/whatsapp so porque o form omitiu."""
        merged = dict(existing or {})
        merged.update(incoming)
        existing_cta = (existing or {}).get("default_cta")
        existing_whatsapp = (existing or {}).get("whatsapp")
        if not str(incoming.get("default_cta") or "").strip() and existing_cta:
            merged["default_cta"] = existing_cta
        if not str(incoming.get("whatsapp") or "").strip() and existing_whatsapp:
            merged["whatsapp"] = existing_whatsapp
        return merged

    @staticmethod
    def _clean_list(values: list[str] | None) -> list[str]:
        if not values:
            return []
        cleaned = [value.strip() for value in values if value and value.strip()]
        return list(dict.fromkeys(cleaned))

    @staticmethod
    def _normalize_handle(handle: str | None) -> str | None:
        if not handle:
            return None
        return handle.strip().lstrip("@") or None
