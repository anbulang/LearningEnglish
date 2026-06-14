from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

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
    WeeklyReportModel,
)
from app.models.contracts import JobStatus, MaterialStatus, SpeakingAttemptStatus
from app.services.admin.scope import get_tenant_or_404

TENANT_DETAIL_LATEST_LIMIT = 5
MODULE_KEYS = ("worksheet_import", "ai_review", "media_pipeline", "speaking_score", "weekly_reports")
AI_PROVIDERS = {"stub", "doubao", "qwen", "dashscope", "bailian", "aliyun"}


def build_admin_dashboard(db: Session, tenant_scope: str) -> dict[str, Any]:
    tenants = db.scalars(select(ParentAccountModel).order_by(ParentAccountModel.created_at.asc())).all()
    tenant_ids = {tenant.id for tenant in tenants}
    if tenant_scope != "all" and tenant_scope not in tenant_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant scope not found")

    scoped_tenants = tenants if tenant_scope == "all" else [tenant for tenant in tenants if tenant.id == tenant_scope]
    scoped_tenant_ids = {tenant.id for tenant in scoped_tenants}
    children = db.scalars(
        select(ChildProfileModel).where(ChildProfileModel.parent_account_id.in_(scoped_tenant_ids or [""]))
    ).all()
    children_by_parent = _count_children_by_parent(children)
    material_rows = db.execute(
        select(CourseMaterialModel, ChildProfileModel, ParentAccountModel)
        .join(ChildProfileModel, ChildProfileModel.id == CourseMaterialModel.child_id)
        .join(ParentAccountModel, ParentAccountModel.id == ChildProfileModel.parent_account_id)
        .where(ChildProfileModel.parent_account_id.in_(scoped_tenant_ids or [""]))
        .order_by(CourseMaterialModel.updated_at.desc())
    ).all()
    material_ids = [row[0].id for row in material_rows]
    jobs = db.scalars(select(MaterialParseJobModel).where(MaterialParseJobModel.material_id.in_(material_ids or [""]))).all()
    job_by_material = {job.material_id: job for job in jobs}
    materials = [
        _admin_material_payload(material, child, parent, job_by_material.get(material.id))
        for material, child, parent in material_rows
    ]
    policy_rows = db.scalars(
        select(TenantProviderPolicyModel)
        .where(TenantProviderPolicyModel.tenant_id.in_(scoped_tenant_ids or [""]))
        .order_by(TenantProviderPolicyModel.updated_at.desc())
    ).all()
    module_rows = db.scalars(
        select(TenantModuleSettingModel)
        .where(TenantModuleSettingModel.tenant_id.in_(scoped_tenant_ids or [""]))
        .order_by(TenantModuleSettingModel.updated_at.desc())
    ).all()

    return {
        "tenants": [
            _admin_tenant_payload(tenant, children_by_parent.get(tenant.id, 0), materials)
            for tenant in scoped_tenants
        ],
        "materials": materials,
        "provider_policies": [
            _global_provider_policy(),
            *[_tenant_provider_policy_payload(policy) for policy in policy_rows],
        ],
        "module_settings": _module_settings_payload(scoped_tenants, module_rows),
    }


def build_admin_tenant_detail(db: Session, tenant_scope: str, tenant_id: str) -> dict[str, Any]:
    tenant = get_tenant_or_404(db, tenant_scope, tenant_id)
    children = db.scalars(
        select(ChildProfileModel)
        .where(ChildProfileModel.parent_account_id == tenant.id)
        .order_by(ChildProfileModel.created_at.asc(), ChildProfileModel.id.asc())
    ).all()
    child_by_id = {child.id: child for child in children}
    child_ids = [child.id for child in children]
    material_counts = _tenant_material_status_counts(db, child_ids)
    materials = _latest_tenant_materials(db, child_ids)
    recent_material_ids = [material.id for material in materials]
    jobs = db.scalars(
        select(MaterialParseJobModel)
        .where(MaterialParseJobModel.material_id.in_(recent_material_ids or [""]))
        .order_by(MaterialParseJobModel.started_at.desc(), MaterialParseJobModel.id.desc())
    ).all()
    job_by_material = {job.material_id: job for job in jobs}
    job_counts = _tenant_job_status_counts(db, tenant.id)
    stale_processing_jobs = _tenant_stale_processing_job_count(db, tenant.id)
    media_failure_count = _tenant_media_failure_count(db, tenant.id)
    policy = db.scalar(select(TenantProviderPolicyModel).where(TenantProviderPolicyModel.tenant_id == tenant.id))
    module_rows = db.scalars(
        select(TenantModuleSettingModel)
        .where(TenantModuleSettingModel.tenant_id == tenant.id)
        .order_by(TenantModuleSettingModel.updated_at.desc())
    ).all()
    latest_reports = _latest_weekly_reports(db, child_ids)
    weekly_report_aggregate = _weekly_report_aggregate(db, child_ids)
    latest_report_by_child = _latest_report_by_child(db, child_ids)
    latest_attempts = _latest_speaking_attempts(db, child_ids)
    speaking_status_counts = _speaking_attempt_status_counts(db, child_ids)
    speaking_average_score = _speaking_attempt_average_score(db, child_ids)
    attempt_count_by_child = _speaking_attempt_counts_by_child(db, child_ids)

    material_payloads = [
        _admin_material_payload(material, child_by_id[material.child_id], tenant, job_by_material.get(material.id))
        for material in materials
        if material.child_id in child_by_id
    ]
    risk_summary = _tenant_risk_summary(
        media_failure_count,
        material_counts,
        job_counts,
        stale_processing_jobs,
        speaking_status_counts,
    )
    return {
        "required_permission": "admin.tenant.read",
        "tenant": _admin_tenant_detail_payload(tenant, risk_summary["risk_level"], len(children)),
        "summary": _tenant_summary_payload(children, material_counts),
        "children": [
            _admin_child_payload(
                child,
                latest_report_by_child.get(child.id),
                attempt_count_by_child.get(child.id, 0),
            )
            for child in children
        ],
        "materials": material_payloads,
        "provider_policy": _effective_tenant_provider_policy_payload(tenant.id, policy),
        "module_settings": _module_settings_payload([tenant], module_rows),
        "weekly_reports": _weekly_report_payload(latest_reports, weekly_report_aggregate),
        "speaking_attempts": _speaking_attempt_payload(
            latest_attempts,
            speaking_status_counts,
            speaking_average_score,
        ),
        "risk_summary": risk_summary,
    }


LEARNING_ASSETS_DEFAULT_LIMIT = 200
LEARNING_ASSETS_MAX_LIMIT = 500


def build_admin_learning_assets(
    db: Session,
    tenant_scope: str,
    *,
    material_id: str = "",
    media_status: str = "",
    limit: int = LEARNING_ASSETS_DEFAULT_LIMIT,
) -> dict[str, Any]:
    """把各讲义里的 learning_assets JSON 扁平成带 material/tenant 上下文的资产列表。

    供 admin Learning Assets 页只读消费。归档讲义的资产不再展示。
    """
    tenant_ids = set(db.scalars(select(ParentAccountModel.id)).all())
    if tenant_scope != "all" and tenant_scope not in tenant_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant scope not found")

    stmt = (
        select(CourseMaterialModel, ChildProfileModel, ParentAccountModel)
        .join(ChildProfileModel, ChildProfileModel.id == CourseMaterialModel.child_id)
        .join(ParentAccountModel, ParentAccountModel.id == ChildProfileModel.parent_account_id)
        .where(CourseMaterialModel.status != MaterialStatus.archived.value)
        .order_by(CourseMaterialModel.updated_at.desc(), CourseMaterialModel.id.desc())
    )
    if tenant_scope != "all":
        stmt = stmt.where(ChildProfileModel.parent_account_id == tenant_scope)
    if material_id:
        stmt = stmt.where(CourseMaterialModel.id == material_id)

    items: list[dict] = []
    for material, child, parent in db.execute(stmt).all():
        for asset in list(material.learning_assets or []):
            payload = _admin_learning_asset_payload(asset, material, child, parent)
            if media_status and payload["media_status"] != media_status:
                continue
            items.append(payload)

    capped = items[: max(1, min(limit, LEARNING_ASSETS_MAX_LIMIT))]
    return {"tenant_scope": tenant_scope, "items": capped, "total": len(items)}


def _admin_learning_asset_payload(
    asset: dict,
    material: CourseMaterialModel,
    child: ChildProfileModel,
    parent: ParentAccountModel,
) -> dict:
    updated_at = material.updated_at or material.created_at
    return {
        "id": str(asset.get("id", "")),
        "material_id": material.id,
        "material_title": material.title,
        "material_status": material.status,
        "tenant_id": parent.id,
        "parent_name": parent.display_name or _fallback_parent_name(parent),
        "child_name": child.name,
        "text": asset.get("text", ""),
        "kind": asset.get("kind", ""),
        "translation": asset.get("translation", ""),
        "primary_accent": asset.get("primary_accent", ""),
        "media_status": _media_status([asset]),
        "generated_image_status": str(asset.get("generated_image_status", "pending")),
        "generated_image_url": asset.get("generated_image_url", ""),
        "tts_us_status": str(asset.get("tts_us_status", "pending")),
        "tts_us_url": asset.get("tts_us_url", ""),
        "tts_uk_status": str(asset.get("tts_uk_status", "pending")),
        "tts_uk_url": asset.get("tts_uk_url", ""),
        "updated_at": _iso(updated_at),
    }


def serialize_admin_tenant(parent: ParentAccountModel, child_count: int, materials: list[dict]) -> dict:
    return _admin_tenant_payload(parent, child_count, materials)


def serialize_admin_material(
    material: CourseMaterialModel,
    child: ChildProfileModel,
    parent: ParentAccountModel,
    job: Optional[MaterialParseJobModel],
) -> dict:
    return _admin_material_payload(material, child, parent, job)


def serialize_provider_policy(policy: TenantProviderPolicyModel) -> dict:
    return _tenant_provider_policy_payload(policy)


def serialize_tenant_module_setting(setting: TenantModuleSettingModel) -> dict:
    return _tenant_module_setting_payload(setting)


def _count_children_by_parent(children: list[ChildProfileModel]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for child in children:
        counts[child.parent_account_id] = counts.get(child.parent_account_id, 0) + 1
    return counts


def _admin_tenant_payload(parent: ParentAccountModel, child_count: int, materials: list[dict]) -> dict:
    tenant_materials = [material for material in materials if material["tenant_id"] == parent.id]
    has_blocker = any(
        material["material_status"] == "failed" or material["job_status"] == "failed" or material["sla_minutes"] > 180
        for material in tenant_materials
    )
    return {
        "id": parent.id,
        "name": parent.display_name or _fallback_parent_name(parent),
        "tenant_type": "pilot_family",
        "status": "warning" if has_blocker else "active",
        "region": "local",
        "owner_contact": parent.phone_number,
        "tier": "pilot",
        "created_at": _iso(parent.created_at),
        "active_parents": 1,
        "children": child_count,
    }


def _admin_tenant_detail_payload(parent: ParentAccountModel, risk_level: str, child_count: int) -> dict:
    return {
        "id": parent.id,
        "name": parent.display_name or _fallback_parent_name(parent),
        "display_name": parent.display_name,
        "avatar_url": parent.avatar_url,
        "phone_number": parent.phone_number,
        "phone_verified_at": _iso(parent.phone_verified_at) if parent.phone_verified_at else "",
        "wechat_union_id": parent.wechat_union_id,
        "wechat_open_id": parent.wechat_open_id,
        "tenant_type": "pilot_family",
        "status": "warning" if risk_level in {"medium", "high"} else "active",
        "region": "local",
        "tier": "pilot",
        "created_at": _iso(parent.created_at),
        "active_parents": 1,
        "children": child_count,
        "updated_at": _iso(parent.updated_at),
    }


def _tenant_material_status_counts(db: Session, child_ids: list[str]) -> dict[str, int]:
    if not child_ids:
        return {}
    rows = db.execute(
        select(CourseMaterialModel.status, func.count(CourseMaterialModel.id))
        .where(CourseMaterialModel.child_id.in_(child_ids))
        .group_by(CourseMaterialModel.status)
    ).all()
    return {status_value: int(count) for status_value, count in rows}


def _latest_tenant_materials(db: Session, child_ids: list[str]) -> list[CourseMaterialModel]:
    if not child_ids:
        return []
    return db.scalars(
        select(CourseMaterialModel)
        .where(CourseMaterialModel.child_id.in_(child_ids))
        .order_by(CourseMaterialModel.updated_at.desc(), CourseMaterialModel.id.desc())
        .limit(TENANT_DETAIL_LATEST_LIMIT)
    ).all()


def _tenant_job_status_counts(db: Session, tenant_id: str) -> dict[str, int]:
    rows = db.execute(
        select(MaterialParseJobModel.status, func.count(MaterialParseJobModel.id))
        .join(CourseMaterialModel, CourseMaterialModel.id == MaterialParseJobModel.material_id)
        .join(ChildProfileModel, ChildProfileModel.id == CourseMaterialModel.child_id)
        .where(ChildProfileModel.parent_account_id == tenant_id)
        .group_by(MaterialParseJobModel.status)
    ).all()
    return {status_value: int(count) for status_value, count in rows}


def _tenant_stale_processing_job_count(db: Session, tenant_id: str) -> int:
    stale_before = datetime.now(timezone.utc) - timedelta(minutes=30)
    value = db.scalar(
        select(func.count(MaterialParseJobModel.id))
        .join(CourseMaterialModel, CourseMaterialModel.id == MaterialParseJobModel.material_id)
        .join(ChildProfileModel, ChildProfileModel.id == CourseMaterialModel.child_id)
        .where(
            ChildProfileModel.parent_account_id == tenant_id,
            MaterialParseJobModel.status == JobStatus.processing.value,
            MaterialParseJobModel.started_at < stale_before,
        )
    )
    return int(value or 0)


def _tenant_media_failure_count(db: Session, tenant_id: str) -> int:
    dialect_name = db.get_bind().dialect.name
    if dialect_name == "sqlite":
        return _tenant_media_failure_count_sqlite(db, tenant_id)
    if dialect_name == "postgresql":
        return _tenant_media_failure_count_postgresql(db, tenant_id)
    return _tenant_media_failure_count_from_json_columns(db, tenant_id)


def _tenant_media_failure_count_sqlite(db: Session, tenant_id: str) -> int:
    material_failures = db.scalar(
        text(
            """
            SELECT COALESCE(SUM(
                CASE WHEN json_extract(asset.value, '$.generated_image_status') = 'failed' THEN 1 ELSE 0 END +
                CASE WHEN json_extract(asset.value, '$.tts_us_status') = 'failed' THEN 1 ELSE 0 END +
                CASE WHEN json_extract(asset.value, '$.tts_uk_status') = 'failed' THEN 1 ELSE 0 END
            ), 0)
            FROM course_materials AS material
            JOIN child_profiles AS child ON child.id = material.child_id
            JOIN json_each(COALESCE(material.learning_assets, '[]')) AS asset
            WHERE child.parent_account_id = :tenant_id
            """
        ),
        {"tenant_id": tenant_id},
    )
    draft_failures = db.scalar(
        text(
            """
            SELECT COALESCE(SUM(
                CASE WHEN json_extract(asset.value, '$.generated_image_status') = 'failed' THEN 1 ELSE 0 END +
                CASE WHEN json_extract(asset.value, '$.tts_us_status') = 'failed' THEN 1 ELSE 0 END +
                CASE WHEN json_extract(asset.value, '$.tts_uk_status') = 'failed' THEN 1 ELSE 0 END
            ), 0)
            FROM material_parse_jobs AS job
            JOIN course_materials AS material ON material.id = job.material_id
            JOIN child_profiles AS child ON child.id = material.child_id
            JOIN json_each(COALESCE(job.draft_learning_assets, '[]')) AS asset
            WHERE child.parent_account_id = :tenant_id
              AND json_array_length(COALESCE(material.learning_assets, '[]')) = 0
            """
        ),
        {"tenant_id": tenant_id},
    )
    return int(material_failures or 0) + int(draft_failures or 0)


def _tenant_media_failure_count_postgresql(db: Session, tenant_id: str) -> int:
    material_failures = db.scalar(
        text(
            """
            SELECT COALESCE(SUM(
                CASE WHEN asset.value ->> 'generated_image_status' = 'failed' THEN 1 ELSE 0 END +
                CASE WHEN asset.value ->> 'tts_us_status' = 'failed' THEN 1 ELSE 0 END +
                CASE WHEN asset.value ->> 'tts_uk_status' = 'failed' THEN 1 ELSE 0 END
            ), 0)
            FROM course_materials AS material
            JOIN child_profiles AS child ON child.id = material.child_id
            CROSS JOIN LATERAL jsonb_array_elements(
                COALESCE(CAST(material.learning_assets AS jsonb), CAST('[]' AS jsonb))
            ) AS asset(value)
            WHERE child.parent_account_id = :tenant_id
            """
        ),
        {"tenant_id": tenant_id},
    )
    draft_failures = db.scalar(
        text(
            """
            SELECT COALESCE(SUM(
                CASE WHEN asset.value ->> 'generated_image_status' = 'failed' THEN 1 ELSE 0 END +
                CASE WHEN asset.value ->> 'tts_us_status' = 'failed' THEN 1 ELSE 0 END +
                CASE WHEN asset.value ->> 'tts_uk_status' = 'failed' THEN 1 ELSE 0 END
            ), 0)
            FROM material_parse_jobs AS job
            JOIN course_materials AS material ON material.id = job.material_id
            JOIN child_profiles AS child ON child.id = material.child_id
            CROSS JOIN LATERAL jsonb_array_elements(
                COALESCE(CAST(job.draft_learning_assets AS jsonb), CAST('[]' AS jsonb))
            ) AS asset(value)
            WHERE child.parent_account_id = :tenant_id
              AND jsonb_array_length(COALESCE(CAST(material.learning_assets AS jsonb), CAST('[]' AS jsonb))) = 0
            """
        ),
        {"tenant_id": tenant_id},
    )
    return int(material_failures or 0) + int(draft_failures or 0)


def _tenant_media_failure_count_from_json_columns(db: Session, tenant_id: str) -> int:
    material_rows = db.execute(
        select(CourseMaterialModel.id, CourseMaterialModel.learning_assets)
        .join(ChildProfileModel, ChildProfileModel.id == CourseMaterialModel.child_id)
        .where(ChildProfileModel.parent_account_id == tenant_id)
    ).all()
    material_ids_with_assets: set[str] = set()
    count = 0
    for material_id, learning_assets in material_rows:
        assets = list(learning_assets or [])
        if assets:
            material_ids_with_assets.add(material_id)
        count += sum(_failed_media_fields(asset) for asset in assets)
    draft_rows = db.execute(
        select(MaterialParseJobModel.material_id, MaterialParseJobModel.draft_learning_assets)
        .join(CourseMaterialModel, CourseMaterialModel.id == MaterialParseJobModel.material_id)
        .join(ChildProfileModel, ChildProfileModel.id == CourseMaterialModel.child_id)
        .where(ChildProfileModel.parent_account_id == tenant_id)
    ).all()
    for material_id, draft_learning_assets in draft_rows:
        if material_id in material_ids_with_assets:
            continue
        count += sum(_failed_media_fields(asset) for asset in (draft_learning_assets or []))
    return count


def _tenant_summary_payload(children: list[ChildProfileModel], material_counts: dict[str, int]) -> dict:
    total_materials = sum(material_counts.values())
    return {
        "active_parents": 1,
        "children": len(children),
        "materials": total_materials,
        "ready_materials": material_counts.get(MaterialStatus.ready.value, 0),
        "failed_materials": material_counts.get(MaterialStatus.failed.value, 0),
        "processing_materials": material_counts.get(MaterialStatus.processing.value, 0),
    }


def _admin_child_payload(
    child: ChildProfileModel,
    latest_report: Optional[WeeklyReportModel],
    speaking_attempts: int,
) -> dict:
    return {
        "id": child.id,
        "parent_account_id": child.parent_account_id,
        "name": child.name,
        "avatar_url": child.avatar_url,
        "age": child.age,
        "level": child.level,
        "learning_goal": child.learning_goal,
        "preferred_review_duration_minutes": child.preferred_review_duration_minutes,
        "parent_notes": child.parent_notes,
        "weekly_report_id": latest_report.id if latest_report else "",
        "speaking_attempts": speaking_attempts,
        "created_at": _iso(child.created_at),
        "updated_at": _iso(child.updated_at),
    }


def _latest_report_by_child(db: Session, child_ids: list[str]) -> dict[str, WeeklyReportModel]:
    latest: dict[str, WeeklyReportModel] = {}
    for child_id in child_ids:
        report = db.scalars(
            select(WeeklyReportModel)
            .where(WeeklyReportModel.child_id == child_id)
            .order_by(WeeklyReportModel.week_start.desc(), WeeklyReportModel.id.desc())
            .limit(1)
        ).first()
        if report is not None:
            latest[child_id] = report
    return latest


def _latest_weekly_reports(db: Session, child_ids: list[str]) -> list[WeeklyReportModel]:
    if not child_ids:
        return []
    return db.scalars(
        select(WeeklyReportModel)
        .where(WeeklyReportModel.child_id.in_(child_ids))
        .order_by(WeeklyReportModel.week_start.desc(), WeeklyReportModel.id.desc())
        .limit(TENANT_DETAIL_LATEST_LIMIT)
    ).all()


def _weekly_report_aggregate(db: Session, child_ids: list[str]) -> dict:
    if not child_ids:
        return {
            "total": 0,
            "children_with_reports": 0,
            "completed_sessions": 0,
            "reviewed_words": 0,
            "speaking_attempts": 0,
        }
    row = db.execute(
        select(
            func.count(WeeklyReportModel.id),
            func.count(func.distinct(WeeklyReportModel.child_id)),
            func.coalesce(func.sum(WeeklyReportModel.completed_sessions), 0),
            func.coalesce(func.sum(WeeklyReportModel.reviewed_words), 0),
            func.coalesce(func.sum(WeeklyReportModel.speaking_attempts), 0),
        ).where(WeeklyReportModel.child_id.in_(child_ids))
    ).one()
    return {
        "total": int(row[0] or 0),
        "children_with_reports": int(row[1] or 0),
        "completed_sessions": int(row[2] or 0),
        "reviewed_words": int(row[3] or 0),
        "speaking_attempts": int(row[4] or 0),
    }


def _weekly_report_payload(reports: list[WeeklyReportModel], aggregate: dict) -> dict:
    latest = reports[0] if reports else None
    return {
        "total": aggregate["total"],
        "children_with_reports": aggregate["children_with_reports"],
        "completed_sessions": aggregate["completed_sessions"],
        "reviewed_words": aggregate["reviewed_words"],
        "speaking_attempts": aggregate["speaking_attempts"],
        "weak_items": _unique_strings(item for report in reports for item in (report.weak_items or [])),
        "recommended_actions": _unique_strings(item for report in reports for item in (report.recommended_actions or [])),
        "latest": _weekly_report_item_payload(latest) if latest else None,
        "history": [_weekly_report_item_payload(report) for report in reports],
    }


def _weekly_report_item_payload(report: WeeklyReportModel) -> dict:
    return {
        "id": report.id,
        "child_id": report.child_id,
        "week_start": report.week_start.isoformat(),
        "week_end": report.week_end.isoformat(),
        "completed_sessions": report.completed_sessions,
        "reviewed_words": report.reviewed_words,
        "speaking_attempts": report.speaking_attempts,
        "weak_items": list(report.weak_items or []),
        "recommended_actions": list(report.recommended_actions or []),
    }


def _latest_speaking_attempts(db: Session, child_ids: list[str]) -> list[SpeakingAttemptModel]:
    if not child_ids:
        return []
    return db.scalars(
        select(SpeakingAttemptModel)
        .where(SpeakingAttemptModel.child_id.in_(child_ids))
        .order_by(SpeakingAttemptModel.updated_at.desc(), SpeakingAttemptModel.id.desc())
        .limit(TENANT_DETAIL_LATEST_LIMIT)
    ).all()


def _speaking_attempt_status_counts(db: Session, child_ids: list[str]) -> dict[str, int]:
    counts = {status.value: 0 for status in SpeakingAttemptStatus}
    if not child_ids:
        return counts
    rows = db.execute(
        select(SpeakingAttemptModel.status, func.count(SpeakingAttemptModel.id))
        .where(SpeakingAttemptModel.child_id.in_(child_ids))
        .group_by(SpeakingAttemptModel.status)
    ).all()
    for status_value, count in rows:
        counts[status_value] = int(count)
    return counts


def _speaking_attempt_average_score(db: Session, child_ids: list[str]) -> Optional[float]:
    if not child_ids:
        return None
    value = db.scalar(
        select(func.avg(SpeakingAttemptModel.overall_score)).where(
            SpeakingAttemptModel.child_id.in_(child_ids),
            SpeakingAttemptModel.status == SpeakingAttemptStatus.scored.value,
        )
    )
    return round(float(value), 1) if value is not None else None


def _speaking_attempt_counts_by_child(db: Session, child_ids: list[str]) -> dict[str, int]:
    if not child_ids:
        return {}
    rows = db.execute(
        select(SpeakingAttemptModel.child_id, func.count(SpeakingAttemptModel.id))
        .where(SpeakingAttemptModel.child_id.in_(child_ids))
        .group_by(SpeakingAttemptModel.child_id)
    ).all()
    return {child_id: int(count) for child_id, count in rows}


def _speaking_attempt_payload(
    attempts: list[SpeakingAttemptModel],
    by_status: dict[str, int],
    average_score: Optional[float],
) -> dict:
    total = sum(by_status.values())
    return {
        "total": total,
        "by_status": by_status,
        "scored": by_status.get(SpeakingAttemptStatus.scored.value, 0),
        "failed": by_status.get(SpeakingAttemptStatus.failed.value, 0),
        "average_overall_score": average_score,
        "latest": [_speaking_attempt_item_payload(attempt) for attempt in attempts],
    }


def _speaking_attempt_item_payload(attempt: SpeakingAttemptModel) -> dict:
    return {
        "id": attempt.id,
        "child_id": attempt.child_id,
        "material_id": attempt.material_id,
        "status": attempt.status,
        "overall_score": attempt.overall_score,
        "failure_reason": attempt.failure_reason,
        "provider": attempt.provider,
        "created_at": _iso(attempt.created_at),
        "updated_at": _iso(attempt.updated_at),
    }


def _tenant_risk_summary(
    media_failure_count: int,
    material_counts: dict[str, int],
    job_counts: dict[str, int],
    stale_processing_jobs: int,
    speaking_status_counts: dict[str, int],
) -> dict:
    failed_materials = material_counts.get(MaterialStatus.failed.value, 0)
    failed_material_jobs = job_counts.get(JobStatus.failed.value, 0)
    processing_materials = material_counts.get(MaterialStatus.processing.value, 0)
    needs_review_materials = material_counts.get(MaterialStatus.needs_review.value, 0)
    failed_speaking_attempts = speaking_status_counts.get(SpeakingAttemptStatus.failed.value, 0)
    risk_level = "low"
    if media_failure_count or failed_materials or failed_material_jobs or failed_speaking_attempts:
        risk_level = "high"
    elif processing_materials or needs_review_materials or stale_processing_jobs:
        risk_level = "medium"
    return {
        "risk_level": risk_level,
        "media_failure_count": media_failure_count,
        "media_failures": media_failure_count,
        "failed_materials": failed_materials,
        "failed_material_jobs": failed_material_jobs,
        "failed_jobs": failed_material_jobs,
        "processing_materials": processing_materials,
        "needs_review_materials": needs_review_materials,
        "stale_processing_jobs": stale_processing_jobs,
        "failed_speaking_attempts": failed_speaking_attempts,
        "material_count": sum(material_counts.values()),
    }


def _failed_media_fields(asset: dict) -> int:
    return sum(
        1
        for key in ("generated_image_status", "tts_us_status", "tts_uk_status")
        if str(asset.get(key, "")).lower() == "failed"
    )


def _unique_strings(values) -> list[str]:
    seen: set[str] = set()
    items: list[str] = []
    for value in values:
        item = str(value)
        if item and item not in seen:
            seen.add(item)
            items.append(item)
    return items


def _admin_material_payload(
    material: CourseMaterialModel,
    child: ChildProfileModel,
    parent: ParentAccountModel,
    job: Optional[MaterialParseJobModel],
) -> dict:
    image_records = list(material.image_records or [])
    learning_assets = list(material.learning_assets or [])
    updated_at = material.updated_at or material.created_at
    return {
        "id": material.id,
        "tenant_id": parent.id,
        "parent_name": parent.display_name or _fallback_parent_name(parent),
        "child_name": child.name,
        "child_age": child.age,
        "title": material.title,
        "page_count": len(image_records) or len(material.source_images or []),
        "job_id": job.id if job else "",
        "confidence_summary": job.confidence_summary if job else "",
        "ocr_confidence": _ocr_confidence(job),
        "source_pages": [_source_page_payload(item) for item in image_records],
        "material_status": material.status,
        "job_status": job.status if job else "queued",
        "provider": _admin_provider(),
        "learning_assets": len(learning_assets),
        "media_status": _media_status(learning_assets),
        "sla_minutes": _elapsed_minutes(updated_at),
        "updated_at": _iso(updated_at),
        "warnings": list(job.warnings or []) if job else [],
    }


def _source_page_payload(item: dict) -> dict:
    return {
        "page_index": item.get("page_index", 0),
        "thumbnail_url": item.get("url", ""),
        "source_type": item.get("source_type", "gallery"),
    }


def _media_status(learning_assets: list[dict]) -> str:
    if not learning_assets:
        return "pending"
    statuses = [
        str(asset.get(key, "pending"))
        for asset in learning_assets
        for key in ("generated_image_status", "tts_us_status", "tts_uk_status")
    ]
    if any(item == "failed" for item in statuses):
        return "failed"
    if statuses and all(item == "ready" for item in statuses):
        return "ready"
    if any(item == "processing" for item in statuses):
        return "processing"
    return "pending"


def _ocr_confidence(job: Optional[MaterialParseJobModel]) -> float:
    if job is None:
        return 0.0
    if job.status == "failed":
        return 0.0
    if job.status == "ready":
        return 0.95
    if job.draft_image_records or job.draft_vocabulary or job.draft_sentences:
        return 0.72
    return 0.0


def _admin_provider() -> str:
    return _normalized_ai_provider(get_settings().ai_provider)


def _global_provider_policy() -> dict:
    settings = get_settings()
    ai_provider = _normalized_ai_provider(settings.ai_provider)
    return {
        "tenant_id": "global",
        "ai_provider": ai_provider,
        "media_provider": "real" if settings.media_provider == "real" else "mock",
        "fallback_mode": "global_stub" if ai_provider == "stub" else "auto_to_mock",
        "monthly_guardrail": 0,
        "source": "global_default",
    }


def _normalized_ai_provider(provider: str) -> str:
    return provider if provider in AI_PROVIDERS else "stub"


def _tenant_provider_policy_payload(policy: TenantProviderPolicyModel) -> dict:
    return {
        "tenant_id": policy.tenant_id,
        "ai_provider": policy.ai_provider,
        "media_provider": policy.media_provider,
        "fallback_mode": policy.fallback_mode,
        "monthly_guardrail": policy.monthly_guardrail,
        "source": policy.source,
    }


def _effective_tenant_provider_policy_payload(tenant_id: str, policy: Optional[TenantProviderPolicyModel]) -> dict:
    if policy is not None:
        return _tenant_provider_policy_payload(policy)
    return {**_global_provider_policy(), "tenant_id": tenant_id}


def _module_settings_payload(tenants: list[ParentAccountModel], rows: list[TenantModuleSettingModel]) -> list[dict]:
    row_by_key = {(row.tenant_id, row.module_key): row for row in rows}
    payloads: list[dict] = []
    for tenant in tenants:
        for module_key in MODULE_KEYS:
            row = row_by_key.get((tenant.id, module_key))
            if row is not None:
                payloads.append(_tenant_module_setting_payload(row))
            else:
                payloads.append(
                    {
                        "tenant_id": tenant.id,
                        "module_key": module_key,
                        "enabled": True,
                        "source": "global_default",
                    }
                )
    return payloads


def _tenant_module_setting_payload(setting: TenantModuleSettingModel) -> dict:
    return {
        "tenant_id": setting.tenant_id,
        "module_key": setting.module_key,
        "enabled": setting.enabled,
        "source": setting.source,
    }


def _elapsed_minutes(value: datetime) -> int:
    normalized = value
    if normalized.tzinfo is None:
        normalized = normalized.replace(tzinfo=timezone.utc)
    return max(0, int((datetime.now(timezone.utc) - normalized.astimezone(timezone.utc)).total_seconds() // 60))


def _iso(value: datetime) -> str:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc).isoformat()
    return value.astimezone(timezone.utc).isoformat()


def _fallback_parent_name(parent: ParentAccountModel) -> str:
    if parent.phone_number:
        return f"Family {parent.phone_number[-4:]}"
    return parent.id
