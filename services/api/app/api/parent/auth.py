from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_parent
from app.core.config import get_auth_service
from app.core.db import get_db
from app.core.settings import get_settings
from app.db.models import ChildProfileModel, ParentAccountModel
from app.models.contracts import (
    AuthLoginResponse,
    AuthStatus,
    MeResponse,
    PhoneBindRequest,
    PhoneOtpRequest,
    PhoneOtpResponse,
    RefreshTokenRequest,
    WechatLoginRequest,
)
from app.services.parent.auth import AuthService
from app.services.shared.mappers import child_profile_from_model, parent_account_from_model

router = APIRouter(prefix="/auth", tags=["auth"])
me_router = APIRouter(tags=["auth"])


@router.post("/wechat/login", response_model=AuthLoginResponse)
def login_with_wechat(
    payload: WechatLoginRequest,
    request: Request,
    db: Session = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthLoginResponse:
    return auth_service.login_with_wechat(
        db,
        payload.auth_code,
        user_agent=request.headers.get("user-agent", ""),
    )


@router.post("/phone/request-otp", response_model=PhoneOtpResponse)
def request_phone_otp(
    payload: PhoneOtpRequest,
    db: Session = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
) -> PhoneOtpResponse:
    try:
        request = auth_service.request_phone_otp(db, payload.bind_token, payload.phone_number)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    debug_code = request.otp_code if get_settings().app_env != "production" else None
    return PhoneOtpResponse(request_id=request.id, expires_at=request.expires_at, debug_code=debug_code)


@router.post("/phone/bind", response_model=AuthLoginResponse)
def bind_phone(
    payload: PhoneBindRequest,
    request: Request,
    db: Session = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthLoginResponse:
    try:
        parent, tokens = auth_service.bind_phone(
            db,
            bind_token=payload.bind_token,
            phone_number=payload.phone_number,
            otp_code=payload.otp_code,
            user_agent=request.headers.get("user-agent", ""),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    children = db.scalars(
        select(ChildProfileModel).where(ChildProfileModel.parent_account_id == parent.id).order_by(ChildProfileModel.created_at)
    ).all()
    return AuthLoginResponse(
        status=AuthStatus.authenticated,
        parent_account=parent_account_from_model(parent),
        children=[child_profile_from_model(item) for item in children],
        tokens=tokens,
    )


@router.post("/refresh", response_model=AuthLoginResponse)
def refresh_session(
    payload: RefreshTokenRequest,
    db: Session = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthLoginResponse:
    try:
        parent, tokens = auth_service.refresh_session(db, payload.refresh_token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    children = db.scalars(
        select(ChildProfileModel).where(ChildProfileModel.parent_account_id == parent.id).order_by(ChildProfileModel.created_at)
    ).all()
    return AuthLoginResponse(
        status=AuthStatus.authenticated,
        parent_account=parent_account_from_model(parent),
        children=[child_profile_from_model(item) for item in children],
        tokens=tokens,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    payload: RefreshTokenRequest,
    db: Session = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
) -> None:
    auth_service.logout(db, payload.refresh_token)
    return None


@router.get("/me", response_model=MeResponse)
def get_me(
    current_parent: ParentAccountModel = Depends(get_current_parent),
    db: Session = Depends(get_db),
) -> MeResponse:
    children = db.scalars(
        select(ChildProfileModel).where(ChildProfileModel.parent_account_id == current_parent.id).order_by(ChildProfileModel.created_at)
    ).all()
    return MeResponse(
        parent_account=parent_account_from_model(current_parent),
        children=[child_profile_from_model(item) for item in children],
    )


@me_router.get("/me", response_model=MeResponse)
def get_me_alias(
    current_parent: ParentAccountModel = Depends(get_current_parent),
    db: Session = Depends(get_db),
) -> MeResponse:
    return get_me(current_parent=current_parent, db=db)
