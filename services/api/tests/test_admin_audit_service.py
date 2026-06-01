from __future__ import annotations

from datetime import datetime, timedelta, timezone

from conftest import configure_test_environment


configure_test_environment("learning-english-api-admin-audit-")

from app.core.db import SessionLocal, init_db  # noqa: E402
from app.services.admin.audit import (  # noqa: E402
    AdminAuditFilters,
    list_resource_timeline,
    record_admin_audit_event,
    search_admin_audit_events,
)
from app.services.admin.identity import AdminActor  # noqa: E402


def _actor() -> AdminActor:
    return AdminActor(
        id="admin_audit_service",
        display_name="Audit Service",
        email="audit-service@example.com",
        role="Operations",
        status="active",
        permissions=["admin.audit.read"],
    )


def _record(
    *,
    audit_id: str,
    tenant_scope: str,
    resource_type: str = "course_material",
    resource_id: str = "material_audit_service",
    action: str = "admin.material.archive",
    created_at: datetime,
) -> None:
    with SessionLocal() as db:
        event = record_admin_audit_event(
            db,
            actor=_actor(),
            tenant_scope=tenant_scope,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            risk_level="high",
            result="success",
            trace_id=f"req_{audit_id}",
            reason="Audit service fixture",
        )
        event.id = audit_id
        event.created_at = created_at
        db.add(event)
        db.commit()


def test_record_admin_audit_event_persists_actor_scope_resource_and_reason() -> None:
    init_db()
    with SessionLocal() as db:
        event = record_admin_audit_event(
            db,
            actor=_actor(),
            tenant_scope="tenant_audit_record",
            action="admin.material.retry",
            resource_type="material_parse_job",
            resource_id="job_audit_record",
            risk_level="medium",
            result="success",
            trace_id="req_audit_record",
            reason="Retry after provider timeout",
        )

    assert event.actor_id == "admin_audit_service"
    assert event.tenant_scope == "tenant_audit_record"
    assert event.action == "admin.material.retry"
    assert event.resource_type == "material_parse_job"
    assert event.resource_id == "job_audit_record"
    assert event.risk_level == "medium"
    assert event.result == "success"
    assert event.reason == "Retry after provider timeout"
    assert event.trace_id == "req_audit_record"


def test_search_admin_audit_events_filters_by_tenant_scope_and_resource() -> None:
    init_db()
    now = datetime(2026, 5, 31, 12, 0, tzinfo=timezone.utc)
    _record(audit_id="audit_service_match", tenant_scope="tenant_audit_a", created_at=now)
    _record(
        audit_id="audit_service_other_resource",
        tenant_scope="tenant_audit_a",
        resource_id="material_other",
        created_at=now - timedelta(minutes=1),
    )
    _record(
        audit_id="audit_service_other_scope",
        tenant_scope="tenant_audit_b",
        created_at=now - timedelta(minutes=2),
    )

    with SessionLocal() as db:
        payload = search_admin_audit_events(
            db,
            tenant_scope="tenant_audit_a",
            filters=AdminAuditFilters(resource_type="course_material", resource_id="material_audit_service", limit=20),
        )

    assert [event["id"] for event in payload["events"]] == ["audit_service_match"]
    assert payload["events"][0]["resource_type"] == "course_material"
    assert payload["events"][0]["resource_id"] == "material_audit_service"
    assert payload["next_cursor"] == ""


def test_search_admin_audit_events_returns_stable_next_cursor() -> None:
    init_db()
    now = datetime(2026, 5, 31, 13, 0, tzinfo=timezone.utc)
    _record(audit_id="audit_service_page_1", tenant_scope="tenant_audit_page", created_at=now)
    _record(audit_id="audit_service_page_2", tenant_scope="tenant_audit_page", created_at=now - timedelta(minutes=1))
    _record(audit_id="audit_service_page_3", tenant_scope="tenant_audit_page", created_at=now - timedelta(minutes=2))

    with SessionLocal() as db:
        first_page = search_admin_audit_events(db, tenant_scope="tenant_audit_page", filters=AdminAuditFilters(limit=2))
        second_page = search_admin_audit_events(
            db,
            tenant_scope="tenant_audit_page",
            filters=AdminAuditFilters(limit=2, cursor=first_page["next_cursor"]),
        )

    assert [event["id"] for event in first_page["events"]] == ["audit_service_page_1", "audit_service_page_2"]
    assert first_page["next_cursor"] == "audit_service_page_2"
    assert [event["id"] for event in second_page["events"]] == ["audit_service_page_3"]
    assert second_page["next_cursor"] == ""


def test_list_resource_timeline_returns_newest_first_bounded_events() -> None:
    init_db()
    now = datetime(2026, 5, 31, 14, 0, tzinfo=timezone.utc)
    _record(audit_id="audit_service_timeline_1", tenant_scope="tenant_audit_timeline", created_at=now)
    _record(
        audit_id="audit_service_timeline_2",
        tenant_scope="tenant_audit_timeline",
        created_at=now + timedelta(minutes=1),
    )
    _record(
        audit_id="audit_service_timeline_other",
        tenant_scope="tenant_audit_timeline",
        resource_id="material_other",
        created_at=now + timedelta(minutes=2),
    )

    with SessionLocal() as db:
        timeline = list_resource_timeline(
            db,
            tenant_scope="tenant_audit_timeline",
            resource_type="course_material",
            resource_id="material_audit_service",
            limit=1,
        )

    assert [event["id"] for event in timeline] == ["audit_service_timeline_2"]
