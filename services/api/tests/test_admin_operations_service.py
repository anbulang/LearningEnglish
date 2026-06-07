from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from conftest import configure_test_environment


configure_test_environment("learning-english-api-admin-operations-")

from app.core.db import SessionLocal, init_db  # noqa: E402
from app.db.models import (  # noqa: E402
    ChildProfileModel,
    CourseMaterialModel,
    MaterialParseJobModel,
    ParentAccountModel,
    SpeakingAttemptModel,
    TenantProviderPolicyModel,
)
from app.models.contracts import JobStatus, MaterialStatus, SpeakingAttemptStatus  # noqa: E402
from app.services.admin.operations import build_admin_operations  # noqa: E402


def _seed_tenant(prefix: str, *, tenant_id: str = "") -> dict[str, str]:
    init_db()
    now = datetime(2026, 5, 31, 16, 0, tzinfo=timezone.utc)
    resolved_tenant_id = tenant_id or f"{prefix}_tenant"
    child_id = f"{prefix}_child"
    with SessionLocal() as db:
        db.add(
            ParentAccountModel(
                id=resolved_tenant_id,
                display_name=f"{prefix} Family",
                avatar_url="",
                phone_number="13800139800",
                phone_verified_at=now,
                wechat_union_id=f"wechat_union_{resolved_tenant_id}",
                wechat_open_id=f"wechat_open_{resolved_tenant_id}",
                created_at=now,
                updated_at=now,
            )
        )
        db.add(
            ChildProfileModel(
                id=child_id,
                parent_account_id=resolved_tenant_id,
                name="Mia",
                avatar_url="",
                age=7,
                level="starter",
                learning_goal="Read short stories",
                preferred_review_duration_minutes=12,
                parent_notes="",
                created_at=now,
                updated_at=now,
            )
        )
        db.commit()
    return {"tenant_id": resolved_tenant_id, "child_id": child_id}


def _seed_material_job(
    prefix: str,
    child_id: str,
    *,
    material_status: str,
    job_status: str,
    started_at: datetime,
) -> dict[str, str]:
    now = datetime(2026, 5, 31, 16, 30, tzinfo=timezone.utc)
    material_id = f"{prefix}_material"
    job_id = f"{prefix}_job"
    with SessionLocal() as db:
        db.add(
            CourseMaterialModel(
                id=material_id,
                child_id=child_id,
                teacher_name="Ms Lee",
                lesson_date=date(2026, 5, 31),
                title=f"{prefix} Worksheet",
                topic="phonics",
                status=material_status,
                image_records=[],
                learning_assets=[
                    {
                        "generated_image_status": "ready",
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
                status=job_status,
                confidence_summary="OCR provider timeout" if job_status == JobStatus.failed.value else "",
                warnings=["OCR provider timeout"] if job_status == JobStatus.failed.value else [],
                started_at=started_at,
                finished_at=now if job_status in {JobStatus.ready.value, JobStatus.failed.value} else None,
            )
        )
        db.commit()
    return {"material_id": material_id, "job_id": job_id}


def _issue_by_resource(payload: dict, resource_type: str, resource_id: str) -> dict:
    return next(
        issue
        for issue in payload["issues"]
        if issue["related_resource"]["type"] == resource_type
        and issue["related_resource"]["id"] == resource_id
    )


def test_build_admin_operations_returns_ok_summary_and_empty_issues_without_failures() -> None:
    fixture = _seed_tenant("ops_ok")
    _seed_material_job(
        "ops_ok_ready",
        fixture["child_id"],
        material_status=MaterialStatus.ready.value,
        job_status=JobStatus.ready.value,
        started_at=datetime(2026, 5, 31, 15, 30, tzinfo=timezone.utc),
    )

    with SessionLocal() as db:
        payload = build_admin_operations(db, tenant_scope=fixture["tenant_id"])

    assert payload["summary"]["severity"] == "ok"
    assert payload["issues"] == []


def test_build_admin_operations_classifies_failed_and_stale_material_job_issues() -> None:
    fixture = _seed_tenant("ops_issues")
    failed = _seed_material_job(
        "ops_issues_failed",
        fixture["child_id"],
        material_status=MaterialStatus.failed.value,
        job_status=JobStatus.failed.value,
        started_at=datetime(2026, 5, 31, 14, 45, tzinfo=timezone.utc),
    )
    stale = _seed_material_job(
        "ops_issues_stale",
        fixture["child_id"],
        material_status=MaterialStatus.processing.value,
        job_status=JobStatus.processing.value,
        started_at=datetime.now(timezone.utc) - timedelta(minutes=45),
    )
    archived = _seed_material_job(
        "ops_issues_archived",
        fixture["child_id"],
        material_status=MaterialStatus.archived.value,
        job_status=JobStatus.failed.value,
        started_at=datetime(2026, 5, 31, 14, 30, tzinfo=timezone.utc),
    )

    with SessionLocal() as db:
        payload = build_admin_operations(db, tenant_scope=fixture["tenant_id"])

    failed_issue = _issue_by_resource(payload, "material_parse_job", failed["job_id"])
    stale_issue = _issue_by_resource(payload, "material_parse_job", stale["job_id"])
    assert payload["summary"]["severity"] == "critical"
    assert failed_issue["severity"] == "critical"
    assert failed_issue["recommended_action"] == "retry_material_job"
    assert failed_issue["required_permission"] == "admin.material.retry"
    assert failed_issue["related_resource"]["tenant_id"] == fixture["tenant_id"]
    assert failed_issue["source"] == "database_snapshot"
    assert stale_issue["severity"] == "warning"
    assert stale_issue["recommended_action"] == "inspect_material_job"
    assert stale_issue["source"] == "database_snapshot"
    assert archived["job_id"] not in str(payload["issues"])


def test_build_admin_operations_includes_provider_readiness_and_bounded_latest_lists() -> None:
    fixture = _seed_tenant("ops_provider")
    for index in range(7):
        _seed_material_job(
            f"ops_provider_failed_{index}",
            fixture["child_id"],
            material_status=MaterialStatus.failed.value,
            job_status=JobStatus.failed.value,
            started_at=datetime(2026, 5, 31, 13, index, tzinfo=timezone.utc),
        )
    with SessionLocal() as db:
        db.add(
            TenantProviderPolicyModel(
                tenant_id=fixture["tenant_id"],
                ai_provider="doubao",
                media_provider="real",
                fallback_mode="per_tenant",
                monthly_guardrail=500,
                source="tenant_override",
                reason="Use real provider",
                created_by="admin_operations_test",
                created_at=datetime(2026, 5, 31, 16, 0, tzinfo=timezone.utc),
                updated_at=datetime(2026, 5, 31, 16, 0, tzinfo=timezone.utc),
            )
        )
        db.commit()
        payload = build_admin_operations(db, tenant_scope=fixture["tenant_id"])

    assert len(payload["material_parse_jobs"]["latest_failed"]) == 5
    assert payload["provider_configuration"]["tenant_overrides"][0]["tenant_id"] == fixture["tenant_id"]
    assert payload["provider_configuration"]["tenant_overrides"][0]["media_provider"] == "real"
    assert "readiness" in payload["provider_configuration"]["runtime"]


def test_build_admin_operations_tenant_scope_limits_issues_without_disclosure() -> None:
    visible = _seed_tenant("ops_scope_visible")
    hidden = _seed_tenant("ops_scope_hidden")
    _seed_material_job(
        "ops_scope_visible_failed",
        visible["child_id"],
        material_status=MaterialStatus.failed.value,
        job_status=JobStatus.failed.value,
        started_at=datetime(2026, 5, 31, 14, 45, tzinfo=timezone.utc),
    )
    _seed_material_job(
        "ops_scope_hidden_failed",
        hidden["child_id"],
        material_status=MaterialStatus.failed.value,
        job_status=JobStatus.failed.value,
        started_at=datetime(2026, 5, 31, 14, 45, tzinfo=timezone.utc),
    )
    with SessionLocal() as db:
        db.add(
            SpeakingAttemptModel(
                id="ops_scope_visible_attempt",
                child_id=visible["child_id"],
                material_id="ops_scope_visible_failed_material",
                prompt_text="Read this sentence",
                target_text="Read this sentence",
                status=SpeakingAttemptStatus.failed.value,
                failure_reason="Speech provider timeout",
                provider="stub",
                created_at=datetime(2026, 5, 31, 15, 0, tzinfo=timezone.utc),
                updated_at=datetime(2026, 5, 31, 15, 0, tzinfo=timezone.utc),
            )
        )
        db.commit()

        payload = build_admin_operations(db, tenant_scope=visible["tenant_id"])

    assert payload["summary"]["severity"] == "critical"
    assert all(issue["related_resource"]["tenant_id"] == visible["tenant_id"] for issue in payload["issues"])
    assert "ops_scope_hidden" not in str(payload["issues"])
    speaking_issue = _issue_by_resource(payload, "speaking_attempt", "ops_scope_visible_attempt")
    assert speaking_issue["recommended_action"] == "inspect_speaking_attempt"
