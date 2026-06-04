from __future__ import annotations

from datetime import datetime, timezone

from app.core.db import SessionLocal
from app.core.settings import get_settings
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

    provider_response = api_client.options(
        "/v1/admin/providers/policies?tenant_scope=all",
        headers={
            "Origin": "http://127.0.0.1:5174",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "X-Admin-Token,Content-Type",
        },
    )

    assert provider_response.status_code == 200
    assert provider_response.headers["access-control-allow-origin"] == "http://127.0.0.1:5174"
    assert "POST" in provider_response.headers["access-control-allow-methods"]

    module_response = api_client.options(
        "/v1/admin/tenants/tenant_test/modules/speaking_score?tenant_scope=all",
        headers={
            "Origin": "http://127.0.0.1:5174",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "X-Admin-Token,Content-Type",
        },
    )

    assert module_response.status_code == 200
    assert module_response.headers["access-control-allow-origin"] == "http://127.0.0.1:5174"
    assert "POST" in module_response.headers["access-control-allow-methods"]

    impersonation_response = api_client.options(
        "/v1/admin/impersonation-sessions?tenant_scope=all",
        headers={
            "Origin": "http://127.0.0.1:5174",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "X-Admin-Token,Content-Type",
        },
    )

    assert impersonation_response.status_code == 200
    assert impersonation_response.headers["access-control-allow-origin"] == "http://127.0.0.1:5174"
    assert "POST" in impersonation_response.headers["access-control-allow-methods"]

    delete_material_response = api_client.options(
        "/v1/materials/material_test",
        headers={
            "Origin": "http://127.0.0.1:5174",
            "Access-Control-Request-Method": "DELETE",
            "Access-Control-Request-Headers": "Authorization",
        },
    )

    assert delete_material_response.status_code == 200
    assert delete_material_response.headers["access-control-allow-origin"] == "http://127.0.0.1:5174"
    assert "DELETE" in delete_material_response.headers["access-control-allow-methods"]
    assert "Authorization" in delete_material_response.headers["access-control-allow-headers"]

    primary_accent_response = api_client.options(
        "/v1/materials/material_test/learning-assets/asset_test/primary-accent",
        headers={
            "Origin": "http://127.0.0.1:5174",
            "Access-Control-Request-Method": "PATCH",
            "Access-Control-Request-Headers": "Authorization,Content-Type",
        },
    )

    assert primary_accent_response.status_code == 200
    assert primary_accent_response.headers["access-control-allow-origin"] == "http://127.0.0.1:5174"
    assert "PATCH" in primary_accent_response.headers["access-control-allow-methods"]
    assert "Authorization" in primary_accent_response.headers["access-control-allow-headers"]


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
    assert audit_event["id"] in {event["id"] for event in access.json()["audit_events"]}

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
    assert audit_event["id"] in {event["id"] for event in access.json()["audit_events"]}

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


def test_admin_retry_material_job_records_failed_audit_when_enqueue_fails(api_client, monkeypatch) -> None:
    def fail_enqueue(job_id: str) -> None:
        raise RuntimeError("redis unavailable")

    monkeypatch.setattr("app.api.routes.admin.enqueue_material_job", fail_enqueue)
    material_id, job_id, _ = seed_parent_material(
        api_client,
        auth_code="admin-retry-enqueue-failure",
        phone_number="13800138132",
        child_name="Olivia Retry",
        material_title="Retry Enqueue Failure Worksheet",
    )
    with SessionLocal() as db:
        job = db.get(MaterialParseJobModel, job_id)
        material = db.get(CourseMaterialModel, material_id)
        assert job is not None
        assert material is not None
        job.status = "failed"
        job.warnings = ["OCR timeout"]
        job.confidence_summary = "识别失败：OCR timeout"
        material.status = "failed"
        db.add_all([job, material])
        db.commit()

    response = api_client.post(
        f"/v1/admin/material-jobs/{job_id}/retry?tenant_scope=all",
        json={"reason": "Queue recovered but broker is still unavailable."},
        headers={**ADMIN_HEADERS, "X-Request-ID": "req_admin_retry_enqueue_failure"},
    )

    assert response.status_code == 503
    payload = response.json()
    assert payload["required_permission"] == "admin.material.retry"
    assert payload["detail"] == "Material retry enqueue failed"
    assert payload["material"]["id"] == material_id
    assert payload["material"]["material_status"] == "failed"
    assert payload["material"]["job_status"] == "failed"
    assert "redis unavailable" in payload["material"]["warnings"][0]
    audit_event = payload["audit_event"]
    assert audit_event["action"] == "admin.material_job.retry"
    assert audit_event["resource_id"] == job_id
    assert audit_event["result"] == "failed"
    assert audit_event["reason"] == "Queue recovered but broker is still unavailable."
    assert audit_event["trace_id"] == "req_admin_retry_enqueue_failure"

    access = api_client.get("/v1/admin/access?tenant_scope=all", headers=ADMIN_HEADERS)
    assert access.status_code == 200
    assert audit_event["id"] in {event["id"] for event in access.json()["audit_events"]}

    with SessionLocal() as db:
        job = db.get(MaterialParseJobModel, job_id)
        material = db.get(CourseMaterialModel, material_id)
        assert job is not None
        assert material is not None
        assert job.status == "failed"
        assert material.status == "failed"


def test_admin_provider_policy_override_requires_reason(api_client) -> None:
    material_id, _, _ = seed_parent_material(
        api_client,
        auth_code="admin-provider-reason",
        phone_number="13800138140",
        child_name="Mia Provider",
        material_title="Provider Reason Worksheet",
    )
    dashboard = api_client.get("/v1/admin/dashboard?tenant_scope=all", headers=ADMIN_HEADERS)
    tenant_id = next(material["tenant_id"] for material in dashboard.json()["materials"] if material["id"] == material_id)

    response = api_client.post(
        "/v1/admin/providers/policies?tenant_scope=all",
        json={
            "tenant_id": tenant_id,
            "ai_provider": "doubao",
            "media_provider": "real",
            "fallback_mode": "per_tenant",
            "monthly_guardrail": 500,
            "reason": "  ",
        },
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Provider policy override reason is required"


def test_admin_provider_policy_override_updates_dashboard_and_records_audit_event(api_client) -> None:
    material_id, _, _ = seed_parent_material(
        api_client,
        auth_code="admin-provider-success",
        phone_number="13800138141",
        child_name="Nora Provider",
        material_title="Provider Success Worksheet",
    )
    dashboard = api_client.get("/v1/admin/dashboard?tenant_scope=all", headers=ADMIN_HEADERS)
    tenant_id = next(material["tenant_id"] for material in dashboard.json()["materials"] if material["id"] == material_id)

    response = api_client.post(
        "/v1/admin/providers/policies?tenant_scope=all",
        json={
            "tenant_id": tenant_id,
            "ai_provider": "doubao",
            "media_provider": "real",
            "fallback_mode": "per_tenant",
            "monthly_guardrail": 500,
            "reason": "Pilot tenant approved for real media provider.",
        },
        headers={**ADMIN_HEADERS, "X-Request-ID": "req_admin_provider"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["required_permission"] == "admin.provider.override"
    assert payload["provider_policy"] == {
        "tenant_id": tenant_id,
        "ai_provider": "doubao",
        "media_provider": "real",
        "fallback_mode": "per_tenant",
        "monthly_guardrail": 500,
        "source": "tenant_override",
    }
    audit_event = payload["audit_event"]
    assert audit_event["action"] == "admin.provider_policy.override"
    assert audit_event["resource_type"] == "tenant_provider_policy"
    assert audit_event["resource_id"] == tenant_id
    assert audit_event["reason"] == "Pilot tenant approved for real media provider."
    assert audit_event["risk_level"] == "high"
    assert audit_event["trace_id"] == "req_admin_provider"

    updated_dashboard = api_client.get("/v1/admin/dashboard?tenant_scope=all", headers=ADMIN_HEADERS)
    assert updated_dashboard.status_code == 200
    policies = updated_dashboard.json()["provider_policies"]
    assert {
        "tenant_id": tenant_id,
        "ai_provider": "doubao",
        "media_provider": "real",
        "fallback_mode": "per_tenant",
        "monthly_guardrail": 500,
        "source": "tenant_override",
    } in policies
    assert "ARK_API_KEY" not in str(policies)

    access = api_client.get("/v1/admin/access?tenant_scope=all", headers=ADMIN_HEADERS)
    assert access.status_code == 200
    assert audit_event["id"] in {event["id"] for event in access.json()["audit_events"]}


def test_admin_provider_policy_override_accepts_qwen(api_client) -> None:
    material_id, _, _ = seed_parent_material(
        api_client,
        auth_code="admin-provider-qwen",
        phone_number="13800138142",
        child_name="Leo Provider",
        material_title="Qwen Provider Worksheet",
    )
    dashboard = api_client.get("/v1/admin/dashboard?tenant_scope=all", headers=ADMIN_HEADERS)
    tenant_id = next(material["tenant_id"] for material in dashboard.json()["materials"] if material["id"] == material_id)

    response = api_client.post(
        "/v1/admin/providers/policies?tenant_scope=all",
        json={
            "tenant_id": tenant_id,
            "ai_provider": "qwen",
            "media_provider": "real",
            "fallback_mode": "per_tenant",
            "monthly_guardrail": 500,
            "reason": "Pilot tenant approved for DashScope Qwen provider.",
        },
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 200
    assert response.json()["provider_policy"] == {
        "tenant_id": tenant_id,
        "ai_provider": "qwen",
        "media_provider": "real",
        "fallback_mode": "per_tenant",
        "monthly_guardrail": 500,
        "source": "tenant_override",
    }


def test_admin_tenant_module_toggle_requires_reason(api_client) -> None:
    material_id, _, _ = seed_parent_material(
        api_client,
        auth_code="admin-module-reason",
        phone_number="13800138150",
        child_name="Mia Module",
        material_title="Module Reason Worksheet",
    )
    dashboard = api_client.get("/v1/admin/dashboard?tenant_scope=all", headers=ADMIN_HEADERS)
    tenant_id = next(material["tenant_id"] for material in dashboard.json()["materials"] if material["id"] == material_id)

    response = api_client.post(
        f"/v1/admin/tenants/{tenant_id}/modules/speaking_score?tenant_scope=all",
        json={"enabled": False, "reason": "  "},
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Module toggle reason is required"


def test_admin_tenant_module_toggle_updates_dashboard_and_records_audit_event(api_client) -> None:
    material_id, _, _ = seed_parent_material(
        api_client,
        auth_code="admin-module-success",
        phone_number="13800138151",
        child_name="Nora Module",
        material_title="Module Success Worksheet",
    )
    dashboard = api_client.get("/v1/admin/dashboard?tenant_scope=all", headers=ADMIN_HEADERS)
    tenant_id = next(material["tenant_id"] for material in dashboard.json()["materials"] if material["id"] == material_id)

    response = api_client.post(
        f"/v1/admin/tenants/{tenant_id}/modules/speaking_score?tenant_scope=all",
        json={"enabled": False, "reason": "Pilot tenant requested speaking score pause."},
        headers={**ADMIN_HEADERS, "X-Request-ID": "req_admin_module"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["required_permission"] == "admin.tenant.module.toggle"
    assert payload["module_setting"] == {
        "tenant_id": tenant_id,
        "module_key": "speaking_score",
        "enabled": False,
        "source": "tenant_override",
    }
    audit_event = payload["audit_event"]
    assert audit_event["action"] == "admin.tenant_module.toggle"
    assert audit_event["resource_type"] == "tenant_module_setting"
    assert audit_event["resource_id"] == f"{tenant_id}:speaking_score"
    assert audit_event["reason"] == "Pilot tenant requested speaking score pause."
    assert audit_event["risk_level"] == "high"
    assert audit_event["trace_id"] == "req_admin_module"

    updated_dashboard = api_client.get("/v1/admin/dashboard?tenant_scope=all", headers=ADMIN_HEADERS)
    assert updated_dashboard.status_code == 200
    module_settings = updated_dashboard.json()["module_settings"]
    assert {
        "tenant_id": tenant_id,
        "module_key": "speaking_score",
        "enabled": False,
        "source": "tenant_override",
    } in module_settings
    assert "ARK_API_KEY" not in str(module_settings)

    access = api_client.get("/v1/admin/access?tenant_scope=all", headers=ADMIN_HEADERS)
    assert access.status_code == 200
    assert audit_event["id"] in {event["id"] for event in access.json()["audit_events"]}


def test_admin_impersonation_session_requires_reason(api_client) -> None:
    material_id, _, _ = seed_parent_material(
        api_client,
        auth_code="admin-impersonation-reason",
        phone_number="13800138160",
        child_name="Mia Impersonation",
        material_title="Impersonation Reason Worksheet",
    )
    dashboard = api_client.get("/v1/admin/dashboard?tenant_scope=all", headers=ADMIN_HEADERS)
    tenant_id = next(material["tenant_id"] for material in dashboard.json()["materials"] if material["id"] == material_id)

    response = api_client.post(
        "/v1/admin/impersonation-sessions?tenant_scope=all",
        json={"tenant_id": tenant_id, "target_parent_id": tenant_id, "reason": "  "},
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Impersonation reason is required"


def test_admin_impersonation_session_creates_audited_supervised_session(api_client) -> None:
    material_id, _, _ = seed_parent_material(
        api_client,
        auth_code="admin-impersonation-success",
        phone_number="13800138161",
        child_name="Nora Impersonation",
        material_title="Impersonation Success Worksheet",
    )
    dashboard = api_client.get("/v1/admin/dashboard?tenant_scope=all", headers=ADMIN_HEADERS)
    tenant_id = next(material["tenant_id"] for material in dashboard.json()["materials"] if material["id"] == material_id)

    response = api_client.post(
        "/v1/admin/impersonation-sessions?tenant_scope=all",
        json={
            "tenant_id": tenant_id,
            "target_parent_id": tenant_id,
            "reason": "Support is reproducing parent-reported upload issue.",
        },
        headers={**ADMIN_HEADERS, "X-Request-ID": "req_admin_impersonation"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["required_permission"] == "admin.impersonation.start"
    assert "access_token" not in str(payload)
    assert "refresh_token" not in str(payload)
    session = payload["impersonation_session"]
    assert session["id"].startswith("imp_")
    assert session["tenant_id"] == tenant_id
    assert session["target_parent_id"] == tenant_id
    assert session["actor_id"] == "admin_local"
    assert session["status"] == "active"
    assert session["reason"] == "Support is reproducing parent-reported upload issue."
    assert datetime.fromisoformat(session["expires_at"]) > datetime.fromisoformat(session["created_at"])
    audit_event = payload["audit_event"]
    assert audit_event["action"] == "admin.impersonation.start"
    assert audit_event["resource_type"] == "admin_impersonation_session"
    assert audit_event["resource_id"] == session["id"]
    assert audit_event["reason"] == "Support is reproducing parent-reported upload issue."
    assert audit_event["risk_level"] == "high"
    assert audit_event["trace_id"] == "req_admin_impersonation"

    access = api_client.get("/v1/admin/access?tenant_scope=all", headers=ADMIN_HEADERS)
    assert access.status_code == 200
    assert audit_event["id"] in {event["id"] for event in access.json()["audit_events"]}


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
    sunny_tenant_id = next(material["tenant_id"] for material in seeded_materials if material["id"] == sunny_material_id)
    assert {
        "tenant_id": "global",
        "ai_provider": "stub",
        "media_provider": "mock",
        "fallback_mode": "global_stub",
        "monthly_guardrail": 0,
        "source": "global_default",
    } in payload["provider_policies"]
    assert {
        "tenant_id": sunny_tenant_id,
        "module_key": "speaking_score",
        "enabled": True,
        "source": "global_default",
    } in payload["module_settings"]

    scoped = api_client.get(f"/v1/admin/dashboard?tenant_scope={sunny_tenant_id}", headers=ADMIN_HEADERS)
    assert scoped.status_code == 200
    scoped_payload = scoped.json()
    assert [tenant["id"] for tenant in scoped_payload["tenants"]] == [sunny_tenant_id]
    assert {material["tenant_id"] for material in scoped_payload["materials"]} == {sunny_tenant_id}
    assert sunny_material_id in {material["id"] for material in scoped_payload["materials"]}

    missing = api_client.get("/v1/admin/dashboard?tenant_scope=tenant_missing", headers=ADMIN_HEADERS)
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Tenant scope not found"


def test_admin_dashboard_reflects_qwen_global_provider(api_client, monkeypatch) -> None:
    with monkeypatch.context() as m:
        m.setenv("AI_PROVIDER", "qwen")
        m.setenv("DASHSCOPE_API_KEY", "sk-test-dashscope")
        m.setenv("MEDIA_PROVIDER", "real")
        get_settings.cache_clear()
        material_id, _, _ = seed_parent_material(
            api_client,
            auth_code="admin-read-qwen",
            phone_number="13800138112",
            child_name="Ava Qwen",
            material_title="Qwen Worksheet",
        )

        response = api_client.get("/v1/admin/dashboard?tenant_scope=all", headers=ADMIN_HEADERS)

    get_settings.cache_clear()
    assert response.status_code == 200
    payload = response.json()
    material = next(item for item in payload["materials"] if item["id"] == material_id)
    assert material["provider"] == "qwen"
    assert {
        "tenant_id": "global",
        "ai_provider": "qwen",
        "media_provider": "real",
        "fallback_mode": "auto_to_mock",
        "monthly_guardrail": 0,
        "source": "global_default",
    } in payload["provider_policies"]


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
