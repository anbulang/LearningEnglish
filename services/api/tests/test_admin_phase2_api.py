from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from app.core.db import SessionLocal
from app.core.settings import get_settings
from app.db.models import AdminAuditEventModel
from conftest import configure_test_environment


configure_test_environment("learning-english-api-admin-phase2-")


def _token_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _set_admin_credentials(monkeypatch, credentials: list[dict]) -> None:
    monkeypatch.setenv("ADMIN_API_CREDENTIALS_JSON", json.dumps(credentials))
    monkeypatch.delenv("ADMIN_API_TOKEN", raising=False)
    get_settings.cache_clear()


def _seed_audit_event(
    *,
    audit_id: str,
    actor_id: str = "admin_ops",
    actor_role: str = "Operations",
    tenant_scope: str = "tenant_task2_a",
    action: str = "admin.material.archive",
    resource_type: str = "course_material",
    resource_id: str = "material_task2",
    risk_level: str = "high",
    result: str = "success",
    created_at: datetime,
) -> None:
    with SessionLocal() as db:
        db.add(
            AdminAuditEventModel(
                id=audit_id,
                actor_id=actor_id,
                actor_role=actor_role,
                tenant_scope=tenant_scope,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                risk_level=risk_level,
                result=result,
                reason="Task 2 audit search fixture",
                trace_id=f"req_{audit_id}",
                content_json={},
                created_at=created_at,
            )
        )
        db.commit()


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


def test_admin_dashboard_requires_dashboard_read_permission(api_client, monkeypatch) -> None:
    _set_admin_credentials(
        monkeypatch,
        [
            {
                "id": "admin_audit_only",
                "display_name": "Audit Only Admin",
                "email": "audit-only@example.com",
                "role": "Audit Viewer",
                "status": "active",
                "permissions": ["admin.audit.read"],
                "token_sha256": _token_hash("audit-only-token"),
            }
        ],
    )

    response = api_client.get(
        "/v1/admin/dashboard?tenant_scope=all",
        headers={"X-Admin-Token": "audit-only-token"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Missing admin.dashboard.read permission"


def test_admin_access_requires_audit_read_permission(api_client, monkeypatch) -> None:
    _set_admin_credentials(
        monkeypatch,
        [
            {
                "id": "admin_dashboard_only",
                "display_name": "Dashboard Only Admin",
                "email": "dashboard-only@example.com",
                "role": "Dashboard Viewer",
                "status": "active",
                "permissions": ["admin.dashboard.read"],
                "token_sha256": _token_hash("dashboard-only-token"),
            }
        ],
    )

    response = api_client.get(
        "/v1/admin/access?tenant_scope=all",
        headers={"X-Admin-Token": "dashboard-only-token"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Missing admin.audit.read permission"


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


def test_admin_audit_events_filter_by_scope_fields_and_paginate_after_cursor(api_client, monkeypatch) -> None:
    _set_admin_credentials(
        monkeypatch,
        [
            {
                "id": "admin_ops",
                "display_name": "Ops Admin",
                "email": "ops@example.com",
                "role": "Operations",
                "status": "active",
                "permissions": ["admin.audit.read"],
                "token_sha256": _token_hash("ops-token"),
            }
        ],
    )
    created_at = datetime(2026, 5, 28, 12, 0, tzinfo=timezone.utc)
    for audit_id, tenant_scope in (
        ("audit_task2_001", "tenant_task2_a"),
        ("audit_task2_002", "tenant_task2_a"),
        ("audit_task2_003", "all"),
    ):
        _seed_audit_event(audit_id=audit_id, tenant_scope=tenant_scope, created_at=created_at)
    _seed_audit_event(audit_id="audit_task2_004", action="admin.dashboard.read", created_at=created_at)
    _seed_audit_event(audit_id="audit_task2_005", result="failed", created_at=created_at)
    _seed_audit_event(audit_id="audit_task2_006", actor_id="admin_other", created_at=created_at)
    _seed_audit_event(audit_id="audit_task2_007", tenant_scope="tenant_task2_b", created_at=created_at)
    _seed_audit_event(audit_id="audit_task2_008", resource_type="tenant_provider_policy", created_at=created_at)
    _seed_audit_event(audit_id="audit_task2_009", risk_level="low", created_at=created_at)

    first_page = api_client.get(
        "/v1/admin/audit-events",
        params={
            "tenant_scope": "tenant_task2_a",
            "action": "admin.material.archive",
            "resource_type": "course_material",
            "risk_level": "high",
            "result": "success",
            "actor_id": "admin_ops",
            "limit": "2",
        },
        headers={"X-Admin-Token": "ops-token"},
    )

    assert first_page.status_code == 200
    first_payload = first_page.json()
    assert [item["id"] for item in first_payload["items"]] == ["audit_task2_003", "audit_task2_002"]
    assert first_payload["next_cursor"] == "audit_task2_002"
    assert {item["tenant_scope"] for item in first_payload["items"]} == {"all", "tenant_task2_a"}

    second_page = api_client.get(
        "/v1/admin/audit-events",
        params={
            "tenant_scope": "tenant_task2_a",
            "action": "admin.material.archive",
            "resource_type": "course_material",
            "risk_level": "high",
            "result": "success",
            "actor_id": "admin_ops",
            "limit": "2",
            "cursor": first_payload["next_cursor"],
        },
        headers={"X-Admin-Token": "ops-token"},
    )

    assert second_page.status_code == 200
    second_payload = second_page.json()
    assert [item["id"] for item in second_payload["items"]] == ["audit_task2_001"]
    assert second_payload["next_cursor"] == ""


def test_admin_audit_events_return_empty_page_for_missing_cursor(api_client, monkeypatch) -> None:
    _set_admin_credentials(
        monkeypatch,
        [
            {
                "id": "admin_ops",
                "display_name": "Ops Admin",
                "email": "ops@example.com",
                "role": "Operations",
                "status": "active",
                "permissions": ["admin.audit.read"],
                "token_sha256": _token_hash("ops-token"),
            }
        ],
    )
    _seed_audit_event(
        audit_id="audit_task2_cursor_existing",
        tenant_scope="tenant_task2_a",
        created_at=datetime(2026, 5, 28, 12, 0, tzinfo=timezone.utc),
    )

    response = api_client.get(
        "/v1/admin/audit-events",
        params={"tenant_scope": "all", "cursor": "audit_task2_missing"},
        headers={"X-Admin-Token": "ops-token"},
    )

    assert response.status_code == 200
    assert response.json() == {"items": [], "next_cursor": ""}


def test_admin_audit_events_clamp_limit_below_one_to_single_item(api_client, monkeypatch) -> None:
    _set_admin_credentials(
        monkeypatch,
        [
            {
                "id": "admin_limit_floor",
                "display_name": "Limit Floor Admin",
                "email": "limit-floor@example.com",
                "role": "Audit Viewer",
                "status": "active",
                "permissions": ["admin.audit.read"],
                "token_sha256": _token_hash("limit-floor-token"),
            }
        ],
    )
    created_at = datetime(2026, 5, 28, 13, 0, tzinfo=timezone.utc)
    for index in range(2):
        _seed_audit_event(
            audit_id=f"audit_task2_limit_floor_{index:03d}",
            actor_id="admin_limit_floor",
            tenant_scope="tenant_task2_limit_floor",
            action="admin.task2.limit_floor",
            resource_type="admin_audit_event",
            risk_level="low",
            created_at=created_at,
        )

    response = api_client.get(
        "/v1/admin/audit-events",
        params={
            "tenant_scope": "tenant_task2_limit_floor",
            "action": "admin.task2.limit_floor",
            "actor_id": "admin_limit_floor",
            "limit": "0",
        },
        headers={"X-Admin-Token": "limit-floor-token"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) == 1
    assert payload["next_cursor"]


def test_admin_audit_events_clamp_limit_above_one_hundred(api_client, monkeypatch) -> None:
    _set_admin_credentials(
        monkeypatch,
        [
            {
                "id": "admin_limit_ceiling",
                "display_name": "Limit Ceiling Admin",
                "email": "limit-ceiling@example.com",
                "role": "Audit Viewer",
                "status": "active",
                "permissions": ["admin.audit.read"],
                "token_sha256": _token_hash("limit-ceiling-token"),
            }
        ],
    )
    created_at = datetime(2026, 5, 28, 14, 0, tzinfo=timezone.utc)
    for index in range(101):
        _seed_audit_event(
            audit_id=f"audit_task2_limit_ceiling_{index:03d}",
            actor_id="admin_limit_ceiling",
            tenant_scope="tenant_task2_limit_ceiling",
            action="admin.task2.limit_ceiling",
            resource_type="admin_audit_event",
            risk_level="low",
            created_at=created_at,
        )

    response = api_client.get(
        "/v1/admin/audit-events",
        params={
            "tenant_scope": "tenant_task2_limit_ceiling",
            "action": "admin.task2.limit_ceiling",
            "actor_id": "admin_limit_ceiling",
            "limit": "101",
        },
        headers={"X-Admin-Token": "limit-ceiling-token"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) == 100
    assert payload["next_cursor"]


def test_admin_audit_events_require_audit_read_permission(api_client, monkeypatch) -> None:
    _set_admin_credentials(
        monkeypatch,
        [
            {
                "id": "admin_viewer",
                "display_name": "Viewer",
                "email": "viewer@example.com",
                "role": "Viewer",
                "status": "active",
                "permissions": ["admin.dashboard.read"],
                "token_sha256": _token_hash("viewer-token"),
            }
        ],
    )

    response = api_client.get(
        "/v1/admin/audit-events?tenant_scope=all",
        headers={"X-Admin-Token": "viewer-token"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Missing admin.audit.read permission"
