"""Geracao de video via fal.ai (Kling / Minimax, configuravel)."""

from __future__ import annotations

import asyncio
import base64
import time
from typing import Any, ClassVar

import httpx

from app.ai.image.base import ImageReference
from app.ai.video.base import GeneratedVideo, VideoPrompt, VideoProvider
from app.core.config import Settings
from app.core.config import settings as default_settings
from app.core.exceptions import AIProviderError
from app.core.logging import get_logger

logger = get_logger(__name__)

_FAL_QUEUE = "https://queue.fal.run"
_POLL_INTERVAL_SECONDS = 2.0
_MAX_POLLS = 90


class FalVideoProvider(VideoProvider):
    name: ClassVar[str] = "fal"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or default_settings
        if not self.settings.FAL_KEY:
            raise AIProviderError(
                "FAL_KEY nao configurada. Defina a chave da fal.ai ou use VIDEO_PROVIDER=mock."
            )
        self._headers = {
            "Authorization": f"Key {self.settings.FAL_KEY}",
            "Content-Type": "application/json",
        }

    @property
    def default_model(self) -> str:
        return self.settings.FAL_VIDEO_MODEL

    async def generate(self, request: VideoPrompt) -> GeneratedVideo:
        started = time.perf_counter()
        model = self.default_model.strip().lstrip("/")
        payload: dict[str, Any] = {
            "prompt": request.prompt,
            "duration": str(request.duration_seconds),
            "aspect_ratio": request.aspect_ratio,
        }
        if request.references:
            payload["image_url"] = _data_uri(request.references[0])
        if request.seed:
            payload["seed"] = abs(int(request.seed)) % (2**31)

        timeout = httpx.Timeout(20.0, read=float(self.settings.FAL_VIDEO_TIMEOUT_SECONDS))
        try:
            async with httpx.AsyncClient(timeout=timeout) as http:
                body = await self._run(http, model, payload)
                raw = await self._extract_bytes(http, body)
        except httpx.TimeoutException as exc:
            raise AIProviderError("A geracao do video demorou mais do que o limite.") from exc
        except httpx.HTTPError as exc:
            raise AIProviderError("Nao foi possivel conectar ao provedor de video (fal.ai).") from exc

        latency_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "ai_video_generation",
            provider=self.name,
            model=model,
            latency_ms=latency_ms,
            used_reference=bool(request.references),
        )
        return GeneratedVideo(
            data=raw,
            mime_type="video/mp4",
            width=720,
            height=1280,
            duration_seconds=request.duration_seconds,
            provider=self.name,
            model=model,
            prompt=request.prompt,
            latency_ms=latency_ms,
            used_reference=bool(request.references),
        )

    async def _run(
        self, http: httpx.AsyncClient, model: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        queued = await http.post(f"{_FAL_QUEUE}/{model}", headers=self._headers, json=payload)
        if queued.status_code >= 400:
            raise AIProviderError(_fal_message(queued, "O provedor recusou o pedido de video."))
        envelope = queued.json()
        status_url = envelope.get("status_url")
        response_url = envelope.get("response_url")
        if not status_url or not response_url:
            if envelope.get("video") or envelope.get("video_url"):
                return envelope
            raise AIProviderError("A fila de video nao devolveu URL de acompanhamento.")

        for _ in range(_MAX_POLLS):
            status_response = await http.get(status_url, headers=self._headers)
            if status_response.status_code >= 400:
                raise AIProviderError(
                    _fal_message(status_response, "Falha ao consultar a fila de video.")
                )
            status_body = status_response.json()
            status = str(status_body.get("status") or "").upper()
            if status in {"COMPLETED", "OK"}:
                result = await http.get(response_url, headers=self._headers)
                if result.status_code >= 400:
                    raise AIProviderError(_fal_message(result, "O provedor nao devolveu o video."))
                return result.json()
            if status in {"FAILED", "ERROR", "CANCELLED"}:
                raise AIProviderError("A geracao do video falhou.")
            await asyncio.sleep(_POLL_INTERVAL_SECONDS)

        raise AIProviderError("A geracao do video demorou mais do que o limite.")

    async def _extract_bytes(self, http: httpx.AsyncClient, body: dict[str, Any]) -> bytes:
        video = body.get("video") or {}
        url = None
        if isinstance(video, dict):
            url = video.get("url")
        if not url:
            url = body.get("video_url")
        if not url:
            raise AIProviderError("A resposta de video nao tinha URL do arquivo.")
        download = await http.get(url)
        download.raise_for_status()
        data = download.content
        if not data:
            raise AIProviderError("O video veio vazio.")
        return data


def _data_uri(reference: ImageReference) -> str:
    encoded = base64.b64encode(reference.data).decode("ascii")
    mime = reference.mime_type or "image/png"
    return f"data:{mime};base64,{encoded}"


def _fal_message(response: httpx.Response, fallback: str) -> str:
    try:
        payload = response.json()
    except ValueError:
        return fallback
    if isinstance(payload, dict):
        detail = payload.get("detail") or payload.get("error") or payload.get("message")
        if isinstance(detail, str) and detail.strip():
            return f"{fallback} {detail.strip()[:240]}"
    return f"{fallback} (HTTP {response.status_code})"
