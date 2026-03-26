from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

import jwt

from app.core.settings import get_settings


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def hash_token(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _encode(payload: dict[str, Any]) -> str:
    settings = get_settings()
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def _decode(token: str) -> dict[str, Any]:
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])


def create_bind_token(payload: dict[str, Any]) -> tuple[str, datetime]:
    settings = get_settings()
    expires_at = now_utc() + timedelta(minutes=settings.bind_token_minutes)
    token = _encode(
        {
            "sub": payload["parent_account_id"],
            "type": "bind",
            "wechat_union_id": payload["wechat_union_id"],
            "wechat_open_id": payload["wechat_open_id"],
            "display_name": payload["display_name"],
            "avatar_url": payload.get("avatar_url", ""),
            "exp": expires_at,
        }
    )
    return token, expires_at


def decode_bind_token(token: str) -> dict[str, Any]:
    payload = _decode(token)
    if payload.get("type") != "bind":
        raise ValueError("Invalid bind token")
    return payload


def create_access_token(parent_account_id: str, session_id: str, phone_verified: bool) -> tuple[str, datetime]:
    settings = get_settings()
    expires_at = now_utc() + timedelta(minutes=settings.access_token_minutes)
    token = _encode(
        {
            "sub": parent_account_id,
            "sid": session_id,
            "type": "access",
            "phone_verified": phone_verified,
            "exp": expires_at,
        }
    )
    return token, expires_at


def create_refresh_token(parent_account_id: str, session_id: str) -> tuple[str, datetime]:
    settings = get_settings()
    expires_at = now_utc() + timedelta(days=settings.refresh_token_days)
    token = _encode(
        {
            "sub": parent_account_id,
            "sid": session_id,
            "jti": f"refresh_{uuid4().hex}",
            "type": "refresh",
            "exp": expires_at,
        }
    )
    return token, expires_at


def decode_access_token(token: str) -> dict[str, Any]:
    payload = _decode(token)
    if payload.get("type") != "access":
        raise ValueError("Invalid access token")
    return payload


def decode_refresh_token(token: str) -> dict[str, Any]:
    payload = _decode(token)
    if payload.get("type") != "refresh":
        raise ValueError("Invalid refresh token")
    return payload
