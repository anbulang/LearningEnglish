from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import and_, delete, or_, select
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
    TenantModuleSettingModel,
    TenantProviderPolicyModel,
)
from app.models.contracts import JobStatus, MaterialStatus
from app.services.job_queue import enqueue_material_job

router = APIRouter(prefix="/admin", tags=["admin"])

ADMIN_PERMISSIONS = [
    "admin.dashboard.read",
    "admin.tenant.read",
    "admin.material.read",
    "admin.material.archive",
    "admin.material.retry",
    "admin.tenant.module.toggle",
    "admin.provider.override",
    "admin.impersonation.start",
    "admin.audit.read",
]

AI_PROVIDERS = {"stub", "doubao"}
MEDIA_PROVIDERS = {"mock", "real"}
FALLBACK_MODES = {"global_stub", "auto_to_mock", "per_tenant"}
MODULE_KEYS = ("worksheet_import", "ai_review", "media_pipeline", "speaking_score", "weekly_reports")


@dataclass(frozen=True)
class AdminActor:
    id: str
    display_name: str
    email: str
    role: str
    status: str
    permissions: list[str]


class AdminCredential(BaseModel):
    id: str
    display_name: str
    email: str
    role: str
    status: str = "active"
    permissions: list[str] = []
    token_sha256: str


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


def require_admin_token(x_admin_token: Optional[str] = Header(default=None)) -> AdminActor:
    if not x_admin_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing admin token")
    settings = get_settings()
    actor = _resolve_admin_actor(settings, x_admin_token)
    if actor is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid admin token")
    if actor.status != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin user is inactive")
    return actor


def _resolve_admin_actor(settings, raw_token: str) -> Optional[AdminActor]:
    credentials = _configured_admin_credentials(settings.admin_api_credentials_json)
    if credentials is not None:
        token_sha256 = _admin_token_hash(raw_token)
        for credential in credentials:
            credential_hash = credential.token_sha256.strip().lower()
            if hmac.compare_digest(token_sha256, credential_hash):
                return AdminActor(
                    id=credential.id,
                    display_name=credential.display_name,
                    email=credential.email,
                    role=credential.role,
                    status=credential.status,
                    permissions=credential.permissions,
                )
        return None

    if not settings.admin_api_token:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Admin API token is not configured")
    if not hmac.compare_digest(raw_token, settings.admin_api_token):
        return None
    return AdminActor(
        id="admin_local",
        display_name="Local Platform Admin",
        email="admin@learningenglish.local",
        role="Platform Owner",
        status="active",
        permissions=ADMIN_PERMISSIONS,
    )


def _configured_admin_credentials(credentials_json: str) -> Optional[list[AdminCredential]]:
    if not credentials_json:
        return None
    try:
        raw_credentials = json.loads(credentials_json)
        if not isinstance(raw_credentials, list):
            raise ValueError("admin credentials must be a list")
        return [AdminCredential.model_validate(item) for item in raw_credentials]
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Admin credentials are invalid")


def _admin_token_hash(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found in tenant scope")
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
        "impersonation_session": _impersonation_session_payload(impersonation_session),
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


def _impersonation_session_payload(impersonation_session: AdminImpersonationSessionModel) -> dict:
    return {
        "id": impersonation_session.id,
        "tenant_id": impersonation_session.tenant_id,
        "target_parent_id": impersonation_session.target_parent_id,
        "actor_id": impersonation_session.actor_id,
        "status": impersonation_session.status,
        "reason": impersonation_session.reason,
        "expires_at": _iso(impersonation_session.expires_at),
        "created_at": _iso(impersonation_session.created_at),
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
