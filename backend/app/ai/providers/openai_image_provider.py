"""Geracao de still via API de imagens da OpenAI.

Isolado do provedor de texto. O restante da aplicacao nao importa `openai`.
"""

from __future__ import annotations

import base64
import io
import time
from typing import Any, ClassVar

import httpx
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
    RateLimitError,
)
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.ai.image.base import GeneratedImage, ImagePrompt, ImageProvider, ImageReference
from app.ai.image.prompt import parse_size
from app.core.config import Settings
from app.core.config import settings as default_settings
from app.core.exceptions import AIProviderError
from app.core.logging import get_logger

logger = get_logger(__name__)

RETRYABLE_ERRORS = (APIConnectionError, APITimeoutError, RateLimitError)

# images.edit do GPT Image nao aceita 1024x1792 (DALL-E 3). generate fica igual.
_EDIT_SIZE_ALIASES = {
    "1024x1792": "1024x1536",
    "1792x1024": "1536x1024",
}


def _status_detail(exc: APIStatusError) -> str | None:
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        error = body.get("error")
        if isinstance(error, dict):
            message = error.get("message")
            if message:
                return str(message)[:300]
        message = body.get("message")
        if message:
            return str(message)[:300]
    text = str(exc)
    return text[:300] if text else None


class OpenAIImageProvider(ImageProvider):
    name: ClassVar[str] = "openai"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or default_settings
        if not self.settings.OPENAI_API_KEY:
            raise AIProviderError(
                "OPENAI_API_KEY nao configurada. Defina a variavel ou use IMAGE_PROVIDER=mock."
            )
        self.client = AsyncOpenAI(
            api_key=self.settings.OPENAI_API_KEY,
            # Nunca passe None: o SDK interpreta OPENAI_BASE_URL="" do .env
            # como URL sem protocolo e vira APIConnectionError.
            base_url=self.settings.OPENAI_BASE_URL or "https://api.openai.com/v1",
            timeout=max(self.settings.OPENAI_TIMEOUT_SECONDS, 120),
            max_retries=0,
        )

    @property
    def default_model(self) -> str:
        return self.settings.OPENAI_IMAGE_MODEL

    async def generate(self, request: ImagePrompt) -> GeneratedImage:
        model = self.default_model
        started = time.perf_counter()
        prompt = request.prompt
        if request.negative_prompt:
            prompt = f"{prompt}\n\nAvoid: {request.negative_prompt}"

        used_reference = bool(request.references)
        size = self._edit_size(request.size) if used_reference else request.size

        @retry(
            retry=retry_if_exception_type(RETRYABLE_ERRORS),
            stop=stop_after_attempt(max(1, self.settings.AI_MAX_RETRIES)),
            wait=wait_exponential(multiplier=1, min=1, max=12),
            reraise=True,
        )
        async def _call() -> Any:
            if used_reference:
                return await self.client.images.edit(
                    **self._edit_kwargs(model, prompt, size, request.references)
                )
            return await self.client.images.generate(
                **self._generate_kwargs(model, prompt, request.size)
            )

        try:
            response = await _call()
        except RateLimitError as exc:
            raise AIProviderError(
                "Limite de uso da API de imagem atingido. Tente novamente em instantes."
            ) from exc
        except APITimeoutError as exc:
            raise AIProviderError("A geracao da imagem demorou mais do que o limite.") from exc
        except APIConnectionError as exc:
            cause = exc.__cause__
            logger.error(
                "openai_image_connection_error",
                model=model,
                cause=str(cause) if cause else str(exc),
            )
            raise AIProviderError("Nao foi possivel conectar ao provedor de imagem.") from exc
        except APIStatusError as exc:
            detail = _status_detail(exc)
            logger.error(
                "openai_image_status_error",
                status=exc.status_code,
                model=model,
                detail=detail,
            )
            message = f"O provedor de imagem respondeu com erro {exc.status_code}."
            if detail:
                message = f"{message} {detail}"
            raise AIProviderError(message) from exc

        data = (getattr(response, "data", None) or [None])[0]
        if data is None:
            raise AIProviderError("O provedor de imagem nao devolveu arquivo.")

        raw = await self._extract_bytes(data)
        width, height = parse_size(size)
        latency_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "ai_image_generation",
            provider=self.name,
            model=model,
            latency_ms=latency_ms,
            used_reference=used_reference,
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
            used_reference=used_reference,
        )

    def _generate_kwargs(self, model: str, prompt: str, size: str) -> dict[str, Any]:
        # DALL-E 3: 4000. GPT Image (gpt-image-2 e sucessores): 32000.
        max_chars = 4000 if model.startswith("dall-e") else 32_000
        kwargs: dict[str, Any] = {
            "model": model,
            "prompt": prompt[:max_chars],
            "size": size,
            "n": 1,
        }
        if model.startswith("dall-e"):
            kwargs["response_format"] = "b64_json"
            kwargs["quality"] = "standard"
            return kwargs
        # GPT Image (`gpt-image-2` e sucessores): PNG em base64, sem response_format.
        kwargs["output_format"] = "png"
        kwargs["quality"] = "medium"
        return kwargs

    def _edit_kwargs(
        self,
        model: str,
        prompt: str,
        size: str,
        references: tuple[ImageReference, ...],
    ) -> dict[str, Any]:
        max_chars = 4000 if model.startswith("dall-e") else 32_000
        files = [_file_from_reference(item) for item in references]
        kwargs: dict[str, Any] = {
            "model": model,
            "prompt": prompt[:max_chars],
            "image": files[0] if len(files) == 1 else files,
            "size": size,
            "n": 1,
        }
        if model.startswith("dall-e"):
            kwargs["response_format"] = "b64_json"
            return kwargs
        kwargs["output_format"] = "png"
        kwargs["quality"] = "medium"
        return kwargs

    def _edit_size(self, size: str) -> str:
        return _EDIT_SIZE_ALIASES.get(size.lower(), size)

    async def _extract_bytes(self, data: Any) -> bytes:
        b64 = getattr(data, "b64_json", None)
        if b64:
            return base64.b64decode(b64)
        url = getattr(data, "url", None)
        if not url:
            raise AIProviderError("A resposta de imagem nao tinha bytes nem URL.")
        async with httpx.AsyncClient(timeout=60) as http:
            response = await http.get(url)
            response.raise_for_status()
            return response.content


def _file_from_reference(reference: ImageReference) -> tuple[str, io.BytesIO, str]:
    buffer = io.BytesIO(reference.data)
    filename = reference.filename or "product.png"
    mime = reference.mime_type or "image/png"
    return filename, buffer, mime
