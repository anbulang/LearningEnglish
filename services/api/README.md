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

## 测试

```bash
.venv/bin/pytest
```
