"""Perguntas determinísticas do fluxo Criar.

Sem custo de IA: as regras olham o cadastro e devolvem no maximo tres perguntas
que realmente mudam o conteudo gerado. Fatos duraveis (preco, beneficio, CTA)
vao para o catalogo / preferencias; fatos so deste post entram no `instruction`.
"""

from __future__ import annotations

import uuid
from decimal import Decimal, InvalidOperation

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationError
from app.models.business import Business
from app.models.catalog import Product, Service
from app.models.enums import AssetStatus, ContentObjective
from app.repositories.asset import AssetRepository
from app.schemas.content import CreationQuestion, QuestionOption
from app.services.catalog_service import ProductService, ServiceCatalogService

MAX_CREATION_QUESTIONS = 3
SKIP_VALUES = frozenset({"", "skip", "pular"})
HIDE_PRICE = "hide"

OBJECTIVE_INSTRUCTIONS: dict[ContentObjective, str] = {
    ContentObjective.SELL: "Objetivo deste conteudo: vender o item em foco.",
    ContentObjective.ATTRACT: "Objetivo deste conteudo: atrair novos clientes.",
    ContentObjective.BRAND: "Objetivo deste conteudo: fortalecer a marca.",
}

CTA_LABELS: dict[str, str] = {
    "whatsapp": "WhatsApp",
    "website": "o site",
    "store": "a loja",
    "comment": "os comentarios",
    "direct": "o direct do Instagram",
}

CTA_OPTIONS = [
    QuestionOption(value="whatsapp", label="WhatsApp"),
    QuestionOption(value="website", label="Site"),
    QuestionOption(value="store", label="Loja fisica"),
    QuestionOption(value="comment", label="Comentar no post"),
    QuestionOption(value="direct", label="Direct do Instagram"),
]


def _is_skipped(value: str | None) -> bool:
    return value is None or value.strip().lower() in SKIP_VALUES


def _has_default_cta(business: Business) -> bool:
    prefs = business.content_preferences or {}
    return bool(str(prefs.get("default_cta") or "").strip())


async def resolve_creation_item(
    session: AsyncSession,
    business_id: uuid.UUID,
    *,
    objective: ContentObjective,
    product_id: uuid.UUID | None,
    service_id: uuid.UUID | None,
) -> tuple[Product | None, Service | None]:
    """Valida posse (404) e regras estruturais (422) do item focado."""
    if product_id and service_id:
        raise ValidationError("Informe produto ou servico, nao os dois.")
    if objective is ContentObjective.SELL and not product_id and not service_id:
        raise ValidationError("Para vender, escolha um produto ou servico.")

    product = None
    service = None
    if product_id:
        product = await ProductService(session).get(business_id, product_id)
    if service_id:
        service = await ServiceCatalogService(session).get(business_id, service_id)
    return product, service


async def has_linked_image(
    session: AsyncSession,
    business_id: uuid.UUID,
    *,
    product_id: uuid.UUID | None = None,
    service_id: uuid.UUID | None = None,
) -> bool:
    if not product_id and not service_id:
        return False
    assets = await AssetRepository(session).list_filtered(
        business_id,
        status=AssetStatus.READY,
        product_id=product_id,
        service_id=service_id,
        limit=8,
    )
    return any(asset.mime_type.startswith("image/") for asset in assets)


async def list_creation_questions(
    session: AsyncSession,
    business: Business,
    *,
    objective: ContentObjective,
    product: Product | None,
    service: Service | None,
) -> list[CreationQuestion]:
    item = product or service
    questions: list[CreationQuestion] = []

    if (
        objective is ContentObjective.SELL
        and item is not None
        and not await has_linked_image(
            session,
            business.id,
            product_id=product.id if product else None,
            service_id=service.id if service else None,
        )
    ):
        label = "produto" if product is not None else "servico"
        questions.append(
            CreationQuestion(
                key="product_photo",
                question=f"Tem uma foto deste {label}?",
                kind="choice",
                options=[
                    QuestionOption(value="upload_now", label="Vou enviar agora"),
                    QuestionOption(value="skip", label="Nao tenho"),
                ],
                optional=True,
                persist_to=None,
            )
        )

    priced = product if product is not None else service
    if objective is ContentObjective.SELL and priced is not None and priced.price is None:
        persist_to = "product.price" if product is not None else "service.price"
        questions.append(
            CreationQuestion(
                key="price",
                question="Qual o preco?",
                kind="money",
                options=[QuestionOption(value=HIDE_PRICE, label="Nao mostrar preco")],
                optional=True,
                persist_to=persist_to,
            )
        )

    if not _has_default_cta(business):
        questions.append(
            CreationQuestion(
                key="cta",
                question="Onde a pessoa deve ir?",
                kind="choice",
                options=CTA_OPTIONS,
                optional=True,
                persist_to="business.content_preferences.default_cta",
            )
        )

    if (
        objective is ContentObjective.SELL
        and product is not None
        and not (product.description and product.description.strip())
        and not (product.highlights or [])
    ):
        questions.append(
            CreationQuestion(
                key="benefit",
                question="O que a cliente ganha com isso, em uma frase?",
                kind="text",
                options=[],
                optional=True,
                persist_to="product.highlights",
            )
        )

    if (
        objective is ContentObjective.ATTRACT
        and service is not None
        and service.duration_minutes is None
    ):
        questions.append(
            CreationQuestion(
                key="duration",
                question="Quanto tempo leva?",
                kind="text",
                options=[],
                optional=True,
                persist_to="service.duration_minutes",
            )
        )

    return questions[:MAX_CREATION_QUESTIONS]


async def persist_creation_answers(
    session: AsyncSession,
    business: Business,
    *,
    product: Product | None,
    service: Service | None,
    objective: ContentObjective,
    answers: dict[str, str],
) -> str:
    """Grava fatos duraveis e devolve o instruction deste post.

    Resposta pulada nao vira instrucao; o motor nao deve afirmar preco, foto
    nem depoimento que o usuario nao confirmou.
    """
    cleaned = {key: value.strip() for key, value in answers.items() if value is not None}
    target = product if product is not None else service

    price_value = cleaned.get("price")
    if not _is_skipped(price_value) and price_value != HIDE_PRICE and target is not None:
        target.price = float(_parse_money(price_value))

    benefit = cleaned.get("benefit")
    if not _is_skipped(benefit) and product is not None:
        phrase = benefit.strip()  # type: ignore[union-attr]
        highlights = list(product.highlights or [])
        if phrase not in highlights:
            highlights.append(phrase)
        product.highlights = highlights
        if not (product.description and product.description.strip()):
            product.description = phrase

    duration = cleaned.get("duration")
    if not _is_skipped(duration) and service is not None:
        service.duration_minutes = _parse_minutes(duration)

    cta = cleaned.get("cta")
    if not _is_skipped(cta):
        prefs = dict(business.content_preferences or {})
        prefs["default_cta"] = cta.strip()  # type: ignore[union-attr]
        business.content_preferences = prefs

    await session.flush()
    return _instruction_from_answers(objective, cleaned)


def _instruction_from_answers(objective: ContentObjective, answers: dict[str, str]) -> str:
    parts: list[str] = [OBJECTIVE_INSTRUCTIONS[objective]]

    price = answers.get("price")
    if price == HIDE_PRICE:
        parts.append("Nao mostre nem cite o preco neste conteudo.")
    elif not _is_skipped(price):
        parts.append(f"O preco e {price}.")

    cta = answers.get("cta")
    if not _is_skipped(cta):
        label = CTA_LABELS.get(cta.strip().lower(), cta)  # type: ignore[union-attr]
        parts.append(f"O chamado para acao deve direcionar para {label}.")

    benefit = answers.get("benefit")
    if not _is_skipped(benefit):
        parts.append(f"Beneficio principal: {benefit}.")

    duration = answers.get("duration")
    if not _is_skipped(duration):
        parts.append(f"A duracao e de {duration} minutos.")

    return " ".join(parts)


def _parse_money(raw: str | None) -> Decimal:
    if raw is None:
        raise ValidationError("Preco invalido.")
    text = raw.strip().replace("R$", "").replace(" ", "")
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".")
    try:
        value = Decimal(text)
    except InvalidOperation as exc:
        raise ValidationError("Preco invalido.", details={"value": raw}) from exc
    if value < 0:
        raise ValidationError("Preco invalido.", details={"value": raw})
    return value


def _parse_minutes(raw: str | None) -> int:
    if raw is None:
        raise ValidationError("Duracao invalida.")
    digits = "".join(ch for ch in raw if ch.isdigit())
    if not digits:
        raise ValidationError("Duracao invalida.", details={"value": raw})
    minutes = int(digits)
    if minutes < 1:
        raise ValidationError("Duracao invalida.", details={"value": raw})
    return minutes
