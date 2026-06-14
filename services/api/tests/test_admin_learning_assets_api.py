from __future__ import annotations

from app.core.db import SessionLocal
from app.db.models import ChildProfileModel, CourseMaterialModel
from app.models.contracts import MaterialStatus
from conftest import auth_headers, configure_test_environment


configure_test_environment("learning-english-api-admin-assets-")

ADMIN_HEADERS = {"X-Admin-Token": "local-admin-token"}

READY_ASSET = {
    "id": "asset_ready",
    "text": "queen",
    "kind": "word",
    "translation": "女王",
    "primary_accent": "us",
    "generated_image_status": "ready",
    "generated_image_url": "http://testserver/uploads/generated/img.png",
    "tts_us_status": "ready",
    "tts_us_url": "http://testserver/uploads/generated/us.mp3",
    "tts_uk_status": "ready",
    "tts_uk_url": "http://testserver/uploads/generated/uk.mp3",
}
PENDING_ASSET = {
    "id": "asset_pending",
    "text": "king",
    "kind": "word",
    "translation": "国王",
    "primary_accent": "us",
}


def _seed_material_with_assets(
    api_client,
    *,
    auth_code: str,
    phone_number: str,
    assets: list[dict],
    title: str = "Assets Worksheet",
    status_value: str = MaterialStatus.ready.value,
) -> tuple[str, str]:
    headers, _ = auth_headers(api_client, auth_code=auth_code)
    child_response = api_client.post(
        "/v1/children",
        json={
            "name": "Mia Assets",
            "age": 6,
            "level": "starter",
            "learning_goal": "稳定复习",
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
            "title": title,
            "topic": "phonics",
            "tags": "admin,mvp",
        },
        files=[("files", ("worksheet.jpg", b"assets worksheet", "image/jpeg"))],
        headers=headers,
    )
    assert upload_response.status_code == 201
    material_id = upload_response.json()["material"]["id"]
    with SessionLocal() as db:
        material = db.get(CourseMaterialModel, material_id)
        material.learning_assets = assets
        material.status = status_value
        db.add(material)
        db.commit()
        tenant_id = db.get(ChildProfileModel, child_id).parent_account_id
    return material_id, tenant_id


def test_admin_learning_assets_requires_token_and_explicit_scope(api_client) -> None:
    missing_token = api_client.get("/v1/admin/learning-assets?tenant_scope=all")
    assert missing_token.status_code == 401

    missing_scope = api_client.get("/v1/admin/learning-assets", headers=ADMIN_HEADERS)
    assert missing_scope.status_code == 422


def test_admin_learning_assets_returns_flattened_assets_with_context(api_client) -> None:
    material_id, tenant_id = _seed_material_with_assets(
        api_client,
        auth_code="admin-assets-flatten",
        phone_number="13800139001",
        assets=[READY_ASSET, PENDING_ASSET],
        title="Phonics Qq",
    )

    response = api_client.get("/v1/admin/learning-assets?tenant_scope=all", headers=ADMIN_HEADERS)

    assert response.status_code == 200
    payload = response.json()
    assert payload["required_permission"] == "admin.dashboard.read"
    seeded = [item for item in payload["items"] if item["material_id"] == material_id]
    assert {item["id"] for item in seeded} == {"asset_ready", "asset_pending"}
    by_id = {item["id"]: item for item in seeded}
    assert by_id["asset_ready"]["text"] == "queen"
    assert by_id["asset_ready"]["material_title"] == "Phonics Qq"
    assert by_id["asset_ready"]["tenant_id"] == tenant_id
    assert by_id["asset_ready"]["child_name"] == "Mia Assets"
    assert by_id["asset_ready"]["media_status"] == "ready"
    assert by_id["asset_pending"]["media_status"] == "pending"
    # 审计事件已记录
    assert payload["audit_event"]["action"] == "admin.learning_assets.read"


def test_admin_learning_assets_filters_by_media_status(api_client) -> None:
    material_id, _ = _seed_material_with_assets(
        api_client,
        auth_code="admin-assets-status-filter",
        phone_number="13800139002",
        assets=[READY_ASSET, PENDING_ASSET],
    )

    response = api_client.get(
        "/v1/admin/learning-assets?tenant_scope=all&media_status=ready",
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 200
    seeded = [item for item in response.json()["items"] if item["material_id"] == material_id]
    assert {item["id"] for item in seeded} == {"asset_ready"}


def test_admin_learning_assets_filters_by_material_id(api_client) -> None:
    target_id, _ = _seed_material_with_assets(
        api_client,
        auth_code="admin-assets-material-a",
        phone_number="13800139003",
        assets=[READY_ASSET],
        title="Target Worksheet",
    )
    _seed_material_with_assets(
        api_client,
        auth_code="admin-assets-material-b",
        phone_number="13800139004",
        assets=[PENDING_ASSET],
        title="Other Worksheet",
    )

    response = api_client.get(
        f"/v1/admin/learning-assets?tenant_scope=all&material_id={target_id}",
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 200
    items = response.json()["items"]
    assert items
    assert {item["material_id"] for item in items} == {target_id}


def test_admin_learning_assets_scopes_to_tenant(api_client) -> None:
    material_a, tenant_a = _seed_material_with_assets(
        api_client,
        auth_code="admin-assets-tenant-a",
        phone_number="13800139005",
        assets=[READY_ASSET],
    )
    material_b, tenant_b = _seed_material_with_assets(
        api_client,
        auth_code="admin-assets-tenant-b",
        phone_number="13800139006",
        assets=[PENDING_ASSET],
    )
    assert tenant_a != tenant_b

    response = api_client.get(
        f"/v1/admin/learning-assets?tenant_scope={tenant_a}",
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 200
    material_ids = {item["material_id"] for item in response.json()["items"]}
    assert material_a in material_ids
    assert material_b not in material_ids


def test_admin_learning_assets_excludes_archived_material(api_client) -> None:
    material_id, _ = _seed_material_with_assets(
        api_client,
        auth_code="admin-assets-archived",
        phone_number="13800139007",
        assets=[READY_ASSET],
        status_value=MaterialStatus.archived.value,
    )

    response = api_client.get("/v1/admin/learning-assets?tenant_scope=all", headers=ADMIN_HEADERS)

    assert response.status_code == 200
    material_ids = {item["material_id"] for item in response.json()["items"]}
    assert material_id not in material_ids
