from __future__ import annotations

import hashlib
import json

from app.core.settings import get_settings
from conftest import configure_test_environment


configure_test_environment("learning-english-api-admin-phase2-")


def _token_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _set_admin_credentials(monkeypatch, credentials: list[dict]) -> None:
    monkeypatch.setenv("ADMIN_API_CREDENTIALS_JSON", json.dumps(credentials))
    monkeypatch.delenv("ADMIN_API_TOKEN", raising=False)
    get_settings.cache_clear()


def test_admin_credentials_resolve_actor_and_exact_permissions(api_client, monkeypatch) -> None:
    _set_admin_credentials(
        monkeypatch,
        [
            {
                "id": "admin_readonly",
                "display_name": "Read Only Admin",
                "email": "readonly@example.com",
                "role": "Support Viewer",
                "status": "active",
                "permissions": ["admin.dashboard.read", "admin.audit.read"],
                "token_sha256": _token_hash("readonly-token"),
            },
            {
                "id": "admin_ops",
                "display_name": "Ops Admin",
                "email": "ops@example.com",
                "role": "Operations",
                "status": "active",
                "permissions": ["admin.dashboard.read", "admin.audit.read", "admin.provider.override"],
                "token_sha256": _token_hash("ops-token"),
            },
        ],
    )

    response = api_client.get(
        "/v1/admin/access?tenant_scope=all",
        headers={"X-Admin-Token": "readonly-token"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["current_admin"] == {
        "id": "admin_readonly",
        "display_name": "Read Only Admin",
        "email": "readonly@example.com",
        "role": "Support Viewer",
        "status": "active",
    }
    assert payload["permissions"] == ["admin.dashboard.read", "admin.audit.read"]
    assert "readonly-token" not in str(payload)

    ops_response = api_client.get(
        "/v1/admin/access?tenant_scope=all",
        headers={"X-Admin-Token": "ops-token"},
    )

    assert ops_response.status_code == 200
    ops_payload = ops_response.json()
    assert ops_payload["current_admin"] == {
        "id": "admin_ops",
        "display_name": "Ops Admin",
        "email": "ops@example.com",
        "role": "Operations",
        "status": "active",
    }
    assert ops_payload["permissions"] == ["admin.dashboard.read", "admin.audit.read", "admin.provider.override"]
    assert "ops-token" not in str(ops_payload)


def test_read_only_admin_token_is_forbidden_from_provider_override(api_client, monkeypatch) -> None:
    _set_admin_credentials(
        monkeypatch,
        [
            {
                "id": "admin_readonly",
                "display_name": "Read Only Admin",
                "email": "readonly@example.com",
                "role": "Support Viewer",
                "status": "active",
                "permissions": ["admin.dashboard.read", "admin.audit.read"],
                "token_sha256": _token_hash("readonly-token"),
            }
        ],
    )

    response = api_client.post(
        "/v1/admin/providers/policies?tenant_scope=all",
        json={
            "tenant_id": "tenant_missing",
            "ai_provider": "doubao",
            "media_provider": "real",
            "fallback_mode": "per_tenant",
            "monthly_guardrail": 500,
            "reason": "Read-only admin must not mutate provider policy.",
        },
        headers={"X-Admin-Token": "readonly-token"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Missing admin.provider.override permission"


def test_inactive_admin_credential_is_rejected(api_client, monkeypatch) -> None:
    _set_admin_credentials(
        monkeypatch,
        [
            {
                "id": "admin_disabled",
                "display_name": "Disabled Admin",
                "email": "disabled@example.com",
                "role": "Operations",
                "status": "disabled",
                "permissions": ["admin.dashboard.read"],
                "token_sha256": _token_hash("disabled-token"),
            }
        ],
    )

    response = api_client.get(
        "/v1/admin/dashboard?tenant_scope=all",
        headers={"X-Admin-Token": "disabled-token"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin user is inactive"


def test_configured_admin_credentials_reject_non_matching_token(api_client, monkeypatch) -> None:
    _set_admin_credentials(
        monkeypatch,
        [
            {
                "id": "admin_ops",
                "display_name": "Ops Admin",
                "email": "ops@example.com",
                "role": "Operations",
                "permissions": ["admin.dashboard.read"],
                "token_sha256": _token_hash("ops-token"),
            }
        ],
    )

    response = api_client.get(
        "/v1/admin/dashboard?tenant_scope=all",
        headers={"X-Admin-Token": "local-admin-token"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Invalid admin token"


def test_invalid_admin_credentials_json_returns_service_unavailable(api_client, monkeypatch) -> None:
    monkeypatch.setenv("ADMIN_API_CREDENTIALS_JSON", "{not-json")
    monkeypatch.delenv("ADMIN_API_TOKEN", raising=False)
    get_settings.cache_clear()

    response = api_client.get(
        "/v1/admin/dashboard?tenant_scope=all",
        headers={"X-Admin-Token": "readonly-token"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Admin credentials are invalid"
