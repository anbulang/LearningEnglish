# LearningEnglish Workers

Celery worker 服务，负责处理讲义识别、学习资产媒体补齐和轻量周报聚合。

## 当前任务

### 已落地

- `materials.process_material_job`
  - 读取讲义图片
  - 调用 OCR / 结构化解析 provider
  - 回写 `draft_image_records`、`draft_learning_assets`
  - 将资料推进到 `needs_review`
- `materials.process_learning_asset_media`
  - 对已确认学习资产补齐配图与英美音 TTS
  - 回填 `CourseMaterial`、`KnowledgePack`、`ReviewTask`
- `reporting.aggregate_weekly_report`
  - 生成当前轻量推荐语
- `speaking.score_attempt`
  - 读取已上传的孩子跟读音频
  - 调用 speech assessment provider
  - 回写 transcript、维度分、逐词反馈和中文建议
  - 评分成功后累计 `WeeklyReport.speaking_attempts`
- `phonics.process_unit_media`
  - 为拼读课程单元生成 sound cards、单词、句子的媒体资源
  - 复用当前媒体 provider，结果按共享课程资源存储
- `phonics.score_attempt`
  - 读取孩子的拼读录音
  - 调用拼读评分逻辑并回写 transcript、accuracy、pass/fail 与进度

### 预留任务（未实现）

以下任务名为历史预留，仅返回固定占位状态，真实链路已整合在 `process_material_job` 与 `process_learning_asset_media`，不会调度它们。各任务带 `未实现` docstring，并由 `tests/test_reserved_placeholder_tasks.py` 锁定契约，防止被误当成真实链路。

- `materials.enhance_images`
- `materials.run_ocr`
- `knowledge.parse_material`
- `review.generate_tasks`
- `speaking.generate_tts`

## 与 API 的关系

- worker 复用 `services/api` 下的 SQLAlchemy model、provider 封装和 pipeline 逻辑。
- 资料一旦被归档为 `archived`，worker 会跳过对应任务，避免已删除资料被重新写回可见状态。
- 如果 Doubao 调用需要走系统代理，worker 进程也必须显式带上 `AI_HTTP_TRUST_ENV=true`；仅在 shell 中导出代理变量还不够。
- 学习资产媒体默认使用 DashScope 真实 provider；测试环境可显式设置 `MEDIA_PROVIDER=mock`。若当前网络依赖系统代理，还需显式设置 `MEDIA_HTTP_TRUST_ENV=true`。
- speaking 默认使用 DashScope ASR + Qwen 评分；测试环境可显式设置 `SPEECH_PROVIDER=stub`。DashScope ASR 需要公网可访问音频 URL，本地或局域网 URL 会被 provider 提前拒绝；真机调试时可配置 `SPEECH_ASSESSMENT_AUDIO_PUBLIC_BASE_URL`，让 worker 使用公网 `/uploads/{object_key}`。
- `phonics` 课程媒体和录音评分也由 worker 承接；如需预热课程内容，可先运行 `make phonics-seed`，再观察 `phonics.process_unit_media` / `phonics.score_attempt` 的任务推进。

## 本地运行

```bash
UV_CACHE_DIR=/tmp/learning_english_uv_cache uv sync
.venv/bin/celery -A workers_app.celery_app.celery_app worker --loglevel=info
```

## 测试

```bash
.venv/bin/pytest -q
```
