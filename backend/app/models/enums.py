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


class JobKind(str, Enum):
    IDEATION = "IDEATION"
    CONTENT_PRODUCTION = "CONTENT_PRODUCTION"
    CONTENT_REGENERATION = "CONTENT_REGENERATION"
    ASSET_ANALYSIS = "ASSET_ANALYSIS"


class JobStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


TERMINAL_JOB_STATUSES: frozenset[JobStatus] = frozenset(
    {JobStatus.COMPLETED, JobStatus.FAILED}
)
