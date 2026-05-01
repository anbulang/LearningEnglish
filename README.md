# LearningEnglish

LearningEnglish is a parent-led English review app for early learners. It turns printed worksheets from live classes into structured digital review packs with guided listening, lightweight practice, and parent coaching.

This repository now contains a closed-pilot MVP baseline:
- a Flutter monorepo layout for phone and tablet with guarded auth routes
- shared Dart domain contracts and design tokens
- a FastAPI backend with persisted auth, multipart uploads, and provider-backed OCR/parsing
- Celery workers, PostgreSQL/Redis/MinIO local infrastructure, and Alembic migrations

## Repository Layout
- `apps/mobile`: Flutter app scaffold for phone and tablet layouts
- `packages/contracts`: shared Dart contracts matching the documented domain model
- `packages/design_tokens`: Flutter design tokens derived from the design system
- `services/api`: FastAPI service for the first vertical slice
- `services/workers`: Celery worker scaffold and provider task boundaries
- `infra`: local development infrastructure definitions
- `docs`: product, design, and architecture source-of-truth documents

## Current MVP Flow
The implemented pilot flow covers:
1. 微信登录家长账号
2. 首次登录绑定手机号
3. 创建孩子档案
4. 上传讲义图片到后端
5. 处理 `CourseMaterial -> MaterialParseJob -> KnowledgePack -> ReviewTask`
6. 家长确认 OCR/解析结果
7. 获取课程详情、复习任务、亲子陪练脚本
8. 提交 practice session 和 speaking attempt
9. 查看周报聚合结果

The Flutter app now targets the same flow in adaptive page structure:
- 启动恢复 / 登录 / 绑定手机号
- 首页
- 资料库
- 上传扫描
- AI 校对
- 课程详情
- 复习入口
- 口语陪练
- 亲子陪练
- 我的

## Tooling Status
- `python3`: available locally
- `uv`: available locally
- `flutter`: verified locally with Flutter `3.41.6`
- `dart`: verified locally with Dart `3.11.4`

The Flutter workspace has been bootstrapped locally and `flutter analyze` passes for `apps/mobile`.

## Local Development
### Backend
```bash
cd services/api
UV_CACHE_DIR=/tmp/learning_english_uv_cache uv sync --group dev
.venv/bin/alembic upgrade head
.venv/bin/uvicorn app.main:app --reload
```

### Worker
```bash
cd services/workers
UV_CACHE_DIR=/tmp/learning_english_uv_cache uv sync --group dev
.venv/bin/celery -A workers_app.celery_app.celery_app worker --loglevel=info
```

### Infrastructure
```bash
cp infra/.env.example infra/.env
docker compose -f infra/docker-compose.yml up -d
```

### Database Migration
```bash
make api-migrate
```

### Mobile
```bash
make mobile-bootstrap
make mobile-analyze
cd apps/mobile
flutter run
```

Build a local Android test APK:
```bash
make mobile-apk
```

Build and export a local iOS internal/Profile IPA:
```bash
make mobile-ios-ipa
```

The iOS target uses bundle id `com.anbulang.learningenglish` with Apple Developer Team `95RDXKW54K`. The local signing identity is `Apple Development: shenchao.bupt@gmail.com (4PZWF88ND8)`. A successful export writes the internal Profile IPA to `dist/ios/export/learning_english_mobile.ipa`. Do not install a Flutter Debug archive for normal home-screen testing; Debug builds require Flutter tooling or Xcode to launch and will crash when opened directly on iOS 14+. If `make mobile-ios-ipa` fails with provisioning errors, confirm the Xcode account can manage Team `95RDXKW54K` and that the test device is included in the generated development provisioning profile.

To point the mobile app at a non-local API host:
```bash
cd apps/mobile
flutter run --dart-define=API_BASE_URL=http://<host>:8000/v1
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
- Backend auth + material flow: `ParentAccount -> ChildProfile -> CourseMaterial -> MaterialParseJob -> KnowledgePack -> ReviewTask -> PracticeSession`
- Adaptive navigation: phone, compact tablet, full tablet breakpoints
- Domain naming alignment with `docs/architecture/data-models.md`
- Alembic migration: `services/api/alembic/versions/20260327_0001_init_mvp_schema.py`

## Short MVP Delivery Flow
Use this when preparing a demo or internal test package:

1. `cp infra/.env.example infra/.env`
2. `make infra-up`
3. `make api-install && make worker-install`
4. `make api-migrate`
5. Start API: `make api-dev`
6. Start worker: `make worker-dev`
7. Validate backend: `make api-test && make worker-test`
8. Validate mobile: `make mobile-bootstrap && make mobile-analyze`
9. Run app locally: `cd apps/mobile && flutter run --dart-define=API_BASE_URL=http://127.0.0.1:8000/v1`
10. Build Android debug APK: `make mobile-apk`

## Demo Login Notes
- MVP defaults to stub providers so it can run without real WeChat, SMS, OCR, or LLM credentials.
- In non-production environments, phone OTP responses include `debug_code`, currently `123456`.
- Core demo path: 登录 -> 绑定手机号 -> 创建默认孩子 -> 上传讲义 -> AI 校对 -> 课程详情 -> 复习 -> 报告。

## Doubao Worksheet Recognition
The AI pipeline defaults to `AI_PROVIDER=stub`. To run the first real worksheet-recognition slice with Doubao / Volcengine Ark, set these values in `infra/.env` and in the API/worker process environment:

```bash
AI_PROVIDER=doubao
ARK_API_KEY=<your-volcengine-ark-api-key>
ARK_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
DOUBAO_VISION_MODEL_OR_ENDPOINT=<your-vision-model-or-endpoint>
DOUBAO_TEXT_MODEL_OR_ENDPOINT=<your-text-model-or-endpoint>
AI_REQUEST_TIMEOUT_SECONDS=60
AI_MAX_IMAGE_COUNT=5
```

This API key was verified locally against `doubao-seed-2-0-lite-260215` for both text and vision requests. If a different model returns `ModelNotOpen`, either activate that model in Ark Console or use an `ep-...` endpoint ID from Online Inference.

Run the provider smoke test without printing secrets:

```bash
services/api/.venv/bin/python scripts/harness/smoke_doubao.py
```

The app contract does not change in Doubao mode: upload still creates `CourseMaterial -> MaterialParseJob`, polling moves the job to `needs_review`, parent confirmation creates `KnowledgePack` and three MVP review tasks. If the Doubao call fails, the job is marked `failed` with a readable `confidence_summary` and can be retried.

For a manual smoke test, start API and worker with the variables above, upload a real worksheet photo from the mobile app, then verify the AI review page shows extracted words and sentences before confirming.

## Harness Deliverables
- Non-technical trial guide: `docs/harness/non-technical-pilot-guide.md`
- MVP readiness checklist: `docs/harness/mvp-readiness-checklist.md`
- iOS export options: `apps/mobile/ios/ExportOptions.internal.plist`
