from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Literal, Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.db.models import (
    ChildProfileModel,
    CourseMaterialModel,
    MaterialParseJobModel,
    ParentAccountModel,
    SpeakingAttemptModel,
    TenantModuleSettingModel,
    TenantProviderPolicyModel,
)
from app.models.contracts import JobStatus, MaterialStatus, MediaGenerationStatus, SpeakingAttemptStatus
from app.services.admin_permissions import ADMIN_MATERIAL_RETRY, ADMIN_OPERATIONS_READ
from app.services.admin_scope import (
    ensure_admin_tenant_scope,
    tenant_child_scope_filter,
    tenant_module_setting_scope_filter,
    tenant_provider_policy_scope_filter,
)

IssueSeverity = Literal["ok", "info", "warning", "critical"]

MODULE_KEYS = ("worksheet_import", "ai_review", "media_pipeline", "speaking_score", "weekly_reports")
OPERATIONS_LATEST_LIMIT = 5
OPERATIONS_STALE_THRESHOLD_MINUTES = 30
PROVIDER_OVERRIDE_SAMPLE_LIMIT = 5
DATABASE_SNAPSHOT_SOURCE = "database_snapshot"


def build_admin_operations(db: Session, tenant_scope: str) -> dict[str, Any]:
    ensure_admin_tenant_scope(db, tenant_scope)
    tenant_count = _operations_tenant_count(db, tenant_scope)
    material_status_counts = _operations_material_status_counts(db, tenant_scope)
    material_parse_jobs = _operations_material_parse_job_payload(db, tenant_scope)
    media_generation = _operations_media_generation_payload(db, tenant_scope, material_status_counts)
    speaking_attempts = _operations_speaking_attempts_payload(db, tenant_scope)
    provider_configuration = _operations_provider_configuration_payload(db, tenant_scope)
    module_toggle_coverage = _operations_module_toggle_coverage_payload(db, tenant_scope, tenant_count)
    issues = build_operations_issues(db, tenant_scope)
    return {
        "tenant_scope": tenant_scope,
        "summary": {
            "tenant_count": tenant_count,
            "materials": sum(material_status_counts.values()),
            "material_parse_jobs": material_parse_jobs["total"],
            "media_failures": media_generation["failure_signals"]["total"],
            "speaking_attempts": speaking_attempts["total"],
            "severity": _operations_summary_severity(issues),
            "issue_count": len(issues),
        },
        "material_parse_jobs": material_parse_jobs,
        "media_generation": media_generation,
        "speaking_attempts": speaking_attempts,
        "provider_configuration": provider_configuration,
        "module_toggle_coverage": module_toggle_coverage,
        "issues": issues,
    }


def build_operations_issues(db: Session, tenant_scope: str) -> list[dict[str, Any]]:
    failed_material_jobs = _latest_operations_material_job_rows(
        db,
        tenant_scope,
        [JobStatus.failed.value],
        exclude_material_statuses=[MaterialStatus.ready.value, MaterialStatus.archived.value],
    )
    stale_processing_jobs = _latest_stale_operations_material_job_rows(db, tenant_scope)
    failed_speaking_attempts = _latest_operations_speaking_attempt_rows(
        db,
        tenant_scope,
        [SpeakingAttemptStatus.failed.value],
    )
    stale_speaking_attempts = _latest_stale_operations_speaking_attempt_rows(db, tenant_scope)

    issues: list[dict[str, Any]] = []
    for job, material, child, parent in failed_material_jobs:
        issue = classify_material_job_issue(job, material, child, parent)
        if issue is not None:
            issues.append(issue)
    for job, material, child, parent in stale_processing_jobs:
        issue = classify_material_job_issue(job, material, child, parent)
        if issue is not None:
            issues.append(issue)
    for attempt, child, parent in failed_speaking_attempts:
        issue = classify_speaking_attempt_issue(attempt, child, parent)
        if issue is not None:
            issues.append(issue)
    for attempt, child, parent in stale_speaking_attempts:
        issue = classify_speaking_attempt_issue(attempt, child, parent)
        if issue is not None:
            issues.append(issue)
    return _dedupe_operations_issues(issues)


def classify_material_job_issue(
    job: MaterialParseJobModel,
    material: CourseMaterialModel,
    child: ChildProfileModel,
    parent: ParentAccountModel,
) -> Optional[dict[str, Any]]:
    if material.status in {MaterialStatus.ready.value, MaterialStatus.archived.value}:
        return None
    if job.status == JobStatus.failed.value:
        return _operations_issue_payload(
            issue_id=f"issue_material_job_{job.id}_failed",
            severity="critical",
            status_label="Parse failed",
            reason=_job_failure_reason(job),
            recommended_action="retry_material_job",
            required_permission=ADMIN_MATERIAL_RETRY,
            related_resource={
                "type": "material_parse_job",
                "id": job.id,
                "tenant_id": parent.id,
                "material_id": material.id,
                "child_id": child.id,
            },
        )
    if job.status == JobStatus.processing.value and _age_minutes(job.started_at) >= OPERATIONS_STALE_THRESHOLD_MINUTES:
        return _operations_issue_payload(
            issue_id=f"issue_material_job_{job.id}_stale",
            severity="warning",
            status_label="Parse processing stale",
            reason=f"Material parse job has been processing for at least {OPERATIONS_STALE_THRESHOLD_MINUTES} minutes.",
            recommended_action="inspect_material_job",
            required_permission=ADMIN_OPERATIONS_READ,
            related_resource={
                "type": "material_parse_job",
                "id": job.id,
                "tenant_id": parent.id,
                "material_id": material.id,
                "child_id": child.id,
            },
        )
    return None


def classify_speaking_attempt_issue(
    attempt: SpeakingAttemptModel,
    child: ChildProfileModel,
    parent: ParentAccountModel,
) -> Optional[dict[str, Any]]:
    if attempt.status == SpeakingAttemptStatus.failed.value:
        return _operations_issue_payload(
            issue_id=f"issue_speaking_attempt_{attempt.id}_failed",
            severity="critical",
            status_label="Speaking assessment failed",
            reason=attempt.failure_reason or "Speaking attempt failed.",
            recommended_action="inspect_speaking_attempt",
            required_permission=ADMIN_OPERATIONS_READ,
            related_resource={
                "type": "speaking_attempt",
                "id": attempt.id,
                "tenant_id": parent.id,
                "material_id": attempt.material_id,
                "child_id": child.id,
            },
        )
    pending_statuses = {
        SpeakingAttemptStatus.queued.value,
        SpeakingAttemptStatus.recording_uploaded.value,
        SpeakingAttemptStatus.transcribing.value,
    }
    if attempt.status in pending_statuses and _age_minutes(attempt.updated_at) >= OPERATIONS_STALE_THRESHOLD_MINUTES:
        return _operations_issue_payload(
            issue_id=f"issue_speaking_attempt_{attempt.id}_stale",
            severity="warning",
            status_label="Speaking assessment stale",
            reason=f"Speaking attempt has been pending for at least {OPERATIONS_STALE_THRESHOLD_MINUTES} minutes.",
            recommended_action="inspect_speaking_attempt",
            required_permission=ADMIN_OPERATIONS_READ,
            related_resource={
                "type": "speaking_attempt",
                "id": attempt.id,
                "tenant_id": parent.id,
                "material_id": attempt.material_id,
                "child_id": child.id,
            },
        )
    return None


def build_provider_readiness(settings=None) -> dict[str, bool]:
    resolved_settings = settings or get_settings()
    return {
        "ai_provider_ready": _ai_provider_ready(resolved_settings),
        "media_image_provider_ready": _media_runtime_provider_ready(
            resolved_settings.media_provider,
            resolved_settings.media_image_provider,
            resolved_settings,
        ),
        "media_tts_provider_ready": _media_runtime_provider_ready(
            resolved_settings.media_provider,
            resolved_settings.media_tts_provider,
            resolved_settings,
        ),
        "speech_provider_ready": _speech_provider_ready(resolved_settings),
        "speech_assessment_provider_ready": _speech_assessment_provider_ready(resolved_settings),
    }


def _operations_tenant_count(db: Session, tenant_scope: str) -> int:
    if tenant_scope == "all":
        value = db.scalar(select(func.count(ParentAccountModel.id)))
        return int(value or 0)
    return 1


def _operations_material_parse_job_payload(db: Session, tenant_scope: str) -> dict:
    by_status = {status_value.value: 0 for status_value in JobStatus}
    rows = db.execute(
        select(MaterialParseJobModel.status, func.count(MaterialParseJobModel.id))
        .join(CourseMaterialModel, CourseMaterialModel.id == MaterialParseJobModel.material_id)
        .join(ChildProfileModel, ChildProfileModel.id == CourseMaterialModel.child_id)
        .where(tenant_child_scope_filter(tenant_scope))
        .group_by(MaterialParseJobModel.status)
    ).all()
    for status_value, count in rows:
        if status_value in by_status:
            by_status[status_value] = int(count)

    running_statuses = [JobStatus.queued.value, JobStatus.processing.value, JobStatus.needs_review.value]
    processing_health = _operations_material_processing_health(db, tenant_scope)
    return {
        "total": sum(by_status.values()),
        "by_status": by_status,
        "failed": by_status.get(JobStatus.failed.value, 0),
        "running": sum(by_status.get(status_value, 0) for status_value in running_statuses),
        **processing_health,
        "latest_failed": _latest_operations_material_jobs(db, tenant_scope, [JobStatus.failed.value]),
        "latest_running": _latest_operations_material_jobs(db, tenant_scope, running_statuses),
    }


def _operations_material_processing_health(db: Session, tenant_scope: str) -> dict:
    stale_before = datetime.now(timezone.utc) - timedelta(minutes=OPERATIONS_STALE_THRESHOLD_MINUTES)
    stale_processing = db.scalar(
        select(func.count(MaterialParseJobModel.id))
        .join(CourseMaterialModel, CourseMaterialModel.id == MaterialParseJobModel.material_id)
        .join(ChildProfileModel, ChildProfileModel.id == CourseMaterialModel.child_id)
        .where(
            tenant_child_scope_filter(tenant_scope),
            MaterialParseJobModel.status == JobStatus.processing.value,
            MaterialParseJobModel.started_at < stale_before,
        )
    )
    oldest_processing_started_at = db.scalar(
        select(func.min(MaterialParseJobModel.started_at))
        .join(CourseMaterialModel, CourseMaterialModel.id == MaterialParseJobModel.material_id)
        .join(ChildProfileModel, ChildProfileModel.id == CourseMaterialModel.child_id)
        .where(
            tenant_child_scope_filter(tenant_scope),
            MaterialParseJobModel.status == JobStatus.processing.value,
        )
    )
    return {
        "stale_threshold_minutes": OPERATIONS_STALE_THRESHOLD_MINUTES,
        "stale_processing": int(stale_processing or 0),
        "oldest_processing_minutes": _age_minutes(oldest_processing_started_at),
    }


def _latest_operations_material_jobs(db: Session, tenant_scope: str, status_values: list[str]) -> list[dict]:
    rows = _latest_operations_material_job_rows(db, tenant_scope, status_values)
    return [_operations_material_job_item_payload(job, material, child, parent) for job, material, child, parent in rows]


def _latest_operations_material_job_rows(
    db: Session,
    tenant_scope: str,
    status_values: list[str],
    *,
    exclude_material_statuses: Optional[list[str]] = None,
):
    query = (
        select(MaterialParseJobModel, CourseMaterialModel, ChildProfileModel, ParentAccountModel)
        .join(CourseMaterialModel, CourseMaterialModel.id == MaterialParseJobModel.material_id)
        .join(ChildProfileModel, ChildProfileModel.id == CourseMaterialModel.child_id)
        .join(ParentAccountModel, ParentAccountModel.id == ChildProfileModel.parent_account_id)
        .where(tenant_child_scope_filter(tenant_scope), MaterialParseJobModel.status.in_(status_values))
    )
    if exclude_material_statuses:
        query = query.where(CourseMaterialModel.status.notin_(exclude_material_statuses))
    return db.execute(
        query.order_by(MaterialParseJobModel.started_at.desc(), MaterialParseJobModel.id.desc()).limit(
            OPERATIONS_LATEST_LIMIT
        )
    ).all()


def _latest_stale_operations_material_job_rows(db: Session, tenant_scope: str):
    stale_before = datetime.now(timezone.utc) - timedelta(minutes=OPERATIONS_STALE_THRESHOLD_MINUTES)
    return db.execute(
        select(MaterialParseJobModel, CourseMaterialModel, ChildProfileModel, ParentAccountModel)
        .join(CourseMaterialModel, CourseMaterialModel.id == MaterialParseJobModel.material_id)
        .join(ChildProfileModel, ChildProfileModel.id == CourseMaterialModel.child_id)
        .join(ParentAccountModel, ParentAccountModel.id == ChildProfileModel.parent_account_id)
        .where(
            tenant_child_scope_filter(tenant_scope),
            MaterialParseJobModel.status == JobStatus.processing.value,
            MaterialParseJobModel.started_at < stale_before,
            CourseMaterialModel.status.notin_([MaterialStatus.ready.value, MaterialStatus.archived.value]),
        )
        .order_by(MaterialParseJobModel.started_at.asc(), MaterialParseJobModel.id.asc())
        .limit(OPERATIONS_LATEST_LIMIT)
    ).all()


def _operations_material_job_item_payload(
    job: MaterialParseJobModel,
    material: CourseMaterialModel,
    child: ChildProfileModel,
    parent: ParentAccountModel,
) -> dict:
    return {
        "id": job.id,
        "tenant_id": parent.id,
        "material_id": material.id,
        "material_title": material.title,
        "material_status": material.status,
        "child_id": child.id,
        "child_name": child.name,
        "status": job.status,
        "confidence_summary": job.confidence_summary,
        "warnings": list(job.warnings or []),
        "started_at": _iso(job.started_at),
        "finished_at": _iso(job.finished_at) if job.finished_at else "",
    }


def _operations_material_status_counts(db: Session, tenant_scope: str) -> dict[str, int]:
    by_status = {status_value.value: 0 for status_value in MaterialStatus}
    rows = db.execute(
        select(CourseMaterialModel.status, func.count(CourseMaterialModel.id))
        .join(ChildProfileModel, ChildProfileModel.id == CourseMaterialModel.child_id)
        .where(tenant_child_scope_filter(tenant_scope))
        .group_by(CourseMaterialModel.status)
    ).all()
    for status_value, count in rows:
        if status_value in by_status:
            by_status[status_value] = int(count)
    return by_status


def _operations_media_generation_payload(
    db: Session,
    tenant_scope: str,
    material_status_counts: dict[str, int],
) -> dict:
    media_status_counts = {status_value.value: 0 for status_value in MediaGenerationStatus}
    failure_signals = {
        "generated_image_status": 0,
        "tts_us_status": 0,
        "tts_uk_status": 0,
        "total": 0,
    }
    for field_name, media_status, count in _operations_media_field_status_counts(db, tenant_scope):
        if media_status in media_status_counts:
            media_status_counts[media_status] += count
        if media_status == MediaGenerationStatus.failed.value and field_name in failure_signals:
            failure_signals[field_name] += count
            failure_signals["total"] += count
    return {
        "materials_by_status": material_status_counts,
        "asset_status_fields_by_status": media_status_counts,
        "failure_signals": failure_signals,
    }


def _operations_media_field_status_counts(db: Session, tenant_scope: str) -> list[tuple[str, str, int]]:
    dialect_name = db.get_bind().dialect.name
    if dialect_name == "sqlite":
        return _operations_media_field_status_counts_sqlite(db, tenant_scope)
    if dialect_name == "postgresql":
        return _operations_media_field_status_counts_postgresql(db, tenant_scope)
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Operations media summary is unsupported for database dialect",
    )


def _operations_media_field_status_counts_sqlite(db: Session, tenant_scope: str) -> list[tuple[str, str, int]]:
    rows = db.execute(
        text(
            """
            SELECT field_name, status, COUNT(*) AS count
            FROM (
                SELECT 'generated_image_status' AS field_name, json_extract(asset.value, '$.generated_image_status') AS status
                FROM course_materials AS material
                JOIN child_profiles AS child ON child.id = material.child_id
                JOIN json_each(COALESCE(material.learning_assets, '[]')) AS asset
                WHERE (:tenant_scope = 'all' OR child.parent_account_id = :tenant_scope)
                UNION ALL
                SELECT 'tts_us_status' AS field_name, json_extract(asset.value, '$.tts_us_status') AS status
                FROM course_materials AS material
                JOIN child_profiles AS child ON child.id = material.child_id
                JOIN json_each(COALESCE(material.learning_assets, '[]')) AS asset
                WHERE (:tenant_scope = 'all' OR child.parent_account_id = :tenant_scope)
                UNION ALL
                SELECT 'tts_uk_status' AS field_name, json_extract(asset.value, '$.tts_uk_status') AS status
                FROM course_materials AS material
                JOIN child_profiles AS child ON child.id = material.child_id
                JOIN json_each(COALESCE(material.learning_assets, '[]')) AS asset
                WHERE (:tenant_scope = 'all' OR child.parent_account_id = :tenant_scope)
                UNION ALL
                SELECT 'generated_image_status' AS field_name, json_extract(asset.value, '$.generated_image_status') AS status
                FROM material_parse_jobs AS job
                JOIN course_materials AS material ON material.id = job.material_id
                JOIN child_profiles AS child ON child.id = material.child_id
                JOIN json_each(COALESCE(job.draft_learning_assets, '[]')) AS asset
                WHERE (:tenant_scope = 'all' OR child.parent_account_id = :tenant_scope)
                  AND json_array_length(COALESCE(material.learning_assets, '[]')) = 0
                UNION ALL
                SELECT 'tts_us_status' AS field_name, json_extract(asset.value, '$.tts_us_status') AS status
                FROM material_parse_jobs AS job
                JOIN course_materials AS material ON material.id = job.material_id
                JOIN child_profiles AS child ON child.id = material.child_id
                JOIN json_each(COALESCE(job.draft_learning_assets, '[]')) AS asset
                WHERE (:tenant_scope = 'all' OR child.parent_account_id = :tenant_scope)
                  AND json_array_length(COALESCE(material.learning_assets, '[]')) = 0
                UNION ALL
                SELECT 'tts_uk_status' AS field_name, json_extract(asset.value, '$.tts_uk_status') AS status
                FROM material_parse_jobs AS job
                JOIN course_materials AS material ON material.id = job.material_id
                JOIN child_profiles AS child ON child.id = material.child_id
                JOIN json_each(COALESCE(job.draft_learning_assets, '[]')) AS asset
                WHERE (:tenant_scope = 'all' OR child.parent_account_id = :tenant_scope)
                  AND json_array_length(COALESCE(material.learning_assets, '[]')) = 0
            ) AS media_fields
            WHERE status IS NOT NULL AND status != ''
            GROUP BY field_name, status
            """
        ),
        {"tenant_scope": tenant_scope},
    ).all()
    return [(field_name, media_status, int(count)) for field_name, media_status, count in rows]


def _operations_media_field_status_counts_postgresql(db: Session, tenant_scope: str) -> list[tuple[str, str, int]]:
    rows = db.execute(
        text(
            """
            SELECT field_name, status, COUNT(*) AS count
            FROM (
                SELECT 'generated_image_status' AS field_name, asset.value ->> 'generated_image_status' AS status
                FROM course_materials AS material
                JOIN child_profiles AS child ON child.id = material.child_id
                CROSS JOIN LATERAL jsonb_array_elements(
                    COALESCE(CAST(material.learning_assets AS jsonb), CAST('[]' AS jsonb))
                ) AS asset(value)
                WHERE (:tenant_scope = 'all' OR child.parent_account_id = :tenant_scope)
                UNION ALL
                SELECT 'tts_us_status' AS field_name, asset.value ->> 'tts_us_status' AS status
                FROM course_materials AS material
                JOIN child_profiles AS child ON child.id = material.child_id
                CROSS JOIN LATERAL jsonb_array_elements(
                    COALESCE(CAST(material.learning_assets AS jsonb), CAST('[]' AS jsonb))
                ) AS asset(value)
                WHERE (:tenant_scope = 'all' OR child.parent_account_id = :tenant_scope)
                UNION ALL
                SELECT 'tts_uk_status' AS field_name, asset.value ->> 'tts_uk_status' AS status
                FROM course_materials AS material
                JOIN child_profiles AS child ON child.id = material.child_id
                CROSS JOIN LATERAL jsonb_array_elements(
                    COALESCE(CAST(material.learning_assets AS jsonb), CAST('[]' AS jsonb))
                ) AS asset(value)
                WHERE (:tenant_scope = 'all' OR child.parent_account_id = :tenant_scope)
                UNION ALL
                SELECT 'generated_image_status' AS field_name, asset.value ->> 'generated_image_status' AS status
                FROM material_parse_jobs AS job
                JOIN course_materials AS material ON material.id = job.material_id
                JOIN child_profiles AS child ON child.id = material.child_id
                CROSS JOIN LATERAL jsonb_array_elements(
                    COALESCE(CAST(job.draft_learning_assets AS jsonb), CAST('[]' AS jsonb))
                ) AS asset(value)
                WHERE (:tenant_scope = 'all' OR child.parent_account_id = :tenant_scope)
                  AND jsonb_array_length(COALESCE(CAST(material.learning_assets AS jsonb), CAST('[]' AS jsonb))) = 0
                UNION ALL
                SELECT 'tts_us_status' AS field_name, asset.value ->> 'tts_us_status' AS status
                FROM material_parse_jobs AS job
                JOIN course_materials AS material ON material.id = job.material_id
                JOIN child_profiles AS child ON child.id = material.child_id
                CROSS JOIN LATERAL jsonb_array_elements(
                    COALESCE(CAST(job.draft_learning_assets AS jsonb), CAST('[]' AS jsonb))
                ) AS asset(value)
                WHERE (:tenant_scope = 'all' OR child.parent_account_id = :tenant_scope)
                  AND jsonb_array_length(COALESCE(CAST(material.learning_assets AS jsonb), CAST('[]' AS jsonb))) = 0
                UNION ALL
                SELECT 'tts_uk_status' AS field_name, asset.value ->> 'tts_uk_status' AS status
                FROM material_parse_jobs AS job
                JOIN course_materials AS material ON material.id = job.material_id
                JOIN child_profiles AS child ON child.id = material.child_id
                CROSS JOIN LATERAL jsonb_array_elements(
                    COALESCE(CAST(job.draft_learning_assets AS jsonb), CAST('[]' AS jsonb))
                ) AS asset(value)
                WHERE (:tenant_scope = 'all' OR child.parent_account_id = :tenant_scope)
                  AND jsonb_array_length(COALESCE(CAST(material.learning_assets AS jsonb), CAST('[]' AS jsonb))) = 0
            ) AS media_fields
            WHERE status IS NOT NULL AND status != ''
            GROUP BY field_name, status
            """
        ),
        {"tenant_scope": tenant_scope},
    ).all()
    return [(field_name, media_status, int(count)) for field_name, media_status, count in rows]


def _operations_speaking_attempts_payload(db: Session, tenant_scope: str) -> dict:
    by_status = {status_value.value: 0 for status_value in SpeakingAttemptStatus}
    rows = db.execute(
        select(SpeakingAttemptModel.status, func.count(SpeakingAttemptModel.id))
        .join(ChildProfileModel, ChildProfileModel.id == SpeakingAttemptModel.child_id)
        .where(tenant_child_scope_filter(tenant_scope))
        .group_by(SpeakingAttemptModel.status)
    ).all()
    for status_value, count in rows:
        if status_value in by_status:
            by_status[status_value] = int(count)

    pending_statuses = [
        SpeakingAttemptStatus.queued.value,
        SpeakingAttemptStatus.recording_uploaded.value,
        SpeakingAttemptStatus.transcribing.value,
    ]
    pending_health = _operations_speaking_pending_health(db, tenant_scope, pending_statuses)
    return {
        "total": sum(by_status.values()),
        "by_status": by_status,
        "failed": by_status.get(SpeakingAttemptStatus.failed.value, 0),
        "pending": sum(by_status.get(status_value, 0) for status_value in pending_statuses),
        **pending_health,
        "latest_failed": _latest_operations_speaking_attempts(
            db,
            tenant_scope,
            [SpeakingAttemptStatus.failed.value],
        ),
        "latest_pending": _latest_operations_speaking_attempts(db, tenant_scope, pending_statuses),
    }


def _operations_speaking_pending_health(db: Session, tenant_scope: str, pending_statuses: list[str]) -> dict:
    stale_before = datetime.now(timezone.utc) - timedelta(minutes=OPERATIONS_STALE_THRESHOLD_MINUTES)
    stale_pending = db.scalar(
        select(func.count(SpeakingAttemptModel.id))
        .join(ChildProfileModel, ChildProfileModel.id == SpeakingAttemptModel.child_id)
        .where(
            tenant_child_scope_filter(tenant_scope),
            SpeakingAttemptModel.status.in_(pending_statuses),
            SpeakingAttemptModel.updated_at < stale_before,
        )
    )
    stale_transcribing = db.scalar(
        select(func.count(SpeakingAttemptModel.id))
        .join(ChildProfileModel, ChildProfileModel.id == SpeakingAttemptModel.child_id)
        .where(
            tenant_child_scope_filter(tenant_scope),
            SpeakingAttemptModel.status == SpeakingAttemptStatus.transcribing.value,
            SpeakingAttemptModel.updated_at < stale_before,
        )
    )
    oldest_pending_updated_at = db.scalar(
        select(func.min(SpeakingAttemptModel.updated_at))
        .join(ChildProfileModel, ChildProfileModel.id == SpeakingAttemptModel.child_id)
        .where(
            tenant_child_scope_filter(tenant_scope),
            SpeakingAttemptModel.status.in_(pending_statuses),
        )
    )
    return {
        "stale_threshold_minutes": OPERATIONS_STALE_THRESHOLD_MINUTES,
        "stale_pending": int(stale_pending or 0),
        "stale_transcribing": int(stale_transcribing or 0),
        "oldest_pending_minutes": _age_minutes(oldest_pending_updated_at),
    }


def _latest_operations_speaking_attempts(db: Session, tenant_scope: str, status_values: list[str]) -> list[dict]:
    rows = _latest_operations_speaking_attempt_rows(db, tenant_scope, status_values)
    return [_operations_speaking_attempt_item_payload(attempt, child, parent) for attempt, child, parent in rows]


def _latest_operations_speaking_attempt_rows(db: Session, tenant_scope: str, status_values: list[str]):
    return db.execute(
        select(SpeakingAttemptModel, ChildProfileModel, ParentAccountModel)
        .join(ChildProfileModel, ChildProfileModel.id == SpeakingAttemptModel.child_id)
        .join(ParentAccountModel, ParentAccountModel.id == ChildProfileModel.parent_account_id)
        .where(tenant_child_scope_filter(tenant_scope), SpeakingAttemptModel.status.in_(status_values))
        .order_by(SpeakingAttemptModel.updated_at.desc(), SpeakingAttemptModel.id.desc())
        .limit(OPERATIONS_LATEST_LIMIT)
    ).all()


def _latest_stale_operations_speaking_attempt_rows(db: Session, tenant_scope: str):
    stale_before = datetime.now(timezone.utc) - timedelta(minutes=OPERATIONS_STALE_THRESHOLD_MINUTES)
    pending_statuses = [
        SpeakingAttemptStatus.queued.value,
        SpeakingAttemptStatus.recording_uploaded.value,
        SpeakingAttemptStatus.transcribing.value,
    ]
    return db.execute(
        select(SpeakingAttemptModel, ChildProfileModel, ParentAccountModel)
        .join(ChildProfileModel, ChildProfileModel.id == SpeakingAttemptModel.child_id)
        .join(ParentAccountModel, ParentAccountModel.id == ChildProfileModel.parent_account_id)
        .where(
            tenant_child_scope_filter(tenant_scope),
            SpeakingAttemptModel.status.in_(pending_statuses),
            SpeakingAttemptModel.updated_at < stale_before,
        )
        .order_by(SpeakingAttemptModel.updated_at.asc(), SpeakingAttemptModel.id.asc())
        .limit(OPERATIONS_LATEST_LIMIT)
    ).all()


def _operations_speaking_attempt_item_payload(
    attempt: SpeakingAttemptModel,
    child: ChildProfileModel,
    parent: ParentAccountModel,
) -> dict:
    return {
        "id": attempt.id,
        "tenant_id": parent.id,
        "child_id": child.id,
        "child_name": child.name,
        "material_id": attempt.material_id,
        "status": attempt.status,
        "provider": attempt.provider,
        "failure_reason": attempt.failure_reason,
        "created_at": _iso(attempt.created_at),
        "updated_at": _iso(attempt.updated_at),
    }


def _operations_provider_configuration_payload(db: Session, tenant_scope: str) -> dict:
    override_count = db.scalar(
        select(func.count(TenantProviderPolicyModel.id)).where(tenant_provider_policy_scope_filter(tenant_scope))
    )
    policies = db.scalars(
        select(TenantProviderPolicyModel)
        .where(tenant_provider_policy_scope_filter(tenant_scope))
        .order_by(TenantProviderPolicyModel.updated_at.desc(), TenantProviderPolicyModel.tenant_id.asc())
        .limit(PROVIDER_OVERRIDE_SAMPLE_LIMIT)
    ).all()
    return {
        "global": _global_provider_policy(),
        "runtime": _operations_provider_runtime_payload(),
        "tenant_overrides": [_tenant_provider_policy_payload(policy) for policy in policies],
        "tenant_overrides_limit": PROVIDER_OVERRIDE_SAMPLE_LIMIT,
        "override_count": int(override_count or 0),
    }


def _operations_provider_runtime_payload() -> dict:
    settings = get_settings()
    secret_presence = {
        "ark_api_key_configured": bool(settings.ark_api_key),
        "openai_api_key_configured": bool(settings.openai_api_key),
        "dashscope_api_key_configured": bool(settings.dashscope_api_key),
        "speech_assessment_app_key_configured": bool(settings.speech_assessment_app_key),
        "speech_assessment_secret_key_configured": bool(settings.speech_assessment_secret_key),
    }
    return {
        "ai_provider": settings.ai_provider,
        "media_provider": settings.media_provider,
        "media_image_provider": settings.media_image_provider,
        "media_tts_provider": settings.media_tts_provider,
        "speech_provider": settings.speech_provider,
        "speech_assessment_provider": settings.speech_assessment_provider,
        "models": {
            "media_image_model": settings.media_image_model,
            "media_image_edit_model": settings.media_image_edit_model,
            "media_tts_model": settings.media_tts_model,
            "speech_assessment_default_accent": settings.speech_assessment_default_accent,
        },
        "secret_presence": secret_presence,
        "readiness": build_provider_readiness(settings),
    }


def _operations_module_toggle_coverage_payload(
    db: Session,
    tenant_scope: str,
    tenant_count: int,
) -> dict:
    override_rows = db.execute(
        select(
            TenantModuleSettingModel.module_key,
            TenantModuleSettingModel.enabled,
            func.count(TenantModuleSettingModel.id),
        )
        .where(
            tenant_module_setting_scope_filter(tenant_scope),
            TenantModuleSettingModel.module_key.in_(MODULE_KEYS),
        )
        .group_by(TenantModuleSettingModel.module_key, TenantModuleSettingModel.enabled)
    ).all()
    override_counts = {
        (module_key, bool(enabled)): int(count)
        for module_key, enabled, count in override_rows
    }
    by_module: list[dict] = []
    total_enabled = 0
    total_disabled = 0
    total_overrides = 0
    for module_key in MODULE_KEYS:
        override_enabled = override_counts.get((module_key, True), 0)
        override_disabled = override_counts.get((module_key, False), 0)
        overrides = override_enabled + override_disabled
        global_defaults = max(0, tenant_count - overrides)
        enabled = global_defaults + override_enabled
        disabled = override_disabled
        total_enabled += enabled
        total_disabled += disabled
        total_overrides += overrides
        by_module.append(
            {
                "module_key": module_key,
                "total": tenant_count,
                "enabled": enabled,
                "disabled": disabled,
                "overrides": overrides,
                "global_defaults": global_defaults,
            }
        )
    return {
        "tenant_count": tenant_count,
        "module_keys": list(MODULE_KEYS),
        "total": tenant_count * len(MODULE_KEYS),
        "enabled": total_enabled,
        "disabled": total_disabled,
        "overrides": total_overrides,
        "global_defaults": tenant_count * len(MODULE_KEYS) - total_overrides,
        "by_module": by_module,
    }


def _operations_issue_payload(
    *,
    issue_id: str,
    severity: IssueSeverity,
    status_label: str,
    reason: str,
    recommended_action: str,
    required_permission: str,
    related_resource: dict[str, Any],
) -> dict[str, Any]:
    return {
        "id": issue_id,
        "severity": severity,
        "status_label": status_label,
        "reason": reason,
        "recommended_action": recommended_action,
        "required_permission": required_permission,
        "related_resource": related_resource,
        "source": DATABASE_SNAPSHOT_SOURCE,
    }


def _operations_summary_severity(issues: list[dict[str, Any]]) -> IssueSeverity:
    severities = {issue["severity"] for issue in issues}
    if "critical" in severities:
        return "critical"
    if "warning" in severities:
        return "warning"
    if "info" in severities:
        return "info"
    return "ok"


def _dedupe_operations_issues(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for issue in issues:
        if issue["id"] in seen:
            continue
        seen.add(issue["id"])
        deduped.append(issue)
    severity_rank = {"critical": 0, "warning": 1, "info": 2, "ok": 3}
    return sorted(deduped, key=lambda issue: (severity_rank.get(issue["severity"], 3), issue["id"]))


def _job_failure_reason(job: MaterialParseJobModel) -> str:
    if job.confidence_summary:
        return job.confidence_summary
    warnings = list(job.warnings or [])
    if warnings:
        return "; ".join(str(item) for item in warnings)
    return "Material parse job failed."


def _global_provider_policy() -> dict:
    settings = get_settings()
    return {
        "tenant_id": "global",
        "ai_provider": "doubao" if settings.ai_provider == "doubao" else "stub",
        "media_provider": "real" if settings.media_provider == "real" else "mock",
        "fallback_mode": "global_stub" if settings.ai_provider != "doubao" else "auto_to_mock",
        "monthly_guardrail": 0,
        "source": "global_default",
    }


def _tenant_provider_policy_payload(policy: TenantProviderPolicyModel) -> dict:
    return {
        "tenant_id": policy.tenant_id,
        "ai_provider": policy.ai_provider,
        "media_provider": policy.media_provider,
        "fallback_mode": policy.fallback_mode,
        "monthly_guardrail": policy.monthly_guardrail,
        "source": policy.source,
    }


def _ai_provider_ready(settings) -> bool:
    provider = settings.ai_provider.lower()
    if provider == "stub":
        return True
    if provider == "doubao":
        return bool(settings.ark_api_key)
    return _provider_api_key_configured(provider, settings)


def _media_runtime_provider_ready(media_provider: str, runtime_provider: str, settings) -> bool:
    if media_provider.lower() == "mock":
        return True
    return _provider_api_key_configured(runtime_provider.lower(), settings)


def _speech_provider_ready(settings) -> bool:
    provider = settings.speech_provider.lower()
    if provider == "stub":
        return True
    if provider == settings.speech_assessment_provider.lower():
        return _speech_assessment_provider_ready(settings)
    return _provider_api_key_configured(provider, settings)


def _speech_assessment_provider_ready(settings) -> bool:
    provider = settings.speech_assessment_provider.lower()
    if provider == "stub":
        return True
    if provider == "dashscope":
        return bool(settings.speech_assessment_app_key and settings.speech_assessment_secret_key)
    return _provider_api_key_configured(provider, settings)


def _provider_api_key_configured(provider: str, settings) -> bool:
    if provider in {"stub", "mock", ""}:
        return True
    if provider == "openai":
        return bool(settings.openai_api_key)
    if provider in {"dashscope", "qwen"}:
        return bool(settings.dashscope_api_key)
    if provider == "doubao":
        return bool(settings.ark_api_key)
    return False


def _age_minutes(value: Optional[datetime]) -> int:
    if value is None:
        return 0
    now = datetime.now(timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return max(0, int((now - value).total_seconds() // 60))


def _iso(value: Optional[datetime]) -> str:
    if value is None:
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
