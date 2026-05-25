from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.settings import get_settings
from app.db.models import (
    AdminAuditEventModel,
    AdminUserModel,
    ChildProfileModel,
    CourseMaterialModel,
    KnowledgePackModel,
    MaterialParseJobModel,
    ParentAccountModel,
    ParentCoachingScriptModel,
    ReviewTaskModel,
)
from app.models.contracts import MaterialStatus

router = APIRouter(prefix="/admin", tags=["admin"])

ADMIN_PERMISSIONS = [
    "admin.dashboard.read",
    "admin.tenant.read",
    "admin.material.read",
    "admin.material.archive",
    "admin.audit.read",
]


@dataclass(frozen=True)
class AdminActor:
    id: str
    display_name: str
    email: str
    role: str
    status: str
    permissions: list[str]


class AdminArchiveMaterialRequest(BaseModel):
    reason: str = ""


def require_admin_token(x_admin_token: Optional[str] = Header(default=None)) -> AdminActor:
    if not x_admin_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing admin token")
    if x_admin_token != get_settings().admin_api_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid admin token")
    return AdminActor(
        id="admin_local",
        display_name="Local Platform Admin",
        email="admin@learningenglish.local",
        role="Platform Owner",
        status="active",
        permissions=ADMIN_PERMISSIONS,
    )


@router.get("/dashboard")
def get_admin_dashboard(
    request: Request,
    tenant_scope: str = Query(..., min_length=1),
    actor: AdminActor = Depends(require_admin_token),
    db: Session = Depends(get_db),
) -> dict:
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
    parent_by_id = {tenant.id: tenant for tenant in scoped_tenants}
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
        "provider_policies": [_global_provider_policy()],
    }


@router.get("/access")
def get_admin_access(
    tenant_scope: str = Query(..., min_length=1),
    actor: AdminActor = Depends(require_admin_token),
    db: Session = Depends(get_db),
) -> dict:
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


def _audit_scope_filter(tenant_scope: str):
    if tenant_scope == "all":
        return AdminAuditEventModel.tenant_scope != ""
    return AdminAuditEventModel.tenant_scope.in_(["all", tenant_scope])


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
