"""Schemas de campanhas de produto."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import Field, model_validator

from app.models.enums import CampaignDestination, CampaignOutput, CampaignStatus
from app.schemas.asset import AssetRead
from app.schemas.catalog import ProductRead
from app.schemas.common import APIModel, APIRequest
from app.schemas.content import ContentRead


class CampaignGenerateRequest(APIRequest):
    product_id: uuid.UUID
    model_asset_id: uuid.UUID | None = None
    destination: CampaignDestination
    outputs: list[CampaignOutput] | None = Field(
        default=None,
        description="Vazio aplica a combinacao recomendada do destino.",
    )
    answers: dict[str, str] = Field(default_factory=dict)
    cover_asset_id: uuid.UUID | None = Field(
        default=None,
        description="Still modelo+produto ja aprovado. O video anima este quadro.",
    )

    @model_validator(mode="after")
    def require_model_or_cover(self) -> CampaignGenerateRequest:
        if self.model_asset_id is None and self.cover_asset_id is None:
            raise ValueError("Informe a modelo ou uma imagem ja integrada.")
        return self


class IntegrationGenerateRequest(APIRequest):
    product_id: uuid.UUID
    model_asset_id: uuid.UUID
    destination: CampaignDestination


class CampaignRegenerateRequest(APIRequest):
    output: CampaignOutput
    instruction: str | None = Field(default=None, max_length=600)


class CampaignStatusUpdate(APIRequest):
    status: CampaignStatus
    reason: str | None = Field(default=None, max_length=300)


class CampaignRead(APIModel):
    id: uuid.UUID
    business_id: uuid.UUID
    product_id: uuid.UUID
    model_asset_id: uuid.UUID | None = None
    job_id: uuid.UUID | None
    destination: CampaignDestination
    outputs_requested: list[CampaignOutput]
    failed_outputs: list[CampaignOutput] = Field(default_factory=list)
    status: CampaignStatus
    title: str
    brief: dict[str, Any]
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    product: ProductRead | None = None
    model: AssetRead | None = None
    contents: list[ContentRead] = Field(default_factory=list)
    allowed_transitions: list[CampaignStatus] = Field(default_factory=list)


class CampaignSummary(APIModel):
    id: uuid.UUID
    title: str
    destination: CampaignDestination
    outputs_requested: list[CampaignOutput]
    failed_outputs: list[CampaignOutput] = Field(default_factory=list)
    status: CampaignStatus
    product_id: uuid.UUID
    product_name: str | None = None
    job_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime


class CampaignGenerateAccepted(APIModel):
    job_id: uuid.UUID
    campaign_id: uuid.UUID
    status: str
    kind: str


class DestinationRead(APIModel):
    destination: CampaignDestination
    label: str
    default_outputs: list[CampaignOutput]
    description: str
