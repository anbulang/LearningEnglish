from __future__ import annotations

from conftest import auth_headers, configure_test_environment


configure_test_environment("learning-english-api-admin-read-")

ADMIN_HEADERS = {"X-Admin-Token": "local-admin-token"}


def test_admin_dashboard_requires_admin_token_and_explicit_tenant_scope(api_client) -> None:
    missing_token = api_client.get("/v1/admin/dashboard?tenant_scope=all")
    assert missing_token.status_code == 401
    assert missing_token.json()["detail"] == "Missing admin token"

    missing_scope = api_client.get("/v1/admin/dashboard", headers=ADMIN_HEADERS)
    assert missing_scope.status_code == 422


def test_admin_dashboard_allows_local_admin_cors_preflight(api_client) -> None:
    response = api_client.options(
        "/v1/admin/dashboard?tenant_scope=all",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "X-Admin-Token",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
    assert "X-Admin-Token" in response.headers["access-control-allow-headers"]


def test_admin_dashboard_returns_cross_tenant_material_pipeline(api_client) -> None:
    seed_parent_material(
        api_client,
        auth_code="admin-read-sunny",
        phone_number="13800138110",
        child_name="Mia Wang",
        material_title="Colors Mini Test",
    )
    seed_parent_material(
        api_client,
        auth_code="admin-read-maple",
        phone_number="13800138111",
        child_name="Tom Zhang",
        material_title="HN-014 Phonics Worksheet",
    )

    response = api_client.get("/v1/admin/dashboard?tenant_scope=all", headers=ADMIN_HEADERS)

    assert response.status_code == 200
    payload = response.json()
    assert {tenant["tenant_type"] for tenant in payload["tenants"]} == {"pilot_family"}
    assert len(payload["tenants"]) == 2
    assert len(payload["materials"]) == 2
    assert {material["title"] for material in payload["materials"]} == {
        "Colors Mini Test",
        "HN-014 Phonics Worksheet",
    }
    assert {material["child_name"] for material in payload["materials"]} == {"Mia Wang", "Tom Zhang"}
    assert all(material["tenant_id"] for material in payload["materials"])
    assert all(material["job_id"] for material in payload["materials"])
    assert all(material["provider"] == "stub" for material in payload["materials"])
    assert all(material["page_count"] == 1 for material in payload["materials"])
    assert payload["provider_policies"] == [
        {
            "tenant_id": "global",
            "ai_provider": "stub",
            "media_provider": "mock",
            "fallback_mode": "global_stub",
            "monthly_guardrail": 0,
            "source": "global_default",
        }
    ]

    first_tenant_id = payload["tenants"][0]["id"]
    scoped = api_client.get(f"/v1/admin/dashboard?tenant_scope={first_tenant_id}", headers=ADMIN_HEADERS)
    assert scoped.status_code == 200
    scoped_payload = scoped.json()
    assert [tenant["id"] for tenant in scoped_payload["tenants"]] == [first_tenant_id]
    assert {material["tenant_id"] for material in scoped_payload["materials"]} == {first_tenant_id}

    missing = api_client.get("/v1/admin/dashboard?tenant_scope=tenant_missing", headers=ADMIN_HEADERS)
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Tenant scope not found"


def seed_parent_material(
    api_client,
    *,
    auth_code: str,
    phone_number: str,
    child_name: str,
    material_title: str,
) -> None:
    headers, _ = auth_headers(api_client, auth_code=auth_code)
    child_response = api_client.post(
        "/v1/children",
        json={
            "name": child_name,
            "age": 6,
            "level": "starter",
            "learning_goal": "课后复习更稳定",
            "preferred_review_duration_minutes": 10,
            "parent_notes": "",
        },
        headers=headers,
    )
    assert child_response.status_code == 201
    child_id = child_response.json()["id"]

    upload_response = api_client.post(
        "/v1/materials",
        data={
            "child_id": child_id,
            "teacher_name": "Emma",
            "lesson_date": "2026-05-25",
            "title": material_title,
            "topic": "phonics",
            "tags": "admin,mvp",
        },
        files=[("files", ("worksheet.jpg", b"admin read api worksheet", "image/jpeg"))],
        headers=headers,
    )
    assert upload_response.status_code == 201
