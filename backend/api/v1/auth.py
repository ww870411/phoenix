"""
认证相关 API。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Header, status

from backend.schemas.auth import (
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    SessionResponse,
)
from backend.services.auth_manager import AuthSession, auth_manager, get_current_session


router = APIRouter(tags=["auth"])


@router.post("/login", response_model=LoginResponse, summary="登录并获取访问令牌")
def login(payload: LoginRequest) -> LoginResponse:
    session = auth_manager.login(payload.username, payload.password, remember=payload.remember_me)
    permissions = session.to_permissions_payload()
    user_payload = session.to_user_payload()
    expires_in = (
        int((session.expires_at - session.issued_at).total_seconds())
        if session.expires_at
        else -1
    )
    return LoginResponse(
        access_token=session.token,
        expires_in=expires_in,
        user=user_payload,
        permissions=permissions,
    )


@router.post("/logout", response_model=LogoutResponse, summary="退出登录")
def logout(authorization: str = Header(None, alias="Authorization")) -> LogoutResponse:
    if authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            auth_manager.logout(parts[1])
    return LogoutResponse()


@router.get("/me", response_model=SessionResponse, summary="获取当前登录用户信息")
def read_current_session(session: AuthSession = Depends(get_current_session)) -> SessionResponse:
    return SessionResponse(
        user=session.to_user_payload(),
        permissions=session.to_permissions_payload(),
    )
