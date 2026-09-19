"""Excecoes de dominio e seus handlers HTTP.

Os services levantam excecoes de dominio; a traducao para status HTTP acontece
em um unico lugar (`register_exception_handlers`). Isso mantem a regra de
negocio independente do transporte.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.logging import get_logger

logger = get_logger(__name__)


class DomainError(Exception):
    """Base de todas as excecoes de negocio."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "domain_error"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotFoundError(DomainError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"


class ConflictError(DomainError):
    status_code = status.HTTP_409_CONFLICT
    code = "conflict"


class ValidationError(DomainError):
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    code = "validation_error"


class AuthenticationError(DomainError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "authentication_error"


class PermissionDeniedError(DomainError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "permission_denied"


class InvalidStateTransitionError(DomainError):
    status_code = status.HTTP_409_CONFLICT
    code = "invalid_state_transition"


class StorageError(DomainError):
    status_code = status.HTTP_502_BAD_GATEWAY
    code = "storage_error"


class AIProviderError(DomainError):
    """Falha ao conversar com o provedor de IA (rede, quota, resposta invalida)."""

    status_code = status.HTTP_502_BAD_GATEWAY
    code = "ai_provider_error"


class AIResponseError(AIProviderError):
    code = "ai_response_error"


def _error_body(code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "details": details or {}}}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
        if exc.status_code >= 500:
            logger.error("domain_error", code=exc.code, message=exc.message, details=exc.details)
        return JSONResponse(
            status_code=exc.status_code,
            # `jsonable_encoder`: `details` pode conter listas de erros do
            # Pydantic, cujo `ctx` embute a excecao original (nao serializavel
            # pelo `json` padrao).
            content=_error_body(exc.code, exc.message, jsonable_encoder(exc.details)),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=_error_body(
                "request_validation_error",
                "Dados enviados sao invalidos.",
                # `exc.errors()` carrega a excecao original em `ctx`, que nao e
                # serializavel; o encoder do FastAPI resolve isso.
                {"fields": jsonable_encoder(exc.errors())},
            ),
        )

    @app.exception_handler(Exception)
    async def _unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_error", path=request.url.path, error=str(exc))
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_body("internal_error", "Erro interno inesperado."),
        )
