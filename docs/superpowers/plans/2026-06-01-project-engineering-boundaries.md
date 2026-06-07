# Project Engineering Boundaries Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将当前 monorepo 的后端服务内部边界调整为 `parent`、`admin`、`shared` 三类包，同时保持 `apps/mobile`、`apps/admin`、`services/api`、`services/workers` 的顶层职责和现有外部 API URL 不变。

**Architecture:** 保留单仓和单个 FastAPI 服务进程；只重组 `services/api/app/api` 与 `services/api/app/services` 的 Python 包边界。第一轮不拆分 `api/admin/routes.py` 内部 endpoint group，先让家长端 API、运维管理 API、共享服务能力在目录层面清楚可见，并通过现有 API、worker、admin 前端测试证明行为未变。

**Tech Stack:** Python 3, FastAPI, SQLAlchemy, Pytest, Celery, React/Vite admin app, Makefile verification.

---

## Scope Check

本计划覆盖设计文档中的阶段 1、阶段 2 和阶段 4：

- `api/parent` 与 `api/admin` 路由分包。
- `services/parent`、`services/admin`、`services/shared` 服务分包。
- README 与架构文档同步。
- 验证命令与旧 import 清理检查。

设计文档中的“阶段 3：拆 admin 大文件”是独立子项目。它依赖本计划先建立 `api/admin/routes.py` 边界；本计划通过后，再单独写一个 focused plan，把 `api/admin/routes.py` 拆成 `dashboard.py`、`operations.py`、`audit.py`、`tenants.py`、`materials.py`、`providers.py`、`impersonation.py`。

## File Structure

### Create

- `services/api/app/api/parent/__init__.py`：聚合家长端 route。
- `services/api/app/api/admin/__init__.py`：聚合 admin route。
- `services/api/app/services/parent/__init__.py`：家长端 service 包。
- `services/api/app/services/admin/__init__.py`：admin service 包。
- `services/api/app/services/shared/__init__.py`：共享 service 包。
- `services/api/tests/test_engineering_boundaries.py`：结构边界与 OpenAPI 稳定性测试。

### Move

- `services/api/app/api/routes/auth.py` -> `services/api/app/api/parent/auth.py`
- `services/api/app/api/routes/children.py` -> `services/api/app/api/parent/children.py`
- `services/api/app/api/routes/knowledge.py` -> `services/api/app/api/parent/knowledge.py`
- `services/api/app/api/routes/material_jobs.py` -> `services/api/app/api/parent/material_jobs.py`
- `services/api/app/api/routes/materials.py` -> `services/api/app/api/parent/materials.py`
- `services/api/app/api/routes/parent_coaching.py` -> `services/api/app/api/parent/parent_coaching.py`
- `services/api/app/api/routes/practice_sessions.py` -> `services/api/app/api/parent/practice_sessions.py`
- `services/api/app/api/routes/reports.py` -> `services/api/app/api/parent/reports.py`
- `services/api/app/api/routes/review_tasks.py` -> `services/api/app/api/parent/review_tasks.py`
- `services/api/app/api/routes/speaking_attempts.py` -> `services/api/app/api/parent/speaking_attempts.py`
- `services/api/app/api/routes/admin.py` -> `services/api/app/api/admin/routes.py`
- `services/api/app/services/auth.py` -> `services/api/app/services/parent/auth.py`
- `services/api/app/services/admin_actions.py` -> `services/api/app/services/admin/actions.py`
- `services/api/app/services/admin_audit.py` -> `services/api/app/services/admin/audit.py`
- `services/api/app/services/admin_identity.py` -> `services/api/app/services/admin/identity.py`
- `services/api/app/services/admin_operations.py` -> `services/api/app/services/admin/operations.py`
- `services/api/app/services/admin_permissions.py` -> `services/api/app/services/admin/permissions.py`
- `services/api/app/services/admin_read_models.py` -> `services/api/app/services/admin/read_models.py`
- `services/api/app/services/admin_scope.py` -> `services/api/app/services/admin/scope.py`
- `services/api/app/services/job_queue.py` -> `services/api/app/services/shared/job_queue.py`
- `services/api/app/services/learning_asset_media.py` -> `services/api/app/services/shared/learning_asset_media.py`
- `services/api/app/services/mappers.py` -> `services/api/app/services/shared/mappers.py`
- `services/api/app/services/media_queue.py` -> `services/api/app/services/shared/media_queue.py`
- `services/api/app/services/media_reference.py` -> `services/api/app/services/shared/media_reference.py`
- `services/api/app/services/pipeline.py` -> `services/api/app/services/shared/pipeline.py`
- `services/api/app/services/speaking_assessment.py` -> `services/api/app/services/shared/speaking_assessment.py`
- `services/api/app/services/speaking_queue.py` -> `services/api/app/services/shared/speaking_queue.py`
- `services/api/app/services/storage.py` -> `services/api/app/services/shared/storage.py`

### Modify

- `services/api/app/api/router.py`：include `parent_router` 和 `admin_router`。
- `services/api/app/core/config.py`：更新 service import。
- `services/api/app/main.py`：更新 storage import。
- `services/api/app/api/parent/*.py`：更新 service import。
- `services/api/app/api/admin/routes.py`：更新 admin/shared service import。
- `services/api/app/services/admin/*.py`：更新 admin/shared service import。
- `services/api/app/services/shared/*.py`：更新 shared service import。
- `services/workers/workers_app/tasks.py`：更新 shared service import。
- `services/api/tests/*.py`：更新测试 import。
- `services/workers/tests/*.py`：更新测试 import。
- `README.md`：更新仓库地图描述。
- `docs/architecture/overview.md`：更新代码边界描述。
- `docs/architecture/backend-architecture.md`：更新后端服务边界描述。

---

### Task 1: Add Boundary Guard Tests

**Files:**
- Create: `services/api/tests/test_engineering_boundaries.py`

- [ ] **Step 1: Write the failing test**

Create `services/api/tests/test_engineering_boundaries.py` with this content:

```python
from __future__ import annotations

from pathlib import Path

from app.main import app


API_ROOT = Path(__file__).resolve().parents[1] / "app" / "api"
SERVICES_ROOT = Path(__file__).resolve().parents[1] / "app" / "services"


def test_api_routes_are_grouped_by_product_boundary() -> None:
    assert (API_ROOT / "parent").is_dir()
    assert (API_ROOT / "admin").is_dir()
    assert not (API_ROOT / "routes").exists()


def test_services_are_grouped_by_runtime_boundary() -> None:
    assert (SERVICES_ROOT / "parent").is_dir()
    assert (SERVICES_ROOT / "admin").is_dir()
    assert (SERVICES_ROOT / "shared").is_dir()
    assert not list(SERVICES_ROOT.glob("admin_*.py"))


def test_public_api_paths_stay_stable_after_package_split() -> None:
    openapi = app.openapi()
    paths = set(openapi["paths"])

    parent_paths = {
        "/v1/auth/wechat/login",
        "/v1/auth/phone/request-otp",
        "/v1/auth/phone/bind",
        "/v1/me",
        "/v1/children",
        "/v1/materials",
        "/v1/reports/weekly",
    }
    admin_paths = {
        "/v1/admin/dashboard",
        "/v1/admin/operations",
        "/v1/admin/access",
        "/v1/admin/audit-events",
        "/v1/admin/impersonation-sessions",
    }

    assert parent_paths.issubset(paths)
    assert admin_paths.issubset(paths)
```

- [ ] **Step 2: Run the focused test to verify it fails**

Run:

```bash
cd services/api
.venv/bin/pytest tests/test_engineering_boundaries.py -q
```

Expected:

```text
FAILED tests/test_engineering_boundaries.py::test_api_routes_are_grouped_by_product_boundary
FAILED tests/test_engineering_boundaries.py::test_services_are_grouped_by_runtime_boundary
```

The OpenAPI path test may pass before migration; the directory tests must fail before implementation.

- [ ] **Step 3: Commit the RED test**

```bash
git add services/api/tests/test_engineering_boundaries.py
git commit -m "test: cover backend engineering boundaries"
```

---

### Task 2: Split API Route Packages

**Files:**
- Create: `services/api/app/api/parent/__init__.py`
- Create: `services/api/app/api/admin/__init__.py`
- Modify: `services/api/app/api/router.py`
- Move: `services/api/app/api/routes/*.py`

- [ ] **Step 1: Move route files**

Run:

```bash
mkdir -p services/api/app/api/parent services/api/app/api/admin
git mv services/api/app/api/routes/auth.py services/api/app/api/parent/auth.py
git mv services/api/app/api/routes/children.py services/api/app/api/parent/children.py
git mv services/api/app/api/routes/knowledge.py services/api/app/api/parent/knowledge.py
git mv services/api/app/api/routes/material_jobs.py services/api/app/api/parent/material_jobs.py
git mv services/api/app/api/routes/materials.py services/api/app/api/parent/materials.py
git mv services/api/app/api/routes/parent_coaching.py services/api/app/api/parent/parent_coaching.py
git mv services/api/app/api/routes/practice_sessions.py services/api/app/api/parent/practice_sessions.py
git mv services/api/app/api/routes/reports.py services/api/app/api/parent/reports.py
git mv services/api/app/api/routes/review_tasks.py services/api/app/api/parent/review_tasks.py
git mv services/api/app/api/routes/speaking_attempts.py services/api/app/api/parent/speaking_attempts.py
git mv services/api/app/api/routes/admin.py services/api/app/api/admin/routes.py
git rm services/api/app/api/routes/__init__.py
```

- [ ] **Step 2: Add parent route aggregator**

Create `services/api/app/api/parent/__init__.py`:

```python
from fastapi import APIRouter

from app.api.parent.auth import me_router, router as auth_router
from app.api.parent.children import router as children_router
from app.api.parent.knowledge import router as knowledge_router
from app.api.parent.material_jobs import router as material_jobs_router
from app.api.parent.materials import router as materials_router
from app.api.parent.parent_coaching import router as parent_coaching_router
from app.api.parent.practice_sessions import router as practice_sessions_router
from app.api.parent.reports import router as reports_router
from app.api.parent.review_tasks import router as review_tasks_router
from app.api.parent.speaking_attempts import router as speaking_attempts_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(me_router)
router.include_router(children_router)
router.include_router(materials_router)
router.include_router(material_jobs_router)
router.include_router(knowledge_router)
router.include_router(review_tasks_router)
router.include_router(practice_sessions_router)
router.include_router(speaking_attempts_router)
router.include_router(parent_coaching_router)
router.include_router(reports_router)
```

- [ ] **Step 3: Add admin route aggregator**

Create `services/api/app/api/admin/__init__.py`:

```python
from app.api.admin.routes import router

__all__ = ["router"]
```

- [ ] **Step 4: Replace the top-level API router**

Replace `services/api/app/api/router.py` with:

```python
from fastapi import APIRouter

from app.api.admin import router as admin_router
from app.api.parent import router as parent_router

api_router = APIRouter(prefix="/v1")
api_router.include_router(parent_router)
api_router.include_router(admin_router)
```

- [ ] **Step 5: Update route import references in tests**

In `services/api/tests/test_admin_auth_config.py`, replace:

```python
from app.api.routes.admin import require_admin_token
```

with:

```python
from app.api.admin.routes import require_admin_token
```

In `services/api/tests/test_material_failures.py`, replace:

```python
from app.api.routes import material_jobs
```

with:

```python
from app.api.parent import material_jobs
```

- [ ] **Step 6: Verify old route imports are gone**

Run:

```bash
rg "app\.api\.routes" services/api services/workers
```

Expected:

```text
no matches
```

- [ ] **Step 7: Run route boundary tests**

Run:

```bash
cd services/api
.venv/bin/pytest tests/test_engineering_boundaries.py -q
```

Expected:

```text
1 failed, 2 passed
```

The remaining failure is `test_services_are_grouped_by_runtime_boundary`, which is implemented in Task 3.

- [ ] **Step 8: Run API smoke tests affected by router imports**

Run:

```bash
cd services/api
.venv/bin/pytest tests/test_admin_auth_config.py tests/test_main_chain_smoke.py tests/test_material_failures.py -q
```

Expected:

```text
all selected tests pass
```

- [ ] **Step 9: Commit route package split**

```bash
git add services/api/app/api services/api/tests/test_admin_auth_config.py services/api/tests/test_material_failures.py
git commit -m "refactor: split api routes by product boundary"
```

---

### Task 3: Split Service Packages

**Files:**
- Create: `services/api/app/services/parent/__init__.py`
- Create: `services/api/app/services/admin/__init__.py`
- Create: `services/api/app/services/shared/__init__.py`
- Move: `services/api/app/services/*.py`
- Modify: `services/api/app/core/config.py`
- Modify: `services/api/app/main.py`
- Modify: `services/api/app/api/parent/*.py`
- Modify: `services/api/app/api/admin/routes.py`
- Modify: `services/workers/workers_app/tasks.py`
- Modify: `services/api/tests/*.py`
- Modify: `services/workers/tests/*.py`

- [ ] **Step 1: Move service files**

Run:

```bash
mkdir -p services/api/app/services/parent services/api/app/services/admin services/api/app/services/shared
touch services/api/app/services/parent/__init__.py
touch services/api/app/services/admin/__init__.py
touch services/api/app/services/shared/__init__.py
git mv services/api/app/services/auth.py services/api/app/services/parent/auth.py
git mv services/api/app/services/admin_actions.py services/api/app/services/admin/actions.py
git mv services/api/app/services/admin_audit.py services/api/app/services/admin/audit.py
git mv services/api/app/services/admin_identity.py services/api/app/services/admin/identity.py
git mv services/api/app/services/admin_operations.py services/api/app/services/admin/operations.py
git mv services/api/app/services/admin_permissions.py services/api/app/services/admin/permissions.py
git mv services/api/app/services/admin_read_models.py services/api/app/services/admin/read_models.py
git mv services/api/app/services/admin_scope.py services/api/app/services/admin/scope.py
git mv services/api/app/services/job_queue.py services/api/app/services/shared/job_queue.py
git mv services/api/app/services/learning_asset_media.py services/api/app/services/shared/learning_asset_media.py
git mv services/api/app/services/mappers.py services/api/app/services/shared/mappers.py
git mv services/api/app/services/media_queue.py services/api/app/services/shared/media_queue.py
git mv services/api/app/services/media_reference.py services/api/app/services/shared/media_reference.py
git mv services/api/app/services/pipeline.py services/api/app/services/shared/pipeline.py
git mv services/api/app/services/speaking_assessment.py services/api/app/services/shared/speaking_assessment.py
git mv services/api/app/services/speaking_queue.py services/api/app/services/shared/speaking_queue.py
git mv services/api/app/services/storage.py services/api/app/services/shared/storage.py
```

- [ ] **Step 2: Apply import mapping**

Update imports according to this exact mapping:

```text
app.services.auth -> app.services.parent.auth
app.services.admin_actions -> app.services.admin.actions
app.services.admin_audit -> app.services.admin.audit
app.services.admin_identity -> app.services.admin.identity
app.services.admin_operations -> app.services.admin.operations
app.services.admin_permissions -> app.services.admin.permissions
app.services.admin_read_models -> app.services.admin.read_models
app.services.admin_scope -> app.services.admin.scope
app.services.job_queue -> app.services.shared.job_queue
app.services.learning_asset_media -> app.services.shared.learning_asset_media
app.services.mappers -> app.services.shared.mappers
app.services.media_queue -> app.services.shared.media_queue
app.services.media_reference -> app.services.shared.media_reference
app.services.pipeline -> app.services.shared.pipeline
app.services.speaking_assessment -> app.services.shared.speaking_assessment
app.services.speaking_queue -> app.services.shared.speaking_queue
app.services.storage -> app.services.shared.storage
```

Use `rg` before editing:

```bash
rg "app\.services\." services/api services/workers
```

Every matched import must be converted through the mapping above. Do not leave compatibility shim files at the old paths.

- [ ] **Step 3: Update known internal service imports**

Confirm these concrete replacements are present:

In `services/api/app/services/admin/operations.py`:

```python
from app.services.admin.permissions import ADMIN_MATERIAL_RETRY, ADMIN_OPERATIONS_READ
from app.services.admin.scope import ensure_tenant_in_scope
```

In `services/api/app/services/admin/read_models.py`:

```python
from app.services.admin.scope import get_tenant_or_404
```

In `services/api/app/services/admin/audit.py`:

```python
from app.services.admin.scope import audit_scope_filter
```

In `services/api/app/services/admin/identity.py`:

```python
from app.services.admin.permissions import ADMIN_PERMISSIONS
```

In `services/api/app/services/shared/media_reference.py`:

```python
from app.services.shared.storage import get_storage_service
```

In `services/api/app/services/shared/media_queue.py`:

```python
from app.services.shared.job_queue import _default_result_backend
```

In `services/api/app/services/shared/speaking_queue.py`:

```python
from app.services.shared.job_queue import _default_result_backend
```

- [ ] **Step 4: Update known route imports**

Confirm these concrete replacements are present:

In `services/api/app/api/parent/auth.py`:

```python
from app.services.parent.auth import AuthService
from app.services.shared.mappers import child_profile_from_model, parent_account_from_model
```

In `services/api/app/api/parent/materials.py`:

```python
from app.services.shared.job_queue import enqueue_material_job
from app.services.shared.mappers import course_material_from_model, material_job_from_model
```

In `services/api/app/api/parent/material_jobs.py`:

```python
from app.services.shared.job_queue import enqueue_material_job
from app.services.shared.media_queue import enqueue_learning_asset_media_job
from app.services.shared.mappers import course_material_from_model, material_job_from_model
from app.services.shared.pipeline import ProviderBackedPipelineService
```

In `services/api/app/api/parent/speaking_attempts.py`:

```python
from app.services.shared.mappers import speaking_attempt_from_model
from app.services.shared.speaking_queue import enqueue_speaking_attempt_job
```

In `services/api/app/api/admin/routes.py`:

```python
from app.services.admin.actions import build_action_result
from app.services.admin.audit import AdminAuditFilters, record_admin_audit_event as _record_audit_event, search_admin_audit_events, serialize_admin_audit_event as _audit_event_payload
from app.services.admin.identity import AdminActor, resolve_admin_actor
from app.services.admin.operations import build_admin_operations
from app.services.admin.permissions import ADMIN_AUDIT_READ, ADMIN_DASHBOARD_READ, ADMIN_IMPERSONATION_END, ADMIN_IMPERSONATION_READ, ADMIN_IMPERSONATION_START, ADMIN_MATERIAL_ARCHIVE, ADMIN_MATERIAL_RETRY, ADMIN_OPERATIONS_READ, ADMIN_PROVIDER_OVERRIDE, ADMIN_TENANT_MODULE_TOGGLE, ADMIN_TENANT_READ, has_permission, require_permission
from app.services.admin.read_models import build_admin_dashboard, build_admin_tenant_detail
from app.services.admin.scope import audit_scope_filter as _audit_scope_filter, ensure_admin_tenant_scope as _ensure_admin_tenant_scope, ensure_tenant_in_scope, impersonation_session_scope_filter as _impersonation_session_scope_filter
from app.services.shared.job_queue import enqueue_material_job
```

If line length gets unwieldy, format the imports with parentheses; preserve the same imported names.

- [ ] **Step 5: Update core, main, workers, and tests imports**

Confirm these replacements are present:

In `services/api/app/core/config.py`:

```python
from app.services.parent.auth import AuthService
from app.services.shared.pipeline import build_pipeline_service
from app.services.shared.storage import get_storage_service
```

In `services/api/app/main.py`:

```python
from app.services.shared.storage import get_storage_service
```

In `services/workers/workers_app/tasks.py`:

```python
from app.services.shared.learning_asset_media import MediaProviderConfigurationError, build_media_provider_bundle
from app.services.shared.mappers import course_material_from_model, material_job_from_model
from app.services.shared.pipeline import build_pipeline_service
from app.services.shared.speaking_assessment import SpeechAssessmentProviderConfigurationError, build_speech_assessment_provider_bundle
from app.services.shared.storage import get_storage_service
```

In `services/api/tests/test_admin_operations_service.py`:

```python
from app.services.admin.operations import build_admin_operations
```

In `services/api/tests/test_admin_read_models_service.py`:

```python
from app.services.admin.read_models import build_admin_dashboard, build_admin_tenant_detail
```

In `services/workers/tests/test_material_job_task.py`:

```python
from app.services.shared.learning_asset_media import GeneratedMedia, MediaProviderConfigurationError
```

- [ ] **Step 6: Verify old service imports are gone**

Run:

```bash
rg "app\.services\.admin_" services/api services/workers
rg "app\.services\.(auth|job_queue|learning_asset_media|mappers|media_queue|media_reference|pipeline|speaking_assessment|speaking_queue|storage)" services/api services/workers
```

Expected:

```text
no matches
```

If the second command matches `app.services.parent.*`, `app.services.admin.*`, or `app.services.shared.*`, refine the regex or inspect manually; the invalid forms are only the old flat paths.

- [ ] **Step 7: Run service boundary tests**

Run:

```bash
cd services/api
.venv/bin/pytest tests/test_engineering_boundaries.py -q
```

Expected:

```text
3 passed
```

- [ ] **Step 8: Run API and worker tests**

Run:

```bash
make api-test
make worker-test
```

Expected:

```text
all API tests pass
all worker tests pass
```

- [ ] **Step 9: Commit service package split**

```bash
git add services/api/app services/api/tests services/workers
git commit -m "refactor: split backend services by runtime boundary"
```

---

### Task 4: Update Architecture Documentation

**Files:**
- Modify: `README.md`
- Modify: `docs/architecture/overview.md`
- Modify: `docs/architecture/backend-architecture.md`

- [ ] **Step 1: Update README repository map**

In `README.md`, update the `仓库地图` entries for `apps/admin` and `services/api` to this wording:

```markdown
| [`apps/admin`](apps/admin) | React/Vite 多租户运维管理后台，可连接 `/v1/admin/*` live API |
| [`services/api`](services/api) | FastAPI 后端服务，内部按 `api/parent`、`api/admin`、`services/parent`、`services/admin`、`services/shared` 区分家长端、运维管理和共享能力 |
```

- [ ] **Step 2: Update overview code boundary section**

In `docs/architecture/overview.md`, replace the `代码边界` bullet list with:

```markdown
- `apps/mobile`：Flutter 家长端 APP，负责登录、资料库、上传、AI 校对、课程详情、复习、报告和个人页。
- `apps/admin`：React/Vite 多租户运维管理后台，面向 `/v1/admin/*` 的 dashboard、operations、audit、tenant 和受监督代入能力。
- `services/api`：FastAPI 后端服务，保持一个运行进程；内部通过 `api/parent`、`api/admin`、`services/parent`、`services/admin`、`services/shared` 区分家长端、运维管理和共享服务能力。
- `services/workers`：Celery worker，负责讲义识别、学习资产媒体生成、周报聚合和口语评分；只依赖共享服务能力和稳定领域模型，不依赖 HTTP route 包。
- `packages/contracts`：Dart 侧共享领域契约，和 API Pydantic models 对齐。
- `packages/design_tokens`：Flutter UI token。
- `scripts/harness`：MVP readiness、主链 smoke、provider smoke、iOS 模拟器辅助脚本。
```

- [ ] **Step 3: Update backend architecture service boundary section**

In `docs/architecture/backend-architecture.md`, replace `## 当前服务边界` with:

```markdown
## 当前服务边界

当前后端仍是一个 FastAPI 模块化单体，但代码边界按入口和运行责任分组：

- `api/parent`：家长端 HTTP API，继续暴露 `/v1/auth`、`/v1/materials`、`/v1/reports` 等原有路径，并使用 `Bearer` parent token。
- `api/admin`：运维管理 HTTP API，继续暴露 `/v1/admin/*`，并使用 admin 身份、权限和审计边界。
- `services/parent`：家长端业务编排，例如登录、验证码、token 刷新和家长资料读取。
- `services/admin`：运维管理业务编排，例如 admin identity、permission、scope、audit、operations read model 和 action result。
- `services/shared`：被 API 与 worker 共用的基础能力，例如 provider pipeline、storage、queue enqueue helper、mapper、learning asset media、speaking assessment。
- `db` / `models` / `core`：数据库模型、契约模型、settings、DB session 和安全基础能力。

外部路径保持兼容：家长端继续访问 `/v1/*`，运维管理继续访问 `/v1/admin/*`。
```

- [ ] **Step 4: Run documentation checks**

Run:

```bash
rg "app/api/routes|api/routes|services/admin_" README.md docs/architecture/overview.md docs/architecture/backend-architecture.md
git diff --check
```

Expected:

```text
no stale architecture references
no whitespace errors
```

- [ ] **Step 5: Commit documentation update**

```bash
git add README.md docs/architecture/overview.md docs/architecture/backend-architecture.md
git commit -m "docs: describe backend product boundaries"
```

---

### Task 5: Full Verification

**Files:**
- Verify working tree only; no expected source changes.

- [ ] **Step 1: Run API tests**

Run:

```bash
make api-test
```

Expected:

```text
all API tests pass
```

- [ ] **Step 2: Run worker tests**

Run:

```bash
make worker-test
```

Expected:

```text
all worker tests pass
```

- [ ] **Step 3: Run admin frontend tests**

Run:

```bash
make admin-test
```

Expected:

```text
all admin tests pass
```

- [ ] **Step 4: Run admin production build**

Run:

```bash
make admin-build
```

Expected:

```text
vite build succeeds
```

- [ ] **Step 5: Verify old flat imports and route package are gone**

Run:

```bash
test ! -d services/api/app/api/routes
rg "app\.api\.routes" services/api services/workers
rg "app\.services\.admin_" services/api services/workers
rg "app\.services\.(auth|job_queue|learning_asset_media|mappers|media_queue|media_reference|pipeline|speaking_assessment|speaking_queue|storage)" services/api services/workers
```

Expected:

```text
services/api/app/api/routes does not exist
no old route imports
no old admin service imports
no old shared service imports
```

If the last command matches new paths such as `app.services.shared.storage`, inspect the exact match before changing code. The invalid forms are the old flat paths listed in Task 3 Step 2.

- [ ] **Step 6: Verify git diff hygiene**

Run:

```bash
git diff --check
git status --short
```

Expected:

```text
no whitespace errors
working tree contains only intended uncommitted verification artifacts, or is clean after commits
```

- [ ] **Step 7: Push branch**

Run:

```bash
git push origin codex/admin-operations-platform-phase3
```

Expected:

```text
branch push succeeds
```

---

## Self-Review

Spec coverage:

- APP 单独目录：covered by documentation updates preserving `apps/mobile`.
- 运维后台前端单独目录：covered by documentation updates preserving `apps/admin`.
- 后端服务单独目录：covered by documentation updates preserving `services/api`.
- 服务内区分家长端和运维管理：covered by Tasks 1-3 with `api/parent`, `api/admin`, `services/parent`, `services/admin`, `services/shared`.
- 外部 API 路径不变：covered by `test_public_api_paths_stay_stable_after_package_split`.
- worker 不依赖 HTTP route 包：covered by old import checks and worker import migration.
- 设计阶段 3 admin 大文件拆分：identified as a separate sub-project after this boundary migration plan.

Placeholder scan:

- No placeholder markers, vague placeholder steps, or missing commands are intentionally present.

Type and path consistency:

- Route target package names use `app.api.parent` and `app.api.admin`.
- Service target package names use `app.services.parent`, `app.services.admin`, and `app.services.shared`.
- Validation commands align with the Makefile gates in the design spec.
