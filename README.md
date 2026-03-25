# LearningEnglish

LearningEnglish is a parent-led English review app for early learners. It turns printed worksheets from live classes into structured digital review packs with guided listening, lightweight practice, and parent coaching.

This repository now contains the first implementation scaffold for the next execution phase:
- a Flutter monorepo layout for phone and tablet
- shared Dart domain contracts and design tokens
- a FastAPI vertical-slice backend with stub OCR/LLM processing
- worker and infrastructure scaffolding for Celery, Redis, PostgreSQL, and object storage

## Repository Layout
- `apps/mobile`: Flutter app scaffold for phone and tablet layouts
- `packages/contracts`: shared Dart contracts matching the documented domain model
- `packages/design_tokens`: Flutter design tokens derived from the design system
- `services/api`: FastAPI service for the first vertical slice
- `services/workers`: Celery worker scaffold and provider task boundaries
- `infra`: local development infrastructure definitions
- `docs`: product, design, and architecture source-of-truth documents

## Current Vertical Slice
The implemented backend slice covers:
1. create a course material
2. poll a material parse job
3. confirm OCR/AI review
4. fetch the generated knowledge pack
5. fetch review tasks
6. create a practice session

The mobile scaffold covers the same flow in adaptive page structure:
- 首页
- 资料库
- 上传扫描
- AI 校对
- 课程详情
- 复习入口

## Tooling Status
- `python3`: available locally
- `uv`: available locally
- `flutter`: not installed locally at the time of implementation
- `dart`: not installed locally at the time of implementation

The Flutter code is scaffolded but could not be compiled in this environment because the SDK is missing.

## Local Development
### Backend
```bash
cd services/api
UV_CACHE_DIR=/tmp/learning_english_uv_cache uv sync --group dev
.venv/bin/uvicorn app.main:app --reload
```

### Worker
```bash
cd services/workers
UV_CACHE_DIR=/tmp/learning_english_uv_cache uv sync
.venv/bin/celery -A workers_app.celery_app.celery_app worker --loglevel=info
```

### Infrastructure
```bash
docker compose -f infra/docker-compose.yml up -d
```

### Mobile
Once Flutter is installed:
```bash
melos bootstrap
cd apps/mobile
flutter run
```

## Verification Targets
- Backend contract flow: `CourseMaterial -> MaterialParseJob -> KnowledgePack -> ReviewTask -> PracticeSession`
- Adaptive navigation: phone, compact tablet, full tablet breakpoints
- Domain naming alignment with `docs/architecture/data-models.md`
