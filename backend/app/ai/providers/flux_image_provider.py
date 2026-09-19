"""Geracao de still via fal.ai (Flux).

Isolado do provedor de texto e da OpenAI. O worker so fala HTTP com a fila da
fal; o restante da aplicacao recebe `GeneratedImage`.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, ClassVar

import httpx

from app.ai.image.base import GeneratedImage, ImagePrompt, ImageProvider
from app.ai.image.prompt import parse_size
from app.core.config import Settings
from app.core.config import settings as default_settings
from app.core.exceptions import AIProviderError
from app.core.logging import get_logger

logger = get_logger(__name__)

_FAL_QUEUE = "https://queue.fal.run"
_POLL_INTERVAL_SECONDS = 1.2
_MAX_POLLS = 90


class FluxImageProvider(ImageProvider):
    name: ClassVar[str] = "flux"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or default_settings
        if not self.settings.FAL_KEY:
            raise AIProviderError(
                "FAL_KEY nao configurada. Defina a chave da fal.ai ou use IMAGE_PROVIDER=mock."
            )
        self._headers = {
            "Authorization": f"Key {self.settings.FAL_KEY}",
            "Content-Type": "application/json",
        }

    @property
    def default_model(self) -> str:
        return self.settings.FAL_IMAGE_MODEL

    async def generate(self, request: ImagePrompt) -> GeneratedImage:
        model = self.default_model.strip().lstrip("/")
        started = time.perf_counter()
        width, height = parse_size(request.size)
        prompt = request.prompt
        # A fal filtra o TEXTO do prompt. Nao anexar "nude/porn" no Avoid —
        # isso dispara o content checker mesmo com enable_safety_checker=false.
        if request.negative_prompt:
            prompt = f"{prompt}\n\nAvoid: {_fal_safe_avoid(request.negative_prompt)}"

        schnell = "schnell" in model.lower()
        safety_on = self.settings.FAL_ENABLE_SAFETY_CHECKER
        payload: dict[str, Any] = {
            "prompt": prompt[:4000],
            "image_size": {"width": width, "height": height},
            "num_images": 1,
            "output_format": "png",
            # Nomes oficiais: https://fal.ai/docs/documentation/model-apis/model-arguments#enable_safety_checker
            "enable_safety_checker": safety_on,
            "enable_safety_checks": safety_on,
            "num_inference_steps": 4 if schnell else 28,
        }
        if not schnell:
            payload["guidance_scale"] = 3.5
        if request.seed:
            payload["seed"] = abs(int(request.seed)) % (2**31)

        timeout = httpx.Timeout(20.0, read=float(self.settings.FAL_TIMEOUT_SECONDS))
        try:
            async with httpx.AsyncClient(timeout=timeout) as http:
                body = await self._run(http, model, payload)
                raw = await self._extract_bytes(http, body)
        except httpx.TimeoutException as exc:
            raise AIProviderError("A geracao da imagem no Flux demorou mais do que o limite.") from exc
        except httpx.HTTPError as exc:
            raise AIProviderError("Nao foi possivel conectar ao Flux (fal.ai).") from exc

        nsfw_flags = body.get("has_nsfw_concepts") or []
        if self.settings.FAL_ENABLE_SAFETY_CHECKER and nsfw_flags and nsfw_flags[0]:
            raise AIProviderError(
                "O still foi bloqueado pelo filtro de seguranca. Tente um enquadramento menos explicito."
            )

        latency_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "ai_image_generation",
            provider=self.name,
            model=model,
            latency_ms=latency_ms,
            presenter=request.presenter_id,
            safety_checker=safety_on,
        )
        return GeneratedImage(
            data=raw,
            mime_type="image/png",
            width=width,
            height=height,
            provider=self.name,
            model=model,
            prompt=request.prompt,
            latency_ms=latency_ms,
        )

    async def _run(
        self, http: httpx.AsyncClient, model: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        queued = await http.post(f"{_FAL_QUEUE}/{model}", headers=self._headers, json=payload)
        if queued.status_code >= 400:
            raise AIProviderError(_fal_message(queued, "O Flux recusou o pedido de imagem."))
        envelope = queued.json()
        status_url = envelope.get("status_url")
        response_url = envelope.get("response_url")
        if not status_url or not response_url:
            if isinstance(envelope.get("images"), list):
                return envelope
            raise AIProviderError("A fila do Flux nao devolveu URL de acompanhamento.")

        for _ in range(_MAX_POLLS):
            status_response = await http.get(status_url, headers=self._headers)
            if status_response.status_code >= 400:
                raise AIProviderError(_fal_message(status_response, "Falha ao consultar a fila do Flux."))
            status_body = status_response.json()
            status = str(status_body.get("status") or "").upper()
            if status in {"COMPLETED", "OK"}:
                result = await http.get(response_url, headers=self._headers)
                if result.status_code >= 400:
                    raise AIProviderError(_fal_message(result, "O Flux nao devolveu a imagem."))
                return result.json()
            if status in {"FAILED", "ERROR", "CANCELLED"}:
                raise AIProviderError("O Flux falhou ao gerar a imagem.")
            await asyncio.sleep(_POLL_INTERVAL_SECONDS)

        raise AIProviderError("A geracao da imagem no Flux demorou mais do que o limite.")

    async def _extract_bytes(self, http: httpx.AsyncClient, body: dict[str, Any]) -> bytes:
        images = body.get("images") or []
        if not images:
            raise AIProviderError("O Flux nao devolveu arquivo.")
        first = images[0] or {}
        url = first.get("url")
        if not url:
            raise AIProviderError("A resposta do Flux nao tinha URL da imagem.")
        download = await http.get(url)
        download.raise_for_status()
        data = download.content
        if not data:
            raise AIProviderError("A imagem do Flux veio vazia.")
        return data


_FAL_PROMPT_TRIGGERS = (
    "nude",
    "nudity",
    "genitals",
    "nipples",
    "pornography",
    "porn",
    "sexual",
    "sex",
    "explicit",
    "teen",
)


def _fal_safe_avoid(negative: str) -> str:
    """Remove termos que o content checker da fal trata como material proibido."""
    kept: list[str] = []
    for part in negative.split(","):
        token = part.strip()
        if not token:
            continue
        low = token.lower()
        if any(trigger in low for trigger in _FAL_PROMPT_TRIGGERS):
            continue
        kept.append(token)
    extra = ["extra limbs", "deformed face", "text overlay", "watermark"]
    for item in extra:
        if item not in {entry.lower() for entry in kept}:
            kept.append(item)
    return ", ".join(kept) or "extra limbs, watermark"


def _fal_message(response: httpx.Response, fallback: str) -> str:
    try:
        payload = response.json()
    except ValueError:
        return fallback
    if isinstance(payload, dict):
        detail = payload.get("detail") or payload.get("error") or payload.get("message")
        if isinstance(detail, str) and detail.strip():
            text = detail.strip()[:240]
            if "content checker" in text.lower() or "flagged" in text.lower():
                return (
                    f"{fallback} {text} "
                    "Se FAL_ENABLE_SAFETY_CHECKER=false e o erro continua, a conta da fal "
                    "precisa autorizar desligar o checker (dashboard / suporte)."
                )
            return f"{fallback} {text}"
        if isinstance(detail, list) and detail:
            first = detail[0]
            if isinstance(first, dict) and first.get("msg"):
                return f"{fallback} {str(first['msg'])[:240]}"
    return f"{fallback} (HTTP {response.status_code})"
