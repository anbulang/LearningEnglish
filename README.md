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
3. retry OCR/AI review when needed
4. confirm OCR/AI review
5. fetch the generated knowledge pack and parent coaching script
6. fetch review tasks
7. create a practice session
8. create a scored speaking attempt

The mobile scaffold covers the same flow in adaptive page structure:
- 首页
- 资料库
- 上传扫描
- AI 校对
- 课程详情
- 复习入口
- 口语陪练
- 亲子陪练

## Tooling Status
- `python3`: available locally
- `uv`: available locally
- `flutter`: verified locally with Flutter `3.41.5`
- `dart`: verified locally with Dart `3.11.3`

The Flutter workspace has been bootstrapped locally and `flutter analyze` passes for `apps/mobile`.

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
```bash
make mobile-bootstrap
make mobile-analyze
cd apps/mobile
flutter run
```

If Flutter is not on your `PATH`, provide it explicitly:
```bash
FLUTTER=/absolute/path/to/flutter make mobile-bootstrap
FLUTTER=/absolute/path/to/flutter make mobile-analyze
```

If you are developing behind a mainland China network, set these mirror variables before running Flutter commands:
```bash
export FLUTTER_STORAGE_BASE_URL=https://storage.flutter-io.cn
export PUB_HOSTED_URL=https://pub.flutter-io.cn
```

## Verification Targets
- Backend contract flow: `CourseMaterial -> MaterialParseJob -> KnowledgePack -> ReviewTask -> PracticeSession`
- Adaptive navigation: phone, compact tablet, full tablet breakpoints
- Domain naming alignment with `docs/architecture/data-models.md`
