"""Fixtures dos testes.

Os testes rodam contra um banco Postgres real (`postex_test`), criado e
destruido pela fixture, porque o schema usa tipos especificos do Postgres
(JSONB). A execucao de IA e forcada para `inline` e o provedor para `mock`, de
modo que o pipeline inteiro e exercitado sem rede e sem custo.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncIterator

os.environ.setdefault("ENVIRONMENT", "test")
os.environ["AI_PROVIDER"] = "mock"
os.environ["IMAGE_PROVIDER"] = "mock"
os.environ["AI_EXECUTION_MODE"] = "inline"
os.environ.setdefault("SECRET_KEY", "chave-de-teste-com-mais-de-32-caracteres-aqui")

_DEFAULT_TEST_DB = "postgresql+asyncpg://postex:postex@localhost:5433/postex_test"
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", _DEFAULT_TEST_DB)

import asyncpg  # noqa: E402
import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.database import SessionFactory, engine  # noqa: E402
from app.models import Base  # noqa: E402


def _admin_dsn() -> tuple[str, str]:
    """DSN do banco administrativo e nome do banco de teste."""
    url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    base, _, database = url.rpartition("/")
    return f"{base}/postgres", database


@pytest.fixture(scope="session", autouse=True)
async def _database() -> AsyncIterator[None]:
    admin_dsn, database = _admin_dsn()

    connection = await asyncpg.connect(admin_dsn)
    try:
        await connection.execute(f'DROP DATABASE IF EXISTS "{database}" WITH (FORCE)')
        await connection.execute(f'CREATE DATABASE "{database}"')
    finally:
        await connection.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    await engine.dispose()
    connection = await asyncpg.connect(admin_dsn)
    try:
        await connection.execute(f'DROP DATABASE IF EXISTS "{database}" WITH (FORCE)')
    finally:
        await connection.close()


@pytest.fixture(autouse=True)
async def _clean_tables() -> AsyncIterator[None]:
    """Cada teste comeca com o banco vazio, sem recriar o schema."""
    yield
    async with engine.begin() as conn:
        tables = ", ".join(f'"{table.name}"' for table in reversed(Base.metadata.sorted_tables))
        await conn.exec_driver_sql(f"TRUNCATE {tables} RESTART IDENTITY CASCADE")


@pytest.fixture
async def session() -> AsyncIterator[object]:
    async with SessionFactory() as db_session:
        yield db_session
        await db_session.rollback()


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """Cliente HTTP com cookies persistentes, como um browser."""
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://testserver", follow_redirects=True
    ) as http_client:
        yield http_client


class ApiUser:
    """Helper de teste: um usuario autenticado com um negocio pronto."""

    def __init__(self, client: AsyncClient, email: str, business_id: str) -> None:
        self.client = client
        self.email = email
        self.business_id = business_id


async def register_user(client: AsyncClient, *, email: str | None = None) -> dict:
    payload = {
        "email": email or f"user-{uuid.uuid4().hex[:10]}@exemplo.com",
        "password": "senhaSegura123",
        "full_name": "Usuario de Teste",
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201, response.text
    return {**response.json(), "password": payload["password"], "email": payload["email"]}


async def create_business(client: AsyncClient, *, name: str = "Atelie Flor de Linho") -> dict:
    response = await client.post(
        "/api/v1/business",
        json={
            "name": name,
            "segment": "moda feminina autoral",
            "description": (
                "Atelie que produz pecas de linho sob medida, com ajuste incluso e "
                "producao propria em oficina."
            ),
            "target_audience": "mulheres de 30 a 55 anos que valorizam pecas duraveis",
            "location": "Curitiba, PR",
            "brand_voice": "acolhedor, direto e sem jargao",
            "differentiators": ["linho certificado", "ajuste sob medida incluso"],
            "objectives": ["aumentar vendas diretas", "atrair clientes da regiao"],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture
async def user_with_business(client: AsyncClient) -> ApiUser:
    account = await register_user(client)
    business = await create_business(client)
    return ApiUser(client, account["email"], business["id"])


@pytest.fixture
async def second_client() -> AsyncIterator[AsyncClient]:
    """Segundo cliente isolado, para testar vazamento entre contas."""
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as http_client:
        yield http_client
