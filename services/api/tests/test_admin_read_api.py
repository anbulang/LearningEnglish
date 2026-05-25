from __future__ import annotations

from datetime import datetime, timezone

from app.core.db import SessionLocal
from app.db.models import CourseMaterialModel, KnowledgePackModel, MaterialParseJobModel, ParentCoachingScriptModel, ReviewTaskModel
from conftest import auth_headers, configure_test_environment


configure_test_environment("learning-english-api-admin-read-")

ADMIN_HEADERS = {"X-Admin-Token": "local-admin-token"}


def test_admin_dashboard_requires_admin_token_and_explicit_tenant_scope(api_client) -> None:
    missing_token = api_client.get("/v1/admin/dashboard?tenant_scope=all")
    assert missing_token.status_code == 401
    assert missing_token.json()["detail"] == "Missing admin token"

    missing_scope = api_client.get("/v1/admin/dashboard", headers=ADMIN_HEADERS)
    assert missing_scope.status_code == 422


def test_admin_access_returns_actor_permissions_and_dashboard_audit_event(api_client) -> None:
    dashboard = api_client.get("/v1/admin/dashboard?tenant_scope=all", headers=ADMIN_HEADERS)
    assert dashboard.status_code == 200

    access = api_client.get("/v1/admin/access?tenant_scope=all", headers=ADMIN_HEADERS)

    assert access.status_code == 200
    payload = access.json()
    assert payload["current_admin"] == {
        "id": "admin_local",
        "display_name": "Local Platform Admin",
        "email": "admin@learningenglish.local",
        "role": "Platform Owner",
        "status": "active",
    }
    assert "admin.dashboard.read" in payload["permissions"]
    assert "admin.audit.read" in payload["permissions"]
    assert "local-admin-token" not in str(payload)
    assert payload["audit_events"]
    latest = payload["audit_events"][0]
    assert latest["actor_id"] == "admin_local"
    assert latest["tenant_scope"] == "all"
    assert latest["action"] == "admin.dashboard.read"
    assert latest["resource_type"] == "admin_dashboard"
    assert latest["resource_id"] == "dashboard"
    assert latest["result"] == "success"
    assert latest["risk_level"] == "low"
    assert latest["trace_id"].startswith("req_")
    assert latest["created_at"]


def test_admin_dashboard_allows_local_admin_cors_preflight(api_client) -> None:
    for origin in ("http://127.0.0.1:5173", "http://127.0.0.1:5174", "http://localhost:52464"):
        response = api_client.options(
            "/v1/admin/dashboard?tenant_scope=all",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "X-Admin-Token",
            },
        )

        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == origin
        assert "X-Admin-Token" in response.headers["access-control-allow-headers"]

    archive_response = api_client.options(
        "/v1/admin/materials/material_test/archive?tenant_scope=all",
        headers={
            "Origin": "http://127.0.0.1:5174",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "X-Admin-Token,Content-Type",
        },
    )

    assert archive_response.status_code == 200
    assert archive_response.headers["access-control-allow-origin"] == "http://127.0.0.1:5174"
    assert "POST" in archive_response.headers["access-control-allow-methods"]

    retry_response = api_client.options(
        "/v1/admin/material-jobs/job_test/retry?tenant_scope=all",
        headers={
            "Origin": "http://127.0.0.1:5174",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "X-Admin-Token,Content-Type",
        },
    )

    assert retry_response.status_code == 200
    assert retry_response.headers["access-control-allow-origin"] == "http://127.0.0.1:5174"
    assert "POST" in retry_response.headers["access-control-allow-methods"]


def test_admin_archive_material_requires_reason(api_client) -> None:
    material_id, _, _ = seed_parent_material(
        api_client,
        auth_code="admin-archive-reason",
        phone_number="13800138120",
        child_name="Mia Archive",
        material_title="Archive Reason Worksheet",
    )

    response = api_client.post(
        f"/v1/admin/materials/{material_id}/archive?tenant_scope=all",
        json={"reason": "  "},
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Archive reason is required"


def test_admin_archive_material_updates_status_and_records_audit_event(api_client) -> None:
    material_id, job_id, child_id = seed_parent_material(
        api_client,
        auth_code="admin-archive-success",
        phone_number="13800138121",
        child_name="Nora Archive",
        material_title="Archive Success Worksheet",
    )
    knowledge_id, coach_id, task_id = seed_ready_derivatives(material_id, child_id)

    response = api_client.post(
        f"/v1/admin/materials/{material_id}/archive?tenant_scope=all",
        json={"reason": "Duplicate worksheet uploaded by parent."},
        headers={**ADMIN_HEADERS, "X-Request-ID": "req_admin_archive"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["required_permission"] == "admin.material.archive"
    assert payload["material"]["id"] == material_id
    assert payload["material"]["job_id"] == job_id
    assert payload["material"]["material_status"] == "archived"
    audit_event = payload["audit_event"]
    assert audit_event["action"] == "admin.material.archive"
    assert audit_event["resource_type"] == "course_material"
    assert audit_event["resource_id"] == material_id
    assert audit_event["reason"] == "Duplicate worksheet uploaded by parent."
    assert audit_event["risk_level"] == "high"
    assert audit_event["result"] == "success"
    assert audit_event["trace_id"] == "req_admin_archive"

    access = api_client.get("/v1/admin/access?tenant_scope=all", headers=ADMIN_HEADERS)
    assert access.status_code == 200
    assert access.json()["audit_events"][0]["id"] == audit_event["id"]

    with SessionLocal() as db:
        assert db.get(KnowledgePackModel, knowledge_id) is None
        assert db.get(ParentCoachingScriptModel, coach_id) is None
        assert db.get(ReviewTaskModel, task_id) is None


def test_admin_retry_material_job_requires_reason(api_client) -> None:
    _, job_id, _ = seed_parent_material(
        api_client,
        auth_code="admin-retry-reason",
        phone_number="13800138130",
        child_name="Mia Retry",
        material_title="Retry Reason Worksheet",
    )

    response = api_client.post(
        f"/v1/admin/material-jobs/{job_id}/retry?tenant_scope=all",
        json={"reason": "  "},
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Retry reason is required"


def test_admin_retry_material_job_resets_state_and_records_audit_event(api_client) -> None:
    material_id, job_id, _ = seed_parent_material(
        api_client,
        auth_code="admin-retry-success",
        phone_number="13800138131",
        child_name="Nora Retry",
        material_title="Retry Success Worksheet",
    )
    with SessionLocal() as db:
        job = db.get(MaterialParseJobModel, job_id)
        material = db.get(CourseMaterialModel, material_id)
        assert job is not None
        assert material is not None
        job.status = "failed"
        job.warnings = ["OCR timeout", "Queue timeout"]
        job.confidence_summary = "识别失败：OCR timeout"
        job.finished_at = datetime(2026, 5, 25, tzinfo=timezone.utc)
        material.status = "failed"
        db.add_all([job, material])
        db.commit()

    response = api_client.post(
        f"/v1/admin/material-jobs/{job_id}/retry?tenant_scope=all",
        json={"reason": "OCR provider recovered."},
        headers={**ADMIN_HEADERS, "X-Request-ID": "req_admin_retry"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["required_permission"] == "admin.material.retry"
    assert payload["material"]["id"] == material_id
    assert payload["material"]["job_id"] == job_id
    assert payload["material"]["material_status"] == "processing"
    assert payload["material"]["job_status"] == "processing"
    assert payload["material"]["warnings"] == []
    audit_event = payload["audit_event"]
    assert audit_event["action"] == "admin.material_job.retry"
    assert audit_event["resource_type"] == "material_parse_job"
    assert audit_event["resource_id"] == job_id
    assert audit_event["reason"] == "OCR provider recovered."
    assert audit_event["risk_level"] == "high"
    assert audit_event["result"] == "success"
    assert audit_event["trace_id"] == "req_admin_retry"

    access = api_client.get("/v1/admin/access?tenant_scope=all", headers=ADMIN_HEADERS)
    assert access.status_code == 200
    assert access.json()["audit_events"][0]["id"] == audit_event["id"]

    with SessionLocal() as db:
        job = db.get(MaterialParseJobModel, job_id)
        material = db.get(CourseMaterialModel, material_id)
        assert job is not None
        assert material is not None
        assert job.status == "processing"
        assert job.warnings == []
        assert job.confidence_summary == "任务已重新排队。"
        assert job.finished_at is None
        assert material.status == "processing"


def test_admin_dashboard_returns_cross_tenant_material_pipeline(api_client) -> None:
    sunny_material_id, _, _ = seed_parent_material(
        api_client,
        auth_code="admin-read-sunny",
        phone_number="13800138110",
        child_name="Mia Wang",
        material_title="Colors Mini Test",
    )
    maple_material_id, _, _ = seed_parent_material(
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
    assert len(payload["tenants"]) >= 2
    assert len(payload["materials"]) >= 2
    seeded_materials = [material for material in payload["materials"] if material["id"] in {sunny_material_id, maple_material_id}]
    assert {material["title"] for material in seeded_materials} == {
        "Colors Mini Test",
        "HN-014 Phonics Worksheet",
    }
    assert {material["child_name"] for material in seeded_materials} == {"Mia Wang", "Tom Zhang"}
    assert all(material["tenant_id"] for material in seeded_materials)
    assert all(material["job_id"] for material in seeded_materials)
    assert all(material["provider"] == "stub" for material in seeded_materials)
    assert all(material["page_count"] == 1 for material in seeded_materials)
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

    sunny_tenant_id = next(material["tenant_id"] for material in seeded_materials if material["id"] == sunny_material_id)
    scoped = api_client.get(f"/v1/admin/dashboard?tenant_scope={sunny_tenant_id}", headers=ADMIN_HEADERS)
    assert scoped.status_code == 200
    scoped_payload = scoped.json()
    assert [tenant["id"] for tenant in scoped_payload["tenants"]] == [sunny_tenant_id]
    assert {material["tenant_id"] for material in scoped_payload["materials"]} == {sunny_tenant_id}
    assert sunny_material_id in {material["id"] for material in scoped_payload["materials"]}

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
) -> tuple[str, str, str]:
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
    payload = upload_response.json()
    return payload["material"]["id"], payload["job"]["id"], child_id


def seed_ready_derivatives(material_id: str, child_id: str) -> tuple[str, str, str]:
    knowledge_id = f"admin_knowledge_{material_id}"
    coach_id = f"admin_coach_{material_id}"
    task_id = f"admin_task_{material_id}"
    with SessionLocal() as db:
        db.add(
            KnowledgePackModel(
                id=knowledge_id,
                material_id=material_id,
                topic="archive",
                difficulty_band="repeat",
                lesson_summary="Ready for admin archive.",
                review_recommendation="Archive duplicate.",
                vocabulary_items=[],
                sentence_patterns=[],
            )
        )
        db.add(
            ParentCoachingScriptModel(
                id=coach_id,
                material_id=material_id,
                title="Archive coaching",
                intro="Duplicate worksheet.",
                steps=[],
            )
        )
        db.add(
            ReviewTaskModel(
                id=task_id,
                child_id=child_id,
                material_id=material_id,
                task_type="flashcard",
                difficulty="easy",
                content_json={"word": "archive"},
                due_date=datetime(2026, 5, 25, tzinfo=timezone.utc),
                status="pending",
            )
        )
        db.commit()
    return knowledge_id, coach_id, task_id
