"""Camada de acesso a dados."""

from app.repositories.asset import AssetRepository
from app.repositories.base import BaseRepository, BusinessScopedRepository
from app.repositories.business import BusinessRepository
from app.repositories.campaign import CampaignRepository
from app.repositories.catalog import ProductRepository, ServiceRepository
from app.repositories.content import (
    ContentIdeaRepository,
    ContentRepository,
    ContentVersionRepository,
)
from app.repositories.job import JobRepository
from app.repositories.user import UserRepository

__all__ = [
    "AssetRepository",
    "BaseRepository",
    "BusinessRepository",
    "BusinessScopedRepository",
    "CampaignRepository",
    "ContentIdeaRepository",
    "ContentRepository",
    "ContentVersionRepository",
    "JobRepository",
    "ProductRepository",
    "ServiceRepository",
    "UserRepository",
]

__all__ = [
    "AssetRepository",
    "BaseRepository",
    "BusinessRepository",
    "BusinessScopedRepository",
    "ContentIdeaRepository",
    "ContentRepository",
    "ContentVersionRepository",
    "JobRepository",
    "ProductRepository",
    "ServiceRepository",
    "UserRepository",
]
