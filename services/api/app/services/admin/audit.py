from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Protocol

from pydantic import BaseModel
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.db.models import AdminAuditEventModel
from app.services.admin.scope import audit_scope_filter


class AdminAuditActor(Protocol):
    id: str
    role: str


class AdminAuditFilters(BaseModel):
    actor_id: Optional[str] = None
    action: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    risk_level: Optional[str] = None
    result: Optional[str] = None
    cursor: Optional[str] = None
    limit: int = 50


def audit_page_limit(raw_limit: object) -> int:
    try:
        page_size = int(raw_limit)
    except (TypeError, ValueError):
        page_size = 50
    return max(1, min(page_size, 100))


def record_admin_audit_event(
    db: Session,
    *,
    actor: AdminAuditActor,
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


def serialize_admin_audit_event(event: AdminAuditEventModel) -> dict:
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


def search_admin_audit_events(db: Session, tenant_scope: str, filters: AdminAuditFilters) -> dict:
    page_size = audit_page_limit(filters.limit)
    stmt = select(AdminAuditEventModel).where(audit_scope_filter(tenant_scope))
    if filters.action:
        stmt = stmt.where(AdminAuditEventModel.action == filters.action)
    if filters.resource_type:
        stmt = stmt.where(AdminAuditEventModel.resource_type == filters.resource_type)
    if filters.resource_id:
        stmt = stmt.where(AdminAuditEventModel.resource_id == filters.resource_id)
    if filters.risk_level:
        stmt = stmt.where(AdminAuditEventModel.risk_level == filters.risk_level)
    if filters.result:
        stmt = stmt.where(AdminAuditEventModel.result == filters.result)
    if filters.actor_id:
        stmt = stmt.where(AdminAuditEventModel.actor_id == filters.actor_id)
    if filters.cursor:
        cursor_event = db.scalars(stmt.where(AdminAuditEventModel.id == filters.cursor).limit(1)).first()
        if cursor_event is None:
            return {"events": [], "items": [], "next_cursor": ""}
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
    serialized = [serialize_admin_audit_event(event) for event in page]
    next_cursor = page[-1].id if len(events) > page_size and page else ""
    return {"events": serialized, "items": serialized, "next_cursor": next_cursor}


def list_resource_timeline(
    db: Session,
    *,
    tenant_scope: str,
    resource_type: str,
    resource_id: str,
    limit: int = 10,
) -> list[dict]:
    page_size = audit_page_limit(limit)
    events = db.scalars(
        select(AdminAuditEventModel)
        .where(
            audit_scope_filter(tenant_scope),
            AdminAuditEventModel.resource_type == resource_type,
            AdminAuditEventModel.resource_id == resource_id,
        )
        .order_by(AdminAuditEventModel.created_at.desc(), AdminAuditEventModel.id.desc())
        .limit(page_size)
    ).all()
    return [serialize_admin_audit_event(event) for event in events]


def _iso(value: datetime) -> str:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc).isoformat()
    return value.astimezone(timezone.utc).isoformat()
