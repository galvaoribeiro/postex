"""Isolamento entre contas.

O requisito e categorico: um usuario jamais acessa dados de outro. Os testes
cobrem leitura, escrita e as operacoes de IA, e verificam que a resposta e 404 -
nunca 403 - para nao confirmar a existencia do recurso alheio.
"""

from __future__ import annotations

from httpx import AsyncClient

from tests.conftest import create_business, register_user


async def _account_with_content(client: AsyncClient, *, email: str) -> dict:
    """Conta completa: negocio, produto, ideia e conteudo."""
    await register_user(client, email=email)
    business = await create_business(client, name=f"Negocio de {email}")

    product = await client.post(
        "/api/v1/products",
        json={"name": "Vestido Ana", "description": "Vestido midi de linho", "price": 489.0},
    )
    assert product.status_code == 201

    generated = await client.post("/api/v1/content-ideas/generate", json={"count": 2})
    assert generated.status_code == 202

    ideas = (await client.get("/api/v1/content-ideas")).json()
    assert ideas, "a ideacao deveria ter gravado ideias"

    created = await client.post(
        "/api/v1/contents/from-idea", json={"idea_id": ideas[0]["id"]}
    )
    assert created.status_code == 202

    contents = (await client.get("/api/v1/contents")).json()["items"]
    assert contents, "a producao deveria ter gravado um conteudo"

    return {
        "business_id": business["id"],
        "product_id": product.json()["id"],
        "idea_id": ideas[0]["id"],
        "content_id": contents[0]["id"],
    }


async def test_other_account_cannot_read_resources(
    client: AsyncClient, second_client: AsyncClient
) -> None:
    owner = await _account_with_content(client, email="dono@exemplo.com")

    await register_user(second_client, email="intruso@exemplo.com")
    await create_business(second_client, name="Negocio do Intruso")

    for path in (
        f"/api/v1/business/{owner['business_id']}",
        f"/api/v1/products/{owner['product_id']}",
        f"/api/v1/content-ideas/{owner['idea_id']}",
        f"/api/v1/contents/{owner['content_id']}",
        f"/api/v1/contents/{owner['content_id']}/versions",
    ):
        response = await second_client.get(path)
        assert response.status_code == 404, f"{path} vazou para outra conta ({response.status_code})"


async def test_other_account_cannot_mutate_resources(
    client: AsyncClient, second_client: AsyncClient
) -> None:
    owner = await _account_with_content(client, email="dono2@exemplo.com")

    await register_user(second_client, email="intruso2@exemplo.com")
    await create_business(second_client, name="Outro Negocio")

    assert (
        await second_client.patch(
            f"/api/v1/contents/{owner['content_id']}", json={"title": "Invadido"}
        )
    ).status_code == 404
    assert (
        await second_client.post(f"/api/v1/contents/{owner['content_id']}/approve")
    ).status_code == 404
    assert (
        await second_client.delete(f"/api/v1/contents/{owner['content_id']}")
    ).status_code == 404
    assert (
        await second_client.post(
            f"/api/v1/contents/{owner['content_id']}/regenerate", json={"scope": "CAPTION"}
        )
    ).status_code == 404
    assert (
        await second_client.patch(
            f"/api/v1/products/{owner['product_id']}", json={"name": "Renomeado"}
        )
    ).status_code == 404

    # O conteudo original permanece intacto.
    original = await client.get(f"/api/v1/contents/{owner['content_id']}")
    assert original.status_code == 200
    assert original.json()["title"] != "Invadido"


async def test_listings_are_scoped_to_the_account(
    client: AsyncClient, second_client: AsyncClient
) -> None:
    await _account_with_content(client, email="dono3@exemplo.com")

    await register_user(second_client, email="intruso3@exemplo.com")
    await create_business(second_client, name="Negocio Vazio")

    assert (await second_client.get("/api/v1/contents")).json()["items"] == []
    assert (await second_client.get("/api/v1/content-ideas")).json() == []
    assert (await second_client.get("/api/v1/products")).json() == []
    assert (await second_client.get("/api/v1/assets")).json() == []
    assert (await second_client.get("/api/v1/jobs")).json() == []


async def test_business_header_of_another_account_is_rejected(
    client: AsyncClient, second_client: AsyncClient
) -> None:
    """Forjar `X-Business-Id` nao da acesso ao negocio de outra conta."""
    owner = await _account_with_content(client, email="dono4@exemplo.com")

    await register_user(second_client, email="intruso4@exemplo.com")
    await create_business(second_client, name="Negocio Proprio")

    response = await second_client.get(
        "/api/v1/contents", headers={"X-Business-Id": owner["business_id"]}
    )
    assert response.status_code == 404

    dashboard = await second_client.get(
        "/api/v1/dashboard", headers={"X-Business-Id": owner["business_id"]}
    )
    assert dashboard.status_code == 404
