from __future__ import annotations

from conftest import auth_headers, configure_test_environment


configure_test_environment("learning-english-api-admin-users-")

ADMIN_HEADERS = {"X-Admin-Token": "local-admin-token"}


def _seed_child(
    api_client,
    *,
    auth_code: str,
    child_name: str,
    level: str = "starter",
    with_material: bool = False,
) -> tuple[str, str]:
    headers, _ = auth_headers(api_client, auth_code=auth_code)
    child_response = api_client.post(
        "/v1/children",
        json={
            "name": child_name,
            "age": 6,
            "level": level,
            "learning_goal": "稳定复习",
            "preferred_review_duration_minutes": 10,
            "parent_notes": "",
        },
        headers=headers,
    )
    assert child_response.status_code == 201
    child_id = child_response.json()["id"]
    if with_material:
        upload = api_client.post(
            "/v1/materials",
            data={
                "child_id": child_id,
                "teacher_name": "Emma",
                "lesson_date": "2026-05-25",
                "title": f"{child_name} Worksheet",
                "topic": "phonics",
                "tags": "admin",
            },
            files=[("files", ("worksheet.jpg", b"users worksheet", "image/jpeg"))],
            headers=headers,
        )
        assert upload.status_code == 201
    # tenant_id == parent id; derive from admin dashboard
    dashboard = api_client.get("/v1/admin/dashboard?tenant_scope=all", headers=ADMIN_HEADERS)
    tenant_id = next(
        material["tenant_id"]
        for material in dashboard.json()["materials"]
        if material["child_name"] == child_name
    ) if with_material else ""
    return child_id, tenant_id


def test_admin_users_requires_token_and_explicit_scope(api_client) -> None:
    missing_token = api_client.get("/v1/admin/users?tenant_scope=all")
    assert missing_token.status_code == 401

    missing_scope = api_client.get("/v1/admin/users", headers=ADMIN_HEADERS)
    assert missing_scope.status_code == 422


def test_admin_users_lists_children_with_context_and_counts(api_client) -> None:
    child_id, tenant_id = _seed_child(
        api_client,
        auth_code="admin-users-context",
        child_name="Mia Users",
        with_material=True,
    )

    response = api_client.get("/v1/admin/users?tenant_scope=all", headers=ADMIN_HEADERS)

    assert response.status_code == 200
    payload = response.json()
    assert payload["required_permission"] == "admin.tenant.read"
    assert payload["audit_event"]["action"] == "admin.users.read"
    row = next(item for item in payload["items"] if item["child_id"] == child_id)
    assert row["child_name"] == "Mia Users"
    assert row["tenant_id"] == tenant_id
    assert row["parent_name"]
    assert row["materials_count"] == 1
    assert row["speaking_attempts"] == 0
    assert row["level"] == "starter"


def test_admin_users_filters_by_level(api_client) -> None:
    starter_id, _ = _seed_child(api_client, auth_code="admin-users-starter", child_name="Leo Starter", level="starter")
    mover_id, _ = _seed_child(api_client, auth_code="admin-users-mover", child_name="Ava Mover", level="mover")

    response = api_client.get("/v1/admin/users?tenant_scope=all&level=mover", headers=ADMIN_HEADERS)

    assert response.status_code == 200
    child_ids = {item["child_id"] for item in response.json()["items"]}
    assert mover_id in child_ids
    assert starter_id not in child_ids


def test_admin_users_scopes_to_tenant(api_client) -> None:
    child_a, tenant_a = _seed_child(
        api_client, auth_code="admin-users-tenant-a", child_name="Tom ScopeA", with_material=True
    )
    child_b, tenant_b = _seed_child(
        api_client, auth_code="admin-users-tenant-b", child_name="Sue ScopeB", with_material=True
    )
    assert tenant_a != tenant_b

    response = api_client.get(f"/v1/admin/users?tenant_scope={tenant_a}", headers=ADMIN_HEADERS)

    assert response.status_code == 200
    child_ids = {item["child_id"] for item in response.json()["items"]}
    assert child_a in child_ids
    assert child_b not in child_ids


def test_admin_users_unknown_scope_returns_404(api_client) -> None:
    response = api_client.get("/v1/admin/users?tenant_scope=tenant_missing", headers=ADMIN_HEADERS)
    assert response.status_code == 404
    assert response.json()["detail"] == "Tenant scope not found"
