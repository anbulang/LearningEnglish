# 后端架构

## 技术栈

- `FastAPI`：REST API
- `SQLAlchemy` + `Alembic`：数据模型与迁移
- `Celery` + `Redis`：异步任务队列
- `PostgreSQL`：主业务数据
- 本地文件系统或 MinIO 兼容对象存储：讲义图片、mock 媒体等文件

## 当前服务边界

当前后端是一个模块化单体：

- `auth`：微信登录占位、手机号验证码、Token 刷新、登出、`/me`
- `children`：孩子档案创建与列表
- `materials`：讲义上传、资料详情、归档删除、学习资产主发音切换
- `material_jobs`：识别状态查询、确认、重试
- `knowledge`：课程详情中的知识包读取
- `review`：复习任务查询、练习完成
- `speaking`：口语尝试列表和创建
- `parent_coaching`：亲子陪练脚本读取
- `reports`：周报读取

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
  - 对已确认的学习资产补齐 mock 配图和英美音 TTS
  - 回填 `CourseMaterial`、`KnowledgePack`、`ReviewTask`
- `reporting.aggregate_weekly_report`
  - 生成轻量推荐语

以下任务名已预留，但当前仍是占位：

- `materials.enhance_images`
- `materials.run_ocr`
- `knowledge.parse_material`
- `review.generate_tasks`
- `speaking.generate_tts`
- `speaking.score_attempt`

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
- 学习资产媒体：
  - `HN014MockMediaProvider`

目前真实外部依赖主要集中在 Doubao；媒体生成仍使用仓库内 mock 资源，不接真实图片/TTS 服务。

## 存储约定

- 原始图片和派生文件不进 PostgreSQL。
- PostgreSQL 保存元数据、状态、JSON 结构化结果和领域关系。
- `CourseMaterial.image_records` 与 `CourseMaterial.learning_assets` 当前作为 JSON 字段保存。
- `KnowledgePack.vocabulary_items`、`sentence_patterns` 和 `ReviewTask.content_json` 也使用 JSON 存储。

## 当前限制

- 真正的 OCR、语音评分、真实 TTS 还没有全部生产化。
- 周报聚合仍是轻量逻辑，不是完整学习分析系统。
- 任务队列默认面向本地环境验证，尚未形成生产级重试、监控和告警规范。
