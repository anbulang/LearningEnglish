# LearningEnglish Workers

Celery worker scaffold for asynchronous OCR, parsing, review generation, speech, and reporting jobs.

## Current Scope
- Celery app bootstrap
- task names aligned with documented provider boundaries
- stub tasks that can later be replaced with real OCR/LLM/TTS/ASR implementations

## Run
```bash
UV_CACHE_DIR=/tmp/learning_english_uv_cache uv sync
.venv/bin/celery -A workers_app.celery_app.celery_app worker --loglevel=info
```
