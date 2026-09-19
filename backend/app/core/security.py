"""Hash de senhas e emissao/verificacao de tokens JWT."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

import jwt
from pwdlib import PasswordHash

from app.core.config import settings
from app.core.exceptions import AuthenticationError

_password_hash = PasswordHash.recommended()


class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"


def hash_password(plain_password: str) -> str:
    return _password_hash.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        return _password_hash.verify(plain_password, password_hash)
    except Exception:  # noqa: BLE001 - hash malformado nao deve derrubar o login
        return False


def _create_token(subject: str, token_type: TokenType, expires_delta: timedelta) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type.value,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(subject: uuid.UUID | str) -> str:
    return _create_token(
        str(subject),
        TokenType.ACCESS,
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(subject: uuid.UUID | str) -> str:
    return _create_token(
        str(subject),
        TokenType.REFRESH,
        timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_token(token: str, expected_type: TokenType) -> uuid.UUID:
    """Valida assinatura, expiracao e tipo do token, devolvendo o id do usuario."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except jwt.ExpiredSignatureError as exc:
        raise AuthenticationError("Sessao expirada. Faca login novamente.") from exc
    except jwt.PyJWTError as exc:
        raise AuthenticationError("Token invalido.") from exc

    if payload.get("type") != expected_type.value:
        raise AuthenticationError("Token invalido para esta operacao.")

    subject = payload.get("sub")
    if not subject:
        raise AuthenticationError("Token invalido.")

    try:
        return uuid.UUID(str(subject))
    except ValueError as exc:
        raise AuthenticationError("Token invalido.") from exc
