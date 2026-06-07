from __future__ import annotations

from datetime import date, datetime, timezone

import pytest
from fastapi import HTTPException

from conftest import configure_test_environment


configure_test_environment("learning-english-api-admin-read-models-")

from app.core.db import SessionLocal, init_db  # noqa: E402
from app.db.models import (  # noqa: E402
    ChildProfileModel,
    CourseMaterialModel,
    MaterialParseJobModel,
    ParentAccountModel,
    TenantModuleSettingModel,
    TenantProviderPolicyModel,
)
from app.models.contracts import JobStatus, MaterialStatus  # noqa: E402
from app.services.admin.read_models import build_admin_dashboard, build_admin_tenant_detail  # noqa: E402


def _seed_read_model_fixture(tenant_id: str = "tenant_read_model") -> dict:
    init_db()
    now = datetime(2026, 5, 31, 15, 0, tzinfo=timezone.utc)
    child_id = f"child_{tenant_id}"
    material_id = f"material_{tenant_id}"
    job_id = f"job_{tenant_id}"
    with SessionLocal() as db:
        db.add(
            ParentAccountModel(
                id=tenant_id,
                display_name="Read Model Family",
                avatar_url="",
                phone_number="13800139901",
                phone_verified_at=now,
                wechat_union_id=f"wechat_union_{tenant_id}",
                wechat_open_id=f"wechat_open_{tenant_id}",
                created_at=now,
                updated_at=now,
            )
        )
        db.add(
            ChildProfileModel(
                id=child_id,
                parent_account_id=tenant_id,
                name="Mia",
                avatar_url="",
                age=7,
                level="starter",
                learning_goal="Read phonics stories",
                preferred_review_duration_minutes=12,
                parent_notes="",
                created_at=now,
                updated_at=now,
            )
        )
        db.add(
            CourseMaterialModel(
                id=material_id,
                child_id=child_id,
                teacher_name="Ms Lee",
                lesson_date=date(2026, 5, 31),
                title="Phonics A",
                topic="phonics",
                status=MaterialStatus.failed.value,
                image_records=[{"page_index": 0, "url": "http://testserver/page.png", "source_type": "gallery"}],
                learning_assets=[
                    {
                        "generated_image_status": "failed",
                        "tts_us_status": "ready",
                        "tts_uk_status": "ready",
                    }
                ],
                created_at=now,
                updated_at=now,
            )
        )
        db.add(
            MaterialParseJobModel(
                id=job_id,
                material_id=material_id,
                status=JobStatus.failed.value,
                confidence_summary="OCR provider timeout",
                warnings=["OCR provider timeout"],
                started_at=now,
                finished_at=now,
            )
        )
        db.add(
            TenantProviderPolicyModel(
                tenant_id=tenant_id,
                ai_provider="doubao",
                media_provider="real",
                fallback_mode="per_tenant",
                monthly_guardrail=500,
                source="tenant_override",
                reason="Fixture",
                created_by="admin_read_model",
                created_at=now,
                updated_at=now,
            )
        )
        db.add(
            TenantModuleSettingModel(
                tenant_id=tenant_id,
                module_key="weekly_reports",
                enabled=False,
                source="tenant_override",
                reason="Fixture",
                created_by="admin_read_model",
                created_at=now,
                updated_at=now,
            )
        )
        db.commit()
    return {"tenant_id": tenant_id, "child_id": child_id, "material_id": material_id, "job_id": job_id}


def test_build_admin_dashboard_returns_phase_two_payload_keys() -> None:
    fixture = _seed_read_model_fixture("tenant_read_model_dashboard")

    with SessionLocal() as db:
        payload = build_admin_dashboard(db, tenant_scope="all")
        scoped_payload = build_admin_dashboard(db, tenant_scope=fixture["tenant_id"])

    assert set(payload.keys()) == {"tenants", "materials", "provider_policies", "module_settings"}
    assert fixture["tenant_id"] in {tenant["id"] for tenant in payload["tenants"]}
    assert fixture["material_id"] in {material["id"] for material in payload["materials"]}
    assert payload["provider_policies"][0]["tenant_id"] == "global"
    assert any(setting["module_key"] == "weekly_reports" for setting in payload["module_settings"])
    assert [tenant["id"] for tenant in scoped_payload["tenants"]] == [fixture["tenant_id"]]
    assert all(material["tenant_id"] == fixture["tenant_id"] for material in scoped_payload["materials"])


def test_build_admin_tenant_detail_returns_phase_two_payload_keys() -> None:
    fixture = _seed_read_model_fixture("tenant_read_model_detail")

    with SessionLocal() as db:
        payload = build_admin_tenant_detail(db, tenant_scope="all", tenant_id=fixture["tenant_id"])

    assert set(payload.keys()) == {
        "required_permission",
        "tenant",
        "summary",
        "children",
        "materials",
        "provider_policy",
        "module_settings",
        "weekly_reports",
        "speaking_attempts",
        "risk_summary",
    }
    assert payload["required_permission"] == "admin.tenant.read"
    assert payload["tenant"]["id"] == fixture["tenant_id"]
    assert payload["tenant"]["active_parents"] == 1
    assert payload["tenant"]["children"] == 1
    assert payload["children"][0]["id"] == fixture["child_id"]
    assert payload["materials"][0]["id"] == fixture["material_id"]
    assert payload["provider_policy"]["tenant_id"] == fixture["tenant_id"]
    assert payload["risk_summary"]["risk_level"] == "high"


def test_build_admin_tenant_detail_honors_tenant_scope_without_disclosure() -> None:
    fixture = _seed_read_model_fixture("tenant_read_model_scope")
    _seed_read_model_fixture("tenant_read_model_hidden")

    with SessionLocal() as db:
        scoped_payload = build_admin_tenant_detail(db, tenant_scope=fixture["tenant_id"], tenant_id=fixture["tenant_id"])
        with pytest.raises(HTTPException) as exc:
            build_admin_tenant_detail(db, tenant_scope=fixture["tenant_id"], tenant_id="tenant_read_model_hidden")

    assert scoped_payload["tenant"]["id"] == fixture["tenant_id"]
    assert exc.value.status_code == 404
    assert exc.value.detail == "Tenant not found"
