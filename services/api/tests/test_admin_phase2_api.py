from __future__ import annotations

from collections.abc import Iterator
import hashlib
import json
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import event

from app.core.db import SessionLocal, engine
from app.core.settings import get_settings
from app.db.models import (
    AdminAuditEventModel,
    AdminImpersonationSessionModel,
    ChildProfileModel,
    CourseMaterialModel,
    MaterialParseJobModel,
    ParentAccountModel,
    SpeakingAttemptModel,
    TenantModuleSettingModel,
    TenantProviderPolicyModel,
    WeeklyReportModel,
)
from app.models.contracts import JobStatus, MaterialStatus, SpeakingAttemptStatus
from conftest import configure_test_environment


configure_test_environment("learning-english-api-admin-phase2-")


@pytest.fixture(autouse=True)
def clear_settings_cache_between_phase2_tests() -> Iterator[None]:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


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


def _seed_tenant_detail_fixture(*, tenant_id: str, display_name: str, phone_number: str = "13800139001") -> dict:
    child_a_id = f"child_{tenant_id}_a"
    child_b_id = f"child_{tenant_id}_b"
    material_id = f"material_{tenant_id}"
    now = datetime(2026, 5, 28, 15, 0, tzinfo=timezone.utc)
    with SessionLocal() as db:
        db.add(
            ParentAccountModel(
                id=tenant_id,
                display_name=display_name,
                avatar_url="http://testserver/avatar.png",
                phone_number=phone_number,
                phone_verified_at=now,
                wechat_union_id=f"wechat_union_{tenant_id}",
                wechat_open_id=f"wechat_open_{tenant_id}",
                created_at=now,
                updated_at=now,
            )
        )
        db.add_all(
            [
                ChildProfileModel(
                    id=child_a_id,
                    parent_account_id=tenant_id,
                    name="Ivy",
                    avatar_url="",
                    age=7,
                    level="starter",
                    learning_goal="Read short phonics stories",
                    preferred_review_duration_minutes=12,
                    parent_notes="Needs gentle speaking prompts.",
                    created_at=now,
                    updated_at=now,
                ),
                ChildProfileModel(
                    id=child_b_id,
                    parent_account_id=tenant_id,
                    name="Leo",
                    avatar_url="",
                    age=5,
                    level="pre-starter",
                    learning_goal="Build picture-word confidence",
                    preferred_review_duration_minutes=8,
                    parent_notes="",
                    created_at=now,
                    updated_at=now,
                ),
            ]
        )
        db.add(
            CourseMaterialModel(
                id=material_id,
                child_id=child_a_id,
                teacher_name="Emma",
                lesson_date=date(2026, 5, 25),
                title="Tenant Detail Worksheet",
                topic="phonics",
                status="failed",
                source_images=["http://testserver/uploads/tenant-detail.jpg"],
                image_records=[
                    {
                        "id": "page_001",
                        "page_index": 1,
                        "url": "http://testserver/uploads/tenant-detail.jpg",
                        "source_type": "gallery",
                    }
                ],
                learning_assets=[
                    {
                        "id": "asset_failed",
                        "text": "queen",
                        "kind": "word",
                        "generated_image_status": "failed",
                        "tts_us_status": "ready",
                        "tts_uk_status": "failed",
                    },
                    {
                        "id": "asset_ready",
                        "text": "rabbit",
                        "kind": "word",
                        "generated_image_status": "ready",
                        "tts_us_status": "ready",
                        "tts_uk_status": "ready",
                    },
                ],
                created_at=now,
                updated_at=now,
            )
        )
        db.add(
            MaterialParseJobModel(
                id=f"job_{tenant_id}",
                material_id=material_id,
                status="failed",
                confidence_summary="Media generation failed for two assets.",
                warnings=["Image generation timeout", "UK TTS timeout"],
                started_at=now,
                finished_at=now,
                draft_learning_assets=[],
            )
        )
        db.add(
            WeeklyReportModel(
                id=f"report_{tenant_id}",
                child_id=child_a_id,
                week_start=date(2026, 5, 18),
                week_end=date(2026, 5, 24),
                completed_sessions=3,
                reviewed_words=18,
                speaking_attempts=2,
                weak_items=["queen"],
                recommended_actions=["Repeat /kw/ sound"],
            )
        )
        db.add_all(
            [
                SpeakingAttemptModel(
                    id=f"attempt_{tenant_id}_scored",
                    child_id=child_a_id,
                    material_id=material_id,
                    prompt_text="Say queen.",
                    target_text="queen",
                    status=SpeakingAttemptStatus.scored.value,
                    overall_score=82.5,
                    provider="stub",
                    created_at=now,
                    updated_at=now,
                ),
                SpeakingAttemptModel(
                    id=f"attempt_{tenant_id}_failed",
                    child_id=child_a_id,
                    material_id=material_id,
                    prompt_text="Say rabbit.",
                    target_text="rabbit",
                    status=SpeakingAttemptStatus.failed.value,
                    failure_reason="Audio was too short.",
                    provider="stub",
                    created_at=now,
                    updated_at=now,
                ),
            ]
        )
        db.add(
            AdminAuditEventModel(
                id=f"audit_{tenant_id}_prior",
                actor_id="admin_ops",
                actor_role="Operations",
                tenant_scope=tenant_id,
                action="admin.provider_policy.override",
                resource_type="tenant_provider_policy",
                resource_id=tenant_id,
                risk_level="high",
                result="success",
                reason="Task 3 prior audit fixture",
                trace_id=f"req_{tenant_id}_prior",
                content_json={},
                created_at=now,
            )
        )
        db.commit()
    return {"tenant_id": tenant_id, "child_a_id": child_a_id, "child_b_id": child_b_id, "material_id": material_id}


def _seed_additional_tenant_activity(*, tenant_id: str, child_id: str, material_id: str, count: int = 7) -> None:
    now = datetime(2026, 5, 28, 16, 0, tzinfo=timezone.utc)
    with SessionLocal() as db:
        for index in range(count):
            extra_child_id = f"child_{tenant_id}_extra_{index}"
            extra_material_id = f"material_{tenant_id}_extra_{index}"
            db.add(
                ChildProfileModel(
                    id=extra_child_id,
                    parent_account_id=tenant_id,
                    name=f"Extra {index}",
                    avatar_url="",
                    age=6,
                    level="starter",
                    learning_goal="Bounded history coverage",
                    preferred_review_duration_minutes=10,
                    parent_notes="",
                    created_at=now,
                    updated_at=now,
                )
            )
            db.add(
                WeeklyReportModel(
                    id=f"report_{tenant_id}_extra_{index}",
                    child_id=extra_child_id,
                    week_start=date(2026, 5, 11),
                    week_end=date(2026, 5, 17),
                    completed_sessions=1,
                    reviewed_words=2,
                    speaking_attempts=1,
                    weak_items=[f"weak_{index}"],
                    recommended_actions=[f"action_{index}"],
                )
            )
            db.add(
                CourseMaterialModel(
                    id=extra_material_id,
                    child_id=child_id,
                    teacher_name="Emma",
                    lesson_date=date(2026, 5, 25),
                    title=f"Extra Material {index}",
                    topic="phonics",
                    status="ready",
                    source_images=[],
                    image_records=[],
                    learning_assets=[],
                    created_at=now,
                    updated_at=now,
                )
            )
            db.add(
                MaterialParseJobModel(
                    id=f"job_{tenant_id}_extra_{index}",
                    material_id=extra_material_id,
                    status="ready",
                    confidence_summary="Ready",
                    warnings=[],
                    started_at=now,
                    finished_at=now,
                    draft_learning_assets=[],
                )
            )
            db.add(
                SpeakingAttemptModel(
                    id=f"attempt_{tenant_id}_extra_{index}",
                    child_id=child_id,
                    material_id=material_id,
                    prompt_text=f"Extra prompt {index}.",
                    target_text="extra",
                    status=SpeakingAttemptStatus.scored.value,
                    overall_score=70 + index,
                    provider="stub",
                    created_at=now,
                    updated_at=now,
                )
            )
        db.commit()


def _seed_operations_snapshot_fixture(*, prefix: str, failed_count: int = 3, running_count: int = 3) -> dict:
    tenant_a = _seed_tenant_detail_fixture(
        tenant_id=f"{prefix}_tenant_a",
        display_name=f"{prefix} Tenant A",
        phone_number="13800139101",
    )
    tenant_b = _seed_tenant_detail_fixture(
        tenant_id=f"{prefix}_tenant_b",
        display_name=f"{prefix} Tenant B",
        phone_number="13800139102",
    )
    now = datetime(2026, 5, 28, 17, 0, tzinfo=timezone.utc)
    stale_at = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(minutes=90)
    with SessionLocal() as db:
        db.add(
            TenantProviderPolicyModel(
                tenant_id=tenant_a["tenant_id"],
                ai_provider="doubao",
                media_provider="real",
                fallback_mode="per_tenant",
                monthly_guardrail=300,
                source="tenant_override",
                reason="Task 4 secret reason should stay server-side",
                created_by="admin_secret_owner",
                created_at=now,
                updated_at=now,
            )
        )
        db.add(
            TenantModuleSettingModel(
                tenant_id=tenant_a["tenant_id"],
                module_key="media_pipeline",
                enabled=False,
                source="tenant_override",
                reason="Task 4 module reason should stay server-side",
                created_by="admin_secret_owner",
                created_at=now,
                updated_at=now,
            )
        )
        for index in range(failed_count + running_count):
            status = JobStatus.failed.value if index < failed_count else JobStatus.processing.value
            material_status = MaterialStatus.failed.value if status == JobStatus.failed.value else MaterialStatus.processing.value
            child_id = tenant_a["child_a_id"] if index % 2 == 0 else tenant_a["child_b_id"]
            material_id = f"{prefix}_material_a_extra_{index}"
            db.add(
                CourseMaterialModel(
                    id=material_id,
                    child_id=child_id,
                    teacher_name="Emma",
                    lesson_date=date(2026, 5, 26),
                    title=f"Task 4 Extra Material {index}",
                    topic="operations",
                    status=material_status,
                    source_images=[],
                    image_records=[],
                    learning_assets=[
                        {
                            "id": f"{prefix}_asset_{index}",
                            "text": "timeout",
                            "kind": "word",
                            "generated_image_status": "failed" if status == JobStatus.failed.value else "processing",
                            "generated_image_error": "provider timeout" if status == JobStatus.failed.value else "",
                            "tts_us_status": "ready",
                            "tts_uk_status": "pending",
                        }
                    ],
                    created_at=now,
                    updated_at=now,
                )
            )
            db.add(
                MaterialParseJobModel(
                    id=f"{prefix}_job_a_extra_{index}",
                    material_id=material_id,
                    status=status,
                    confidence_summary=f"Task 4 job {status}",
                    warnings=["provider timeout"] if status == JobStatus.failed.value else [],
                    started_at=now if status == JobStatus.failed.value else stale_at,
                    finished_at=now if status == JobStatus.failed.value else None,
                    draft_learning_assets=[],
                )
            )
            if index < failed_count:
                attempt_status = SpeakingAttemptStatus.failed.value
            elif index == failed_count:
                attempt_status = SpeakingAttemptStatus.transcribing.value
            else:
                attempt_status = SpeakingAttemptStatus.queued.value
            db.add(
                SpeakingAttemptModel(
                    id=f"{prefix}_attempt_a_extra_{index}",
                    child_id=child_id,
                    material_id=tenant_a["material_id"],
                    prompt_text=f"Task 4 prompt {index}",
                    target_text="timeout",
                    status=attempt_status,
                    failure_reason="Audio provider timeout" if attempt_status == SpeakingAttemptStatus.failed.value else "",
                    provider="stub",
                    created_at=now if attempt_status == SpeakingAttemptStatus.failed.value else stale_at,
                    updated_at=now if attempt_status == SpeakingAttemptStatus.failed.value else stale_at,
                )
            )
        db.commit()
    return {"tenant_a": tenant_a, "tenant_b": tenant_b}


def _seed_operations_provider_overrides(*, prefix: str, count: int = 7) -> None:
    now = datetime(2026, 5, 28, 18, 0, tzinfo=timezone.utc)
    with SessionLocal() as db:
        for index in range(count):
            tenant_id = f"{prefix}_tenant_override_{index}"
            db.add(
                ParentAccountModel(
                    id=tenant_id,
                    display_name=f"Provider Override {index}",
                    avatar_url="",
                    phone_number=f"138001392{index:02d}",
                    phone_verified_at=now,
                    wechat_union_id=f"wechat_union_{tenant_id}",
                    wechat_open_id=f"wechat_open_{tenant_id}",
                    created_at=now,
                    updated_at=now,
                )
            )
            db.add(
                TenantProviderPolicyModel(
                    tenant_id=tenant_id,
                    ai_provider="doubao" if index % 2 == 0 else "stub",
                    media_provider="real" if index % 2 == 0 else "mock",
                    fallback_mode="per_tenant",
                    monthly_guardrail=100 + index,
                    source="tenant_override",
                    reason=f"Task 4 provider override {index}",
                    created_by="admin_provider_owner",
                    created_at=now,
                    updated_at=now,
                )
            )
        db.commit()


def _seed_impersonation_session_fixture(*, prefix: str) -> dict:
    now = datetime(2026, 5, 28, 19, 0, tzinfo=timezone.utc)
    tenant_a_id = f"{prefix}_tenant_a"
    tenant_b_id = f"{prefix}_tenant_b"
    active_newer_id = f"{prefix}_session_active_newer"
    active_older_id = f"{prefix}_session_active_older"
    active_other_id = f"{prefix}_session_active_other"
    ended_id = f"{prefix}_session_ended"
    ended_at = now + timedelta(minutes=14)
    with SessionLocal() as db:
        db.add_all(
            [
                ParentAccountModel(
                    id=tenant_a_id,
                    display_name=f"{prefix} Tenant A",
                    avatar_url="",
                    phone_number="13800139301",
                    phone_verified_at=now,
                    wechat_union_id=f"wechat_union_{tenant_a_id}",
                    wechat_open_id=f"wechat_open_{tenant_a_id}",
                    created_at=now,
                    updated_at=now,
                ),
                ParentAccountModel(
                    id=tenant_b_id,
                    display_name=f"{prefix} Tenant B",
                    avatar_url="",
                    phone_number="13800139302",
                    phone_verified_at=now,
                    wechat_union_id=f"wechat_union_{tenant_b_id}",
                    wechat_open_id=f"wechat_open_{tenant_b_id}",
                    created_at=now,
                    updated_at=now,
                ),
            ]
        )
        db.add_all(
            [
                AdminImpersonationSessionModel(
                    id=active_newer_id,
                    tenant_id=tenant_a_id,
                    target_parent_id=tenant_a_id,
                    actor_id="admin_task5_starter",
                    status="active",
                    reason="Help parent recover review flow.",
                    expires_at=now + timedelta(minutes=45),
                    created_at=now + timedelta(minutes=12),
                    updated_at=now + timedelta(minutes=12),
                ),
                AdminImpersonationSessionModel(
                    id=active_older_id,
                    tenant_id=tenant_a_id,
                    target_parent_id=tenant_a_id,
                    actor_id="admin_task5_starter",
                    status="active",
                    reason="Older active support session.",
                    expires_at=now + timedelta(minutes=30),
                    created_at=now + timedelta(minutes=5),
                    updated_at=now + timedelta(minutes=5),
                ),
                AdminImpersonationSessionModel(
                    id=active_other_id,
                    tenant_id=tenant_b_id,
                    target_parent_id=tenant_b_id,
                    actor_id="admin_task5_other",
                    status="active",
                    reason="Other tenant support session.",
                    expires_at=now + timedelta(minutes=35),
                    created_at=now + timedelta(minutes=9),
                    updated_at=now + timedelta(minutes=9),
                ),
                AdminImpersonationSessionModel(
                    id=ended_id,
                    tenant_id=tenant_a_id,
                    target_parent_id=tenant_a_id,
                    actor_id="admin_task5_starter",
                    status="ended",
                    reason="Already ended support session.",
                    expires_at=now + timedelta(minutes=25),
                    ended_at=ended_at,
                    created_at=now + timedelta(minutes=3),
                    updated_at=ended_at,
                ),
            ]
        )
        db.commit()
    return {
        "tenant_a_id": tenant_a_id,
        "tenant_b_id": tenant_b_id,
        "active_newer_id": active_newer_id,
        "active_older_id": active_older_id,
        "active_other_id": active_other_id,
        "ended_id": ended_id,
        "ended_at": ended_at,
    }


def test_admin_operations_snapshot_all_scope_returns_production_read_model(api_client, monkeypatch) -> None:
    _seed_operations_snapshot_fixture(prefix="task4_all")
    monkeypatch.setenv("AI_PROVIDER", "doubao")
    monkeypatch.setenv("MEDIA_PROVIDER", "real")
    monkeypatch.setenv("MEDIA_IMAGE_PROVIDER", "dashscope")
    monkeypatch.setenv("MEDIA_TTS_PROVIDER", "openai")
    monkeypatch.setenv("SPEECH_PROVIDER", "dashscope")
    monkeypatch.setenv("SPEECH_ASSESSMENT_PROVIDER", "dashscope")
    monkeypatch.setenv("ARK_API_KEY", "ark-task4-api-key-value")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-task4-api-key-value")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "dashscope-task4-api-key-value")
    monkeypatch.setenv("SPEECH_ASSESSMENT_APP_KEY", "speech-task4-app-key-value")
    monkeypatch.setenv("SPEECH_ASSESSMENT_SECRET_KEY", "speech-task4-secret-key-value")
    _set_admin_credentials(
        monkeypatch,
        [
            {
                "id": "admin_operations_reader",
                "display_name": "Operations Reader",
                "email": "operations-reader@example.com",
                "role": "Operations",
                "status": "active",
                "permissions": ["admin.operations.read"],
                "token_sha256": _token_hash("operations-reader-token"),
            }
        ],
    )

    response = api_client.get(
        "/v1/admin/operations?tenant_scope=all",
        headers={"X-Admin-Token": "operations-reader-token", "X-Request-ID": "req_task4_operations_all"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert set(payload.keys()) == {
        "required_permission",
        "tenant_scope",
        "summary",
        "material_parse_jobs",
        "media_generation",
        "speaking_attempts",
        "provider_configuration",
        "module_toggle_coverage",
        "issues",
        "audit_event",
        "access_context",
    }
    assert payload["required_permission"] == "admin.operations.read"
    assert payload["tenant_scope"] == "all"
    assert payload["summary"]["tenant_count"] >= 2
    assert payload["summary"]["material_parse_jobs"] >= 8
    assert payload["summary"]["media_failures"] >= 6
    assert payload["material_parse_jobs"]["by_status"]["failed"] >= 5
    assert payload["material_parse_jobs"]["by_status"]["processing"] >= 3
    assert payload["material_parse_jobs"]["stale_threshold_minutes"] == 30
    assert payload["material_parse_jobs"]["stale_processing"] >= 3
    assert payload["material_parse_jobs"]["oldest_processing_minutes"] >= 80
    assert 1 <= len(payload["material_parse_jobs"]["latest_failed"]) <= 5
    assert 1 <= len(payload["material_parse_jobs"]["latest_running"]) <= 5
    assert all(item["tenant_id"] for item in payload["material_parse_jobs"]["latest_failed"])
    assert all(item["status"] == "failed" for item in payload["material_parse_jobs"]["latest_failed"])
    assert payload["media_generation"]["materials_by_status"]["failed"] >= 5
    assert payload["media_generation"]["asset_status_fields_by_status"]["failed"] >= 6
    assert payload["media_generation"]["failure_signals"]["generated_image_status"] >= 5
    assert payload["speaking_attempts"]["by_status"]["failed"] >= 5
    assert payload["speaking_attempts"]["by_status"]["queued"] >= 2
    assert payload["speaking_attempts"]["by_status"]["transcribing"] >= 1
    assert payload["speaking_attempts"]["stale_threshold_minutes"] == 30
    assert payload["speaking_attempts"]["stale_pending"] >= 3
    assert payload["speaking_attempts"]["stale_transcribing"] >= 1
    assert payload["speaking_attempts"]["oldest_pending_minutes"] >= 80
    assert 1 <= len(payload["speaking_attempts"]["latest_failed"]) <= 5
    assert 1 <= len(payload["speaking_attempts"]["latest_pending"]) <= 5
    assert all(item["status"] == "failed" for item in payload["speaking_attempts"]["latest_failed"])
    assert payload["provider_configuration"]["global"]["tenant_id"] == "global"
    assert payload["provider_configuration"]["runtime"]["ai_provider"] == "doubao"
    assert payload["provider_configuration"]["runtime"]["media_provider"] == "real"
    assert payload["provider_configuration"]["runtime"]["media_image_provider"] == "dashscope"
    assert payload["provider_configuration"]["runtime"]["media_tts_provider"] == "openai"
    assert payload["provider_configuration"]["runtime"]["speech_provider"] == "dashscope"
    assert payload["provider_configuration"]["runtime"]["speech_assessment_provider"] == "dashscope"
    assert payload["provider_configuration"]["runtime"]["secret_presence"] == {
        "ark_api_key_configured": True,
        "openai_api_key_configured": True,
        "dashscope_api_key_configured": True,
        "speech_assessment_app_key_configured": True,
        "speech_assessment_secret_key_configured": True,
    }
    assert payload["provider_configuration"]["runtime"]["readiness"]["ai_provider_ready"] is True
    assert payload["provider_configuration"]["runtime"]["readiness"]["media_image_provider_ready"] is True
    assert payload["provider_configuration"]["runtime"]["readiness"]["media_tts_provider_ready"] is True
    assert payload["provider_configuration"]["runtime"]["readiness"]["speech_provider_ready"] is True
    assert payload["provider_configuration"]["runtime"]["readiness"]["speech_assessment_provider_ready"] is True
    tenant_overrides = payload["provider_configuration"]["tenant_overrides"]
    assert payload["provider_configuration"]["override_count"] >= 1
    assert 1 <= len(tenant_overrides) <= payload["provider_configuration"]["tenant_overrides_limit"]
    assert all(
        {"tenant_id", "ai_provider", "media_provider", "fallback_mode", "monthly_guardrail", "source"}
        <= set(policy.keys())
        for policy in tenant_overrides
    )
    assert "ark-task4-api-key-value" not in str(payload)
    assert "openai-task4-api-key-value" not in str(payload)
    assert "dashscope-task4-api-key-value" not in str(payload)
    assert "speech-task4-app-key-value" not in str(payload)
    assert "speech-task4-secret-key-value" not in str(payload)
    assert payload["module_toggle_coverage"]["tenant_count"] >= 2
    assert payload["module_toggle_coverage"]["module_keys"] == [
        "worksheet_import",
        "ai_review",
        "media_pipeline",
        "speaking_score",
        "weekly_reports",
    ]
    assert payload["module_toggle_coverage"]["disabled"] >= 1
    assert payload["summary"]["severity"] == "critical"
    assert payload["summary"]["issue_count"] == len(payload["issues"])
    assert payload["issues"]
    for issue in payload["issues"]:
        assert {
            "id",
            "severity",
            "status_label",
            "reason",
            "recommended_action",
            "required_permission",
            "related_resource",
            "source",
        } <= set(issue.keys())
        assert issue["source"] == "database_snapshot"
        assert issue["related_resource"]["tenant_id"]
    material_issue = next(
        issue
        for issue in payload["issues"]
        if issue["related_resource"]["type"] == "material_parse_job"
    )
    assert material_issue["severity"] == "critical"
    assert material_issue["recommended_action"] == "retry_material_job"
    assert material_issue["required_permission"] == "admin.material.retry"
    assert payload["audit_event"]["action"] == "admin.operations.read"
    assert payload["audit_event"]["tenant_scope"] == "all"
    assert payload["audit_event"]["trace_id"] == "req_task4_operations_all"
    assert payload["access_context"]["current_admin"]["id"] == "admin_operations_reader"
    assert "operations-reader-token" not in str(payload)


def test_admin_operations_snapshot_allows_dashboard_read_permission(api_client, monkeypatch) -> None:
    _set_admin_credentials(
        monkeypatch,
        [
            {
                "id": "admin_dashboard_reader_for_ops",
                "display_name": "Dashboard Reader",
                "email": "dashboard-reader-for-ops@example.com",
                "role": "Support Viewer",
                "status": "active",
                "permissions": ["admin.dashboard.read"],
                "token_sha256": _token_hash("dashboard-reader-for-ops-token"),
            }
        ],
    )

    response = api_client.get(
        "/v1/admin/operations?tenant_scope=all",
        headers={"X-Admin-Token": "dashboard-reader-for-ops-token"},
    )

    assert response.status_code == 200
    assert response.json()["required_permission"] == "admin.dashboard.read"


def test_admin_operations_snapshot_honors_tenant_scope_without_disclosure(api_client, monkeypatch) -> None:
    fixture = _seed_operations_snapshot_fixture(prefix="task4_scope")
    _set_admin_credentials(
        monkeypatch,
        [
            {
                "id": "admin_operations_scoped",
                "display_name": "Operations Scoped",
                "email": "operations-scoped@example.com",
                "role": "Operations",
                "status": "active",
                "permissions": ["admin.operations.read"],
                "token_sha256": _token_hash("operations-scoped-token"),
            }
        ],
    )

    scoped_response = api_client.get(
        f"/v1/admin/operations?tenant_scope={fixture['tenant_a']['tenant_id']}",
        headers={"X-Admin-Token": "operations-scoped-token"},
    )
    missing_response = api_client.get(
        "/v1/admin/operations?tenant_scope=task4_scope_missing",
        headers={"X-Admin-Token": "operations-scoped-token"},
    )

    assert scoped_response.status_code == 200
    payload = scoped_response.json()
    assert payload["tenant_scope"] == fixture["tenant_a"]["tenant_id"]
    assert payload["summary"]["tenant_count"] == 1
    assert {item["tenant_id"] for item in payload["material_parse_jobs"]["latest_failed"]} == {
        fixture["tenant_a"]["tenant_id"]
    }
    assert payload["issues"]
    assert {item["related_resource"]["tenant_id"] for item in payload["issues"]} == {
        fixture["tenant_a"]["tenant_id"]
    }
    assert fixture["tenant_b"]["tenant_id"] not in str(payload)
    assert missing_response.status_code == 404
    assert missing_response.json()["detail"] == "Tenant scope not found"


def test_admin_operations_snapshot_requires_operations_or_dashboard_permission(api_client, monkeypatch) -> None:
    _set_admin_credentials(
        monkeypatch,
        [
            {
                "id": "admin_audit_only_for_ops",
                "display_name": "Audit Only",
                "email": "audit-only-for-ops@example.com",
                "role": "Audit Viewer",
                "status": "active",
                "permissions": ["admin.audit.read"],
                "token_sha256": _token_hash("audit-only-for-ops-token"),
            }
        ],
    )

    response = api_client.get(
        "/v1/admin/operations?tenant_scope=all",
        headers={"X-Admin-Token": "audit-only-for-ops-token"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Missing admin.operations.read or admin.dashboard.read permission"


def test_admin_operations_snapshot_uses_aggregate_queries_and_bounded_latest_lists(api_client, monkeypatch) -> None:
    _seed_operations_snapshot_fixture(prefix="task4_query", failed_count=7, running_count=7)
    _seed_operations_provider_overrides(prefix="task4_query", count=7)
    _set_admin_credentials(
        monkeypatch,
        [
            {
                "id": "admin_operations_query",
                "display_name": "Operations Query",
                "email": "operations-query@example.com",
                "role": "Operations",
                "status": "active",
                "permissions": ["admin.operations.read"],
                "token_sha256": _token_hash("operations-query-token"),
            }
        ],
    )
    statements: list[str] = []

    def capture_sql(conn, cursor, statement, parameters, context, executemany) -> None:
        statements.append(" ".join(statement.lower().split()))

    event.listen(engine, "before_cursor_execute", capture_sql)
    try:
        response = api_client.get(
            "/v1/admin/operations?tenant_scope=all",
            headers={"X-Admin-Token": "operations-query-token"},
        )
    finally:
        event.remove(engine, "before_cursor_execute", capture_sql)

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["material_parse_jobs"]["latest_failed"]) == 5
    assert len(payload["material_parse_jobs"]["latest_running"]) == 5
    assert len(payload["speaking_attempts"]["latest_failed"]) == 5
    assert len(payload["speaking_attempts"]["latest_pending"]) == 5
    assert payload["provider_configuration"]["override_count"] >= 8
    assert payload["provider_configuration"]["tenant_overrides_limit"] == 5
    assert len(payload["provider_configuration"]["tenant_overrides"]) == 5
    job_selects = [statement for statement in statements if "from material_parse_jobs" in statement]
    material_selects = [statement for statement in statements if "from course_materials" in statement]
    speaking_selects = [statement for statement in statements if "from speaking_attempts" in statement]
    tenant_selects = [statement for statement in statements if "from parent_accounts" in statement]
    provider_selects = [statement for statement in statements if "from tenant_provider_policies" in statement]
    assert any("count(" in statement and "group by" in statement for statement in job_selects)
    assert any("count(" in statement and "group by" in statement for statement in material_selects)
    assert any("count(" in statement and "group by" in statement for statement in speaking_selects)
    assert any("count(" in statement for statement in tenant_selects)
    assert any("count(" in statement for statement in provider_selects)
    assert any(" limit " in statement for statement in provider_selects)
    assert any(" limit " in statement for statement in job_selects)
    assert any(" limit " in statement for statement in speaking_selects)
    assert not any("from parent_accounts order by" in statement for statement in statements)
    assert not any("tenant_module_settings.tenant_id in" in statement for statement in statements)


def test_admin_impersonation_sessions_list_active_all_scope_returns_audited_payload(api_client, monkeypatch) -> None:
    fixture = _seed_impersonation_session_fixture(prefix="task5_list_all")
    _set_admin_credentials(
        monkeypatch,
        [
            {
                "id": "admin_impersonation_reader",
                "display_name": "Impersonation Reader",
                "email": "impersonation-reader@example.com",
                "role": "Support Supervisor",
                "status": "active",
                "permissions": ["admin.impersonation.read"],
                "token_sha256": _token_hash("impersonation-reader-token"),
            }
        ],
    )

    response = api_client.get(
        "/v1/admin/impersonation-sessions",
        params={"tenant_scope": "all", "status": "active"},
        headers={"X-Admin-Token": "impersonation-reader-token", "X-Request-ID": "req_task5_list_all"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert set(payload.keys()) == {"required_permission", "tenant_scope", "status", "items", "audit_event"}
    assert payload["required_permission"] == "admin.impersonation.read"
    assert payload["tenant_scope"] == "all"
    assert payload["status"] == "active"
    assert len(payload["items"]) <= 50
    seeded_items = {item["id"]: item for item in payload["items"] if item["id"].startswith("task5_list_all_")}
    assert set(seeded_items) == {
        fixture["active_newer_id"],
        fixture["active_older_id"],
        fixture["active_other_id"],
    }
    assert {item["tenant_id"] for item in seeded_items.values()} == {fixture["tenant_a_id"], fixture["tenant_b_id"]}
    assert all(item["status"] == "active" for item in seeded_items.values())
    newest_item = seeded_items[fixture["active_newer_id"]]
    assert set(newest_item.keys()) == {
        "id",
        "tenant_id",
        "target_parent_id",
        "actor_id",
        "status",
        "reason",
        "created_at",
        "expires_at",
        "ended_at",
        "updated_at",
        "tenant_display_name",
        "target_parent_display_name",
    }
    assert newest_item["tenant_display_name"] == "task5_list_all Tenant A"
    assert newest_item["target_parent_display_name"] == "task5_list_all Tenant A"
    assert newest_item["ended_at"] == ""
    assert newest_item["created_at"] == "2026-05-28T19:12:00+00:00"
    audit_event = payload["audit_event"]
    assert audit_event["action"] == "admin.impersonation.read"
    assert audit_event["resource_type"] == "admin_impersonation_session"
    assert audit_event["resource_id"] == "list"
    assert audit_event["risk_level"] == "low"
    assert audit_event["result"] == "success"
    assert audit_event["trace_id"] == "req_task5_list_all"


def test_admin_impersonation_sessions_list_honors_scope_status_and_validation(api_client, monkeypatch) -> None:
    fixture = _seed_impersonation_session_fixture(prefix="task5_list_scope")
    _set_admin_credentials(
        monkeypatch,
        [
            {
                "id": "admin_impersonation_scope_reader",
                "display_name": "Impersonation Scope Reader",
                "email": "impersonation-scope-reader@example.com",
                "role": "Support Supervisor",
                "status": "active",
                "permissions": ["admin.impersonation.read"],
                "token_sha256": _token_hash("impersonation-scope-reader-token"),
            }
        ],
    )

    scoped_response = api_client.get(
        "/v1/admin/impersonation-sessions",
        params={"tenant_scope": fixture["tenant_a_id"], "status": "ended"},
        headers={"X-Admin-Token": "impersonation-scope-reader-token"},
    )
    invalid_scope_response = api_client.get(
        "/v1/admin/impersonation-sessions",
        params={"tenant_scope": "task5_list_scope_missing", "status": "active"},
        headers={"X-Admin-Token": "impersonation-scope-reader-token"},
    )
    invalid_status_response = api_client.get(
        "/v1/admin/impersonation-sessions",
        params={"tenant_scope": "all", "status": "suspended"},
        headers={"X-Admin-Token": "impersonation-scope-reader-token"},
    )

    assert scoped_response.status_code == 200
    payload = scoped_response.json()
    assert payload["tenant_scope"] == fixture["tenant_a_id"]
    assert payload["status"] == "ended"
    assert [item["id"] for item in payload["items"]] == [fixture["ended_id"]]
    assert payload["items"][0]["ended_at"] == "2026-05-28T19:14:00+00:00"
    assert fixture["tenant_b_id"] not in str(payload)
    assert invalid_scope_response.status_code == 404
    assert invalid_scope_response.json()["detail"] == "Tenant scope not found"
    assert invalid_status_response.status_code == 422
    assert invalid_status_response.json()["detail"] == "Unsupported impersonation session status"


def test_admin_impersonation_sessions_list_requires_read_permission(api_client, monkeypatch) -> None:
    _set_admin_credentials(
        monkeypatch,
        [
            {
                "id": "admin_impersonation_start_only",
                "display_name": "Impersonation Start Only",
                "email": "impersonation-start-only@example.com",
                "role": "Support Agent",
                "status": "active",
                "permissions": ["admin.impersonation.start"],
                "token_sha256": _token_hash("impersonation-start-only-token"),
            }
        ],
    )

    response = api_client.get(
        "/v1/admin/impersonation-sessions?tenant_scope=all",
        headers={"X-Admin-Token": "impersonation-start-only-token"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Missing admin.impersonation.read permission"


def test_admin_impersonation_session_end_ends_active_session_and_records_audit(api_client, monkeypatch) -> None:
    fixture = _seed_impersonation_session_fixture(prefix="task5_end_active")
    _set_admin_credentials(
        monkeypatch,
        [
            {
                "id": "admin_impersonation_ender",
                "display_name": "Impersonation Ender",
                "email": "impersonation-ender@example.com",
                "role": "Support Supervisor",
                "status": "active",
                "permissions": ["admin.impersonation.end"],
                "token_sha256": _token_hash("impersonation-ender-token"),
            }
        ],
    )

    response = api_client.post(
        f"/v1/admin/impersonation-sessions/{fixture['active_newer_id']}/end",
        params={"tenant_scope": "all"},
        json={"reason": "Support handoff complete; ending parent access."},
        headers={"X-Admin-Token": "impersonation-ender-token", "X-Request-ID": "req_task5_end_active"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert set(payload.keys()) == {"required_permission", "impersonation_session", "action_result", "audit_event"}
    assert payload["required_permission"] == "admin.impersonation.end"
    session = payload["impersonation_session"]
    assert session["id"] == fixture["active_newer_id"]
    assert session["tenant_id"] == fixture["tenant_a_id"]
    assert session["target_parent_id"] == fixture["tenant_a_id"]
    assert session["status"] == "ended"
    assert session["ended_at"]
    assert session["updated_at"]
    assert session["tenant_display_name"] == "task5_end_active Tenant A"
    assert payload["action_result"] == {
        "action": "end_impersonation_session",
        "status": "success",
        "resource_type": "admin_impersonation_session",
        "resource_id": fixture["active_newer_id"],
        "tenant_id": fixture["tenant_a_id"],
        "message": "Impersonation session ended.",
    }
    audit_event = payload["audit_event"]
    assert audit_event["action"] == "admin.impersonation.end"
    assert audit_event["resource_type"] == "admin_impersonation_session"
    assert audit_event["resource_id"] == fixture["active_newer_id"]
    assert audit_event["risk_level"] == "high"
    assert audit_event["result"] == "success"
    assert audit_event["reason"] == "Support handoff complete; ending parent access."
    assert audit_event["trace_id"] == "req_task5_end_active"
    with SessionLocal() as db:
        persisted_session = db.get(AdminImpersonationSessionModel, fixture["active_newer_id"])
        assert persisted_session is not None
        assert persisted_session.status == "ended"
        assert persisted_session.ended_at is not None


def test_admin_impersonation_session_end_requires_reason(api_client, monkeypatch) -> None:
    fixture = _seed_impersonation_session_fixture(prefix="task5_end_reason")
    _set_admin_credentials(
        monkeypatch,
        [
            {
                "id": "admin_impersonation_reason_ender",
                "display_name": "Impersonation Reason Ender",
                "email": "impersonation-reason-ender@example.com",
                "role": "Support Supervisor",
                "status": "active",
                "permissions": ["admin.impersonation.end"],
                "token_sha256": _token_hash("impersonation-reason-ender-token"),
            }
        ],
    )

    response = api_client.post(
        f"/v1/admin/impersonation-sessions/{fixture['active_newer_id']}/end",
        params={"tenant_scope": "all"},
        json={"reason": "  "},
        headers={"X-Admin-Token": "impersonation-reason-ender-token"},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Impersonation end reason is required"


def test_admin_impersonation_session_end_is_idempotent_and_preserves_ended_at(api_client, monkeypatch) -> None:
    fixture = _seed_impersonation_session_fixture(prefix="task5_end_idempotent")
    _set_admin_credentials(
        monkeypatch,
        [
            {
                "id": "admin_impersonation_idempotent_ender",
                "display_name": "Impersonation Idempotent Ender",
                "email": "impersonation-idempotent-ender@example.com",
                "role": "Support Supervisor",
                "status": "active",
                "permissions": ["admin.impersonation.end"],
                "token_sha256": _token_hash("impersonation-idempotent-ender-token"),
            }
        ],
    )

    response = api_client.post(
        f"/v1/admin/impersonation-sessions/{fixture['ended_id']}/end",
        params={"tenant_scope": fixture["tenant_a_id"]},
        json={"reason": "Supervisor verified session was already closed."},
        headers={
            "X-Admin-Token": "impersonation-idempotent-ender-token",
            "X-Request-ID": "req_task5_end_idempotent",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["impersonation_session"]["status"] == "ended"
    assert payload["impersonation_session"]["ended_at"] == "2026-05-28T19:14:00+00:00"
    assert payload["action_result"] == {
        "action": "end_impersonation_session",
        "status": "noop",
        "resource_type": "admin_impersonation_session",
        "resource_id": fixture["ended_id"],
        "tenant_id": fixture["tenant_a_id"],
        "message": "Impersonation session already ended.",
    }
    assert payload["audit_event"]["action"] == "admin.impersonation.end.already_ended"
    assert payload["audit_event"]["risk_level"] == "medium"
    assert payload["audit_event"]["result"] == "noop"
    assert payload["audit_event"]["reason"] == "Supervisor verified session was already closed."
    assert payload["audit_event"]["trace_id"] == "req_task5_end_idempotent"
    with SessionLocal() as db:
        persisted_session = db.get(AdminImpersonationSessionModel, fixture["ended_id"])
        assert persisted_session is not None
        assert persisted_session.ended_at == fixture["ended_at"].replace(tzinfo=None)


def test_admin_impersonation_session_end_honors_scope_without_disclosure(api_client, monkeypatch) -> None:
    fixture = _seed_impersonation_session_fixture(prefix="task5_end_scope")
    _set_admin_credentials(
        monkeypatch,
        [
            {
                "id": "admin_impersonation_scoped_ender",
                "display_name": "Impersonation Scoped Ender",
                "email": "impersonation-scoped-ender@example.com",
                "role": "Support Supervisor",
                "status": "active",
                "permissions": ["admin.impersonation.end"],
                "token_sha256": _token_hash("impersonation-scoped-ender-token"),
            }
        ],
    )

    out_of_scope_response = api_client.post(
        f"/v1/admin/impersonation-sessions/{fixture['active_other_id']}/end",
        params={"tenant_scope": fixture["tenant_a_id"]},
        json={"reason": "Scoped support supervisor requested end."},
        headers={"X-Admin-Token": "impersonation-scoped-ender-token"},
    )
    missing_response = api_client.post(
        "/v1/admin/impersonation-sessions/task5_end_scope_missing/end",
        params={"tenant_scope": fixture["tenant_a_id"]},
        json={"reason": "Scoped support supervisor requested end."},
        headers={"X-Admin-Token": "impersonation-scoped-ender-token"},
    )

    assert out_of_scope_response.status_code == 404
    assert out_of_scope_response.json()["detail"] == "Impersonation session not found"
    assert missing_response.status_code == 404
    assert missing_response.json() == out_of_scope_response.json()


def test_admin_impersonation_start_uses_generic_tenant_not_found_for_out_of_scope(api_client, monkeypatch) -> None:
    fixture = _seed_impersonation_session_fixture(prefix="task5_start_scope")
    _set_admin_credentials(
        monkeypatch,
        [
            {
                "id": "admin_impersonation_starter_scope",
                "display_name": "Impersonation Starter Scope",
                "email": "impersonation-starter-scope@example.com",
                "role": "Support Supervisor",
                "status": "active",
                "permissions": ["admin.impersonation.start"],
                "token_sha256": _token_hash("impersonation-starter-scope-token"),
            }
        ],
    )

    out_of_scope_response = api_client.post(
        "/v1/admin/impersonation-sessions",
        params={"tenant_scope": fixture["tenant_a_id"]},
        json={
            "tenant_id": fixture["tenant_b_id"],
            "target_parent_id": fixture["tenant_b_id"],
            "reason": "Need supervised support session.",
        },
        headers={"X-Admin-Token": "impersonation-starter-scope-token"},
    )
    missing_response = api_client.post(
        "/v1/admin/impersonation-sessions",
        params={"tenant_scope": fixture["tenant_a_id"]},
        json={
            "tenant_id": "task5_start_scope_missing",
            "target_parent_id": "task5_start_scope_missing",
            "reason": "Need supervised support session.",
        },
        headers={"X-Admin-Token": "impersonation-starter-scope-token"},
    )

    assert out_of_scope_response.status_code == 404
    assert out_of_scope_response.json()["detail"] == "Tenant not found"
    assert missing_response.status_code == 404
    assert missing_response.json() == out_of_scope_response.json()


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


def test_admin_tenant_detail_returns_admin_read_model_for_all_scope(api_client, monkeypatch) -> None:
    fixture = _seed_tenant_detail_fixture(tenant_id="tenant_task3_primary", display_name="Task 3 Family")
    _set_admin_credentials(
        monkeypatch,
        [
            {
                "id": "admin_tenant_reader",
                "display_name": "Tenant Reader",
                "email": "tenant-reader@example.com",
                "role": "Support Viewer",
                "status": "active",
                "permissions": ["admin.tenant.read"],
                "token_sha256": _token_hash("tenant-reader-token"),
            }
        ],
    )

    response = api_client.get(
        f"/v1/admin/tenants/{fixture['tenant_id']}?tenant_scope=all",
        headers={"X-Admin-Token": "tenant-reader-token", "X-Request-ID": "req_task3_read"},
    )

    assert response.status_code == 200
    payload = response.json()
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
        "audit_event",
        "access_context",
    }
    assert payload["required_permission"] == "admin.tenant.read"
    assert payload["tenant"] == {
        "id": "tenant_task3_primary",
        "name": "Task 3 Family",
        "display_name": "Task 3 Family",
        "avatar_url": "http://testserver/avatar.png",
        "phone_number": "13800139001",
        "phone_verified_at": "2026-05-28T15:00:00+00:00",
        "wechat_union_id": "wechat_union_tenant_task3_primary",
        "wechat_open_id": "wechat_open_tenant_task3_primary",
        "tenant_type": "pilot_family",
        "status": "warning",
        "region": "local",
        "tier": "pilot",
        "created_at": "2026-05-28T15:00:00+00:00",
        "updated_at": "2026-05-28T15:00:00+00:00",
    }
    assert payload["summary"] == {
        "active_parents": 1,
        "children": 2,
        "materials": 1,
        "ready_materials": 0,
        "failed_materials": 1,
        "processing_materials": 0,
    }
    assert [child["id"] for child in payload["children"]] == [fixture["child_a_id"], fixture["child_b_id"]]
    assert payload["children"][0]["name"] == "Ivy"
    assert payload["children"][0]["weekly_report_id"] == "report_tenant_task3_primary"
    assert payload["children"][0]["speaking_attempts"] == 2
    assert payload["materials"][0]["id"] == fixture["material_id"]
    assert payload["materials"][0]["tenant_id"] == "tenant_task3_primary"
    assert payload["provider_policy"]["tenant_id"] == "tenant_task3_primary"
    assert any(item["module_key"] == "weekly_reports" for item in payload["module_settings"])
    assert payload["weekly_reports"]["total"] == 1
    assert payload["weekly_reports"]["latest"]["id"] == "report_tenant_task3_primary"
    assert payload["weekly_reports"]["completed_sessions"] == 3
    assert payload["weekly_reports"]["reviewed_words"] == 18
    assert payload["speaking_attempts"]["total"] == 2
    assert payload["speaking_attempts"]["by_status"] == {
        "queued": 0,
        "recording_uploaded": 0,
        "transcribing": 0,
        "scored": 1,
        "failed": 1,
    }
    assert payload["speaking_attempts"]["failed"] == 1
    assert payload["risk_summary"]["risk_level"] == "high"
    assert payload["risk_summary"]["media_failure_count"] == 2
    assert payload["risk_summary"]["media_failures"] == 2
    assert payload["risk_summary"]["failed_material_jobs"] == 1
    assert payload["risk_summary"]["failed_jobs"] == 1
    assert payload["risk_summary"]["failed_speaking_attempts"] == 1
    assert payload["audit_event"]["action"] == "admin.tenant.read"
    assert payload["audit_event"]["trace_id"] == "req_task3_read"
    assert payload["access_context"]["current_admin"]["id"] == "admin_tenant_reader"
    assert payload["access_context"]["current_admin"]["role"] == "Support Viewer"
    assert payload["access_context"]["recent_audit_events"] == []
    assert "tenant-reader-token" not in str(payload)


def test_admin_tenant_detail_gates_recent_audit_history_behind_audit_read(api_client, monkeypatch) -> None:
    fixture = _seed_tenant_detail_fixture(tenant_id="tenant_task3_audit_gate", display_name="Audit Gate Family")
    _set_admin_credentials(
        monkeypatch,
        [
            {
                "id": "admin_tenant_auditor",
                "display_name": "Tenant Auditor",
                "email": "tenant-auditor@example.com",
                "role": "Audit Viewer",
                "status": "active",
                "permissions": ["admin.tenant.read", "admin.audit.read"],
                "token_sha256": _token_hash("tenant-auditor-token"),
            }
        ],
    )

    response = api_client.get(
        f"/v1/admin/tenants/{fixture['tenant_id']}?tenant_scope=all",
        headers={"X-Admin-Token": "tenant-auditor-token", "X-Request-ID": "req_task3_audit_gate"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["audit_event"]["trace_id"] == "req_task3_audit_gate"
    assert payload["access_context"]["recent_audit_events"]
    assert payload["access_context"]["recent_audit_events"][0]["action"] == "admin.tenant.read"
    assert payload["access_context"]["recent_audit_events"][0]["trace_id"] == "req_task3_audit_gate"


def test_admin_tenant_detail_requires_tenant_read_permission(api_client, monkeypatch) -> None:
    _seed_tenant_detail_fixture(tenant_id="tenant_task3_forbidden", display_name="Forbidden Family")
    _set_admin_credentials(
        monkeypatch,
        [
            {
                "id": "admin_without_tenant_read",
                "display_name": "Dashboard Only",
                "email": "dashboard-only@example.com",
                "role": "Dashboard Viewer",
                "status": "active",
                "permissions": ["admin.dashboard.read"],
                "token_sha256": _token_hash("dashboard-only-token"),
            }
        ],
    )

    response = api_client.get(
        "/v1/admin/tenants/tenant_task3_forbidden?tenant_scope=all",
        headers={"X-Admin-Token": "dashboard-only-token"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Missing admin.tenant.read permission"


def test_admin_tenant_detail_honors_tenant_scope_without_disclosure(api_client, monkeypatch) -> None:
    _seed_tenant_detail_fixture(tenant_id="tenant_task3_scoped", display_name="Scoped Family")
    _seed_tenant_detail_fixture(tenant_id="tenant_task3_other", display_name="Other Family", phone_number="13800139002")
    _set_admin_credentials(
        monkeypatch,
        [
            {
                "id": "admin_scoped_reader",
                "display_name": "Scoped Reader",
                "email": "scoped-reader@example.com",
                "role": "Tenant Support",
                "status": "active",
                "permissions": ["admin.tenant.read"],
                "token_sha256": _token_hash("scoped-reader-token"),
            }
        ],
    )

    scoped_response = api_client.get(
        "/v1/admin/tenants/tenant_task3_scoped?tenant_scope=tenant_task3_scoped",
        headers={"X-Admin-Token": "scoped-reader-token"},
    )
    out_of_scope_response = api_client.get(
        "/v1/admin/tenants/tenant_task3_other?tenant_scope=tenant_task3_scoped",
        headers={"X-Admin-Token": "scoped-reader-token"},
    )
    missing_response = api_client.get(
        "/v1/admin/tenants/tenant_task3_missing?tenant_scope=tenant_task3_scoped",
        headers={"X-Admin-Token": "scoped-reader-token"},
    )

    assert scoped_response.status_code == 200
    assert scoped_response.json()["tenant"]["id"] == "tenant_task3_scoped"
    assert out_of_scope_response.status_code == 404
    assert out_of_scope_response.json()["detail"] == "Tenant not found"
    assert missing_response.status_code == 404
    assert missing_response.json() == out_of_scope_response.json()


def test_admin_tenant_detail_uses_aggregate_queries_and_bounded_latest_lists(api_client, monkeypatch) -> None:
    fixture = _seed_tenant_detail_fixture(tenant_id="tenant_task3_bounded", display_name="Bounded Family")
    _seed_additional_tenant_activity(
        tenant_id=fixture["tenant_id"],
        child_id=fixture["child_a_id"],
        material_id=fixture["material_id"],
    )
    _set_admin_credentials(
        monkeypatch,
        [
            {
                "id": "admin_bounded_reader",
                "display_name": "Bounded Reader",
                "email": "bounded-reader@example.com",
                "role": "Support Viewer",
                "status": "active",
                "permissions": ["admin.tenant.read"],
                "token_sha256": _token_hash("bounded-reader-token"),
            }
        ],
    )
    statements: list[str] = []

    def capture_sql(conn, cursor, statement, parameters, context, executemany) -> None:
        statements.append(" ".join(statement.lower().split()))

    event.listen(engine, "before_cursor_execute", capture_sql)
    try:
        response = api_client.get(
            f"/v1/admin/tenants/{fixture['tenant_id']}?tenant_scope=all",
            headers={"X-Admin-Token": "bounded-reader-token"},
        )
    finally:
        event.remove(engine, "before_cursor_execute", capture_sql)

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["materials"] == 8
    assert len(payload["materials"]) == 5
    assert fixture["material_id"] not in {material["id"] for material in payload["materials"]}
    assert payload["risk_summary"]["media_failure_count"] == 2
    assert payload["risk_summary"]["media_failures"] == 2
    assert payload["risk_summary"]["failed_materials"] == 1
    assert payload["risk_summary"]["failed_material_jobs"] == 1
    assert payload["weekly_reports"]["total"] == 8
    assert len(payload["weekly_reports"]["history"]) == 5
    assert payload["speaking_attempts"]["total"] == 9
    assert len(payload["speaking_attempts"]["latest"]) == 5
    weekly_selects = [statement for statement in statements if "from weekly_reports" in statement]
    speaking_selects = [statement for statement in statements if "from speaking_attempts" in statement]
    assert any("count(" in statement for statement in weekly_selects)
    assert any(" limit " in statement for statement in weekly_selects)
    assert any("count(" in statement for statement in speaking_selects)
    assert any(" limit " in statement for statement in speaking_selects)


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
    _seed_audit_event(audit_id="audit_task2_010", resource_id="material_task2_other", created_at=created_at)

    first_page = api_client.get(
        "/v1/admin/audit-events",
        params={
            "tenant_scope": "tenant_task2_a",
            "action": "admin.material.archive",
            "resource_type": "course_material",
            "resource_id": "material_task2",
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
            "resource_id": "material_task2",
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


def test_admin_audit_events_return_empty_page_for_cursor_outside_active_filter(api_client, monkeypatch) -> None:
    _set_admin_credentials(
        monkeypatch,
        [
            {
                "id": "admin_cursor_match",
                "display_name": "Cursor Match Admin",
                "email": "cursor-match@example.com",
                "role": "Audit Viewer",
                "status": "active",
                "permissions": ["admin.audit.read"],
                "token_sha256": _token_hash("cursor-match-token"),
            }
        ],
    )
    created_at = datetime(2026, 5, 28, 12, 30, tzinfo=timezone.utc)
    _seed_audit_event(
        audit_id="audit_task2_cursor_match_001",
        actor_id="admin_cursor_match",
        tenant_scope="tenant_task2_cursor_match",
        action="admin.task2.cursor_match",
        created_at=created_at,
    )
    _seed_audit_event(
        audit_id="audit_task2_cursor_match_002",
        actor_id="admin_cursor_match",
        tenant_scope="tenant_task2_cursor_match",
        action="admin.task2.cursor_match",
        created_at=created_at,
    )
    _seed_audit_event(
        audit_id="audit_task2_cursor_other_999",
        actor_id="admin_cursor_other",
        tenant_scope="tenant_task2_cursor_other",
        action="admin.task2.cursor_other",
        created_at=created_at,
    )

    response = api_client.get(
        "/v1/admin/audit-events",
        params={
            "tenant_scope": "tenant_task2_cursor_match",
            "action": "admin.task2.cursor_match",
            "actor_id": "admin_cursor_match",
            "cursor": "audit_task2_cursor_other_999",
        },
        headers={"X-Admin-Token": "cursor-match-token"},
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
