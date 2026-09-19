"""Registro, autenticacao e sessao do usuario."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, ConflictError, NotFoundError
from app.core.security import (
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.repositories.business import BusinessRepository
from app.repositories.user import UserRepository


@dataclass(frozen=True, slots=True)
class TokenPair:
    access_token: str
    refresh_token: str


@dataclass(frozen=True, slots=True)
class AuthenticatedSession:
    user: User
    tokens: TokenPair
    business_id: uuid.UUID | None


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.businesses = BusinessRepository(session)

    async def register(self, *, email: str, password: str, full_name: str) -> AuthenticatedSession:
        normalized_email = email.strip().lower()
        if await self.users.email_exists(normalized_email):
            raise ConflictError("Ja existe uma conta com este e-mail.")

        user = await self.users.add(
            User(
                email=normalized_email,
                password_hash=hash_password(password),
                full_name=full_name.strip(),
            )
        )
        return AuthenticatedSession(user=user, tokens=self._issue_tokens(user.id), business_id=None)

    async def authenticate(self, *, email: str, password: str) -> AuthenticatedSession:
        user = await self.users.get_by_email(email)

        # Mensagem unica para e-mail inexistente e senha errada: nao revela
        # quais e-mails estao cadastrados.
        if user is None or not verify_password(password, user.password_hash):
            raise AuthenticationError("E-mail ou senha incorretos.")
        if not user.is_active:
            raise AuthenticationError("Esta conta esta desativada.")

        business = await self.businesses.get_primary_for_user(user.id)
        return AuthenticatedSession(
            user=user,
            tokens=self._issue_tokens(user.id),
            business_id=business.id if business else None,
        )

    async def refresh(self, refresh_token: str) -> AuthenticatedSession:
        user_id = decode_token(refresh_token, TokenType.REFRESH)
        user = await self.users.get(user_id)
        if user is None or not user.is_active:
            raise AuthenticationError("Sessao invalida. Faca login novamente.")

        business = await self.businesses.get_primary_for_user(user.id)
        return AuthenticatedSession(
            user=user,
            tokens=self._issue_tokens(user.id),
            business_id=business.id if business else None,
        )

    async def change_password(
        self, user: User, *, current_password: str, new_password: str
    ) -> None:
        if not verify_password(current_password, user.password_hash):
            raise AuthenticationError("Senha atual incorreta.")
        user.password_hash = hash_password(new_password)
        await self.session.flush()

    async def update_profile(self, user: User, *, full_name: str | None) -> User:
        if full_name is not None:
            user.full_name = full_name.strip()
        await self.session.flush()
        return user

    async def get_user(self, user_id: uuid.UUID) -> User:
        user = await self.users.get(user_id)
        if user is None:
            raise NotFoundError("Usuario nao encontrado.")
        return user

    @staticmethod
    def _issue_tokens(user_id: uuid.UUID) -> TokenPair:
        return TokenPair(
            access_token=create_access_token(user_id),
            refresh_token=create_refresh_token(user_id),
        )
