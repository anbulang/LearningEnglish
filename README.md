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
成功时 APK 位于 `apps/mobile/build/app/outputs/flutter-apk/app-debug.apk`。如果返回 `/opt/homebrew/share/flutter/bin/cache/engine.stamp: Operation not permitted`，这是本机全局 Flutter SDK cache 写入权限阻塞；可临时复制一份用户可写 Flutter SDK 后用 `FLUTTER=/private/tmp/learningenglish-flutter/bin/flutter make mobile-apk` 继续验证。如果随后返回 `No Android SDK found`，说明下一层 blocker 是本机 Android SDK 未安装或未配置。这些环境问题不代表 Flutter 代码或 MVP 主链失败。

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

## Harness Engineering 验证入口
后续需求默认使用中文文档和 Harness Engineering 验收方式。每条需求都要说明自动化命令、人工证据和证据目录。

常用命令：

```bash
HARNESS_RESET=1 make harness-mvp-readiness
make harness-main-chain-smoke
make harness-doubao-smoke
make harness-reset-ios-sim
make harness-capture-ios-screen SCREEN=login-screen
```

证据目录：
- `dist/harness/mvp-readiness.log`
- `dist/harness/HN-*/`
- `dist/harness/screens/`

Clean-state UI 验证建议顺序：
1. 重置后端并确认数据状态。
2. 启动 iOS simulator。
3. 运行 `make harness-reset-ios-sim`。
4. 用当前 API URL 运行 App。
5. 逐页运行 `make harness-capture-ios-screen SCREEN=<name>` 留存截图。

## Demo Login Notes
- MVP defaults to stub providers so it can run without real WeChat, SMS, OCR, or LLM credentials.
- In non-production environments, phone OTP responses include `debug_code`, currently `123456`.
- Core demo path: 登录 -> 绑定手机号 -> 创建默认孩子 -> 上传讲义 -> AI 校对 -> 课程详情 -> 复习 -> 报告。

## Doubao Worksheet Recognition
AI pipeline 默认使用 `AI_PROVIDER=stub`。要运行第一条真实豆包 / 火山方舟讲义识别链路，需要在 `infra/.env` 以及 API/worker 进程环境中配置：

```bash
AI_PROVIDER=doubao
ARK_API_KEY=<your-volcengine-ark-api-key>
ARK_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
DOUBAO_VISION_MODEL_OR_ENDPOINT=<your-vision-model-or-endpoint>
DOUBAO_TEXT_MODEL_OR_ENDPOINT=<your-text-model-or-endpoint>
AI_REQUEST_TIMEOUT_SECONDS=180
AI_MAX_IMAGE_COUNT=5
```

豆包调用方式已与 ReceiptLens 对齐：文本和视觉都请求 `ARK_BASE_URL/responses`，文本内容使用 `input_text`，图片使用 `input_image`。真实讲义图片会比 provider smoke 慢，建议 `AI_REQUEST_TIMEOUT_SECONDS=180` 起步；前端校对页使用后台任务轮询，不会等待这个长请求。`doubao-seed-2-0-lite-260215` 可同时用于文本和视觉 smoke；如果其他模型返回 `ModelNotOpen`，需要先在火山方舟控制台开通该模型，或改用在线推理中的 `ep-...` endpoint ID。

运行 provider smoke，不会打印密钥：

```bash
make harness-doubao-smoke
```

该命令会写入 `dist/harness/HN-006/doubao-smoke.log`。缺配置时记录 `BLOCKED: Doubao provider smoke missing required configuration`；DNS/网络不可达时记录 `BLOCKED: Doubao provider smoke network/DNS unavailable`。配置完整且 provider 可用时会出现 `text_ok`、`vision_ok`、`PASS: Doubao provider smoke`。
2026-05-04 08:12 已用当前配置完成一次真实 smoke，通过项包含 `text_ok`、`vision_ok` 和 `PASS: Doubao provider smoke`。

Doubao 模式下 App 契约不变：上传仍创建 `CourseMaterial -> MaterialParseJob`，轮询后 job 进入 `needs_review`，家长确认后创建 `KnowledgePack` 和三类 MVP 复习任务。如果 Doubao 调用失败，job 会标记为 `failed`，并在 `confidence_summary` 中写入可读错误，后续可重试。

手动 smoke 时，用上述环境变量启动 API 和 worker，从移动端上传真实讲义照片，再确认 AI 校对页展示了抽取出的单词和句型。

## Harness Deliverables
- Non-technical trial guide: `docs/harness/non-technical-pilot-guide.md`
- MVP readiness checklist: `docs/harness/mvp-readiness-checklist.md`
- Upload recognition loop requirements: `docs/harness/upload-recognition-loop.md`
- Upload recognition implementation plan: `docs/superpowers/plans/2026-05-05-upload-recognition-loop.md`
- iOS export options: `apps/mobile/ios/ExportOptions.internal.plist`
