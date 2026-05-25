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
- `POST /v1/admin/material-jobs/{job_id}/retry?tenant_scope=all`
- `POST /v1/admin/materials/{material_id}/archive?tenant_scope=all`
- `POST /v1/admin/providers/policies?tenant_scope=all`
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
- `GET/POST /v1/speaking-attempts`
- `GET /v1/parent-coaching/{material_id}`
- `GET /v1/reports/weekly`

## 当前行为

- Admin read API 需要 `X-Admin-Token`，默认本地 token 为 `local-admin-token`。`/v1/admin/dashboard` 只读聚合当前数据库中的家长、孩子、讲义和解析任务，`/v1/admin/access` 返回当前管理员、权限和最近审计事件；生产级 admin session、role mutation、permission mutation 后续补齐。
- Admin material job retry 是受控 mutation：必须提供 `reason`，需要 `admin.material.retry` 权限，会把解析任务和材料重新置为 `processing`、重新排队识别任务，并写入 high-risk `AuditEvent`。
- Admin material archive 是受控 mutation：必须提供 `reason`，需要 `admin.material.archive` 权限，会把材料置为 `archived`、清理用户可见衍生内容，并写入 high-risk `AuditEvent`。
- Admin provider policy override 是受控 mutation：必须提供 `reason`，需要 `admin.provider.override` 权限，会写入租户级 `TenantProviderPolicy`，并写入 high-risk `AuditEvent`；接口只返回 provider key、fallback、guardrail 和 source，不返回 secret 明文。
- 本地 admin CORS 默认允许 `http://127.0.0.1:<port>` 和 `http://localhost:<port>`，可用 `ADMIN_CORS_ORIGINS` 配置固定来源，用 `ADMIN_CORS_ORIGIN_REGEX` 调整本地端口匹配。
- 上传讲义会创建 `CourseMaterial` 和 `MaterialParseJob`，然后通过 `Celery` 排队到后台识别，不再依赖前端首次读取 job 时才触发。
- 默认 `AI_PROVIDER=stub`，可以直接跑通本地 MVP。
- 配置 `AI_PROVIDER=doubao`、`ARK_API_KEY`、`DOUBAO_VISION_MODEL_OR_ENDPOINT`、`DOUBAO_TEXT_MODEL_OR_ENDPOINT` 后，可走 Volcengine Ark / Doubao 真识别。
- 如果当前网络依赖系统代理，需额外配置 `AI_HTTP_TRUST_ENV=true`；默认值 `false` 不会继承 shell 中的 `HTTP_PROXY` / `HTTPS_PROXY` / `NO_PROXY`。
- `GET /v1/material-jobs/{job_id}` 用于查看后台识别状态；成功后状态推进到 `needs_review`。
- `POST /v1/material-jobs/{job_id}/confirm` 会生成 `KnowledgePack`、`ReviewTask` 和 `ParentCoachingScript`，并触发学习资产 mock 媒体补齐。
- `DELETE /v1/materials/{material_id}` 会把资料归档，并从用户可见入口移除知识包、复习任务和亲子陪练脚本。
- `POST /v1/practice-sessions` 会完成对应复习任务并更新周报统计。
- `POST /v1/speaking-attempts` 当前返回 stub 反馈，并累计周报中的口语次数。

## 本地运行

```bash
UV_CACHE_DIR=/tmp/learning_english_uv_cache uv sync --group dev
.venv/bin/alembic upgrade head
.venv/bin/uvicorn app.main:app --reload
```

本地 admin 页面如需接入 API：

```bash
ADMIN_API_BASE_URL=http://127.0.0.1:8000 ADMIN_API_TOKEN=local-admin-token make admin-dev-live
```

## 测试

```bash
.venv/bin/pytest
```
