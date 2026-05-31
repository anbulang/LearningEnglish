# Admin Operations Platform Phase 3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the LearningEnglish admin backend into a maintainable production-grade multi-tenant operations platform, then connect the Admin UI to the stable Phase 2/3 read models for operations, audit, tenant detail, and impersonation workflows.

**Architecture:** Keep existing `/v1/admin/...` routes and Phase 2 response keys compatible, but move identity, permissions, tenant scope, audit, read-model, operations health, and action-result logic out of `services/api/app/api/routes/admin.py` into focused service modules. Admin UI consumes backend-provided operations vocabulary instead of deriving operational state from dashboard fixtures.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, pytest, React, TypeScript, Vite, Vitest, existing Admin UI theme and i18n.

---

## Current Baseline

- Branch: `codex/admin-operations-platform-phase3`.
- Worktree: `/Users/chaucermini/.codex/worktrees/b7c3/LearningEnglish`.
- Base: local `main` at `949925e`.
- Phase 2 spec and backend are already merged into main.
- `services/api/app/api/routes/admin.py` is the current admin route and helper concentration point.
- `apps/admin` has live calls for dashboard/access and selected mutations, but does not yet use the Phase 2 `/operations`, `/tenants/{tenant_id}`, `/audit-events`, or impersonation list/end read models as first-class screens.

## File Map

### Backend Create

- `services/api/app/services/admin_identity.py`
  - Move `AdminActor`, `AdminCredential`, credential parsing, token hash, local fallback, and inactive credential rejection here.
- `services/api/app/services/admin_permissions.py`
  - Move `ADMIN_PERMISSIONS`, permission constants, `require_permission`, and `require_any_permission` here.
- `services/api/app/services/admin_scope.py`
  - Move tenant scope validation, scope filters, no-disclosure lookup helpers, and impersonation scope filters here.
- `services/api/app/services/admin_audit.py`
  - Move audit write/search/cursor/resource timeline payload logic here.
- `services/api/app/services/admin_read_models.py`
  - Move dashboard and tenant detail read-model builders here.
- `services/api/app/services/admin_operations.py`
  - Move operations snapshot, severity calculation, recommended actions, provider readiness, and bounded latest-list logic here.
- `services/api/app/services/admin_actions.py`
  - Add a common action-result builder used by existing mutation routes.

### Backend Modify

- `services/api/app/api/routes/admin.py`
  - Keep route registration and request models.
  - Replace large helper bodies with service calls.
  - Preserve existing URLs and response keys.
  - Add enhanced `issues` section to `/operations`.
  - Add `action_result` to mutation responses while retaining old resource keys.
- `services/api/app/services/__init__.py`
  - Export nothing unless local package style already requires it; avoid import cycles.
- `services/api/README.md`
  - Document Phase 3 service boundaries, operations read model, and mutation action result.
- `docs/harness/mvp-readiness-checklist.md`
  - Add Phase 3 verification note and commands.

### Backend Tests

- Create `services/api/tests/test_admin_identity_service.py`.
- Create `services/api/tests/test_admin_permissions_service.py`.
- Create `services/api/tests/test_admin_scope_service.py`.
- Create `services/api/tests/test_admin_audit_service.py`.
- Create `services/api/tests/test_admin_read_models_service.py`.
- Create `services/api/tests/test_admin_operations_service.py`.
- Modify `services/api/tests/test_admin_phase2_api.py`.
  - Keep Phase 2 compatibility coverage.
  - Add API contract assertions for `issues` and `action_result`.

### Admin UI Modify

- `apps/admin/src/domain/types.ts`
  - Add Phase 2/3 API types for operations, issues, audit filters, tenant detail, impersonation end, and action result.
- `apps/admin/src/domain/adminApi.ts`
  - Add API clients for operations, tenant detail, audit search, impersonation list/end.
  - Normalize snake_case backend payloads into camelCase UI types.
- `apps/admin/src/domain/adminApi.test.ts`
  - Cover new API clients and normalization.
- `apps/admin/src/domain/mockData.ts`
  - Add Phase 3 fixtures for operations issues, tenant detail, audit pagination, and impersonation sessions.
- `apps/admin/src/App.tsx`
  - Load operations/access/tenant detail data when live API is configured.
  - Pass operations and impersonation handlers into pages.
- `apps/admin/src/pages/CommandCenter.tsx`
  - Use `/operations` data for operational health and issue rows.
  - Keep mock fallback.
- `apps/admin/src/pages/CommandCenter.test.tsx`
  - Cover severity colors, issue rows, and recommended actions.
- `apps/admin/src/pages/TenantDetail.tsx`
  - Prefer tenant detail read model when available.
  - Preserve current dashboard-derived fallback.
- `apps/admin/src/pages/TenantDetail.test.tsx`
  - Cover tenant detail API shape and audit timeline rendering.
- `apps/admin/src/pages/AuditAccess.tsx`
  - Add audit explorer filters, pagination surface, impersonation sessions list, and end action.
- `apps/admin/src/pages/AuditAccess.test.tsx`
  - Cover filters, list/end impersonation, and reason-required behavior.
- Create `apps/admin/src/components/ActionDrawer.tsx`.
  - Shared issue/action drawer with required reason and audit preview.
- Create `apps/admin/src/components/ActionDrawer.test.tsx`.
  - Cover open/close, disabled unavailable action, reason validation, and success rendering.

---

## Task 1: Extract Admin Identity Service

**Files:**
- Create `services/api/app/services/admin_identity.py`
- Modify `services/api/app/api/routes/admin.py`
- Create `services/api/tests/test_admin_identity_service.py`
- Modify `services/api/tests/test_admin_phase2_api.py`

- [ ] **Step 1: Write failing service tests**

Create `services/api/tests/test_admin_identity_service.py` with focused tests:

```python
from __future__ import annotations

import hashlib
import json

from app.services.admin_identity import admin_token_hash, resolve_admin_actor


class _Settings:
    admin_api_token = ""
    admin_api_credentials_json = ""


def _hash(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def test_resolve_admin_actor_from_credentials_json() -> None:
    settings = _Settings()
    settings.admin_api_credentials_json = json.dumps(
        [
            {
                "id": "admin_ops",
                "display_name": "Ops Admin",
                "email": "ops@example.com",
                "role": "Operations",
                "status": "active",
                "permissions": ["admin.dashboard.read", "admin.operations.read"],
                "token_sha256": _hash("ops-token"),
            }
        ]
    )

    actor = resolve_admin_actor(settings, "ops-token")

    assert actor is not None
    assert actor.id == "admin_ops"
    assert actor.display_name == "Ops Admin"
    assert actor.permissions == ["admin.dashboard.read", "admin.operations.read"]


def test_resolve_admin_actor_rejects_inactive_credential() -> None:
    settings = _Settings()
    settings.admin_api_credentials_json = json.dumps(
        [
            {
                "id": "admin_disabled",
                "display_name": "Disabled",
                "email": "disabled@example.com",
                "role": "Operations",
                "status": "disabled",
                "permissions": ["admin.dashboard.read"],
                "token_sha256": _hash("disabled-token"),
            }
        ]
    )

    actor = resolve_admin_actor(settings, "disabled-token")

    assert actor is None


def test_resolve_admin_actor_uses_local_token_fallback() -> None:
    settings = _Settings()
    settings.admin_api_token = "local-admin-token"

    actor = resolve_admin_actor(settings, "local-admin-token")

    assert actor is not None
    assert actor.id == "local_admin"
    assert "admin.dashboard.read" in actor.permissions


def test_admin_token_hash_is_sha256_hex() -> None:
    assert admin_token_hash("local-admin-token") == _hash("local-admin-token")
```

- [ ] **Step 2: Run the failing test**

Run:

```bash
cd services/api && .venv/bin/pytest tests/test_admin_identity_service.py -q
```

Expected output before implementation:

```text
ModuleNotFoundError: No module named 'app.services.admin_identity'
```

- [ ] **Step 3: Implement `admin_identity.py`**

Create `services/api/app/services/admin_identity.py`:

```python
from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from typing import Any, Protocol

from pydantic import BaseModel, ValidationError


class AdminSettings(Protocol):
    admin_api_token: str
    admin_api_credentials_json: str


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


def admin_token_hash(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def resolve_admin_actor(settings: AdminSettings, raw_token: str) -> AdminActor | None:
    credentials = _parse_credentials(settings.admin_api_credentials_json)
    if credentials:
        token_hash = admin_token_hash(raw_token)
        for credential in credentials:
            if not hmac.compare_digest(credential.token_sha256, token_hash):
                continue
            if credential.status != "active":
                return None
            return AdminActor(
                id=credential.id,
                display_name=credential.display_name,
                email=credential.email,
                role=credential.role,
                status=credential.status,
                permissions=list(credential.permissions),
            )
        return None

    if settings.admin_api_token and hmac.compare_digest(settings.admin_api_token, raw_token):
        return _local_admin_actor()
    return None


def _parse_credentials(raw_json: str) -> list[AdminCredential]:
    if not raw_json:
        return []
    try:
        payload: Any = json.loads(raw_json)
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, list):
        return []
    credentials: list[AdminCredential] = []
    for item in payload:
        try:
            credentials.append(AdminCredential.model_validate(item))
        except ValidationError:
            continue
    return credentials


def _local_admin_actor() -> AdminActor:
    return AdminActor(
        id="local_admin",
        display_name="Local Admin",
        email="admin@example.local",
        role="Platform Owner",
        status="active",
        permissions=["*"],
    )
```

Adjust if the current route already uses `BaseModel` versions of these structures and a dataclass would create too much conversion friction; keep the exported field names identical either way.

- [ ] **Step 4: Wire route dependency to the service**

In `services/api/app/api/routes/admin.py`:

- Remove local `AdminActor` and `AdminCredential` definitions after tests are migrated.
- Import `AdminActor` and `resolve_admin_actor`.
- Keep `require_admin_token()` in the route file as the FastAPI dependency:

```python
def require_admin_token(x_admin_token: Optional[str] = Header(default=None)) -> AdminActor:
    if not x_admin_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing admin token")
    actor = resolve_admin_actor(get_settings(), x_admin_token)
    if actor is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid admin token")
    return actor
```

Preserve the existing inactive-token behavior if Phase 2 tests assert a more specific detail such as `Admin user is inactive`; if so, return a typed inactive resolution result from the service instead of flattening it to `None`.

- [ ] **Step 5: Verify compatibility**

Run:

```bash
cd services/api && .venv/bin/pytest tests/test_admin_identity_service.py tests/test_admin_phase2_api.py -q
```

Expected output:

```text
passed
```

- [ ] **Step 6: Commit**

Run:

```bash
git status --short
git add services/api/app/services/admin_identity.py services/api/app/api/routes/admin.py services/api/tests/test_admin_identity_service.py services/api/tests/test_admin_phase2_api.py
git commit -m "refactor: extract admin identity service"
```

---

## Task 2: Extract Permissions And Tenant Scope

**Files:**
- Create `services/api/app/services/admin_permissions.py`
- Create `services/api/app/services/admin_scope.py`
- Modify `services/api/app/api/routes/admin.py`
- Create `services/api/tests/test_admin_permissions_service.py`
- Create `services/api/tests/test_admin_scope_service.py`
- Modify `services/api/tests/test_admin_phase2_api.py`

- [ ] **Step 1: Write permission service tests**

Create `services/api/tests/test_admin_permissions_service.py`:

```python
from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.services.admin_identity import AdminActor
from app.services.admin_permissions import ADMIN_PERMISSIONS, require_any_permission, require_permission


def _actor(permissions: list[str]) -> AdminActor:
    return AdminActor(
        id="admin_ops",
        display_name="Ops",
        email="ops@example.com",
        role="Operations",
        status="active",
        permissions=permissions,
    )


def test_require_permission_allows_exact_permission() -> None:
    require_permission(_actor(["admin.operations.read"]), "admin.operations.read")


def test_require_permission_allows_wildcard() -> None:
    require_permission(_actor(["*"]), "admin.operations.read")


def test_require_permission_raises_stable_detail() -> None:
    with pytest.raises(HTTPException) as exc:
        require_permission(_actor(["admin.dashboard.read"]), "admin.operations.read")

    assert exc.value.status_code == 403
    assert exc.value.detail == "Missing admin.operations.read permission"


def test_admin_permissions_include_phase_three_entries() -> None:
    assert "admin.operations.read" in ADMIN_PERMISSIONS
    assert "admin.impersonation.end" in ADMIN_PERMISSIONS
```

- [ ] **Step 2: Write tenant scope service tests**

Create `services/api/tests/test_admin_scope_service.py` with tests that use the same database factories/payload setup style already present in `test_admin_phase2_api.py`:

```python
from __future__ import annotations

from app.services.admin_scope import normalize_tenant_scope


def test_normalize_tenant_scope_keeps_all_scope() -> None:
    assert normalize_tenant_scope("all") == "all"


def test_normalize_tenant_scope_strips_whitespace() -> None:
    assert normalize_tenant_scope(" tenant_123 ") == "tenant_123"
```

Add DB-backed tests after inspecting the existing test fixture names:

- in-scope tenant returns the tenant row.
- out-of-scope tenant raises `HTTPException(404, "Tenant not found")`.
- `tenant_scope=all` can read any tenant only when the actor has the route's required read permission.

- [ ] **Step 3: Run the failing tests**

Run:

```bash
cd services/api && .venv/bin/pytest tests/test_admin_permissions_service.py tests/test_admin_scope_service.py -q
```

Expected output before implementation:

```text
ModuleNotFoundError
```

- [ ] **Step 4: Implement `admin_permissions.py`**

Move the existing `ADMIN_PERMISSIONS` constant from `admin.py` into `services/api/app/services/admin_permissions.py`.

Export:

```python
ADMIN_DASHBOARD_READ = "admin.dashboard.read"
ADMIN_OPERATIONS_READ = "admin.operations.read"
ADMIN_AUDIT_READ = "admin.audit.read"
ADMIN_MATERIAL_RETRY = "admin.material.retry"
ADMIN_MATERIAL_ARCHIVE = "admin.material.archive"
ADMIN_PROVIDER_OVERRIDE = "admin.provider.override"
ADMIN_TENANT_MODULE_TOGGLE = "admin.tenant.module.toggle"
ADMIN_IMPERSONATION_READ = "admin.impersonation.read"
ADMIN_IMPERSONATION_START = "admin.impersonation.start"
ADMIN_IMPERSONATION_END = "admin.impersonation.end"
```

Implement:

```python
def has_permission(actor: AdminActor, permission: str) -> bool:
    return "*" in actor.permissions or permission in actor.permissions


def require_permission(actor: AdminActor, permission: str) -> None:
    if not has_permission(actor, permission):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Missing {permission} permission")


def require_any_permission(actor: AdminActor, permissions: Sequence[str]) -> None:
    if any(has_permission(actor, permission) for permission in permissions):
        return
    joined = ", ".join(permissions)
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Missing one of {joined} permissions")
```

- [ ] **Step 5: Implement `admin_scope.py`**

Move scope helpers from `admin.py` in small pieces. Start with pure helpers, then DB helpers.

Export:

```python
def normalize_tenant_scope(tenant_scope: str) -> str: ...
def tenant_scope_filter(model: type[Any], tenant_scope: str): ...
def tenant_child_scope_filter(tenant_scope: str): ...
def ensure_admin_tenant_scope(session: Session, tenant_scope: str, tenant_id: str) -> None: ...
def get_tenant_or_404(session: Session, tenant_scope: str, tenant_id: str) -> Tenant: ...
```

The no-disclosure rule must stay the same as Phase 2: if the tenant exists but is outside scope, return the same 404 detail as a missing tenant.

- [ ] **Step 6: Wire routes to permission and scope services**

In `admin.py`:

- Replace local permission helper calls with imports from `admin_permissions.py`.
- Replace local scope filter helpers with imports from `admin_scope.py`.
- Keep route signatures unchanged.
- Keep error details unchanged; update tests if they reveal a real existing detail that differs from the plan text.

- [ ] **Step 7: Verify focused and full admin tests**

Run:

```bash
cd services/api && .venv/bin/pytest tests/test_admin_permissions_service.py tests/test_admin_scope_service.py tests/test_admin_phase2_api.py tests/test_admin_read_api.py -q
```

Expected output:

```text
passed
```

- [ ] **Step 8: Commit**

Run:

```bash
git status --short
git add services/api/app/services/admin_permissions.py services/api/app/services/admin_scope.py services/api/app/api/routes/admin.py services/api/tests/test_admin_permissions_service.py services/api/tests/test_admin_scope_service.py services/api/tests/test_admin_phase2_api.py services/api/tests/test_admin_read_api.py
git commit -m "refactor: extract admin permissions and scope"
```

---

## Task 3: Extract Audit Service And Resource Timeline

**Files:**
- Create `services/api/app/services/admin_audit.py`
- Modify `services/api/app/api/routes/admin.py`
- Create `services/api/tests/test_admin_audit_service.py`
- Modify `services/api/tests/test_admin_phase2_api.py`

- [ ] **Step 1: Write audit service tests**

Create `services/api/tests/test_admin_audit_service.py` using existing model factories or setup helpers from `test_admin_phase2_api.py`.

Cover:

- `record_admin_audit_event()` persists actor, scope, action, resource, risk, result, reason, and trace id.
- `search_admin_audit_events()` filters by `tenant_scope`.
- `search_admin_audit_events()` filters by `resource_type` and `resource_id`.
- cursor pagination returns stable `next_cursor`.
- resource timeline returns newest-first bounded entries.

Expected assertion shape:

```python
payload = search_admin_audit_events(
    session,
    tenant_scope="tenant_alpha",
    filters=AdminAuditFilters(resource_type="course_material", resource_id="material_123"),
    limit=20,
)

assert payload["events"][0]["resource_type"] == "course_material"
assert payload["events"][0]["resource_id"] == "material_123"
assert "next_cursor" in payload
```

- [ ] **Step 2: Run the failing test**

Run:

```bash
cd services/api && .venv/bin/pytest tests/test_admin_audit_service.py -q
```

Expected output before implementation:

```text
ModuleNotFoundError: No module named 'app.services.admin_audit'
```

- [ ] **Step 3: Implement audit service**

Move audit helpers from `admin.py` into `admin_audit.py`.

Export:

```python
class AdminAuditFilters(BaseModel):
    actor_id: str | None = None
    action: str | None = None
    resource_type: str | None = None
    resource_id: str | None = None
    risk_level: str | None = None
    result: str | None = None
    cursor: str | None = None
    limit: int = 50


def record_admin_audit_event(...): ...
def serialize_admin_audit_event(event: AdminAuditEvent) -> dict[str, Any]: ...
def search_admin_audit_events(session: Session, tenant_scope: str, filters: AdminAuditFilters) -> dict[str, Any]: ...
def list_resource_timeline(session: Session, tenant_scope: str, resource_type: str, resource_id: str, limit: int = 10) -> list[dict[str, Any]]: ...
```

Use existing DB model names and field names from `services/api/app/db/models.py`; do not invent new audit tables.

- [ ] **Step 4: Update `/audit-events` route**

In `admin.py`:

- Keep `GET /audit-events` route path and query params.
- Construct `AdminAuditFilters` from query params.
- Call `search_admin_audit_events`.
- Record read audit with existing risk/result behavior.
- Return the same Phase 2 key names.

- [ ] **Step 5: Add API resource timeline assertions**

In `test_admin_phase2_api.py`, add or extend an audit endpoint test:

- create two events for the same resource and one for a different resource.
- call `/v1/admin/audit-events?tenant_scope=all&resource_type=course_material&resource_id=<id>`.
- assert only matching resource events are returned.

- [ ] **Step 6: Verify**

Run:

```bash
cd services/api && .venv/bin/pytest tests/test_admin_audit_service.py tests/test_admin_phase2_api.py -q
```

Expected output:

```text
passed
```

- [ ] **Step 7: Commit**

Run:

```bash
git status --short
git add services/api/app/services/admin_audit.py services/api/app/api/routes/admin.py services/api/tests/test_admin_audit_service.py services/api/tests/test_admin_phase2_api.py
git commit -m "refactor: extract admin audit service"
```

---

## Task 4: Extract Read Models For Dashboard And Tenant Detail

**Files:**
- Create `services/api/app/services/admin_read_models.py`
- Modify `services/api/app/api/routes/admin.py`
- Create `services/api/tests/test_admin_read_models_service.py`
- Modify `services/api/tests/test_admin_phase2_api.py`
- Modify `services/api/tests/test_admin_read_api.py`

- [ ] **Step 1: Write read-model tests**

Create `services/api/tests/test_admin_read_models_service.py`.

Cover:

- dashboard payload includes tenants, materials, provider policies, module settings.
- tenant detail includes children, materials, weekly reports, speaking attempts, module settings, and risk summary.
- tenant detail respects tenant scope.
- latest lists are bounded by existing constants.
- payload uses the same key names as Phase 2 routes.

Use the existing route test setup helpers rather than duplicating large fixture construction.

- [ ] **Step 2: Run failing tests**

Run:

```bash
cd services/api && .venv/bin/pytest tests/test_admin_read_models_service.py -q
```

Expected output before implementation:

```text
ModuleNotFoundError: No module named 'app.services.admin_read_models'
```

- [ ] **Step 3: Implement `admin_read_models.py`**

Move payload builders from `admin.py`:

```python
def build_admin_dashboard(session: Session, tenant_scope: str) -> dict[str, Any]: ...
def build_admin_tenant_detail(session: Session, tenant_scope: str, tenant_id: str) -> dict[str, Any]: ...
def serialize_admin_tenant(...): ...
def serialize_admin_material(...): ...
def serialize_provider_policy(...): ...
def serialize_tenant_module_setting(...): ...
```

Keep these functions free of `Header`, `Depends`, and route-specific `HTTPException` construction except no-disclosure helpers delegated to `admin_scope.py`.

- [ ] **Step 4: Route migration**

In `admin.py`:

- `/dashboard` calls `build_admin_dashboard`.
- `/tenants/{tenant_id}` calls `build_admin_tenant_detail`.
- Route still records read audit and enforces permissions.
- Response keys and casing stay unchanged.

- [ ] **Step 5: Verify compatibility**

Run:

```bash
cd services/api && .venv/bin/pytest tests/test_admin_read_models_service.py tests/test_admin_phase2_api.py tests/test_admin_read_api.py -q
```

Expected output:

```text
passed
```

- [ ] **Step 6: Commit**

Run:

```bash
git status --short
git add services/api/app/services/admin_read_models.py services/api/app/api/routes/admin.py services/api/tests/test_admin_read_models_service.py services/api/tests/test_admin_phase2_api.py services/api/tests/test_admin_read_api.py
git commit -m "refactor: extract admin read models"
```

---

## Task 5: Extract Operations Service And Add Issues Contract

**Files:**
- Create `services/api/app/services/admin_operations.py`
- Modify `services/api/app/api/routes/admin.py`
- Create `services/api/tests/test_admin_operations_service.py`
- Modify `services/api/tests/test_admin_phase2_api.py`

- [ ] **Step 1: Write operations service tests**

Create `services/api/tests/test_admin_operations_service.py`.

Cover:

- no failures returns an empty `issues` list and `summary.severity == "ok"` if existing summary supports this key.
- failed material parse job produces a `critical` issue with `recommended_action == "retry_material_job"`.
- archived or ready materials do not produce retry issues.
- stale processing job produces `warning` with `source == "database_snapshot"`.
- provider policy with real media enabled appears in provider readiness.
- bounded latest lists do not exceed existing limits.

Expected issue assertion:

```python
payload = build_admin_operations(session, tenant_scope="all")

issue = next(item for item in payload["issues"] if item["related_resource"]["type"] == "material_parse_job")
assert issue["severity"] == "critical"
assert issue["recommended_action"] == "retry_material_job"
assert issue["required_permission"] == "admin.material.retry"
assert issue["related_resource"]["tenant_id"] == "tenant_alpha"
```

- [ ] **Step 2: Run failing tests**

Run:

```bash
cd services/api && .venv/bin/pytest tests/test_admin_operations_service.py -q
```

Expected output before implementation:

```text
ModuleNotFoundError: No module named 'app.services.admin_operations'
```

- [ ] **Step 3: Implement operations service**

Move Phase 2 operations helpers from `admin.py` into `admin_operations.py`.

Export:

```python
IssueSeverity = Literal["ok", "info", "warning", "critical"]


def build_admin_operations(session: Session, tenant_scope: str) -> dict[str, Any]: ...
def build_operations_issues(session: Session, tenant_scope: str) -> list[dict[str, Any]]: ...
def classify_material_job_issue(...): ...
def classify_speaking_attempt_issue(...): ...
def build_provider_readiness(...): ...
```

Each issue must include:

```python
{
    "id": "...",
    "severity": "critical",
    "status_label": "Parse failed",
    "reason": "...",
    "recommended_action": "retry_material_job",
    "required_permission": "admin.material.retry",
    "related_resource": {
        "type": "material_parse_job",
        "id": "...",
        "tenant_id": "...",
    },
    "source": "database_snapshot",
}
```

Do not claim worker or broker truth. Any worker-facing status derived from DB state must carry `source: "database_snapshot"`.

- [ ] **Step 4: Update `/operations` route**

In `admin.py`:

- `/operations` calls `build_admin_operations`.
- Keep existing Phase 2 top-level keys.
- Add `issues`.
- Keep read audit.

- [ ] **Step 5: Add API contract tests**

In `test_admin_phase2_api.py`, add assertions:

- `GET /v1/admin/operations?tenant_scope=all` returns existing keys and `issues`.
- every issue has `id`, `severity`, `status_label`, `reason`, `recommended_action`, `related_resource`, and `source`.
- `required_permission` is present when action is executable.
- tenant-scoped operations only show issues for that tenant.

- [ ] **Step 6: Verify**

Run:

```bash
cd services/api && .venv/bin/pytest tests/test_admin_operations_service.py tests/test_admin_phase2_api.py -q
```

Expected output:

```text
passed
```

- [ ] **Step 7: Commit**

Run:

```bash
git status --short
git add services/api/app/services/admin_operations.py services/api/app/api/routes/admin.py services/api/tests/test_admin_operations_service.py services/api/tests/test_admin_phase2_api.py
git commit -m "feat: add admin operations issues contract"
```

---

## Task 6: Standardize Mutation Action Results

**Files:**
- Create `services/api/app/services/admin_actions.py`
- Modify `services/api/app/api/routes/admin.py`
- Modify `services/api/tests/test_admin_phase2_api.py`

- [ ] **Step 1: Write API tests for action result**

In `services/api/tests/test_admin_phase2_api.py`, extend existing mutation tests for:

- material retry.
- material archive.
- provider policy override.
- tenant module toggle.
- impersonation end.

Each mutation response must include:

```python
assert payload["required_permission"] == "admin.material.retry"
assert payload["action_result"] == {
    "action": "retry_material_job",
    "status": "success",
    "resource_type": "material_parse_job",
    "resource_id": job_id,
    "tenant_id": tenant_id,
    "message": "Material parse job queued for retry.",
}
assert payload["audit_event"]["resource_id"] == job_id
```

Keep the old resource key assertions in the same tests, such as `payload["material"]`, `payload["provider_policy"]`, or `payload["module_setting"]`.

- [ ] **Step 2: Run failing mutation tests**

Run:

```bash
cd services/api && .venv/bin/pytest tests/test_admin_phase2_api.py -q
```

Expected output before implementation:

```text
KeyError: 'action_result'
```

- [ ] **Step 3: Implement `admin_actions.py`**

Create:

```python
from __future__ import annotations

from typing import Literal, TypedDict


ActionStatus = Literal["success", "noop", "failed", "unavailable"]


class AdminActionResult(TypedDict):
    action: str
    status: ActionStatus
    resource_type: str
    resource_id: str
    tenant_id: str
    message: str


def build_action_result(
    *,
    action: str,
    status: ActionStatus,
    resource_type: str,
    resource_id: str,
    tenant_id: str,
    message: str,
) -> AdminActionResult:
    return {
        "action": action,
        "status": status,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "tenant_id": tenant_id,
        "message": message,
    }
```

- [ ] **Step 4: Add action result to mutation routes**

In `admin.py`, update each existing mutation response:

- `POST /materials/{material_id}/archive`
  - `required_permission: "admin.material.archive"`
  - `action_result.action: "archive_material"`
- `POST /materials/jobs/{job_id}/retry`
  - `required_permission: "admin.material.retry"`
  - `action_result.action: "retry_material_job"`
- `POST /providers/policies`
  - `required_permission: "admin.provider.override"`
  - `action_result.action: "override_provider_policy"`
- `POST /tenants/{tenant_id}/modules/{module_key}`
  - `required_permission: "admin.tenant.module.toggle"`
  - `action_result.action: "toggle_tenant_module"`
- `POST /impersonation-sessions/{session_id}/end`
  - `required_permission: "admin.impersonation.end"`
  - `action_result.action: "end_impersonation_session"`
  - already-ended behavior returns `status: "noop"` and does not overwrite the original `ended_at`.

Keep existing top-level resource and `audit_event` keys.

- [ ] **Step 5: Verify**

Run:

```bash
cd services/api && .venv/bin/pytest tests/test_admin_phase2_api.py -q
```

Expected output:

```text
passed
```

- [ ] **Step 6: Commit**

Run:

```bash
git status --short
git add services/api/app/services/admin_actions.py services/api/app/api/routes/admin.py services/api/tests/test_admin_phase2_api.py
git commit -m "feat: standardize admin action results"
```

---

## Task 7: Add Admin UI API Contracts And Fixtures

**Files:**
- Modify `apps/admin/src/domain/types.ts`
- Modify `apps/admin/src/domain/adminApi.ts`
- Modify `apps/admin/src/domain/adminApi.test.ts`
- Modify `apps/admin/src/domain/mockData.ts`

- [ ] **Step 1: Add failing API client tests**

In `apps/admin/src/domain/adminApi.test.ts`, add tests for:

- `loadAdminOperations()` maps `issues` and existing operations sections.
- `loadAdminTenantDetail()` maps nested tenant detail data.
- `loadAdminAuditEvents()` forwards filters and maps `next_cursor`.
- `loadAdminImpersonationSessions()` maps sessions.
- `endAdminImpersonationSession()` sends `reason`, maps `action_result`, and returns `auditEvent`.

Use mocked `global.fetch` following the existing test style.

- [ ] **Step 2: Run failing UI tests**

Run:

```bash
cd apps/admin && npm test -- adminApi.test.ts
```

Expected output before implementation:

```text
ReferenceError or TypeError for missing exported API client
```

- [ ] **Step 3: Add TypeScript domain types**

In `apps/admin/src/domain/types.ts`, add:

```ts
export type AdminSeverity = "ok" | "info" | "warning" | "critical";
export type AdminActionStatus = "success" | "noop" | "failed" | "unavailable";

export interface AdminRelatedResource {
  type: string;
  id: string;
  tenantId?: string;
}

export interface AdminOperationsIssue {
  id: string;
  severity: AdminSeverity;
  statusLabel: string;
  reason: string;
  recommendedAction: string;
  requiredPermission?: string;
  relatedResource: AdminRelatedResource;
  source: "database_snapshot";
}

export interface AdminActionResult {
  action: string;
  status: AdminActionStatus;
  resourceType: string;
  resourceId: string;
  tenantId: string;
  message: string;
}

export interface AdminOperationsData {
  summary: Record<string, unknown>;
  materialParseJobs: Record<string, unknown>;
  mediaGeneration: Record<string, unknown>;
  speakingAttempts: Record<string, unknown>;
  providerConfiguration: Record<string, unknown>;
  moduleToggleCoverage: Record<string, unknown>;
  issues: AdminOperationsIssue[];
}
```

Use stricter nested types where the current backend response is already stable; keep `Record<string, unknown>` only for Phase 2 sections that are still broad aggregation maps.

- [ ] **Step 4: Implement API clients**

In `apps/admin/src/domain/adminApi.ts`, add:

```ts
export async function loadAdminOperations(options: AdminApiOptions): Promise<AdminOperationsData> { ... }
export async function loadAdminTenantDetail(options: AdminTenantDetailOptions): Promise<AdminTenantDetailData> { ... }
export async function loadAdminAuditEvents(options: AdminAuditEventsOptions): Promise<AdminAuditEventsData> { ... }
export async function loadAdminImpersonationSessions(options: AdminApiOptions): Promise<AdminImpersonationSessionsData> { ... }
export async function endAdminImpersonationSession(options: EndAdminImpersonationSessionOptions): Promise<EndAdminImpersonationSessionResult> { ... }
```

Follow the existing `apiBaseUrl`, `adminToken`, and `tenantScope` option pattern. Add mapper helpers:

```ts
function mapActionResult(payload: AdminActionResultPayload): AdminActionResult { ... }
function mapOperationsIssue(payload: AdminOperationsIssuePayload): AdminOperationsIssue { ... }
```

- [ ] **Step 5: Add fixtures**

In `mockData.ts`, export:

- `mockOperationsData`.
- `mockTenantDetailData`.
- `mockAuditEventsPage`.
- `mockImpersonationSessions`.

Use bilingual-friendly labels through page rendering, not fixture text that duplicates i18n strings.

- [ ] **Step 6: Verify**

Run:

```bash
cd apps/admin && npm test -- adminApi.test.ts
```

Expected output:

```text
passed
```

- [ ] **Step 7: Commit**

Run:

```bash
git status --short
git add apps/admin/src/domain/types.ts apps/admin/src/domain/adminApi.ts apps/admin/src/domain/adminApi.test.ts apps/admin/src/domain/mockData.ts
git commit -m "feat: add admin operations ui api contracts"
```

---

## Task 8: Wire Command Center To Operations Read Model

**Files:**
- Modify `apps/admin/src/App.tsx`
- Modify `apps/admin/src/pages/CommandCenter.tsx`
- Modify `apps/admin/src/pages/CommandCenter.test.tsx`
- Create `apps/admin/src/components/ActionDrawer.tsx`
- Create `apps/admin/src/components/ActionDrawer.test.tsx`
- Modify `apps/admin/src/i18n/messages.ts`

- [ ] **Step 1: Write page and drawer tests**

Add tests that prove:

- Command Center renders backend operation issues when `operationsData` is passed.
- severity maps to existing status colors or stable class names.
- clicking an issue opens `ActionDrawer`.
- unavailable actions render disabled execution controls.
- action drawer requires a reason before invoking an action.
- Chinese and English labels render through existing i18n.

- [ ] **Step 2: Run failing tests**

Run:

```bash
cd apps/admin && npm test -- CommandCenter.test.tsx ActionDrawer.test.tsx
```

Expected output before implementation:

```text
failed
```

- [ ] **Step 3: Implement `ActionDrawer`**

Create `apps/admin/src/components/ActionDrawer.tsx`:

- props:
  - `language`.
  - `issue`.
  - `isOpen`.
  - `isSubmitting`.
  - `onClose`.
  - `onSubmit(reason)`.
- local state:
  - `reason`.
  - validation error.
- render:
  - issue severity/status/reason.
  - related resource.
  - recommended action.
  - audit preview containing action/resource/risk text.
  - reason textarea.
  - submit/cancel buttons.

Do not add a separate visual theme; reuse `apps/admin/src/components/ui.tsx` and existing CSS tokens.

- [ ] **Step 4: Update Command Center**

In `CommandCenter.tsx`:

- Accept optional `operationsData`.
- Render issue table from `operationsData.issues` when present.
- Preserve existing dashboard-derived fallback for mock or API failure mode.
- Use backend `severity` to select status color.
- Use backend `recommendedAction`, not local guesses.

- [ ] **Step 5: Load operations in `App.tsx`**

In `App.tsx`:

- import `loadAdminOperations`.
- add `operationsData` state initialized to `mockOperationsData`.
- after dashboard/access live load succeeds, call operations endpoint with current `tenantScope`.
- reload operations when `tenantScope` changes and live API is configured.
- pass `operationsData` into `CommandCenter`.

Avoid an infinite effect loop: use one bootstrap effect for dashboard/access and a separate effect keyed by `tenantScope` for operations.

- [ ] **Step 6: Verify**

Run:

```bash
cd apps/admin && npm test -- CommandCenter.test.tsx ActionDrawer.test.tsx
cd apps/admin && npm run build
```

Expected output:

```text
passed
vite build completes
```

- [ ] **Step 7: Commit**

Run:

```bash
git status --short
git add apps/admin/src/App.tsx apps/admin/src/pages/CommandCenter.tsx apps/admin/src/pages/CommandCenter.test.tsx apps/admin/src/components/ActionDrawer.tsx apps/admin/src/components/ActionDrawer.test.tsx apps/admin/src/i18n/messages.ts
git commit -m "feat: wire admin command center operations"
```

---

## Task 9: Wire Tenant Detail, Audit Explorer, And Impersonation Sessions

**Files:**
- Modify `apps/admin/src/App.tsx`
- Modify `apps/admin/src/pages/TenantDetail.tsx`
- Modify `apps/admin/src/pages/TenantDetail.test.tsx`
- Modify `apps/admin/src/pages/AuditAccess.tsx`
- Modify `apps/admin/src/pages/AuditAccess.test.tsx`
- Modify `apps/admin/src/i18n/messages.ts`

- [ ] **Step 1: Write failing page tests**

Cover:

- Tenant Detail renders API tenant detail sections when passed.
- Tenant Detail falls back to dashboard-derived data when API detail is absent.
- Audit Explorer filters by tenant, actor, action, resource type, resource id, risk, and result.
- Audit Explorer pagination uses `nextCursor`.
- Impersonation sessions list active and ended sessions.
- ending impersonation requires reason and calls the API handler.
- already-ended `noop` result appears without changing the displayed original end time.

- [ ] **Step 2: Run failing tests**

Run:

```bash
cd apps/admin && npm test -- TenantDetail.test.tsx AuditAccess.test.tsx
```

Expected output before implementation:

```text
failed
```

- [ ] **Step 3: Load tenant detail in `App.tsx`**

In `App.tsx`:

- import `loadAdminTenantDetail`.
- add `tenantDetailData` state.
- when `activePage === "tenants"` and a selected tenant exists, load `/v1/admin/tenants/{tenant_id}`.
- pass `tenantDetailData` into `TenantDetail`.
- reset detail state when selected tenant changes.

- [ ] **Step 4: Update Tenant Detail page**

In `TenantDetail.tsx`:

- prefer backend detail data for children/materials/weekly reports/speaking attempts/module settings/risk summary.
- keep existing props and fallback behavior.
- show embedded audit timeline only when audit data is passed by `App` or page state; do not silently fake audit rows.

- [ ] **Step 5: Add Audit Explorer filters**

In `AuditAccess.tsx`:

- call new props for `onLoadAuditEvents(filters)`.
- render filter controls using existing compact admin style.
- show cursor pagination controls when `nextCursor` exists.
- map risk/result to existing status styles.

- [ ] **Step 6: Add impersonation list/end UI**

In `AuditAccess.tsx`:

- accept `impersonationSessions`.
- display active/ended/expired status.
- keep existing start impersonation flow.
- add end flow with required reason.
- call `onEndImpersonationSession(sessionId, reason)`.
- display `actionResult.status` and `auditEvent` after success.

- [ ] **Step 7: Wire API handlers in `App.tsx`**

Add live handlers:

- `loadAdminAuditEvents`.
- `loadAdminImpersonationSessions`.
- `endAdminImpersonationSession`.

Update state after end:

- replace the ended session with returned session payload if present.
- prepend returned audit event to access/audit data.
- preserve old session when result is `noop` and returned payload says no state changed.

- [ ] **Step 8: Verify**

Run:

```bash
cd apps/admin && npm test -- TenantDetail.test.tsx AuditAccess.test.tsx
cd apps/admin && npm run build
```

Expected output:

```text
passed
vite build completes
```

- [ ] **Step 9: Commit**

Run:

```bash
git status --short
git add apps/admin/src/App.tsx apps/admin/src/pages/TenantDetail.tsx apps/admin/src/pages/TenantDetail.test.tsx apps/admin/src/pages/AuditAccess.tsx apps/admin/src/pages/AuditAccess.test.tsx apps/admin/src/i18n/messages.ts
git commit -m "feat: wire admin tenant audit impersonation views"
```

---

## Task 10: Documentation And Full Verification

**Files:**
- Modify `services/api/README.md`
- Modify `apps/admin/README.md` if it exists
- Modify `docs/harness/mvp-readiness-checklist.md`
- Modify `docs/superpowers/specs/2026-05-31-admin-operations-platform-phase3-design.md`

- [ ] **Step 1: Update backend documentation**

In `services/api/README.md`, document:

- Phase 3 service modules and responsibilities.
- `/v1/admin/operations` `issues` contract.
- mutation `action_result` contract.
- `source="database_snapshot"` limitation for worker-facing health.
- verification command:

```bash
make api-test
```

- [ ] **Step 2: Update Admin UI documentation**

If `apps/admin/README.md` exists, update it. If it does not exist, create it with:

- local environment variables:
  - `VITE_ADMIN_API_BASE_URL`.
  - `VITE_ADMIN_API_TOKEN`.
- live fallback behavior.
- supported Phase 3 screens:
  - Command Center operations.
  - Tenant Detail.
  - Audit Explorer.
  - Impersonation Sessions.
- verification commands:

```bash
cd apps/admin && npm test
cd apps/admin && npm run build
```

- [ ] **Step 3: Update readiness checklist**

In `docs/harness/mvp-readiness-checklist.md`, add a short Phase 3 admin evidence item:

- backend service tests.
- API compatibility.
- Admin UI test/build.
- explicit note that SSO, DB-backed role mutation, and worker broker introspection are still outside Phase 3.

- [ ] **Step 4: Update spec status**

At the bottom of `docs/superpowers/specs/2026-05-31-admin-operations-platform-phase3-design.md`, add an implementation status note with:

- implemented service modules.
- implemented UI pages.
- verification commands run.
- remaining deferred production items from the non-goals.

- [ ] **Step 5: Run full verification**

Run:

```bash
make api-test
cd apps/admin && npm test
cd apps/admin && npm run build
git diff --check
```

Expected output:

```text
make api-test completes successfully
vitest passes
vite build completes
git diff --check prints no output
```

If `services/api/.venv/bin/pytest` or `node_modules` is missing, run the repo's documented dependency setup command first. Do not mark verification complete until the actual test/build commands have run successfully in this worktree.

- [ ] **Step 6: Commit**

Run:

```bash
git status --short
git add services/api/README.md apps/admin/README.md docs/harness/mvp-readiness-checklist.md docs/superpowers/specs/2026-05-31-admin-operations-platform-phase3-design.md
git commit -m "docs: document admin operations platform phase three"
```

---

## Final Review Checklist

- [ ] `services/api/app/api/routes/admin.py` is materially smaller or its local helper surface is materially reduced.
- [ ] No existing `/v1/admin/...` route path is renamed.
- [ ] Phase 2 response keys remain present.
- [ ] `/v1/admin/operations` includes `issues`.
- [ ] mutation responses include `required_permission`, `action_result`, and `audit_event`.
- [ ] every mutation still requires reason, exact permission, tenant scope, and audit write.
- [ ] no-disclosure 404 behavior remains covered by tests.
- [ ] Admin UI keeps Chinese/English language switching.
- [ ] Admin UI keeps the warm LearningEnglish theme and dense operations-table style.
- [ ] Admin UI uses backend severity/status vocabulary instead of local issue guessing.
- [ ] docs explicitly state that SSO, DB-backed role mutation, and real broker introspection are outside Phase 3.
- [ ] `make api-test` passes.
- [ ] `cd apps/admin && npm test` passes.
- [ ] `cd apps/admin && npm run build` passes.
- [ ] `git diff --check` passes.

## Suggested Execution Order

1. Backend extraction first: Tasks 1 through 4.
2. Operations and action contract: Tasks 5 and 6.
3. Admin UI API contract: Task 7.
4. Admin UI screen wiring: Tasks 8 and 9.
5. Documentation and full verification: Task 10.

This order keeps each commit reviewable and prevents the UI from binding to temporary backend shapes.
