"""Caminho critico ponta a ponta.

Cobre o fluxo que define o produto: contexto do negocio -> ideacao -> selecao ->
producao -> edicao -> regeneracao parcial -> aprovacao -> calendario.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from httpx import AsyncClient

from tests.conftest import ApiUser


async def _seed_catalog(client: AsyncClient) -> None:
    assert (
        await client.post(
            "/api/v1/products",
            json={
                "name": "Vestido Ana",
                "description": "Vestido midi de linho com bolsos embutidos",
                "category": "vestidos",
                "price": 489.0,
                "highlights": ["linho 100%", "forro de algodao"],
            },
        )
    ).status_code == 201
    assert (
        await client.post(
            "/api/v1/services",
            json={
                "name": "Ajuste sob medida",
                "description": "Ajuste de caimento feito na oficina",
                "duration_minutes": 60,
                "deliverables": ["prova inicial", "ajuste final"],
            },
        )
    ).status_code == 201


async def _generate_ideas(client: AsyncClient, count: int = 4) -> list[dict]:
    response = await client.post("/api/v1/content-ideas/generate", json={"count": count})
    assert response.status_code == 202, response.text
    job_id = response.json()["job_id"]

    # Em modo inline o job termina antes da resposta HTTP retornar.
    job = await client.get(f"/api/v1/jobs/{job_id}")
    assert job.status_code == 200
    assert job.json()["status"] == "COMPLETED", job.json()
    assert job.json()["result"]["count"] == count

    ideas = (await client.get("/api/v1/content-ideas")).json()
    assert len(ideas) == count
    return ideas


async def _produce(client: AsyncClient, idea_id: str, **extra) -> dict:
    response = await client.post(
        "/api/v1/contents/from-idea", json={"idea_id": idea_id, **extra}
    )
    assert response.status_code == 202, response.text
    job = (await client.get(f"/api/v1/jobs/{response.json()['job_id']}")).json()
    assert job["status"] == "COMPLETED", job
    content = await client.get(f"/api/v1/contents/{job['result']['content_id']}")
    assert content.status_code == 200
    return content.json()


# ------------------------------------------------------------------ contexto --


async def test_business_completeness_reflects_filled_context(
    user_with_business: ApiUser,
) -> None:
    business = (await user_with_business.client.get("/api/v1/business/current")).json()
    assert business["completeness_score"] >= 80
    assert business["content_preferences"]["posts_per_week"] == 3


async def test_ideation_requires_a_business(client: AsyncClient) -> None:
    from tests.conftest import register_user

    await register_user(client)
    response = await client.post("/api/v1/content-ideas/generate", json={"count": 3})
    assert response.status_code == 404
    assert "negocio" in response.json()["error"]["message"].lower()


# ------------------------------------------------------------------- ideacao --


async def test_ideation_produces_specific_and_varied_ideas(
    user_with_business: ApiUser,
) -> None:
    client = user_with_business.client
    await _seed_catalog(client)

    ideas = await _generate_ideas(client, count=5)

    # Variedade: pilares diferentes na mesma rodada.
    assert len({idea["category"] for idea in ideas}) >= 3
    # Especificidade: as ideias citam o catalogo real, nao placeholders.
    blob = " ".join(f"{idea['title']} {idea['concept']}" for idea in ideas).lower()
    assert "vestido ana" in blob or "ajuste sob medida" in blob
    for forbidden in ("lorem ipsum", "seu produto", "[nome do produto]"):
        assert forbidden not in blob

    for idea in ideas:
        assert idea["status"] == "AVAILABLE"
        assert 1 <= idea["relevance_score"] <= 10
        assert idea["suggested_format"] in {"REEL", "IMAGE_POST", "CAROUSEL", "STORY"}


async def test_ideation_respects_requested_categories_and_format(
    user_with_business: ApiUser,
) -> None:
    client = user_with_business.client
    await _seed_catalog(client)

    response = await client.post(
        "/api/v1/content-ideas/generate",
        json={"count": 2, "categories": ["objecoes", "bastidores"], "format_hint": "REEL"},
    )
    assert response.status_code == 202

    ideas = (await client.get("/api/v1/content-ideas")).json()
    assert {idea["category"] for idea in ideas} == {"objecoes", "bastidores"}
    assert all(idea["suggested_format"] == "REEL" for idea in ideas)


async def test_ideation_rejects_unknown_category(user_with_business: ApiUser) -> None:
    response = await user_with_business.client.post(
        "/api/v1/content-ideas/generate",
        json={"count": 1, "categories": ["categoria-inexistente"]},
    )
    # A validacao acontece dentro do job: ele termina como FAILED com o motivo.
    assert response.status_code == 202
    job = (await user_with_business.client.get(f"/api/v1/jobs/{response.json()['job_id']}")).json()
    assert job["status"] == "FAILED"
    assert "categoria" in job["error_message"].lower()


# ------------------------------------------------- selecao e producao --------


@pytest.mark.parametrize(
    ("content_format", "payload_key"),
    [
        ("REEL", "scenes"),
        ("CAROUSEL", "slides"),
        ("STORY", "frames"),
        ("IMAGE_POST", "headline"),
    ],
)
async def test_production_fills_format_specific_payload(
    user_with_business: ApiUser, content_format: str, payload_key: str
) -> None:
    client = user_with_business.client
    await _seed_catalog(client)
    ideas = await _generate_ideas(client, count=1)

    content = await _produce(client, ideas[0]["id"], format=content_format)

    assert content["format"] == content_format
    assert content["status"] == "DRAFT"
    assert content["caption"]
    assert content["cta"]
    assert len(content["hashtags"]) >= 5
    assert payload_key in content["payload"]
    assert content["current_version"] == 1


async def test_production_marks_idea_as_used(user_with_business: ApiUser) -> None:
    client = user_with_business.client
    await _seed_catalog(client)
    ideas = await _generate_ideas(client, count=2)

    await _produce(client, ideas[0]["id"])

    idea = (await client.get(f"/api/v1/content-ideas/{ideas[0]['id']}")).json()
    assert idea["status"] == "USED"

    # Ideia usada nao pode ser excluida: o conteudo dela existe.
    assert (await client.delete(f"/api/v1/content-ideas/{ideas[0]['id']}")).status_code == 409


async def test_production_records_first_version(user_with_business: ApiUser) -> None:
    client = user_with_business.client
    await _seed_catalog(client)
    ideas = await _generate_ideas(client, count=1)
    content = await _produce(client, ideas[0]["id"], format="REEL")

    versions = (await client.get(f"/api/v1/contents/{content['id']}/versions")).json()
    assert len(versions) == 1
    assert versions[0]["version"] == 1
    assert versions[0]["author"] == "AI"


# --------------------------------------------------------- edicao manual -----


async def test_manual_edit_creates_new_version(user_with_business: ApiUser) -> None:
    client = user_with_business.client
    await _seed_catalog(client)
    ideas = await _generate_ideas(client, count=1)
    content = await _produce(client, ideas[0]["id"], format="REEL")

    updated = await client.patch(
        f"/api/v1/contents/{content['id']}",
        json={"title": "Titulo ajustado a mao", "change_reason": "ajuste de titulo"},
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Titulo ajustado a mao"
    assert updated.json()["current_version"] == 2

    versions = (await client.get(f"/api/v1/contents/{content['id']}/versions")).json()
    assert [version["version"] for version in versions] == [2, 1]
    assert versions[0]["change_reason"] == "ajuste de titulo"


async def test_invalid_payload_edit_is_rejected(user_with_business: ApiUser) -> None:
    client = user_with_business.client
    await _seed_catalog(client)
    ideas = await _generate_ideas(client, count=1)
    content = await _produce(client, ideas[0]["id"], format="CAROUSEL")

    response = await client.patch(
        f"/api/v1/contents/{content['id']}",
        json={"payload": {"cover_title": "so isso"}},
    )
    assert response.status_code == 422


async def test_version_can_be_restored(user_with_business: ApiUser) -> None:
    client = user_with_business.client
    await _seed_catalog(client)
    ideas = await _generate_ideas(client, count=1)
    content = await _produce(client, ideas[0]["id"], format="REEL")
    original_title = content["title"]

    await client.patch(f"/api/v1/contents/{content['id']}", json={"title": "Titulo temporario"})
    restored = await client.post(f"/api/v1/contents/{content['id']}/versions/1/restore")

    assert restored.status_code == 200
    assert restored.json()["title"] == original_title
    assert restored.json()["current_version"] == 3


# ----------------------------------------------------------- regeneracao -----


@pytest.mark.parametrize("scope", ["CAPTION", "HASHTAGS", "CTA", "TITLE", "BODY", "FULL"])
async def test_partial_regeneration_touches_only_its_scope(
    user_with_business: ApiUser, scope: str
) -> None:
    client = user_with_business.client
    await _seed_catalog(client)
    ideas = await _generate_ideas(client, count=1)
    content = await _produce(client, ideas[0]["id"], format="REEL")

    response = await client.post(
        f"/api/v1/contents/{content['id']}/regenerate",
        json={"scope": scope, "instruction": "deixe mais curto e direto"},
    )
    assert response.status_code == 202
    job = (await client.get(f"/api/v1/jobs/{response.json()['job_id']}")).json()
    assert job["status"] == "COMPLETED", job

    updated = (await client.get(f"/api/v1/contents/{content['id']}")).json()
    assert updated["current_version"] == 2

    versions = (await client.get(f"/api/v1/contents/{content['id']}/versions")).json()
    assert versions[0]["regeneration_scope"] == scope
    assert versions[0]["ai_instruction"] == "deixe mais curto e direto"
    assert versions[0]["author"] == "AI"

    if scope in {"CAPTION", "HASHTAGS", "CTA", "TITLE"}:
        # Escopos pontuais nao devem mexer na estrutura do formato.
        assert updated["payload"] == content["payload"]


async def test_hook_regeneration_is_rejected_for_formats_without_hook(
    user_with_business: ApiUser,
) -> None:
    client = user_with_business.client
    await _seed_catalog(client)
    ideas = await _generate_ideas(client, count=1)
    content = await _produce(client, ideas[0]["id"], format="CAROUSEL")

    response = await client.post(
        f"/api/v1/contents/{content['id']}/regenerate", json={"scope": "HOOK"}
    )
    job = (await client.get(f"/api/v1/jobs/{response.json()['job_id']}")).json()
    assert job["status"] == "FAILED"
    assert "gancho" in job["error_message"].lower()


async def test_regeneration_of_approved_content_returns_it_to_draft(
    user_with_business: ApiUser,
) -> None:
    client = user_with_business.client
    await _seed_catalog(client)
    ideas = await _generate_ideas(client, count=1)
    content = await _produce(client, ideas[0]["id"], format="REEL")

    assert (await client.post(f"/api/v1/contents/{content['id']}/approve")).status_code == 200

    await client.post(
        f"/api/v1/contents/{content['id']}/regenerate", json={"scope": "CAPTION"}
    )
    updated = (await client.get(f"/api/v1/contents/{content['id']}")).json()
    # O texto aprovado nao existe mais, entao a aprovacao nao pode persistir.
    assert updated["status"] == "DRAFT"


# ------------------------------------------------------------ transicoes -----


async def test_status_transitions_follow_the_state_machine(
    user_with_business: ApiUser,
) -> None:
    client = user_with_business.client
    await _seed_catalog(client)
    ideas = await _generate_ideas(client, count=1)
    content = await _produce(client, ideas[0]["id"], format="REEL")
    content_id = content["id"]

    assert set(content["allowed_transitions"]) == {"REVIEW", "APPROVED", "REJECTED", "ARCHIVED"}

    # DRAFT -> PUBLISHED e proibido: nao se publica o que nao foi aprovado.
    invalid = await client.post(
        f"/api/v1/contents/{content_id}/status", json={"status": "PUBLISHED"}
    )
    assert invalid.status_code == 409
    assert invalid.json()["error"]["code"] == "invalid_state_transition"

    assert (
        await client.post(f"/api/v1/contents/{content_id}/status", json={"status": "REVIEW"})
    ).status_code == 200
    approved = await client.post(f"/api/v1/contents/{content_id}/approve")
    assert approved.status_code == 200
    assert approved.json()["status"] == "APPROVED"


async def test_scheduling_requires_a_date(user_with_business: ApiUser) -> None:
    client = user_with_business.client
    await _seed_catalog(client)
    ideas = await _generate_ideas(client, count=1)
    content = await _produce(client, ideas[0]["id"], format="REEL")

    await client.post(f"/api/v1/contents/{content['id']}/approve")

    without_date = await client.post(
        f"/api/v1/contents/{content['id']}/status", json={"status": "SCHEDULED"}
    )
    assert without_date.status_code == 422

    target = date.today() + timedelta(days=3)
    scheduled = await client.post(
        f"/api/v1/contents/{content['id']}/schedule",
        json={"planned_date": target.isoformat()},
    )
    assert scheduled.status_code == 200
    assert scheduled.json()["status"] == "SCHEDULED"
    assert scheduled.json()["planned_date"] == target.isoformat()


async def test_duplicate_creates_independent_draft(user_with_business: ApiUser) -> None:
    client = user_with_business.client
    await _seed_catalog(client)
    ideas = await _generate_ideas(client, count=1)
    content = await _produce(client, ideas[0]["id"], format="REEL")
    await client.post(f"/api/v1/contents/{content['id']}/approve")

    copy = await client.post(
        f"/api/v1/contents/{content['id']}/duplicate", json={"title": "Versao para teste A/B"}
    )
    assert copy.status_code == 201
    body = copy.json()
    assert body["id"] != content["id"]
    assert body["status"] == "DRAFT"
    assert body["planned_date"] is None
    assert body["payload"] == content["payload"]


async def test_change_format_resets_payload_and_queues_rewrite(
    user_with_business: ApiUser,
) -> None:
    client = user_with_business.client
    await _seed_catalog(client)
    ideas = await _generate_ideas(client, count=1)
    content = await _produce(client, ideas[0]["id"], format="REEL")

    response = await client.post(
        f"/api/v1/contents/{content['id']}/change-format",
        json={"format": "CAROUSEL", "regenerate": True},
    )
    assert response.status_code == 200
    assert response.json()["job_id"]

    updated = (await client.get(f"/api/v1/contents/{content['id']}")).json()
    assert updated["format"] == "CAROUSEL"
    assert "slides" in updated["payload"]


# -------------------------------------------------- dashboard e calendario ---


async def test_dashboard_next_action_follows_priority(user_with_business: ApiUser) -> None:
    client = user_with_business.client
    await _seed_catalog(client)

    empty = (await client.get("/api/v1/dashboard")).json()
    assert empty["next_action"]["kind"] == "create"
    assert empty["next_action"]["href"] == "/criar"
    assert empty["counters"]["total"] == 0
    assert {item["kind"] for item in empty["quick_create"]} == {"product"}

    await _generate_ideas(client, count=3)
    with_ideas = (await client.get("/api/v1/dashboard")).json()
    # Ideias nao mudam o destino: Inicio so dispara criar ou abre preview.
    assert with_ideas["next_action"]["kind"] == "create"
    assert with_ideas["counters"]["ideas_available"] == 3

    ideas = (await client.get("/api/v1/content-ideas")).json()
    content = await _produce(client, ideas[0]["id"], format="REEL")
    with_draft = (await client.get("/api/v1/dashboard")).json()
    assert with_draft["next_action"]["kind"] == "review"
    assert with_draft["next_action"]["content_id"] == content["id"]
    assert with_draft["next_action"]["cta_label"] == "Abrir preview"

    await client.post(f"/api/v1/contents/{content['id']}/approve")
    await client.post(
        f"/api/v1/contents/{content['id']}/schedule",
        json={"planned_date": date.today().isoformat()},
    )
    after_schedule = (await client.get("/api/v1/dashboard")).json()
    assert after_schedule["next_action"]["kind"] == "create"
    assert len(after_schedule["today"]) == 1


async def test_dashboard_does_not_gate_on_completeness(client: AsyncClient) -> None:
    from tests.conftest import register_user

    await register_user(client)
    await client.post("/api/v1/business", json={"name": "Loja X", "segment": "moda"})
    dashboard = (await client.get("/api/v1/dashboard")).json()
    assert dashboard["business_completeness"] < 60
    assert dashboard["next_action"]["kind"] == "create"
    assert dashboard["quick_create"] == []


async def test_calendar_groups_contents_by_planned_date(user_with_business: ApiUser) -> None:
    client = user_with_business.client
    await _seed_catalog(client)
    ideas = await _generate_ideas(client, count=2)

    planned = date.today().replace(day=15)
    content = await _produce(client, ideas[0]["id"], format="REEL")
    await client.post(
        f"/api/v1/contents/{content['id']}/schedule", json={"planned_date": planned.isoformat()}
    )
    unscheduled = await _produce(client, ideas[1]["id"], format="STORY")

    response = await client.get(
        "/api/v1/calendar", params={"year": planned.year, "month": planned.month}
    )
    assert response.status_code == 200
    body = response.json()

    days_with_content = {day["day"]: day["contents"] for day in body["days"] if day["contents"]}
    assert planned.isoformat() in days_with_content
    assert days_with_content[planned.isoformat()][0]["id"] == content["id"]
    assert unscheduled["id"] in {item["id"] for item in body["unscheduled"]}


async def test_content_listing_filters_by_status_and_format(
    user_with_business: ApiUser,
) -> None:
    client = user_with_business.client
    await _seed_catalog(client)
    ideas = await _generate_ideas(client, count=2)

    reel = await _produce(client, ideas[0]["id"], format="REEL")
    await _produce(client, ideas[1]["id"], format="CAROUSEL")
    await client.post(f"/api/v1/contents/{reel['id']}/approve")

    only_reels = (await client.get("/api/v1/contents", params={"format": "REEL"})).json()
    assert [item["id"] for item in only_reels["items"]] == [reel["id"]]

    approved = (await client.get("/api/v1/contents", params={"status": "APPROVED"})).json()
    assert approved["total"] == 1

    drafts = (await client.get("/api/v1/contents", params={"status": "DRAFT"})).json()
    assert drafts["total"] == 1


# --------------------------------------------------------------- metadados ---


async def test_taxonomy_and_formats_are_exposed(user_with_business: ApiUser) -> None:
    client = user_with_business.client

    taxonomy = (await client.get("/api/v1/ai/taxonomy")).json()
    assert len(taxonomy["categories"]) == 13
    assert {"educativo", "objecoes", "oferta"} <= {c["key"] for c in taxonomy["categories"]}

    formats = (await client.get("/api/v1/ai/formats")).json()
    assert {item["format"] for item in formats} == {"REEL", "IMAGE_POST", "CAROUSEL", "STORY"}
    assert all(item["payload_schema"]["type"] == "object" for item in formats)

    capabilities = (await client.get("/api/v1/ai/capabilities")).json()
    assert capabilities["provider"] == "mock"
    assert capabilities["execution_mode"] == "inline"
