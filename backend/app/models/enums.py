"""Enums de dominio.

Mantidos em um unico modulo porque atravessam models, schemas, services e a
camada de IA. Novos formatos de conteudo entram aqui e em
`app/ai/production/` - nenhum outro lugar do codigo precisa mudar.
"""

from __future__ import annotations

from enum import Enum


class ContentFormat(str, Enum):
    REEL = "REEL"
    IMAGE_POST = "IMAGE_POST"
    CAROUSEL = "CAROUSEL"
    STORY = "STORY"


class CampaignDestination(str, Enum):
    INSTAGRAM = "INSTAGRAM"
    TIKTOK = "TIKTOK"
    TIKTOK_SHOP = "TIKTOK_SHOP"


class CampaignOutput(str, Enum):
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"
    COPY = "COPY"


class CampaignStatus(str, Enum):
    DRAFT = "DRAFT"
    GENERATING = "GENERATING"
    REVIEW = "REVIEW"
    APPROVED = "APPROVED"
    FAILED = "FAILED"
    ARCHIVED = "ARCHIVED"


CAMPAIGN_STATUS_TRANSITIONS: dict[CampaignStatus, frozenset[CampaignStatus]] = {
    CampaignStatus.DRAFT: frozenset(
        {CampaignStatus.GENERATING, CampaignStatus.ARCHIVED}
    ),
    CampaignStatus.GENERATING: frozenset(
        {CampaignStatus.REVIEW, CampaignStatus.FAILED, CampaignStatus.ARCHIVED}
    ),
    CampaignStatus.REVIEW: frozenset(
        {
            CampaignStatus.APPROVED,
            CampaignStatus.GENERATING,
            CampaignStatus.ARCHIVED,
        }
    ),
    CampaignStatus.APPROVED: frozenset({CampaignStatus.ARCHIVED, CampaignStatus.REVIEW}),
    CampaignStatus.FAILED: frozenset(
        {CampaignStatus.GENERATING, CampaignStatus.ARCHIVED}
    ),
    CampaignStatus.ARCHIVED: frozenset({CampaignStatus.REVIEW}),
}


class ContentStatus(str, Enum):
    IDEA = "IDEA"
    DRAFT = "DRAFT"
    REVIEW = "REVIEW"
    APPROVED = "APPROVED"
    SCHEDULED = "SCHEDULED"
    PUBLISHED = "PUBLISHED"
    REJECTED = "REJECTED"
    ARCHIVED = "ARCHIVED"


#: Transicoes permitidas. Fonte unica de verdade, consumida por
#: `ContentService.change_status` e exposta na API para a interface habilitar
#: ou desabilitar acoes sem duplicar a regra no frontend.
CONTENT_STATUS_TRANSITIONS: dict[ContentStatus, frozenset[ContentStatus]] = {
    ContentStatus.IDEA: frozenset({ContentStatus.DRAFT, ContentStatus.ARCHIVED}),
    ContentStatus.DRAFT: frozenset(
        {
            ContentStatus.REVIEW,
            ContentStatus.APPROVED,
            ContentStatus.REJECTED,
            ContentStatus.ARCHIVED,
        }
    ),
    ContentStatus.REVIEW: frozenset(
        {
            ContentStatus.DRAFT,
            ContentStatus.APPROVED,
            ContentStatus.REJECTED,
            ContentStatus.ARCHIVED,
        }
    ),
    ContentStatus.APPROVED: frozenset(
        {
            ContentStatus.SCHEDULED,
            ContentStatus.PUBLISHED,
            ContentStatus.DRAFT,
            ContentStatus.ARCHIVED,
        }
    ),
    ContentStatus.SCHEDULED: frozenset(
        {
            ContentStatus.PUBLISHED,
            ContentStatus.APPROVED,
            ContentStatus.ARCHIVED,
        }
    ),
    ContentStatus.PUBLISHED: frozenset({ContentStatus.ARCHIVED}),
    ContentStatus.REJECTED: frozenset({ContentStatus.DRAFT, ContentStatus.ARCHIVED}),
    ContentStatus.ARCHIVED: frozenset({ContentStatus.DRAFT}),
}

#: Status que representam conteudo que ainda demanda acao do usuario.
OPEN_CONTENT_STATUSES: frozenset[ContentStatus] = frozenset(
    {ContentStatus.IDEA, ContentStatus.DRAFT, ContentStatus.REVIEW}
)


class IdeaStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    USED = "USED"
    DISCARDED = "DISCARDED"


class AssetKind(str, Enum):
    PRODUCT_PHOTO = "PRODUCT_PHOTO"
    PLACE_PHOTO = "PLACE_PHOTO"
    TEAM_PHOTO = "TEAM_PHOTO"
    LOGO = "LOGO"
    REFERENCE = "REFERENCE"
    AI_GENERATED = "AI_GENERATED"
    MODEL_PHOTO = "MODEL_PHOTO"
    INTEGRATION_PHOTO = "INTEGRATION_PHOTO"
    VIDEO_GENERATED = "VIDEO_GENERATED"
    THUMBNAIL = "THUMBNAIL"
    OTHER = "OTHER"


class AssetStatus(str, Enum):
    PENDING_UPLOAD = "PENDING_UPLOAD"
    READY = "READY"
    FAILED = "FAILED"


class ContentAssetRole(str, Enum):
    COVER = "COVER"
    SLIDE = "SLIDE"
    SCENE = "SCENE"
    REFERENCE = "REFERENCE"
    PRIMARY_VIDEO = "PRIMARY_VIDEO"
    THUMBNAIL = "THUMBNAIL"


class VersionAuthor(str, Enum):
    USER = "USER"
    AI = "AI"
    SYSTEM = "SYSTEM"


class RegenerationScope(str, Enum):
    """Parte do conteudo que a IA deve reescrever."""

    FULL = "FULL"
    TITLE = "TITLE"
    CONCEPT = "CONCEPT"
    HOOK = "HOOK"
    BODY = "BODY"
    CAPTION = "CAPTION"
    HASHTAGS = "HASHTAGS"
    CTA = "CTA"
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"


class ContentObjective(str, Enum):
    """Objetivo do conteudo na linguagem do usuario.

    A UI expoe so estes tres valores. O mapeamento para pilares da taxonomia
    editorial vive em `app.ai.taxonomy.OBJECTIVE_PILLARS`.
    """

    SELL = "SELL"  # vender
    ATTRACT = "ATTRACT"  # atrair clientes
    BRAND = "BRAND"  # fortalecer a marca


class JobKind(str, Enum):
    IDEATION = "IDEATION"
    CONTENT_PRODUCTION = "CONTENT_PRODUCTION"
    CONTENT_REGENERATION = "CONTENT_REGENERATION"
    CONTENT_CREATION = "CONTENT_CREATION"
    CAMPAIGN_GENERATION = "CAMPAIGN_GENERATION"
    CAMPAIGN_REGENERATION = "CAMPAIGN_REGENERATION"
    TALENT_GENERATION = "TALENT_GENERATION"
    INTEGRATION_GENERATION = "INTEGRATION_GENERATION"
    ASSET_ANALYSIS = "ASSET_ANALYSIS"


class JobStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


TERMINAL_JOB_STATUSES: frozenset[JobStatus] = frozenset(
    {JobStatus.COMPLETED, JobStatus.FAILED}
)
