from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from typing import Any, Protocol

from fastapi import HTTPException, status
from pydantic import BaseModel, Field

from app.services.admin_permissions import ADMIN_PERMISSIONS


class AdminSettings(Protocol):
    admin_api_token: str
    admin_api_credentials_json: str


@dataclass(frozen=True)
class AdminActor:
    id: str
    display_name: str
    email: str
    role: str
    status: str
    permissions: list[str]


class AdminCredential(BaseModel):
    id: str
    display_name: str
    email: str
    role: str
    status: str = "active"
    permissions: list[str] = Field(default_factory=list)
    token_sha256: str


def admin_token_hash(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def resolve_admin_actor(settings: AdminSettings, raw_token: str, *, include_inactive: bool = False) -> AdminActor | None:
    credentials = _configured_admin_credentials(settings.admin_api_credentials_json)
    if credentials is not None:
        token_sha256 = admin_token_hash(raw_token)
        for credential in credentials:
            credential_hash = credential.token_sha256.strip().lower()
            if not hmac.compare_digest(token_sha256, credential_hash):
                continue
            if credential.status != "active" and not include_inactive:
                return None
            return AdminActor(
                id=credential.id,
                display_name=credential.display_name,
                email=credential.email,
                role=credential.role,
                status=credential.status,
                permissions=list(credential.permissions),
            )
        return None

    if not settings.admin_api_token:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Admin API token is not configured")
    if not hmac.compare_digest(raw_token, settings.admin_api_token):
        return None
    return _local_admin_actor()


def _configured_admin_credentials(credentials_json: str) -> list[AdminCredential] | None:
    if not credentials_json:
        return None
    try:
        raw_credentials: Any = json.loads(credentials_json)
        if not isinstance(raw_credentials, list):
            raise ValueError("admin credentials must be a list")
        return [AdminCredential.model_validate(item) for item in raw_credentials]
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Admin credentials are invalid")


def _local_admin_actor() -> AdminActor:
    return AdminActor(
        id="admin_local",
        display_name="Local Platform Admin",
        email="admin@learningenglish.local",
        role="Platform Owner",
        status="active",
        permissions=list(ADMIN_PERMISSIONS),
    )
