# Admin Backend Phase 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the LearningEnglish admin backend from Phase 1 live endpoints to production-grade multi-tenant operations support with configured admin actors, scoped audit search, tenant detail, operations health, and impersonation lifecycle controls.

**Architecture:** Keep the current FastAPI admin route surface stable, but replace fixed admin actor resolution with credential-driven identity and add read-model helpers for audit, tenant detail, operations health, and impersonation sessions. This phase reads database state and provider settings; it does not introspect Celery broker state or implement full admin login.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, pytest, existing `app.api.routes.admin`, existing admin audit/session models.

---

## File Map

- Modify: `services/api/app/core/settings.py`
  - Add `admin_api_credentials_json`.
- Modify: `services/api/app/api/routes/admin.py`
  - Add credential-driven admin actor resolution.
  - Add `admin.operations.read`, `admin.impersonation.read`, `admin.impersonation.end`.
  - Add `/audit-events`, `/tenants/{tenant_id}`, `/operations`, `GET /impersonation-sessions`, `POST /impersonation-sessions/{session_id}/end`.
  - Add pure payload/query helpers for the new routes.
- Modify: `services/api/tests/conftest.py`
  - Keep explicit local `ADMIN_API_TOKEN`.
  - Clear `ADMIN_API_CREDENTIALS_JSON` unless a test sets it.
- Create: `services/api/tests/test_admin_phase2_api.py`
  - Hold new Phase 2 integration tests instead of further growing `test_admin_read_api.py`.
- Modify: `services/api/README.md`
  - Document local token and hashed credential JSON.
- Modify: `infra/env/local.example.env`
  - Add commented `ADMIN_API_CREDENTIALS_JSON` example with fake hash.
- Modify: `docs/harness/mvp-readiness-checklist.md`
  - Add Admin Phase 2 verification note and command.

---

### Task 1: Configured Admin Actors And Permission Boundary

**Files:**
- Modify: `services/api/app/core/settings.py`
- Modify: `services/api/app/api/routes/admin.py`
- Modify: `services/api/tests/conftest.py`
- Create: `services/api/tests/test_admin_phase2_api.py`

- [ ] **Step 1: Write failing credential resolution tests**

Create `services/api/tests/test_admin_phase2_api.py`:

```python
from __future__ import annotations

import hashlib
import json

from app.core.settings import get_settings
from conftest import configure_test_environment


configure_test_environment("learning-english-api-admin-phase2-")


def _token_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _set_admin_credentials(monkeypatch, credentials: list[dict]) -> None:
    monkeypatch.setenv("ADMIN_API_CREDENTIALS_JSON", json.dumps(credentials))
    monkeypatch.delenv("ADMIN_API_TOKEN", raising=False)
    get_settings.cache_clear()


def test_admin_credentials_resolve_actor_and_permissions(api_client, monkeypatch) -> None:
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


def test_admin_credentials_enforce_missing_mutation_permission(api_client, monkeypatch) -> None:
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
cd services/api && .venv/bin/pytest tests/test_admin_phase2_api.py -q
```

Expected: tests fail because `ADMIN_API_CREDENTIALS_JSON` is not read and all tokens are compared only to `ADMIN_API_TOKEN`.

- [ ] **Step 3: Add settings field**

Modify `services/api/app/core/settings.py`:

```python
admin_api_token: str
admin_api_credentials_json: str
admin_cors_origins: tuple[str, ...]
```

In `get_settings()`:

```python
admin_api_token=os.getenv("ADMIN_API_TOKEN", "").strip(),
admin_api_credentials_json=os.getenv("ADMIN_API_CREDENTIALS_JSON", "").strip(),
admin_cors_origins=_csv_tuple(os.getenv("ADMIN_CORS_ORIGINS", "http://127.0.0.1:5173,http://localhost:5173")),
```

- [ ] **Step 4: Clear credential JSON in test environment**

Modify `services/api/tests/conftest.py` inside `configure_test_environment()`:

```python
os.environ["ADMIN_API_TOKEN"] = "local-admin-token"
os.environ.pop("ADMIN_API_CREDENTIALS_JSON", None)
```

- [ ] **Step 5: Implement credential parsing and actor resolution**

Modify `services/api/app/api/routes/admin.py` imports:

```python
import hashlib
import hmac
import json
```

Add helper models near request models:

```python
class AdminCredential(BaseModel):
    id: str
    display_name: str
    email: str
    role: str
    status: str = "active"
    permissions: list[str] = []
    token_sha256: str
```

Replace `require_admin_token()` body with:

```python
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
```

Add helpers:

```python
def _resolve_admin_actor(settings, raw_token: str) -> Optional[AdminActor]:
    credentials = _configured_admin_credentials(settings.admin_api_credentials_json)
    if credentials:
        token_hash = _admin_token_hash(raw_token)
        for credential in credentials:
            if hmac.compare_digest(token_hash, credential.token_sha256.lower()):
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


def _configured_admin_credentials(raw_json: str) -> list[AdminCredential]:
    if not raw_json:
        return []
    try:
        payload = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Admin credentials are invalid") from exc
    if not isinstance(payload, list):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Admin credentials are invalid")
    return [AdminCredential(**item) for item in payload]


def _admin_token_hash(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
```

- [ ] **Step 6: Run credential tests**

Run:

```bash
cd services/api && .venv/bin/pytest tests/test_admin_phase2_api.py -q
```

Expected: all tests in `test_admin_phase2_api.py` pass.

- [ ] **Step 7: Commit**

```bash
git add services/api/app/core/settings.py services/api/app/api/routes/admin.py services/api/tests/conftest.py services/api/tests/test_admin_phase2_api.py
git commit -m "feat(admin): resolve configured admin actors"
```

---

### Task 2: Independent Audit Event Search

**Files:**
- Modify: `services/api/app/api/routes/admin.py`
- Modify: `services/api/tests/test_admin_phase2_api.py`

- [ ] **Step 1: Write failing audit query tests**

Append to `services/api/tests/test_admin_phase2_api.py`:

```python
def test_admin_audit_events_filter_by_action_result_actor_and_tenant(api_client, monkeypatch) -> None:
    _set_admin_credentials(
        monkeypatch,
        [
            {
                "id": "admin_ops",
                "display_name": "Ops Admin",
                "email": "ops@example.com",
                "role": "Operations",
                "status": "active",
                "permissions": ["admin.dashboard.read", "admin.audit.read"],
                "token_sha256": _token_hash("ops-token"),
            }
        ],
    )
    headers = {"X-Admin-Token": "ops-token"}
    first = api_client.get("/v1/admin/dashboard?tenant_scope=all", headers={**headers, "X-Request-ID": "req_admin_all"})
    assert first.status_code == 200
    second = api_client.get("/v1/admin/dashboard?tenant_scope=all", headers={**headers, "X-Request-ID": "req_admin_all_2"})
    assert second.status_code == 200

    response = api_client.get(
        "/v1/admin/audit-events",
        params={
            "tenant_scope": "all",
            "action": "admin.dashboard.read",
            "result": "success",
            "actor_id": "admin_ops",
            "limit": "1",
        },
        headers=headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) == 1
    assert payload["items"][0]["actor_id"] == "admin_ops"
    assert payload["items"][0]["action"] == "admin.dashboard.read"
    assert payload["items"][0]["result"] == "success"
    assert payload["next_cursor"]

    next_page = api_client.get(
        "/v1/admin/audit-events",
        params={
            "tenant_scope": "all",
            "action": "admin.dashboard.read",
            "actor_id": "admin_ops",
            "limit": "1",
            "cursor": payload["next_cursor"],
        },
        headers=headers,
    )

    assert next_page.status_code == 200
    assert len(next_page.json()["items"]) == 1
    assert next_page.json()["items"][0]["id"] != payload["items"][0]["id"]


def test_admin_audit_events_require_permission(api_client, monkeypatch) -> None:
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
```

- [ ] **Step 2: Run tests to verify failure**

```bash
cd services/api && .venv/bin/pytest tests/test_admin_phase2_api.py::test_admin_audit_events_filter_by_action_result_actor_and_tenant tests/test_admin_phase2_api.py::test_admin_audit_events_require_permission -q
```

Expected: `404 Not Found` for missing `/audit-events`.

- [ ] **Step 3: Implement audit route**

Add route to `services/api/app/api/routes/admin.py` after `/access`:

```python
@router.get("/audit-events")
def list_admin_audit_events(
    tenant_scope: str = Query(..., min_length=1),
    action: str = "",
    resource_type: str = "",
    risk_level: str = "",
    result: str = "",
    actor_id: str = "",
    limit: int = Query(50, ge=1, le=100),
    cursor: str = "",
    actor: AdminActor = Depends(require_admin_token),
    db: Session = Depends(get_db),
) -> dict:
    if "admin.audit.read" not in actor.permissions:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing admin.audit.read permission")
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
        cursor_event = db.get(AdminAuditEventModel, cursor)
        if cursor_event is None:
            return {"items": [], "next_cursor": ""}
        stmt = stmt.where(AdminAuditEventModel.created_at <= cursor_event.created_at, AdminAuditEventModel.id != cursor)
    events = db.scalars(stmt.order_by(AdminAuditEventModel.created_at.desc(), AdminAuditEventModel.id.desc()).limit(limit + 1)).all()
    page = events[:limit]
    next_cursor = page[-1].id if len(events) > limit and page else ""
    return {"items": [_audit_event_payload(event) for event in page], "next_cursor": next_cursor}
```

- [ ] **Step 4: Run audit tests**

```bash
cd services/api && .venv/bin/pytest tests/test_admin_phase2_api.py::test_admin_audit_events_filter_by_action_result_actor_and_tenant tests/test_admin_phase2_api.py::test_admin_audit_events_require_permission -q
```

Expected: both tests pass.

- [ ] **Step 5: Commit**

```bash
git add services/api/app/api/routes/admin.py services/api/tests/test_admin_phase2_api.py
git commit -m "feat(admin): add audit event search"
```

---

### Task 3: Tenant Detail Read Model

**Files:**
- Modify: `services/api/app/api/routes/admin.py`
- Modify: `services/api/tests/test_admin_phase2_api.py`

- [ ] **Step 1: Write failing tenant detail tests**

Append:

```python
def test_admin_tenant_detail_returns_scoped_operational_context(api_client) -> None:
    from app.core.db import SessionLocal
    from app.db.models import CourseMaterialModel, MaterialParseJobModel
    from app.models.contracts import JobStatus, MaterialStatus
    from conftest import auth_headers

    headers, _ = auth_headers(api_client, auth_code="admin-phase2-tenant")
    child_response = api_client.post(
        "/v1/children",
        json={
            "name": "Mia",
            "age": 6,
            "level": "starter",
            "learning_goal": "稳定复习",
            "preferred_review_duration_minutes": 10,
            "parent_notes": "",
        },
        headers=headers,
    )
    assert child_response.status_code == 201
    child_id = child_response.json()["id"]
    material_response = api_client.post(
        "/v1/materials",
        data={
            "child_id": child_id,
            "teacher_name": "Emma",
            "lesson_date": "2026-05-25",
            "title": "Tenant Detail Worksheet",
            "topic": "phonics",
            "tags": "admin",
        },
        files=[("files", ("worksheet.jpg", b"tenant detail", "image/jpeg"))],
        headers=headers,
    )
    assert material_response.status_code == 201
    material_id = material_response.json()["material"]["id"]
    dashboard = api_client.get("/v1/admin/dashboard?tenant_scope=all", headers={"X-Admin-Token": "local-admin-token"})
    tenant_id = next(item["tenant_id"] for item in dashboard.json()["materials"] if item["id"] == material_id)
    with SessionLocal() as db:
        material = db.get(CourseMaterialModel, material_id)
        job = db.scalar(__import__("sqlalchemy").select(MaterialParseJobModel).where(MaterialParseJobModel.material_id == material_id))
        assert material is not None
        assert job is not None
        material.status = MaterialStatus.failed.value
        material.learning_assets = [
            {
                "id": "asset_failed",
                "text": "rabbit",
                "kind": "word",
                "generated_image_status": "failed",
                "tts_us_status": "ready",
                "tts_uk_status": "failed",
            }
        ]
        job.status = JobStatus.failed.value
        db.add_all([material, job])
        db.commit()

    response = api_client.get(
        f"/v1/admin/tenants/{tenant_id}?tenant_scope=all",
        headers={"X-Admin-Token": "local-admin-token"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["tenant"]["id"] == tenant_id
    assert payload["children"][0]["id"] == child_id
    assert payload["materials"][0]["id"] == material_id
    assert payload["risk_summary"]["failed_materials"] == 1
    assert payload["risk_summary"]["failed_jobs"] == 1
    assert payload["risk_summary"]["media_failures"] == 2
    assert payload["provider_policy"]["tenant_id"] == tenant_id
    assert any(item["module_key"] == "weekly_reports" for item in payload["module_settings"])


def test_admin_tenant_detail_rejects_cross_scope_access(api_client) -> None:
    response = api_client.get(
        "/v1/admin/tenants/tenant_a?tenant_scope=tenant_b",
        headers={"X-Admin-Token": "local-admin-token"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Tenant not found"
```

- [ ] **Step 2: Run tests to verify failure**

```bash
cd services/api && .venv/bin/pytest tests/test_admin_phase2_api.py::test_admin_tenant_detail_returns_scoped_operational_context tests/test_admin_phase2_api.py::test_admin_tenant_detail_rejects_cross_scope_access -q
```

Expected: `404 Not Found` for missing route.

- [ ] **Step 3: Implement tenant detail route and helpers**

Add route:

```python
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
    if tenant_scope != "all" and tenant_scope != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    tenant = db.get(ParentAccountModel, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    children = db.scalars(select(ChildProfileModel).where(ChildProfileModel.parent_account_id == tenant.id)).all()
    child_by_id = {child.id: child for child in children}
    materials = db.scalars(select(CourseMaterialModel).where(CourseMaterialModel.child_id.in_(child_by_id.keys() or [""]))).all()
    jobs = db.scalars(select(MaterialParseJobModel).where(MaterialParseJobModel.material_id.in_([item.id for item in materials] or [""]))).all()
    job_by_material = {job.material_id: job for job in jobs}
    policy = db.scalar(select(TenantProviderPolicyModel).where(TenantProviderPolicyModel.tenant_id == tenant.id))
    module_rows = db.scalars(select(TenantModuleSettingModel).where(TenantModuleSettingModel.tenant_id == tenant.id)).all()
    reports = db.scalars(select(WeeklyReportModel).where(WeeklyReportModel.child_id.in_(child_by_id.keys() or [""]))).all()
    material_payloads = [
        _admin_material_payload(material, child_by_id[material.child_id], tenant, job_by_material.get(material.id))
        for material in materials
        if material.child_id in child_by_id
    ]
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
    return {
        "tenant": _admin_tenant_payload(tenant, len(children), material_payloads),
        "children": [_admin_child_payload(child) for child in children],
        "materials": material_payloads,
        "provider_policy": _tenant_provider_policy_payload(policy) if policy else {**_global_provider_policy(), "tenant_id": tenant.id},
        "module_settings": _module_settings_payload([tenant], module_rows),
        "weekly_reports": [_weekly_report_payload(report) for report in reports],
        "risk_summary": _tenant_risk_summary(materials, jobs),
        "audit_event": _audit_event_payload(audit_event),
    }
```

Add helpers:

```python
def _admin_child_payload(child: ChildProfileModel) -> dict:
    return {
        "id": child.id,
        "name": child.name,
        "age": child.age,
        "level": child.level,
        "learning_goal": child.learning_goal,
        "preferred_review_duration_minutes": child.preferred_review_duration_minutes,
    }


def _weekly_report_payload(report: WeeklyReportModel) -> dict:
    return {
        "id": report.id,
        "child_id": report.child_id,
        "week_start": report.week_start.isoformat(),
        "week_end": report.week_end.isoformat(),
        "completed_sessions": report.completed_sessions,
        "reviewed_words": report.reviewed_words,
        "speaking_attempts": report.speaking_attempts,
        "weak_items": report.weak_items or [],
        "recommended_actions": report.recommended_actions or [],
    }


def _tenant_risk_summary(materials: list[CourseMaterialModel], jobs: list[MaterialParseJobModel]) -> dict:
    return {
        "failed_materials": sum(1 for item in materials if item.status == MaterialStatus.failed.value),
        "failed_jobs": sum(1 for item in jobs if item.status == JobStatus.failed.value),
        "media_failures": sum(_media_failure_count(material.learning_assets or []) for material in materials),
        "stale_processing_jobs": sum(1 for job in jobs if job.status == JobStatus.processing.value and _elapsed_minutes(job.started_at) > 30),
        "failed_speaking_attempts": 0,
    }


def _media_failure_count(assets: list[dict]) -> int:
    return sum(
        1
        for asset in assets
        for key in ("generated_image_status", "tts_us_status", "tts_uk_status")
        if asset.get(key) == "failed"
    )
```

At the top import `WeeklyReportModel`.

- [ ] **Step 4: Include speaking failures in risk summary**

Extend route before summary:

```python
speaking_attempts = db.scalars(
    select(SpeakingAttemptModel).where(SpeakingAttemptModel.child_id.in_(child_by_id.keys() or [""]))
).all()
```

Change helper signature:

```python
def _tenant_risk_summary(
    materials: list[CourseMaterialModel],
    jobs: list[MaterialParseJobModel],
    speaking_attempts: list[SpeakingAttemptModel],
) -> dict:
```

Set:

```python
"failed_speaking_attempts": sum(1 for attempt in speaking_attempts if attempt.status == SpeakingAttemptStatus.failed.value),
```

At the top import `SpeakingAttemptModel` and `SpeakingAttemptStatus`.

- [ ] **Step 5: Run tenant detail tests**

```bash
cd services/api && .venv/bin/pytest tests/test_admin_phase2_api.py::test_admin_tenant_detail_returns_scoped_operational_context tests/test_admin_phase2_api.py::test_admin_tenant_detail_rejects_cross_scope_access -q
```

Expected: both tests pass.

- [ ] **Step 6: Commit**

```bash
git add services/api/app/api/routes/admin.py services/api/tests/test_admin_phase2_api.py
git commit -m "feat(admin): add tenant detail read model"
```

---

### Task 4: Operations Snapshot

**Files:**
- Modify: `services/api/app/api/routes/admin.py`
- Modify: `services/api/tests/test_admin_phase2_api.py`

- [ ] **Step 1: Write failing operations snapshot test**

Append:

```python
def test_admin_operations_snapshot_summarizes_backend_health(api_client) -> None:
    from datetime import date, datetime, timedelta, timezone
    from app.core.db import SessionLocal
    from app.db.models import ChildProfileModel, CourseMaterialModel, MaterialParseJobModel, ParentAccountModel, SpeakingAttemptModel
    from app.models.contracts import JobStatus, MaterialStatus, SpeakingAttemptStatus

    with SessionLocal() as db:
        parent = ParentAccountModel(
            id="tenant_ops",
            display_name="Ops Tenant",
            wechat_union_id="ops_union",
            wechat_open_id="ops_open",
        )
        child = ChildProfileModel(
            id="child_ops",
            parent_account_id=parent.id,
            name="Mia",
            age=6,
            level="starter",
            learning_goal="稳定复习",
            preferred_review_duration_minutes=10,
            parent_notes="",
        )
        material = CourseMaterialModel(
            id="material_ops",
            child_id=child.id,
            teacher_name="Emma",
            lesson_date=date(2026, 5, 28),
            title="Ops Worksheet",
            topic="phonics",
            status=MaterialStatus.processing.value,
            learning_assets=[
                {"id": "asset_1", "text": "cat", "kind": "word", "generated_image_status": "failed", "tts_us_status": "ready", "tts_uk_status": "pending"},
                {"id": "asset_2", "text": "dog", "kind": "word", "generated_image_status": "processing", "tts_us_status": "failed", "tts_uk_status": "ready"},
            ],
        )
        job = MaterialParseJobModel(
            id="job_ops",
            material_id=material.id,
            status=JobStatus.processing.value,
            started_at=datetime.now(timezone.utc) - timedelta(minutes=45),
        )
        attempt = SpeakingAttemptModel(
            id="attempt_ops",
            child_id=child.id,
            material_id=material.id,
            prompt_text="cat",
            target_text="cat",
            status=SpeakingAttemptStatus.failed.value,
        )
        db.add_all([parent, child, material, job, attempt])
        db.commit()

    response = api_client.get("/v1/admin/operations?tenant_scope=all", headers={"X-Admin-Token": "local-admin-token"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["material_jobs"]["processing"] >= 1
    assert payload["material_jobs"]["stale_processing"] >= 1
    assert payload["material_jobs"]["oldest_processing_minutes"] >= 45
    assert payload["media_generation"]["failed"] >= 2
    assert payload["media_generation"]["pending"] >= 1
    assert payload["media_generation"]["processing"] >= 1
    assert payload["speaking_attempts"]["failed"] >= 1
    assert payload["provider_config"]["ai_provider"] in {"stub", "doubao"}
    assert "openai_api_key" in payload["provider_config"]["secrets_present"]
    assert "sk-" not in str(payload)
```

- [ ] **Step 2: Run test to verify failure**

```bash
cd services/api && .venv/bin/pytest tests/test_admin_phase2_api.py::test_admin_operations_snapshot_summarizes_backend_health -q
```

Expected: `404 Not Found`.

- [ ] **Step 3: Add permission**

Modify `ADMIN_PERMISSIONS`:

```python
"admin.operations.read",
```

- [ ] **Step 4: Implement operations route**

Add route:

```python
@router.get("/operations")
def get_admin_operations(
    tenant_scope: str = Query(..., min_length=1),
    actor: AdminActor = Depends(require_admin_token),
    db: Session = Depends(get_db),
) -> dict:
    if "admin.operations.read" not in actor.permissions and "admin.dashboard.read" not in actor.permissions:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing admin.operations.read permission")
    tenant_ids = _tenant_ids_for_scope(db, tenant_scope)
    materials = _materials_for_tenants(db, tenant_ids)
    material_ids = [material.id for material in materials]
    child_ids = [material.child_id for material in materials]
    jobs = db.scalars(select(MaterialParseJobModel).where(MaterialParseJobModel.material_id.in_(material_ids or [""]))).all()
    speaking_attempts = db.scalars(select(SpeakingAttemptModel).where(SpeakingAttemptModel.child_id.in_(child_ids or [""]))).all()
    return {
        "material_jobs": _material_job_operations_summary(jobs),
        "media_generation": _media_generation_operations_summary(materials),
        "speaking_attempts": _speaking_attempt_operations_summary(speaking_attempts),
        "provider_config": _provider_config_summary(),
    }
```

Add helpers:

```python
def _tenant_ids_for_scope(db: Session, tenant_scope: str) -> list[str]:
    if tenant_scope == "all":
        return list(db.scalars(select(ParentAccountModel.id)).all())
    tenant = db.get(ParentAccountModel, tenant_scope)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant scope not found")
    return [tenant_scope]


def _materials_for_tenants(db: Session, tenant_ids: list[str]) -> list[CourseMaterialModel]:
    rows = db.scalars(
        select(CourseMaterialModel)
        .join(ChildProfileModel, ChildProfileModel.id == CourseMaterialModel.child_id)
        .where(ChildProfileModel.parent_account_id.in_(tenant_ids or [""]))
    ).all()
    return list(rows)


def _material_job_operations_summary(jobs: list[MaterialParseJobModel]) -> dict:
    summary = {status_value: 0 for status_value in ["queued", "processing", "needs_review", "ready", "failed"]}
    processing_minutes: list[int] = []
    for job in jobs:
        summary[job.status] = summary.get(job.status, 0) + 1
        if job.status == JobStatus.processing.value:
            processing_minutes.append(_elapsed_minutes(job.started_at))
    stale = [value for value in processing_minutes if value > 30]
    return {
        **summary,
        "stale_processing": len(stale),
        "oldest_processing_minutes": max(processing_minutes or [0]),
    }


def _media_generation_operations_summary(materials: list[CourseMaterialModel]) -> dict:
    summary = {status_value: 0 for status_value in ["pending", "processing", "ready", "failed"]}
    for material in materials:
        for asset in material.learning_assets or []:
            for key in ("generated_image_status", "tts_us_status", "tts_uk_status"):
                value = str(asset.get(key, "pending"))
                summary[value] = summary.get(value, 0) + 1
    return summary


def _speaking_attempt_operations_summary(attempts: list[SpeakingAttemptModel]) -> dict:
    summary = {status_value: 0 for status_value in ["queued", "recording_uploaded", "transcribing", "scored", "failed"]}
    transcribing_minutes: list[int] = []
    for attempt in attempts:
        summary[attempt.status] = summary.get(attempt.status, 0) + 1
        if attempt.status == SpeakingAttemptStatus.transcribing.value:
            transcribing_minutes.append(_elapsed_minutes(attempt.updated_at))
    stale = [value for value in transcribing_minutes if value > 30]
    return {**summary, "stale_transcribing": len(stale)}


def _provider_config_summary() -> dict:
    settings = get_settings()
    return {
        "ai_provider": settings.ai_provider,
        "media_provider": settings.media_provider,
        "media_image_provider": settings.media_image_provider,
        "media_tts_provider": settings.media_tts_provider,
        "speech_provider": settings.speech_provider,
        "secrets_present": {
            "ark_api_key": bool(settings.ark_api_key),
            "openai_api_key": bool(settings.openai_api_key),
            "dashscope_api_key": bool(settings.dashscope_api_key),
        },
    }
```

- [ ] **Step 5: Run operations test**

```bash
cd services/api && .venv/bin/pytest tests/test_admin_phase2_api.py::test_admin_operations_snapshot_summarizes_backend_health -q
```

Expected: test passes.

- [ ] **Step 6: Commit**

```bash
git add services/api/app/api/routes/admin.py services/api/tests/test_admin_phase2_api.py
git commit -m "feat(admin): add operations health snapshot"
```

---

### Task 5: Impersonation Session List And End

**Files:**
- Modify: `services/api/app/api/routes/admin.py`
- Modify: `services/api/tests/test_admin_phase2_api.py`

- [ ] **Step 1: Write failing impersonation lifecycle test**

Append:

```python
def test_admin_impersonation_sessions_can_be_listed_and_ended(api_client) -> None:
    from conftest import auth_headers

    headers, _ = auth_headers(api_client, auth_code="admin-phase2-impersonation")
    child_response = api_client.post(
        "/v1/children",
        json={
            "name": "Mia",
            "age": 6,
            "level": "starter",
            "learning_goal": "稳定复习",
            "preferred_review_duration_minutes": 10,
            "parent_notes": "",
        },
        headers=headers,
    )
    assert child_response.status_code == 201
    dashboard = api_client.get("/v1/admin/dashboard?tenant_scope=all", headers={"X-Admin-Token": "local-admin-token"})
    tenant_id = dashboard.json()["tenants"][0]["id"]
    start = api_client.post(
        "/v1/admin/impersonation-sessions?tenant_scope=all",
        json={
            "tenant_id": tenant_id,
            "target_parent_id": tenant_id,
            "reason": "Support is reproducing upload issue.",
        },
        headers={"X-Admin-Token": "local-admin-token", "X-Request-ID": "req_imp_start"},
    )
    assert start.status_code == 200
    session_id = start.json()["impersonation_session"]["id"]

    listed = api_client.get(
        "/v1/admin/impersonation-sessions?tenant_scope=all&status=active",
        headers={"X-Admin-Token": "local-admin-token"},
    )

    assert listed.status_code == 200
    assert session_id in {item["id"] for item in listed.json()["items"]}

    ended = api_client.post(
        f"/v1/admin/impersonation-sessions/{session_id}/end?tenant_scope=all",
        json={"reason": "Support case finished."},
        headers={"X-Admin-Token": "local-admin-token", "X-Request-ID": "req_imp_end"},
    )

    assert ended.status_code == 200
    payload = ended.json()
    assert payload["impersonation_session"]["status"] == "ended"
    assert payload["impersonation_session"]["ended_at"]
    assert payload["audit_event"]["action"] == "admin.impersonation.end"
    assert payload["audit_event"]["trace_id"] == "req_imp_end"
```

- [ ] **Step 2: Run test to verify failure**

```bash
cd services/api && .venv/bin/pytest tests/test_admin_phase2_api.py::test_admin_impersonation_sessions_can_be_listed_and_ended -q
```

Expected: list or end route fails.

- [ ] **Step 3: Add request model and permissions**

In `ADMIN_PERMISSIONS` add:

```python
"admin.impersonation.read",
"admin.impersonation.end",
```

Add request model:

```python
class AdminImpersonationSessionEndRequest(BaseModel):
    reason: str = ""
```

- [ ] **Step 4: Implement list route**

Add before start route or after it:

```python
@router.get("/impersonation-sessions")
def list_admin_impersonation_sessions(
    tenant_scope: str = Query(..., min_length=1),
    session_status: str = Query("active", alias="status"),
    actor: AdminActor = Depends(require_admin_token),
    db: Session = Depends(get_db),
) -> dict:
    if "admin.impersonation.read" not in actor.permissions:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing admin.impersonation.read permission")
    stmt = select(AdminImpersonationSessionModel)
    if tenant_scope != "all":
        stmt = stmt.where(AdminImpersonationSessionModel.tenant_id == tenant_scope)
    if session_status:
        stmt = stmt.where(AdminImpersonationSessionModel.status == session_status)
    sessions = db.scalars(stmt.order_by(AdminImpersonationSessionModel.created_at.desc()).limit(100)).all()
    return {"items": [_impersonation_session_payload(session) for session in sessions]}
```

- [ ] **Step 5: Implement end route**

Add:

```python
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
    session = db.get(AdminImpersonationSessionModel, session_id)
    if session is None or (tenant_scope != "all" and session.tenant_id != tenant_scope):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Impersonation session not found")
    if session.status != "active":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Impersonation session is not active")
    session.status = "ended"
    session.ended_at = datetime.now(timezone.utc)
    db.add(session)
    db.commit()
    db.refresh(session)
    audit_event = _record_audit_event(
        db,
        actor=actor,
        tenant_scope=session.tenant_id,
        action="admin.impersonation.end",
        resource_type="admin_impersonation_session",
        resource_id=session.id,
        risk_level="high",
        result="success",
        trace_id=_trace_id(request),
        reason=reason,
    )
    return {
        "required_permission": "admin.impersonation.end",
        "impersonation_session": _impersonation_session_payload(session),
        "audit_event": _audit_event_payload(audit_event),
    }
```

- [ ] **Step 6: Include `ended_at` in payload**

Modify `_impersonation_session_payload()`:

```python
"ended_at": _iso(impersonation_session.ended_at) if impersonation_session.ended_at else "",
```

- [ ] **Step 7: Run impersonation test**

```bash
cd services/api && .venv/bin/pytest tests/test_admin_phase2_api.py::test_admin_impersonation_sessions_can_be_listed_and_ended -q
```

Expected: test passes.

- [ ] **Step 8: Commit**

```bash
git add services/api/app/api/routes/admin.py services/api/tests/test_admin_phase2_api.py
git commit -m "feat(admin): manage impersonation session lifecycle"
```

---

### Task 6: Documentation And Full Verification

**Files:**
- Modify: `services/api/README.md`
- Modify: `infra/env/local.example.env`
- Modify: `docs/harness/mvp-readiness-checklist.md`

Status: completed on 2026-05-29 in `codex/backend-next-phase`; `make api-test` returned `191 passed`, `git diff --check` had no output, and owned docs/config secret scan found no raw test/provider tokens.

- [x] **Step 1: Document admin credentials in API README**

Add to `services/api/README.md` under local admin API configuration:

```markdown
生产化 admin token 建议使用 hash credential JSON，而不是把明文 token 写进仓库或日志：

```bash
python - <<'PY'
import hashlib
print(hashlib.sha256(b"replace-with-admin-token").hexdigest())
PY
```

```bash
export ADMIN_API_CREDENTIALS_JSON='[{"id":"admin_ops","display_name":"Ops Admin","email":"ops@example.com","role":"Operations","status":"active","permissions":["admin.dashboard.read","admin.audit.read","admin.operations.read"],"token_sha256":"<sha256>"}]'
```

`ADMIN_API_TOKEN=local-admin-token` 只用于本地开发或测试环境。API 响应和 audit log 不返回 token 明文。
```

- [x] **Step 2: Add env example**

Append to `infra/env/local.example.env` near admin config:

```bash
# Optional production-like admin credentials. Generate token_sha256 locally; do not store raw admin tokens.
# ADMIN_API_CREDENTIALS_JSON=[{"id":"admin_ops","display_name":"Ops Admin","email":"ops@example.com","role":"Operations","status":"active","permissions":["admin.dashboard.read","admin.audit.read","admin.operations.read"],"token_sha256":"0000000000000000000000000000000000000000000000000000000000000000"}]
```

- [x] **Step 3: Add harness checklist note**

Add to `docs/harness/mvp-readiness-checklist.md` near admin/backend verification notes:

```markdown
Admin Phase 2 后端生产化验证：
- `make api-test` 必须覆盖 configured admin actors、audit event search、tenant detail、operations snapshot、impersonation session lifecycle。
- 本地可以继续使用 `ADMIN_API_TOKEN=local-admin-token`；生产化演练应使用 `ADMIN_API_CREDENTIALS_JSON` 的 SHA-256 token hash。
```

- [x] **Step 4: Run full API verification**

```bash
make api-test
```

Expected: all API tests pass.

- [x] **Step 5: Run documentation diff check**

```bash
git diff --check
```

Expected: no output.

- [x] **Step 6: Commit docs**

```bash
git add services/api/README.md infra/env/local.example.env docs/harness/mvp-readiness-checklist.md
git commit -m "docs: document admin backend phase two"
```

---

## Final Verification

- [x] Run:

```bash
make api-test
git diff --check
```

- [x] Expected:

```text
191 passed
```

`git diff --check` prints no whitespace errors.

- [x] Confirm no raw admin tokens appear in docs except the existing local development placeholder:

```bash
rg -n "readonly-token|ops-token|disabled-token|replace-with-admin-token|sk-" services/api/README.md infra/env/local.example.env docs/harness/mvp-readiness-checklist.md services/api/app/api/routes/admin.py
```

Expected:
- Test-only tokens do not appear in production docs.
- `replace-with-admin-token` appears only in the README hashing example.
- No real secret values appear.

---

## Implementation Notes

- Keep existing Phase 1 endpoints backward compatible.
- Prefer exact integration tests over unit-only tests because admin behavior depends on auth, tenant scope, database rows and audit side effects.
- Do not return token hashes through any API.
- If `services/api/app/api/routes/admin.py` becomes too hard to review during implementation, stop after the current task and split helpers into `app/services/admin_identity.py` and `app/services/admin_read_models.py` in a separate commit.
