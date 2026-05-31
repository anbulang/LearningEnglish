# LearningEnglish Admin 运维平台 Phase 3 实施计划

> **给执行代理：** 必须使用 `superpowers:subagent-driven-development`（推荐）或 `superpowers:executing-plans` 按任务执行本计划。执行过程中使用复选框（`- [ ]`）跟踪进度。

**目标：** 把 LearningEnglish admin 后端推进为可维护的生产级多租户运维平台，并让 Admin UI 接入稳定的 Phase 2/3 读模型，覆盖 operations、audit、tenant detail 和 impersonation 工作流。

**架构：** 保持现有 `/v1/admin/...` route 与 Phase 2 response key 兼容，但把 identity、permissions、tenant scope、audit、read model、operations health、action result 从 `services/api/app/api/routes/admin.py` 拆到聚焦的 service 模块。Admin UI 消费后端提供的 operations 词汇与 severity/status，不再从 dashboard fixture 里本地推断运维状态。

**技术栈：** FastAPI、SQLAlchemy、Pydantic、pytest、React、TypeScript、Vite、Vitest、现有 Admin UI 主题与 i18n。

---

## 当前基线

- 分支：`codex/admin-operations-platform-phase3`。
- 工作树：`/Users/chaucermini/.codex/worktrees/b7c3/LearningEnglish`。
- 基线：本地 `main` 的 `949925e`。
- Phase 2 spec 和 backend 已合入 main。
- `services/api/app/api/routes/admin.py` 仍是 admin route 与 helper 的主要集中点。
- `apps/admin` 已有 dashboard/access 与部分 mutation 的 live 调用，但还没有把 Phase 2 的 `/operations`、`/tenants/{tenant_id}`、`/audit-events`、impersonation list/end 作为一等页面数据源。

## 文件地图

### 后端新增文件

- `services/api/app/services/admin_identity.py`
  - 放置 `AdminActor`、`AdminCredential`、credential JSON 解析、token hash、本地 token fallback、inactive credential 拒绝逻辑。
- `services/api/app/services/admin_permissions.py`
  - 放置 `ADMIN_PERMISSIONS`、permission 常量、`require_permission`、`require_any_permission`。
- `services/api/app/services/admin_scope.py`
  - 放置 tenant scope 校验、scope filter、no-disclosure lookup helper、impersonation scope filter。
- `services/api/app/services/admin_audit.py`
  - 放置 audit 写入、搜索、cursor pagination、resource timeline payload 逻辑。
- `services/api/app/services/admin_read_models.py`
  - 放置 dashboard 与 tenant detail read-model builder。
- `services/api/app/services/admin_operations.py`
  - 放置 operations snapshot、severity 计算、recommended action、provider readiness、有界 latest list 逻辑。
- `services/api/app/services/admin_actions.py`
  - 放置现有 mutation route 共用的 action result builder。

### 后端修改文件

- `services/api/app/api/routes/admin.py`
  - 保留 route 注册和 request model。
  - 大块 helper body 改为调用 service。
  - 保留现有 URL 和 response key。
  - 给 `/operations` 增加增强版 `issues` section。
  - 给 mutation response 增加 `action_result`，同时保留旧 resource key。
- `services/api/app/services/__init__.py`
  - 除非本地 package 风格需要，否则不新增集中导出，避免 import cycle。
- `services/api/README.md`
  - 记录 Phase 3 service 边界、operations read model、mutation action result。
- `docs/harness/mvp-readiness-checklist.md`
  - 增加 Phase 3 验证说明和命令。

### 后端测试文件

- 新增 `services/api/tests/test_admin_identity_service.py`。
- 新增 `services/api/tests/test_admin_permissions_service.py`。
- 新增 `services/api/tests/test_admin_scope_service.py`。
- 新增 `services/api/tests/test_admin_audit_service.py`。
- 新增 `services/api/tests/test_admin_read_models_service.py`。
- 新增 `services/api/tests/test_admin_operations_service.py`。
- 修改 `services/api/tests/test_admin_phase2_api.py`。
  - 保留 Phase 2 兼容性覆盖。
  - 增加 `issues` 与 `action_result` 的 API contract 断言。

### 后台 UI 修改文件

- `apps/admin/src/domain/types.ts`
  - 增加 Phase 2/3 API 类型：operations、issues、audit filters、tenant detail、impersonation end、action result。
- `apps/admin/src/domain/adminApi.ts`
  - 增加 operations、tenant detail、audit search、impersonation list/end API client。
  - 把后端 snake_case payload 归一化成 UI 侧 camelCase type。
- `apps/admin/src/domain/adminApi.test.ts`
  - 覆盖新增 API client 与 normalization。
- `apps/admin/src/domain/mockData.ts`
  - 增加 Phase 3 fixture：operations issues、tenant detail、audit pagination、impersonation sessions。
- `apps/admin/src/App.tsx`
  - live API 配置存在时加载 operations/access/tenant detail 数据。
  - 把 operations 与 impersonation handler 传入页面。
- `apps/admin/src/pages/CommandCenter.tsx`
  - 使用 `/operations` 数据展示 operational health 与 issue rows。
  - 保留 mock fallback。
- `apps/admin/src/pages/CommandCenter.test.tsx`
  - 覆盖 severity 颜色、issue rows、recommended actions。
- `apps/admin/src/pages/TenantDetail.tsx`
  - 优先使用 tenant detail read model。
  - 保留当前 dashboard-derived fallback。
- `apps/admin/src/pages/TenantDetail.test.tsx`
  - 覆盖 tenant detail API shape 与 audit timeline 渲染。
- `apps/admin/src/pages/AuditAccess.tsx`
  - 增加 audit explorer filters、pagination surface、impersonation sessions list、end action。
- `apps/admin/src/pages/AuditAccess.test.tsx`
  - 覆盖 filters、list/end impersonation、reason required。
- 新增 `apps/admin/src/components/ActionDrawer.tsx`。
  - 共用 issue/action drawer，包含 required reason 和 audit preview。
- 新增 `apps/admin/src/components/ActionDrawer.test.tsx`。
  - 覆盖 open/close、disabled unavailable action、reason validation、success rendering。

---

## 任务 1：抽取管理员身份服务

**文件：**
- 新增 `services/api/app/services/admin_identity.py`
- 修改 `services/api/app/api/routes/admin.py`
- 新增 `services/api/tests/test_admin_identity_service.py`
- 修改 `services/api/tests/test_admin_phase2_api.py`

- [ ] **步骤 1：先写失败的 service 测试**

新增 `services/api/tests/test_admin_identity_service.py`，覆盖 credential JSON、inactive credential、本地 token fallback 与 hash：

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

- [ ] **步骤 2：运行失败测试**

执行：

```bash
cd services/api && .venv/bin/pytest tests/test_admin_identity_service.py -q
```

实现前预期输出：

```text
ModuleNotFoundError: No module named 'app.services.admin_identity'
```

- [ ] **步骤 3：实现 `admin_identity.py`**

新增 `services/api/app/services/admin_identity.py`：

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

如果当前 route 里的 `AdminActor` 已经是 Pydantic model，并且 dataclass 会导致转换成本过高，可以保留 Pydantic 版本；但导出的字段名必须保持一致。

- [ ] **步骤 4：把 route dependency 接到 service**

在 `services/api/app/api/routes/admin.py` 中：

- 迁移测试后移除本地 `AdminActor` 和 `AdminCredential` 定义。
- import `AdminActor` 和 `resolve_admin_actor`。
- 保留 `require_admin_token()` 作为 FastAPI dependency：

```python
def require_admin_token(x_admin_token: Optional[str] = Header(default=None)) -> AdminActor:
    if not x_admin_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing admin token")
    actor = resolve_admin_actor(get_settings(), x_admin_token)
    if actor is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid admin token")
    return actor
```

如果 Phase 2 测试要求 inactive token 返回更具体的 `Admin user is inactive`，service 应返回 typed resolution result，而不是把 inactive 简化成 `None`。

- [ ] **步骤 5：验证兼容性**

执行：

```bash
cd services/api && .venv/bin/pytest tests/test_admin_identity_service.py tests/test_admin_phase2_api.py -q
```

预期输出：

```text
passed
```

- [ ] **步骤 6：提交**

执行：

```bash
git status --short
git add services/api/app/services/admin_identity.py services/api/app/api/routes/admin.py services/api/tests/test_admin_identity_service.py services/api/tests/test_admin_phase2_api.py
git commit -m "refactor: extract admin identity service"
```

---

## 任务 2：抽取权限与租户范围服务

**文件：**
- 新增 `services/api/app/services/admin_permissions.py`
- 新增 `services/api/app/services/admin_scope.py`
- 修改 `services/api/app/api/routes/admin.py`
- 新增 `services/api/tests/test_admin_permissions_service.py`
- 新增 `services/api/tests/test_admin_scope_service.py`
- 修改 `services/api/tests/test_admin_phase2_api.py`

- [ ] **步骤 1：写 permission service 测试**

新增 `services/api/tests/test_admin_permissions_service.py`：

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

- [ ] **步骤 2：写 tenant scope service 测试**

新增 `services/api/tests/test_admin_scope_service.py`，先覆盖纯函数，再按 `test_admin_phase2_api.py` 的 fixture 风格补 DB 测试：

```python
from __future__ import annotations

from app.services.admin_scope import normalize_tenant_scope


def test_normalize_tenant_scope_keeps_all_scope() -> None:
    assert normalize_tenant_scope("all") == "all"


def test_normalize_tenant_scope_strips_whitespace() -> None:
    assert normalize_tenant_scope(" tenant_123 ") == "tenant_123"
```

DB 测试必须覆盖：

- in-scope tenant 返回 tenant row。
- out-of-scope tenant 抛出 `HTTPException(404, "Tenant not found")`。
- `tenant_scope=all` 只在 actor 拥有对应 read permission 时可读。

- [ ] **步骤 3：运行失败测试**

执行：

```bash
cd services/api && .venv/bin/pytest tests/test_admin_permissions_service.py tests/test_admin_scope_service.py -q
```

实现前预期输出：

```text
ModuleNotFoundError
```

- [ ] **步骤 4：实现 `admin_permissions.py`**

把现有 `ADMIN_PERMISSIONS` 从 `admin.py` 移到 `services/api/app/services/admin_permissions.py`。

导出：

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

实现：

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

- [ ] **步骤 5：实现 `admin_scope.py`**

小步迁移 `admin.py` 里的 scope helper。先迁移纯 helper，再迁移 DB helper。

导出：

```python
def normalize_tenant_scope(tenant_scope: str) -> str: ...
def tenant_scope_filter(model: type[Any], tenant_scope: str): ...
def tenant_child_scope_filter(tenant_scope: str): ...
def ensure_admin_tenant_scope(session: Session, tenant_scope: str, tenant_id: str) -> None: ...
def get_tenant_or_404(session: Session, tenant_scope: str, tenant_id: str) -> Tenant: ...
```

no-disclosure 规则必须保持 Phase 2 行为：tenant 存在但超出 scope 时，返回与 tenant 不存在相同的 404 detail。

- [ ] **步骤 6：把 route 接到 permission 和 scope service**

在 `admin.py` 中：

- 用 `admin_permissions.py` 的 import 替换本地 permission helper。
- 用 `admin_scope.py` 的 import 替换本地 scope filter helper。
- route signature 不变。
- error detail 不变；如果测试暴露现有 detail 与计划文字不同，以已有测试合同为准。

- [ ] **步骤 7：验证 focused 与 full admin 测试**

执行：

```bash
cd services/api && .venv/bin/pytest tests/test_admin_permissions_service.py tests/test_admin_scope_service.py tests/test_admin_phase2_api.py tests/test_admin_read_api.py -q
```

预期输出：

```text
passed
```

- [ ] **步骤 8：提交**

执行：

```bash
git status --short
git add services/api/app/services/admin_permissions.py services/api/app/services/admin_scope.py services/api/app/api/routes/admin.py services/api/tests/test_admin_permissions_service.py services/api/tests/test_admin_scope_service.py services/api/tests/test_admin_phase2_api.py services/api/tests/test_admin_read_api.py
git commit -m "refactor: extract admin permissions and scope"
```

---

## 任务 3：抽取审计服务与资源时间线

**文件：**
- 新增 `services/api/app/services/admin_audit.py`
- 修改 `services/api/app/api/routes/admin.py`
- 新增 `services/api/tests/test_admin_audit_service.py`
- 修改 `services/api/tests/test_admin_phase2_api.py`

- [ ] **步骤 1：写 audit service 测试**

新增 `services/api/tests/test_admin_audit_service.py`，使用 `test_admin_phase2_api.py` 中已有的 model factory 或 setup helper。

覆盖：

- `record_admin_audit_event()` 持久化 actor、scope、action、resource、risk、result、reason、trace id。
- `search_admin_audit_events()` 按 `tenant_scope` 过滤。
- `search_admin_audit_events()` 按 `resource_type` 和 `resource_id` 过滤。
- cursor pagination 返回稳定的 `next_cursor`。
- resource timeline 返回 newest-first 的有界 entries。

关键断言形状：

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

- [ ] **步骤 2：运行失败测试**

执行：

```bash
cd services/api && .venv/bin/pytest tests/test_admin_audit_service.py -q
```

实现前预期输出：

```text
ModuleNotFoundError: No module named 'app.services.admin_audit'
```

- [ ] **步骤 3：实现 audit service**

把 audit helper 从 `admin.py` 移到 `admin_audit.py`。

导出：

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

使用 `services/api/app/db/models.py` 里已有 DB model 与字段名，不新增 audit table。

- [ ] **步骤 4：更新 `/audit-events` route**

在 `admin.py` 中：

- 保持 `GET /audit-events` route path 和 query params。
- 用 query params 构造 `AdminAuditFilters`。
- 调用 `search_admin_audit_events`。
- 保持现有 read audit 的 risk/result 行为。
- 返回 Phase 2 已有 key。

- [ ] **步骤 5：增加 API resource timeline 断言**

在 `test_admin_phase2_api.py` 中扩展 audit endpoint 测试：

- 为同一 resource 创建两个 event，为另一个 resource 创建一个 event。
- 调用 `/v1/admin/audit-events?tenant_scope=all&resource_type=course_material&resource_id=<id>`。
- 断言只返回匹配 resource 的 event。

- [ ] **步骤 6：验证**

执行：

```bash
cd services/api && .venv/bin/pytest tests/test_admin_audit_service.py tests/test_admin_phase2_api.py -q
```

预期输出：

```text
passed
```

- [ ] **步骤 7：提交**

执行：

```bash
git status --short
git add services/api/app/services/admin_audit.py services/api/app/api/routes/admin.py services/api/tests/test_admin_audit_service.py services/api/tests/test_admin_phase2_api.py
git commit -m "refactor: extract admin audit service"
```

---

## 任务 4：抽取控制台与租户详情读模型

**文件：**
- 新增 `services/api/app/services/admin_read_models.py`
- 修改 `services/api/app/api/routes/admin.py`
- 新增 `services/api/tests/test_admin_read_models_service.py`
- 修改 `services/api/tests/test_admin_phase2_api.py`
- 修改 `services/api/tests/test_admin_read_api.py`

- [ ] **步骤 1：写 read-model 测试**

新增 `services/api/tests/test_admin_read_models_service.py`。

覆盖：

- dashboard payload 包含 tenants、materials、provider policies、module settings。
- tenant detail 包含 children、materials、weekly reports、speaking attempts、module settings、risk summary。
- tenant detail 遵守 tenant scope。
- latest lists 受现有常量限制。
- payload 使用与 Phase 2 route 相同的 key。

优先复用已有 route test setup helper，不复制大段 fixture construction。

- [ ] **步骤 2：运行失败测试**

执行：

```bash
cd services/api && .venv/bin/pytest tests/test_admin_read_models_service.py -q
```

实现前预期输出：

```text
ModuleNotFoundError: No module named 'app.services.admin_read_models'
```

- [ ] **步骤 3：实现 `admin_read_models.py`**

迁移 `admin.py` 里的 payload builder：

```python
def build_admin_dashboard(session: Session, tenant_scope: str) -> dict[str, Any]: ...
def build_admin_tenant_detail(session: Session, tenant_scope: str, tenant_id: str) -> dict[str, Any]: ...
def serialize_admin_tenant(...): ...
def serialize_admin_material(...): ...
def serialize_provider_policy(...): ...
def serialize_tenant_module_setting(...): ...
```

这些函数不能依赖 `Header`、`Depends` 或 route-specific `HTTPException`；no-disclosure 行为委托给 `admin_scope.py`。

- [ ] **步骤 4：迁移 route**

在 `admin.py` 中：

- `/dashboard` 调用 `build_admin_dashboard`。
- `/tenants/{tenant_id}` 调用 `build_admin_tenant_detail`。
- route 继续负责 read audit 与 permission enforcement。
- response key 和 casing 不变。

- [ ] **步骤 5：验证兼容性**

执行：

```bash
cd services/api && .venv/bin/pytest tests/test_admin_read_models_service.py tests/test_admin_phase2_api.py tests/test_admin_read_api.py -q
```

预期输出：

```text
passed
```

- [ ] **步骤 6：提交**

执行：

```bash
git status --short
git add services/api/app/services/admin_read_models.py services/api/app/api/routes/admin.py services/api/tests/test_admin_read_models_service.py services/api/tests/test_admin_phase2_api.py services/api/tests/test_admin_read_api.py
git commit -m "refactor: extract admin read models"
```

---

## 任务 5：抽取运维服务并增加问题合同

**文件：**
- 新增 `services/api/app/services/admin_operations.py`
- 修改 `services/api/app/api/routes/admin.py`
- 新增 `services/api/tests/test_admin_operations_service.py`
- 修改 `services/api/tests/test_admin_phase2_api.py`

- [ ] **步骤 1：写 operations service 测试**

新增 `services/api/tests/test_admin_operations_service.py`。

覆盖：

- 没有失败项时返回空 `issues`，并在现有 summary 支持时断言 `summary.severity == "ok"`。
- failed material parse job 产生 `critical` issue，且 `recommended_action == "retry_material_job"`。
- archived 或 ready material 不产生 retry issue。
- stale processing job 产生 `warning`，且 `source == "database_snapshot"`。
- real media 已启用的 provider policy 出现在 provider readiness。
- bounded latest lists 不超过现有 limit。

关键断言：

```python
payload = build_admin_operations(session, tenant_scope="all")

issue = next(item for item in payload["issues"] if item["related_resource"]["type"] == "material_parse_job")
assert issue["severity"] == "critical"
assert issue["recommended_action"] == "retry_material_job"
assert issue["required_permission"] == "admin.material.retry"
assert issue["related_resource"]["tenant_id"] == "tenant_alpha"
```

- [ ] **步骤 2：运行失败测试**

执行：

```bash
cd services/api && .venv/bin/pytest tests/test_admin_operations_service.py -q
```

实现前预期输出：

```text
ModuleNotFoundError: No module named 'app.services.admin_operations'
```

- [ ] **步骤 3：实现 operations service**

把 Phase 2 operations helper 从 `admin.py` 移到 `admin_operations.py`。

导出：

```python
IssueSeverity = Literal["ok", "info", "warning", "critical"]


def build_admin_operations(session: Session, tenant_scope: str) -> dict[str, Any]: ...
def build_operations_issues(session: Session, tenant_scope: str) -> list[dict[str, Any]]: ...
def classify_material_job_issue(...): ...
def classify_speaking_attempt_issue(...): ...
def build_provider_readiness(...): ...
```

每个 issue 必须包含：

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

不要伪装 worker 或 broker truth。所有从 DB 推导出来的 worker-facing status 都必须带 `source: "database_snapshot"`。

- [ ] **步骤 4：更新 `/operations` route**

在 `admin.py` 中：

- `/operations` 调用 `build_admin_operations`。
- 保留现有 Phase 2 top-level keys。
- 新增 `issues`。
- 保留 read audit。

- [ ] **步骤 5：增加 API contract 测试**

在 `test_admin_phase2_api.py` 中增加断言：

- `GET /v1/admin/operations?tenant_scope=all` 返回现有 key 和 `issues`。
- 每个 issue 都有 `id`、`severity`、`status_label`、`reason`、`recommended_action`、`related_resource`、`source`。
- action 可执行时存在 `required_permission`。
- tenant-scoped operations 只显示该 tenant 的 issue。

- [ ] **步骤 6：验证**

执行：

```bash
cd services/api && .venv/bin/pytest tests/test_admin_operations_service.py tests/test_admin_phase2_api.py -q
```

预期输出：

```text
passed
```

- [ ] **步骤 7：提交**

执行：

```bash
git status --short
git add services/api/app/services/admin_operations.py services/api/app/api/routes/admin.py services/api/tests/test_admin_operations_service.py services/api/tests/test_admin_phase2_api.py
git commit -m "feat: add admin operations issues contract"
```

---

## 任务 6：统一变更操作结果

**文件：**
- 新增 `services/api/app/services/admin_actions.py`
- 修改 `services/api/app/api/routes/admin.py`
- 修改 `services/api/tests/test_admin_phase2_api.py`

- [ ] **步骤 1：为 action result 写 API 测试**

在 `services/api/tests/test_admin_phase2_api.py` 中扩展现有 mutation 测试：

- material retry。
- material archive。
- provider policy override。
- tenant module toggle。
- impersonation end。

每个 mutation response 必须包含：

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

同一个测试里保留旧 resource key 断言，例如 `payload["material"]`、`payload["provider_policy"]`、`payload["module_setting"]`。

- [ ] **步骤 2：运行失败的 mutation 测试**

执行：

```bash
cd services/api && .venv/bin/pytest tests/test_admin_phase2_api.py -q
```

实现前预期输出：

```text
KeyError: 'action_result'
```

- [ ] **步骤 3：实现 `admin_actions.py`**

新增：

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

- [ ] **步骤 4：给 mutation route 增加 action result**

在 `admin.py` 中更新每个现有 mutation response：

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
  - already-ended 行为返回 `status: "noop"`，并且不覆盖原始 `ended_at`。

保留现有 top-level resource key 和 `audit_event` key。

- [ ] **步骤 5：验证**

执行：

```bash
cd services/api && .venv/bin/pytest tests/test_admin_phase2_api.py -q
```

预期输出：

```text
passed
```

- [ ] **步骤 6：提交**

执行：

```bash
git status --short
git add services/api/app/services/admin_actions.py services/api/app/api/routes/admin.py services/api/tests/test_admin_phase2_api.py
git commit -m "feat: standardize admin action results"
```

---

## 任务 7：增加后台 UI API 合同与测试数据

**文件：**
- 修改 `apps/admin/src/domain/types.ts`
- 修改 `apps/admin/src/domain/adminApi.ts`
- 修改 `apps/admin/src/domain/adminApi.test.ts`
- 修改 `apps/admin/src/domain/mockData.ts`

- [ ] **步骤 1：增加失败的 API client 测试**

在 `apps/admin/src/domain/adminApi.test.ts` 中增加测试：

- `loadAdminOperations()` 映射 `issues` 与现有 operations sections。
- `loadAdminTenantDetail()` 映射 nested tenant detail data。
- `loadAdminAuditEvents()` 透传 filters 并映射 `next_cursor`。
- `loadAdminImpersonationSessions()` 映射 sessions。
- `endAdminImpersonationSession()` 发送 `reason`，映射 `action_result` 并返回 `auditEvent`。

沿用现有测试风格 mock `global.fetch`。

- [ ] **步骤 2：运行失败的 UI 测试**

执行：

```bash
cd apps/admin && npm test -- adminApi.test.ts
```

实现前预期输出：

```text
ReferenceError or TypeError for missing exported API client
```

- [ ] **步骤 3：增加 TypeScript domain types**

在 `apps/admin/src/domain/types.ts` 中增加：

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

如果当前后端 response 已经足够稳定，可以把 `Record<string, unknown>` 细化为更严格的嵌套类型。

- [ ] **步骤 4：实现 API clients**

在 `apps/admin/src/domain/adminApi.ts` 中增加：

```ts
export async function loadAdminOperations(options: AdminApiOptions): Promise<AdminOperationsData> { ... }
export async function loadAdminTenantDetail(options: AdminTenantDetailOptions): Promise<AdminTenantDetailData> { ... }
export async function loadAdminAuditEvents(options: AdminAuditEventsOptions): Promise<AdminAuditEventsData> { ... }
export async function loadAdminImpersonationSessions(options: AdminApiOptions): Promise<AdminImpersonationSessionsData> { ... }
export async function endAdminImpersonationSession(options: EndAdminImpersonationSessionOptions): Promise<EndAdminImpersonationSessionResult> { ... }
```

继续沿用现有 `apiBaseUrl`、`adminToken`、`tenantScope` option pattern。增加 mapper helper：

```ts
function mapActionResult(payload: AdminActionResultPayload): AdminActionResult { ... }
function mapOperationsIssue(payload: AdminOperationsIssuePayload): AdminOperationsIssue { ... }
```

- [ ] **步骤 5：增加 fixtures**

在 `mockData.ts` 中导出：

- `mockOperationsData`。
- `mockTenantDetailData`。
- `mockAuditEventsPage`。
- `mockImpersonationSessions`。

fixture 不要复制 i18n 文案；中英文标签通过页面渲染和 `messages.ts` 处理。

- [ ] **步骤 6：验证**

执行：

```bash
cd apps/admin && npm test -- adminApi.test.ts
```

预期输出：

```text
passed
```

- [ ] **步骤 7：提交**

执行：

```bash
git status --short
git add apps/admin/src/domain/types.ts apps/admin/src/domain/adminApi.ts apps/admin/src/domain/adminApi.test.ts apps/admin/src/domain/mockData.ts
git commit -m "feat: add admin operations ui api contracts"
```

---

## 任务 8：把指挥中心接入运维读模型

**文件：**
- 修改 `apps/admin/src/App.tsx`
- 修改 `apps/admin/src/pages/CommandCenter.tsx`
- 修改 `apps/admin/src/pages/CommandCenter.test.tsx`
- 新增 `apps/admin/src/components/ActionDrawer.tsx`
- 新增 `apps/admin/src/components/ActionDrawer.test.tsx`
- 修改 `apps/admin/src/i18n/messages.ts`

- [ ] **步骤 1：写 page 与 drawer 测试**

增加测试证明：

- 传入 `operationsData` 时，Command Center 渲染后端 operations issue。
- severity 映射到现有 status color 或稳定 class name。
- 点击 issue 打开 `ActionDrawer`。
- unavailable action 展示 disabled execution control。
- action drawer 在没有 reason 时不会提交。
- 中文和英文文案都通过现有 i18n 渲染。

- [ ] **步骤 2：运行失败测试**

执行：

```bash
cd apps/admin && npm test -- CommandCenter.test.tsx ActionDrawer.test.tsx
```

实现前预期输出：

```text
failed
```

- [ ] **步骤 3：实现 `ActionDrawer`**

新增 `apps/admin/src/components/ActionDrawer.tsx`。

props：

- `language`。
- `issue`。
- `isOpen`。
- `isSubmitting`。
- `onClose`。
- `onSubmit(reason)`。

本地状态：

- `reason`。
- validation error。

渲染内容：

- issue severity/status/reason。
- related resource。
- recommended action。
- audit preview，包含 action/resource/risk 文案。
- reason textarea。
- submit/cancel buttons。

不要新增视觉主题；复用 `apps/admin/src/components/ui.tsx` 和现有 CSS token。

- [ ] **步骤 4：更新 Command Center**

在 `CommandCenter.tsx` 中：

- 接收 optional `operationsData`。
- 有 `operationsData.issues` 时用它渲染 issue table。
- 保留 dashboard-derived fallback，支持 mock 或 API failure mode。
- 用后端 `severity` 选择 status color。
- 用后端 `recommendedAction`，不要在 UI 本地猜 action。

- [ ] **步骤 5：在 `App.tsx` 中加载 operations**

在 `App.tsx` 中：

- import `loadAdminOperations`。
- 增加 `operationsData` state，初始值为 `mockOperationsData`。
- dashboard/access live load 成功后，用当前 `tenantScope` 调 operations endpoint。
- `tenantScope` 变化且 live API 已配置时重新加载 operations。
- 把 `operationsData` 传给 `CommandCenter`。

避免 effect 无限循环：dashboard/access bootstrap 用一个 effect，按 `tenantScope` 加载 operations 用另一个 effect。

- [ ] **步骤 6：验证**

执行：

```bash
cd apps/admin && npm test -- CommandCenter.test.tsx ActionDrawer.test.tsx
cd apps/admin && npm run build
```

预期输出：

```text
passed
vite build completes
```

- [ ] **步骤 7：提交**

执行：

```bash
git status --short
git add apps/admin/src/App.tsx apps/admin/src/pages/CommandCenter.tsx apps/admin/src/pages/CommandCenter.test.tsx apps/admin/src/components/ActionDrawer.tsx apps/admin/src/components/ActionDrawer.test.tsx apps/admin/src/i18n/messages.ts
git commit -m "feat: wire admin command center operations"
```

---

## 任务 9：接入租户详情、审计检索与代管会话

**文件：**
- 修改 `apps/admin/src/App.tsx`
- 修改 `apps/admin/src/pages/TenantDetail.tsx`
- 修改 `apps/admin/src/pages/TenantDetail.test.tsx`
- 修改 `apps/admin/src/pages/AuditAccess.tsx`
- 修改 `apps/admin/src/pages/AuditAccess.test.tsx`
- 修改 `apps/admin/src/i18n/messages.ts`

- [ ] **步骤 1：写失败的页面测试**

覆盖：

- Tenant Detail 在传入 API tenant detail 时渲染对应 sections。
- Tenant Detail 在 API detail 缺失时回退到 dashboard-derived data。
- Audit Explorer 支持 tenant、actor、action、resource type、resource id、risk、result filters。
- Audit Explorer pagination 使用 `nextCursor`。
- Impersonation sessions 列出 active 和 ended sessions。
- ending impersonation 必须输入 reason，并调用 API handler。
- already-ended `noop` result 展示出来，但不改变原始 end time。

- [ ] **步骤 2：运行失败测试**

执行：

```bash
cd apps/admin && npm test -- TenantDetail.test.tsx AuditAccess.test.tsx
```

实现前预期输出：

```text
failed
```

- [ ] **步骤 3：在 `App.tsx` 中加载 tenant detail**

在 `App.tsx` 中：

- import `loadAdminTenantDetail`。
- 增加 `tenantDetailData` state。
- 当 `activePage === "tenants"` 且存在 selected tenant 时，加载 `/v1/admin/tenants/{tenant_id}`。
- 把 `tenantDetailData` 传给 `TenantDetail`。
- selected tenant 变化时重置 detail state。

- [ ] **步骤 4：更新 Tenant Detail 页面**

在 `TenantDetail.tsx` 中：

- 优先使用后端 detail data 展示 children/materials/weekly reports/speaking attempts/module settings/risk summary。
- 保持现有 props 和 fallback 行为。
- 只有 `App` 或 page state 传入 audit data 时才展示嵌入式 audit timeline，不伪造 audit rows。

- [ ] **步骤 5：增加 Audit Explorer filters**

在 `AuditAccess.tsx` 中：

- 使用新的 `onLoadAuditEvents(filters)` prop。
- 用现有紧凑 admin 风格渲染 filter controls。
- `nextCursor` 存在时展示 cursor pagination controls。
- risk/result 映射到现有 status styles。

- [ ] **步骤 6：增加 impersonation list/end UI**

在 `AuditAccess.tsx` 中：

- 接收 `impersonationSessions`。
- 展示 active/ended/expired status。
- 保留现有 start impersonation flow。
- 增加 end flow，并要求 reason。
- 调用 `onEndImpersonationSession(sessionId, reason)`。
- 成功后展示 `actionResult.status` 和 `auditEvent`。

- [ ] **步骤 7：在 `App.tsx` 中接入 API handlers**

增加 live handlers：

- `loadAdminAuditEvents`。
- `loadAdminImpersonationSessions`。
- `endAdminImpersonationSession`。

end 成功后的 state 更新：

- 返回 session payload 时替换对应 session。
- 把返回的 audit event prepend 到 access/audit data。
- result 为 `noop` 且后端说明状态未变化时，保留原 session。

- [ ] **步骤 8：验证**

执行：

```bash
cd apps/admin && npm test -- TenantDetail.test.tsx AuditAccess.test.tsx
cd apps/admin && npm run build
```

预期输出：

```text
passed
vite build completes
```

- [ ] **步骤 9：提交**

执行：

```bash
git status --short
git add apps/admin/src/App.tsx apps/admin/src/pages/TenantDetail.tsx apps/admin/src/pages/TenantDetail.test.tsx apps/admin/src/pages/AuditAccess.tsx apps/admin/src/pages/AuditAccess.test.tsx apps/admin/src/i18n/messages.ts
git commit -m "feat: wire admin tenant audit impersonation views"
```

---

## 任务 10：文档与完整验证

**文件：**
- 修改 `services/api/README.md`
- 修改或新增 `apps/admin/README.md`
- 修改 `docs/harness/mvp-readiness-checklist.md`
- 修改 `docs/superpowers/specs/2026-05-31-admin-operations-platform-phase3-design.md`

- [ ] **步骤 1：更新后端文档**

在 `services/api/README.md` 中记录：

- Phase 3 service module 与职责。
- `/v1/admin/operations` 的 `issues` contract。
- mutation `action_result` contract。
- worker-facing health 的 `source="database_snapshot"` 限制。
- 验证命令：

```bash
make api-test
```

- [ ] **步骤 2：更新 Admin UI 文档**

如果 `apps/admin/README.md` 已存在，就修改它；如果不存在，就新建并记录：

- local environment variables：
  - `VITE_ADMIN_API_BASE_URL`。
  - `VITE_ADMIN_API_TOKEN`。
- live fallback 行为。
- Phase 3 已支持 screens：
  - Command Center operations。
  - Tenant Detail。
  - Audit Explorer。
  - Impersonation Sessions。
- 验证命令：

```bash
cd apps/admin && npm test
cd apps/admin && npm run build
```

- [ ] **步骤 3：更新 readiness checklist**

在 `docs/harness/mvp-readiness-checklist.md` 增加 Phase 3 admin evidence item：

- backend service tests。
- API compatibility。
- Admin UI test/build。
- 明确说明 SSO、DB-backed role mutation、worker broker introspection 仍不属于 Phase 3。

- [ ] **步骤 4：更新 spec 状态**

在 `docs/superpowers/specs/2026-05-31-admin-operations-platform-phase3-design.md` 底部增加 implementation status note，包含：

- 已实现 service modules。
- 已实现 UI pages。
- 已运行 verification commands。
- non-goals 中延后的 production items。

- [ ] **步骤 5：运行完整验证**

执行：

```bash
make api-test
cd apps/admin && npm test
cd apps/admin && npm run build
git diff --check
```

预期输出：

```text
make api-test completes successfully
vitest passes
vite build completes
git diff --check prints no output
```

如果 `services/api/.venv/bin/pytest` 或 `node_modules` 缺失，先运行仓库文档中的依赖安装命令。只有实际测试和 build 在当前工作树成功运行后，才可以标记验证完成。

- [ ] **步骤 6：提交**

执行：

```bash
git status --short
git add services/api/README.md apps/admin/README.md docs/harness/mvp-readiness-checklist.md docs/superpowers/specs/2026-05-31-admin-operations-platform-phase3-design.md
git commit -m "docs: document admin operations platform phase three"
```

---

## 最终复核清单

- [ ] `services/api/app/api/routes/admin.py` 明显瘦身，或本地 helper surface 明显减少。
- [ ] 没有重命名现有 `/v1/admin/...` route path。
- [ ] Phase 2 response keys 仍然存在。
- [ ] `/v1/admin/operations` 包含 `issues`。
- [ ] mutation response 包含 `required_permission`、`action_result`、`audit_event`。
- [ ] 每个 mutation 仍要求 reason、exact permission、tenant scope、audit write。
- [ ] no-disclosure 404 行为有测试覆盖。
- [ ] Admin UI 保留中文/英文语言切换。
- [ ] Admin UI 保留 LearningEnglish 温暖品牌识别与高密度运维表格风格。
- [ ] Admin UI 使用后端 severity/status 词汇，不在本地猜 issue 状态。
- [ ] 文档明确 SSO、DB-backed role mutation、真实 broker introspection 不属于 Phase 3。
- [ ] `make api-test` 通过。
- [ ] `cd apps/admin && npm test` 通过。
- [ ] `cd apps/admin && npm run build` 通过。
- [ ] `git diff --check` 通过。

## 建议执行顺序

1. 先做后端抽取：任务 1 到任务 4。
2. 再做 operations 与 action contract：任务 5 和任务 6。
3. 再做 Admin UI API contract：任务 7。
4. 再做 Admin UI screen wiring：任务 8 和任务 9。
5. 最后做文档与完整验证：任务 10。

这个顺序能让每次提交都保持可审查，同时避免 UI 绑定临时后端 shape。
