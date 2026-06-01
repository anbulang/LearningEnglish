from __future__ import annotations

import hashlib
import json

from app.services.admin.identity import admin_token_hash, resolve_admin_actor


class _Settings:
    admin_api_token = ""
    admin_api_credentials_json = ""


def _hash(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def test_resolve_admin_actor_from_credentials_json() -> None:
    settings = _Settings()
    settings.admin_api_credentials_json = json.dumps(
        [
            {
                "id": "admin_ops",
                "display_name": "Ops Admin",
                "email": "ops@example.com",
                "role": "Operations",
                "status": "active",
                "permissions": ["admin.dashboard.read", "admin.operations.read"],
                "token_sha256": _hash("ops-token"),
            }
        ]
    )

    actor = resolve_admin_actor(settings, "ops-token")

    assert actor is not None
    assert actor.id == "admin_ops"
    assert actor.display_name == "Ops Admin"
    assert actor.permissions == ["admin.dashboard.read", "admin.operations.read"]


def test_resolve_admin_actor_rejects_inactive_credential() -> None:
    settings = _Settings()
    settings.admin_api_credentials_json = json.dumps(
        [
            {
                "id": "admin_disabled",
                "display_name": "Disabled",
                "email": "disabled@example.com",
                "role": "Operations",
                "status": "disabled",
                "permissions": ["admin.dashboard.read"],
                "token_sha256": _hash("disabled-token"),
            }
        ]
    )

    actor = resolve_admin_actor(settings, "disabled-token")

    assert actor is None


def test_resolve_admin_actor_uses_local_token_fallback() -> None:
    settings = _Settings()
    settings.admin_api_token = "local-admin-token"

    actor = resolve_admin_actor(settings, "local-admin-token")

    assert actor is not None
    assert actor.id == "admin_local"
    assert "admin.dashboard.read" in actor.permissions


def test_admin_token_hash_is_sha256_hex() -> None:
    assert admin_token_hash("local-admin-token") == _hash("local-admin-token")
