"""Campanhas: produto -> destino -> imagem / video / copy."""

from __future__ import annotations

from httpx import AsyncClient

from tests.conftest import ApiUser


async def _wait_job(client: AsyncClient, job_id: str) -> dict:
    job = (await client.get(f"/api/v1/jobs/{job_id}")).json()
    assert job["status"] == "COMPLETED", job
    return job


async def _create_model(client: AsyncClient) -> str:
    accepted = await client.post("/api/v1/talents/generate")
    assert accepted.status_code == 202, accepted.text
    assert accepted.json()["kind"] == "TALENT_GENERATION"
    job = await _wait_job(client, accepted.json()["job_id"])
    asset_id = job["result"]["asset_id"]
    listed = (await client.get("/api/v1/assets", params={"kind": "MODEL_PHOTO"})).json()
    assert any(item["id"] == asset_id and item["kind"] == "MODEL_PHOTO" for item in listed)
    return asset_id


async def test_talent_generation_saves_model_photo(user_with_business: ApiUser) -> None:
    client = user_with_business.client
    first = await _create_model(client)
    second = await _create_model(client)
    assert first != second
    listed = (await client.get("/api/v1/assets", params={"kind": "MODEL_PHOTO"})).json()
    assert {item["id"] for item in listed} == {first, second}


async def test_instagram_campaign_image_and_copy(user_with_business: ApiUser) -> None:
    client = user_with_business.client
    product = await client.post(
        "/api/v1/products",
        json={"name": "Bolsa Lina", "description": "Bolsa de couro caramelo", "price": 389.0},
    )
    assert product.status_code == 201
    product_id = product.json()["id"]

    model_id = await _create_model(client)
    accepted = await client.post(
        "/api/v1/campaigns/generate",
        json={
            "product_id": product_id,
            "model_asset_id": model_id,
            "destination": "INSTAGRAM",
            "outputs": ["IMAGE", "COPY"],
        },
    )
    assert accepted.status_code == 202, accepted.text
    body = accepted.json()
    assert body["kind"] == "CAMPAIGN_GENERATION"
    job = await _wait_job(client, body["job_id"])
    assert job["result"]["campaign_id"] == body["campaign_id"]
    assert job["result"]["image"]["provider"] == "mock"
    assert job["result"]["video"] is None
    assert job["result"]["failed_outputs"] == []

    campaign = (await client.get(f"/api/v1/campaigns/{body['campaign_id']}")).json()
    assert campaign["status"] == "REVIEW"
    assert campaign["destination"] == "INSTAGRAM"
    assert campaign["product_id"] == product_id
    assert campaign["model_asset_id"] == model_id
    assert campaign["model"]["kind"] == "MODEL_PHOTO"
    assert len(campaign["contents"]) == 1
    content = campaign["contents"][0]
    assert content["campaign_id"] == campaign["id"]
    covers = [link for link in content["assets"] if link["role"] == "COVER"]
    assert covers
    videos = [link for link in content["assets"] if link["role"] == "PRIMARY_VIDEO"]
    assert not videos
    blob = f"{content['title']} {content['caption']}".lower()
    assert "bolsa lina" in blob


async def _create_integration(client: AsyncClient, product_id: str, model_id: str) -> str:
    accepted = await client.post(
        "/api/v1/integrations/generate",
        json={
            "product_id": product_id,
            "model_asset_id": model_id,
            "destination": "TIKTOK",
        },
    )
    assert accepted.status_code == 202, accepted.text
    assert accepted.json()["kind"] == "INTEGRATION_GENERATION"
    job = await _wait_job(client, accepted.json()["job_id"])
    asset_id = job["result"]["asset_id"]
    listed = (await client.get("/api/v1/assets", params={"kind": "INTEGRATION_PHOTO"})).json()
    assert any(item["id"] == asset_id and item["kind"] == "INTEGRATION_PHOTO" for item in listed)
    return asset_id


async def test_integration_generation_saves_photo(user_with_business: ApiUser) -> None:
    client = user_with_business.client
    product = await client.post("/api/v1/products", json={"name": "Bolsa Lina"})
    product_id = product.json()["id"]
    model_id = await _create_model(client)
    first = await _create_integration(client, product_id, model_id)
    second = await _create_integration(client, product_id, model_id)
    assert first != second


async def test_tiktok_campaign_reuses_approved_cover(user_with_business: ApiUser) -> None:
    client = user_with_business.client
    product = await client.post(
        "/api/v1/products",
        json={"name": "Tenis Nova", "description": "Tenis urbano branco", "price": 259.0},
    )
    product_id = product.json()["id"]
    model_id = await _create_model(client)
    cover_id = await _create_integration(client, product_id, model_id)
    accepted = await client.post(
        "/api/v1/campaigns/generate",
        json={
            "product_id": product_id,
            "model_asset_id": model_id,
            "destination": "TIKTOK",
            "cover_asset_id": cover_id,
        },
    )
    assert accepted.status_code == 202, accepted.text
    job = await _wait_job(client, accepted.json()["job_id"])
    assert job["result"]["video"]["provider"] == "mock"
    campaign = (await client.get(f"/api/v1/campaigns/{accepted.json()['campaign_id']}")).json()
    content = campaign["contents"][0]
    covers = [link for link in content["assets"] if link["role"] == "COVER"]
    videos = [link for link in content["assets"] if link["role"] == "PRIMARY_VIDEO"]
    assert covers
    assert covers[0]["asset"]["id"] == cover_id
    assert covers[0]["asset"]["kind"] == "INTEGRATION_PHOTO"
    assert videos
    assert job["result"]["image"] is None


async def test_tiktok_campaign_video_and_copy(user_with_business: ApiUser) -> None:
    client = user_with_business.client
    product = await client.post(
        "/api/v1/products",
        json={"name": "Tenis Nova", "description": "Tenis urbano branco", "price": 259.0},
    )
    product_id = product.json()["id"]
    model_id = await _create_model(client)
    accepted = await client.post(
        "/api/v1/campaigns/generate",
        json={"product_id": product_id, "model_asset_id": model_id, "destination": "TIKTOK"},
    )
    assert accepted.status_code == 202, accepted.text
    job = await _wait_job(client, accepted.json()["job_id"])
    assert job["result"]["video"]["provider"] == "mock"
    campaign = (await client.get(f"/api/v1/campaigns/{accepted.json()['campaign_id']}")).json()
    content = campaign["contents"][0]
    videos = [link for link in content["assets"] if link["role"] == "PRIMARY_VIDEO"]
    assert videos
    assert videos[0]["asset"]["kind"] == "VIDEO_GENERATED"
    assert videos[0]["asset"]["mime_type"].startswith("video/")
    assert videos[0]["asset"]["url"]


async def test_tiktok_shop_includes_cta(user_with_business: ApiUser) -> None:
    client = user_with_business.client
    product = await client.post(
        "/api/v1/products",
        json={"name": "Oleo Floral", "description": "Oleo corporal", "price": 79.0},
    )
    product_id = product.json()["id"]
    questions = (
        await client.get(
            "/api/v1/campaigns/generate/questions",
            params={"product_id": product_id, "destination": "TIKTOK_SHOP"},
        )
    ).json()
    cta = next(item for item in questions if item["key"] == "cta")
    assert any(option["value"] == "shop" for option in cta["options"])

    model_id = await _create_model(client)
    accepted = await client.post(
        "/api/v1/campaigns/generate",
        json={
            "product_id": product_id,
            "model_asset_id": model_id,
            "destination": "TIKTOK_SHOP",
            "answers": {"cta": "shop"},
        },
    )
    job = await _wait_job(client, accepted.json()["job_id"])
    campaign = (await client.get(f"/api/v1/campaigns/{accepted.json()['campaign_id']}")).json()
    content = campaign["contents"][0]
    assert content["cta"]
    assert job["result"]["video"]["provider"] == "mock"


async def test_campaign_requires_product(user_with_business: ApiUser) -> None:
    response = await user_with_business.client.post(
        "/api/v1/campaigns/generate",
        json={"destination": "INSTAGRAM"},
    )
    assert response.status_code == 422


async def test_campaign_requires_model(user_with_business: ApiUser) -> None:
    client = user_with_business.client
    product = await client.post("/api/v1/products", json={"name": "Bolsa"})
    response = await client.post(
        "/api/v1/campaigns/generate",
        json={"product_id": product.json()["id"], "destination": "INSTAGRAM"},
    )
    assert response.status_code == 422


async def test_regenerate_image_output(user_with_business: ApiUser) -> None:
    client = user_with_business.client
    product = await client.post(
        "/api/v1/products",
        json={"name": "Cinto Ocre", "price": 120.0, "description": "Cinto de couro"},
    )
    product_id = product.json()["id"]
    model_id = await _create_model(client)
    created = await client.post(
        "/api/v1/campaigns/generate",
        json={
            "product_id": product_id,
            "model_asset_id": model_id,
            "destination": "INSTAGRAM",
            "outputs": ["IMAGE", "COPY"],
        },
    )
    await _wait_job(client, created.json()["job_id"])
    campaign_id = created.json()["campaign_id"]
    before = (await client.get(f"/api/v1/campaigns/{campaign_id}")).json()
    old_cover = next(
        link["asset"]["id"] for link in before["contents"][0]["assets"] if link["role"] == "COVER"
    )

    regen = await client.post(
        f"/api/v1/campaigns/{campaign_id}/regenerate",
        json={"output": "IMAGE"},
    )
    assert regen.status_code == 202, regen.text
    job = await _wait_job(client, regen.json()["job_id"])
    assert job["kind"] == "CAMPAIGN_REGENERATION"
    assert job["result"]["output"] == "IMAGE"

    after = (await client.get(f"/api/v1/campaigns/{campaign_id}")).json()
    new_cover = next(
        link["asset"]["id"] for link in after["contents"][0]["assets"] if link["role"] == "COVER"
    )
    assert new_cover != old_cover
    assert after["status"] == "REVIEW"


async def test_campaign_list_filters_destination(user_with_business: ApiUser) -> None:
    client = user_with_business.client
    product = await client.post(
        "/api/v1/products",
        json={"name": "Saia Lima", "price": 210.0, "description": "Saia midi"},
    )
    product_id = product.json()["id"]
    model_id = await _create_model(client)
    created = await client.post(
        "/api/v1/campaigns/generate",
        json={
            "product_id": product_id,
            "model_asset_id": model_id,
            "destination": "INSTAGRAM",
            "outputs": ["COPY"],
        },
    )
    await _wait_job(client, created.json()["job_id"])
    listed = (
        await client.get("/api/v1/campaigns", params={"destination": "INSTAGRAM"})
    ).json()
    assert listed["total"] >= 1
    assert listed["items"][0]["destination"] == "INSTAGRAM"
