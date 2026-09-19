"""Provedor OpenAI com saida estruturada.

Concentra tudo o que e especifico do fornecedor: montagem da requisicao,
selecao de modelo (texto x visao), retentativas, timeout e traducao de erros do
SDK para as excecoes de dominio da aplicacao. O restante do sistema nunca
importa `openai`.
"""

from __future__ import annotations

import time
from typing import Any, ClassVar

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

from app.ai.base import AICompletion, AIProvider, OutputT
from app.ai.types import Prompt
from app.core.config import Settings, settings as default_settings
from app.core.exceptions import AIProviderError, AIResponseError
from app.core.logging import get_logger

logger = get_logger(__name__)

#: Erros que compensa repetir: indisponibilidade momentanea e limite de taxa.
RETRYABLE_ERRORS = (APIConnectionError, APITimeoutError, RateLimitError)


class OpenAIProvider(AIProvider):
    name: ClassVar[str] = "openai"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or default_settings
        if not self.settings.OPENAI_API_KEY:
            raise AIProviderError(
                "OPENAI_API_KEY nao configurada. Defina a variavel de ambiente ou "
                "use AI_PROVIDER=mock."
            )
        self.client = AsyncOpenAI(
            api_key=self.settings.OPENAI_API_KEY,
            base_url=self.settings.OPENAI_BASE_URL or "https://api.openai.com/v1",
            timeout=self.settings.OPENAI_TIMEOUT_SECONDS,
            max_retries=0,  # as retentativas ficam com o tenacity, abaixo
        )

    @property
    def supports_vision(self) -> bool:
        return True

    @property
    def default_model(self) -> str:
        return self.settings.OPENAI_MODEL

    def _model_for(self, prompt: Prompt) -> str:
        return (
            self.settings.OPENAI_VISION_MODEL
            if prompt.requires_vision
            else self.settings.OPENAI_MODEL
        )

    def _build_input(self, prompt: Prompt) -> list[dict[str, Any]]:
        content: list[dict[str, Any]] = [{"type": "input_text", "text": prompt.user}]
        for image in prompt.images:
            content.append({"type": "input_image", "image_url": image.url})
            if image.label:
                content.append(
                    {"type": "input_text", "text": f"Rotulo da imagem acima: {image.label}"}
                )

        return [
            {"role": "system", "content": prompt.system},
            {"role": "user", "content": content},
        ]

    async def generate_structured(
        self,
        *,
        prompt: Prompt,
        output_model: type[OutputT],
    ) -> AICompletion[OutputT]:
        model = self._model_for(prompt)
        started = time.perf_counter()

        @retry(
            retry=retry_if_exception_type(RETRYABLE_ERRORS),
            stop=stop_after_attempt(max(1, self.settings.AI_MAX_RETRIES)),
            wait=wait_exponential(multiplier=1, min=1, max=12),
            reraise=True,
        )
        async def _call() -> Any:
            return await self.client.responses.parse(
                model=model,
                input=self._build_input(prompt),
                text_format=output_model,
                temperature=(
                    prompt.temperature
                    if prompt.temperature is not None
                    else self.settings.AI_TEMPERATURE
                ),
                max_output_tokens=prompt.max_output_tokens,
            )

        try:
            response = await _call()
        except RateLimitError as exc:
            raise AIProviderError(
                "Limite de uso da API de IA atingido. Tente novamente em instantes."
            ) from exc
        except APITimeoutError as exc:
            raise AIProviderError("A geracao demorou mais do que o limite configurado.") from exc
        except APIConnectionError as exc:
            cause = exc.__cause__
            logger.error(
                "openai_connection_error",
                prompt=prompt.name,
                model=model,
                cause=str(cause) if cause else str(exc),
            )
            raise AIProviderError("Nao foi possivel conectar ao provedor de IA.") from exc
        except APIStatusError as exc:
            logger.error(
                "openai_status_error",
                status=exc.status_code,
                prompt=prompt.name,
                model=model,
            )
            raise AIProviderError(
                f"O provedor de IA respondeu com erro {exc.status_code}."
            ) from exc

        parsed = getattr(response, "output_parsed", None)
        if parsed is None:
            refusal = self._extract_refusal(response)
            raise AIResponseError(
                "A IA nao devolveu uma resposta no formato esperado.",
                details={"prompt": prompt.name, "refusal": refusal},
            )

        latency_ms = int((time.perf_counter() - started) * 1000)
        usage = getattr(response, "usage", None)

        logger.info(
            "ai_generation",
            provider=self.name,
            model=model,
            prompt=prompt.name,
            latency_ms=latency_ms,
            images=len(prompt.images),
        )

        return AICompletion(
            value=parsed,
            provider=self.name,
            model=model,
            latency_ms=latency_ms,
            input_tokens=getattr(usage, "input_tokens", None) if usage else None,
            output_tokens=getattr(usage, "output_tokens", None) if usage else None,
        )

    @staticmethod
    def _extract_refusal(response: Any) -> str | None:
        """Recupera a mensagem de recusa, quando o modelo se nega a responder."""
        try:
            for item in getattr(response, "output", []) or []:
                for part in getattr(item, "content", []) or []:
                    refusal = getattr(part, "refusal", None)
                    if refusal:
                        return str(refusal)
        except Exception:  # noqa: BLE001 - diagnostico best effort
            return None
        return None
