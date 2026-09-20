"""Models SQLAlchemy.

Importar todos aqui garante que o mapeador esteja completo antes de qualquer
uso de relacionamentos por string e que o Alembic veja todas as tabelas.
"""

from app.models.asset import Asset
from app.models.base import Base
from app.models.business import Business
from app.models.campaign import Campaign
from app.models.catalog import Product, Service
from app.models.content import Content, ContentAsset, ContentIdea, ContentVersion
from app.models.job import Job
from app.models.user import User

__all__ = [
    "Asset",
    "Base",
    "Business",
    "Campaign",
    "Content",
    "ContentAsset",
    "ContentIdea",
    "ContentVersion",
    "Job",
    "Product",
    "Service",
    "User",
]
