# LearningEnglish Workers

Celery workers for the MVP material-processing pipeline. The worker package now shares the same SQLAlchemy models and provider-backed parsing logic as the API service, so a queued material job can be pushed from `processing` to `needs_review` by the worker task.

## Current Scope
- `materials.process_material_job`: load stored assets, run OCR/parsing providers, update `CourseMaterial` and `MaterialParseJob`
- `reporting.aggregate_weekly_report`: recompute lightweight weekly recommendations
- placeholder task names kept for later TTS/ASR expansion

## Run
```bash
UV_CACHE_DIR=/tmp/learning_english_uv_cache uv sync --group dev
.venv/bin/celery -A workers_app.celery_app.celery_app worker --loglevel=info
```

## Test
```bash
.venv/bin/pytest -q
```
