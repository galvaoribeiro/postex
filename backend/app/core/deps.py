"""Dependencias compartilhadas dos endpoints.

Aqui vive a autorizacao. `get_current_user` resolve a sessao a partir do cookie
httpOnly e `get_current_business` garante, uma vez por request, que o negocio
acessado pertence ao usuario autenticado. Os endpoints recebem o `Business` ja
verificado e os repositories exigem `business_id`, entao nao existe caminho em
que dados de outra conta possam ser lidos.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, Header, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_session
from app.core.exceptions import AuthenticationError, NotFoundError
from app.core.security import TokenType, decode_token
from app.models.business import Business
from app.models.user import User
from app.repositories.business import BusinessRepository
from app.repositories.user import UserRepository

ACCESS_TOKEN_COOKIE = "mdc_access_token"
REFRESH_TOKEN_COOKIE = "mdc_refresh_token"


def set_auth_cookies(response: Response, *, access_token: str, refresh_token: str) -> None:
    """Grava os tokens em cookies httpOnly.

    httpOnly mantem os tokens fora do alcance de JavaScript, o que neutraliza o
    roubo de sessao por XSS - diferente de guardar em localStorage.
    """
    common = {
        "httponly": True,
        "secure": settings.COOKIE_SECURE,
        "samesite": settings.COOKIE_SAMESITE,
        "domain": settings.COOKIE_DOMAIN,
        "path": "/",
    }
    response.set_cookie(
        ACCESS_TOKEN_COOKIE,
        access_token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        **common,
    )
    response.set_cookie(
        REFRESH_TOKEN_COOKIE,
        refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        **common,
    )


def clear_auth_cookies(response: Response) -> None:
    for name in (ACCESS_TOKEN_COOKIE, REFRESH_TOKEN_COOKIE):
        response.delete_cookie(
            name,
            path="/",
            domain=settings.COOKIE_DOMAIN,
            secure=settings.COOKIE_SECURE,
            httponly=True,
            samesite=settings.COOKIE_SAMESITE,
        )


def get_refresh_token(request: Request) -> str:
    token = request.cookies.get(REFRESH_TOKEN_COOKIE)
    if not token:
        raise AuthenticationError("Sessao nao encontrada. Faca login novamente.")
    return token


DbSession = Annotated[AsyncSession, Depends(get_session)]


async def get_current_user(request: Request, session: DbSession) -> User:
    token = request.cookies.get(ACCESS_TOKEN_COOKIE)
    if not token:
        raise AuthenticationError("Autenticacao necessaria.")

    user_id = decode_token(token, TokenType.ACCESS)
    user = await UserRepository(session).get(user_id)
    if user is None or not user.is_active:
        raise AuthenticationError("Sessao invalida. Faca login novamente.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_current_business(
    session: DbSession,
    user: CurrentUser,
    x_business_id: Annotated[str | None, Header(alias="X-Business-Id")] = None,
) -> Business:
    """Resolve o negocio do request.

    Sem o header `X-Business-Id`, usa o negocio principal da conta - o caminho
    normal da interface atual. Com o header, valida a posse antes de devolver,
    o que mantem o suporte a multiplos negocios sem abrir brecha.
    """
    repository = BusinessRepository(session)

    if x_business_id:
        try:
            business_id = uuid.UUID(x_business_id)
        except ValueError as exc:
            raise NotFoundError("Negocio nao encontrado.") from exc

        business = await repository.get_for_user(user.id, business_id)
        if business is None:
            # 404 em vez de 403: nao confirma a existencia de negocios alheios.
            raise NotFoundError("Negocio nao encontrado.")
        return business

    business = await repository.get_primary_for_user(user.id)
    if business is None:
        raise NotFoundError(
            "Nenhum negocio cadastrado. Cadastre o seu negocio para comecar."
        )
    return business


CurrentBusiness = Annotated[Business, Depends(get_current_business)]
