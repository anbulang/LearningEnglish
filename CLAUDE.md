# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

LearningEnglish 把线下英语讲义变成可复习、可陪练、可追踪的家庭学习包。家长拍照上传讲义 → AI 识别 → 家长校对 → 生成课程包 → 复习/口语练习 → 周报。核心后端链路：

```
ParentAccount -> ChildProfile -> CourseMaterial -> MaterialParseJob
-> KnowledgePack -> ReviewTask -> PracticeSession -> WeeklyReport
```

Polyglot monorepo:
- `services/api` — FastAPI 后端 (Python, managed by `uv`)
- `services/workers` — Celery worker (Python, managed by `uv`)
- `apps/mobile` — Flutter 移动端 (phone/tablet 自适应)
- `apps/admin` — React/Vite 运维管理后台
- `packages/contracts`, `packages/design_tokens` — Dart 共享包
- `infra` — Docker Compose (PostgreSQL, Redis, MinIO)

## Commands

The `Makefile` is the canonical task entry point — prefer it over raw `uv`/`flutter`/`npm` invocations so env defaults stay consistent.

| Task | Command |
| --- | --- |
| Bring up local infra | `cp infra/env/local.example.env infra/.env && make infra-up` |
| Install / migrate API | `make api-install && make api-migrate` |
| Run API (reload) | `make api-dev` |
| Run worker | `make worker-install && make worker-dev` |
| API tests | `make api-test` |
| Worker tests | `make worker-test` |
| Mobile deps / analyze / test | `make mobile-bootstrap` · `make mobile-analyze` · `make mobile-test` |
| Run mobile | `cd apps/mobile && flutter run --dart-define=API_BASE_URL=http://127.0.0.1:8000/v1` |
| Admin (mock data) | `make admin-install && make admin-dev` |
| Admin against live API | `make admin-dev-live` |
| Admin test / build | `make admin-test` · `make admin-build` |

Run a single Python test (the suite installs into a local `.venv`):

```bash
cd services/api && .venv/bin/pytest tests/test_main_chain_smoke.py
cd services/api && .venv/bin/pytest tests/test_speaking_attempts.py::test_name -x
```

Non-production phone-OTP flows return `debug_code` in the API response (default `123456`).

## Architecture you can't see from one file

**Modular monolith with enforced boundaries.** `services/api/app` is one FastAPI app, but code is split by entry + runtime responsibility:
- `api/parent` — 家长端 HTTP (`/v1/*`, Bearer parent token)
- `api/admin` — 运维管理 HTTP (`/v1/admin/*`, admin identity/permission/audit)
- `services/parent`, `services/admin` — business orchestration per side
- `services/shared` — provider pipeline, storage, queue enqueue, mappers, media, speaking assessment (shared by API **and** workers)
- `core` / `db` / `models` / `repositories` — settings, DB session, security, contracts

These boundaries are **asserted by `services/api/tests/test_engineering_boundaries.py`**: routes must live under `api/parent` or `api/admin` (no `api/routes`), services must split into `parent`/`admin`/`shared`, workers must not import `app.api`, and public `/v1` paths must stay stable. Don't restructure these directories without updating that test — it will fail loudly.

**Async work** is enqueued to Celery (`services/workers/workers_app/tasks.py`). Live tasks: `materials.process_material_job` (OCR/parse → `needs_review`), `materials.process_learning_asset_media` (image + en/us TTS backfill), `speaking.score_attempt` (ASR + scoring), `reporting.aggregate_weekly_report`. Several task names (`materials.run_ocr`, `knowledge.parse_material`, etc.) are reserved placeholders — check before assuming they do work.

**Storage convention:** raw images and derived media never enter Postgres. Postgres holds metadata, status, and JSON structured results (`CourseMaterial.image_records`/`learning_assets`, `KnowledgePack.vocabulary_items`/`sentence_patterns`, `ReviewTask.content_json` are JSON columns). Files go to local FS or MinIO.

**Mobile** (`apps/mobile/lib`) is `flutter_riverpod` + `go_router` + `dio`, organized as `features/<name>` (auth, materials, lessons, review, speaking, coaching, reports, …) over a `core/` layer. No local DB (no Drift) — state is API + in-memory providers, async results via **polling** `material-jobs`, not push. `AppRepository` auto-refreshes session on `401`. Material routing (ready → `/lessons/:id`, otherwise → `/materials/review/:jobId`) is centralized in `features/materials/presentation/material_navigation.dart`; reuse it rather than re-deriving readiness.

## AI providers

Local + Docker default to Aliyun DashScope / Qwen: `AI_PROVIDER=qwen`, `MEDIA_PROVIDER=real`, `SPEECH_PROVIDER=dashscope`. **Tests pin everything to stub/mock** (`AI_PROVIDER=stub`, `MEDIA_PROVIDER=mock`, `SPEECH_PROVIDER=stub`) via `services/api/tests/conftest.py` so they never hit the network — keep that the default for new tests. Doubao/Volcengine Ark is an alternate provider (`AI_PROVIDER=doubao`). The AI HTTP client does **not** inherit shell proxies unless `AI_HTTP_TRUST_ENV=true` — relevant when real-provider calls fail behind a corporate/Wi-Fi proxy. DashScope speaking-assessment needs a publicly reachable audio URL; `localhost`/`127.0.0.1`/`192.168.*`/`testserver` bases fail fast by design.

## Harness / evidence workflow

This project verifies via **Harness Engineering**: each requirement (`HN-NNN`) defines an automation command, manual evidence, and an evidence directory under `dist/harness/HN-*/`. When adding or validating features, follow this — run the relevant `make harness-*` target and check its log:

```bash
HARNESS_RESET=1 make harness-mvp-readiness   # full MVP readiness regression
make harness-main-chain-smoke                # backend main-chain smoke
make harness-doubao-smoke                    # real Doubao provider connectivity
make harness-capture-ios-screen SCREEN=login-screen
```

## Conventions

- New requirements and docs are written **in Chinese** by default (see `docs/` and `README.md`). The source-of-truth doc index is in `README.md` § 文档入口.
- `packages/contracts` (Dart) mirrors the API's Pydantic models — keep them aligned when changing API shapes.
- iOS builds default to bundle id `com.anbulang.learningenglish`, Apple team `95RDXKW54K`; real-device builds must override `IOS_API_BASE_URL` with the current LAN IP (`make mobile-ios-ipa IOS_API_BASE_URL=http://<lan-ip>:8000/v1`).
