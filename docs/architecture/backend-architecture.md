# 后端架构

## 技术栈

- `FastAPI`：REST API
- `SQLAlchemy` + `Alembic`：数据模型与迁移
- `Celery` + `Redis`：异步任务队列
- `PostgreSQL`：主业务数据
- 本地文件系统或 MinIO 兼容对象存储：讲义图片、mock 媒体等文件

## 当前服务边界

当前后端仍是一个 FastAPI 模块化单体，但代码边界按入口和运行责任分组：

- `api/parent`：家长端 HTTP API，继续暴露 `/v1/auth`、`/v1/materials`、`/v1/reports` 等原有路径，并使用 `Bearer` parent token。
- `api/admin`：运维管理 HTTP API，继续暴露 `/v1/admin/*`，并使用 admin 身份、权限和审计边界。
- `services/parent`：家长端业务编排，例如登录、验证码、token 刷新和家长资料读取。
- `services/admin`：运维管理业务编排，例如 admin identity、permission、scope、audit、operations read model 和 action result。
- `services/shared`：被 API 与 worker 共用的基础能力，例如 provider pipeline、storage、queue enqueue helper、mapper、learning asset media、speaking assessment。
- `db` / `models` / `core`：数据库模型、契约模型、settings、DB session 和安全基础能力。

外部路径保持兼容：家长端继续访问 `/v1/*`，运维管理继续访问 `/v1/admin/*`。

## 已实现 API 面

### 鉴权与会话

- `POST /v1/auth/wechat/login`
- `POST /v1/auth/phone/request-otp`
- `POST /v1/auth/phone/bind`
- `POST /v1/auth/refresh`
- `POST /v1/auth/logout`
- `GET /v1/auth/me`
- `GET /v1/me`

### 核心业务

- `GET/POST /v1/children`
- `GET/POST /v1/materials`
- `GET /v1/materials/{material_id}`
- `DELETE /v1/materials/{material_id}`
- `PATCH /v1/materials/{material_id}/learning-assets/{asset_id}/primary-accent`
- `GET /v1/material-jobs/{job_id}`
- `POST /v1/material-jobs/{job_id}/confirm`
- `POST /v1/material-jobs/{job_id}/retry`
- `GET /v1/knowledge-packs/{material_id}`
- `GET /v1/review-tasks`
- `POST /v1/practice-sessions`
- `GET/POST /v1/speaking-attempts`
- `GET /v1/parent-coaching/{material_id}`
- `GET /v1/reports/weekly`

## 当前异步任务

- `materials.process_material_job`
  - 读取讲义图片
  - 调用 OCR / 解析 provider
  - 回写 `draft_image_records`、`draft_learning_assets`
  - 将资料推进到 `needs_review`
- `materials.process_learning_asset_media`
  - 对已确认的学习资产补齐配图和英美音 TTS
  - 回填 `CourseMaterial`、`KnowledgePack`、`ReviewTask`
- `reporting.aggregate_weekly_report`
  - 生成轻量推荐语
- `speaking.score_attempt`
  - 读取已上传的孩子跟读音频
  - 调用 speech assessment provider
  - 回写 transcript、维度分、逐词反馈和中文建议
  - 评分成功后累计 `WeeklyReport.speaking_attempts`

以下任务名已预留，但当前仍是占位（带 `未实现` docstring，并由 `services/workers/tests/test_reserved_placeholder_tasks.py` 锁定契约，调用方不应依赖其副作用）：

- `materials.enhance_images`
- `materials.run_ocr`
- `knowledge.parse_material`
- `review.generate_tasks`
- `speaking.generate_tts`

## 当前状态机

### `CourseMaterial.status`

`processing -> needs_review -> ready -> archived`

失败时会进入：

`processing -> failed`

### `MaterialParseJob.status`

`processing -> needs_review -> ready`

失败或重试时：

`processing -> failed -> processing`

## Provider 策略

后端当前已经不是“只靠 stub”：

- OCR：
  - `StubOCRProvider`
  - `PaddleOCRProvider`（可选依赖）
  - `DoubaoVisionOCRProvider`
- 结构化解析：
  - `StubLanguageParsingProvider`
  - `DoubaoLanguageParsingProvider`
  - `QwenLanguageParsingProvider`
- 学习资产媒体：
  - Learning Asset Media Provider（mock / OpenAI image+TTS / DashScope image+TTS）
- 口语评分：
  - `StubSpeechAssessmentProvider`
  - DashScope ASR + Qwen JSON 评分 provider

当前本地示例和 Docker Compose 默认使用阿里云百炼 / DashScope：`AI_PROVIDER=qwen`、`MEDIA_PROVIDER=real`、`MEDIA_IMAGE_PROVIDER=dashscope`、`MEDIA_TTS_PROVIDER=dashscope`、`SPEECH_PROVIDER=dashscope`。自动化测试仍会显式设置 stub/mock，以便不依赖外网。

## 存储约定

- 原始图片和派生文件不进 PostgreSQL。
- PostgreSQL 保存元数据、状态、JSON 结构化结果和领域关系。
- `CourseMaterial.image_records` 与 `CourseMaterial.learning_assets` 当前作为 JSON 字段保存。
- `KnowledgePack.vocabulary_items`、`sentence_patterns` 和 `ReviewTask.content_json` 也使用 JSON 存储。

## 当前限制

- 真实 OCR、真实媒体和真实语音评分都已有默认可运行路径，但 readiness 仍依赖本机网络、provider 密钥和物理设备证据，不是“开箱即生产”。
- 周报聚合仍是轻量逻辑，不是完整学习分析系统。
- 任务队列默认面向本地环境验证，尚未形成生产级重试、监控和告警规范。
