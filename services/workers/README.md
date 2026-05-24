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

### 仍是占位

- `materials.enhance_images`
- `materials.run_ocr`
- `knowledge.parse_material`
- `review.generate_tasks`
- `speaking.generate_tts`
- `speaking.score_attempt`

## 与 API 的关系

- worker 复用 `services/api` 下的 SQLAlchemy model、provider 封装和 pipeline 逻辑。
- 资料一旦被归档为 `archived`，worker 会跳过对应任务，避免已删除资料被重新写回可见状态。
- 如果 Doubao 调用需要走系统代理，worker 进程也必须显式带上 `AI_HTTP_TRUST_ENV=true`；仅在 shell 中导出代理变量还不够。
- 学习资产媒体默认使用 mock provider；当 `MEDIA_PROVIDER=real` 时，可按 `MEDIA_IMAGE_PROVIDER` / `MEDIA_TTS_PROVIDER` 切到 OpenAI 或 DashScope。若当前网络依赖系统代理，还需显式设置 `MEDIA_HTTP_TRUST_ENV=true`。

## 本地运行

```bash
UV_CACHE_DIR=/tmp/learning_english_uv_cache uv sync
.venv/bin/celery -A workers_app.celery_app.celery_app worker --loglevel=info
```

## 测试

```bash
.venv/bin/pytest -q
```
