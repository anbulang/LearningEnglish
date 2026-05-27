# Admin 后端生产化二期设计

## 背景

PR #7 已把后台从 OpenAPI 占位推进到 bilingual、多租户 admin 原型，并补齐了第一批真实 admin API：dashboard、access、material archive/retry、provider policy override、tenant module toggle、supervised impersonation start 和 audit event。当前后端已经能支撑 Phase 1 页面跑 live mode，但仍偏“受控本地运维工具”：

- `require_admin_token()` 只根据一个 token 返回固定 `admin_local` actor。
- `AdminUserModel` 会被 `_ensure_admin_user()` 写入，但 admin 身份、角色、权限并没有真正来自配置或数据。
- audit 只能通过 `/v1/admin/access` 顺带返回最近 50 条，缺少过滤、分页和独立查询合同。
- 队列与 provider 运维状态需要从 dashboard 的 material row、worker log、speaking attempt、learning asset JSON 中人工拼接。
- impersonation 只有 start，没有 end / expire 查询，也不能形成完整支持会话生命周期。

Admin Phase 2 的目标是把这些“能 demo”能力推进到生产后台服务的最小后端基础：明确身份边界、可审计、可筛选、可定位租户问题、可判断队列和 provider 健康。

## 目标

1. admin token 解析出真实 actor、角色、状态和权限，不再把所有请求都视为 `admin_local`。
2. 高风险 admin mutation 继续要求 reason，并统一写入 audit event；audit 可以独立查询、过滤和分页。
3. 增加租户详情后端合同，让后台能查看单个 tenant/parent 的 children、materials、provider policy、module settings、reports 和近期风险。
4. 增加 operations 后端合同，把 material jobs、learning asset media、speaking attempts 和 provider config 汇总成可扫描的运维健康视图。
5. 补全 supervised impersonation lifecycle：支持查询 active sessions 和手动 end，并记录 audit。
6. 保持现有 Admin Phase 1 UI 和 API 客户端兼容；新合同可以逐步接入 UI。

## 非目标

- 不实现完整 SSO、OAuth、magic link 或管理员登录 UI。
- 不接入外部 secrets manager；Phase 2 只做 token hash / config-driven actor 边界。
- 不实现真实 Celery worker heartbeat 或 broker introspection；operations 先从数据库状态和配置摘要推导。
- 不给 support 返回家长 access token；impersonation session 仍只是受监督支持会话记录。
- 不拆分 `learning_assets` JSON 成独立表；这属于后续数据模型演进。

## 方案选择

### 方案 A：配置驱动 admin credentials + 后端读模型扩展（推荐）

在 `Settings` 中增加 `ADMIN_API_CREDENTIALS_JSON`，每个 credential 包含 `id`、`display_name`、`email`、`role`、`status`、`permissions`、`token_sha256`。`ADMIN_API_TOKEN` 继续作为本地/测试的单 actor 显式配置 fallback，但生产建议使用 JSON credentials。API 侧用 SHA-256 constant-time compare 解析 actor，并把 actor upsert 到 `AdminUserModel`。

优点：不需要引入登录 UI，也能解决固定 actor 和权限边界问题；测试稳定；部署成本低。缺点：token 轮换仍依赖配置发布，不是最终账号系统。

### 方案 B：数据库 admin users + admin token table

新增 `AdminApiTokenModel`，token hash、状态、权限都在 DB；通过 migration 或管理脚本创建 token。

优点：更接近生产系统，支持运行时停用 token。缺点：需要 bootstrapping 管理脚本和更复杂的密钥生命周期，超出当前后台二期最小目标。

### 方案 C：直接上登录系统

做管理员登录、session、refresh token、角色管理页面。

优点：最终形态更完整。缺点：范围过大，会把 Phase 2 从后端运维基础拖成独立 IAM 项目。

选择方案 A。它能在最小改动内把 Phase 1 的“固定本地管理员”升级成“可配置、多角色、可审计”的后端边界，同时为以后迁移到数据库 token 或 SSO 留出接口。

## 后端合同

### Admin actor resolution

请求仍支持：

```http
X-Admin-Token: <raw-token>
```

解析顺序：

1. 如果 `ADMIN_API_CREDENTIALS_JSON` 存在，遍历 credentials，用 `sha256(raw-token)` 与 `token_sha256` constant-time compare。
2. 如果 JSON 未配置且 `ADMIN_API_TOKEN` 显式存在，返回本地 actor：
   - `id=admin_local`
   - `display_name=Local Platform Admin`
   - `role=Platform Owner`
   - `permissions=ADMIN_PERMISSIONS`
3. 如果没有任何 admin credential，返回 `503 Admin API token is not configured`。
4. credential `status != active` 返回 `403 Admin user is inactive`。

Credential JSON 形态：

```json
[
  {
    "id": "admin_ops",
    "display_name": "Ops Admin",
    "email": "ops@example.com",
    "role": "Operations",
    "status": "active",
    "permissions": ["admin.dashboard.read", "admin.audit.read"],
    "token_sha256": "64-char-lowercase-sha256"
  }
]
```

### Audit query

新增：

```http
GET /v1/admin/audit-events?tenant_scope=all&action=&resource_type=&risk_level=&result=&actor_id=&limit=50&cursor=
```

返回：

```json
{
  "items": [
    {
      "id": "audit_...",
      "actor_id": "admin_ops",
      "actor_role": "Operations",
      "tenant_scope": "tenant_...",
      "action": "admin.material_job.retry",
      "resource_type": "material_parse_job",
      "resource_id": "job_...",
      "risk_level": "high",
      "result": "success",
      "reason": "OCR provider recovered.",
      "trace_id": "req_...",
      "created_at": "2026-05-28T..."
    }
  ],
  "next_cursor": "audit_..."
}
```

Rules:

- Requires `admin.audit.read`.
- `tenant_scope != all` only returns `tenant_scope in ["all", selected_tenant]`.
- `limit` is clamped to 1..100.
- `cursor` is the last seen audit id; pagination orders by `created_at desc, id desc`.

### Tenant detail

新增：

```http
GET /v1/admin/tenants/{tenant_id}?tenant_scope=all
```

返回：

```json
{
  "tenant": { "id": "parent_...", "name": "Family 0010", "status": "warning" },
  "children": [{ "id": "child_...", "name": "Mia", "age": 6 }],
  "materials": [{ "...": "same shape as dashboard material" }],
  "provider_policy": { "tenant_id": "parent_...", "ai_provider": "stub", "media_provider": "mock" },
  "module_settings": [{ "tenant_id": "parent_...", "module_key": "weekly_reports", "enabled": true }],
  "weekly_reports": [{ "child_id": "child_...", "completed_sessions": 2, "speaking_attempts": 1 }],
  "risk_summary": {
    "failed_materials": 1,
    "failed_jobs": 1,
    "media_failures": 2,
    "stale_processing_jobs": 0,
    "failed_speaking_attempts": 1
  }
}
```

Rules:

- Requires `admin.tenant.read`.
- `tenant_scope` must be `all` or match `tenant_id`.
- Uses the same material payload as dashboard to avoid divergent UI rules.

### Operations snapshot

新增：

```http
GET /v1/admin/operations?tenant_scope=all
```

返回：

```json
{
  "material_jobs": {
    "queued": 0,
    "processing": 2,
    "needs_review": 3,
    "ready": 10,
    "failed": 1,
    "stale_processing": 1,
    "oldest_processing_minutes": 42
  },
  "media_generation": {
    "pending": 4,
    "processing": 1,
    "ready": 38,
    "failed": 2
  },
  "speaking_attempts": {
    "recording_uploaded": 1,
    "transcribing": 0,
    "scored": 8,
    "failed": 1,
    "stale_transcribing": 0
  },
  "provider_config": {
    "ai_provider": "stub",
    "media_provider": "mock",
    "media_image_provider": "openai",
    "media_tts_provider": "openai",
    "speech_provider": "stub",
    "secrets_present": {
      "ark_api_key": false,
      "openai_api_key": false,
      "dashscope_api_key": false
    }
  }
}
```

Rules:

- Requires `admin.operations.read` or `admin.dashboard.read`. Phase 2 should add `admin.operations.read` to `ADMIN_PERMISSIONS`.
- No secret values are returned.
- `stale_processing` threshold defaults to 30 minutes and can be a helper constant.
- Media status is computed from learning asset fields:
  - `generated_image_status`
  - `tts_us_status`
  - `tts_uk_status`

### Impersonation lifecycle

新增：

```http
GET /v1/admin/impersonation-sessions?tenant_scope=all&status=active
POST /v1/admin/impersonation-sessions/{session_id}/end?tenant_scope=all
```

End request:

```json
{ "reason": "Support case finished." }
```

Rules:

- List requires `admin.impersonation.read`.
- End requires `admin.impersonation.end`.
- End only works for active sessions.
- End sets `status=ended`, `ended_at=now`, writes high-risk `admin.impersonation.end` audit event.
- Existing start endpoint remains unchanged except permissions should continue to be checked from actor credentials.

## Module boundaries

### `app/api/routes/admin.py`

Keep route definitions here for Phase 2, but split pure helpers into small functions inside the file before considering a module split. The file is already large, but Phase 2 can still stay scoped if helpers are explicit:

- `_resolve_admin_actor()`
- `_configured_admin_credentials()`
- `_admin_token_hash()`
- `_admin_tenant_detail_payload()`
- `_admin_operations_payload()`
- `_audit_events_query()`
- `_impersonation_session_scope_filter()`

If this file grows past a manageable point during implementation, the follow-up split should be:

- `app/api/routes/admin.py` for route registration
- `app/services/admin_identity.py` for actor resolution
- `app/services/admin_read_models.py` for dashboard/detail/operations payload builders

Do not split preemptively in the planning commit.

### `app/core/settings.py`

Add:

- `admin_api_credentials_json: str`
- `speech_provider: str` already exists in current branch; operations snapshot should use the existing setting rather than inventing a new one.

### `app/models/contracts.py`

Add Pydantic contracts only when the route payload becomes shared or tested by response model. Existing admin routes currently return dicts; Phase 2 can keep dict responses for consistency, but tests must assert exact payload keys.

### `services/api/tests/test_admin_read_api.py`

Continue using this file for admin read/mutation integration tests. Add targeted tests near related behavior:

- actor credential resolution
- audit query filters
- tenant detail
- operations snapshot
- impersonation list/end

If the file becomes difficult to scan, split new Phase 2 tests into `test_admin_phase2_api.py`.

## Error handling

- Missing admin token: `401 Missing admin token`
- Unknown token: `403 Invalid admin token`
- Inactive admin credential: `403 Admin user is inactive`
- No credential configured: `503 Admin API token is not configured`
- Missing permission: `403 Missing <permission>`
- Tenant outside selected scope: `404 Tenant not found`
- Audit cursor not found: return empty `items` with `next_cursor=""`, not a 500.
- End non-active impersonation session: `409 Impersonation session is not active`

## Testing strategy

Backend tests must be TDD-first:

1. Add failing tests for credential-driven actor and permission boundary.
2. Add failing tests for audit filtering/pagination.
3. Add failing tests for tenant detail scope and risk summary.
4. Add failing tests for operations snapshot.
5. Add failing tests for impersonation list/end lifecycle.
6. Implement minimal code to pass.
7. Run `make api-test`.

Worker tests are not required for this phase because operations snapshot reads database state and configuration, not Celery broker state.

## Acceptance criteria

- Two different admin tokens can produce different actor ids, roles and permission sets.
- A read-only admin cannot perform provider override, material retry/archive, module toggle, or impersonation mutation.
- `/v1/admin/audit-events` can filter by tenant, action, risk, result and actor, and paginates deterministically.
- `/v1/admin/tenants/{tenant_id}` returns scoped tenant detail and rejects cross-scope access.
- `/v1/admin/operations` summarizes material jobs, media generation, speaking attempts and provider config without leaking secrets.
- Impersonation sessions can be listed and ended; end writes audit.
- Existing Admin Phase 1 tests still pass.
- `make api-test` passes.

## Rollout notes

- Local development can keep `ADMIN_API_TOKEN=local-admin-token`.
- Production-like environments should use `ADMIN_API_CREDENTIALS_JSON` with token hashes.
- Do not print raw admin tokens or hash source values in logs, API responses, tests or docs examples.
- Admin UI can continue using `VITE_ADMIN_API_TOKEN`; Phase 2 only changes what the backend resolves from that token.
