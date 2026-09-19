"""Autenticacao: cookies, sessao e troca de senha."""

from __future__ import annotations

from httpx import AsyncClient

from app.core.deps import ACCESS_TOKEN_COOKIE, REFRESH_TOKEN_COOKIE
from tests.conftest import register_user


async def test_register_sets_httponly_cookies(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "novo@exemplo.com",
            "password": "senhaSegura123",
            "full_name": "Pessoa Nova",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["user"]["email"] == "novo@exemplo.com"
    assert body["has_business"] is False
    # O token nunca vai no corpo: so em cookie httpOnly.
    assert "access_token" not in response.text

    cookies = response.headers.get_list("set-cookie")
    assert any(ACCESS_TOKEN_COOKIE in cookie and "HttpOnly" in cookie for cookie in cookies)
    assert any(REFRESH_TOKEN_COOKIE in cookie and "HttpOnly" in cookie for cookie in cookies)


async def test_register_rejects_duplicate_email(client: AsyncClient) -> None:
    await register_user(client, email="duplicado@exemplo.com")
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "duplicado@exemplo.com",
            "password": "senhaSegura123",
            "full_name": "Outra Pessoa",
        },
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"


async def test_register_rejects_weak_password(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "fraca@exemplo.com", "password": "12345678", "full_name": "Pessoa"},
    )
    assert response.status_code == 422


async def test_login_with_wrong_password_is_generic(client: AsyncClient) -> None:
    await register_user(client, email="alvo@exemplo.com")
    await client.post("/api/v1/auth/logout")

    wrong_password = await client.post(
        "/api/v1/auth/login",
        json={"email": "alvo@exemplo.com", "password": "senhaErrada123"},
    )
    unknown_email = await client.post(
        "/api/v1/auth/login",
        json={"email": "naoexiste@exemplo.com", "password": "senhaErrada123"},
    )

    assert wrong_password.status_code == unknown_email.status_code == 401
    # Mensagem identica: nao permite descobrir quais e-mails estao cadastrados.
    assert wrong_password.json()["error"]["message"] == unknown_email.json()["error"]["message"]


async def test_me_requires_authentication(client: AsyncClient) -> None:
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


async def test_logout_clears_session(client: AsyncClient) -> None:
    await register_user(client)
    assert (await client.get("/api/v1/auth/me")).status_code == 200

    await client.post("/api/v1/auth/logout")
    assert (await client.get("/api/v1/auth/me")).status_code == 401


async def test_refresh_issues_new_session(client: AsyncClient) -> None:
    await register_user(client)
    response = await client.post("/api/v1/auth/refresh")
    assert response.status_code == 200
    assert (await client.get("/api/v1/auth/me")).status_code == 200


async def test_change_password_forces_new_login(client: AsyncClient) -> None:
    account = await register_user(client, email="trocasenha@exemplo.com")

    response = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": account["password"], "new_password": "outraSenha456"},
    )
    assert response.status_code == 200
    assert (await client.get("/api/v1/auth/me")).status_code == 401

    relogin = await client.post(
        "/api/v1/auth/login",
        json={"email": "trocasenha@exemplo.com", "password": "outraSenha456"},
    )
    assert relogin.status_code == 200


async def test_business_endpoints_require_authentication(client: AsyncClient) -> None:
    for method, path in (
        ("get", "/api/v1/business/current"),
        ("get", "/api/v1/products"),
        ("get", "/api/v1/contents"),
        ("get", "/api/v1/dashboard"),
        ("get", "/api/v1/ai/taxonomy"),
    ):
        response = await getattr(client, method)(path)
        assert response.status_code == 401, f"{path} deveria exigir autenticacao"
