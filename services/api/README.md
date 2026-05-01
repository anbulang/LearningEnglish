# LearningEnglish API

FastAPI service for the first runnable vertical slice.

## Implemented Resources
- `GET/POST /v1/children`
- `GET/POST /v1/materials`
- `GET /v1/material-jobs/{job_id}`
- `POST /v1/material-jobs/{job_id}/retry`
- `POST /v1/material-jobs/{job_id}/confirm`
- `GET /v1/knowledge-packs/{material_id}`
- `GET /v1/review-tasks`
- `POST /v1/practice-sessions`
- `GET/POST /v1/speaking-attempts`
- `GET /v1/parent-coaching/{material_id}`
- `GET /v1/reports/weekly`

## Current Behavior
- Material upload accepts multipart worksheet image files and stores them through the configured storage backend.
- OCR and parsing default to deterministic stub providers.
- Set `AI_PROVIDER=doubao` plus `ARK_API_KEY`, `DOUBAO_VISION_MODEL_OR_ENDPOINT`, and `DOUBAO_TEXT_MODEL_OR_ENDPOINT` to run real worksheet recognition through Volcengine Ark / Doubao.
- Polling a material job advances it from `processing` to `needs_review`.
- Retrying a material job sends it back to `processing`.
- Confirming a material job creates the knowledge pack, review tasks, and parent coaching script.
- Practice session creation marks included review tasks as completed and updates the weekly report.
- Speaking attempt creation returns stub feedback and updates speaking counts in the weekly report.
- Provider failures mark the material job as `failed` with a readable retry message instead of silently falling back to fake AI output.

## Run
```bash
UV_CACHE_DIR=/tmp/learning_english_uv_cache uv sync --group dev
.venv/bin/uvicorn app.main:app --reload
```
