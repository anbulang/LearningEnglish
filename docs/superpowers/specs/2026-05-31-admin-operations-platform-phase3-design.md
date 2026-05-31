# Admin Operations Platform Phase 3 设计

## 背景

Admin 后端 Phase 2 已合入主线，当前能力包括配置化 `ADMIN_API_CREDENTIALS_JSON`、独立 audit search、tenant detail、operations snapshot、impersonation session list/end。后端已经能支撑生产级多租户 admin 的基础读模型和受控 mutation。

下一阶段不应继续把逻辑堆进 `services/api/app/api/routes/admin.py`。当前 `admin.py` 已超过 2200 行，`test_admin_phase2_api.py` 也接近 1900 行；继续追加接口会让权限、tenant scope、audit、operations 聚合和 UI payload 形状更难审查。Phase 3 的目标是把 Admin 后端推进到可维护的平台层，并让 Admin UI 开始消费这些稳定合同。

## 目标

1. 把 admin identity、permissions、audit、tenant scope、read models、operations health 拆成明确服务层。
2. 保持现有 `/v1/admin/...` URL 和 Phase 2 payload 兼容。
3. 定义稳定 operations platform 合同，让 Admin UI 不直接猜数据库状态枚举。
4. 增加 issue drilldown、recommended action、resource timeline 的后端形状，为后续运维处置闭环做准备。
5. 让 `apps/admin` 逐步接入 Phase 2/3 read models：operations、tenant detail、audit explorer、impersonation sessions。
6. 用服务层测试、API 兼容测试和 Admin UI fixture/live 测试证明迁移没有行为回退。

## 非目标

- 不实现完整 SSO、OAuth、magic link 或管理员登录 UI。
- 不实现复杂 DB-backed role/permission mutation 页面。
- 不实现完整 Celery broker 控制台或 worker 远程控制。
- 不把 `learning_assets` JSON 拆成独立表。
- 不重做 Admin UI 视觉主题；继续沿用现有温暖品牌识别和高密度运维表格风格。
- 不改变移动端业务 API。

## 方案选择

### 方案 A：运维工作流纵切

从 Admin UI 的真实操作路径倒推后端：`Operations Center -> 异常 drilldown -> 处置动作 -> audit 追踪`。优点是最快形成可用后台闭环；缺点是 `admin.py` 仍可能承受过多平台逻辑。

### 方案 B：后端平台化优先（本阶段采用）

先把 admin 后端拆出服务层，稳定 identity、permissions、scope、audit、read model 和 operations health 边界，再让 UI 接入这些稳定合同。优点是能降低 Phase 4/5 的维护成本，避免 UI 绑定临时 payload；缺点是第一批工作更偏架构治理，短期页面变化会比方案 A 慢。

### 方案 C：UI 接入优先

先把现有 Phase 2 read models 接入 Admin UI，后端只修最小缺口。优点是很快能看到页面；缺点是后端平台边界不清晰，UI 可能被大而临时的 payload 绑住。

选择方案 B。Phase 3 先让后端具备平台层，再通过小步 UI 接入验证这些合同可用。

## 后端架构

Phase 3 先拆服务层，不拆 FastAPI route 目录。`services/api/app/api/routes/admin.py` 继续注册现有 route，但 route 只负责 HTTP glue：依赖注入、输入参数、调用服务、返回 dict。

### `app/services/admin_identity.py`

职责：

- `AdminActor` 和 `AdminCredential` 数据结构。
- `ADMIN_API_CREDENTIALS_JSON` 解析。
- `ADMIN_API_TOKEN` 本地 fallback。
- SHA-256 token hash 与 constant-time compare。
- inactive credential 拒绝。

对外接口示例：

- `resolve_admin_actor(settings, raw_token) -> AdminActor | None`
- `admin_token_hash(raw_token) -> str`

### `app/services/admin_permissions.py`

职责：

- `ADMIN_PERMISSIONS` 权限常量。
- permission name 集中定义。
- `require_permission(actor, permission)`。
- `require_any_permission(actor, permissions)`。
- 统一 `403 Missing <permission>` 文案。

避免 route 和测试继续散落硬编码 permission string。

### `app/services/admin_scope.py`

职责：

- tenant scope 验证。
- no-disclosure 404 规则。
- `tenant_scope=all` 与单 tenant filter 生成。
- impersonation session scope filter。
- provider policy / module setting / child profile / audit scope filter。

目标是所有 admin endpoint 都通过同一层处理 scope，避免某些接口泄露 “tenant exists but out of scope”。

### `app/services/admin_audit.py`

职责：

- audit event 写入。
- audit search filters。
- cursor pagination。
- resource timeline 查询。
- audit payload 序列化。

Phase 3 增强：

- 保留 `/v1/admin/audit-events` 合同。
- 增加资源维度 timeline 查询约定，例如 `resource_type` + `resource_id`。
- 所有 mutation action result 都带本次 `audit_event`。

### `app/services/admin_read_models.py`

职责：

- dashboard payload builder。
- tenant detail payload builder。
- operations snapshot read model 中不属于 action 的聚合部分。
- provider/module/material/speaking/weekly report payload 复用函数。

约束：

- 不做 HTTP exception。
- 不读取 header。
- 输入是 `Session`、actor、tenant scope 或 resource id。
- 输出是稳定 dict 或内部 typed structure，再由 route 返回。

### `app/services/admin_operations.py`

职责：

- operations health。
- issue severity。
- recommended action。
- bounded latest lists。
- provider readiness。
- stale material job / speaking attempt 检测。
- 后续 remediation action contract 的服务边界。

Phase 3 的核心是让 UI 消费 backend-provided operations vocabulary：

- `severity`: `ok | info | warning | critical`
- `status_label`: 面向 UI 的稳定短标签。
- `reason`: 为什么这个 issue 存在。
- `recommended_action`: 后端建议动作 key。
- `related_resource`: 可以 drilldown 的资源引用。
- `required_permission`: 如果推荐动作需要权限，在 read model 中说明。

## 工作流与 API 合同

### 1. Operations Health

入口：`GET /v1/admin/operations?tenant_scope=all`

保持 Phase 2 key 兼容，同时增强 issue section：

```json
{
  "summary": {},
  "material_parse_jobs": {},
  "media_generation": {},
  "speaking_attempts": {},
  "provider_configuration": {},
  "module_toggle_coverage": {},
  "issues": [
    {
      "id": "issue_material_job_failed_job_123",
      "severity": "critical",
      "status_label": "Parse failed",
      "reason": "OCR provider timeout",
      "recommended_action": "retry_material_job",
      "required_permission": "admin.material.retry",
      "related_resource": {
        "type": "material_parse_job",
        "id": "job_123",
        "tenant_id": "tenant_123"
      }
    }
  ],
  "audit_event": {}
}
```

不做 broker introspection。`worker_health` 可以先返回数据库推导出的 worker-facing health，例如 stale processing count、oldest processing age、last successful job time；如果无法可靠判断，明确返回 `source="database_snapshot"`。

### 2. Issue Drilldown

入口可以先复用现有资源 read model，不急着新增统一 `/issues/{id}`。Phase 3 先定义 issue payload 中的 `related_resource`，UI 根据 resource type 跳转：

- `tenant` -> tenant detail。
- `material_parse_job` -> material/job detail drawer。
- `course_material` -> material drawer。
- `speaking_attempt` -> speaking attempt drawer。
- `admin_impersonation_session` -> impersonation sessions。

如果实现时发现 UI 需要一跳拿齐上下文，再新增：

```http
GET /v1/admin/issues/{issue_id}?tenant_scope=all
```

但第一版不强制新增，避免过早引入 issue storage。

### 3. Remediation Action

Phase 3 不需要一次实现所有 action，但要统一 action result 合同。所有 mutation 都必须：

- 要求 `reason`。
- 校验 exact permission。
- 校验 tenant scope。
- 使用 no-disclosure 404。
- 写 audit event。
- 返回稳定 `action_result`。

统一返回形状：

```json
{
  "required_permission": "admin.material.retry",
  "action_result": {
    "action": "retry_material_job",
    "status": "success",
    "resource_type": "material_parse_job",
    "resource_id": "job_123",
    "tenant_id": "tenant_123",
    "message": "Material parse job queued for retry."
  },
  "resource": {},
  "audit_event": {}
}
```

Phase 3 可以纳入的首批 action：

- existing `admin.material.retry` 标准化为 action result。
- existing `admin.material.archive` 标准化为 action result。
- existing `admin.provider.override` 标准化为 action result。
- existing `admin.tenant.module.toggle` 标准化为 action result。
- existing `admin.impersonation.end` 标准化为 action result。
- 新增 `admin.media.retry` 和 `admin.speaking.retry` 仅在后端已有可靠 retry 入口时实施；否则只在 operations issue 中返回 recommended action，但 UI 显示为不可执行。

### 4. Audit Trail

入口：继续使用 `/v1/admin/audit-events`。

增强：

- 明确支持 `resource_type` + `resource_id` 查询资源 timeline。
- UI 的 tenant detail、issue drawer、impersonation session detail 都可内嵌 recent audit。
- 所有 read audit 和 mutation audit 继续区分 `risk_level` 与 `result`。

## Admin UI 接入策略

UI 不重做主题，采用逐页替换数据源。

### Command Center / Operations

- 接入 enhanced operations read model。
- 展示 provider health、worker/job health、失败队列、stale items、recommended actions。
- issue row 点击打开 action drawer。
- read model 中的 `severity` 决定状态颜色。

### Tenant Detail

- dashboard tenant row 进入 tenant detail。
- 接入 `GET /v1/admin/tenants/{tenant_id}`。
- 展示 children、materials、weekly reports、speaking attempts、risk summary、module settings。
- 内嵌 audit timeline 时必须检查 actor 是否有 `admin.audit.read`。

### Audit Explorer

- 接入 `/v1/admin/audit-events`。
- filter：tenant、actor、action、resource type、resource id、risk、result。
- 支持 cursor pagination。
- 使用表格密度和状态颜色，不做营销页式布局。

### Impersonation Sessions

- 接入 list/end。
- start 保持已有入口。
- active/ended 分段或 filter。
- end action 必须输入 reason。
- already ended session 显示 noop audit result，不覆盖原 `ended_at`。

### Issue Drawer / Action Drawer

- 从 operations issue、tenant risk、audit resource 进入。
- 展示 issue context、recommended action、recent audit。
- 所有 action 都要求 reason。
- 提交前展示将写入 audit 的 action、resource、risk level。

## 迁移策略

1. 新增服务层文件和服务层测试，不改变 route 行为。
2. 逐个 route 迁移到服务层，保持 `/v1/admin/...` URL 和 payload key 兼容。
3. 对 operations payload 增量增加 `issues`，不删除 Phase 2 key。
4. 标准化 action result，保留旧 key 直到 UI 完成迁移。
5. Admin UI 逐页接入 enhanced read models。
6. 文档更新后再考虑拆 `admin.py` route 文件本身。

## 测试策略

### 后端服务层测试

- `test_admin_identity.py`：credential JSON、token hash、inactive、fallback local token、invalid JSON。
- `test_admin_permissions.py`：single permission、any permission、missing permission detail。
- `test_admin_scope.py`：tenant scope、all scope、no-disclosure。
- `test_admin_audit_service.py`：filters、cursor、resource timeline。
- `test_admin_read_models.py`：tenant detail 和 operations payload 稳定性。
- `test_admin_operations_service.py`：severity、recommended action、bounded lists、provider readiness。

### API 兼容测试

- 保留 Phase 2 integration tests。
- 现有 `/v1/admin/dashboard`、`/access`、`/audit-events`、`/tenants/{tenant_id}`、`/operations`、`/impersonation-sessions` 行为不变。
- 新增 contract tests 防止 key 漂移。
- 每个 mutation action result 都断言 `required_permission`、`action_result`、`audit_event`。

### Admin UI 测试

- `apps/admin` 增加 Phase 2/3 fixture。
- 覆盖 operations page、tenant detail、audit explorer、impersonation sessions。
- action drawer 覆盖 reason required、permission error、success audit display。
- live dev path 保持 `VITE_ADMIN_API_BASE_URL` + `VITE_ADMIN_API_TOKEN`。

### 验证命令

后端：

```bash
make api-test
git diff --check
```

Admin UI：

```bash
cd apps/admin && npm test
cd apps/admin && npm run build
```

## 验收标准

1. `services/api/app/api/routes/admin.py` 明显瘦身，route 只负责 HTTP glue。
2. Admin Phase 2 API 合同保持兼容，所有旧测试继续通过。
3. 新服务层有直接测试，核心权限、scope、audit、operations 逻辑不只靠 route integration test 覆盖。
4. `/v1/admin/operations` 返回可供 UI 直接消费的 `issues`、`severity`、`recommended_action` 和 `related_resource`。
5. 至少 Command Center / Operations 与 Audit Explorer 接入新 read model；Tenant Detail 和 Impersonation Sessions 可以按计划分批，但 fixture 和 API client 合同要先落地。
6. 所有 mutation 仍要求 reason、permission、tenant scope 和 audit event。
7. 文档明确哪些 action 可执行，哪些只是 recommended but unavailable。

## 风险与处理

- **重构引入行为回退**：先写服务层测试，再逐 route 迁移；每次迁移跑 admin focused tests。
- **服务层过度抽象**：只抽 Phase 2 已经存在的重复边界，不做通用 admin framework。
- **UI 绑定临时字段**：后端新增字段必须有 contract tests；UI 只消费稳定字段。
- **operations issue 没有可靠来源**：用 `source` 标识来源，例如 `database_snapshot`，不伪装成 broker truth。
- **action result 双合同过渡期复杂**：旧 key 保留到 UI 迁移完成，新增 `action_result` 作为统一合同。

## 后续阶段

Phase 3 完成后，后续可以选择：

1. Admin auth production：DB-backed token、rotation、role mutation、SSO/magic link。
2. Worker control plane：真实 worker heartbeat、queue depth、broker introspection。
3. Admin UI production hardening：URL state、saved filters、bulk actions、audit export。
4. Data model evolution：把 learning assets 拆成独立表，降低 JSON 聚合复杂度。
