"""Endpoints de autenticacao."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status

from app.core.deps import (
    CurrentUser,
    DbSession,
    clear_auth_cookies,
    get_refresh_token,
    set_auth_cookies,
)
from app.repositories.business import BusinessRepository
from app.schemas.auth import (
    LoginRequest,
    PasswordChangeRequest,
    RegisterRequest,
    SessionResponse,
    UserRead,
    UserUpdate,
)
from app.schemas.common import MessageResponse
from app.services.auth_service import AuthService, AuthenticatedSession

router = APIRouter(prefix="/auth", tags=["auth"])


def _session_response(response: Response, session: AuthenticatedSession) -> SessionResponse:
    set_auth_cookies(
        response,
        access_token=session.tokens.access_token,
        refresh_token=session.tokens.refresh_token,
    )
    return SessionResponse(
        user=UserRead.model_validate(session.user),
        business_id=session.business_id,
        has_business=session.business_id is not None,
    )


@router.post("/register", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest, response: Response, session: DbSession
) -> SessionResponse:
    result = await AuthService(session).register(
        email=payload.email,
        password=payload.password,
        full_name=payload.full_name,
    )
    return _session_response(response, result)


@router.post("/login", response_model=SessionResponse)
async def login(
    payload: LoginRequest, response: Response, session: DbSession
) -> SessionResponse:
    result = await AuthService(session).authenticate(
        email=payload.email, password=payload.password
    )
    return _session_response(response, result)


@router.post("/refresh", response_model=SessionResponse)
async def refresh(
    response: Response,
    session: DbSession,
    refresh_token: str = Depends(get_refresh_token),
) -> SessionResponse:
    result = await AuthService(session).refresh(refresh_token)
    return _session_response(response, result)


@router.post("/logout", response_model=MessageResponse)
async def logout(response: Response) -> MessageResponse:
    clear_auth_cookies(response)
    return MessageResponse(message="Sessao encerrada.")


@router.get("/me", response_model=SessionResponse)
async def me(user: CurrentUser, session: DbSession) -> SessionResponse:
    business = await BusinessRepository(session).get_primary_for_user(user.id)
    return SessionResponse(
        user=UserRead.model_validate(user),
        business_id=business.id if business else None,
        has_business=business is not None,
    )


@router.patch("/me", response_model=UserRead)
async def update_me(payload: UserUpdate, user: CurrentUser, session: DbSession) -> UserRead:
    updated = await AuthService(session).update_profile(user, full_name=payload.full_name)
    return UserRead.model_validate(updated)


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    payload: PasswordChangeRequest,
    user: CurrentUser,
    session: DbSession,
    response: Response,
) -> MessageResponse:
    await AuthService(session).change_password(
        user,
        current_password=payload.current_password,
        new_password=payload.new_password,
    )
    # Forca novo login: os tokens antigos continuariam validos ate expirar.
    clear_auth_cookies(response)
    return MessageResponse(message="Senha alterada. Faca login novamente.")
