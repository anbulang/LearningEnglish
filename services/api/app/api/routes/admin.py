from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import and_, delete, func, or_, select, text
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.settings import get_settings
from app.db.models import (
    AdminAuditEventModel,
    AdminImpersonationSessionModel,
    AdminUserModel,
    ChildProfileModel,
    CourseMaterialModel,
    KnowledgePackModel,
    MaterialParseJobModel,
    ParentAccountModel,
    ParentCoachingScriptModel,
    ReviewTaskModel,
    SpeakingAttemptModel,
    TenantModuleSettingModel,
    TenantProviderPolicyModel,
    WeeklyReportModel,
)
from app.models.contracts import JobStatus, MaterialStatus, MediaGenerationStatus, SpeakingAttemptStatus
from app.services.admin_identity import AdminActor, resolve_admin_actor
from app.services.job_queue import enqueue_material_job

router = APIRouter(prefix="/admin", tags=["admin"])

ADMIN_PERMISSIONS = [
    "admin.dashboard.read",
    "admin.operations.read",
    "admin.tenant.read",
    "admin.material.read",
    "admin.material.archive",
    "admin.material.retry",
    "admin.tenant.module.toggle",
    "admin.provider.override",
    "admin.impersonation.start",
    "admin.impersonation.read",
    "admin.impersonation.end",
    "admin.audit.read",
]

AI_PROVIDERS = {"stub", "doubao"}
MEDIA_PROVIDERS = {"mock", "real"}
FALLBACK_MODES = {"global_stub", "auto_to_mock", "per_tenant"}
MODULE_KEYS = ("worksheet_import", "ai_review", "media_pipeline", "speaking_score", "weekly_reports")
TENANT_DETAIL_LATEST_LIMIT = 5
OPERATIONS_LATEST_LIMIT = 5
OPERATIONS_STALE_THRESHOLD_MINUTES = 30
PROVIDER_OVERRIDE_SAMPLE_LIMIT = 5
IMPERSONATION_SESSION_LATEST_LIMIT = 50
IMPERSONATION_SESSION_STATUSES = {"active", "ended", "all"}


class AdminArchiveMaterialRequest(BaseModel):
    reason: str = ""


class AdminRetryMaterialJobRequest(BaseModel):
    reason: str = ""


class AdminProviderPolicyOverrideRequest(BaseModel):
    tenant_id: str = ""
    ai_provider: str = "stub"
    media_provider: str = "mock"
    fallback_mode: str = "global_stub"
    monthly_guardrail: int = 0
    reason: str = ""


class AdminTenantModuleToggleRequest(BaseModel):
    enabled: bool = True
    reason: str = ""


class AdminImpersonationSessionRequest(BaseModel):
    tenant_id: str = ""
    target_parent_id: str = ""
    reason: str = ""


class AdminImpersonationSessionEndRequest(BaseModel):
    reason: str = ""


def require_admin_token(x_admin_token: Optional[str] = Header(default=None)) -> AdminActor:
    if not x_admin_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing admin token")
    settings = get_settings()
    actor = resolve_admin_actor(settings, x_admin_token, include_inactive=True)
    if actor is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid admin token")
    if actor.status != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin user is inactive")
    return actor


@router.get("/dashboard")
def get_admin_dashboard(
    request: Request,
    tenant_scope: str = Query(..., min_length=1),
    actor: AdminActor = Depends(require_admin_token),
    db: Session = Depends(get_db),
) -> dict:
    if "admin.dashboard.read" not in actor.permissions:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing admin.dashboard.read permission")

    _ensure_admin_user(db, actor)
    tenants = db.scalars(select(ParentAccountModel).order_by(ParentAccountModel.created_at.asc())).all()
    tenant_ids = {tenant.id for tenant in tenants}
    if tenant_scope != "all" and tenant_scope not in tenant_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant scope not found")

    scoped_tenants = tenants if tenant_scope == "all" else [tenant for tenant in tenants if tenant.id == tenant_scope]
    scoped_tenant_ids = {tenant.id for tenant in scoped_tenants}
    children = db.scalars(
        select(ChildProfileModel).where(ChildProfileModel.parent_account_id.in_(scoped_tenant_ids or [""]))
    ).all()
    child_by_id = {child.id: child for child in children}
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
    _record_audit_event(
        db,
        actor=actor,
        tenant_scope=tenant_scope,
        action="admin.dashboard.read",
        resource_type="admin_dashboard",
        resource_id="dashboard",
        risk_level="low",
        result="success",
        trace_id=_trace_id(request),
    )

    return {
        "tenants": [_admin_tenant_payload(tenant, children_by_parent.get(tenant.id, 0), materials) for tenant in scoped_tenants],
        "materials": materials,
        "provider_policies": [_global_provider_policy(), *[_tenant_provider_policy_payload(policy) for policy in policy_rows]],
        "module_settings": _module_settings_payload(scoped_tenants, module_rows),
    }


@router.get("/operations")
def get_admin_operations_snapshot(
    request: Request,
    tenant_scope: str = Query(..., min_length=1),
    actor: AdminActor = Depends(require_admin_token),
    db: Session = Depends(get_db),
) -> dict:
    required_permission = _operations_read_permission(actor)
    _ensure_admin_tenant_scope(db, tenant_scope)
    tenant_count = _operations_tenant_count(db, tenant_scope)

    _ensure_admin_user(db, actor)
    material_status_counts = _operations_material_status_counts(db, tenant_scope)
    material_parse_jobs = _operations_material_parse_job_payload(db, tenant_scope)
    media_generation = _operations_media_generation_payload(db, tenant_scope, material_status_counts)
    speaking_attempts = _operations_speaking_attempts_payload(db, tenant_scope)
    provider_configuration = _operations_provider_configuration_payload(db, tenant_scope)
    module_toggle_coverage = _operations_module_toggle_coverage_payload(db, tenant_scope, tenant_count)
    audit_event = _record_audit_event(
        db,
        actor=actor,
        tenant_scope=tenant_scope,
        action="admin.operations.read",
        resource_type="admin_operations",
        resource_id="operations",
        risk_level="low",
        result="success",
        trace_id=_trace_id(request),
    )

    return {
        "required_permission": required_permission,
        "tenant_scope": tenant_scope,
        "summary": {
            "tenant_count": tenant_count,
            "materials": sum(material_status_counts.values()),
            "material_parse_jobs": material_parse_jobs["total"],
            "media_failures": media_generation["failure_signals"]["total"],
            "speaking_attempts": speaking_attempts["total"],
        },
        "material_parse_jobs": material_parse_jobs,
        "media_generation": media_generation,
        "speaking_attempts": speaking_attempts,
        "provider_configuration": provider_configuration,
        "module_toggle_coverage": module_toggle_coverage,
        "audit_event": _audit_event_payload(audit_event),
        "access_context": _access_context_payload(actor, []),
    }


@router.get("/access")
def get_admin_access(
    tenant_scope: str = Query(..., min_length=1),
    actor: AdminActor = Depends(require_admin_token),
    db: Session = Depends(get_db),
) -> dict:
    if "admin.audit.read" not in actor.permissions:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing admin.audit.read permission")

    _ensure_admin_user(db, actor)
    events = db.scalars(
        select(AdminAuditEventModel)
        .where(_audit_scope_filter(tenant_scope))
        .order_by(AdminAuditEventModel.created_at.desc())
        .limit(50)
    ).all()
    return {
        "current_admin": {
            "id": actor.id,
            "display_name": actor.display_name,
            "email": actor.email,
            "role": actor.role,
            "status": actor.status,
        },
        "permissions": actor.permissions,
        "audit_events": [_audit_event_payload(event) for event in events],
    }


@router.get("/audit-events")
def list_admin_audit_events(
    tenant_scope: str = Query(..., min_length=1),
    action: str = "",
    resource_type: str = "",
    risk_level: str = "",
    result: str = "",
    actor_id: str = "",
    limit: str = Query("50"),
    cursor: str = "",
    actor: AdminActor = Depends(require_admin_token),
    db: Session = Depends(get_db),
) -> dict:
    if "admin.audit.read" not in actor.permissions:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing admin.audit.read permission")

    page_size = _audit_page_limit(limit)
    stmt = select(AdminAuditEventModel).where(_audit_scope_filter(tenant_scope))
    if action:
        stmt = stmt.where(AdminAuditEventModel.action == action)
    if resource_type:
        stmt = stmt.where(AdminAuditEventModel.resource_type == resource_type)
    if risk_level:
        stmt = stmt.where(AdminAuditEventModel.risk_level == risk_level)
    if result:
        stmt = stmt.where(AdminAuditEventModel.result == result)
    if actor_id:
        stmt = stmt.where(AdminAuditEventModel.actor_id == actor_id)
    if cursor:
        cursor_event = db.scalars(stmt.where(AdminAuditEventModel.id == cursor).limit(1)).first()
        if cursor_event is None:
            return {"items": [], "next_cursor": ""}
        stmt = stmt.where(
            or_(
                AdminAuditEventModel.created_at < cursor_event.created_at,
                and_(
                    AdminAuditEventModel.created_at == cursor_event.created_at,
                    AdminAuditEventModel.id < cursor_event.id,
                ),
            )
        )

    events = db.scalars(
        stmt.order_by(AdminAuditEventModel.created_at.desc(), AdminAuditEventModel.id.desc()).limit(page_size + 1)
    ).all()
    page = events[:page_size]
    next_cursor = page[-1].id if len(events) > page_size and page else ""
    return {"items": [_audit_event_payload(event) for event in page], "next_cursor": next_cursor}


@router.get("/tenants/{tenant_id}")
def get_admin_tenant_detail(
    tenant_id: str,
    request: Request,
    tenant_scope: str = Query(..., min_length=1),
    actor: AdminActor = Depends(require_admin_token),
    db: Session = Depends(get_db),
) -> dict:
    if "admin.tenant.read" not in actor.permissions:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing admin.tenant.read permission")

    normalized_tenant_id = tenant_id.strip()
    if tenant_scope != "all" and tenant_scope != normalized_tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    tenant = db.get(ParentAccountModel, normalized_tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    _ensure_admin_user(db, actor)
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
    audit_event = _record_audit_event(
        db,
        actor=actor,
        tenant_scope=tenant.id,
        action="admin.tenant.read",
        resource_type="tenant",
        resource_id=tenant.id,
        risk_level="low",
        result="success",
        trace_id=_trace_id(request),
    )
    recent_audit_events: list[AdminAuditEventModel] = []
    if "admin.audit.read" in actor.permissions:
        recent_audit_events = db.scalars(
            select(AdminAuditEventModel)
            .where(_audit_scope_filter(tenant.id))
            .order_by(AdminAuditEventModel.created_at.desc(), AdminAuditEventModel.id.desc())
            .limit(TENANT_DETAIL_LATEST_LIMIT)
        ).all()
        if audit_event.id not in {event.id for event in recent_audit_events}:
            recent_audit_events = [audit_event, *recent_audit_events[: TENANT_DETAIL_LATEST_LIMIT - 1]]

    return {
        "required_permission": "admin.tenant.read",
        "tenant": _admin_tenant_detail_payload(tenant, risk_summary["risk_level"]),
        "summary": _tenant_summary_payload(children, material_counts),
        "children": [
            _admin_child_payload(child, latest_report_by_child.get(child.id), attempt_count_by_child.get(child.id, 0))
            for child in children
        ],
        "materials": material_payloads,
        "provider_policy": _effective_tenant_provider_policy_payload(tenant.id, policy),
        "module_settings": _module_settings_payload([tenant], module_rows),
        "weekly_reports": _weekly_report_payload(latest_reports, weekly_report_aggregate),
        "speaking_attempts": _speaking_attempt_payload(latest_attempts, speaking_status_counts, speaking_average_score),
        "risk_summary": risk_summary,
        "audit_event": _audit_event_payload(audit_event),
        "access_context": _access_context_payload(actor, recent_audit_events),
    }


@router.post("/materials/{material_id}/archive")
def archive_admin_material(
    material_id: str,
    payload: AdminArchiveMaterialRequest,
    request: Request,
    tenant_scope: str = Query(..., min_length=1),
    actor: AdminActor = Depends(require_admin_token),
    db: Session = Depends(get_db),
) -> dict:
    reason = payload.reason.strip()
    if not reason:
        raise HTTPException(status_code=422, detail="Archive reason is required")
    if "admin.material.archive" not in actor.permissions:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing admin.material.archive permission")

    _ensure_admin_user(db, actor)
    row = db.execute(
        select(CourseMaterialModel, ChildProfileModel, ParentAccountModel)
        .join(ChildProfileModel, ChildProfileModel.id == CourseMaterialModel.child_id)
        .join(ParentAccountModel, ParentAccountModel.id == ChildProfileModel.parent_account_id)
        .where(CourseMaterialModel.id == material_id)
    ).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material not found")
    material, child, parent = row
    if tenant_scope != "all" and parent.id != tenant_scope:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material not found in tenant scope")

    material.status = MaterialStatus.archived.value
    db.add(material)
    db.execute(delete(KnowledgePackModel).where(KnowledgePackModel.material_id == material.id))
    db.execute(delete(ParentCoachingScriptModel).where(ParentCoachingScriptModel.material_id == material.id))
    db.execute(delete(ReviewTaskModel).where(ReviewTaskModel.material_id == material.id))
    db.commit()
    db.refresh(material)

    job = db.scalar(
        select(MaterialParseJobModel)
        .where(MaterialParseJobModel.material_id == material.id)
        .order_by(MaterialParseJobModel.started_at.desc(), MaterialParseJobModel.id.desc())
    )
    audit_event = _record_audit_event(
        db,
        actor=actor,
        tenant_scope=parent.id,
        action="admin.material.archive",
        resource_type="course_material",
        resource_id=material.id,
        risk_level="high",
        result="success",
        trace_id=_trace_id(request),
        reason=reason,
    )
    return {
        "required_permission": "admin.material.archive",
        "material": _admin_material_payload(material, child, parent, job),
        "audit_event": _audit_event_payload(audit_event),
    }


@router.post("/material-jobs/{job_id}/retry")
def retry_admin_material_job(
    job_id: str,
    payload: AdminRetryMaterialJobRequest,
    request: Request,
    tenant_scope: str = Query(..., min_length=1),
    actor: AdminActor = Depends(require_admin_token),
    db: Session = Depends(get_db),
) -> dict:
    reason = payload.reason.strip()
    if not reason:
        raise HTTPException(status_code=422, detail="Retry reason is required")
    if "admin.material.retry" not in actor.permissions:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing admin.material.retry permission")

    _ensure_admin_user(db, actor)
    row = db.execute(
        select(MaterialParseJobModel, CourseMaterialModel, ChildProfileModel, ParentAccountModel)
        .join(CourseMaterialModel, CourseMaterialModel.id == MaterialParseJobModel.material_id)
        .join(ChildProfileModel, ChildProfileModel.id == CourseMaterialModel.child_id)
        .join(ParentAccountModel, ParentAccountModel.id == ChildProfileModel.parent_account_id)
        .where(MaterialParseJobModel.id == job_id)
    ).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material job not found")
    job, material, child, parent = row
    if tenant_scope != "all" and parent.id != tenant_scope:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material job not found in tenant scope")
    if material.status == MaterialStatus.archived.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Archived material cannot be retried")

    job.status = JobStatus.processing.value
    job.warnings = []
    job.confidence_summary = "任务已重新排队。"
    job.finished_at = None
    job.draft_image_records = material.image_records or []
    job.draft_learning_assets = material.learning_assets or []
    material.status = MaterialStatus.processing.value
    db.add_all([job, material])
    db.commit()
    db.refresh(job)
    db.refresh(material)
    try:
        enqueue_material_job(job.id)
    except Exception as exc:
        enqueue_error = str(exc)
        job.status = JobStatus.failed.value
        job.confidence_summary = f"识别任务排队失败：{enqueue_error}"
        job.warnings = [f"识别任务排队失败：{enqueue_error}", "请稍后重新识别。"]
        material.status = MaterialStatus.failed.value
        db.add_all([job, material])
        db.commit()
        db.refresh(job)
        db.refresh(material)
    else:
        enqueue_error = ""

    audit_event = _record_audit_event(
        db,
        actor=actor,
        tenant_scope=parent.id,
        action="admin.material_job.retry",
        resource_type="material_parse_job",
        resource_id=job.id,
        risk_level="high",
        result="failed" if enqueue_error else "success",
        trace_id=_trace_id(request),
        reason=reason,
    )
    response_payload = {
        "required_permission": "admin.material.retry",
        "material": _admin_material_payload(material, child, parent, job),
        "audit_event": _audit_event_payload(audit_event),
    }
    if enqueue_error:
        response_payload["detail"] = "Material retry enqueue failed"
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=response_payload)
    return response_payload


@router.post("/providers/policies")
def override_admin_provider_policy(
    payload: AdminProviderPolicyOverrideRequest,
    request: Request,
    tenant_scope: str = Query(..., min_length=1),
    actor: AdminActor = Depends(require_admin_token),
    db: Session = Depends(get_db),
) -> dict:
    reason = payload.reason.strip()
    if not reason:
        raise HTTPException(status_code=422, detail="Provider policy override reason is required")
    if "admin.provider.override" not in actor.permissions:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing admin.provider.override permission")

    tenant_id = payload.tenant_id.strip()
    tenant = db.get(ParentAccountModel, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    if tenant_scope != "all" and tenant.id != tenant_scope:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found in tenant scope")
    ai_provider = payload.ai_provider.strip().lower()
    media_provider = payload.media_provider.strip().lower()
    fallback_mode = payload.fallback_mode.strip().lower()
    if ai_provider not in AI_PROVIDERS:
        raise HTTPException(status_code=422, detail="Unsupported ai_provider")
    if media_provider not in MEDIA_PROVIDERS:
        raise HTTPException(status_code=422, detail="Unsupported media_provider")
    if fallback_mode not in FALLBACK_MODES:
        raise HTTPException(status_code=422, detail="Unsupported fallback_mode")
    if payload.monthly_guardrail < 0:
        raise HTTPException(status_code=422, detail="monthly_guardrail must be >= 0")

    _ensure_admin_user(db, actor)
    policy = db.scalar(select(TenantProviderPolicyModel).where(TenantProviderPolicyModel.tenant_id == tenant.id))
    if policy is None:
        policy = TenantProviderPolicyModel(tenant_id=tenant.id)
    policy.ai_provider = ai_provider
    policy.media_provider = media_provider
    policy.fallback_mode = fallback_mode
    policy.monthly_guardrail = payload.monthly_guardrail
    policy.source = "tenant_override"
    policy.reason = reason
    policy.created_by = actor.id
    db.add(policy)
    db.commit()
    db.refresh(policy)
    audit_event = _record_audit_event(
        db,
        actor=actor,
        tenant_scope=tenant.id,
        action="admin.provider_policy.override",
        resource_type="tenant_provider_policy",
        resource_id=tenant.id,
        risk_level="high",
        result="success",
        trace_id=_trace_id(request),
        reason=reason,
    )
    return {
        "required_permission": "admin.provider.override",
        "provider_policy": _tenant_provider_policy_payload(policy),
        "audit_event": _audit_event_payload(audit_event),
    }


@router.post("/tenants/{tenant_id}/modules/{module_key}")
def toggle_admin_tenant_module(
    tenant_id: str,
    module_key: str,
    payload: AdminTenantModuleToggleRequest,
    request: Request,
    tenant_scope: str = Query(..., min_length=1),
    actor: AdminActor = Depends(require_admin_token),
    db: Session = Depends(get_db),
) -> dict:
    reason = payload.reason.strip()
    if not reason:
        raise HTTPException(status_code=422, detail="Module toggle reason is required")
    if "admin.tenant.module.toggle" not in actor.permissions:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing admin.tenant.module.toggle permission")

    normalized_module_key = module_key.strip().lower()
    if normalized_module_key not in MODULE_KEYS:
        raise HTTPException(status_code=422, detail="Unsupported module_key")
    tenant = db.get(ParentAccountModel, tenant_id.strip())
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    if tenant_scope != "all" and tenant.id != tenant_scope:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found in tenant scope")

    _ensure_admin_user(db, actor)
    setting = db.scalar(
        select(TenantModuleSettingModel).where(
            TenantModuleSettingModel.tenant_id == tenant.id,
            TenantModuleSettingModel.module_key == normalized_module_key,
        )
    )
    if setting is None:
        setting = TenantModuleSettingModel(tenant_id=tenant.id, module_key=normalized_module_key)
    setting.enabled = payload.enabled
    setting.source = "tenant_override"
    setting.reason = reason
    setting.created_by = actor.id
    db.add(setting)
    db.commit()
    db.refresh(setting)
    audit_event = _record_audit_event(
        db,
        actor=actor,
        tenant_scope=tenant.id,
        action="admin.tenant_module.toggle",
        resource_type="tenant_module_setting",
        resource_id=f"{tenant.id}:{normalized_module_key}",
        risk_level="high",
        result="success",
        trace_id=_trace_id(request),
        reason=reason,
    )
    return {
        "required_permission": "admin.tenant.module.toggle",
        "module_setting": _tenant_module_setting_payload(setting),
        "audit_event": _audit_event_payload(audit_event),
    }


@router.get("/impersonation-sessions")
def list_admin_impersonation_sessions(
    request: Request,
    tenant_scope: str = Query(..., min_length=1),
    session_status: str = Query("active", alias="status"),
    actor: AdminActor = Depends(require_admin_token),
    db: Session = Depends(get_db),
) -> dict:
    if "admin.impersonation.read" not in actor.permissions:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing admin.impersonation.read permission")

    _ensure_admin_tenant_scope(db, tenant_scope)
    normalized_status = session_status.strip().lower()
    if normalized_status not in IMPERSONATION_SESSION_STATUSES:
        raise HTTPException(status_code=422, detail="Unsupported impersonation session status")

    _ensure_admin_user(db, actor)
    stmt = select(AdminImpersonationSessionModel).where(_impersonation_session_scope_filter(tenant_scope))
    if normalized_status != "all":
        stmt = stmt.where(AdminImpersonationSessionModel.status == normalized_status)
    impersonation_sessions = db.scalars(
        stmt.order_by(
            AdminImpersonationSessionModel.updated_at.desc(),
            AdminImpersonationSessionModel.created_at.desc(),
            AdminImpersonationSessionModel.id.desc(),
        ).limit(IMPERSONATION_SESSION_LATEST_LIMIT)
    ).all()
    parent_by_id = _impersonation_session_parent_map(db, impersonation_sessions)
    audit_event = _record_audit_event(
        db,
        actor=actor,
        tenant_scope=tenant_scope,
        action="admin.impersonation.read",
        resource_type="admin_impersonation_session",
        resource_id="list",
        risk_level="low",
        result="success",
        trace_id=_trace_id(request),
    )
    return {
        "required_permission": "admin.impersonation.read",
        "tenant_scope": tenant_scope,
        "status": normalized_status,
        "items": [
            _impersonation_session_payload(
                impersonation_session,
                tenant=parent_by_id.get(impersonation_session.tenant_id),
                target_parent=parent_by_id.get(impersonation_session.target_parent_id),
            )
            for impersonation_session in impersonation_sessions
        ],
        "audit_event": _audit_event_payload(audit_event),
    }


@router.post("/impersonation-sessions")
def start_admin_impersonation_session(
    payload: AdminImpersonationSessionRequest,
    request: Request,
    tenant_scope: str = Query(..., min_length=1),
    actor: AdminActor = Depends(require_admin_token),
    db: Session = Depends(get_db),
) -> dict:
    reason = payload.reason.strip()
    if not reason:
        raise HTTPException(status_code=422, detail="Impersonation reason is required")
    if "admin.impersonation.start" not in actor.permissions:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing admin.impersonation.start permission")

    tenant = db.get(ParentAccountModel, payload.tenant_id.strip())
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    if tenant_scope != "all" and tenant.id != tenant_scope:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    target_parent = db.get(ParentAccountModel, payload.target_parent_id.strip())
    if target_parent is None or target_parent.id != tenant.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target parent not found in tenant scope")

    _ensure_admin_user(db, actor)
    impersonation_session = AdminImpersonationSessionModel(
        tenant_id=tenant.id,
        target_parent_id=target_parent.id,
        actor_id=actor.id,
        status="active",
        reason=reason,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
    )
    db.add(impersonation_session)
    db.commit()
    db.refresh(impersonation_session)
    audit_event = _record_audit_event(
        db,
        actor=actor,
        tenant_scope=tenant.id,
        action="admin.impersonation.start",
        resource_type="admin_impersonation_session",
        resource_id=impersonation_session.id,
        risk_level="high",
        result="success",
        trace_id=_trace_id(request),
        reason=reason,
    )
    return {
        "required_permission": "admin.impersonation.start",
        "impersonation_session": _impersonation_session_payload(
            impersonation_session,
            tenant=tenant,
            target_parent=target_parent,
        ),
        "audit_event": _audit_event_payload(audit_event),
    }


@router.post("/impersonation-sessions/{session_id}/end")
def end_admin_impersonation_session(
    session_id: str,
    payload: AdminImpersonationSessionEndRequest,
    request: Request,
    tenant_scope: str = Query(..., min_length=1),
    actor: AdminActor = Depends(require_admin_token),
    db: Session = Depends(get_db),
) -> dict:
    reason = payload.reason.strip()
    if not reason:
        raise HTTPException(status_code=422, detail="Impersonation end reason is required")
    if "admin.impersonation.end" not in actor.permissions:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing admin.impersonation.end permission")
    _ensure_admin_tenant_scope(db, tenant_scope)

    _ensure_admin_user(db, actor)
    stmt = select(AdminImpersonationSessionModel).where(AdminImpersonationSessionModel.id == session_id)
    if tenant_scope != "all":
        stmt = stmt.where(AdminImpersonationSessionModel.tenant_id == tenant_scope)
    impersonation_session = db.scalar(stmt)
    if impersonation_session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Impersonation session not found")

    already_ended = impersonation_session.status == "ended"
    if already_ended:
        audit_action = "admin.impersonation.end.already_ended"
        audit_risk_level = "medium"
        audit_result = "noop"
    else:
        now = datetime.now(timezone.utc)
        impersonation_session.status = "ended"
        impersonation_session.ended_at = now
        impersonation_session.updated_at = now
        db.add(impersonation_session)
        db.commit()
        db.refresh(impersonation_session)
        audit_action = "admin.impersonation.end"
        audit_risk_level = "high"
        audit_result = "success"

    parent_by_id = _impersonation_session_parent_map(db, [impersonation_session])
    audit_event = _record_audit_event(
        db,
        actor=actor,
        tenant_scope=impersonation_session.tenant_id,
        action=audit_action,
        resource_type="admin_impersonation_session",
        resource_id=impersonation_session.id,
        risk_level=audit_risk_level,
        result=audit_result,
        trace_id=_trace_id(request),
        reason=reason,
    )
    return {
        "required_permission": "admin.impersonation.end",
        "impersonation_session": _impersonation_session_payload(
            impersonation_session,
            tenant=parent_by_id.get(impersonation_session.tenant_id),
            target_parent=parent_by_id.get(impersonation_session.target_parent_id),
        ),
        "audit_event": _audit_event_payload(audit_event),
    }


def _audit_scope_filter(tenant_scope: str):
    if tenant_scope == "all":
        return AdminAuditEventModel.tenant_scope != ""
    return AdminAuditEventModel.tenant_scope.in_(["all", tenant_scope])


def _audit_page_limit(raw_limit: str) -> int:
    try:
        page_size = int(raw_limit)
    except (TypeError, ValueError):
        page_size = 50
    return max(1, min(page_size, 100))


def _operations_read_permission(actor: AdminActor) -> str:
    if "admin.operations.read" in actor.permissions:
        return "admin.operations.read"
    if "admin.dashboard.read" in actor.permissions:
        return "admin.dashboard.read"
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Missing admin.operations.read or admin.dashboard.read permission",
    )


def _ensure_admin_tenant_scope(db: Session, tenant_scope: str) -> None:
    if tenant_scope == "all":
        return
    tenant_count = db.scalar(select(func.count(ParentAccountModel.id)).where(ParentAccountModel.id == tenant_scope))
    if not tenant_count:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant scope not found")


def _operations_tenant_count(db: Session, tenant_scope: str) -> int:
    if tenant_scope == "all":
        value = db.scalar(select(func.count(ParentAccountModel.id)))
        return int(value or 0)
    return 1


def _tenant_child_scope_filter(tenant_scope: str):
    if tenant_scope == "all":
        return ChildProfileModel.parent_account_id != ""
    return ChildProfileModel.parent_account_id == tenant_scope


def _tenant_provider_policy_scope_filter(tenant_scope: str):
    if tenant_scope == "all":
        return TenantProviderPolicyModel.tenant_id != ""
    return TenantProviderPolicyModel.tenant_id == tenant_scope


def _tenant_module_setting_scope_filter(tenant_scope: str):
    if tenant_scope == "all":
        return TenantModuleSettingModel.tenant_id != ""
    return TenantModuleSettingModel.tenant_id == tenant_scope


def _impersonation_session_scope_filter(tenant_scope: str):
    if tenant_scope == "all":
        return AdminImpersonationSessionModel.tenant_id != ""
    return AdminImpersonationSessionModel.tenant_id == tenant_scope


def _impersonation_session_parent_map(
    db: Session,
    impersonation_sessions: list[AdminImpersonationSessionModel],
) -> dict[str, ParentAccountModel]:
    parent_ids = {
        parent_id
        for impersonation_session in impersonation_sessions
        for parent_id in (impersonation_session.tenant_id, impersonation_session.target_parent_id)
        if parent_id
    }
    if not parent_ids:
        return {}
    parents = db.scalars(select(ParentAccountModel).where(ParentAccountModel.id.in_(parent_ids))).all()
    return {parent.id: parent for parent in parents}


def _operations_material_parse_job_payload(db: Session, tenant_scope: str) -> dict:
    by_status = {status_value.value: 0 for status_value in JobStatus}
    rows = db.execute(
        select(MaterialParseJobModel.status, func.count(MaterialParseJobModel.id))
        .join(CourseMaterialModel, CourseMaterialModel.id == MaterialParseJobModel.material_id)
        .join(ChildProfileModel, ChildProfileModel.id == CourseMaterialModel.child_id)
        .where(_tenant_child_scope_filter(tenant_scope))
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
            _tenant_child_scope_filter(tenant_scope),
            MaterialParseJobModel.status == JobStatus.processing.value,
            MaterialParseJobModel.started_at < stale_before,
        )
    )
    oldest_processing_started_at = db.scalar(
        select(func.min(MaterialParseJobModel.started_at))
        .join(CourseMaterialModel, CourseMaterialModel.id == MaterialParseJobModel.material_id)
        .join(ChildProfileModel, ChildProfileModel.id == CourseMaterialModel.child_id)
        .where(
            _tenant_child_scope_filter(tenant_scope),
            MaterialParseJobModel.status == JobStatus.processing.value,
        )
    )
    return {
        "stale_threshold_minutes": OPERATIONS_STALE_THRESHOLD_MINUTES,
        "stale_processing": int(stale_processing or 0),
        "oldest_processing_minutes": _age_minutes(oldest_processing_started_at),
    }


def _latest_operations_material_jobs(db: Session, tenant_scope: str, status_values: list[str]) -> list[dict]:
    rows = db.execute(
        select(MaterialParseJobModel, CourseMaterialModel, ChildProfileModel, ParentAccountModel)
        .join(CourseMaterialModel, CourseMaterialModel.id == MaterialParseJobModel.material_id)
        .join(ChildProfileModel, ChildProfileModel.id == CourseMaterialModel.child_id)
        .join(ParentAccountModel, ParentAccountModel.id == ChildProfileModel.parent_account_id)
        .where(_tenant_child_scope_filter(tenant_scope), MaterialParseJobModel.status.in_(status_values))
        .order_by(MaterialParseJobModel.started_at.desc(), MaterialParseJobModel.id.desc())
        .limit(OPERATIONS_LATEST_LIMIT)
    ).all()
    return [_operations_material_job_item_payload(job, material, child, parent) for job, material, child, parent in rows]


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
        .where(_tenant_child_scope_filter(tenant_scope))
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
        .where(_tenant_child_scope_filter(tenant_scope))
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
            _tenant_child_scope_filter(tenant_scope),
            SpeakingAttemptModel.status.in_(pending_statuses),
            SpeakingAttemptModel.updated_at < stale_before,
        )
    )
    stale_transcribing = db.scalar(
        select(func.count(SpeakingAttemptModel.id))
        .join(ChildProfileModel, ChildProfileModel.id == SpeakingAttemptModel.child_id)
        .where(
            _tenant_child_scope_filter(tenant_scope),
            SpeakingAttemptModel.status == SpeakingAttemptStatus.transcribing.value,
            SpeakingAttemptModel.updated_at < stale_before,
        )
    )
    oldest_pending_updated_at = db.scalar(
        select(func.min(SpeakingAttemptModel.updated_at))
        .join(ChildProfileModel, ChildProfileModel.id == SpeakingAttemptModel.child_id)
        .where(
            _tenant_child_scope_filter(tenant_scope),
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
    rows = db.execute(
        select(SpeakingAttemptModel, ChildProfileModel, ParentAccountModel)
        .join(ChildProfileModel, ChildProfileModel.id == SpeakingAttemptModel.child_id)
        .join(ParentAccountModel, ParentAccountModel.id == ChildProfileModel.parent_account_id)
        .where(_tenant_child_scope_filter(tenant_scope), SpeakingAttemptModel.status.in_(status_values))
        .order_by(SpeakingAttemptModel.updated_at.desc(), SpeakingAttemptModel.id.desc())
        .limit(OPERATIONS_LATEST_LIMIT)
    ).all()
    return [_operations_speaking_attempt_item_payload(attempt, child, parent) for attempt, child, parent in rows]


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
        select(func.count(TenantProviderPolicyModel.id)).where(_tenant_provider_policy_scope_filter(tenant_scope))
    )
    policies = db.scalars(
        select(TenantProviderPolicyModel)
        .where(_tenant_provider_policy_scope_filter(tenant_scope))
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
        "readiness": {
            "ai_provider_ready": _ai_provider_ready(settings),
            "media_image_provider_ready": _media_runtime_provider_ready(
                settings.media_provider,
                settings.media_image_provider,
                settings,
            ),
            "media_tts_provider_ready": _media_runtime_provider_ready(
                settings.media_provider,
                settings.media_tts_provider,
                settings,
            ),
            "speech_provider_ready": _speech_provider_ready(settings),
            "speech_assessment_provider_ready": _speech_assessment_provider_ready(settings),
        },
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
            _tenant_module_setting_scope_filter(tenant_scope),
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


def _ensure_admin_user(db: Session, actor: AdminActor) -> None:
    user = db.get(AdminUserModel, actor.id)
    if user is None:
        user = AdminUserModel(
            id=actor.id,
            email=actor.email,
            display_name=actor.display_name,
            role=actor.role,
            status=actor.status,
            permissions=actor.permissions,
        )
    else:
        user.email = actor.email
        user.display_name = actor.display_name
        user.role = actor.role
        user.status = actor.status
        user.permissions = actor.permissions
    db.add(user)
    db.commit()


def _record_audit_event(
    db: Session,
    *,
    actor: AdminActor,
    tenant_scope: str,
    action: str,
    resource_type: str,
    resource_id: str,
    risk_level: str,
    result: str,
    trace_id: str,
    reason: str = "",
) -> AdminAuditEventModel:
    event = AdminAuditEventModel(
        actor_id=actor.id,
        actor_role=actor.role,
        tenant_scope=tenant_scope,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        risk_level=risk_level,
        result=result,
        reason=reason,
        trace_id=trace_id,
        content_json={},
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def _audit_event_payload(event: AdminAuditEventModel) -> dict:
    return {
        "id": event.id,
        "actor_id": event.actor_id,
        "actor_role": event.actor_role,
        "tenant_scope": event.tenant_scope,
        "action": event.action,
        "resource_type": event.resource_type,
        "resource_id": event.resource_id,
        "risk_level": event.risk_level,
        "result": event.result,
        "reason": event.reason,
        "trace_id": event.trace_id,
        "created_at": _iso(event.created_at),
    }


def _trace_id(request: Request) -> str:
    value = getattr(request.state, "request_id", "")
    return value if value else f"req_{uuid4().hex[:8]}"


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


def _admin_tenant_detail_payload(parent: ParentAccountModel, risk_level: str) -> dict:
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
        "recommended_actions": _unique_strings(
            item for report in reports for item in (report.recommended_actions or [])
        ),
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


def _access_context_payload(actor: AdminActor, events: list[AdminAuditEventModel]) -> dict:
    return {
        "current_admin": {
            "id": actor.id,
            "display_name": actor.display_name,
            "email": actor.email,
            "role": actor.role,
            "status": actor.status,
        },
        "recent_audit_events": [_audit_event_payload(event) for event in events],
    }


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
    return "doubao" if get_settings().ai_provider == "doubao" else "stub"


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


def _impersonation_session_payload(
    impersonation_session: AdminImpersonationSessionModel,
    *,
    tenant: Optional[ParentAccountModel] = None,
    target_parent: Optional[ParentAccountModel] = None,
) -> dict:
    return {
        "id": impersonation_session.id,
        "tenant_id": impersonation_session.tenant_id,
        "target_parent_id": impersonation_session.target_parent_id,
        "actor_id": impersonation_session.actor_id,
        "status": impersonation_session.status,
        "reason": impersonation_session.reason,
        "created_at": _iso(impersonation_session.created_at),
        "expires_at": _iso(impersonation_session.expires_at),
        "ended_at": _iso(impersonation_session.ended_at) if impersonation_session.ended_at else "",
        "updated_at": _iso(impersonation_session.updated_at),
        "tenant_display_name": _parent_display_name(tenant, impersonation_session.tenant_id),
        "target_parent_display_name": _parent_display_name(target_parent, impersonation_session.target_parent_id),
    }


def _parent_display_name(parent: Optional[ParentAccountModel], fallback_id: str) -> str:
    if parent is None:
        return fallback_id
    return parent.display_name or _fallback_parent_name(parent)


def _age_minutes(value: Optional[datetime]) -> int:
    if value is None:
        return 0
    normalized = value
    if isinstance(normalized, str):
        normalized = datetime.fromisoformat(normalized)
    return _elapsed_minutes(normalized)


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
