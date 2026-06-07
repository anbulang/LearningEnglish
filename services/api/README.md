# LearningEnglish API

FastAPI 服务，负责鉴权、讲义上传、AI 草稿、课程详情、复习任务、陪练脚本和周报等核心接口。

## 当前接口

### 鉴权

- `POST /v1/auth/wechat/login`
- `POST /v1/auth/phone/request-otp`
- `POST /v1/auth/phone/bind`
- `POST /v1/auth/refresh`
- `POST /v1/auth/logout`
- `GET /v1/auth/me`
- `GET /v1/me`

### 业务接口

- `GET /v1/admin/dashboard?tenant_scope=all`
- `GET /v1/admin/access?tenant_scope=all`
- `GET /v1/admin/audit-events?tenant_scope=all`
- `GET /v1/admin/tenants/{tenant_id}?tenant_scope=all`
- `GET /v1/admin/operations?tenant_scope=all`
- `POST /v1/admin/material-jobs/{job_id}/retry?tenant_scope=all`
- `POST /v1/admin/materials/{material_id}/archive?tenant_scope=all`
- `POST /v1/admin/providers/policies?tenant_scope=all`
- `POST /v1/admin/tenants/{tenant_id}/modules/{module_key}?tenant_scope=all`
- `GET /v1/admin/impersonation-sessions?tenant_scope=all&status=active`
- `POST /v1/admin/impersonation-sessions?tenant_scope=all`
- `POST /v1/admin/impersonation-sessions/{session_id}/end?tenant_scope=all`
- `GET/POST /v1/children`
- `GET/POST /v1/materials`
- `GET /v1/materials/{material_id}`
- `DELETE /v1/materials/{material_id}`
- `PATCH /v1/materials/{material_id}/learning-assets/{asset_id}/primary-accent`
- `GET /v1/material-jobs/{job_id}`
- `POST /v1/material-jobs/{job_id}/retry`
- `POST /v1/material-jobs/{job_id}/confirm`
- `GET /v1/knowledge-packs/{material_id}`
- `GET /v1/review-tasks`
- `POST /v1/practice-sessions`
- `GET /v1/speaking-attempts`
- `POST /v1/speaking-attempts`
- `GET /v1/speaking-attempts/{attempt_id}`
- `POST /v1/speaking-attempts/{attempt_id}/retry`
- `GET /v1/parent-coaching/{material_id}`
- `GET /v1/reports/weekly`

## 当前行为

- Admin API 需要 `X-Admin-Token`。本地和测试环境可以继续显式设置 `ADMIN_API_TOKEN=local-admin-token`，它会解析成 `admin_local`，并拥有 `ADMIN_PERMISSIONS` 的完整本地权限集合。
- 生产化 admin token 建议使用 `ADMIN_API_CREDENTIALS_JSON`，不要把明文 token 写进仓库或日志。每个 credential 包含 `id`、`display_name`、`email`、`role`、`status`、`permissions` 和 `token_sha256`；后端用请求 token 的 SHA-256 与 `token_sha256` 做 constant-time compare。配置 JSON 后，actor 只拥有 credential 中列出的 exact permissions；`status != active` 返回 `403 Admin user is inactive`，没有任何 admin credential 时返回 `503 Admin API token is not configured`。

  ```bash
  python - <<'PY'
  import getpass
  import hashlib

  raw_token = getpass.getpass("Admin token: ")
  print(hashlib.sha256(raw_token.encode("utf-8")).hexdigest())
  PY
  ```

  ```bash
  export ADMIN_API_CREDENTIALS_JSON='[{"id":"admin_ops","display_name":"Ops Admin","email":"ops@example.com","role":"Operations","status":"active","permissions":["admin.dashboard.read","admin.audit.read","admin.operations.read","admin.impersonation.read","admin.impersonation.end"],"token_sha256":"<64-char-sha256>"}]'
  ```

- 当前 admin permission 边界：
  - `admin.dashboard.read`：读取 `/v1/admin/dashboard`，并可作为 `/v1/admin/operations` 的兼容读权限。
  - `admin.audit.read`：读取 `/v1/admin/access` 的最近审计记录，以及 `/v1/admin/audit-events` 独立审计查询。
  - `admin.tenant.read`：读取 `/v1/admin/tenants/{tenant_id}` 租户详情。
  - `admin.operations.read`：读取 `/v1/admin/operations` 运维快照；这是 Phase 2 新增权限。
  - `admin.material.archive`、`admin.material.retry`、`admin.provider.override`、`admin.tenant.module.toggle`：受控 mutation，必须提供 `reason`，成功后写入 high-risk `AuditEvent`。
  - `admin.impersonation.start`、`admin.impersonation.read`、`admin.impersonation.end`：受监督支持会话的 start/list/end 权限；`admin.impersonation.read` 和 `admin.impersonation.end` 是 Phase 2 新增权限。start/end 必须提供 `reason`，接口不返回 parent access token 或 refresh token。
  - `admin.material.read` 保留在默认本地权限集合中；当前没有独立 endpoint 单独消费该权限。
- `/v1/admin/dashboard` 只读聚合当前数据库中的家长、孩子、讲义和解析任务，`/v1/admin/access` 返回当前管理员、exact permissions 和最近审计事件；生产级 admin login、role mutation、permission mutation 后续补齐。
- `GET /v1/admin/audit-events` 需要 `admin.audit.read`，支持 `tenant_scope`、`action`、`resource_type`、`risk_level`、`result`、`actor_id` 过滤；`limit` 会夹在 `1..100`，`cursor` 是上一页最后一条 audit id，排序为 `created_at desc, id desc`。`tenant_scope=all` 返回所有非空 scope，指定 tenant scope 时只返回 `all` 和该 tenant 的事件。
- `GET /v1/admin/tenants/{tenant_id}` 需要 `admin.tenant.read`，返回单租户 read model：`tenant`、`summary`、`children`、`materials`、`provider_policy`、`module_settings`、`weekly_reports`、`speaking_attempts`、`risk_summary`、本次读操作 `audit_event` 和 `access_context`。如果 actor 同时有 `admin.audit.read`，`access_context.recent_audit_events` 会包含该租户近期审计；否则为空。
- `GET /v1/admin/operations` 需要 `admin.operations.read` 或兼容的 `admin.dashboard.read`，返回 `summary`、`material_parse_jobs`、`media_generation`、`speaking_attempts`、`provider_configuration`、`module_toggle_coverage`、本次读操作 `audit_event` 和 `access_context`。运维 readiness 只从数据库状态和配置摘要推导，不做 Celery broker introspection；provider secret 只返回 `secret_presence` 布尔值，不返回 secret 明文。
- `GET /v1/admin/impersonation-sessions` 需要 `admin.impersonation.read`，按 `tenant_scope` 和 `status=active|ended|all` 查询，最多返回 50 条，并写入 low-risk `admin.impersonation.read` audit event。`POST /v1/admin/impersonation-sessions/{session_id}/end` 需要 `admin.impersonation.end` 和 `reason`，active session 会被置为 `ended` 并写入 high-risk `admin.impersonation.end` audit event；重复结束已结束 session 会保留原 `ended_at` 并写入 `admin.impersonation.end.already_ended` noop audit event。
- Tenant scope 遵循 no-disclosure 规则：指定 `tenant_scope` 时，只允许访问该 tenant 的详情、材料、操作快照和 impersonation session；越权或不存在的单资源请求返回同类 404，不暴露其它 tenant 是否存在。
- Admin material job retry 是受控 mutation：必须提供 `reason`，需要 `admin.material.retry` 权限，会把解析任务和材料重新置为 `processing`、重新排队识别任务，并写入 high-risk `AuditEvent`。
- Admin material archive 是受控 mutation：必须提供 `reason`，需要 `admin.material.archive` 权限，会把材料置为 `archived`、清理用户可见衍生内容，并写入 high-risk `AuditEvent`。
- Admin provider policy override 是受控 mutation：必须提供 `reason`，需要 `admin.provider.override` 权限，会写入租户级 `TenantProviderPolicy`，并写入 high-risk `AuditEvent`；接口只返回 provider key、fallback、guardrail 和 source，不返回 secret 明文。
- Admin tenant module toggle 是受控 mutation：必须提供 `reason`，需要 `admin.tenant.module.toggle` 权限，会写入租户级 `TenantModuleSetting`，并写入 high-risk `AuditEvent`；当前支持 `worksheet_import`、`ai_review`、`media_pipeline`、`speaking_score` 和 `weekly_reports`。
- Admin supervised impersonation 是受控 mutation：必须提供 `reason`，需要 `admin.impersonation.start` 权限，会创建短期 `AdminImpersonationSession` 并写入 high-risk `AuditEvent`；接口不返回 parent access token 或 refresh token。
- 本地 admin CORS 默认允许 `http://127.0.0.1:<port>` 和 `http://localhost:<port>`，可用 `ADMIN_CORS_ORIGINS` 配置固定来源，用 `ADMIN_CORS_ORIGIN_REGEX` 调整本地端口匹配。
- 上传讲义会创建 `CourseMaterial` 和 `MaterialParseJob`，然后通过 `Celery` 排队到后台识别，不再依赖前端首次读取 job 时才触发。
- 默认 `AI_PROVIDER=qwen`，Docker Compose 与本地示例环境优先使用阿里云百炼 / DashScope；自动化测试会显式设置 `AI_PROVIDER=stub` 保持稳定。
- 默认 `MEDIA_PROVIDER=real`、`MEDIA_IMAGE_PROVIDER=dashscope`、`MEDIA_TTS_PROVIDER=dashscope`，学习资产会走 DashScope 图片生成和 CosyVoice TTS；测试可显式设置 `MEDIA_PROVIDER=mock`。
- 默认 `SPEECH_PROVIDER=dashscope`、`SPEECH_ASSESSMENT_PROVIDER=dashscope`，口语评分采用 DashScope ASR + Qwen JSON 评分；测试可显式设置 `SPEECH_PROVIDER=stub`。
- 配置 `AI_PROVIDER=doubao`、`ARK_API_KEY`、`DOUBAO_VISION_MODEL_OR_ENDPOINT`、`DOUBAO_TEXT_MODEL_OR_ENDPOINT` 后，可走 Volcengine Ark / Doubao 真识别。
- 配置 `AI_PROVIDER=qwen`、`DASHSCOPE_API_KEY`、`QWEN_VISION_MODEL`、`QWEN_MODEL` 后，可走阿里云百炼 / DashScope Qwen-VL 讲义识别和 Qwen 文本解析。
- 如果当前网络依赖系统代理，需额外配置 `AI_HTTP_TRUST_ENV=true`；默认值 `false` 不会继承 shell 中的 `HTTP_PROXY` / `HTTPS_PROXY` / `NO_PROXY`。
- `GET /v1/material-jobs/{job_id}` 用于查看后台识别状态；成功后状态推进到 `needs_review`。
- `POST /v1/material-jobs/{job_id}/confirm` 会生成 `KnowledgePack`、`ReviewTask` 和 `ParentCoachingScript`，并触发学习资产媒体补齐任务；默认走 DashScope，也可显式切到 OpenAI 或 mock。
- `DELETE /v1/materials/{material_id}` 会把资料归档，并从用户可见入口移除知识包、复习任务和亲子陪练脚本。
- `POST /v1/practice-sessions` 会完成对应复习任务并更新周报统计。
- `POST /v1/speaking-attempts` 接收 multipart 音频上传，保存 `owner_type=speaking_attempt` 的音频对象，创建 `recording_uploaded` attempt，并由 worker 异步评分；接口本身不等待语音 provider 完成。
- `GET /v1/speaking-attempts/{attempt_id}` 用于移动端轮询评分结果；`POST /v1/speaking-attempts/{attempt_id}/retry` 可对失败 attempt 重新入队。
- DashScope ASR 需要云端可访问的公网音频 URL；本地 `localhost`、`testserver`、`192.168.*` 等地址会被提前拒绝。真机调试时可配置 `SPEECH_ASSESSMENT_AUDIO_PUBLIC_BASE_URL`，让 worker 把 `audio_object_key` 改写成公网 `/uploads/{object_key}` 后再交给 provider。
- `GET /v1/reports/weekly` 会返回周报基础统计、讲义汇总和每个 `learning_asset` 的掌握度、复习表现、口语表现与推荐动作。

## Admin Phase 3 运维平台化

Phase 3 把 admin 后端从单个 route 文件中的堆叠逻辑拆到 `app.services.admin.*` 服务层，现有 `/v1/admin/...` path 和 Phase 2 response keys 保持兼容。

服务层边界：

- `app.services.admin.identity`：解析本地 token、`ADMIN_API_CREDENTIALS_JSON`、token SHA-256 比对和 inactive admin 拒绝。
- `app.services.admin.permissions`：exact permission 检查、any-permission read fallback 和统一 missing permission 错误。
- `app.services.admin.scope`：`tenant_scope=all` 与单租户 no-disclosure 边界。
- `app.services.admin.audit`：审计事件写入、分页过滤、resource timeline 和 route read audit。
- `app.services.admin.read_models`：dashboard 与 tenant detail read model。
- `app.services.admin.operations`：operations snapshot、severity、issue vocabulary 和 recommended action。
- `app.services.admin.actions`：mutation `action_result` 统一合同。

`GET /v1/admin/operations` 的 Phase 3 `issues` 合同：

- `severity`：`ok|info|warning|critical`，供 UI 直接映射状态颜色。
- `status_label`：后台可读问题名称。
- `reason`：问题原因，不要求 UI 重新推断。
- `recommended_action`：后端给出的建议动作；UI 不在本地猜测。
- `required_permission`：执行该动作所需权限；不可执行时可以缺省或使用 unavailable action。
- `related_resource`：包含 `type`、`id`、可选 `tenant_id`、`material_id`、`child_id`。
- `source="database_snapshot"`：当前只代表数据库与配置快照，不代表真实 worker broker 状态。

所有 Phase 3 mutation response 都应包含：

- `required_permission`
- 原资源 payload，例如 `material`、`provider_policy`、`module_setting` 或 `impersonation_session`
- `action_result`：`action`、`status=success|noop|failed|unavailable`、`resource_type`、`resource_id`、`tenant_id`、`message`
- `audit_event`

Worker-facing health 仍然是 `source="database_snapshot"` 的运维摘要：可以用于发现解析失败、媒体失败、stale processing、provider 配置缺失等信号，但不能解读为 Celery broker queue depth、worker heartbeat 或真实 broker introspection。

验证入口：

```bash
make api-test
```

## 本地运行

```bash
UV_CACHE_DIR=/tmp/learning_english_uv_cache uv sync --group dev
.venv/bin/alembic upgrade head
ADMIN_API_TOKEN=local-admin-token .venv/bin/uvicorn app.main:app --reload
```

本地 admin 页面如需接入 API：

```bash
ADMIN_API_BASE_URL=http://127.0.0.1:8000 ADMIN_API_TOKEN=local-admin-token make admin-dev-live
```

## 测试

```bash
.venv/bin/pytest
```
