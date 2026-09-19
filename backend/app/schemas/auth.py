"""Schemas de autenticacao e do usuario."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import EmailStr, Field, field_validator

from app.schemas.common import APIModel, APIRequest

MIN_PASSWORD_LENGTH = 8


class RegisterRequest(APIRequest):
    email: EmailStr
    password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=128)
    full_name: str = Field(min_length=2, max_length=160)

    @field_validator("password")
    @classmethod
    def _password_strength(cls, value: str) -> str:
        if value.isdigit() or value.isalpha():
            raise ValueError("A senha deve combinar letras e numeros.")
        return value


class LoginRequest(APIRequest):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserRead(APIModel):
    id: uuid.UUID
    email: str
    full_name: str
    is_active: bool
    created_at: datetime


class UserUpdate(APIRequest):
    full_name: str | None = Field(default=None, min_length=2, max_length=160)


class PasswordChangeRequest(APIRequest):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=128)


class SessionResponse(APIModel):
    """Resposta de login/registro.

    Os tokens nao aparecem aqui de proposito: eles sao entregues em cookies
    httpOnly, inacessiveis ao JavaScript. O corpo traz apenas o que a interface
    precisa para se montar.
    """

    user: UserRead
    business_id: uuid.UUID | None = None
    has_business: bool = False
