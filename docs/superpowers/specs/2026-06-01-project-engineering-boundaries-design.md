# LearningEnglish 工程边界优化设计

## 背景

当前仓库已经形成 monorepo 雏形：

- `apps/mobile` 是家长端 Flutter APP。
- `apps/admin` 是运维管理后台 Web。
- `services/api` 是 FastAPI 后端服务。
- `services/workers` 是 Celery 异步任务服务。
- `packages/contracts` 与 `packages/design_tokens` 是共享包。

这说明顶层方向基本正确，问题不在于是否要从零拆仓，而在于 `services/api/app` 内部仍然是平铺结构：家长端 API、运维管理 API、家长端业务编排、admin 业务编排、队列、provider、mapper 都直接放在 `api/routes` 或 `services` 下。随着 `/v1/admin/*` 已经进入生产级多租户后台方向，这种平铺结构会继续放大文件体积、import 依赖和认知成本。

## 目标

本阶段目标是让工程边界更贴近产品边界：

1. APP 保持独立目录：`apps/mobile`。
2. 运维管理后台前端保持独立目录：`apps/admin`。
3. 后端服务保持独立目录：`services/api`。
4. 异步任务服务保持独立目录：`services/workers`。
5. 在 `services/api/app` 内明确区分家长端和运维管理。
6. 保持现有外部 API 路径和客户端调用方式不变。

## 非目标

本阶段不做这些事情：

- 不把仓库拆成多个 git repo。
- 不把 FastAPI 拆成多个独立部署进程。
- 不修改 `/v1/*` 和 `/v1/admin/*` 的外部 URL。
- 不重写移动端或 admin 前端。
- 不在结构迁移同时重做权限模型、数据库模型或 provider 策略。
- 不一次性拆完所有大文件；大文件拆分要跟随测试和业务边界逐步完成。

## 推荐方案

采用“保留 monorepo，重组服务内部边界”的方案。

顶层结构保持：

```text
apps/
  mobile/
  admin/

services/
  api/
  workers/

packages/
  contracts/
  design_tokens/
```

`services/api/app` 目标结构：

```text
services/api/app/
  api/
    parent/
      __init__.py
      auth.py
      children.py
      materials.py
      material_jobs.py
      knowledge.py
      review_tasks.py
      practice_sessions.py
      speaking_attempts.py
      parent_coaching.py
      reports.py
    admin/
      __init__.py
      routes.py
    router.py
  services/
    parent/
      __init__.py
      auth.py
    admin/
      __init__.py
      actions.py
      audit.py
      identity.py
      operations.py
      permissions.py
      read_models.py
      scope.py
    shared/
      __init__.py
      job_queue.py
      learning_asset_media.py
      mappers.py
      media_queue.py
      media_reference.py
      pipeline.py
      speaking_assessment.py
      speaking_queue.py
      storage.py
  core/
  db/
  models/
  repositories/
  static/
```

第一轮迁移中，`api/admin/routes.py` 可以先承接当前 `api/routes/admin.py` 的完整内容。后续再按功能拆成 `dashboard.py`、`operations.py`、`audit.py`、`tenants.py`、`materials.py`、`providers.py` 和 `impersonation.py`。这样可以先建立边界，再控制拆分风险。

## 边界定义

### 家长端 API

家长端 API 是移动 APP 的后端接口，继续暴露原有路径：

- `/v1/auth/*`
- `/v1/me`
- `/v1/children`
- `/v1/materials`
- `/v1/material-jobs`
- `/v1/knowledge-packs`
- `/v1/review-tasks`
- `/v1/practice-sessions`
- `/v1/speaking-attempts`
- `/v1/parent-coaching`
- `/v1/reports`

家长端 API 只依赖 `Bearer` parent token，不依赖 `X-Admin-Token`。

### 运维管理 API

运维管理 API 是后台 Web 和运营工具的后端接口，继续暴露：

- `/v1/admin/dashboard`
- `/v1/admin/operations`
- `/v1/admin/access`
- `/v1/admin/audit-events`
- `/v1/admin/tenants/{tenant_id}`
- `/v1/admin/materials/{material_id}/archive`
- `/v1/admin/material-jobs/{job_id}/retry`
- `/v1/admin/providers/policies`
- `/v1/admin/tenants/{tenant_id}/modules/{module_key}`
- `/v1/admin/impersonation-sessions`
- `/v1/admin/impersonation-sessions/{session_id}/end`

运维管理 API 只接受 admin 身份与权限边界，不复用家长端 `Bearer` token。受监督代入继续保留为 admin 侧显式审计能力，不等于给 admin 直接签发家长端 token。

### 共享服务

`services/shared` 放置被家长端、admin、worker 共同使用的基础能力：

- provider pipeline
- storage
- queue enqueue helper
- mapper
- learning asset media
- speaking assessment
- media reference

共享服务不应该直接依赖 admin HTTP request，也不应该直接依赖家长端 UI 流程。它们提供可复用的领域能力，由 `parent` 或 `admin` 编排层调用。

## 路由聚合

`services/api/app/api/router.py` 保持唯一外部聚合入口：

```python
api_router = APIRouter(prefix="/v1")
api_router.include_router(parent_router)
api_router.include_router(admin_router)
```

`parent_router` 内部 include 家长端路由；`admin_router` 内部 include admin 路由。这样 URL 不变，但代码所有权边界变清楚。

## 迁移阶段

### 阶段 1：API route 分包

把 `services/api/app/api/routes/*.py` 拆到 `api/parent` 和 `api/admin`：

- 家长端文件移动到 `api/parent/`。
- `admin.py` 移动到 `api/admin/routes.py`。
- 更新 `api/router.py` import。
- 保留 endpoint path、response model 和 status code 不变。

阶段 1 完成后，`make api-test` 必须通过。

### 阶段 2：service 分包并保留兼容

把 admin service 移动到 `services/admin/`：

- `admin_actions.py` -> `admin/actions.py`
- `admin_audit.py` -> `admin/audit.py`
- `admin_identity.py` -> `admin/identity.py`
- `admin_operations.py` -> `admin/operations.py`
- `admin_permissions.py` -> `admin/permissions.py`
- `admin_read_models.py` -> `admin/read_models.py`
- `admin_scope.py` -> `admin/scope.py`

把共享能力移动到 `services/shared/`，但需要同步更新 worker 和测试 import。若一次性更新风险较高，可以先留下旧路径兼容 re-export，完成所有调用点迁移后再删除旧文件。

阶段 2 完成后，`make api-test` 和 `make worker-test` 必须通过。

### 阶段 3：拆 admin 大文件

在边界稳定后，再拆 `api/admin/routes.py`：

- `dashboard.py`
- `operations.py`
- `audit.py`
- `tenants.py`
- `materials.py`
- `providers.py`
- `impersonation.py`

拆分时以 endpoint group 为单位，每次迁移后运行 admin API 相关测试，避免在同一次变更里同时移动文件、改权限、改返回结构。

### 阶段 4：文档与验证入口同步

更新这些文档：

- `README.md`
- `docs/architecture/overview.md`
- `docs/architecture/backend-architecture.md`
- `docs/project/2026-05-31-status-and-todo.md` 或后续新的状态文档

文档要明确：

- 顶层目录边界。
- 家长端 API 与运维管理 API 的身份边界。
- worker 与 API 的共享依赖边界。
- 迁移后的验证命令。

## 测试与验收

结构迁移的最低验收门：

```bash
make api-test
make worker-test
make admin-test
make admin-build
git diff --check
```

如果只完成阶段 1，可以先不跑 admin build，但正式合并完整工程边界迁移前必须跑完上述命令。

额外检查：

```bash
rg "app.api.routes" services/api services/workers
rg "app.services.admin_" services/api services/workers
```

目标是迁移完成后不再有旧平铺路径依赖。

## 风险与控制

### 风险：移动文件导致大量 import 断裂

控制方式：

- 优先迁移 route 分包，service 分包放第二阶段。
- service 分包可以先保留兼容 re-export。
- 每一阶段单独跑测试。

### 风险：admin 大文件拆分时混入行为变更

控制方式：

- 第一轮只移动，不改行为。
- 大文件拆分按 endpoint group 做。
- 权限、审计、返回结构不在同一 PR 中重写。

### 风险：worker 与 API 共享服务边界混乱

控制方式：

- worker 只依赖 `services/shared` 和稳定领域模型。
- worker 不依赖 `api/parent` 或 `api/admin`。
- shared 服务不读取 HTTP request，也不处理 admin token。

## 成功标准

设计完成后的实现成功标准是：

1. `apps/mobile`、`apps/admin`、`services/api`、`services/workers` 的顶层职责在 README 和架构文档中清楚可见。
2. `services/api/app/api` 中能直接看出 `parent` 和 `admin` 两个入口。
3. `services/api/app/services` 中能直接看出 `parent`、`admin` 和 `shared` 三类服务。
4. 外部 API URL 不变。
5. 家长端 token 与 admin token 的身份边界不被混用。
6. worker 不依赖 HTTP route 包。
7. 迁移后验证命令通过。

## 下一步

本设计通过后，进入 implementation plan。计划应按阶段拆任务，先做 route 分包，再做 service 分包，最后拆 admin 大文件与同步文档。
