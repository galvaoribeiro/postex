"""Criacao de conteudo em um passo.

Cobre o job unico CONTENT_CREATION, as perguntas determinísticas e as regras
de item obrigatorio (SELL) vs opcional (BRAND/ATTRACT).
"""

from __future__ import annotations

from httpx import AsyncClient

from tests.conftest import ApiUser


async def _generate(client: AsyncClient, **payload) -> dict:
    response = await client.post("/api/v1/contents/generate", json=payload)
    assert response.status_code == 202, response.text
    body = response.json()
    assert body["kind"] == "CONTENT_CREATION"
    job = (await client.get(f"/api/v1/jobs/{body['job_id']}")).json()
    assert job["status"] == "COMPLETED", job
    return job


async def test_content_creation_job_produces_draft(
    user_with_business: ApiUser,
) -> None:
    client = user_with_business.client
    product = await client.post(
        "/api/v1/products",
        json={"name": "Vestido Ana", "description": "Vestido midi de linho", "price": 489.0},
    )
    assert product.status_code == 201
    product_id = product.json()["id"]

    job = await _generate(client, product_id=product_id, objective="SELL")

    assert job["kind"] == "CONTENT_CREATION"
    assert job["stage"] == "finalizando"
    assert job["progress"] == 100
    result = job["result"]
    assert result["content_id"]
    assert result["idea_id"]
    assert result["stages"] == ["ideia", "roteiro", "imagem", "finalizando"]
    assert result["image"]["provider"] == "mock"

    content = (await client.get(f"/api/v1/contents/{result['content_id']}")).json()
    assert content["status"] == "DRAFT"
    assert content["idea_id"] == result["idea_id"]
    covers = [link for link in content["assets"] if link["role"] == "COVER"]
    assert covers, "o still gerado deveria virar capa"
    assert covers[0]["asset"]["kind"] == "AI_GENERATED"
    assert covers[0]["asset"]["url"]
    blob = f"{content['title']} {content['concept']}".lower()
    assert "vestido ana" in blob

    idea = (await client.get(f"/api/v1/content-ideas/{result['idea_id']}")).json()
    assert idea["status"] == "USED"


async def test_sell_without_item_is_rejected(user_with_business: ApiUser) -> None:
    response = await user_with_business.client.post(
        "/api/v1/contents/generate", json={"objective": "SELL"}
    )
    assert response.status_code == 422


async def test_brand_without_item_is_accepted(user_with_business: ApiUser) -> None:
    job = await _generate(user_with_business.client, objective="BRAND")
    assert job["status"] == "COMPLETED"
    content = (
        await user_with_business.client.get(f"/api/v1/contents/{job['result']['content_id']}")
    ).json()
    assert content["status"] == "DRAFT"


async def test_attract_without_item_is_accepted(user_with_business: ApiUser) -> None:
    job = await _generate(user_with_business.client, objective="ATTRACT")
    assert job["result"]["content_id"]


async def test_questions_ask_price_when_missing(user_with_business: ApiUser) -> None:
    client = user_with_business.client
    product = await client.post("/api/v1/products", json={"name": "Saia lima"})
    assert product.status_code == 201
    product_id = product.json()["id"]

    questions = (
        await client.get(
            "/api/v1/contents/generate/questions",
            params={"objective": "SELL", "product_id": product_id},
        )
    ).json()
    keys = [item["key"] for item in questions]
    assert "price" in keys
    assert len(questions) <= 3


async def test_questions_omit_price_when_present(user_with_business: ApiUser) -> None:
    client = user_with_business.client
    product = await client.post(
        "/api/v1/products",
        json={
            "name": "Saia lima",
            "price": 210.0,
            "description": "Saia midi de linho com bolso",
            "highlights": ["linho 100%"],
        },
    )
    product_id = product.json()["id"]
    await client.patch(
        "/api/v1/business/current",
        json={
            "content_preferences": {
                "preferred_formats": ["REEL"],
                "posts_per_week": 3,
                "language": "pt-BR",
                "emoji_usage": "moderado",
                "default_cta": "whatsapp",
            }
        },
    )

    questions = (
        await client.get(
            "/api/v1/contents/generate/questions",
            params={"objective": "SELL", "product_id": product_id},
        )
    ).json()
    keys = [item["key"] for item in questions]
    assert "price" not in keys
    assert "cta" not in keys
    assert "benefit" not in keys


async def test_price_answer_persists_on_product(user_with_business: ApiUser) -> None:
    client = user_with_business.client
    product = await client.post("/api/v1/products", json={"name": "Cinto ocre"})
    product_id = product.json()["id"]

    job = await _generate(
        client,
        product_id=product_id,
        objective="SELL",
        answers={"price": "199.90"},
    )
    assert job["status"] == "COMPLETED"

    updated = (await client.get(f"/api/v1/products/{product_id}")).json()
    assert float(updated["price"]) == 199.9


async def test_cta_answer_persists_on_preferences(user_with_business: ApiUser) -> None:
    client = user_with_business.client
    job = await _generate(
        client, objective="BRAND", answers={"cta": "whatsapp"}
    )
    assert job["status"] == "COMPLETED"

    business = (await client.get("/api/v1/business/current")).json()
    assert business["content_preferences"]["default_cta"] == "whatsapp"

    questions = (
        await client.get("/api/v1/contents/generate/questions", params={"objective": "BRAND"})
    ).json()
    assert questions == []


async def test_skipped_price_does_not_persist(user_with_business: ApiUser) -> None:
    client = user_with_business.client
    product = await client.post("/api/v1/products", json={"name": "Bolsa cru"})
    product_id = product.json()["id"]

    await _generate(
        client,
        product_id=product_id,
        objective="SELL",
        answers={"price": "skip"},
    )
    updated = (await client.get(f"/api/v1/products/{product_id}")).json()
    assert updated["price"] is None
