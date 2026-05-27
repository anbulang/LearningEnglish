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
- `GET /v1/speaking-attempts`
- `POST /v1/speaking-attempts`
- `GET /v1/speaking-attempts/{attempt_id}`
- `POST /v1/speaking-attempts/{attempt_id}/retry`
- `GET /v1/parent-coaching/{material_id}`
- `GET /v1/reports/weekly`

## 当前行为

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
