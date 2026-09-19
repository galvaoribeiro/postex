"""Agregacao dos routers da v1."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import (
    ai,
    assets,
    auth,
    business,
    content_ideas,
    contents,
    dashboard,
    jobs,
    products,
    services,
)

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(business.router)
api_router.include_router(products.router)
api_router.include_router(services.router)
api_router.include_router(assets.router)
api_router.include_router(content_ideas.router)
api_router.include_router(contents.router)
api_router.include_router(jobs.router)
api_router.include_router(ai.router)
api_router.include_router(dashboard.router)
