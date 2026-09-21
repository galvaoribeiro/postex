"""Geracao de video via fal.ai (Kling / Seedance, configuravel)."""

from __future__ import annotations

import asyncio
import base64
import time
from io import BytesIO
from typing import Any, ClassVar

import httpx
from PIL import Image

from app.ai.image.base import ImageReference
from app.ai.video.base import GeneratedVideo, VideoPrompt, VideoProvider
from app.core.config import Settings
from app.core.config import settings as default_settings
from app.core.exceptions import AIProviderError
from app.core.logging import get_logger

logger = get_logger(__name__)

_FAL_QUEUE = "https://queue.fal.run"
_FAL_UPLOAD_INIT = "https://rest.alpha.fal.ai/storage/upload/initiate"
_KLING_PROMPT_MAX = 2500
_STILL_MAX_EDGE = 1280


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

    @property
    def _poll_interval_seconds(self) -> float:
        return max(0.5, float(self.settings.FAL_VIDEO_POLL_INTERVAL_SECONDS))

    @property
    def _max_polls(self) -> int:
        budget = max(30, int(self.settings.FAL_VIDEO_TIMEOUT_SECONDS))
        return max(1, int(budget / self._poll_interval_seconds))

    def _http_timeout(self) -> httpx.Timeout:
        read = float(max(30, self.settings.FAL_VIDEO_TIMEOUT_SECONDS))
        return httpx.Timeout(30.0, read=read, write=read, pool=read)

    async def generate(self, request: VideoPrompt) -> GeneratedVideo:
        started = time.perf_counter()
        model = normalize_fal_video_model(self.default_model)
        if not request.references:
            raise AIProviderError(
                "O provedor de video precisa do still da modelo (image-to-video)."
            )

        timeout = self._http_timeout()
        try:
            async with httpx.AsyncClient(timeout=timeout) as http:
                image_url = await self._image_url(http, request.references[0])
                try:
                    return await self._generate_with_model(
                        http, model, request, image_url, started
                    )
                except AIProviderError as exc:
                    fallback = normalize_fal_video_model(
                        self.settings.FAL_VIDEO_FALLBACK_MODEL or ""
                    )
                    if (
                        fallback
                        and fallback != model
                        and _is_seedance(model)
                        and _is_likeness_refusal(str(exc))
                    ):
                        logger.warning(
                            "ai_video_seedance_likeness_fallback",
                            model=model,
                            fallback=fallback,
                            error=str(exc)[:240],
                        )
                        return await self._generate_with_model(
                            http, fallback, request, image_url, started
                        )
                    raise
        except httpx.TimeoutException as exc:
            raise AIProviderError(
                "A geracao do video demorou mais do que o limite "
                f"({self.settings.FAL_VIDEO_TIMEOUT_SECONDS}s). "
                "Aumente FAL_VIDEO_TIMEOUT_SECONDS no .env se usar Seedance ou Kling."
            ) from exc
        except httpx.HTTPError as exc:
            raise AIProviderError("Nao foi possivel conectar ao provedor de video (fal.ai).") from exc

    async def _generate_with_model(
        self,
        http: httpx.AsyncClient,
        model: str,
        request: VideoPrompt,
        image_url: str,
        started: float,
    ) -> GeneratedVideo:
        payload = build_fal_video_payload(model, request, image_url)
        logger.info(
            "ai_video_request",
            model=model,
            duration=payload.get("duration"),
            generate_audio=payload.get("generate_audio"),
            prompt_chars=len(str(payload.get("prompt") or "")),
            image_hosted=not str(image_url).startswith("data:"),
        )
        body = await self._run(http, model, payload)
        raw = await self._extract_bytes(http, body)
        latency_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "ai_video_generation",
            provider=self.name,
            model=model,
            latency_ms=latency_ms,
            used_reference=True,
        )
        duration_seconds = _payload_duration_seconds(
            payload.get("duration"), request.duration_seconds
        )
        return GeneratedVideo(
            data=raw,
            mime_type="video/mp4",
            width=720,
            height=1280,
            duration_seconds=duration_seconds,
            provider=self.name,
            model=model,
            prompt=request.prompt,
            latency_ms=latency_ms,
            used_reference=True,
        )

    async def _image_url(self, http: httpx.AsyncClient, reference: ImageReference) -> str:
        prepared = compress_still_for_video(reference)
        uploaded = await self._upload_still(http, prepared)
        if uploaded:
            return uploaded
        return _data_uri(prepared)

    async def _upload_still(
        self, http: httpx.AsyncClient, reference: ImageReference
    ) -> str | None:
        filename = reference.filename or "still.jpg"
        mime = reference.mime_type or "image/jpeg"
        try:
            initiated = await http.post(
                _FAL_UPLOAD_INIT,
                headers={
                    "Authorization": f"Key {self.settings.FAL_KEY}",
                    "Content-Type": "application/json",
                },
                json={"content_type": mime, "file_name": filename},
            )
            if initiated.status_code >= 400:
                logger.warning(
                    "fal_video_upload_initiate_rejected",
                    status=initiated.status_code,
                )
                return None
            body = initiated.json()
            upload_url = body.get("upload_url")
            file_url = body.get("file_url")
            if not upload_url or not file_url:
                logger.warning("fal_video_upload_initiate_empty")
                return None
            put = await http.put(
                str(upload_url),
                content=reference.data,
                headers={"Content-Type": mime},
            )
            if put.status_code >= 400:
                logger.warning("fal_video_upload_put_rejected", status=put.status_code)
                return None
            return str(file_url)
        except Exception as exc:  # noqa: BLE001 - upload e opcional; cai no data URI
            logger.warning("fal_video_upload_failed", error=type(exc).__name__)
            return None

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

        max_polls = self._max_polls
        for attempt in range(max_polls):
            status_response = await http.get(status_url, headers=self._headers)
            if status_response.status_code == 202:
                await asyncio.sleep(self._poll_interval_seconds)
                continue
            if status_response.status_code >= 400:
                raise AIProviderError(
                    _fal_message(status_response, "Falha ao consultar a fila de video.")
                )
            status_body = status_response.json()
            status = str(status_body.get("status") or "").upper()
            if status in {"COMPLETED", "OK"}:
                result = await http.get(response_url, headers=self._headers)
                if result.status_code >= 400:
                    raise AIProviderError(
                        _fal_message(result, "O provedor recusou o video gerado.")
                    )
                return result.json()
            if status in {"FAILED", "ERROR", "CANCELLED"}:
                raise AIProviderError(
                    _queue_error(status_body, "A geracao do video falhou.")
                )
            if attempt and attempt % 15 == 0:
                logger.info(
                    "ai_video_queue_waiting",
                    model=model,
                    attempt=attempt,
                    max_polls=max_polls,
                    status=status or "UNKNOWN",
                )
            await asyncio.sleep(self._poll_interval_seconds)

        raise AIProviderError(
            "A geracao do video demorou mais do que o limite "
            f"({self.settings.FAL_VIDEO_TIMEOUT_SECONDS}s). "
            "Aumente FAL_VIDEO_TIMEOUT_SECONDS no .env se usar Seedance ou Kling."
        )

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


def compress_still_for_video(reference: ImageReference) -> ImageReference:
    """JPEG menor para I2V: PNG 9:16 do Flux costuma passar de 2 MB."""
    try:
        image = Image.open(BytesIO(reference.data)).convert("RGB")
    except Exception:  # noqa: BLE001 - se nao for imagem, manda o original
        return reference
    image.thumbnail((_STILL_MAX_EDGE, _STILL_MAX_EDGE), Image.Resampling.LANCZOS)
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=82, optimize=True)
    data = buffer.getvalue()
    if not data:
        return reference
    return ImageReference(data=data, mime_type="image/jpeg", filename="still.jpg")


def normalize_fal_video_model(model: str) -> str:
    """Seedance 2.5 sem sufixo e o endpoint B2B generico, nao o I2V."""
    name = (model or "").strip().lstrip("/")
    if name.rstrip("/") == "bytedance/seedance-2.5":
        return "bytedance/seedance-2.5/image-to-video"
    return name


def build_fal_video_payload(
    model: str, request: VideoPrompt, image_url: str
) -> dict[str, Any]:
    """Monta o JSON aceito pelo endpoint de cada familia (Kling 2.x/3, Veo, Seedance)."""
    name = normalize_fal_video_model(model).lower()
    prompt = request.prompt.strip()
    if "kling" in name:
        prompt = prompt[:_KLING_PROMPT_MAX]
    duration = _provider_duration(name, request.duration_seconds)
    negative = " ".join(request.negative_prompt.split())[:1000] if request.negative_prompt else ""

    if _is_kling_v3(name):
        payload: dict[str, Any] = {
            "prompt": prompt,
            "start_image_url": image_url,
            "duration": duration,
            "generate_audio": bool(request.generate_audio),
        }
        if negative:
            payload["negative_prompt"] = negative
        return payload

    if _is_veo(name):
        payload = {
            "prompt": prompt,
            "image_url": image_url,
            "duration": duration,
            "aspect_ratio": "9:16",
            "resolution": "720p",
            "generate_audio": bool(request.generate_audio),
            "auto_fix": True,
        }
        if negative:
            payload["negative_prompt"] = negative
        if request.seed:
            payload["seed"] = abs(int(request.seed)) % (2**31)
        return payload

    payload = {
        "prompt": prompt,
        "image_url": image_url,
        "duration": duration,
    }
    if "seedance" in name:
        payload["aspect_ratio"] = "auto"
        payload["resolution"] = "720p"
        payload["generate_audio"] = bool(request.generate_audio)
        if request.end_user_id:
            payload["end_user_id"] = request.end_user_id[:128]
        if request.seed:
            payload["seed"] = abs(int(request.seed)) % (2**31)
        return payload
    if negative:
        payload["negative_prompt"] = negative
    return payload


def _provider_duration(model: str, requested: int) -> str:
    seconds = max(1, int(requested or 5))
    if _is_kling_v3(model):
        return str(min(15, max(3, seconds)))
    if "kling" in model:
        return "10" if seconds >= 8 else "5"
    if _is_veo(model):
        if seconds <= 5:
            return "4s"
        if seconds <= 7:
            return "6s"
        return "8s"
    if "seedance" in model:
        return str(min(30, max(4, seconds)))
    return str(seconds)


def _payload_duration_seconds(duration: object, fallback: int) -> int:
    raw = str(duration or "").strip().lower().rstrip("s")
    if raw.isdigit():
        return int(raw)
    return fallback


def _is_kling_v3(model: str) -> bool:
    name = (model or "").lower()
    return "kling" in name and "/v3/" in name


def _is_veo(model: str) -> bool:
    return "veo3" in (model or "").lower() or "/veo3." in (model or "").lower()


def _is_seedance(model: str) -> bool:
    return "seedance" in (model or "").lower()


def _is_likeness_refusal(message: str) -> bool:
    low = message.lower()
    return (
        "likenesses of real people" in low
        or "likeness of real people" in low
        or "private information that cannot be processed" in low
        or "semelhancas de pessoas reais" in low
    )


def _data_uri(reference: ImageReference) -> str:
    encoded = base64.b64encode(reference.data).decode("ascii")
    mime = reference.mime_type or "image/png"
    return f"data:{mime};base64,{encoded}"


def _queue_error(body: dict[str, Any], fallback: str) -> str:
    for key in ("error", "message", "detail"):
        value = body.get(key)
        if isinstance(value, str) and value.strip():
            return f"{fallback} {value.strip()[:240]}"
    return fallback


def _fal_message(response: httpx.Response, fallback: str) -> str:
    try:
        payload = response.json()
    except ValueError:
        return f"{fallback} (HTTP {response.status_code})"
    if isinstance(payload, dict):
        detail = payload.get("detail") or payload.get("error") or payload.get("message")
        if isinstance(detail, str) and detail.strip():
            text = detail.strip()[:320]
            if _is_likeness_refusal(text):
                return (
                    f"{fallback} O Seedance recusou o still da modelo: o filtro "
                    "trata o rosto fotorrealista como pessoa real. Use Kling "
                    "para este tipo de video ou deixe o fallback ativo."
                )
            return f"{fallback} {text}"
        if isinstance(detail, list) and detail:
            parts: list[str] = []
            for item in detail[:4]:
                if isinstance(item, dict):
                    loc = item.get("loc")
                    msg = item.get("msg") or item.get("message")
                    if msg:
                        where = ".".join(str(part) for part in loc) if isinstance(loc, list) else ""
                        parts.append(f"{where}: {msg}".strip(": "))
                elif isinstance(item, str):
                    parts.append(item)
            if parts:
                return f"{fallback} {' | '.join(parts)[:320]}"
    return f"{fallback} (HTTP {response.status_code})"
