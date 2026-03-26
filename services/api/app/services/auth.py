from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    create_bind_token,
    create_refresh_token,
    decode_bind_token,
    decode_refresh_token,
    hash_token,
    now_utc,
)
from app.core.settings import get_settings
from app.db.models import AuthSessionModel, ParentAccountModel, PhoneBindingModel
from app.models.contracts import AuthLoginResponse, AuthStatus, AuthTokens, ParentAccount
from app.services.mappers import parent_account_from_model


@dataclass(frozen=True)
class WechatIdentity:
    union_id: str
    open_id: str
    display_name: str
    avatar_url: str


class DevWechatIdentityProvider:
    def exchange(self, auth_code: str) -> WechatIdentity:
        suffix = auth_code.strip() or uuid4().hex[:8]
        normalized = suffix.replace(" ", "_")
        return WechatIdentity(
            union_id=f"wechat_union_{normalized}",
            open_id=f"wechat_open_{normalized}",
            display_name=f"微信家长{normalized[-4:]}",
            avatar_url="",
        )


class DevSmsProvider:
    def send_code(self, phone_number: str, otp_code: str) -> None:
        return None


class AuthService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.wechat_provider = DevWechatIdentityProvider()
        self.sms_provider = DevSmsProvider()

    def login_with_wechat(self, db: Session, auth_code: str, user_agent: str = "") -> AuthLoginResponse:
        identity = self.wechat_provider.exchange(auth_code)
        parent = db.scalar(
            select(ParentAccountModel).where(ParentAccountModel.wechat_union_id == identity.union_id)
        )
        if parent is None:
            parent = ParentAccountModel(
                display_name=identity.display_name,
                avatar_url=identity.avatar_url,
                wechat_union_id=identity.union_id,
                wechat_open_id=identity.open_id,
            )
            db.add(parent)
            db.commit()
            db.refresh(parent)
        else:
            parent.display_name = parent.display_name or identity.display_name
            parent.avatar_url = parent.avatar_url or identity.avatar_url
            parent.wechat_open_id = identity.open_id
            db.add(parent)
            db.commit()
            db.refresh(parent)

        if parent.phone_verified_at is None:
            bind_token, _ = create_bind_token(
                {
                    "parent_account_id": parent.id,
                    "wechat_union_id": identity.union_id,
                    "wechat_open_id": identity.open_id,
                    "display_name": parent.display_name,
                    "avatar_url": parent.avatar_url,
                }
            )
            return AuthLoginResponse(
                status=AuthStatus.phone_binding_required,
                parent_account=parent_account_from_model(parent),
                children=[],
                bind_token=bind_token,
            )

        tokens = self._create_session(db, parent.id, user_agent=user_agent)
        children = []
        return AuthLoginResponse(
            status=AuthStatus.authenticated,
            parent_account=parent_account_from_model(parent),
            children=children,
            tokens=tokens,
        )

    def request_phone_otp(self, db: Session, bind_token: str, phone_number: str) -> PhoneBindingModel:
        payload = decode_bind_token(bind_token)
        parent_id = payload["sub"]
        request = PhoneBindingModel(
            parent_account_id=parent_id,
            phone_number=phone_number,
            otp_code=self._generate_otp(),
            expires_at=now_utc() + timedelta(minutes=self.settings.otp_expiration_minutes),
        )
        db.add(request)
        db.commit()
        db.refresh(request)
        self.sms_provider.send_code(phone_number, request.otp_code)
        return request

    def bind_phone(self, db: Session, bind_token: str, phone_number: str, otp_code: str, user_agent: str = "") -> tuple[ParentAccountModel, AuthTokens]:
        payload = decode_bind_token(bind_token)
        parent_id = payload["sub"]
        parent = db.get(ParentAccountModel, parent_id)
        if parent is None:
            raise ValueError("Parent account not found")

        binding = db.scalar(
            select(PhoneBindingModel)
            .where(
                PhoneBindingModel.parent_account_id == parent_id,
                PhoneBindingModel.phone_number == phone_number,
                PhoneBindingModel.verified_at.is_(None),
            )
            .order_by(PhoneBindingModel.created_at.desc())
        )
        if binding is None:
            raise ValueError("OTP request not found")
        if _as_utc(binding.expires_at) < now_utc():
            raise ValueError("OTP expired")
        if binding.otp_code != otp_code:
            raise ValueError("OTP code mismatch")

        binding.verified_at = now_utc()
        parent.phone_number = phone_number
        parent.phone_verified_at = now_utc()
        db.add_all([binding, parent])
        db.commit()
        db.refresh(parent)
        tokens = self._create_session(db, parent.id, user_agent=user_agent)
        return parent, tokens

    def refresh_session(self, db: Session, refresh_token: str) -> tuple[ParentAccountModel, AuthTokens]:
        payload = decode_refresh_token(refresh_token)
        session_id = payload["sid"]
        parent_id = payload["sub"]
        session = db.get(AuthSessionModel, session_id)
        if session is None or session.revoked:
            raise ValueError("Session not found")
        if _as_utc(session.refresh_expires_at) < now_utc():
            raise ValueError("Refresh token expired")
        if session.refresh_token_hash != hash_token(refresh_token):
            raise ValueError("Refresh token mismatch")
        parent = db.get(ParentAccountModel, parent_id)
        if parent is None:
            raise ValueError("Parent account not found")
        tokens = self._rotate_session_tokens(db, session, phone_verified=parent.phone_verified_at is not None)
        return parent, tokens

    def logout(self, db: Session, refresh_token: str) -> None:
        payload = decode_refresh_token(refresh_token)
        session = db.get(AuthSessionModel, payload["sid"])
        if session is not None:
            session.revoked = True
            db.add(session)
            db.commit()

    def _create_session(self, db: Session, parent_id: str, user_agent: str = "") -> AuthTokens:
        session = AuthSessionModel(
            parent_account_id=parent_id,
            refresh_token_hash="pending",
            user_agent=user_agent,
            access_expires_at=now_utc(),
            refresh_expires_at=now_utc(),
        )
        db.add(session)
        db.flush()
        tokens = self._rotate_session_tokens(db, session, phone_verified=True)
        db.refresh(session)
        return tokens

    def _rotate_session_tokens(self, db: Session, session: AuthSessionModel, phone_verified: bool) -> AuthTokens:
        access_token, access_expires_at = create_access_token(session.parent_account_id, session.id, phone_verified)
        refresh_token, refresh_expires_at = create_refresh_token(session.parent_account_id, session.id)
        session.refresh_token_hash = hash_token(refresh_token)
        session.access_expires_at = access_expires_at
        session.refresh_expires_at = refresh_expires_at
        db.add(session)
        db.commit()
        return AuthTokens(
            access_token=access_token,
            refresh_token=refresh_token,
            access_token_expires_at=access_expires_at,
            refresh_token_expires_at=refresh_expires_at,
        )

    def _generate_otp(self) -> str:
        if self.settings.app_env == "production":
            return str(uuid4().int)[-6:]
        return "123456"


def parent_contract(parent: ParentAccountModel) -> ParentAccount:
    return parent_account_from_model(parent)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
